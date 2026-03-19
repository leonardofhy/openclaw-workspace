#!/usr/bin/env python3
"""Cross-machine task orchestrator — dispatch, sync-state, gpu-queue, handoff.

Integrates coordinator mailbox with experiment_dispatch for real
cross-machine orchestration between Lab, MacBook, and Battleship.

Usage:
    python3 orchestrator.py dispatch --name <name> --script <path> --model <model> [--dry-run]
    python3 orchestrator.py sync-state [--json]
    python3 orchestrator.py gpu-queue [--status <status>] [--json]
    python3 orchestrator.py handoff --to <lab|mac> --title <title> --files <f1> [<f2>...] [--context <text>]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ── Path setup ──
SCRIPT_DIR = Path(__file__).resolve().parent
SKILLS_DIR = SCRIPT_DIR.parent.parent
SHARED_DIR = SKILLS_DIR / "shared"

sys.path.insert(0, str(SHARED_DIR))
from jsonl_store import JsonlStore, find_workspace

sys.path.insert(0, str(SKILLS_DIR / "lib"))
from common import TZ

WORKSPACE = find_workspace()
QUEUE_PATH = WORKSPACE / "memory" / "learning" / "state" / "queue.json"
AUTODIDACT_STATE = WORKSPACE / "memory" / "learning" / "state"
MAILBOX_REL = "memory/mailbox/messages.jsonl"
DISPATCHES_LOG = WORKSPACE / "memory" / "learning" / "dispatches.jsonl"

mailbox_store = JsonlStore(MAILBOX_REL, prefix="MB")

# SSH targets
SSH_LAB = "lab"
SSH_BATTLESHIP = "battleship"
LAB_WORKSPACE = "~/.openclaw/workspace"

BRANCH_MAP = {
    "lab-desktop": "macbook-m3",
    "macbook-m3": "lab-desktop",
}


def now_iso() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%dT%H:%M:%S%z")


def _current_branch() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            text=True, stderr=subprocess.DEVNULL, cwd=WORKSPACE,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _run_ssh(host: str, cmd: str, *, dry_run: bool = False) -> str:
    """Run a command on remote host via SSH."""
    if dry_run:
        print(f"[DRY RUN] ssh {host} '{cmd}'")
        return ""
    result = subprocess.run(
        ["ssh", host, cmd],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"SSH failed ({host}): {result.stderr.strip()}")
    return result.stdout.strip()


def _scp_from(host: str, remote: str, local: str, *, dry_run: bool = False) -> None:
    if dry_run:
        print(f"[DRY RUN] scp {host}:{remote} {local}")
        return
    subprocess.run(
        ["scp", f"{host}:{remote}", local],
        capture_output=True, text=True, check=True, timeout=30,
    )


# ─────────────────────────────────────────────────────────────
# dispatch — send experiment to Battleship via mailbox + SSH
# ─────────────────────────────────────────────────────────────

def cmd_dispatch(args: argparse.Namespace) -> int:
    """Dispatch experiment to Battleship: SCP script + mailbox notify Lab."""
    script_path = Path(args.script).resolve()
    if not script_path.exists():
        print(f"ERROR: script not found: {script_path}", file=sys.stderr)
        return 1

    dry = args.dry_run
    name = args.name
    model = args.model

    print(f"=== Dispatching experiment: {name} ===")
    print(f"  Script: {script_path}")
    print(f"  Model:  {model}")
    print(f"  Target: {SSH_BATTLESHIP}")

    # 1. Use experiment_dispatch for the actual SLURM submission
    dispatch_cmd = [
        sys.executable,
        str(SHARED_DIR / "experiment_dispatch.py"),
        "dispatch",
        "--script", str(script_path),
        "--model", model,
        "--name", name,
    ]
    if args.gpus:
        dispatch_cmd += ["--gpus", str(args.gpus)]
    if args.walltime:
        dispatch_cmd += ["--walltime", args.walltime]
    if dry:
        dispatch_cmd.append("--dry-run")

    print(f"\n→ Delegating to experiment_dispatch...")
    result = subprocess.run(dispatch_cmd, text=True, cwd=WORKSPACE)
    if result.returncode != 0:
        print("ERROR: experiment_dispatch failed", file=sys.stderr)
        return 1

    # 2. Send mailbox notification so Lab knows about the dispatch
    sender = "mac" if "macbook" in _current_branch() else "lab"
    receiver = "lab" if sender == "mac" else "mac"

    msg = mailbox_store.append({
        "from": sender,
        "to": receiver,
        "title": f"GPU dispatch: {name}",
        "body": f"Dispatched experiment '{name}' (model={model}) to {SSH_BATTLESHIP}. Monitor with: experiment_dispatch.py status --all",
        "task_id": "",
        "priority": 1,
        "urgent": False,
        "status": "open",
        "created_at": now_iso(),
        "acked_at": "",
        "done_at": "",
    })
    print(f"\n📬 Mailbox notification sent: {msg['id']}")
    return 0


# ─────────────────────────────────────────────────────────────
# sync-state — pull Lab's autodidact state + merge with Mac's
# ─────────────────────────────────────────────────────────────

def cmd_sync_state(args: argparse.Namespace) -> int:
    """Pull Lab's autodidact state and merge with local state."""
    dry = args.dry_run
    use_json = args.json

    local_queue = _load_queue(QUEUE_PATH)
    remote_queue_path = f"{LAB_WORKSPACE}/memory/learning/state/queue.json"

    # 1. Fetch remote queue
    remote_queue = {}
    if not dry:
        try:
            tmp = Path("/tmp/lab_queue.json")
            _scp_from(SSH_LAB, remote_queue_path, str(tmp))
            remote_queue = json.loads(tmp.read_text())
        except Exception as e:
            print(f"⚠️ Could not fetch Lab state: {e}", file=sys.stderr)
            remote_queue = {}
    else:
        print(f"[DRY RUN] scp {SSH_LAB}:{remote_queue_path} /tmp/lab_queue.json")

    # 2. Fetch remote dispatches log
    remote_dispatches = []
    if not dry:
        try:
            tmp_d = Path("/tmp/lab_dispatches.jsonl")
            _scp_from(SSH_LAB, f"{LAB_WORKSPACE}/memory/learning/dispatches.jsonl", str(tmp_d))
            remote_dispatches = [
                json.loads(line) for line in tmp_d.read_text().strip().splitlines()
                if line.strip()
            ]
        except Exception:
            remote_dispatches = []

    # 3. Merge: report differences
    local_tasks = {t["id"]: t for t in local_queue.get("tasks", [])}
    remote_tasks = {t["id"]: t for t in remote_queue.get("tasks", [])}

    only_local = set(local_tasks) - set(remote_tasks)
    only_remote = set(remote_tasks) - set(local_tasks)
    common = set(local_tasks) & set(remote_tasks)

    status_diffs = []
    for tid in common:
        ls = local_tasks[tid].get("status")
        rs = remote_tasks[tid].get("status")
        if ls != rs:
            status_diffs.append({"id": tid, "local": ls, "remote": rs})

    report = {
        "timestamp": now_iso(),
        "local_tasks": len(local_tasks),
        "remote_tasks": len(remote_tasks),
        "only_local": sorted(only_local),
        "only_remote": sorted(only_remote),
        "status_diffs": status_diffs,
        "remote_dispatches": len(remote_dispatches),
    }

    if use_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"🔄 Sync State — {report['timestamp']}")
        print(f"   Local tasks:  {report['local_tasks']}")
        print(f"   Remote tasks: {report['remote_tasks']}")
        if only_local:
            print(f"   Only on Mac:  {', '.join(sorted(only_local))}")
        if only_remote:
            print(f"   Only on Lab:  {', '.join(sorted(only_remote))}")
        if status_diffs:
            print(f"   Status diffs:")
            for d in status_diffs:
                print(f"     {d['id']}: local={d['local']} remote={d['remote']}")
        if not only_local and not only_remote and not status_diffs:
            print("   ✅ States are in sync")
        print(f"   Remote dispatches: {report['remote_dispatches']}")

    return 0


