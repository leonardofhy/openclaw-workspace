#!/usr/bin/env python3
"""Self-improvement CLI — log learnings/errors, search for patterns, review, promote.

Usage:
    python3 learn.py log -c correction -p high -s "summary" [-d "details"] [-a "action"] [-k "pattern.key"]
    python3 learn.py error -s "summary" -e "error msg" [-f "fix"] [--prevention "how to avoid"]
    python3 learn.py search "keyword"
    python3 learn.py review [--promote-ready]
    python3 learn.py promote LRN-003 --to TOOLS.md
    python3 learn.py stats
    python3 learn.py migrate-known-issues
"""

import argparse
import json
import sys
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

# --- Bootstrap: find workspace and import JsonlStore ---
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from shared.jsonl_store import JsonlStore, find_workspace

WORKSPACE = find_workspace()
LEARNINGS_PATH = "memory/learnings/learnings.jsonl"
ERRORS_PATH = "memory/learnings/errors.jsonl"

VALID_CATEGORIES = ("correction", "knowledge_gap", "best_practice", "gotcha")
VALID_PRIORITIES = ("low", "medium", "high", "critical")
VALID_STATUSES = ("pending", "resolved", "promoted", "wont_fix")
PROMOTION_THRESHOLD = 3


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def similarity(a: str, b: str) -> float:
    """Quick string similarity ratio (0-1)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_similar(store: JsonlStore, summary: str, pattern_key: str | None = None,
                 threshold: float = 0.6) -> list[dict]:
    """Find existing entries similar to the given summary or matching pattern_key."""
    items = store.load()
    matches = []
    for item in items:
        # Exact pattern_key match is strongest signal
        if pattern_key and item.get("pattern_key") == pattern_key:
            matches.append(item)
            continue
        # Fuzzy summary match
        if similarity(item.get("summary", ""), summary) >= threshold:
            matches.append(item)
    return matches


# ── Commands ──────────────────────────────────────────────

def cmd_log(args):
    """Log a learning entry."""
    store = JsonlStore(LEARNINGS_PATH, prefix="LRN")

    # Check for similar existing entries
    similar = find_similar(store, args.summary, args.pattern_key)
    if similar:
        # Bump recurrence on best match
        best = similar[0]
        new_recurrence = best.get("recurrence", 1) + 1
        store.update(best["id"], {
            "recurrence": new_recurrence,
            "last_seen": today(),
            "details": args.details or best.get("details", ""),
        })
        print(f"🔁 Bumped recurrence on {best['id']}: \"{best['summary']}\" (now {new_recurrence}x)")
        if new_recurrence >= PROMOTION_THRESHOLD:
            print(f"   ⚡ PROMOTION READY — recurrence >= {PROMOTION_THRESHOLD}. Run: learn.py promote {best['id']} --to <target>")
        return

    # New entry
    entry = {
        "date": today(),
        "category": args.category,
        "priority": args.priority,
        "status": "pending",
        "summary": args.summary,
        "details": args.details or "",
        "action": args.action or "",
        "pattern_key": args.pattern_key or "",
        "recurrence": 1,
        "first_seen": today(),
        "last_seen": today(),
        "see_also": [],
        "promoted_to": None,
    }
    result = store.append(entry)
    print(f"✅ Logged {result['id']}: {args.summary}")


def cmd_error(args):
    """Log an error entry."""
    store = JsonlStore(ERRORS_PATH, prefix="ERR")

    # Check for similar existing errors
    similar = find_similar(store, args.summary)
    if similar:
        best = similar[0]
        new_recurrence = best.get("recurrence", 1) + 1
        store.update(best["id"], {
            "recurrence": new_recurrence,
            "last_seen": today(),
        })
        print(f"🔁 Bumped recurrence on {best['id']}: \"{best['summary']}\" (now {new_recurrence}x)")
        return

    entry = {
        "date": today(),
        "status": "pending" if not args.fix else "resolved",
        "summary": args.summary,
        "error": args.error or "",
        "fix": args.fix or "",
        "prevention": args.prevention or "",
        "recurrence": 1,
        "first_seen": today(),
        "last_seen": today(),
        "see_also": [],
    }
    result = store.append(entry)
    status = "resolved" if args.fix else "pending"
    print(f"✅ Logged {result['id']} ({status}): {args.summary}")


def cmd_search(args):
    """Search learnings and errors for a keyword."""
    keyword = args.keyword.lower()
    lrn_store = JsonlStore(LEARNINGS_PATH, prefix="LRN")
    err_store = JsonlStore(ERRORS_PATH, prefix="ERR")

    results = []
    for item in lrn_store.load():
        searchable = " ".join(str(v) for v in item.values()).lower()
        if keyword in searchable:
            results.append(item)
    for item in err_store.load():
        searchable = " ".join(str(v) for v in item.values()).lower()
        if keyword in searchable:
            results.append(item)

    if not results:
        print(f"No results for \"{args.keyword}\"")
        return

    print(f"Found {len(results)} result(s) for \"{args.keyword}\":\n")
    for item in results:
        _id = item.get("id", "?")
        summary = item.get("summary", "")
        status = item.get("status", "")
        recurrence = item.get("recurrence", 1)
        rec_str = f" (x{recurrence})" if recurrence > 1 else ""
        print(f"  [{_id}] {status:>8} {summary}{rec_str}")


def cmd_review(args):
    """Review pending items. --promote-ready shows only items ready for promotion."""
    lrn_store = JsonlStore(LEARNINGS_PATH, prefix="LRN")
    err_store = JsonlStore(ERRORS_PATH, prefix="ERR")

    learnings = lrn_store.load()
    errors = err_store.load()

    if args.promote_ready:
        candidates = [i for i in learnings
                      if i.get("recurrence", 1) >= PROMOTION_THRESHOLD
                      and i.get("status") != "promoted"]
        if not candidates:
            print("No learnings ready for promotion.")
            return
        print(f"⚡ {len(candidates)} learning(s) ready for promotion (recurrence >= {PROMOTION_THRESHOLD}):\n")
        for item in candidates:
            print(f"  [{item['id']}] x{item['recurrence']} | {item['summary']}")
            if item.get("action"):
                print(f"           Action: {item['action']}")
        return

    # Show all pending
    pending_lrn = [i for i in learnings if i.get("status") == "pending"]
    pending_err = [i for i in errors if i.get("status") == "pending"]

    if not pending_lrn and not pending_err:
        print("✅ No pending items. All clear.")
        return

    if pending_lrn:
        print(f"📝 Pending learnings ({len(pending_lrn)}):")
        for item in pending_lrn:
            rec = item.get("recurrence", 1)
            flag = " ⚡PROMOTE" if rec >= PROMOTION_THRESHOLD else ""
            print(f"  [{item['id']}] {item.get('priority', '?'):>8} | x{rec}{flag} | {item['summary']}")

    if pending_err:
        print(f"\n🐛 Pending errors ({len(pending_err)}):")
        for item in pending_err:
            print(f"  [{item['id']}] {item['summary']}")


def cmd_promote(args):
    """Mark a learning as promoted and show what to add to target file."""
    store = JsonlStore(LEARNINGS_PATH, prefix="LRN")
    item = store.find(args.entry_id)
    if not item:
        print(f"❌ {args.entry_id} not found", file=sys.stderr)
        sys.exit(1)

    if item.get("status") == "promoted":
        print(f"⚠️  {args.entry_id} already promoted to {item.get('promoted_to')}")
        return

    target = args.to
    valid_targets = ("AGENTS.md", "SOUL.md", "TOOLS.md", "MEMORY.md",
                     "PROACTIVE.md", "HEARTBEAT.md")
    if target not in valid_targets:
        print(f"❌ Invalid target. Choose from: {', '.join(valid_targets)}", file=sys.stderr)
        sys.exit(1)

    # Update status
    store.update(args.entry_id, {
        "status": "promoted",
        "promoted_to": target,
    })

    # Show what to add
    print(f"✅ {args.entry_id} marked as promoted → {target}")
    print(f"\n📋 Add this to {target}:")
    print(f"---")
    summary = item.get("summary", "")
    action = item.get("action", "")
    if action:
        print(f"- **{summary}** — {action}")
    else:
        print(f"- **{summary}** — {item.get('details', '')}")
    print(f"---")
    print(f"\n(Manually add the above to {target}, then commit.)")


def cmd_stats(args):
    """Show stats overview."""
    lrn_store = JsonlStore(LEARNINGS_PATH, prefix="LRN")
    err_store = JsonlStore(ERRORS_PATH, prefix="ERR")

    learnings = lrn_store.load()
    errors = err_store.load()

    lrn_pending = sum(1 for i in learnings if i.get("status") == "pending")
    lrn_resolved = sum(1 for i in learnings if i.get("status") == "resolved")
    lrn_promoted = sum(1 for i in learnings if i.get("status") == "promoted")
    err_pending = sum(1 for i in errors if i.get("status") == "pending")
    err_resolved = sum(1 for i in errors if i.get("status") == "resolved")
    promote_ready = sum(1 for i in learnings
                        if i.get("recurrence", 1) >= PROMOTION_THRESHOLD
                        and i.get("status") != "promoted")

    print(f"📊 Self-Improvement Stats")
    print(f"  Learnings: {len(learnings)} total ({lrn_pending} pending, {lrn_resolved} resolved, {lrn_promoted} promoted)")
    print(f"  Errors:    {len(errors)} total ({err_pending} pending, {err_resolved} resolved)")
    if promote_ready:
        print(f"  ⚡ {promote_ready} learning(s) ready for promotion")


def cmd_migrate(args):
    """Migrate existing known-issues.md entries to errors.jsonl."""
    store = JsonlStore(ERRORS_PATH, prefix="ERR")
    existing = store.load()
    if existing:
        print(f"⚠️  errors.jsonl already has {len(existing)} entries. Skipping migration to avoid duplicates.")
        print(f"   To force: delete errors.jsonl first.")
        return

    # Hardcoded migration from the 4 known entries in known-issues.md
    entries = [
        {
            "date": "2026-02-27",
            "status": "resolved",
            "summary": "openclaw.json direct edit cleared by validation",
            "error": "Manually added 'guilds' key disappears after gateway restart",
            "fix": "Use `openclaw config set channels.discord.groupPolicy open`",
            "prevention": "Always use `openclaw config set`, never edit openclaw.json directly",
            "recurrence": 1, "first_seen": "2026-02-27", "last_seen": "2026-02-27",
            "see_also": [],
        },
        {
            "date": "2026-02-27",
            "status": "resolved",
            "summary": "WORKSPACE path wrong — parent level count off by one",
            "error": "task-board.md not found, experiments.jsonl written to wrong location",
            "fix": "Use `find_workspace()` (git rev-parse) instead of fragile `.parent` chains",
            "prevention": "New scripts: always use shared.jsonl_store.find_workspace() or verify path with print",
            "recurrence": 2, "first_seen": "2026-02-27", "last_seen": "2026-02-27",
            "see_also": [],
        },
        {
            "date": "2026-02-27",
            "status": "resolved",
            "summary": "rm -rf skills/memory deleted entire skill directory",
            "error": "skills/memory/SKILL.md and fetch_latest_diary.py gone",
            "fix": "Restored from git: `git show HEAD~1:path > file`",
            "prevention": "`ls` before `rm -rf`; target specific subdirectory not parent; use `trash` over `rm`",
            "recurrence": 1, "first_seen": "2026-02-27", "last_seen": "2026-02-27",
            "see_also": [],
        },
        {
            "date": "2026-02-27",
            "status": "resolved",
            "summary": "Gateway restart from inside session kills own connection",
            "error": "exec command timeout or disconnect when restarting gateway",
            "fix": "`nohup bash -c 'sleep 2 && systemctl --user restart openclaw-gateway' &`",
            "prevention": "Use nohup for gateway restart, or ask Leo to run manually",
            "recurrence": 1, "first_seen": "2026-02-27", "last_seen": "2026-02-27",
            "see_also": [],
        },
    ]

    for entry in entries:
        store.append(entry)

    print(f"✅ Migrated {len(entries)} entries from known-issues.md → errors.jsonl")
    print(f"   known-issues.md can now be replaced with a pointer file.")


# ── CLI ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Self-improvement CLI — log, search, review, promote learnings and errors.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # log
    p_log = sub.add_parser("log", help="Log a learning")
    p_log.add_argument("-c", "--category", required=True, choices=VALID_CATEGORIES)
    p_log.add_argument("-p", "--priority", default="medium", choices=VALID_PRIORITIES)
    p_log.add_argument("-s", "--summary", required=True)
    p_log.add_argument("-d", "--details", default="")
    p_log.add_argument("-a", "--action", default="")
    p_log.add_argument("-k", "--pattern-key", default="")

    # error
    p_err = sub.add_parser("error", help="Log an error")
    p_err.add_argument("-s", "--summary", required=True)
    p_err.add_argument("-e", "--error", default="")
    p_err.add_argument("-f", "--fix", default="")
    p_err.add_argument("--prevention", default="")

    # search
    p_search = sub.add_parser("search", help="Search learnings and errors")
    p_search.add_argument("keyword")

    # review
    p_review = sub.add_parser("review", help="Review pending items")
    p_review.add_argument("--promote-ready", action="store_true",
                          help="Show only items ready for promotion")

    # promote
    p_promote = sub.add_parser("promote", help="Mark a learning as promoted")
    p_promote.add_argument("entry_id", help="e.g. LRN-003")
    p_promote.add_argument("--to", required=True, help="Target file (e.g. TOOLS.md)")

    # stats
    sub.add_parser("stats", help="Show stats overview")

    # migrate
    sub.add_parser("migrate-known-issues", help="Migrate known-issues.md to errors.jsonl")

    args = parser.parse_args()
    cmd_map = {
        "log": cmd_log,
        "error": cmd_error,
        "search": cmd_search,
        "review": cmd_review,
        "promote": cmd_promote,
        "stats": cmd_stats,
        "migrate-known-issues": cmd_migrate,
    }
    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
