#!/usr/bin/env python3
"""Task Board staleness checker — run during heartbeat.

Usage:
    python3 task-check.py                 # human-readable output (auto owner)
    python3 task-check.py --json          # structured JSON output
    python3 task-check.py --owner bot-a   # force owner scope: bot-a|bot-b|all
"""

import argparse
import json as json_mod
import os
import platform
import re
import socket
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "shared"))
from jsonl_store import find_workspace

BOARD = find_workspace() / "memory" / "task-board.md"
ACTIVE_STALE_DAYS = 3
WAITING_STALE_DAYS = 7
MAX_ACTIVE = 5
VALID_OWNERS = {"bot-a", "bot-b", "all"}


def detect_owner() -> str:
    """Auto-detect local owner scope. Customize this for your setup."""
    env_owner = (os.getenv("TASK_CHECK_OWNER") or os.getenv("TASK_OWNER") or "").strip().lower()
    if env_owner in VALID_OWNERS:
        return env_owner

    if platform.system().lower() == "darwin":
        return "bot-a"  # Laptop bot

    return "bot-b"  # Server bot


def in_scope(task: dict, owner_scope: str) -> bool:
    if owner_scope == "all":
        return True
    return task.get("owner") == owner_scope


def parse_tasks(text: str) -> list[dict]:
    """Parse task entries from task-board.md."""
    tasks = []
    current = None
    section = None

    for line in text.splitlines():
        if line.startswith("## ACTIVE"):
            section = "ACTIVE"
        elif line.startswith("## WAITING"):
            section = "WAITING"
        elif line.startswith("## DONE") or line.startswith("## ARCHIVE"):
            section = "DONE"
        elif line.startswith("### ") and section in ("ACTIVE", "WAITING"):
            # Parse task header: ### A-01 | Task Title
            m = re.match(r"### ([A-Z]-\d+)\s*\|\s*(.*)", line)
            if m:
                current = {
                    "id": m.group(1),
                    "title": m.group(2).strip(),
                    "section": section,
                    "owner": "bot-a" if m.group(1).startswith("A-") else "bot-b",
                    "last_touched": None,
                }
                tasks.append(current)
        elif current and line.strip().startswith("last_touched:"):
            date_str = line.strip().split(":", 1)[1].strip()
            try:
                current["last_touched"] = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                pass

    return tasks


def check_staleness(tasks: list[dict], owner_scope: str) -> list[dict]:
    """Check for stale tasks."""
    alerts = []
    now = datetime.now()
    active_count = 0

    for t in tasks:
        if not in_scope(t, owner_scope):
            continue

        if t["section"] == "ACTIVE":
            active_count += 1
            if t["last_touched"]:
                age = (now - t["last_touched"]).days
                if age >= ACTIVE_STALE_DAYS:
                    alerts.append({
                        "type": "stale_active",
                        "task": t["id"],
                        "title": t["title"],
                        "days_stale": age,
                    })

        elif t["section"] == "WAITING":
            if t["last_touched"]:
                age = (now - t["last_touched"]).days
                if age >= WAITING_STALE_DAYS:
                    alerts.append({
                        "type": "stale_waiting",
                        "task": t["id"],
                        "title": t["title"],
                        "days_stale": age,
                    })

    if active_count > MAX_ACTIVE:
        alerts.append({
            "type": "too_many_active",
            "count": active_count,
            "max": MAX_ACTIVE,
        })

    return alerts


def main():
    parser = argparse.ArgumentParser(description="Task board staleness checker")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--owner", choices=list(VALID_OWNERS), default=None)
    args = parser.parse_args()

    owner = args.owner or detect_owner()

    if not BOARD.exists():
        if args.json:
            print(json_mod.dumps({"status": "no_board", "alerts": []}))
        else:
            print("ℹ️  No task-board.md found. Create one to track tasks.")
        return

    text = BOARD.read_text(encoding="utf-8")
    tasks = parse_tasks(text)
    alerts = check_staleness(tasks, owner)

    if args.json:
        print(json_mod.dumps({"status": "ok" if not alerts else "alerts", "alerts": alerts}, indent=2))
        return

    if not alerts:
        print(f"✅ Task board OK (owner: {owner})")
        return

    print(f"⚠️  Task Board Alerts (owner: {owner}):\n")
    for a in alerts:
        if a["type"] == "stale_active":
            print(f"  🔴 STALE ACTIVE: {a['task']} | {a['title']} ({a['days_stale']}d without update)")
        elif a["type"] == "stale_waiting":
            print(f"  ⚠️  STALE WAITING: {a['task']} | {a['title']} ({a['days_stale']}d)")
        elif a["type"] == "too_many_active":
            print(f"  ⚠️  TOO MANY ACTIVE: {a['count']} (max {a['max']})")


if __name__ == "__main__":
    main()
