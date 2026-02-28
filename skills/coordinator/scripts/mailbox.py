#!/usr/bin/env python3
"""Cross-bot durable mailbox (Git-synced fallback channel).

Usage examples:
  python3 skills/coordinator/scripts/mailbox.py send \
    --from lab --to mac --title "HN handoff" --body "Take over 13:30/20:30 digest" --task-id L-09

  python3 skills/coordinator/scripts/mailbox.py list --to mac --status open
  python3 skills/coordinator/scripts/mailbox.py ack MB-001
  python3 skills/coordinator/scripts/mailbox.py done MB-001
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "shared"))
from jsonl_store import JsonlStore, find_workspace

WORKSPACE = find_workspace()
MAILBOX_REL = "memory/mailbox/messages.jsonl"
store = JsonlStore(MAILBOX_REL, prefix="MB")


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def cmd_send(args: argparse.Namespace) -> int:
    item = {
        "from": args.sender,
        "to": args.receiver,
        "title": args.title,
        "body": args.body,
        "task_id": args.task_id or "",
        "priority": args.priority,
        "urgent": args.urgent,
        "status": "open",
        "created_at": now_iso(),
        "acked_at": "",
        "done_at": "",
    }
    out = store.append(item)
    print(json.dumps(out, ensure_ascii=False))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    items = store.load()
    if args.to:
        items = [x for x in items if x.get("to") == args.to]
    if args.status:
        items = [x for x in items if x.get("status") == args.status]

    for x in items:
        print(json.dumps(x, ensure_ascii=False))
    if not items:
        print("(empty)")
    return 0


def _update(msg_id: str, updates: dict) -> int:
    out = store.update(msg_id, updates)
    if out is None:
        print(f"ERROR: {msg_id} not found", file=sys.stderr)
        return 1
    print(json.dumps(out, ensure_ascii=False))
    return 0


def cmd_ack(args: argparse.Namespace) -> int:
    return _update(args.id, {"status": "acked", "acked_at": now_iso()})


def cmd_done(args: argparse.Namespace) -> int:
    return _update(args.id, {"status": "done", "done_at": now_iso()})


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Git-synced mailbox for Lab↔Mac")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("send", help="send mailbox message")
    s.add_argument("--from", dest="sender", required=True, choices=["lab", "mac"])
    s.add_argument("--to", dest="receiver", required=True, choices=["lab", "mac"])
    s.add_argument("--title", required=True)
    s.add_argument("--body", required=True)
    s.add_argument("--task-id", default="")
    s.add_argument("--priority", type=int, choices=[1, 2, 3], default=2)
    s.add_argument("--urgent", action="store_true")
    s.set_defaults(func=cmd_send)

    l = sub.add_parser("list", help="list mailbox messages")
    l.add_argument("--to", choices=["lab", "mac"], default="")
    l.add_argument("--status", choices=["open", "acked", "done"], default="")
    l.set_defaults(func=cmd_list)

    a = sub.add_parser("ack", help="ack mailbox message")
    a.add_argument("id")
    a.set_defaults(func=cmd_ack)

    d = sub.add_parser("done", help="mark mailbox message done")
    d.add_argument("id")
    d.set_defaults(func=cmd_done)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
