#!/usr/bin/env python3
"""6-month financial plan milestone tracker.

Usage:
    python3 milestone_check.py                # Check all milestones
    python3 milestone_check.py --complete M1-1 [--note "done via NTU portal"]
    python3 milestone_check.py --skip M2-3 --note "decided not to pursue"
    python3 milestone_check.py --overdue       # Show only overdue items
    python3 milestone_check.py --next          # Show next 3 actionable items
    python3 milestone_check.py --init          # Initialize milestones.json (first time only)
"""

import argparse
import json
import sys
from datetime import datetime, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "shared"))
from jsonl_store import find_workspace

WORKSPACE = find_workspace()
MILESTONES_FILE = WORKSPACE / "memory" / "finance" / "milestones.json"

# Default milestones based on the 6-month financial survival plan
DEFAULT_MILESTONES = [
    # Month 1 — Plug the leak
    {
        "id": "M1-1", "month": 1, "phase": "plug-the-leak",
        "task": "申請工作證 (ezwp.wda.gov.tw)",
        "due": "2026-03-31", "status": "pending", "owner": "leo",
        "impact": "Legal prerequisite for all paid work",
        "effort": "30 min application + 7 days processing, NT$100"
    },
    {
        "id": "M1-2", "month": 1, "phase": "plug-the-leak",
        "task": "開始家教 (ML/Python, 2-3 hr/week)",
        "due": "2026-03-31", "status": "pending", "owner": "leo",
        "impact": "+6,400-14,400 TWD/month — covers the deficit",
        "effort": "Post on NTU forums + EECS LINE groups"
    },
    {
        "id": "M1-3", "month": 1, "phase": "plug-the-leak",
        "task": "啟動 Substack newsletter (free, AI Safety)",
        "due": "2026-03-31", "status": "pending", "owner": "leo",
        "impact": "Foundation for future paid subscribers",
        "effort": "2-3 posts this month, ~3 hr total"
    },
    {
        "id": "M1-4", "month": 1, "phase": "plug-the-leak",
        "task": "Hahow 課程大綱 (Speech AI 實戰)",
        "due": "2026-03-31", "status": "pending", "owner": "leo",
        "impact": "Prep for M2 proposal submission",
        "effort": "Outline + competitor research, ~2 hr"
    },

    # Month 2 — Launch content + apply for grants
    {
        "id": "M2-1", "month": 2, "phase": "launch-content",
        "task": "Submit LTFF grant application (AI Safety community building)",
        "due": "2026-04-30", "status": "pending", "owner": "leo",
        "impact": "$5K-20K USD — single biggest potential win",
        "effort": "2-page research proposal, ~4 hr"
    },
    {
        "id": "M2-2", "month": 2, "phase": "launch-content",
        "task": "Contact Kairos/Open Phil for organizer funding",
        "due": "2026-04-30", "status": "pending", "owner": "leo",
        "impact": "Get paid for work already doing (NTUAIS)",
        "effort": "1 email + follow-up"
    },
    {
        "id": "M2-3", "month": 2, "phase": "launch-content",
        "task": "Set up Upwork profile (Speech AI / ML)",
        "due": "2026-04-30", "status": "pending", "owner": "leo",
        "impact": "Pipeline for $40-65/hr freelancing",
        "effort": "Profile + 3 proposals, ~3 hr"
    },
    {
        "id": "M2-4", "month": 2, "phase": "launch-content",
        "task": "Submit Hahow course proposal video",
        "due": "2026-04-30", "status": "pending", "owner": "leo",
        "impact": "Unlocks crowdfunding → TWD 240K+ potential",
        "effort": "1-3 min video + outline, ~4 hr"
    },
    {
        "id": "M2-5", "month": 2, "phase": "launch-content",
        "task": "Substack: 4 posts published this month",
        "due": "2026-04-30", "status": "pending", "owner": "leo",
        "impact": "Growing to ~200 subscribers",
        "effort": "1 post/week, ~1.5 hr each"
    },

    # Month 3 — First freelancing income + scholarship apps
    {
        "id": "M3-1", "month": 3, "phase": "first-income",
        "task": "Land first Upwork project ($300-500)",
        "due": "2026-05-31", "status": "pending", "owner": "leo",
        "impact": "First non-stipend income, +25K-40K TWD",
        "effort": "5-8 hrs project work"
    },
    {
        "id": "M3-2", "month": 3, "phase": "first-income",
        "task": "Apply NSTC Conference Travel Grant (Interspeech)",
        "due": "2026-05-31", "status": "pending", "owner": "leo",
        "impact": "Covers Interspeech travel costs",
        "effort": "NTU application form, ~2 hr"
    },

    # Month 4-5 — Hahow + grant decisions
    {
        "id": "M4-1", "month": 4, "phase": "scale-up",
        "task": "Hahow course production (if crowdfunding succeeds)",
        "due": "2026-06-30", "status": "pending", "owner": "leo",
        "impact": "Deliver course → first payout",
        "effort": "15-20 hrs total recording + editing"
    },
    {
        "id": "M4-2", "month": 4, "phase": "scale-up",
        "task": "CTCI 研究獎學金 preparation starts",
        "due": "2026-06-01", "status": "pending", "owner": "bot",
        "impact": "TWD 150,000 — strong candidate with Interspeech pub",
        "effort": "Research plan + advisor recommendation"
    },

    # Month 5-6 — Passive income + diversification
    {
        "id": "M5-1", "month": 5, "phase": "passive-income",
        "task": "Convert 5% Substack free → paid (~25 paid subs)",
        "due": "2026-07-31", "status": "pending", "owner": "leo",
        "impact": "+6,250 TWD/month recurring",
        "effort": "Launch paid tier + promote"
    },
    {
        "id": "M5-2", "month": 5, "phase": "passive-income",
        "task": "Pitch first corporate AI workshop",
        "due": "2026-07-31", "status": "pending", "owner": "leo",
        "impact": "TWD 40K-120K per workshop day",
        "effort": "LinkedIn outreach + NTU alumni network"
    },
    {
        "id": "M6-1", "month": 6, "phase": "diversified",
        "task": "Monthly income ≥ TWD 60,000 (cash-flow positive)",
        "due": "2026-08-31", "status": "pending", "owner": "leo",
        "impact": "🎯 GOAL: sustainable financial position",
        "effort": "All streams running"
    },
]


