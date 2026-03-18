#!/usr/bin/env python3
"""DAG Orchestrator — wave-based agent pipeline with dependency resolution.

CLI:
    orchestrator.py init --name 'pipeline-name'
    orchestrator.py add --id CC-viz --prompt 'Create viz' [--depends-on CC-data]
    orchestrator.py plan
    orchestrator.py run [--wave N]
    orchestrator.py status
    orchestrator.py retry --id CC-viz
    orchestrator.py clean
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# Bootstrap imports
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import manifest as mf
import worktree_manager as wm

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_MANIFEST = REPO_ROOT / "manifest.json"
POLL_INTERVAL = 5  # seconds


# ── Helpers ──────────────────────────────────────────────

def _resolve_prompt(task: dict, workdir: Path | None = None) -> str:
    """Resolve task prompt from inline or file."""
    if task.get("prompt"):
        return task["prompt"]
    if task.get("prompt_file"):
        pf = Path(task["prompt_file"])
        if not pf.is_absolute():
            pf = REPO_ROOT / pf
        return pf.read_text().strip()
    raise ValueError("Task has no prompt or prompt_file")


def _spawn_cc(task_id: str, task: dict, workdir: Path) -> subprocess.Popen:
    """Spawn a Claude Code agent in the background."""
    prompt = _resolve_prompt(task, workdir)
    model = task.get("model", "claude-sonnet-4-20250514")
    timeout = task.get("timeout", 300)

    full_prompt = f"""{prompt}

