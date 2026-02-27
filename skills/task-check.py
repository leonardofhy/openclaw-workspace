#!/usr/bin/env python3
"""Task Board staleness checker — run during heartbeat."""

import re
from datetime import datetime, timedelta
from pathlib import Path

BOARD = Path(__file__).resolve().parent.parent / "memory" / "task-board.md"
TODAY = datetime.now().date()
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


def check(tasks: list[dict]) -> list[str]:
    """Return list of alert strings."""
    alerts = []
    active_count = sum(1 for t in tasks if t["status"] == "ACTIVE")

    if active_count > MAX_ACTIVE:
        alerts.append(f"⚠️ ACTIVE 任務超過上限：{active_count}/{MAX_ACTIVE}，需要 PARK 或完成一些")

    for t in tasks:
        if t["status"] == "DONE":
            continue

        # Staleness
        if t["last_touched"]:
            days = (TODAY - t["last_touched"]).days
            if t["status"] == "ACTIVE" and days >= ACTIVE_STALE_DAYS:
                alerts.append(f"🔴 STALE: {t['id']} {t['title']} — {days} 天沒更新")
            elif t["status"] == "WAITING" and days >= WAITING_STALE_DAYS:
                alerts.append(f"🟡 STALE: {t['id']} {t['title']} — {days} 天沒更新")

        # Deadline
        if t["deadline"]:
            days_left = (t["deadline"] - TODAY).days
            if days_left < 0:
                alerts.append(f"🔴 OVERDUE: {t['id']} {t['title']} — 逾期 {-days_left} 天")
            elif days_left <= 1:
                alerts.append(f"⚠️ DEADLINE: {t['id']} {t['title']} — 剩 {days_left} 天")

    return alerts


def main():
    if not BOARD.exists():
        print("❌ task-board.md not found")
        return

    text = BOARD.read_text()
    tasks = parse_tasks(text)

    active = [t for t in tasks if t["status"] == "ACTIVE"]
    waiting = [t for t in tasks if t["status"] == "WAITING"]
    blocked = [t for t in tasks if t["status"] == "BLOCKED"]

    print(f"📋 Task Board: {len(active)} active, {len(waiting)} waiting, {len(blocked)} blocked")

    alerts = check(tasks)
    if alerts:
        print("\n".join(alerts))
    else:
        print("✅ 所有任務健康，無 stale/overdue")


if __name__ == "__main__":
    main()