def load_milestones() -> list[dict]:
    if not MILESTONES_FILE.exists():
        print(f"⚠️  {MILESTONES_FILE} not found. Run --init to create.", file=sys.stderr)
        sys.exit(1)
    with open(MILESTONES_FILE) as f:
        return json.load(f)


def save_milestones(milestones: list[dict]):
    MILESTONES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MILESTONES_FILE, "w") as f:
        json.dump(milestones, f, ensure_ascii=False, indent=2)


def cmd_init():
    if MILESTONES_FILE.exists():
        print(f"⚠️  {MILESTONES_FILE} already exists. Delete first to reinitialize.")
        return
    save_milestones(DEFAULT_MILESTONES)
    print(f"✅ Initialized {len(DEFAULT_MILESTONES)} milestones at {MILESTONES_FILE}")


def cmd_check(show_all: bool = True):
    milestones = load_milestones()
    today = date.today()

    phases = {}
    for m in milestones:
        phase = m.get("phase", "unknown")
        if phase not in phases:
            phases[phase] = []
        phases[phase].append(m)

    overdue_count = 0
    done_count = 0
    total = len(milestones)

    for phase, items in phases.items():
        print(f"\n{'─'*50}")
        print(f"📋 Phase: {phase}")
        for m in items:
            due = datetime.strptime(m["due"], "%Y-%m-%d").date()
            days_left = (due - today).days
            status = m["status"]

            if status in ("done", "skipped"):
                icon = "✅" if status == "done" else "⏭️"
                done_count += 1
            elif days_left < 0:
                icon = "🔴"
                overdue_count += 1
            elif days_left <= 7:
                icon = "⚠️"
            else:
                icon = "⬜"

            if not show_all and status in ("done", "skipped"):
                continue

            time_str = f"逾期 {-days_left}d" if days_left < 0 else f"剩 {days_left}d"
            print(f"  {icon} [{m['id']}] {m['task']}")
            print(f"     Due: {m['due']} ({time_str}) | Owner: {m['owner']}")
            if m.get("note"):
                print(f"     Note: {m['note']}")

    print(f"\n{'─'*50}")
    print(f"📊 Progress: {done_count}/{total} done | {overdue_count} overdue")

    if overdue_count > 0:
        sys.exit(1)