# ─────────────────────────────────────────────────────────────
# gpu-queue — list pending GPU experiments from queue.json
# ─────────────────────────────────────────────────────────────

def cmd_gpu_queue(args: argparse.Namespace) -> int:
    """List GPU experiments from queue.json, optionally filtered by status."""
    queue = _load_queue(QUEUE_PATH)
    tasks = queue.get("tasks", [])

    # Filter to experiment-type tasks
    experiments = [t for t in tasks if t.get("type") == "experiment"]

    if args.status:
        experiments = [t for t in experiments if t.get("status") == args.status]

    if args.json:
        print(json.dumps(experiments, ensure_ascii=False, indent=2))
    else:
        if not experiments:
            print("No GPU experiments in queue.")
            return 0
        print(f"🖥️ GPU Experiment Queue ({len(experiments)} items)")
        print("-" * 60)
        for t in experiments:
            status = t.get("status", "?")
            blocked = t.get("blocked_by", "")
            icon = {"queued": "⏳", "running": "🔄", "blocked": "🔴", "done": "✅"}.get(status, "❓")
            print(f"  {icon} {t['id']} | {t.get('title', '?')}")
            print(f"       status={status}  priority={t.get('priority', '?')}")
            if blocked:
                print(f"       blocked_by: {blocked}")

    return 0


