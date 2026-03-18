#!/usr/bin/env python3
"""Experiment dispatcher for battleship GPU via SSH.

Dispatches ML experiments to the lab's GPU machine (battleship) via SSH,
tracks job queue in JSONL, and fetches results.

Usage:
    python3 experiment_dispatch.py run --exp Q001 --model whisper-small
    python3 experiment_dispatch.py run --exp Q001 --model whisper-medium
    python3 experiment_dispatch.py status
    python3 experiment_dispatch.py queue --list
    python3 experiment_dispatch.py queue --add Q002 --model whisper-small --priority high
    python3 experiment_dispatch.py results --exp Q001 --model whisper-small
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Paths ──
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
QUEUE_PATH = REPO_ROOT / "memory" / "experiments" / "queue.jsonl"
RESULTS_DIR = REPO_ROOT / "memory" / "experiments" / "results"

# ── SSH config ──
SSH_CMD_BASE = ["ssh", "-J", "iso_leo", "-p", "2222", "leonardo@localhost"]
SSH_TIMEOUT = 30

# ── Remote paths ──
REMOTE_PYTHON = "~/miniconda3/bin/python3"
REMOTE_WORKSPACE = "~/.openclaw/workspace"
REMOTE_SCRIPTS = f"{REMOTE_WORKSPACE}/skills/autodidact/scripts"

# ── Timezone (Asia/Taipei) ──
TZ = timezone(timedelta(hours=8))


def _now_iso() -> str:
    """Return current time in ISO format with timezone."""
    return datetime.now(TZ).isoformat(timespec="seconds")


def _make_job_id(exp_id: str, model: str) -> str:
    """Generate a job ID like Q001-whisper-small-20260319-0330."""
    ts = datetime.now(TZ).strftime("%Y%m%d-%H%M")
    return f"{exp_id}-{model}-{ts}"


# ── Queue I/O ──

def _read_queue() -> list[dict]:
    """Read all jobs from queue.jsonl."""
    if not QUEUE_PATH.exists():
        return []
    jobs = []
    for line in QUEUE_PATH.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                jobs.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return jobs


def _write_queue(jobs: list[dict]) -> None:
    """Overwrite queue.jsonl with the given jobs."""
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_PATH, "w") as f:
        for job in jobs:
            f.write(json.dumps(job, ensure_ascii=False) + "\n")


def _append_job(job: dict) -> None:
    """Append a single job to queue.jsonl."""
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_PATH, "a") as f:
        f.write(json.dumps(job, ensure_ascii=False) + "\n")


# ── SSH helpers ──

def _run_ssh(remote_cmd: str, *, dry_run: bool = False, timeout: int = SSH_TIMEOUT) -> str:
    """Run a command on battleship via SSH. Returns stdout on success."""
    full_cmd = SSH_CMD_BASE + [remote_cmd]
    if dry_run:
        print(f"[DRY RUN] {' '.join(full_cmd)}")
        return ""
    try:
        result = subprocess.run(
            full_cmd, capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            raise RuntimeError(f"SSH command failed (rc={result.returncode}): {result.stderr.strip()}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"SSH command timed out after {timeout}s")


def _build_run_command(exp_id: str, model: str) -> str:
    """Build the remote nohup command to run an experiment."""
    script_map = {
        "Q001": "q001_voicing_geometry.py",
        "Q002": "q002_causal_contribution.py",
    }
    script = script_map.get(exp_id, f"{exp_id.lower()}_experiment.py")
    log_file = f"/tmp/{exp_id}_{model}.log"
    result_file = f"/tmp/{exp_id}_{model}_results.json"
    return (
        f"nohup {REMOTE_PYTHON} {REMOTE_SCRIPTS}/{script} "
        f"--model {model} --output {result_file} "
        f"> {log_file} 2>&1 & echo $!"
    )


# ── Core functions ──

def dispatch(exp_id: str, model: str, priority: str = "normal", dry_run: bool = False) -> str:
    """Dispatch an experiment to battleship GPU.

    Returns the job_id string.
    """
    job_id = _make_job_id(exp_id, model)
    remote_cmd = _build_run_command(exp_id, model)

    job = {
        "job_id": job_id,
        "exp_id": exp_id,
        "model": model,
        "priority": priority,
        "status": "queued",
        "submitted_at": _now_iso(),
        "started_at": None,
        "completed_at": None,
        "result_path": None,
        "error": None,
    }

    try:
        output = _run_ssh(remote_cmd, dry_run=dry_run)
        if not dry_run and output:
            job["status"] = "running"
            job["started_at"] = _now_iso()
            job["pid"] = output.strip()
        elif dry_run:
            job["status"] = "dry_run"
    except RuntimeError as e:
        job["status"] = "failed"
        job["error"] = str(e)

    _append_job(job)
    return job_id


def check_status(job_id: str | None = None, dry_run: bool = False) -> list[dict]:
    """Check status of jobs on battleship.

    If job_id is given, check only that job. Otherwise check all non-terminal jobs.
    Returns list of job status dicts.
    """
    jobs = _read_queue()
    if not jobs:
        return []

    targets = jobs if job_id is None else [j for j in jobs if j["job_id"] == job_id]
    updated = False

    for job in targets:
        if job["status"] not in ("running", "queued"):
            continue

        pid = job.get("pid")
        if not pid:
            continue

        try:
            output = _run_ssh(f"kill -0 {pid} 2>/dev/null && echo ALIVE || echo DEAD", dry_run=dry_run)
            if dry_run:
                continue
            if "DEAD" in output:
                # Check if results exist
                result_file = f"/tmp/{job['exp_id']}_{job['model']}_results.json"
                try:
                    _run_ssh(f"test -f {result_file} && echo EXISTS", dry_run=dry_run)
                    job["status"] = "done"
                    job["completed_at"] = _now_iso()
                    job["result_path"] = result_file
                except RuntimeError:
                    job["status"] = "failed"
                    job["error"] = "Process ended without producing results"
                    job["completed_at"] = _now_iso()
                updated = True
        except RuntimeError as e:
            job["status"] = "failed"
            job["error"] = str(e)
            job["completed_at"] = _now_iso()
            updated = True

    if updated:
        _write_queue(jobs)

    return targets


def fetch_results(exp_id: str, model: str, dry_run: bool = False) -> dict | None:
    """Fetch results from battleship for a given experiment.

    Caches to memory/experiments/results/<exp_id>_<model>.json.
    """
    cache_path = RESULTS_DIR / f"{exp_id}_{model}.json"

    # Return cached if available
    if cache_path.exists():
        return json.loads(cache_path.read_text())

    remote_file = f"/tmp/{exp_id}_{model}_results.json"
    try:
        output = _run_ssh(f"cat {remote_file}", dry_run=dry_run)
        if dry_run:
            return None
        if not output:
            return None
        data = json.loads(output)
        # Cache locally
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        return data
    except (RuntimeError, json.JSONDecodeError) as e:
        print(f"Failed to fetch results: {e}", file=sys.stderr)
        return None


# ── CLI commands ──

def cmd_run(args: argparse.Namespace) -> int:
    """Handle 'run' subcommand."""
    print(f"Dispatching {args.exp} with model {args.model} (priority={args.priority})")
    job_id = dispatch(args.exp, args.model, priority=args.priority, dry_run=args.dry_run)
    print(f"Job ID: {job_id}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Handle 'status' subcommand."""
    job_id = getattr(args, "job_id", None)
    jobs = check_status(job_id=job_id, dry_run=args.dry_run)
    if not jobs:
        print("No jobs found.")
        return 0

    if args.json:
        print(json.dumps(jobs, indent=2, ensure_ascii=False))
    else:
        for j in jobs:
            icon = {"queued": "⏳", "running": "🔄", "done": "✅", "failed": "❌", "dry_run": "🔍"}.get(j["status"], "❓")
            print(f"  {icon} {j['job_id']}  status={j['status']}  priority={j['priority']}")
            if j.get("error"):
                print(f"       error: {j['error']}")
    return 0