def cmd_overdue():
    milestones = load_milestones()
    today = date.today()
    overdue = [
        m for m in milestones
        if m["status"] not in ("done", "skipped")
        and (datetime.strptime(m["due"], "%Y-%m-%d").date() - today).days < 0
    ]
    if not overdue:
        print("✅ No overdue milestones!")
        return
    print(f"🔴 {len(overdue)} overdue milestone(s):")
    for m in overdue:
        due = datetime.strptime(m["due"], "%Y-%m-%d").date()
        print(f"  [{m['id']}] {m['task']} — 逾期 {(today - due).days}d")
        print(f"     Impact: {m.get('impact', 'N/A')}")


def cmd_next(count: int = 3):
    milestones = load_milestones()
    today = date.today()
    pending = [
        m for m in milestones
        if m["status"] not in ("done", "skipped")
    ]
    pending.sort(key=lambda m: m["due"])
    top = pending[:count]
    if not top:
        print("🎉 All milestones complete!")
        return
    print(f"📋 Next {len(top)} actionable milestone(s):")
    for m in top:
        due = datetime.strptime(m["due"], "%Y-%m-%d").date()
        days_left = (due - today).days
        icon = "🔴" if days_left < 0 else "⚠️" if days_left <= 7 else "📌"
        print(f"  {icon} [{m['id']}] {m['task']}")
        print(f"     Due: {m['due']} | Effort: {m.get('effort', 'N/A')}")


def cmd_complete(milestone_id: str, note: str = ""):
    milestones = load_milestones()
    for m in milestones:
        if m["id"] == milestone_id:
            m["status"] = "done"
            m["completed_date"] = date.today().isoformat()
            if note:
                m["note"] = note
            save_milestones(milestones)
            print(f"✅ {milestone_id} marked done: {m['task']}")
            return
    print(f"❌ Milestone {milestone_id} not found", file=sys.stderr)
    sys.exit(1)


def cmd_skip(milestone_id: str, note: str = ""):
    milestones = load_milestones()
    for m in milestones:
        if m["id"] == milestone_id:
            m["status"] = "skipped"
            if note:
                m["note"] = note
            save_milestones(milestones)
            print(f"⏭️  {milestone_id} skipped: {m['task']}")
            return
    print(f"❌ Milestone {milestone_id} not found", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="6-month financial plan milestones")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--init", action="store_true", help="Initialize milestones.json")
    group.add_argument("--complete", type=str, metavar="ID", help="Mark milestone as done")
    group.add_argument("--skip", type=str, metavar="ID", help="Skip a milestone")
    group.add_argument("--overdue", action="store_true", help="Show only overdue")
    group.add_argument("--next", action="store_true", help="Show next actionable items")

    parser.add_argument("--note", type=str, default="", help="Note for complete/skip")
    parser.add_argument("--count", type=int, default=3, help="Number of items for --next")

    args = parser.parse_args()

    if args.init:
        cmd_init()
    elif args.complete:
        cmd_complete(args.complete, args.note)
    elif args.skip:
        cmd_skip(args.skip, args.note)
    elif args.overdue:
        cmd_overdue()
    elif args.next:
        cmd_next(args.count)
    else:
        cmd_check()


if __name__ == "__main__":
    main()
