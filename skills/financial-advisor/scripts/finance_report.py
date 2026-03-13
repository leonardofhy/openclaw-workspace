#!/usr/bin/env python3
"""Monthly financial report generator.

Usage:
    python3 finance_report.py              # Full report (snapshot + milestones + deadlines)
    python3 finance_report.py --brief      # One-paragraph summary for heartbeat
"""

import argparse
import json
import sys
from datetime import datetime, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "shared"))
from jsonl_store import JsonlStore, find_workspace

WORKSPACE = find_workspace()
SNAPSHOTS_PATH = "memory/finance/snapshots.jsonl"
MILESTONES_FILE = WORKSPACE / "memory" / "finance" / "milestones.json"
DEADLINES_FILE = WORKSPACE / "memory" / "finance" / "deadlines.json"
INCOME_LOG_PATH = "memory/finance/income-log.jsonl"


def load_json(path: Path) -> list:
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def snapshot_age_days(snapshots: list) -> int | None:
    """Returns age in days of latest snapshot, or None."""
    if not snapshots:
        return None
    latest_date = datetime.strptime(snapshots[-1]["date"], "%Y-%m-%d").date()
    return (date.today() - latest_date).days


def cmd_full():
    today = date.today()
    print(f"{'='*55}")
    print(f"💰 Leo Financial Report — {today.isoformat()}")
    print(f"{'='*55}")

    # 1. Latest snapshot
    snapshots = JsonlStore(SNAPSHOTS_PATH, prefix="SNAP").load()
    if snapshots:
        s = snapshots[-1]
        net = s.get("net", 0)
        runway = s.get("runway_months")
        age = snapshot_age_days(snapshots)
        stale_warn = f" ⚠️ {age}d old!" if age and age > 30 else ""
        print(f"\n📊 Financial Position (as of {s['date']}){stale_warn}")
        print(f"   Savings:  TWD {s['savings']:,.0f}")
        print(f"   Income:   TWD {s['monthly_income']:,.0f}/mo")
        print(f"   Expenses: TWD {s['monthly_expenses']:,.0f}/mo")
        print(f"   Net:      TWD {net:+,.0f}/mo")
        if runway and runway > 0:
            print(f"   Runway:   {runway:.0f} months")
        if len(snapshots) >= 2:
            prev = snapshots[-2]
            delta = s["savings"] - prev["savings"]
            print(f"   Δ vs prev: TWD {delta:+,.0f}")
    else:
        print("\n📊 No financial snapshots recorded.")

    # 2. Income this month
    income_store = JsonlStore(INCOME_LOG_PATH, prefix="INC")
    income_items = income_store.load()
    month_income = [
        i for i in income_items
        if i["date"].startswith(today.strftime("%Y-%m"))
    ]
    if month_income:
        total = sum(i["amount"] for i in month_income)
        print(f"\n💵 Income This Month: TWD {total:,.0f}")
        for i in month_income:
            print(f"   {i['date']} | {i['source']}: TWD {i['amount']:,.0f}")

    # 3. Milestone progress
    if MILESTONES_FILE.exists():
        milestones = load_json(MILESTONES_FILE)
        done = [m for m in milestones if m["status"] == "done"]
        overdue = [
            m for m in milestones
            if m["status"] not in ("done", "skipped")
            and (datetime.strptime(m["due"], "%Y-%m-%d").date() - today).days < 0
        ]
        pending = [
            m for m in milestones
            if m["status"] not in ("done", "skipped")
            and (datetime.strptime(m["due"], "%Y-%m-%d").date() - today).days >= 0
        ]
        print(f"\n📋 6-Month Plan: {len(done)}/{len(milestones)} done, {len(overdue)} overdue")
        if overdue:
            for m in overdue[:3]:
                print(f"   🔴 [{m['id']}] {m['task']}")
        # Next up
        pending.sort(key=lambda m: m["due"])
        if pending:
            nxt = pending[0]
            days_left = (datetime.strptime(nxt["due"], "%Y-%m-%d").date() - today).days
            print(f"   📌 Next: [{nxt['id']}] {nxt['task']} (剩 {days_left}d)")

    # 4. Upcoming financial deadlines (next 30 days)
    if DEADLINES_FILE.exists():
        deadlines = load_json(DEADLINES_FILE)
        upcoming = []
        for d in deadlines:
            if d.get("status") in ("closed", "done", "cancelled"):
                continue
            if d.get("category") not in ("scholarship", "funding", "admin"):
                continue
            dl = datetime.strptime(d["deadline"], "%Y-%m-%d").date()
            days_left = (dl - today).days
            if 0 <= days_left <= 30:
                upcoming.append({**d, "days_left": days_left})
        if upcoming:
            upcoming.sort(key=lambda x: x["days_left"])
            print(f"\n📅 Upcoming Deadlines (30 days):")
            for d in upcoming:
                print(f"   {'⚠️' if d['days_left'] <= 7 else '📌'} {d['name']} — "
                      f"{d['deadline']} (剩 {d['days_left']}d)")

    print(f"\n{'='*55}")


def cmd_brief():
    """One-paragraph summary for heartbeat."""
    today = date.today()
    parts = []

    snapshots = JsonlStore(SNAPSHOTS_PATH, prefix="SNAP").load()
    if snapshots:
        s = snapshots[-1]
        net = s.get("net", 0)
        runway = s.get("runway_months")
        age = snapshot_age_days(snapshots)
        status = "🟢" if net >= 0 else "🟡" if (runway and runway > 24) else "🔴"
        parts.append(f"{status} TWD {s['savings']:,.0f}, {net:+,.0f}/mo")
        if runway and runway > 0:
            parts.append(f"{runway:.0f}mo runway")
        if age and age > 30:
            parts.append(f"⚠️ snapshot {age}d stale")

    if MILESTONES_FILE.exists():
        milestones = load_json(MILESTONES_FILE)
        done = sum(1 for m in milestones if m["status"] == "done")
        overdue = [
            m for m in milestones
            if m["status"] not in ("done", "skipped")
            and (datetime.strptime(m["due"], "%Y-%m-%d").date() - today).days < 0
        ]
        total = len(milestones)
        if overdue:
            parts.append(f"🔴 {len(overdue)} overdue")
        parts.append(f"plan {done}/{total}")

    # Upcoming financial deadlines count
    if DEADLINES_FILE.exists():
        deadlines = load_json(DEADLINES_FILE)
        upcoming_30d = sum(
            1 for d in deadlines
            if d.get("status") not in ("closed", "done", "cancelled")
            and d.get("category") in ("scholarship", "funding", "admin")
            and 0 <= (datetime.strptime(d["deadline"], "%Y-%m-%d").date() - today).days <= 30
        )
        if upcoming_30d:
            parts.append(f"📅 {upcoming_30d} deadlines <30d")

    if parts:
        print(f"💰 Finance: {' | '.join(parts)}")
    else:
        print("💰 Finance: No data yet.")


def main():
    parser = argparse.ArgumentParser(description="Monthly financial report")
    parser.add_argument("--brief", action="store_true", help="Brief heartbeat summary")
    args = parser.parse_args()

    if args.brief:
        cmd_brief()
    else:
        cmd_full()


if __name__ == "__main__":
    main()
