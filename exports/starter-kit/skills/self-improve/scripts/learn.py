#!/usr/bin/env python3
"""Self-improvement CLI — log learnings/errors, search for patterns, review, promote.

Usage:
    python3 learn.py log -c correction -p high -s "summary" [-d "details"] [-a "action"] [-k "pattern.key"] [--force]
    python3 learn.py error -s "summary" -e "error msg" [-f "fix"] [--prevention "..."] [-k "pattern.key"]
    python3 learn.py resolve <ID> [-n "resolution notes"]
    python3 learn.py search "keyword"
    python3 learn.py review [--promote-ready] [--json]
    python3 learn.py promote <ID> --to TOOLS.md
    python3 learn.py stats [--json]
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
    seen_ids = set()
    for item in items:
        item_id = item.get("id", "")
        if pattern_key and item.get("pattern_key") == pattern_key:
            if item_id not in seen_ids:
                matches.append(item)
                seen_ids.add(item_id)
            continue
        if similarity(item.get("summary", ""), summary) >= threshold:
            if item_id not in seen_ids:
                matches.append(item)
                seen_ids.add(item_id)
    return matches


def cmd_log(args):
    """Log a learning entry."""
    store = JsonlStore(LEARNINGS_PATH, prefix="LRN")

    if not args.force:
        similar = find_similar(store, args.summary, args.pattern_key or None)
        if similar:
            best = similar[0]
            new_recurrence = best.get("recurrence", 1) + 1
            updates = {"recurrence": new_recurrence, "last_seen": today()}
            if args.details:
                updates["details"] = args.details
            if args.action:
                updates["action"] = args.action
            store.update(best["id"], updates)
            print(f"🔁 Bumped recurrence on {best['id']}: \"{best['summary']}\" (now {new_recurrence}x)")
            if new_recurrence >= PROMOTION_THRESHOLD:
                print(f"   ⚡ PROMOTION READY — recurrence >= {PROMOTION_THRESHOLD}. Run: learn.py promote {best['id']} --to <target>")
            return

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

    if not args.force:
        similar = find_similar(store, args.summary, args.pattern_key or None)
        if similar:
            best = similar[0]
            new_recurrence = best.get("recurrence", 1) + 1
            updates = {"recurrence": new_recurrence, "last_seen": today()}
            if args.fix:
                updates["fix"] = args.fix
                updates["status"] = "resolved"
            if args.prevention:
                updates["prevention"] = args.prevention
            store.update(best["id"], updates)
            print(f"🔁 Bumped recurrence on {best['id']}: \"{best['summary']}\" (now {new_recurrence}x)")
            return

    entry = {
        "date": today(),
        "status": "resolved" if args.fix else "pending",
        "summary": args.summary,
        "error": args.error or "",
        "fix": args.fix or "",
        "prevention": args.prevention or "",
        "pattern_key": args.pattern_key or "",
        "recurrence": 1,
        "first_seen": today(),
        "last_seen": today(),
        "see_also": [],
    }
    result = store.append(entry)
    status = "resolved" if args.fix else "pending"
    print(f"✅ Logged {result['id']} ({status}): {args.summary}")


def cmd_resolve(args):
    entry_id = args.entry_id.upper()
    if entry_id.startswith("LRN"):
        store = JsonlStore(LEARNINGS_PATH, prefix="LRN")
    elif entry_id.startswith("ERR"):
        store = JsonlStore(ERRORS_PATH, prefix="ERR")
    else:
        print(f"❌ Unknown ID prefix: {entry_id}. Expected LRN-xxx or ERR-xxx", file=sys.stderr)
        sys.exit(1)

    item = store.find(entry_id)
    if not item:
        print(f"❌ {entry_id} not found", file=sys.stderr)
        sys.exit(1)

    if item.get("status") == "resolved":
        print(f"⚠️  {entry_id} is already resolved")
        return

    updates = {"status": "resolved", "last_seen": today()}
    if args.notes:
        updates["fix" if entry_id.startswith("ERR") else "action"] = args.notes
    store.update(entry_id, updates)
    print(f"✅ {entry_id} marked as resolved")


def cmd_search(args):
    keyword = args.keyword.lower()
    results = []
    for store in [JsonlStore(LEARNINGS_PATH, prefix="LRN"), JsonlStore(ERRORS_PATH, prefix="ERR")]:
        for item in store.load():
            if keyword in " ".join(str(v) for v in item.values()).lower():
                results.append(item)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    if not results:
        print(f"No results for \"{args.keyword}\"")
        return

    print(f"Found {len(results)} result(s) for \"{args.keyword}\":\n")
    for item in results:
        rec = item.get("recurrence", 1)
        print(f"  [{item.get('id','?')}] {item.get('status',''):>8} {item.get('summary','')}" + (f" (x{rec})" if rec > 1 else ""))


def cmd_review(args):
    lrn_store = JsonlStore(LEARNINGS_PATH, prefix="LRN")
    err_store = JsonlStore(ERRORS_PATH, prefix="ERR")
    learnings = lrn_store.load()
    errors = err_store.load()

    if args.json:
        pending_lrn = [i for i in learnings if i.get("status") == "pending"]
        pending_err = [i for i in errors if i.get("status") == "pending"]
        candidates = [i for i in learnings if i.get("recurrence", 1) >= PROMOTION_THRESHOLD and i.get("status") != "promoted"]
        print(json.dumps({
            "pending_learnings": len(pending_lrn),
            "pending_errors": len(pending_err),
            "promote_ready": len(candidates),
            "promote_candidates": [{"id": i["id"], "summary": i["summary"], "recurrence": i.get("recurrence", 1)} for i in candidates],
        }, ensure_ascii=False, indent=2))
        return

    if args.promote_ready:
        candidates = [i for i in learnings if i.get("recurrence", 1) >= PROMOTION_THRESHOLD and i.get("status") != "promoted"]
        if not candidates:
            print("No learnings ready for promotion.")
            return
        print(f"⚡ {len(candidates)} learning(s) ready for promotion:\n")
        for item in candidates:
            print(f"  [{item['id']}] x{item['recurrence']} | {item['summary']}")
        return

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
    entry_id = args.entry_id.upper()
    if entry_id.startswith("LRN"):
        store = JsonlStore(LEARNINGS_PATH, prefix="LRN")
    elif entry_id.startswith("ERR"):
        store = JsonlStore(ERRORS_PATH, prefix="ERR")
    else:
        print(f"❌ Unknown ID prefix. Expected LRN-xxx or ERR-xxx", file=sys.stderr)
        sys.exit(1)

    item = store.find(entry_id)
    if not item:
        print(f"❌ {entry_id} not found", file=sys.stderr)
        sys.exit(1)

    valid_targets = ("AGENTS.md", "SOUL.md", "TOOLS.md", "MEMORY.md", "PROACTIVE.md", "HEARTBEAT.md", "SESSION-STATE.md")
    if args.to not in valid_targets:
        print(f"❌ Invalid target. Choose from: {', '.join(valid_targets)}", file=sys.stderr)
        sys.exit(1)

    store.update(entry_id, {"status": "promoted", "promoted_to": args.to})
    summary = item.get("summary", "")
    action = item.get("prevention", "") or item.get("fix", "") or item.get("action", "") or item.get("details", "")
    print(f"✅ {entry_id} marked as promoted → {args.to}")
    print(f"\n📋 Add this to {args.to}:")
    print(f"---")
    print(f"- **{summary}** — {action}")
    print(f"---")


def cmd_stats(args):
    lrn_store = JsonlStore(LEARNINGS_PATH, prefix="LRN")
    err_store = JsonlStore(ERRORS_PATH, prefix="ERR")
    learnings = lrn_store.load()
    errors = err_store.load()

    lrn_by_status = {}
    for i in learnings:
        s = i.get("status", "unknown")
        lrn_by_status[s] = lrn_by_status.get(s, 0) + 1

    err_by_status = {}
    for i in errors:
        s = i.get("status", "unknown")
        err_by_status[s] = err_by_status.get(s, 0) + 1

    promote_ready = sum(1 for i in learnings if i.get("recurrence", 1) >= PROMOTION_THRESHOLD and i.get("status") != "promoted")

    if args.json:
        print(json.dumps({"learnings": {"total": len(learnings), "by_status": lrn_by_status}, "errors": {"total": len(errors), "by_status": err_by_status}, "promote_ready": promote_ready}, ensure_ascii=False, indent=2))
        return

    lrn_parts = ", ".join(f"{v} {k}" for k, v in sorted(lrn_by_status.items()))
    err_parts = ", ".join(f"{v} {k}" for k, v in sorted(err_by_status.items()))
    print(f"📊 Self-Improvement Stats")
    print(f"  Learnings: {len(learnings)} total ({lrn_parts})")
    print(f"  Errors:    {len(errors)} total ({err_parts})")
    if promote_ready:
        print(f"  ⚡ {promote_ready} learning(s) ready for promotion")


def main():
    parser = argparse.ArgumentParser(description="Self-improvement CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_log = sub.add_parser("log", help="Log a learning")
    p_log.add_argument("-c", "--category", required=True, choices=VALID_CATEGORIES)
    p_log.add_argument("-p", "--priority", default="medium", choices=VALID_PRIORITIES)
    p_log.add_argument("-s", "--summary", required=True)
    p_log.add_argument("-d", "--details", default="")
    p_log.add_argument("-a", "--action", default="")
    p_log.add_argument("-k", "--pattern-key", default="")
    p_log.add_argument("--force", action="store_true")

    p_err = sub.add_parser("error", help="Log an error")
    p_err.add_argument("-s", "--summary", required=True)
    p_err.add_argument("-e", "--error", default="")
    p_err.add_argument("-f", "--fix", default="")
    p_err.add_argument("--prevention", default="")
    p_err.add_argument("-k", "--pattern-key", default="")
    p_err.add_argument("--force", action="store_true")

    p_resolve = sub.add_parser("resolve", help="Mark resolved")
    p_resolve.add_argument("entry_id")
    p_resolve.add_argument("-n", "--notes", default="")

    p_search = sub.add_parser("search", help="Search entries")
    p_search.add_argument("keyword")
    p_search.add_argument("--json", action="store_true")

    p_review = sub.add_parser("review", help="Review pending items")
    p_review.add_argument("--promote-ready", action="store_true")
    p_review.add_argument("--json", action="store_true")

    p_promote = sub.add_parser("promote", help="Mark as promoted")
    p_promote.add_argument("entry_id")
    p_promote.add_argument("--to", required=True)

    p_stats = sub.add_parser("stats", help="Show stats")
    p_stats.add_argument("--json", action="store_true")

    args = parser.parse_args()
    {
        "log": cmd_log,
        "error": cmd_error,
        "resolve": cmd_resolve,
        "search": cmd_search,
        "review": cmd_review,
        "promote": cmd_promote,
        "stats": cmd_stats,
    }[args.command](args)


if __name__ == "__main__":
    main()