Working directory: {workdir}
Output artifacts to this directory.
IMPORTANT: When done, run `git add -A && git commit -m 'done: {task_id}'` to persist your work.
Then create a file COMPLETED.txt with summary.
On error, create FAILED.txt with error details.
"""

    cmd = [
        "claude",
        "--model", model,
        "--permission-mode", "bypassPermissions",
        "--print",
        full_prompt,
    ]

    proc = subprocess.Popen(
        cmd,
        cwd=str(workdir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc


def _check_completion(workdir: Path) -> str | None:
    """Check if a task completed. Returns 'completed', 'failed', or None."""
    if (workdir / "COMPLETED.txt").exists():
        return "completed"
    if (workdir / "FAILED.txt").exists():
        return "failed"
    return None


# ── Commands ─────────────────────────────────────────────

def cmd_init(args: argparse.Namespace) -> None:
    path = Path(args.manifest)
    if path.exists() and not args.force:
        print(f"Manifest already exists: {path}")
        print("Use --force to overwrite.")
        sys.exit(1)

    m = mf.new_manifest(args.name)
    mf.save(path, m)
    print(f"Created manifest: {path}")
    print(f"Pipeline: {args.name}")


def cmd_add(args: argparse.Namespace) -> None:
    path = Path(args.manifest)
    m = mf.load(path)

    depends = [d.strip() for d in args.depends_on.split(",") if d.strip()] if args.depends_on else []

    mf.add_task(
        m,
        args.id,
        prompt=args.prompt,
        prompt_file=args.prompt_file,
        depends_on=depends,
        model=args.model,
        timeout=args.timeout,
        retries=args.retries,
    )
    mf.save(path, m)
    deps_str = ", ".join(depends) if depends else "(none)"
    print(f"Added task '{args.id}' [depends: {deps_str}]")


def cmd_plan(args: argparse.Namespace) -> None:
    path = Path(args.manifest)
    m = mf.load(path)

    errors = mf.validate(m)
    if errors:
        print("Validation errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    waves = mf.compute_waves(m)
    m["waves"] = waves
    mf.save(path, m)

    print(f"Pipeline: {m['pipeline_name']}")
    print(f"Tasks: {len(m['tasks'])}")
    print(f"Waves: {len(waves)}")
    print()

    for i, wave in enumerate(waves, 1):
        print(f"Wave {i}:")
        for tid in wave:
            task = m["tasks"][tid]
            deps = task.get("depends_on", [])
            deps_str = f" <- [{', '.join(deps)}]" if deps else ""
            model = task.get("model", "sonnet")
            status = task.get("status", "pending")
            print(f"  {tid} ({model}) [{status}]{deps_str}")
    print()
    print("Run with: python3 orchestrator.py run")


def cmd_run(args: argparse.Namespace) -> None:
    path = Path(args.manifest)
    m = mf.load(path)

    errors = mf.validate(m)
    if errors:
        print("Validation errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    waves = mf.compute_waves(m)
    m["waves"] = waves
    mf.save(path, m)

    target_wave = args.wave  # 1-indexed, or None for all

    for wave_idx, wave in enumerate(waves, 1):
        if target_wave and wave_idx != target_wave:
            continue

        print(f"\n{'='*60}")
        print(f"Wave {wave_idx}/{len(waves)}: {wave}")
        print(f"{'='*60}")

        # Filter to ready tasks only
        ready = [tid for tid in wave if m["tasks"][tid]["status"] == "pending"]
        if not ready:
            print("  All tasks in this wave already processed. Skipping.")
            continue

        # Create worktrees + spawn CCs
        procs: dict[str, tuple[subprocess.Popen, Path]] = {}
        for tid in ready:
            task = m["tasks"][tid]
            try:
                wt_path = wm.create_worktree(tid)
            except FileExistsError:
                wm.cleanup_worktree(tid)
                wt_path = wm.create_worktree(tid)

            task["workdir"] = str(wt_path)
            mf.update_status(m, tid, "running")
            mf.save(path, m)

            print(f"  Spawning {tid} in {wt_path}...")
            proc = _spawn_cc(tid, task, wt_path)
            task["session_id"] = str(proc.pid)
            mf.save(path, m)
            procs[tid] = (proc, wt_path)

        # Poll for completion
        print(f"\n  Waiting for {len(procs)} tasks...")
        remaining = dict(procs)
        while remaining:
            for tid, (proc, wt_path) in list(remaining.items()):
                task = m["tasks"][tid]
                timeout = task.get("timeout", 300)

                # Check process exit
                retcode = proc.poll()
                completion = _check_completion(wt_path)

                if completion == "completed" or (retcode is not None and retcode == 0):
                    # Collect artifacts (recursive, skip .git)
                    artifacts = [
                        str(f.relative_to(wt_path))
                        for f in wt_path.rglob("*")
                        if f.is_file() and ".git" not in f.parts
                    ]
                    mf.update_status(m, tid, "completed", artifacts=artifacts)
                    mf.save(path, m)
                    print(f"  [{tid}] COMPLETED")
                    del remaining[tid]

                elif completion == "failed" or (retcode is not None and retcode != 0):
                    error_msg = ""
                    if (wt_path / "FAILED.txt").exists():
                        error_msg = (wt_path / "FAILED.txt").read_text()[:500]
                    elif proc.stderr:
                        error_msg = proc.stderr.read().decode()[:500] if proc.stderr.readable() else ""

                    retry_count = task.get("retry_count", 0)
                    max_retries = task.get("retries", 3)

                    if retry_count < max_retries:
                        task["retry_count"] = retry_count + 1
                        mf.update_status(m, tid, "pending", error=error_msg)
                        mf.save(path, m)
                        print(f"  [{tid}] FAILED (retry {retry_count + 1}/{max_retries})")

                        # Cleanup and re-spawn
                        wm.cleanup_worktree(tid)
                        wt_path = wm.create_worktree(tid)
                        task["workdir"] = str(wt_path)
                        mf.update_status(m, tid, "running")
                        mf.save(path, m)

                        new_proc = _spawn_cc(tid, task, wt_path)
                        remaining[tid] = (new_proc, wt_path)
                    else:
                        mf.update_status(m, tid, "failed", error=error_msg)
                        mf.save(path, m)
                        print(f"  [{tid}] FAILED (no retries left)")
                        del remaining[tid]

                elif retcode is None:
                    # Check timeout
                    started = task.get("started_at")
                    if started:
                        from datetime import datetime, timezone
                        elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(started)).total_seconds()
                        if elapsed > timeout:
                            proc.kill()
                            mf.update_status(m, tid, "failed", error=f"Timeout after {timeout}s")
                            mf.save(path, m)
                            print(f"  [{tid}] TIMEOUT ({timeout}s)")
                            del remaining[tid]

            if remaining:
                time.sleep(POLL_INTERVAL)

        # Merge completed worktrees sequentially
        print(f"\n  Merging wave {wave_idx} results...")
        for tid in ready:
            task = m["tasks"][tid]
            if task["status"] == "completed":
                try:
                    wm.merge_worktree(tid)
                    print(f"  Merged {tid}")
                except RuntimeError as e:
                    print(f"  Merge failed for {tid}: {e}")
            wm.cleanup_worktree(tid)

    # Final stats
    m = mf.load(path)
    stats = mf.get_stats(m)
    print(f"\nPipeline complete: {stats}")


def cmd_status(args: argparse.Namespace) -> None:
    path = Path(args.manifest)
    m = mf.load(path)

    stats = mf.get_stats(m)
    print(f"Pipeline: {m['pipeline_name']}")
    print(f"Stats: {stats}")
    print()

    for tid, task in m["tasks"].items():
        status = task["status"]
        icon = {"pending": ".", "running": ">", "completed": "+", "failed": "X", "skipped": "-"}.get(status, "?")
        deps = task.get("depends_on", [])
        deps_str = f" <- [{', '.join(deps)}]" if deps else ""
        error_str = f" ERR: {task['error'][:60]}..." if task.get("error") else ""
        print(f"  [{icon}] {tid}: {status}{deps_str}{error_str}")


def cmd_retry(args: argparse.Namespace) -> None:
    path = Path(args.manifest)
    m = mf.load(path)

    tid = args.id
    if tid not in m["tasks"]:
        print(f"Task not found: {tid}")
        sys.exit(1)

    task = m["tasks"][tid]
    if task["status"] != "failed":
        print(f"Task '{tid}' is not failed (status: {task['status']})")
        sys.exit(1)

    task["retry_count"] = 0
    mf.update_status(m, tid, "pending", error=None)
    mf.save(path, m)
    print(f"Reset '{tid}' to pending. Run 'orchestrator.py run' to execute.")


def cmd_clean(args: argparse.Namespace) -> None:
    path = Path(args.manifest)

    print("Cleaning worktrees...")
    wm.cleanup_all()

    if path.exists():
        m = mf.load(path)
        for tid in m["tasks"]:
            m["tasks"][tid]["status"] = "pending"
            m["tasks"][tid]["error"] = None
            m["tasks"][tid]["artifacts"] = []
            m["tasks"][tid]["workdir"] = None
            m["tasks"][tid]["started_at"] = None
            m["tasks"][tid]["completed_at"] = None
            m["tasks"][tid]["session_id"] = None
            m["tasks"][tid]["retry_count"] = 0
        m["waves"] = []
        mf.save(path, m)
        print(f"Reset manifest: {path}")

    print("Done.")


# ── CLI ──────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="DAG Orchestrator — wave-based agent pipeline")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Path to manifest.json")
    sub = parser.add_subparsers(dest="command", required=True)

    # init
    p = sub.add_parser("init", help="Create empty manifest")
    p.add_argument("--name", required=True, help="Pipeline name")
    p.add_argument("--force", action="store_true", help="Overwrite existing manifest")

    # add
    p = sub.add_parser("add", help="Add a task")
    p.add_argument("--id", required=True, help="Task ID (e.g., CC-viz)")
    p.add_argument("--prompt", help="Inline prompt")
    p.add_argument("--prompt-file", help="Path to prompt file")
    p.add_argument("--depends-on", default="", help="Comma-separated dependency IDs")
    p.add_argument("--model", default="claude-sonnet-4-20250514")
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--retries", type=int, default=3)

    # plan
    sub.add_parser("plan", help="Show execution plan")

    # run
    p = sub.add_parser("run", help="Execute pipeline")
    p.add_argument("--wave", type=int, default=None, help="Run only this wave (1-indexed)")

    # status
    sub.add_parser("status", help="Show task status")

    # retry
    p = sub.add_parser("retry", help="Retry a failed task")
    p.add_argument("--id", required=True, help="Task ID to retry")

    # clean
    sub.add_parser("clean", help="Remove worktrees + reset manifest")

    args = parser.parse_args()
    cmd = {
        "init": cmd_init,
        "add": cmd_add,
        "plan": cmd_plan,
        "run": cmd_run,
        "status": cmd_status,
        "retry": cmd_retry,
        "clean": cmd_clean,
    }
    cmd[args.command](args)


if __name__ == "__main__":
    main()
