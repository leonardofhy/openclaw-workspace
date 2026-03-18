#!/usr/bin/env python3
"""Task Board staleness checker — run during heartbeat.

Usage:
    python3 task-check.py                 # human-readable output (auto owner)
    python3 task-check.py --json          # structured JSON output
    python3 task-check.py --owner mac     # force owner scope: mac|lab|all
"""

import argparse
import json as json_mod
import os
import platform
import re
import socket
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "shared"))
from jsonl_store import find_workspace

BOARD = find_workspace() / "memory" / "task-board.md"
ACTIVE_STALE_DAYS = 3
WAITING_STALE_DAYS = 7
MAX_ACTIVE = 5
VALID_OWNERS = {"mac", "lab", "all"}


def detect_owner() -> str:
    """Auto-detect local owner scope."""
    env_owner = (os.getenv("TASK_CHECK_OWNER") or os.getenv("TASK_OWNER") or "").strip().lower()
    if env_owner in VALID_OWNERS:
        return env_owner

    if platform.system().lower() == "darwin":
        return "mac"

    host = socket.gethostname().lower()
    if "mac" in host or "darwin" in host:
        return "mac"
    return "lab"


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
        elif line.startswith("## BLOCKED"):
            section = "BLOCKED"
        elif line.startswith("## PARKED"):
            section = "PARKED"
        elif line.startswith("## DONE"):
            section = "DONE"
        elif line.startswith("## ") or line.startswith("---"):
            section = None

        m = re.match(r"^### ([A-Z]-\d+\w?)\s*\|\s*(.+)", line)
        if m and section:
            if current:
                tasks.append(current)
            tid = m.group(1)
            owner = "lab" if tid.startswith("L-") else "mac" if tid.startswith("M-") else "unknown"
            current = {
                "id": tid,
                "title": m.group(2).strip(),
                "status": section,
                "owner": owner,
                "last_touched": None,
                "priority": None,
                "deadline": None,
            }
            continue

        if current and line.startswith("- **"):
            fm = re.match(r"- \*\*(\w+)\*\*:\s*(.+)", line)
            if not fm:
                fm = re.match(r"- \*\*(\w[\w_]*)\*\*:\s*(.+)", line)
            if fm:
                key = fm.group(1).lower().replace("優先級", "priority")
                val = fm.group(2).strip()
                if key == "last_touched":
                    try:
                        current["last_touched"] = datetime.strptime(val, "%Y-%m-%d").date()
                    except ValueError:
                        pass
                elif key == "deadline":
                    try:
                        current["deadline"] = datetime.strptime(val, "%Y-%m-%d").date()
                    except ValueError:
                        pass
                elif key == "priority":
                    current["priority"] = val

    if current:
        tasks.append(current)

    return tasks


def check(tasks: list[dict], today: date | None = None, owner_scope: str = "all") -> list[str]:
    """Return list of alert strings (scoped by owner)."""
    today = today or datetime.now().date()
    alerts = []

    scoped_tasks = [t for t in tasks if in_scope(t, owner_scope)]

    if owner_scope == "all":
        from collections import Counter
        active_by_owner = Counter(t["owner"] for t in tasks if t["status"] == "ACTIVE")
        for owner, count in active_by_owner.items():
            if count > MAX_ACTIVE:
                alerts.append(f"⚠️ {owner} ACTIVE 任務超過上限：{count}/{MAX_ACTIVE}，需要 PARK 或完成一些")
    else:
        active_count = sum(1 for t in scoped_tasks if t["status"] == "ACTIVE")
        if active_count > MAX_ACTIVE:
            alerts.append(f"⚠️ {owner_scope} ACTIVE 任務超過上限：{active_count}/{MAX_ACTIVE}，需要 PARK 或完成一些")

    for t in scoped_tasks:
        if t["status"] == "DONE":
            continue

        if t["last_touched"]:
            days = (today - t["last_touched"]).days
            if t["status"] == "ACTIVE" and days >= ACTIVE_STALE_DAYS:
                alerts.append(f"🔴 STALE: {t['id']} {t['title']} — {days} 天沒更新")
            elif t["status"] == "WAITING" and days >= WAITING_STALE_DAYS:
                alerts.append(f"🟡 STALE: {t['id']} {t['title']} — {days} 天沒更新")

        if t["deadline"]:
            days_left = (t["deadline"] - today).days
            if days_left < 0:
                alerts.append(f"🔴 OVERDUE: {t['id']} {t['title']} — 逾期 {-days_left} 天")
            elif days_left <= 1:
                alerts.append(f"⚠️ DEADLINE: {t['id']} {t['title']} — 剩 {days_left} 天")

    return alerts


def main() -> None:
    parser = argparse.ArgumentParser(description="Task board checker")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--owner", default="auto", choices=["auto", "mac", "lab", "all"],
                        help="Owner scope for alerts")
    args = parser.parse_args()

    owner_scope = detect_owner() if args.owner == "auto" else args.owner

    if not BOARD.exists():
        if args.json:
            print(json_mod.dumps({"error": "task-board.md not found"}))
        else:
            print("❌ task-board.md not found", file=sys.stderr)
        sys.exit(1)

    text = BOARD.read_text()
    tasks = parse_tasks(text)
    today = datetime.now().date()

    scoped_tasks = [t for t in tasks if in_scope(t, owner_scope)]

    active = [t for t in scoped_tasks if t["status"] == "ACTIVE"]
    waiting = [t for t in scoped_tasks if t["status"] == "WAITING"]
    blocked = [t for t in scoped_tasks if t["status"] == "BLOCKED"]
    done = [t for t in scoped_tasks if t["status"] == "DONE"]

    alerts = check(tasks, today, owner_scope=owner_scope)

    if args.json:
        print(json_mod.dumps({
            "date": str(today),
            "owner_scope": owner_scope,
            "counts": {
                "active": len(active),
                "waiting": len(waiting),
                "blocked": len(blocked),
                "done": len(done),
            },
            "alerts": alerts,
            "tasks": [
                {k: (str(v) if v is not None else None)
                 for k, v in t.items()}
                for t in scoped_tasks if t["status"] != "DONE"
            ],
        }, ensure_ascii=False, indent=2))
    else:
        print(f"📋 Task Board ({owner_scope}): {len(active)} active, {len(waiting)} waiting, {len(blocked)} blocked")
        if len(done) > 10:
            print(f"⚠️ DONE 區有 {len(done)} 個任務，建議歸檔到 task-archive.md")
        if alerts:
            print("\n".join(alerts))
        else:
            print("✅ 所有任務健康，無 stale/overdue")

    sys.exit(1 if alerts else 0)


if __name__ == "__main__":
    main()
