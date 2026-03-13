#!/usr/bin/env python3
"""Deadline watchdog — checks upcoming deadlines and alerts.

Usage:
    python3 deadline_watch.py                # human-readable, warn within 7 days
    python3 deadline_watch.py --days 14      # warn within 14 days
    python3 deadline_watch.py --json         # structured JSON output
    python3 deadline_watch.py --all          # show all deadlines regardless of proximity
"""

import argparse
import json
import sys
from datetime import datetime, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "shared"))
from jsonl_store import find_workspace

DEADLINES_FILE = find_workspace() / "memory" / "finance" / "deadlines.json"


def load_deadlines() -> list[dict]:
    """Load deadlines from JSON file."""
    if not DEADLINES_FILE.exists():
        print(f"❌ {DEADLINES_FILE} not found", file=sys.stderr)
        sys.exit(1)
    with open(DEADLINES_FILE) as f:
        return json.load(f)


def check_deadlines(deadlines: list[dict], today: date | None = None,
                    warn_days: int = 7, show_all: bool = False) -> dict:
    """Check deadlines and return categorized results.

    Returns:
        dict with keys: overdue, urgent (<=warn_days), upcoming, passed_alerts
    """
    today = today or date.today()
    overdue: list[dict] = []
    urgent: list[dict] = []
    upcoming: list[dict] = []

    for d in deadlines:
        # Skip closed/done deadlines
        if d.get("status") in ("closed", "done", "cancelled"):
            continue
        dl = datetime.strptime(d["deadline"], "%Y-%m-%d").date()
        days_left = (dl - today).days
        entry = {**d, "days_left": days_left, "deadline_date": dl}

        if days_left < 0:
            overdue.append(entry)
        elif days_left <= max(d.get("warn_days", 0), warn_days):
            urgent.append(entry)
        elif show_all:
            upcoming.append(entry)

    # Sort by deadline (nearest first)
    overdue.sort(key=lambda x: x["days_left"])
    urgent.sort(key=lambda x: x["days_left"])
    upcoming.sort(key=lambda x: x["days_left"])

    return {"overdue": overdue, "urgent": urgent, "upcoming": upcoming}


def format_alerts(results: dict) -> list[str]:
    """Format results into alert strings."""
    alerts = []

    for d in results["overdue"]:
        alerts.append(
            f"🔴 OVERDUE: {d['id']} {d['name']} — 逾期 {-d['days_left']} 天 | "
            f"Action: {d['action']}"
        )

    for d in results["urgent"]:
        alerts.append(
            f"⚠️ UPCOMING: {d['id']} {d['name']} — 剩 {d['days_left']} 天 "
            f"({d['deadline']}) | Action: {d['action']}"
        )

    return alerts


def main():
    parser = argparse.ArgumentParser(description="Deadline watchdog")
    parser.add_argument("--days", type=int, default=7,
                        help="Warn for deadlines within N days (default: 7)")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON")
    parser.add_argument("--all", action="store_true",
                        help="Show all deadlines")
    args = parser.parse_args()

    deadlines = load_deadlines()
    today = date.today()
    results = check_deadlines(deadlines, today, warn_days=args.days,
                              show_all=args.all)

    if args.json:
        out = {
            "date": str(today),
            "warn_days": args.days,
            "overdue": [{k: (str(v) if isinstance(v, date) else v)
                         for k, v in d.items() if k != "deadline_date"}
                        for d in results["overdue"]],
            "urgent": [{k: (str(v) if isinstance(v, date) else v)
                        for k, v in d.items() if k != "deadline_date"}
                       for d in results["urgent"]],
            "upcoming": [{k: (str(v) if isinstance(v, date) else v)
                          for k, v in d.items() if k != "deadline_date"}
                         for d in results["upcoming"]],
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        total = len(deadlines)
        active = len([d for d in deadlines
                      if (datetime.strptime(d["deadline"], "%Y-%m-%d").date() - today).days >= 0])
        print(f"📅 Deadline Watchdog: {active}/{total} active deadlines")

        alerts = format_alerts(results)
        if alerts:
            print()
            for a in alerts:
                print(a)
        else:
            print("✅ 無逾期或即將到期項目")

        if args.all and results["upcoming"]:
            print(f"\n📋 未來 deadlines ({len(results['upcoming'])} 項):")
            for d in results["upcoming"]:
                print(f"  • {d['id']} {d['name']} — {d['deadline']} "
                      f"(剩 {d['days_left']} 天)")

    has_alerts = bool(results["overdue"] or results["urgent"])
    sys.exit(1 if has_alerts else 0)


if __name__ == "__main__":
    main()
