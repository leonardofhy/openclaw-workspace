#!/usr/bin/env python3
"""Agent Manager — sub-agent lifecycle management with registry, dashboard, and cleanup.

CLI:
    agent_mgr.py spawn --name "Paper §3 Polish" --task "..." [--model sonnet] [--timeout 300]
    agent_mgr.py status [--all] [--name "Paper*"]
    agent_mgr.py history [--today] [--name "Feed*"] [--limit N]
    agent_mgr.py cleanup [--all] [--older-than 60m]
    agent_mgr.py kill --name "Paper*" | --id <spawn-id>
"""

import argparse
import fcntl
import fnmatch
import json
import os
import random
import re
import signal
import string
import subprocess
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
REGISTRY_DIR = REPO_ROOT / "memory" / "agents"
REGISTRY_FILE = REGISTRY_DIR / "registry.jsonl"

MODEL_ALIASES = {
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-6",
    "haiku": "claude-haiku-4-5-20251001",
}


# ── Registry I/O ────────────────────────────────────────

def _ensure_registry():
    """Create registry dir and file if missing."""
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    if not REGISTRY_FILE.exists():
        REGISTRY_FILE.touch()


def _append_entry(entry: dict) -> None:
    """Atomically append a JSONL entry with file locking."""
    _ensure_registry()
    with open(REGISTRY_FILE, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write(json.dumps(entry, default=str) + "\n")
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _read_entries() -> list[dict]:
    """Read all registry entries."""
    _ensure_registry()
    entries = []
    with open(REGISTRY_FILE) as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        try:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
    return entries


def _rewrite_entries(entries: list[dict]) -> None:
    """Atomically rewrite the registry via temp file + rename."""
    _ensure_registry()
    fd, tmp_path = tempfile.mkstemp(dir=REGISTRY_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry, default=str) + "\n")
        os.replace(tmp_path, REGISTRY_FILE)
    except BaseException:
        os.unlink(tmp_path)
        raise


# ── ID Generation ───────────────────────────────────────

def _slugify(name: str) -> str:
    """Convert name to URL-safe slug."""
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug[:30] if slug else "agent"


def generate_id(name: str) -> str:
    """Generate unique ID: spawn-YYYYMMDD-HHMMSS-slug-rand4."""
    now = datetime.now()
    ts = now.strftime("%Y%m%d-%H%M%S")
    slug = _slugify(name)
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"spawn-{ts}-{slug}-{rand}"


# ── Process Checking ────────────────────────────────────

def _is_pid_alive(pid: int) -> bool:
    """Check if a process is still running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


# ── Core Functions ──────────────────────────────────────

def spawn(name: str, task: str, model: str = "sonnet",
          timeout: int | None = None, workdir: str | None = None) -> dict:
    """Spawn a Claude Code agent and register it."""
    resolved_model = MODEL_ALIASES.get(model, model)
    spawn_id = generate_id(name)
    work_path = workdir or str(REPO_ROOT)

    cmd = [
        "claude",
        "--model", resolved_model,
        "--permission-mode", "bypassPermissions",
        "--print",
        task,
    ]

    if timeout:
        # Wrap with system timeout to enforce time limit
        cmd = ["timeout", str(timeout)] + cmd

    log_dir = REGISTRY_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{spawn_id}.log"

    with open(log_path, "w") as log_file:
        proc = subprocess.Popen(
            cmd,
            cwd=work_path,
            stdout=log_file,
            stderr=log_file,
        )

    now = datetime.now(timezone.utc).isoformat()
    entry = {
        "id": spawn_id,
        "name": name,
        "task_summary": task[:200],
        "model": resolved_model,
        "status": "running",
        "spawned_at": now,
        "completed_at": None,
        "duration_s": None,
        "exit_code": None,
        "pid": proc.pid,
        "workdir": work_path,
        "log": str(log_path),
        "artifacts": [],
        "error": None,
    }

    _append_entry(entry)
    return entry


def update_status() -> list[dict]:
    """Check running agents' process status, update registry, return current state."""
    entries = _read_entries()
    changed = False

    for entry in entries:
        if entry["status"] != "running":
            continue

        pid = entry.get("pid")
        if pid is None:
            continue

        if not _is_pid_alive(pid):
            # Process finished — try to get exit code
            try:
                _, status = os.waitpid(pid, os.WNOHANG)
                exit_code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -1
            except ChildProcessError:
                # Not our child (spawned by prior invocation) — unknown exit code
                exit_code = None

            now = datetime.now(timezone.utc).isoformat()
            spawned = datetime.fromisoformat(entry["spawned_at"])
            duration = (datetime.now(timezone.utc) - spawned).total_seconds()

            if exit_code is None:
                entry["status"] = "completed"
            elif exit_code == 0:
                entry["status"] = "completed"
            else:
                entry["status"] = "failed"
                entry["error"] = f"Process exited with code {exit_code}"
            entry["completed_at"] = now
            entry["duration_s"] = round(duration, 1)
            entry["exit_code"] = exit_code
            changed = True

    if changed:
        _rewrite_entries(entries)

    return entries


