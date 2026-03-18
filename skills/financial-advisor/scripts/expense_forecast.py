#!/usr/bin/env python3
"""Expense forecasting and runway projection for Leo's finances.

Usage:
    # Full monthly financial summary
    python3 expense_forecast.py

    # Heartbeat one-liner (JSON)
    python3 expense_forecast.py --json

    # Show only runway projection
    python3 expense_forecast.py --runway

    # Show upcoming financial deadlines
    python3 expense_forecast.py --deadlines [--days 30]
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
DEADLINES_FILE = WORKSPACE / "memory" / "finance" / "deadlines.json"

# Fixed monthly expenses (TWD) — baseline from FINANCE_TRACKER.md
FIXED_EXPENSES = {
    "rent": 8_000,
    "food": 8_000,
    "utilities": 1_500,
    "phone": 500,
    "transport": 1_500,
}
FIXED_TOTAL = sum(FIXED_EXPENSES.values())
# Average variable on top of fixed (from 25,609 - 19,500 fixed)
VARIABLE_BASELINE = 6_100


def load_snapshots() -> list[dict]:
    return JsonlStore(SNAPSHOTS_PATH, prefix="SNAP").load()


def load_income_log() -> list[dict]:
    return JsonlStore(INCOME_LOG_PATH, prefix="INC").load()


def load_expense_log() -> list[dict]:
    return JsonlStore(EXPENSE_LOG_PATH, prefix="EXP").load()


def load_deadlines() -> list[dict]:
    if not DEADLINES_FILE.exists():
        return []
    with open(DEADLINES_FILE) as f:
        return json.load(f)


def calc_burn_rate(snapshots: list[dict]) -> float:
    """Calculate monthly burn rate from snapshots. Returns positive number = net outflow."""
    if not snapshots:
        return 0.0
    latest = snapshots[-1]
    net = latest.get("net", latest.get("monthly_income", 0) - latest.get("monthly_expenses", 0))
    return -net if net < 0 else 0.0


def calc_avg_income(income_log: list[dict], months: int = 3) -> float:
    """Average monthly income from recent log entries."""
    if not income_log:
        return 0.0
    today = date.today()
    cutoff_month = today.month - months + 1
    cutoff_year = today.year
    while cutoff_month <= 0:
        cutoff_month += 12
        cutoff_year -= 1

    filtered = []
    for item in income_log:
        d = datetime.strptime(item["date"], "%Y-%m-%d").date()
        if (d.year, d.month) >= (cutoff_year, cutoff_month):
            filtered.append(item)

    if not filtered:
        return 0.0
    total = sum(i["amount"] for i in filtered)
    # Count distinct months in filtered data
    seen_months = {(datetime.strptime(i["date"], "%Y-%m-%d").year,
                     datetime.strptime(i["date"], "%Y-%m-%d").month) for i in filtered}
    return total / max(len(seen_months), 1)


def calc_avg_expenses(snapshots: list[dict], expense_log: list[dict]) -> float:
    """Average monthly expenses from snapshots."""
    if snapshots:
        return snapshots[-1].get("monthly_expenses", FIXED_TOTAL + VARIABLE_BASELINE)
    return FIXED_TOTAL + VARIABLE_BASELINE


def project_runway(savings: float, burn_rate: float) -> dict:
    """Project runway under pessimistic/realistic/optimistic scenarios.

    Returns dict with months for each scenario.
    """
    if burn_rate <= 0:
        return {"pessimistic": float("inf"), "realistic": float("inf"), "optimistic": float("inf")}

    return {
        "pessimistic": savings / (burn_rate * 1.2),   # 20% higher burn
        "realistic": savings / burn_rate,
        "optimistic": savings / (burn_rate * 0.8),     # 20% lower burn
    }


def get_income_sources(income_log: list[dict], months: int = 3) -> dict[str, float]:
    """Group income by source over recent months."""
    if not income_log:
        return {}
    today = date.today()
    cutoff_month = today.month - months + 1
    cutoff_year = today.year
    while cutoff_month <= 0:
        cutoff_month += 12
        cutoff_year -= 1

    by_source: dict[str, float] = {}
    for item in income_log:
        d = datetime.strptime(item["date"], "%Y-%m-%d").date()
        if (d.year, d.month) >= (cutoff_year, cutoff_month):
            src = item["source"]
            by_source[src] = by_source.get(src, 0) + item["amount"]
    return by_source


def get_upcoming_deadlines(deadlines: list[dict], days: int = 30) -> list[dict]:
    """Return financial deadlines within the next N days."""
    today = date.today()
    upcoming = []
    for d in deadlines:
        if d.get("status") in ("closed", "done", "cancelled"):
            continue
        if d.get("category") not in ("scholarship", "funding", "admin"):
            continue
        dl = datetime.strptime(d["deadline"], "%Y-%m-%d").date()
        days_left = (dl - today).days
        if 0 <= days_left <= days:
            upcoming.append({**d, "days_left": days_left})
    upcoming.sort(key=lambda x: x["days_left"])
    return upcoming


def get_scholarship_status(deadlines: list[dict]) -> list[dict]:
    """Extract scholarship/grant items with their status."""
    results = []
    today = date.today()
    for d in deadlines:
        if d.get("category") not in ("scholarship", "funding"):
            continue
        dl = datetime.strptime(d["deadline"], "%Y-%m-%d").date()
        days_left = (dl - today).days
        status = d.get("status", "open" if days_left >= 0 else "past_due")
        results.append({
            "name": d["name"],
            "deadline": d["deadline"],
            "days_left": days_left,
            "status": status,
            "category": d["category"],
        })
    results.sort(key=lambda x: x["days_left"])
    return results


def build_summary() -> dict:
    """Build the full financial summary as a structured dict."""
    snapshots = load_snapshots()
    income_log = load_income_log()
    expense_log = load_expense_log()
    deadlines = load_deadlines()

    savings = snapshots[-1]["savings"] if snapshots else 0.0
    monthly_income = snapshots[-1].get("monthly_income", 0) if snapshots else 0.0
    monthly_expenses = calc_avg_expenses(snapshots, expense_log)
    burn_rate = calc_burn_rate(snapshots)
    avg_income = calc_avg_income(income_log, months=3)
    runway = project_runway(savings, burn_rate)

    snapshot_date = snapshots[-1]["date"] if snapshots else None
    snapshot_age = (date.today() - datetime.strptime(snapshot_date, "%Y-%m-%d").date()).days if snapshot_date else None

    return {
        "date": date.today().isoformat(),
        "snapshot_date": snapshot_date,
        "snapshot_age_days": snapshot_age,
        "savings": savings,
        "monthly_income": monthly_income,
        "avg_income_3mo": round(avg_income, 0),
        "monthly_expenses": monthly_expenses,
        "fixed_expenses": FIXED_TOTAL,
        "variable_expenses": monthly_expenses - FIXED_TOTAL,
        "burn_rate": burn_rate,
        "runway": {k: round(v, 1) if v != float("inf") else None for k, v in runway.items()},
        "income_sources": get_income_sources(income_log, months=3),
        "upcoming_deadlines": get_upcoming_deadlines(deadlines, days=60),
        "scholarship_status": get_scholarship_status(deadlines),
    }


def cmd_full() -> None:
    """Print full monthly financial summary."""
    s = build_summary()
    today = date.today()
    print(f"{'='*55}")
    print(f"📊 Expense Forecast & Runway — {today.isoformat()}")
    print(f"{'='*55}")

    # Position
    stale = f" ⚠️ {s['snapshot_age_days']}d stale!" if s["snapshot_age_days"] and s["snapshot_age_days"] > 30 else ""
    print(f"\n💰 Position (data: {s['snapshot_date'] or 'N/A'}){stale}")
    print(f"   Savings:  TWD {s['savings']:,.0f}")

    # Income
    print(f"\n📈 Income")
    print(f"   Monthly (latest):  TWD {s['monthly_income']:,.0f}")
    print(f"   3-mo average:      TWD {s['avg_income_3mo']:,.0f}")
    if s["income_sources"]:
        for src, amt in sorted(s["income_sources"].items(), key=lambda x: -x[1]):
            print(f"     {src}: TWD {amt:,.0f}")

    # Expenses
    print(f"\n📉 Expenses: TWD {s['monthly_expenses']:,.0f}/mo")
    print(f"   Fixed:    TWD {s['fixed_expenses']:,.0f}")
    for name, amt in FIXED_EXPENSES.items():
        print(f"     {name}: TWD {amt:,.0f}")
    print(f"   Variable: TWD {s['variable_expenses']:,.0f}")

    # Runway
    print(f"\n⏳ Runway Projection")
    if s["burn_rate"] > 0:
        print(f"   Burn rate: TWD {s['burn_rate']:,.0f}/mo")
        r = s["runway"]
        for scenario in ("pessimistic", "realistic", "optimistic"):
            val = r[scenario]
            label = f"{val:.0f} months" if val is not None else "∞"
            marker = "🔴" if val is not None and val < 12 else "🟡" if val is not None and val < 24 else "🟢"
            print(f"   {marker} {scenario.capitalize():>12}: {label}")
    else:
        print(f"   🟢 Cash-flow positive — no depletion projected")

    # Scholarships
    scholarships = s["scholarship_status"]
    if scholarships:
        active = [x for x in scholarships if x["status"] not in ("closed", "done", "cancelled")]
        if active:
            print(f"\n🎓 Scholarship/Grant Pipeline ({len(active)} active)")
            for item in active[:5]:
                marker = "⚠️" if 0 <= item["days_left"] <= 14 else "📌" if item["days_left"] >= 0 else "❌"
                days_str = f"{item['days_left']}d" if item["days_left"] >= 0 else "PAST"
                print(f"   {marker} {item['name']} — {item['deadline']} ({days_str})")

    # Upcoming deadlines
    upcoming = s["upcoming_deadlines"]
    if upcoming:
        print(f"\n📅 Financial Deadlines (next 60d)")
        for d in upcoming:
            marker = "⚠️" if d["days_left"] <= 7 else "📌"
            print(f"   {marker} {d['name']} — {d['deadline']} ({d['days_left']}d)")

    print(f"\n{'='*55}")


def cmd_runway() -> None:
    """Print just the runway projection."""
    s = build_summary()
    if s["burn_rate"] <= 0:
        print("🟢 Cash-flow positive — no depletion projected")
        return
    r = s["runway"]
    print(f"⏳ Runway (burn TWD {s['burn_rate']:,.0f}/mo, savings TWD {s['savings']:,.0f}):")
    for scenario in ("pessimistic", "realistic", "optimistic"):
        val = r[scenario]
        label = f"{val:.0f}mo" if val is not None else "∞"
        print(f"   {scenario.capitalize():>12}: {label}")


def cmd_deadlines(days: int = 30) -> None:
    """Print upcoming financial deadlines."""
    deadlines = load_deadlines()
    upcoming = get_upcoming_deadlines(deadlines, days=days)
    if not upcoming:
        print(f"📅 No financial deadlines in the next {days} days.")
        return
    print(f"📅 Financial Deadlines (next {days}d):")
    for d in upcoming:
        marker = "⚠️" if d["days_left"] <= 7 else "📌"
        print(f"   {marker} [{d['id']}] {d['name']} — {d['deadline']} ({d['days_left']}d)")
        print(f"      Action: {d['action']}")


def cmd_json() -> None:
    """Output summary as JSON for heartbeat integration."""
    s = build_summary()
    # Simplify for heartbeat
    output = {
        "date": s["date"],
        "savings": s["savings"],
        "monthly_income": s["monthly_income"],
        "monthly_expenses": s["monthly_expenses"],
        "burn_rate": s["burn_rate"],
        "runway": s["runway"],
        "snapshot_age_days": s["snapshot_age_days"],
        "upcoming_deadline_count": len(s["upcoming_deadlines"]),
        "next_deadline": s["upcoming_deadlines"][0]["name"] if s["upcoming_deadlines"] else None,
        "status": "stale" if s["snapshot_age_days"] and s["snapshot_age_days"] > 45
                  else "warning" if s["snapshot_age_days"] and s["snapshot_age_days"] > 30
                  else "ok",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Expense forecasting and runway projection")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--json", action="store_true", help="JSON output for heartbeat")
    group.add_argument("--runway", action="store_true", help="Runway projection only")
    group.add_argument("--deadlines", action="store_true", help="Upcoming deadlines only")
    parser.add_argument("--days", type=int, default=30, help="Deadline lookahead days (default 30)")
    args = parser.parse_args()

    if args.json:
        cmd_json()
    elif args.runway:
        cmd_runway()
    elif args.deadlines:
        cmd_deadlines(args.days)
    else:
        cmd_full()


if __name__ == "__main__":
    main()
