#!/usr/bin/env python3
"""Cross-bot durable mailbox (Git-synced fallback channel).

All commands auto-sync git (pull other branch before read, push after write).
Use --no-sync to skip git operations.

Usage:
  # Send (auto: write + git push + print Discord @mention)
  python3 mailbox.py send --from lab --to mac --title "..." --body "..."

  # List open items for me (auto: git pull other branch first)
  python3 mailbox.py list --to lab --status open

  # Ack (auto: git pull + update + git push)
  python3 mailbox.py ack MB-003

  # Done (auto: git pull + update + git push)
  python3 mailbox.py done MB-003
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "shared"))
from jsonl_store import JsonlStore, find_workspace

WORKSPACE = find_workspace()
MAILBOX_REL = "memory/mailbox/messages.jsonl"
store = JsonlStore(MAILBOX_REL, prefix="MB")

# Branch mapping: my branch → other branch
BRANCH_MAP = {
    "lab-desktop": "macbook-m3",
    "macbook-m3": "lab-desktop",
}

# Discord bot IDs for @mention generation
BOT_IDS = {
    "lab": "1476497627490025644",
    "mac": "1473210706567495730",
}

BOT_SYNC_CHANNEL = "1476624495702966506"


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _current_branch() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            text=True, stderr=subprocess.DEVNULL, cwd=WORKSPACE,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _other_branch() -> str:
    return BRANCH_MAP.get(_current_branch(), "")


def _git_pull(quiet: bool = False) -> bool:
    """Fetch and merge the other branch to get latest messages."""
    other = _other_branch()
    if not other:
        if not quiet:
            print("⚠️ Cannot determine other branch, skipping git pull", file=sys.stderr)
        return False
    try:
        subprocess.run(
            ["git", "fetch", "origin", other],
            cwd=WORKSPACE, capture_output=True, text=True, timeout=15,
        )
        result = subprocess.run(
            ["git", "merge", f"origin/{other}", "--no-edit"],
            cwd=WORKSPACE, capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0 and "CONFLICT" in (result.stdout + result.stderr):
            # Conflict on messages.jsonl — abort and warn
            subprocess.run(["git", "merge", "--abort"], cwd=WORKSPACE, capture_output=True)
            if not quiet:
                print(f"⚠️ Merge conflict with {other}, aborted. Manual resolve needed.", file=sys.stderr)
            return False
        return True
    except (subprocess.TimeoutExpired, Exception) as e:
        if not quiet:
            print(f"⚠️ git pull failed: {e}", file=sys.stderr)
        return False


def _git_push(msg_id: str, action: str) -> bool:
    """Add, commit, and push messages.jsonl."""
    jsonl_path = str(WORKSPACE / MAILBOX_REL)
    try:
        subprocess.run(
            ["git", "add", jsonl_path],
            cwd=WORKSPACE, capture_output=True, timeout=10,
        )
        subprocess.run(
            ["git", "commit", "-m", f"mailbox: {msg_id} {action}"],
            cwd=WORKSPACE, capture_output=True, text=True, timeout=10,
        )
        result = subprocess.run(
            ["git", "push"],
            cwd=WORKSPACE, capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            print(f"📤 git push ok", file=sys.stderr)
            return True
        else:
            print(f"⚠️ git push failed: {result.stderr.strip()}", file=sys.stderr)
            return False
    except (subprocess.TimeoutExpired, Exception) as e:
        print(f"⚠️ git push failed: {e}", file=sys.stderr)
        return False


def _discord_mention(recipient: str, msg_id: str, title: str, body: str) -> str:
    """Generate a ready-to-paste Discord @mention for #bot-sync."""
    bot_id = BOT_IDS.get(recipient, "???")
    short_body = body[:100] + ("..." if len(body) > 100 else "")
    return f"<@{bot_id}> [{msg_id}] {title}: {short_body}"


def cmd_send(args: argparse.Namespace) -> int:
    if args.sync:
        _git_pull(quiet=True)

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

    if args.sync:
        _git_push(out["id"], "send")

    # Print Discord @mention for agent to forward
    mention = _discord_mention(args.receiver, out["id"], args.title, args.body)
    print(f"\n💬 Discord @mention (paste to #bot-sync):\n{mention}", file=sys.stderr)

    return 0


def cmd_list(args: argparse.Namespace) -> int:
    if args.sync:
        _git_pull(quiet=True)

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


def _update_with_sync(msg_id: str, updates: dict, action: str, sync: bool) -> int:
    if sync:
        _git_pull(quiet=True)

    out = store.update(msg_id, updates)
    if out is None:
        print(f"ERROR: {msg_id} not found", file=sys.stderr)
        return 1
    print(json.dumps(out, ensure_ascii=False))

    if sync:
        _git_push(msg_id, action)

    return 0


def cmd_ack(args: argparse.Namespace) -> int:
    return _update_with_sync(args.id, {"status": "acked", "acked_at": now_iso()}, "ack", args.sync)


def cmd_done(args: argparse.Namespace) -> int:
    return _update_with_sync(args.id, {"status": "done", "done_at": now_iso()}, "done", args.sync)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Git-synced mailbox for Lab↔Mac")
    p.add_argument("--no-sync", dest="sync", action="store_false", default=True,
                    help="Skip automatic git pull/push")
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