def get_dashboard(filter_name: str | None = None,
                  include_completed: bool = False) -> str:
    """Pretty-print agent status table (code-block safe for Discord)."""
    entries = update_status()

    if filter_name:
        entries = [e for e in entries if fnmatch.fnmatch(e["name"], filter_name)]

    if not include_completed:
        entries = [e for e in entries if e["status"] == "running"]

    if not entries:
        return "No agents found."

    # Calculate column widths
    headers = ["Name", "Model", "Status", "Duration", "ID"]
    rows = []
    for e in entries:
        model_short = e["model"].split("-")[1] if "-" in e["model"] else e["model"]
        if e["duration_s"] is not None:
            mins, secs = divmod(int(e["duration_s"]), 60)
            duration = f"{mins}m{secs:02d}s"
        elif e["status"] == "running" and e.get("spawned_at"):
            spawned = datetime.fromisoformat(e["spawned_at"])
            elapsed = (datetime.now(timezone.utc) - spawned).total_seconds()
            mins, secs = divmod(int(elapsed), 60)
            duration = f"{mins}m{secs:02d}s*"
        else:
            duration = "-"

        status = e["status"].upper()
        rows.append([
            e["name"][:25],
            model_short[:8],
            status[:10],
            duration,
            e["id"][:30],
        ])

    # Compute widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    # Build table with box drawing
    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    header_line = "|" + "|".join(f" {h:<{widths[i]}} " for i, h in enumerate(headers)) + "|"

    lines = [sep, header_line, sep]
    for row in rows:
        line = "|" + "|".join(f" {cell:<{widths[i]}} " for i, cell in enumerate(row)) + "|"
        lines.append(line)
    lines.append(sep)
    lines.append(f"Total: {len(rows)} agent(s)")

    return "\n".join(lines)


def cleanup(older_than_minutes: int = 60, cleanup_all: bool = False) -> int:
    """Remove completed/failed entries older than threshold. Returns count removed."""
    entries = update_status()
    now = datetime.now(timezone.utc)
    threshold = timedelta(minutes=older_than_minutes)

    kept = []
    removed = 0
    for entry in entries:
        if entry["status"] in ("completed", "failed"):
            completed_at = entry.get("completed_at")
            if cleanup_all or (completed_at and
                               (now - datetime.fromisoformat(completed_at)) > threshold):
                removed += 1
                continue
        kept.append(entry)

    if removed > 0:
        _rewrite_entries(kept)

    return removed


def get_history(days: int = 7, name_filter: str | None = None,
                today_only: bool = False, limit: int = 20) -> list[dict]:
    """Return historical runs, newest first."""
    entries = _read_entries()
    now = datetime.now(timezone.utc)

    if today_only:
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        entries = [e for e in entries
                   if datetime.fromisoformat(e["spawned_at"]) >= today_start]
    else:
        cutoff = now - timedelta(days=days)
        entries = [e for e in entries
                   if datetime.fromisoformat(e["spawned_at"]) >= cutoff]

    if name_filter:
        entries = [e for e in entries if fnmatch.fnmatch(e["name"], name_filter)]

    entries.sort(key=lambda e: e["spawned_at"], reverse=True)
    return entries[:limit]


def kill_agents(name_pattern: str | None = None,
                agent_id: str | None = None) -> list[str]:
    """Kill agents by name pattern or ID. Returns list of killed IDs."""
    entries = update_status()
    killed = []
    changed = False

    for entry in entries:
        if entry["status"] != "running":
            continue

        match = False
        if agent_id and entry["id"] == agent_id:
            match = True
        elif name_pattern and fnmatch.fnmatch(entry["name"], name_pattern):
            match = True

        if match and entry.get("pid"):
            now = datetime.now(timezone.utc).isoformat()
            try:
                os.kill(entry["pid"], signal.SIGTERM)
                entry["status"] = "killed"
            except ProcessLookupError:
                entry["status"] = "completed"
            entry["completed_at"] = now
            if entry.get("spawned_at"):
                spawned = datetime.fromisoformat(entry["spawned_at"])
                entry["duration_s"] = round(
                    (datetime.now(timezone.utc) - spawned).total_seconds(), 1)
            killed.append(entry["id"])
            changed = True

    if changed:
        _rewrite_entries(entries)

    return killed


