#!/usr/bin/env python3
"""Cross-bot durable mailbox (Git-synced fallback channel).

All commands auto-sync git (pull other branch before read, push after write).
Use --no-sync to skip git operations.

Usage:
  # Send (auto: write + git push)
  python3 mailbox.py send --from bot-a --to bot-b --title "..." --body "..."

  # List open items for me (auto: git pull other branch first)
  python3 mailbox.py list --to bot-b --status open

  # Ack (auto: git pull + update + git push)
  python3 mailbox.py ack MB-003

  # Done (auto: git pull + update + git push)
  python3 mailbox.py done MB-003

Configuration:
  Edit BOT_NAMES and BRANCH_MAP below to match your setup.
  Set DISCORD_BOT_SYNC_CHANNEL to your bot-sync channel ID.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "shared"))
from jsonl_store import JsonlStore, find_workspace

WORKSPACE = find_workspace()
MAILBOX_REL = "memory/mailbox/messages.jsonl"
store = JsonlStore(MAILBOX_REL, prefix="MB")

# ── Configure these for your setup ──────────────────────────────────────
BOT_NAMES = ["bot-a", "bot-b"]  # Names of your two bots

# Branch mapping: my branch → other branch
BRANCH_MAP = {
    "bot-a": "bot-b",
    "bot-b": "bot-a",
}

# Discord channel for bot-to-bot notifications (optional)
BOT_SYNC_CHANNEL = os.environ.get('OPENCLAW_DISCORD_CHANNEL', '{{CHANNEL_BOT_SYNC}}')
# ────────────────────────────────────────────────────────────────────────


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


def _git_sync(action: str = "pull", quiet: bool = False) -> bool:
    """Fetch/push with the other branch."""
    other = _other_branch()
    if not other:
        if not quiet:
            print("⚠️  Cannot determine other branch, skipping git sync", file=sys.stderr)
        return False
    try:
        if action == "pull":
            subprocess.run(["git", "fetch", "origin", other], cwd=WORKSPACE, capture_output=True, timeout=15)
            result = subprocess.run(["git", "merge", f"origin/{other}", "--no-edit"], cwd=WORKSPACE, capture_output=True, text=True, timeout=15)
            return result.returncode == 0
        elif action == "push":
            result = subprocess.run(["git", "add", "-A"], cwd=WORKSPACE, capture_output=True, timeout=10)
            result = subprocess.run(["git", "commit", "-m", "mailbox: sync message"], cwd=WORKSPACE, capture_output=True, timeout=10)
            result = subprocess.run(["git", "push", "origin", _current_branch()], cwd=WORKSPACE, capture_output=True, timeout=30)
            return result.returncode == 0
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        if not quiet:
            print(f"⚠️  Git {action} failed: {e}", file=sys.stderr)
        return False


def cmd_send(args):
    """Send a message to the other bot."""
    if args.sync:
        _git_sync("pull", quiet=True)

    msg = {
        "from": args.from_bot,
        "to": args.to_bot,
        "title": args.title,
        "body": args.body,
        "sent_at": now_iso(),
        "status": "open",
        "urgent": args.urgent,
    }
    if args.task_id:
        msg["task_id"] = args.task_id

    result = store.append(msg)
    print(f"✅ Sent {result['id']}: {args.title}")

    if args.sync:
        _git_sync("push", quiet=True)
        print(f"   📤 Pushed to git")

    print(f"\n💬 Notify other bot in #bot-sync: @bot mention + {result['id']}")


def cmd_list(args):
    """List messages."""
    if args.sync:
        _git_sync("pull", quiet=True)

    msgs = store.load()
    if args.to_bot:
        msgs = [m for m in msgs if m.get("to") == args.to_bot]
    if args.status:
        msgs = [m for m in msgs if m.get("status") == args.status]
    if args.from_bot:
        msgs = [m for m in msgs if m.get("from") == args.from_bot]

    if args.json:
        print(json.dumps(msgs, ensure_ascii=False, indent=2))
        return

    if not msgs:
        print("No messages matching criteria.")
        return

    print(f"{'ID':>6} {'FROM':>6} {'STATUS':>8} {'URGENT':>6}  TITLE")
    print("-" * 60)
    for m in msgs:
        urgent = "🚨" if m.get("urgent") else "  "
        print(f"{m.get('id','?'):>6} {m.get('from','?'):>6} {m.get('status','?'):>8} {urgent}  {m.get('title','?')}")


def cmd_ack(args):
    """Acknowledge a message (mark as seen)."""
    if args.sync:
        _git_sync("pull", quiet=True)

    msg = store.find(args.msg_id)
    if not msg:
        print(f"❌ {args.msg_id} not found", file=sys.stderr)
        sys.exit(1)

    store.update(args.msg_id, {"status": "acked", "acked_at": now_iso()})
    print(f"✅ {args.msg_id} acknowledged")

    if args.sync:
        _git_sync("push", quiet=True)


def cmd_done(args):
    """Mark a message as done."""
    if args.sync:
        _git_sync("pull", quiet=True)

    msg = store.find(args.msg_id)
    if not msg:
        print(f"❌ {args.msg_id} not found", file=sys.stderr)
        sys.exit(1)

    store.update(args.msg_id, {"status": "done", "done_at": now_iso()})
    print(f"✅ {args.msg_id} marked done")

    if args.sync:
        _git_sync("push", quiet=True)


def main():
    parser = argparse.ArgumentParser(description="Cross-bot mailbox")
    parser.add_argument("--no-sync", dest="sync", action="store_false", default=True,
                        help="Skip git sync operations")
    sub = parser.add_subparsers(dest="command", required=True)

    p_send = sub.add_parser("send", help="Send a message")
    p_send.add_argument("--from", dest="from_bot", required=True, choices=BOT_NAMES)
    p_send.add_argument("--to", dest="to_bot", required=True, choices=BOT_NAMES)
    p_send.add_argument("--title", required=True)
    p_send.add_argument("--body", default="")
    p_send.add_argument("--task-id", default="")
    p_send.add_argument("--urgent", action="store_true")

    p_list = sub.add_parser("list", help="List messages")
    p_list.add_argument("--to", dest="to_bot")
    p_list.add_argument("--from", dest="from_bot")
    p_list.add_argument("--status", choices=["open", "acked", "done"])
    p_list.add_argument("--json", action="store_true")

    p_ack = sub.add_parser("ack", help="Acknowledge a message")
    p_ack.add_argument("msg_id")

    p_done = sub.add_parser("done", help="Mark a message as done")
    p_done.add_argument("msg_id")

    args = parser.parse_args()
    {
        "send": cmd_send,
        "list": cmd_list,
        "ack": cmd_ack,
        "done": cmd_done,
    }[args.command](args)


if __name__ == "__main__":
    main()