def cmd_queue(args: argparse.Namespace) -> int:
    """Handle 'queue' subcommand."""
    if args.add:
        job_id = _make_job_id(args.add, args.model)
        job = {
            "job_id": job_id,
            "exp_id": args.add,
            "model": args.model,
            "priority": args.priority,
            "status": "queued",
            "submitted_at": _now_iso(),
            "started_at": None,
            "completed_at": None,
            "result_path": None,
            "error": None,
        }
        _append_job(job)
        print(f"Queued: {job_id}")
        return 0

    # --list (default)
    jobs = _read_queue()
    if not jobs:
        print("Queue is empty.")
        return 0

    # Sort: high priority first, then by submitted_at
    priority_order = {"high": 0, "normal": 1, "low": 2}
    jobs.sort(key=lambda j: (priority_order.get(j.get("priority", "normal"), 1), j.get("submitted_at", "")))

    if args.json:
        print(json.dumps(jobs, indent=2, ensure_ascii=False))
    else:
        print(f"Experiment Queue ({len(jobs)} jobs)")
        print("-" * 60)
        for j in jobs:
            icon = {"queued": "⏳", "running": "🔄", "done": "✅", "failed": "❌", "dry_run": "🔍"}.get(j["status"], "❓")
            print(f"  {icon} {j['job_id']}  [{j['priority']}]  status={j['status']}")
    return 0


def cmd_results(args: argparse.Namespace) -> int:
    """Handle 'results' subcommand."""
    data = fetch_results(args.exp, args.model, dry_run=args.dry_run)
    if data is None:
        print(f"No results found for {args.exp}/{args.model}")
        return 1
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


# ── CLI parser ──

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    p = argparse.ArgumentParser(
        description="Experiment dispatcher for battleship GPU"
    )
    sub = p.add_subparsers(dest="command", required=True)

    # run
    r = sub.add_parser("run", help="Dispatch an experiment to battleship")
    r.add_argument("--exp", required=True, help="Experiment ID (e.g. Q001)")
    r.add_argument("--model", required=True, help="Model name (e.g. whisper-small)")
    r.add_argument("--priority", default="normal", choices=["high", "normal", "low"])
    r.add_argument("--dry-run", action="store_true", help="Print SSH command without executing")

    # status
    s = sub.add_parser("status", help="Check job status on battleship")
    s.add_argument("--job-id", help="Specific job ID to check")
    s.add_argument("--json", action="store_true", help="Output JSON")
    s.add_argument("--dry-run", action="store_true")

    # queue
    q = sub.add_parser("queue", help="Manage the job queue")
    q.add_argument("--list", action="store_true", default=True, help="List queued jobs")
    q.add_argument("--add", help="Add experiment to queue (exp_id)")
    q.add_argument("--model", help="Model for --add")
    q.add_argument("--priority", default="normal", choices=["high", "normal", "low"])
    q.add_argument("--json", action="store_true", help="Output JSON")

    # results
    res = sub.add_parser("results", help="Fetch experiment results")
    res.add_argument("--exp", required=True, help="Experiment ID")
    res.add_argument("--model", required=True, help="Model name")
    res.add_argument("--dry-run", action="store_true")

    return p


def main() -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()
    handlers = {
        "run": cmd_run,
        "status": cmd_status,
        "queue": cmd_queue,
        "results": cmd_results,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