# ── CLI ─────────────────────────────────────────────────

def _parse_duration(s: str) -> int:
    """Parse duration string like '30m', '2h', '90s' to minutes."""
    s = s.strip().lower()
    if s.endswith("h"):
        return int(s[:-1]) * 60
    elif s.endswith("m"):
        return int(s[:-1])
    elif s.endswith("s"):
        return max(1, int(s[:-1]) // 60)
    return int(s)


def cmd_spawn(args: argparse.Namespace) -> dict:
    entry = spawn(
        name=args.name,
        task=args.task,
        model=args.model,
        timeout=args.timeout,
        workdir=args.workdir,
    )
    if args.json:
        print(json.dumps(entry, default=str))
    else:
        print(f"Spawned: {entry['id']}")
        print(f"  Name:  {entry['name']}")
        print(f"  Model: {entry['model']}")
        print(f"  PID:   {entry['pid']}")
    return entry


def cmd_status(args: argparse.Namespace) -> None:
    if args.json:
        entries = update_status()
        if args.name:
            entries = [e for e in entries if fnmatch.fnmatch(e["name"], args.name)]
        if not args.all:
            entries = [e for e in entries if e["status"] == "running"]
        print(json.dumps(entries, default=str))
    else:
        dashboard = get_dashboard(
            filter_name=args.name,
            include_completed=args.all,
        )
        print(dashboard)


def cmd_history(args: argparse.Namespace) -> None:
    entries = get_history(
        name_filter=args.name,
        today_only=args.today,
        limit=args.limit,
    )
    if args.json:
        print(json.dumps(entries, default=str))
        return

    if not entries:
        print("No history found.")
        return

    for e in entries:
        status = e["status"].upper()
        duration = f"{e['duration_s']}s" if e.get("duration_s") else "-"
        spawned = e["spawned_at"][:19].replace("T", " ")
        model_short = e["model"].split("-")[1] if "-" in e["model"] else e["model"]
        error = f" | err: {e['error'][:40]}" if e.get("error") else ""
        print(f"  {spawned}  {e['name'][:25]:<25}  {model_short:<8}  {status:<10}  {duration}{error}")


def cmd_cleanup(args: argparse.Namespace) -> None:
    if args.older_than:
        minutes = _parse_duration(args.older_than)
    else:
        minutes = 60

    removed = cleanup(older_than_minutes=minutes, cleanup_all=args.all)
    if args.json:
        print(json.dumps({"removed": removed}))
    else:
        print(f"Cleaned up {removed} agent(s).")


def cmd_kill(args: argparse.Namespace) -> None:
    if not args.name and not args.id:
        print("Error: specify --name or --id")
        sys.exit(1)

    killed = kill_agents(name_pattern=args.name, agent_id=args.id)
    if args.json:
        print(json.dumps({"killed": killed}))
    elif killed:
        print(f"Killed {len(killed)} agent(s):")
        for k in killed:
            print(f"  - {k}")
    else:
        print("No matching running agents found.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agent Manager — sub-agent lifecycle management")
    sub = parser.add_subparsers(dest="command", required=True)

    # spawn
    p = sub.add_parser("spawn", help="Spawn a new agent")
    p.add_argument("--name", required=True, help="Human-readable agent name")
    p.add_argument("--task", required=True, help="Task prompt for the agent")
    p.add_argument("--model", default="sonnet", help="Model alias or full ID")
    p.add_argument("--timeout", type=int, default=None, help="Timeout in seconds")
    p.add_argument("--workdir", default=None, help="Working directory")

    # status
    p = sub.add_parser("status", help="Show agent dashboard")
    p.add_argument("--all", action="store_true", help="Include completed/failed")
    p.add_argument("--name", default=None, help="Filter by name glob pattern")

    # history
    p = sub.add_parser("history", help="Show historical runs")
    p.add_argument("--today", action="store_true", help="Today's runs only")
    p.add_argument("--name", default=None, help="Filter by name glob")
    p.add_argument("--limit", type=int, default=20, help="Max entries")

    # cleanup
    p = sub.add_parser("cleanup", help="Remove old completed entries")
    p.add_argument("--all", action="store_true", help="Remove all non-running")
    p.add_argument("--older-than", default=None, help="Threshold (e.g., 30m, 2h)")

    # kill
    p = sub.add_parser("kill", help="Kill running agents")
    p.add_argument("--name", default=None, help="Kill by name glob pattern")
    p.add_argument("--id", default=None, help="Kill by spawn ID")

    # --json output
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")

    args = parser.parse_args()

    commands = {
        "spawn": cmd_spawn,
        "status": cmd_status,
        "history": cmd_history,
        "cleanup": cmd_cleanup,
        "kill": cmd_kill,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
