#!/usr/bin/env python3
"""AMA (Ask Me Anything) — track knowledge-gap questions and answers."""

import argparse
import json
import os
import sys
import textwrap
from datetime import datetime, timezone, timedelta

# ── paths ──
WORKSPACE = os.environ.get(
    "OPENCLAW_WORKSPACE",
    os.path.join(os.path.expanduser("~"), ".openclaw", "workspace"),
)
DATA_DIR = os.path.join(WORKSPACE, "memory", "ama")
QUESTIONS_FILE = os.path.join(DATA_DIR, "questions.jsonl")

TZ = timezone(timedelta(hours=8))  # Asia/Taipei


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _load() -> list[dict]:
    if not os.path.exists(QUESTIONS_FILE):
        return []
    rows = []
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _save(rows: list[dict]):
    _ensure_dir()
    import tempfile

    fd, tmp = tempfile.mkstemp(dir=DATA_DIR, suffix=".jsonl")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        os.replace(tmp, QUESTIONS_FILE)
    except Exception:
        os.unlink(tmp)
        raise


def _next_id(rows: list[dict]) -> str:
    max_n = 0
    for r in rows:
        qid = r.get("id", "")
        if qid.startswith("Q-"):
            try:
                n = int(qid[2:])
                max_n = max(max_n, n)
            except ValueError:
                pass
    return f"Q-{max_n + 1:03d}"


def _now() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M")


def _priority_emoji(p: int) -> str:
    return {1: "🔴", 2: "🟡", 3: "🟢"}.get(p, "⚪")


# ── commands ──


def cmd_ask(args):
    rows = _load()
    qid = _next_id(rows)
    entry = {
        "id": qid,
        "question": args.question,
        "context": args.context or "",
        "task": args.task or "",
        "priority": args.priority,
        "status": "open",
        "asked_at": _now(),
        "answer": "",
        "answered_at": "",
    }
    rows.append(entry)
    _save(rows)

    emoji = _priority_emoji(args.priority)
    plabel = {1: "P1 Blocking", 2: "P2 Important", 3: "P3 Nice-to-have"}[args.priority]

    # Build suggested search prompt
    search_prompt = args.question
    if args.context:
        search_prompt += f"\n\n背景：{args.context}"

    print(f"✅ Saved as {qid}")
    print()
    print(f"🔍 AMA [{plabel}] {emoji} — {qid}")
    print()
    print(f"❓ {args.question}")
    if args.context:
        print(f"\n📋 背景：{args.context}")
    if args.task:
        print(f"🔗 任務：{args.task}")
    print()
    print("💡 建議搜索 prompt（可直接貼到 GPT-5.2 PRO）：")
    print("```")
    print(search_prompt)
    print("```")


def cmd_answer(args):
    rows = _load()
    found = False
    for r in rows:
        if r["id"] == args.question_id:
            r["answer"] = args.answer
            r["status"] = "answered"
            r["answered_at"] = _now()
            found = True
            break
    if not found:
        print(f"❌ Question {args.question_id} not found", file=sys.stderr)
        sys.exit(1)
    _save(rows)
    print(f"✅ {args.question_id} marked as answered")


def cmd_list(args):
    rows = _load()
    if args.status != "all":
        rows = [r for r in rows if r["status"] == args.status]
    if args.priority:
        rows = [r for r in rows if r["priority"] == args.priority]
    if not rows:
        print("（沒有符合條件的問題）")
        return
    for r in rows:
        emoji = _priority_emoji(r["priority"])
        status = "✅" if r["status"] == "answered" else "❓"
        task = f" [{r['task']}]" if r.get("task") else ""
        print(f"{status} {r['id']} {emoji} P{r['priority']}{task} — {r['question'][:80]}")
        if r["status"] == "answered" and r.get("answer"):
            print(f"   → {r['answer'][:100]}")


def cmd_search(args):
    rows = _load()
    kw = args.keyword.lower()
    hits = [
        r
        for r in rows
        if kw in r.get("question", "").lower()
        or kw in r.get("answer", "").lower()
        or kw in r.get("context", "").lower()
    ]
    if not hits:
        print(f"（找不到包含 '{args.keyword}' 的問題）")
        return
    for r in hits:
        emoji = _priority_emoji(r["priority"])
        status = "✅" if r["status"] == "answered" else "❓"
        print(f"{status} {r['id']} {emoji} — {r['question'][:80]}")
        if r.get("answer"):
            print(f"   → {r['answer'][:100]}")


def cmd_stats(args):
    rows = _load()
    total = len(rows)
    answered = sum(1 for r in rows if r["status"] == "answered")
    by_priority = {}
    for r in rows:
        p = r["priority"]
        by_priority.setdefault(p, {"total": 0, "open": 0})
        by_priority[p]["total"] += 1
        if r["status"] == "open":
            by_priority[p]["open"] += 1

    print(f"📊 AMA Stats")
    print(f"   Total: {total} | Answered: {answered} | Open: {total - answered}")
    for p in sorted(by_priority):
        d = by_priority[p]
        emoji = _priority_emoji(p)
        print(f"   {emoji} P{p}: {d['total']} total, {d['open']} open")


# ── main ──


def main():
    parser = argparse.ArgumentParser(description="AMA question tracker")
    sub = parser.add_subparsers(dest="cmd")

    # ask
    p_ask = sub.add_parser("ask", help="Record a new question")
    p_ask.add_argument("question", help="The question to ask")
    p_ask.add_argument("--context", "-c", help="Why you need this")
    p_ask.add_argument("--task", "-t", help="Related task ID (e.g. L-08)")
    p_ask.add_argument("--priority", "-p", type=int, default=2, choices=[1, 2, 3])

    # answer
    p_ans = sub.add_parser("answer", help="Record an answer")
    p_ans.add_argument("question_id", help="Question ID (e.g. Q-001)")
    p_ans.add_argument("answer", help="The answer summary")

    # list
    p_list = sub.add_parser("list", help="List questions")
    p_list.add_argument("--status", "-s", default="open", choices=["open", "answered", "all"])
    p_list.add_argument("--priority", "-p", type=int, choices=[1, 2, 3])

    # search
    p_search = sub.add_parser("search", help="Search Q&A")
    p_search.add_argument("keyword")

    # stats
    sub.add_parser("stats", help="Show stats")

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    {"ask": cmd_ask, "answer": cmd_answer, "list": cmd_list, "search": cmd_search, "stats": cmd_stats}[args.cmd](args)


if __name__ == "__main__":
    main()
