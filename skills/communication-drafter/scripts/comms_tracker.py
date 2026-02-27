#!/usr/bin/env python3
"""Communication tracker — log, list, overdue, resolve.

Usage:
    comms_tracker.py log --to NAME --subject SUBJ --channel CH --status STATUS [--followup-days N] [--notes TEXT]
    comms_tracker.py list [--to NAME] [--status STATUS] [--limit N]
    comms_tracker.py overdue
    comms_tracker.py resolve COM-ID [--notes TEXT]
    comms_tracker.py show COM-ID
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "shared"))
from jsonl_store import JsonlStore
import json

store = JsonlStore("memory/communications/comms.jsonl", prefix="COM")


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def cmd_log(args):
    followup_date = None
    if args.followup_days:
        followup_date = (datetime.now() + timedelta(days=args.followup_days)).strftime("%Y-%m-%d")

    comm = store.append({
        "to": args.to, "subject": args.subject, "channel": args.channel,
        "status": args.status, "created": now_iso(),
        "followup_date": followup_date, "followup_days": args.followup_days,
        "resolved": False, "resolved_date": None, "notes": args.notes,
    })
    print(f"📧 Logged {comm['id']}: → {args.to} | {args.subject}")
    if followup_date:
        print(f"   Follow-up by: {followup_date}")


def cmd_list(args):
    comms = store.load()
    if args.to:
        comms = [c for c in comms if args.to.lower() in c["to"].lower()]
    if args.status:
        comms = [c for c in comms if c["status"] == args.status]
    if args.limit:
        comms = comms[-args.limit:]

    if not comms:
        print("📧 No communications found.")
        return

    print(f"📧 Communications ({len(comms)}):\n")
    for c in comms:
        resolved = "✅" if c.get("resolved") else "📨"
        followup = f" | follow-up: {c['followup_date']}" if c.get("followup_date") and not c.get("resolved") else ""
        print(f"  {resolved} {c['id']} | → {c['to']} | {c['subject']}")
        print(f"     {c['channel']} · {c['status']} · {c['created'][:10]}{followup}")
        if c.get("notes"):
            print(f"     📝 {c['notes']}")
        print()


def cmd_overdue(_args):
    comms = store.load()
    today = datetime.now().date()

    overdue, upcoming = [], []
    for c in comms:
        if c.get("resolved") or not c.get("followup_date"):
            continue
        followup = datetime.strptime(c["followup_date"], "%Y-%m-%d").date()
        days_left = (followup - today).days
        if days_left < 0:
            overdue.append((c, -days_left))
        elif days_left <= 2:
            upcoming.append((c, days_left))

    if not overdue and not upcoming:
        print("✅ No overdue or upcoming follow-ups.")
        return

    if overdue:
        print(f"🔴 Overdue ({len(overdue)}):\n")
        for c, days in overdue:
            print(f"  {c['id']} | → {c['to']} | {c['subject']} — {days} 天逾期")
        print()
    if upcoming:
        print(f"⚠️ Upcoming ({len(upcoming)}):\n")
        for c, days in upcoming:
            print(f"  {c['id']} | → {c['to']} | {c['subject']} — {days} 天後到期")


def cmd_resolve(args):
    comm = store.find(args.comm_id)
    if not comm:
        print(f"❌ {args.comm_id} not found", file=sys.stderr)
        sys.exit(1)
    updates = {"resolved": True, "resolved_date": now_iso()}
    if args.notes:
        updates["notes"] = (comm.get("notes") or "") + f" | Resolved: {args.notes}"
    store.update(args.comm_id, updates)
    print(f"✅ {args.comm_id} resolved")


def cmd_show(args):
    comm = store.find(args.comm_id)
    if not comm:
        print(f"❌ {args.comm_id} not found", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(comm, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="Communication Tracker")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("log")
    p.add_argument("--to", required=True); p.add_argument("--subject", required=True)
    p.add_argument("--channel", required=True, choices=["email", "discord", "line", "signal", "in-person", "other"])
    p.add_argument("--status", required=True, choices=["sent", "received", "drafted", "scheduled"])
    p.add_argument("--followup-days", type=int); p.add_argument("--notes")

    p = sub.add_parser("list")
    p.add_argument("--to"); p.add_argument("--status", choices=["sent", "received", "drafted", "scheduled"])
    p.add_argument("--limit", type=int)

    sub.add_parser("overdue")

    p = sub.add_parser("resolve"); p.add_argument("comm_id"); p.add_argument("--notes")
    p = sub.add_parser("show"); p.add_argument("comm_id")

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help(); sys.exit(1)

    {"log": cmd_log, "list": cmd_list, "overdue": cmd_overdue,
     "resolve": cmd_resolve, "show": cmd_show}[args.cmd](args)


if __name__ == "__main__":
    main()
