#!/usr/bin/env python3
"""Task Board staleness checker — run during heartbeat.

Usage:
    python3 task-check.py          # human-readable output
    python3 task-check.py --json   # structured JSON output
"""

import json as json_mod
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

BOARD = Path(__file__).resolve().parent.parent / "memory" / "task-board.md"
ACTIVE_STALE_DAYS = 3
WAITING_STALE_DAYS = 7
MAX_ACTIVE = 5

def parse_tasks(text: str) -> list[dict]:
    """Parse task entries from task-board.md."""
    tasks = []
    current = None
    section = None

    for line in text.splitlines():
        # Detect section headers
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

        # Parse task header
        m = re.match(r"^### (T-\d+)\s*\|\s*(.+)", line)
        if m and section:
            if current:
                tasks.append(current)
            current = {
                "id": m.group(1),
                "title": m.group(2).strip(),
                "status": section,
                "last_touched": None,
                "priority": None,
                "deadline": None,
            }
            continue

        if current and line.startswith("- **"):
            # Parse fields
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


def check(tasks: list[dict], today=None) -> list[str]:
    """Return list of alert strings."""
    today = today or datetime.now().date()
    alerts = []
    active_count = sum(1 for t in tasks if t["status"] == "ACTIVE")

    if active_count > MAX_ACTIVE:
        alerts.append(f"⚠️ ACTIVE 任務超過上限：{active_count}/{MAX_ACTIVE}，需要 PARK 或完成一些")

    for t in tasks:
        if t["status"] == "DONE":
            continue

        # Staleness
        if t["last_touched"]:
            days = (today - t["last_touched"]).days
            if t["status"] == "ACTIVE" and days >= ACTIVE_STALE_DAYS:
                alerts.append(f"🔴 STALE: {t['id']} {t['title']} — {days} 天沒更新")
            elif t["status"] == "WAITING" and days >= WAITING_STALE_DAYS:
                alerts.append(f"🟡 STALE: {t['id']} {t['title']} — {days} 天沒更新")

        # Deadline
        if t["deadline"]:
            days_left = (t["deadline"] - today).days
            if days_left < 0:
                alerts.append(f"🔴 OVERDUE: {t['id']} {t['title']} — 逾期 {-days_left} 天")
            elif days_left <= 1:
                alerts.append(f"⚠️ DEADLINE: {t['id']} {t['title']} — 剩 {days_left} 天")

    return alerts


def main():
    use_json = "--json" in sys.argv

    if not BOARD.exists():
        if use_json:
            print(json_mod.dumps({"error": "task-board.md not found"}))
        else:
            print("❌ task-board.md not found", file=sys.stderr)
        sys.exit(1)

    text = BOARD.read_text()
    tasks = parse_tasks(text)
    today = datetime.now().date()

    active = [t for t in tasks if t["status"] == "ACTIVE"]
    waiting = [t for t in tasks if t["status"] == "WAITING"]
    blocked = [t for t in tasks if t["status"] == "BLOCKED"]
    done = [t for t in tasks if t["status"] == "DONE"]

    alerts = check(tasks, today)

    if use_json:
        print(json_mod.dumps({
            "date": str(today),
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
                for t in tasks if t["status"] != "DONE"
            ],
        }, ensure_ascii=False, indent=2))
    else:
        print(f"📋 Task Board: {len(active)} active, {len(waiting)} waiting, {len(blocked)} blocked")
        if len(done) > 10:
            print(f"⚠️ DONE 區有 {len(done)} 個任務，建議歸檔到 task-archive.md")
        if alerts:
            print("\n".join(alerts))
        else:
            print("✅ 所有任務健康，無 stale/overdue")

    sys.exit(1 if alerts else 0)


if __name__ == "__main__":
    main()
