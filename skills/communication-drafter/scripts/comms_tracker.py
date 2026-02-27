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
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
COMMS_DIR = WORKSPACE / "memory" / "communications"
COMMS_FILE = COMMS_DIR / "comms.jsonl"


def load_comms() -> list[dict]:
    if not COMMS_FILE.exists():
        return []
    comms = []
    for line in COMMS_FILE.read_text().strip().splitlines():
        if line.strip():
            try:
                comms.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"⚠️ Skipping malformed line", file=sys.stderr)
    return comms


def save_comm(comm: dict):
    COMMS_DIR.mkdir(parents=True, exist_ok=True)
    with open(COMMS_FILE, "a") as f:
        f.write(json.dumps(comm, ensure_ascii=False) + "\n")


def rewrite_all(comms: list[dict]):
    COMMS_DIR.mkdir(parents=True, exist_ok=True)
    with open(COMMS_FILE, "w") as f:
        for c in comms:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")


def next_id(comms: list[dict]) -> str:
    if not comms:
        return "COM-001"
    max_num = 0
    for c in comms:
        try:
            num = int(c["id"].split("-")[1])
            max_num = max(max_num, num)
        except (IndexError, ValueError):
            pass
    return f"COM-{max_num + 1:03d}"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def cmd_log(args):
    comms = load_comms()
    comm_id = next_id(comms)

    followup_date = None
    if args.followup_days:
        followup_date = (datetime.now() + timedelta(days=args.followup_days)).strftime("%Y-%m-%d")

    comm = {
        "id": comm_id,
        "to": args.to,
        "subject": args.subject,
        "channel": args.channel,
        "status": args.status,
        "created": now_iso(),
        "followup_date": followup_date,
        "followup_days": args.followup_days,
        "resolved": False,
        "resolved_date": None,
        "notes": args.notes,
    }

    save_comm(comm)
    print(f"📧 Logged {comm_id}: → {args.to} | {args.subject}")
    if followup_date:
        print(f"   Follow-up by: {followup_date}")


def cmd_list(args):
    comms = load_comms()

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


def cmd_overdue(args):
    comms = load_comms()
    today = datetime.now().date()

    overdue = []
    upcoming = []
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
    comms = load_comms()
    found = False
    for c in comms:
        if c["id"] == args.comm_id:
            c["resolved"] = True
            c["resolved_date"] = now_iso()
            if args.notes:
                c["notes"] = (c.get("notes") or "") + f" | Resolved: {args.notes}"
            found = True
            break
    if not found:
        print(f"❌ {args.comm_id} not found", file=sys.stderr)
        sys.exit(1)
    rewrite_all(comms)
    print(f"✅ {args.comm_id} resolved")


def cmd_show(args):
    comms = load_comms()
    comm = next((c for c in comms if c["id"] == args.comm_id), None)
    if not comm:
        print(f"❌ {args.comm_id} not found", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(comm, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="Communication Tracker")
    sub = parser.add_subparsers(dest="cmd")

    # log
    p_log = sub.add_parser("log")
    p_log.add_argument("--to", required=True, help="Recipient name")
    p_log.add_argument("--subject", required=True, help="Subject/topic")
    p_log.add_argument("--channel", required=True, choices=["email", "discord", "line", "signal", "in-person", "other"])
    p_log.add_argument("--status", required=True, choices=["sent", "received", "drafted", "scheduled"])
    p_log.add_argument("--followup-days", type=int, help="Days until follow-up needed")
    p_log.add_argument("--notes", help="Additional notes")

    # list
    p_list = sub.add_parser("list")
    p_list.add_argument("--to", help="Filter by recipient")
    p_list.add_argument("--status", choices=["sent", "received", "drafted", "scheduled"])
    p_list.add_argument("--limit", type=int)

    # overdue
    sub.add_parser("overdue")

    # resolve
    p_resolve = sub.add_parser("resolve")
    p_resolve.add_argument("comm_id")
    p_resolve.add_argument("--notes", help="Resolution notes")

    # show
    p_show = sub.add_parser("show")
    p_show.add_argument("comm_id")

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    {
        "log": cmd_log,
        "list": cmd_list,
        "overdue": cmd_overdue,
        "resolve": cmd_resolve,
        "show": cmd_show,
    }[args.cmd](args)


if __name__ == "__main__":
    main()