# ─────────────────────────────────────────────────────────────
# handoff — package files + context for the other machine
# ─────────────────────────────────────────────────────────────

def cmd_handoff(args: argparse.Namespace) -> int:
    """Package a task (files + context) and send via mailbox to the other machine."""
    target = args.to
    title = args.title
    files = args.files or []
    context = args.context or ""
    dry = args.dry_run

    # Validate files exist
    resolved_files = []
    for f in files:
        p = Path(f).resolve()
        if not p.exists():
            print(f"ERROR: file not found: {f}", file=sys.stderr)
            return 1
        resolved_files.append(str(p))

    # Build file manifest
    manifest = []
    for fp in resolved_files:
        p = Path(fp)
        try:
            rel = p.relative_to(WORKSPACE)
        except ValueError:
            rel = p.name
        manifest.append({"path": str(rel), "size": p.stat().st_size})

    sender = "mac" if "macbook" in _current_branch() else "lab"

    body_parts = [f"Handoff: {title}"]
    if context:
        body_parts.append(f"Context: {context}")
    if manifest:
        file_list = ", ".join(m["path"] for m in manifest)
        body_parts.append(f"Files ({len(manifest)}): {file_list}")
    body_parts.append("Please git pull to get the latest files.")

    body = "\n".join(body_parts)

    if dry:
        print(f"[DRY RUN] Handoff to {target}")
        print(f"  Title: {title}")
        print(f"  Files: {manifest}")
        print(f"  Body:\n{body}")
        return 0

    # Send mailbox message
    msg = mailbox_store.append({
        "from": sender,
        "to": target,
        "title": f"Handoff: {title}",
        "body": body,
        "task_id": "",
        "priority": args.priority,
        "urgent": args.urgent,
        "status": "open",
        "created_at": now_iso(),
        "acked_at": "",
        "done_at": "",
        "metadata": {"files": manifest, "context": context},
    })

    print(f"📦 Handoff packaged → {target}")
    print(f"   Mailbox ID: {msg['id']}")
    print(f"   Files: {len(manifest)}")
    print(f"   Title: {title}")
    if context:
        print(f"   Context: {context}")
    print(f"\n⚠️ Remember to git push so {target} can pull the files.")

    return 0


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _load_queue(path: Path) -> dict:
    """Load queue.json, returning empty dict on failure."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Cross-machine task orchestrator (dispatch/sync/gpu-queue/handoff)"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # dispatch
    d = sub.add_parser("dispatch", help="Dispatch experiment to Battleship via mailbox + SSH")
    d.add_argument("--name", required=True, help="Experiment name")
    d.add_argument("--script", required=True, help="Path to experiment script")
    d.add_argument("--model", required=True, help="Model name (e.g. whisper-base)")
    d.add_argument("--gpus", type=int, default=None, help="Number of GPUs")
    d.add_argument("--walltime", default=None, help="Walltime (e.g. 04:00:00)")
    d.add_argument("--dry-run", action="store_true", default=True, help="Preview only (default: True)")
    d.add_argument("--execute", action="store_true", help="Actually execute (overrides --dry-run)")

    # sync-state
    s = sub.add_parser("sync-state", help="Pull Lab state and merge with Mac state")
    s.add_argument("--json", action="store_true", help="Output JSON")
    s.add_argument("--dry-run", action="store_true", default=True, help="Preview only (default: True)")
    s.add_argument("--execute", action="store_true", help="Actually execute (overrides --dry-run)")

    # gpu-queue
    g = sub.add_parser("gpu-queue", help="List pending GPU experiments from queue.json")
    g.add_argument("--status", help="Filter by status (e.g. blocked, queued, running)")
    g.add_argument("--json", action="store_true", help="Output JSON")

    # handoff
    h = sub.add_parser("handoff", help="Package files + context for the other machine")
    h.add_argument("--to", required=True, choices=["lab", "mac"], help="Target machine")
    h.add_argument("--title", required=True, help="Handoff title")
    h.add_argument("--files", nargs="*", help="Files to include in handoff")
    h.add_argument("--context", help="Additional context text")
    h.add_argument("--priority", type=int, choices=[1, 2, 3], default=2)
    h.add_argument("--urgent", action="store_true")
    h.add_argument("--dry-run", action="store_true", default=True, help="Preview only (default: True)")
    h.add_argument("--execute", action="store_true", help="Actually execute (overrides --dry-run)")

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # Override dry-run if --execute is specified
    if hasattr(args, 'execute') and args.execute:
        args.dry_run = False

    handlers = {
        "dispatch": cmd_dispatch,
        "sync-state": cmd_sync_state,
        "gpu-queue": cmd_gpu_queue,
        "handoff": cmd_handoff,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
