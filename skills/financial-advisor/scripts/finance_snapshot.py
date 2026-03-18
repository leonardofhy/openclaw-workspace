#!/usr/bin/env python3
"""Financial snapshot manager — record, view, and track Leo's financial position.

Usage:
    # View latest snapshot
    python3 finance_snapshot.py --latest

    # Check if snapshot is stale (for heartbeat)
    python3 finance_snapshot.py --check-stale [--max-age 45]

    # Record a new monthly snapshot
    python3 finance_snapshot.py --record --savings 280000 --income 20000 --expenses 25600

    # Log an income event
    python3 finance_snapshot.py --log-income --source tutoring --amount 4800 [--note "2 sessions"] [--date 2026-03-10]

    # Log an expense event
    python3 finance_snapshot.py --log-expense --source "Interspeech registration" --amount 8000 [--date 2026-03-10]

    # View income log (current month)
    python3 finance_snapshot.py --income-summary [--months 3]

    # Trend analysis (last N months)
    python3 finance_snapshot.py --trend [--months 6]
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
INCOME_LOG_PATH = "memory/finance/income-log.jsonl"
EXPENSE_LOG_PATH = "memory/finance/expense-log.jsonl"


def get_snapshots() -> JsonlStore:
    return JsonlStore(SNAPSHOTS_PATH, prefix="SNAP")


def get_income_log() -> JsonlStore:
    return JsonlStore(INCOME_LOG_PATH, prefix="INC")


def get_expense_log() -> JsonlStore:
    return JsonlStore(EXPENSE_LOG_PATH, prefix="EXP")


def cmd_latest() -> None:
    """Show latest financial snapshot."""
    store = get_snapshots()
    items = store.load()
    if not items:
        print("📊 No snapshots recorded yet.")
        print("Record one: python3 finance_snapshot.py --record --savings X --income Y --expenses Z")
        return

    latest = items[-1]
    savings = latest.get("savings", 0)
    income = latest.get("monthly_income", 0)
    expenses = latest.get("monthly_expenses", 0)
    net = income - expenses
    runway_months = savings / (-net) if net < 0 else float("inf")

    print(f"📊 Financial Snapshot ({latest.get('date', 'unknown')})")
    print(f"   💰 Savings:  TWD {savings:,.0f}")
    print(f"   📈 Income:   TWD {income:,.0f}/mo")
    print(f"   📉 Expenses: TWD {expenses:,.0f}/mo")
    print(f"   {'🔴' if net < 0 else '🟢'} Net:      TWD {net:+,.0f}/mo")
    if net < 0:
        print(f"   ⏳ Runway:   {runway_months:.0f} months")

    # Compare with previous
    if len(items) >= 2:
        prev = items[-2]
        prev_savings = prev.get("savings", 0)
        delta = savings - prev_savings
        print(f"\n   vs {prev.get('date', 'prev')}: {'📈' if delta > 0 else '📉'} TWD {delta:+,.0f}")


def cmd_record(savings: float, income: float, expenses: float, note: str = "") -> None:
    """Record a new monthly snapshot."""
    store = get_snapshots()
    today = date.today().isoformat()
    net = income - expenses
    runway = savings / (-net) if net < 0 else -1  # -1 = infinite

    entry = {
        "date": today,
        "savings": savings,
        "monthly_income": income,
        "monthly_expenses": expenses,
        "net": net,
        "runway_months": round(runway, 1) if runway > 0 else None,
    }
    if note:
        entry["note"] = note

    item = store.append(entry)
    print(f"✅ Snapshot recorded: {item['id']} ({today})")
    print(f"   TWD {savings:,.0f} savings | {income:,.0f} in | {expenses:,.0f} out | {net:+,.0f} net")
    if runway > 0:
        print(f"   Runway: {runway:.0f} months")


def cmd_check_stale(max_age: int = 45) -> None:
    """Check if latest snapshot is too old."""
    store = get_snapshots()
    items = store.load()
    if not items:
        print(f"🔴 No snapshots recorded. Record one with --record.", file=sys.stderr)
        sys.exit(2)

    latest = items[-1]
    latest_date = datetime.strptime(latest["date"], "%Y-%m-%d").date()
    age_days = (date.today() - latest_date).days

    if age_days > max_age:
        print(f"🔴 Snapshot is {age_days} days old (threshold: {max_age}d). Ask Leo for updated 記帳.")
        sys.exit(1)
    elif age_days > max_age * 0.7:
        print(f"⚠️ Snapshot is {age_days} days old (threshold: {max_age}d). Consider updating soon.")
        sys.exit(0)
    else:
        print(f"✅ Snapshot is {age_days} days old (threshold: {max_age}d).")
        sys.exit(0)


def cmd_log_income(source: str, amount: float, note: str = "", log_date: str = "") -> None:
    """Log an income event."""
    store = get_income_log()
    entry_date = log_date or date.today().isoformat()

    entry = {
        "date": entry_date,
        "source": source,
        "amount": amount,
    }
    if note:
        entry["note"] = note

    item = store.append(entry)
    print(f"✅ Income logged: {item['id']} | {source} | TWD {amount:,.0f} | {entry_date}")


def cmd_log_expense(source: str, amount: float, note: str = "", log_date: str = "") -> None:
    """Log a one-off expense event."""
    store = get_expense_log()
    entry_date = log_date or date.today().isoformat()

    entry = {
        "date": entry_date,
        "source": source,
        "amount": amount,
    }
    if note:
        entry["note"] = note

    item = store.append(entry)
    print(f"✅ Expense logged: {item['id']} | {source} | TWD {amount:,.0f} | {entry_date}")


def cmd_income_summary(months: int = 1) -> None:
    """Show income summary for recent months."""
    store = get_income_log()
    items = store.load()
    if not items:
        print("📊 No income events logged yet.")
        return

    today = date.today()
    # Correct month arithmetic: subtract months, handling year rollover
    cutoff_month = today.month - months + 1
    cutoff_year = today.year
    while cutoff_month <= 0:
        cutoff_month += 12
        cutoff_year -= 1

    filtered = []
    for item in items:
        d = datetime.strptime(item["date"], "%Y-%m-%d").date()
        if (d.year, d.month) >= (cutoff_year, cutoff_month):
            filtered.append(item)

    if not filtered:
        print(f"📊 No income events in the last {months} month(s).")
        return

    # Group by source
    by_source: dict[str, float] = {}
    for item in filtered:
        src = item["source"]
        by_source[src] = by_source.get(src, 0) + item["amount"]

    total = sum(by_source.values())
    print(f"📊 Income Summary (last {months} month{'s' if months > 1 else ''}):")
    for src, amt in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"   {src}: TWD {amt:,.0f}")
    print(f"   ─────────────")
    print(f"   Total: TWD {total:,.0f}")


def cmd_trend(months: int = 6) -> None:
    """Show trend over recent snapshots."""
    store = get_snapshots()
    items = store.load()
    if len(items) < 2:
        print("📊 Need at least 2 snapshots for trend analysis.")
        return

    recent = items[-months:]
    print(f"📊 Financial Trend (last {len(recent)} snapshots):")
    print(f"   {'Date':<12} {'Savings':>10} {'Income':>8} {'Expenses':>10} {'Net':>8}")
    print(f"   {'─'*12} {'─'*10} {'─'*8} {'─'*10} {'─'*8}")
    for s in recent:
        net = s.get("net", s.get("monthly_income", 0) - s.get("monthly_expenses", 0))
        print(f"   {s['date']:<12} {s['savings']:>10,.0f} {s.get('monthly_income', 0):>8,.0f} "
              f"{s.get('monthly_expenses', 0):>10,.0f} {net:>+8,.0f}")

    # Overall direction
    first_savings = recent[0]["savings"]
    last_savings = recent[-1]["savings"]
    delta = last_savings - first_savings
    direction = "📈 improving" if delta > 0 else "📉 declining"
    print(f"\n   Overall: {direction} (TWD {delta:+,.0f})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Financial snapshot manager")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--latest", action="store_true", help="View latest snapshot")
    group.add_argument("--check-stale", action="store_true", help="Check snapshot staleness")
    group.add_argument("--record", action="store_true", help="Record new snapshot")
    group.add_argument("--log-income", action="store_true", help="Log income event")
    group.add_argument("--log-expense", action="store_true", help="Log expense event")
    group.add_argument("--income-summary", action="store_true", help="Income summary")
    group.add_argument("--trend", action="store_true", help="Trend analysis")

    parser.add_argument("--savings", type=float, help="Total savings (TWD)")
    parser.add_argument("--income", type=float, help="Monthly income (TWD)")
    parser.add_argument("--expenses", type=float, help="Monthly expenses (TWD)")
    parser.add_argument("--source", type=str, help="Income/expense source name")
    parser.add_argument("--amount", type=float, help="Amount (TWD)")
    parser.add_argument("--note", type=str, default="", help="Optional note")
    parser.add_argument("--date", type=str, default="", help="Override date (YYYY-MM-DD)")
    parser.add_argument("--months", type=int, default=3, help="Months to look back")
    parser.add_argument("--max-age", type=int, default=45, help="Max snapshot age in days")

    args = parser.parse_args()

    if args.latest:
        cmd_latest()
    elif args.check_stale:
        cmd_check_stale(args.max_age)
    elif args.record:
        if not all([args.savings is not None, args.income is not None, args.expenses is not None]):
            parser.error("--record requires --savings, --income, and --expenses")
        cmd_record(args.savings, args.income, args.expenses, args.note)
    elif args.log_income:
        if not all([args.source, args.amount is not None]):
            parser.error("--log-income requires --source and --amount")
        cmd_log_income(args.source, args.amount, args.note, args.date)
    elif args.log_expense:
        if not all([args.source, args.amount is not None]):
            parser.error("--log-expense requires --source and --amount")
        cmd_log_expense(args.source, args.amount, args.note, args.date)
    elif args.income_summary:
        cmd_income_summary(args.months)
    elif args.trend:
        cmd_trend(args.months)


if __name__ == "__main__":
    main()
