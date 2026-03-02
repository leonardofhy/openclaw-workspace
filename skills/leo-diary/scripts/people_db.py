#!/usr/bin/env python3
"""Personal Relationship Database — extract, store, query people & interactions.

Data lives in memory/people/:
  - people.jsonl   — person profiles
  - events.jsonl   — interaction events

Usage:
  people_db.py add "智凱" --aliases "智凱哥,凱哥" --rel "labmate, co-1st author" --tags lab,research
  people_db.py log "智凱" --date 2026-02-20 --type meeting --summary "AudioMatters 作者序確認"
  people_db.py show "智凱"                    # full profile + recent events
  people_db.py list                            # all people, sorted by last interaction
  people_db.py scan "智凱" [--start ...] [--end ...]   # scan diary for interactions
  people_db.py import-scan "智凱" --file /tmp/scan.json # import scan results as events
  people_db.py timeline "智凱"                 # chronological event list
  people_db.py update "智凱" --trust 8 --closeness 7 --notes "..."
  people_db.py stats                           # overview stats
"""

import argparse
import json
import sys
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

TZ = timezone(timedelta(hours=8))
WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
PEOPLE_DIR = WORKSPACE / "memory" / "people"
PEOPLE_FILE = PEOPLE_DIR / "people.jsonl"
EVENTS_FILE = PEOPLE_DIR / "events.jsonl"
SEARCH_SCRIPT = WORKSPACE / "skills" / "leo-diary" / "scripts" / "search_diary.py"

# Valid ranges for numeric fields
TRUST_RANGE = (1, 10)
CLOSENESS_RANGE = (1, 10)

# Reuse shared JSONL module
sys.path.insert(0, str(WORKSPACE / "skills" / "shared"))
try:
    from jsonl_store import JsonlStore
    _has_shared = True
except ImportError:
    _has_shared = False

# --- JSONL helpers (fallback if shared module unavailable) ---

def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    items = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return items


def _save_jsonl(path: Path, items: list[dict]):
    """Atomic rewrite via tempfile (matches shared/jsonl_store.py pattern)."""
    import tempfile, os
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(json.dumps(i, ensure_ascii=False) for i in items) + "\n"
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        os.replace(tmp, path)
    except:
        os.close(fd) if not os.get_inheritable(fd) else None
        os.unlink(tmp)
        raise


def _append_jsonl(path: Path, item: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def _next_id(items: list[dict], prefix: str) -> str:
    nums = []
    for i in items:
        id_ = i.get("id", "")
        if id_.startswith(prefix):
            try:
                nums.append(int(id_[len(prefix):]))
            except ValueError:
                pass
    return f"{prefix}{max(nums, default=0) + 1:03d}"


# --- Core functions ---

def find_person(people: list[dict], name: str) -> dict | None:
    """Find person by name or alias (case-insensitive)."""
    name_lower = name.lower()
    for p in people:
        if p.get("name", "").lower() == name_lower:
            return p
        for a in p.get("aliases", []):
            if a.lower() == name_lower:
                return p
    return None


def _validate_range(value: int | None, name: str, lo: int, hi: int) -> int | None:
    """Validate numeric field is in range. Returns value or raises."""
    if value is None:
        return None
    if not (lo <= value <= hi):
        print(f"❌ {name} 必須在 {lo}-{hi} 之間，收到: {value}", file=sys.stderr)
        sys.exit(1)
    return value


def cmd_add(args):
    if not args.name or not args.name.strip():
        print("❌ 名字不能為空", file=sys.stderr)
        sys.exit(1)

    trust = _validate_range(args.trust, "trust", *TRUST_RANGE)
    closeness = _validate_range(args.closeness, "closeness", *CLOSENESS_RANGE)

    people = _load_jsonl(PEOPLE_FILE)
    existing = find_person(people, args.name)
    if existing:
        print(f"⚠️  {args.name} 已存在 (ID: {existing['id']}). 用 update 修改。")
        sys.exit(1)

    aliases = [a.strip() for a in args.aliases.split(",") if a.strip()] if args.aliases else []
    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []
    now = datetime.now(TZ).strftime("%Y-%m-%d")

    person = {
        "id": _next_id(people, "P"),
        "name": args.name.strip(),
        "aliases": aliases,
        "relationship": args.rel or "",
        "context": args.context or "",
        "first_met": args.first_met or "",
        "trust": trust if trust is not None else 5,
        "closeness": closeness if closeness is not None else 5,
        "tags": tags,
        "notes": args.notes or "",
        "next_steps": [],
        "created_at": now,
        "updated_at": now,
    }
    _append_jsonl(PEOPLE_FILE, person)
    print(f"✅ Added {person['id']}: {person['name']}")


def cmd_update(args):
    _validate_range(args.trust, "trust", *TRUST_RANGE)
    _validate_range(args.closeness, "closeness", *CLOSENESS_RANGE)

    people = _load_jsonl(PEOPLE_FILE)
    p = find_person(people, args.name)
    if not p:
        print(f"❌ 找不到: {args.name}", file=sys.stderr)
        sys.exit(1)

    if args.trust is not None:
        p["trust"] = args.trust
    if args.closeness is not None:
        p["closeness"] = args.closeness
    if args.notes:
        p["notes"] = args.notes
    if args.rel:
        p["relationship"] = args.rel
    if args.context:
        p["context"] = args.context
    if args.aliases:
        p["aliases"] = [a.strip() for a in args.aliases.split(",")]
    if args.tags:
        p["tags"] = [t.strip() for t in args.tags.split(",")]
    if args.next_steps:
        p["next_steps"] = [s.strip() for s in args.next_steps.split(";")]
    p["updated_at"] = datetime.now(TZ).strftime("%Y-%m-%d")

    _save_jsonl(PEOPLE_FILE, people)
    print(f"✅ Updated {p['id']}: {p['name']}")


def cmd_log(args):
    people = _load_jsonl(PEOPLE_FILE)
    p = find_person(people, args.name)
    if not p:
        print(f"❌ 找不到: {args.name}. 先用 add 新增。", file=sys.stderr)
        sys.exit(1)

    events = _load_jsonl(EVENTS_FILE)
    now = datetime.now(TZ).strftime("%Y-%m-%d")

    event = {
        "id": _next_id(events, "E"),
        "person_id": p["id"],
        "person_name": p["name"],
        "date": args.date or now,
        "type": args.type or "interaction",
        "summary": args.summary or "",
        "sentiment": args.sentiment or "neutral",
        "tags": [t.strip() for t in args.tags.split(",")] if args.tags else [],
        "source": args.source or "manual",
    }
    _append_jsonl(EVENTS_FILE, event)
    print(f"✅ Logged {event['id']}: {p['name']} / {event['date']} / {event['type']}")


def cmd_show(args):
    people = _load_jsonl(PEOPLE_FILE)
    p = find_person(people, args.name)
    if not p:
        print(f"❌ 找不到: {args.name}", file=sys.stderr)
        sys.exit(1)

    events = _load_jsonl(EVENTS_FILE)
    person_events = sorted(
        [e for e in events if e.get("person_id") == p["id"]],
        key=lambda e: e.get("date", ""),
        reverse=True,
    )

    # Print profile
    print(f"{'='*50}")
    print(f"👤 {p['name']} ({p['id']})")
    if p.get("aliases"):
        print(f"   別名: {', '.join(p['aliases'])}")
    print(f"   關係: {p.get('relationship', '-')}")
    if p.get("context"):
        print(f"   背景: {p['context']}")
    if p.get("first_met"):
        print(f"   初識: {p['first_met']}")
    print(f"   信任: {'█' * p.get('trust', 5)}{'░' * (10 - p.get('trust', 5))} {p.get('trust', 5)}/10")
    print(f"   親近: {'█' * p.get('closeness', 5)}{'░' * (10 - p.get('closeness', 5))} {p.get('closeness', 5)}/10")
    if p.get("tags"):
        print(f"   標籤: {', '.join(p['tags'])}")
    if p.get("notes"):
        print(f"   備註: {p['notes']}")
    if p.get("next_steps"):
        print(f"   下一步:")
        for s in p["next_steps"]:
            print(f"     - {s}")
    print(f"   更新: {p.get('updated_at', '-')}")

    # Recent events
    print(f"\n📅 互動記錄 ({len(person_events)} 筆)")
    limit = args.limit if hasattr(args, 'limit') and args.limit else 10
    for e in person_events[:limit]:
        icon = {"meeting": "🤝", "chat": "💬", "meal": "🍽️", "conflict": "⚡",
                "favor": "🎁", "milestone": "🏆", "work": "💻", "social": "🎉",
                "interaction": "▪️"}.get(e.get("type", ""), "▪️")
        sent = {"positive": "😊", "negative": "😟", "mixed": "🤔", "neutral": ""}.get(
            e.get("sentiment", ""), "")
        print(f"  {icon} {e['date']} [{e.get('type','')}] {e.get('summary','')} {sent}")

    if len(person_events) > limit:
        print(f"  ... 還有 {len(person_events) - limit} 筆")
    print(f"{'='*50}")


def cmd_list(args):
    people = _load_jsonl(PEOPLE_FILE)
    events = _load_jsonl(EVENTS_FILE)

    # Compute last interaction per person
    last_date = {}
    event_count = {}
    for e in events:
        pid = e.get("person_id")
        d = e.get("date", "")
        if pid not in last_date or d > last_date[pid]:
            last_date[pid] = d
        event_count[pid] = event_count.get(pid, 0) + 1

    # Sort by last interaction (recent first), then by name
    def sort_key(p):
        return (last_date.get(p["id"], "0000"), p.get("closeness", 0))

    people_sorted = sorted(people, key=sort_key, reverse=True)

    print(f"👥 共 {len(people)} 人\n")
    for p in people_sorted:
        pid = p["id"]
        last = last_date.get(pid, "-")
        count = event_count.get(pid, 0)
        trust_bar = "█" * p.get("trust", 5)
        close_bar = "█" * p.get("closeness", 5)
        tags = ", ".join(p.get("tags", [])[:3])
        print(f"  {pid} {p['name']:8s} | {p.get('relationship','')[:30]:30s} | "
              f"T:{trust_bar:10s} C:{close_bar:10s} | "
              f"{count:2d} events | last: {last} | {tags}")


def cmd_scan(args):
    """Scan diary for mentions of a person, output structured results."""
    people = _load_jsonl(PEOPLE_FILE)
    p = find_person(people, args.name)

    # Build search terms: name + aliases
    search_terms = [args.name]
    if p and p.get("aliases"):
        search_terms.extend(p["aliases"])

    # Run search_diary.py
    cmd = [
        sys.executable, str(SEARCH_SCRIPT),
        *search_terms,
        "--or", "--json", "--max", str(args.max or 100),
        "--context", str(args.context or 120),
    ]
    if args.start:
        cmd.extend(["--start", args.start])
    if args.end:
        cmd.extend(["--end", args.end])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        print(f"❌ 日記搜尋失敗: {e}", file=sys.stderr)
        return

    results = data.get("results", [])
    if not results:
        print(f"找不到 {args.name} 的日記提及。")
        return

    print(f"📖 找到 {len(results)} 天提及 {args.name}\n")

    # Output structured for review
    scan_output = []
    for r in results:
        entry = {
            "date": r["date"],
            "mood": r.get("mood", ""),
            "energy": r.get("energy", ""),
            "snippets": r.get("snippets", []),
            "diary_length": r.get("diary_length", 0),
        }
        scan_output.append(entry)

        # Print summary
        snippets_preview = r.get("snippets", [""])[0][:100]
        print(f"  📅 {r['date']} (mood:{r.get('mood','-')} energy:{r.get('energy','-')})")
        print(f"     {snippets_preview}...")
        print()

    # Save to temp file for import
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = Path(f"/tmp/scan_{args.name}.json")
    out_path.write_text(json.dumps({
        "person": args.name,
        "person_id": p["id"] if p else None,
        "scan_date": datetime.now(TZ).strftime("%Y-%m-%d"),
        "count": len(scan_output),
        "entries": scan_output,
    }, ensure_ascii=False, indent=2))
    print(f"\n💾 掃描結果存到: {out_path}")
    print(f"   用 LLM 分析後可用 import-scan 匯入事件")


def cmd_import_scan(args):
    """Import events from a scan result file (after LLM review/annotation)."""
    people = _load_jsonl(PEOPLE_FILE)
    p = find_person(people, args.name)
    if not p:
        print(f"❌ 找不到: {args.name}. 先用 add 新增。", file=sys.stderr)
        sys.exit(1)

    scan_path = Path(args.file)
    if not scan_path.exists():
        print(f"❌ 檔案不存在: {args.file}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(scan_path.read_text())
    entries = data.get("entries", [])
    if not entries:
        print("沒有可匯入的條目。")
        return

    events = _load_jsonl(EVENTS_FILE)
    # Dedup by (person_id, date, summary_prefix) — allows multiple events per day
    # but blocks exact re-imports
    existing_keys = set()
    for e in events:
        if e.get("person_id") == p["id"]:
            key = (e["date"], e.get("summary", "")[:40])
            existing_keys.add(key)

    imported = 0
    skipped = 0
    for entry in entries:
        date = entry.get("date", "")

        # Only import entries that have been annotated with summary
        summary = entry.get("summary", "")
        if not summary:
            # Auto-generate minimal summary from first snippet
            snippets = entry.get("snippets", [])
            if snippets:
                summary = snippets[0][:80] + "..."
            else:
                skipped += 1
                continue

        # Check dedup key
        dedup_key = (date, summary[:40])
        if dedup_key in existing_keys:
            skipped += 1
            continue

        event = {
            "id": _next_id(events, "E"),
            "person_id": p["id"],
            "person_name": p["name"],
            "date": date,
            "type": entry.get("type", "interaction"),
            "summary": summary,
            "sentiment": entry.get("sentiment", "neutral"),
            "tags": entry.get("tags", []),
            "source": "diary",
        }
        events.append(event)
        _append_jsonl(EVENTS_FILE, event)
        imported += 1

    print(f"✅ 匯入 {imported} 筆事件，跳過 {skipped} 筆（已存在或無摘要）")


def cmd_timeline(args):
    people = _load_jsonl(PEOPLE_FILE)
    p = find_person(people, args.name)
    if not p:
        print(f"❌ 找不到: {args.name}", file=sys.stderr)
        sys.exit(1)

    events = _load_jsonl(EVENTS_FILE)
    person_events = sorted(
        [e for e in events if e.get("person_id") == p["id"]],
        key=lambda e: e.get("date", ""),
    )

    if not person_events:
        print(f"沒有 {p['name']} 的互動記錄。用 scan + import-scan 從日記匯入。")
        return

    print(f"📅 {p['name']} 互動時間軸 ({len(person_events)} 筆)\n")

    current_month = ""
    for e in person_events:
        month = e["date"][:7]
        if month != current_month:
            current_month = month
            print(f"\n  --- {month} ---")

        icon = {"meeting": "🤝", "chat": "💬", "meal": "🍽️", "conflict": "⚡",
                "favor": "🎁", "milestone": "🏆", "work": "💻", "social": "🎉",
                "interaction": "▪️"}.get(e.get("type", ""), "▪️")
        sent = {"positive": "+", "negative": "-", "mixed": "±", "neutral": ""}.get(
            e.get("sentiment", ""), "")
        print(f"  {e['date']} {icon} {e.get('summary','')[:60]} {sent}")


def cmd_delete(args):
    """Delete a person (and their events) or a single event by ID."""
    target = args.target.strip()

    if target.startswith("E") and target[1:].isdigit():
        # Delete a single event
        events = _load_jsonl(EVENTS_FILE)
        before = len(events)
        events = [e for e in events if e.get("id") != target]
        if len(events) == before:
            print(f"❌ 找不到事件: {target}", file=sys.stderr)
            sys.exit(1)
        _save_jsonl(EVENTS_FILE, events)
        print(f"🗑️ 刪除事件 {target}")
    else:
        # Delete a person + their events
        people = _load_jsonl(PEOPLE_FILE)
        p = find_person(people, target)
        if not p:
            print(f"❌ 找不到: {target}", file=sys.stderr)
            sys.exit(1)

        events = _load_jsonl(EVENTS_FILE)
        event_count = sum(1 for e in events if e.get("person_id") == p["id"])

        if not args.confirm:
            print(f"⚠️  即將刪除 {p['name']} ({p['id']}) 及其 {event_count} 筆事件")
            print(f"   加 --confirm 確認刪除")
            return

        people = [pp for pp in people if pp.get("id") != p["id"]]
        events = [e for e in events if e.get("person_id") != p["id"]]
        _save_jsonl(PEOPLE_FILE, people)
        _save_jsonl(EVENTS_FILE, events)
        print(f"🗑️ 刪除 {p['name']} ({p['id']}) + {event_count} 筆事件")


def cmd_profile(args):
    """Generate a human-readable profile markdown for a person."""
    people = _load_jsonl(PEOPLE_FILE)
    p = find_person(people, args.name)
    if not p:
        print(f"❌ 找不到: {args.name}", file=sys.stderr)
        sys.exit(1)

    events = _load_jsonl(EVENTS_FILE)
    person_events = sorted(
        [e for e in events if e.get("person_id") == p["id"]],
        key=lambda e: e.get("date", ""),
    )

    # Compute stats
    from collections import Counter
    type_counts = Counter(e.get("type", "") for e in person_events)
    sentiment_counts = Counter(e.get("sentiment", "") for e in person_events)
    months_active = sorted(set(e["date"][:7] for e in person_events if e.get("date")))

    # Find milestones
    milestones = [e for e in person_events if e.get("type") == "milestone"]

    # Build markdown
    lines = []
    lines.append(f"# 👤 {p['name']}")
    lines.append("")
    if p.get("aliases"):
        lines.append(f"**別名**: {', '.join(p['aliases'])}")
    lines.append(f"**關係**: {p.get('relationship', '-')}")
    if p.get("context"):
        lines.append(f"**背景**: {p['context']}")
    if p.get("first_met"):
        lines.append(f"**初識**: {p['first_met']}")
    lines.append(f"**信任**: {p.get('trust', 5)}/10 | **親近**: {p.get('closeness', 5)}/10")
    if p.get("tags"):
        lines.append(f"**標籤**: {', '.join(p['tags'])}")
    if p.get("notes"):
        lines.append(f"\n> {p['notes']}")
    lines.append("")

    # Stats
    lines.append("## 📊 互動統計")
    lines.append(f"- 總互動: {len(person_events)} 次")
    if person_events:
        lines.append(f"- 時間跨度: {person_events[0]['date']} ~ {person_events[-1]['date']}")
    lines.append(f"- 活躍月份: {len(months_active)} 個月")
    if type_counts:
        top_types = ", ".join(f"{t}({c})" for t, c in type_counts.most_common(3))
        lines.append(f"- 主要互動類型: {top_types}")
    pos = sentiment_counts.get("positive", 0)
    neg = sentiment_counts.get("negative", 0)
    total_s = pos + neg + sentiment_counts.get("mixed", 0) + sentiment_counts.get("neutral", 0)
    if total_s > 0:
        lines.append(f"- 情緒: {pos*100//total_s}% 正面, {neg*100//total_s}% 負面")
    lines.append("")

    # Milestones
    if milestones:
        lines.append("## 🏆 重要里程碑")
        for m in milestones:
            lines.append(f"- **{m['date']}**: {m.get('summary', '')}")
        lines.append("")

    # Timeline (grouped by month, max 3 per month)
    lines.append("## 📅 互動時間軸")
    current_month = ""
    month_count = 0
    for e in person_events:
        month = e["date"][:7]
        if month != current_month:
            current_month = month
            month_count = 0
            lines.append(f"\n### {month}")

        month_count += 1
        if month_count > 5:
            if month_count == 6:
                remaining = sum(1 for ee in person_events if ee["date"][:7] == month) - 5
                lines.append(f"- *...還有 {remaining} 筆*")
            continue

        icon = {"meeting": "🤝", "chat": "💬", "meal": "🍽️", "conflict": "⚡",
                "favor": "🎁", "milestone": "🏆", "work": "💻", "social": "🎉",
                "interaction": "▪️"}.get(e.get("type", ""), "▪️")
        lines.append(f"- {e['date']} {icon} {e.get('summary', '')[:80]}")

    lines.append("")

    # Next steps
    if p.get("next_steps"):
        lines.append("## 🎯 下一步")
        for s in p["next_steps"]:
            lines.append(f"- {s}")
        lines.append("")

    lines.append(f"---\n_Generated: {datetime.now(TZ).strftime('%Y-%m-%d %H:%M')}_")

    content = "\n".join(lines)

    # Save
    if args.output:
        out_path = Path(args.output)
    else:
        out_dir = PEOPLE_DIR / "profiles"
        out_dir.mkdir(parents=True, exist_ok=True)
        safe_name = p["name"].replace(" ", "_")
        out_path = out_dir / f"{p['id']}-{safe_name}.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content)
    print(f"💾 Profile saved: {out_path}")
    print(content)


def cmd_stats(args):
    people = _load_jsonl(PEOPLE_FILE)
    events = _load_jsonl(EVENTS_FILE)

    print(f"📊 人際關係資料庫統計\n")
    print(f"  👥 人數: {len(people)}")
    print(f"  📅 事件: {len(events)}")

    if events:
        dates = [e["date"] for e in events if e.get("date")]
        if dates:
            print(f"  📆 時間範圍: {min(dates)} ~ {max(dates)}")

    # Top by events
    event_count = {}
    for e in events:
        pid = e.get("person_id", "")
        event_count[pid] = event_count.get(pid, 0) + 1

    if event_count:
        print(f"\n  互動最多:")
        pid_to_name = {p["id"]: p["name"] for p in people}
        for pid, count in sorted(event_count.items(), key=lambda x: x[1], reverse=True)[:5]:
            name = pid_to_name.get(pid, pid)
            print(f"    {name}: {count} 筆")

    # Tag distribution
    all_tags = {}
    for p in people:
        for t in p.get("tags", []):
            all_tags[t] = all_tags.get(t, 0) + 1
    if all_tags:
        print(f"\n  標籤分布:")
        for tag, count in sorted(all_tags.items(), key=lambda x: x[1], reverse=True)[:8]:
            print(f"    #{tag}: {count}人")


# --- CLI ---

def main():
    parser = argparse.ArgumentParser(description="Personal Relationship Database")
    sub = parser.add_subparsers(dest="command")

    # add
    p_add = sub.add_parser("add", help="新增人物")
    p_add.add_argument("name")
    p_add.add_argument("--aliases", default="")
    p_add.add_argument("--rel", default="")
    p_add.add_argument("--context", default="")
    p_add.add_argument("--first-met", default="")
    p_add.add_argument("--trust", type=int, default=None)
    p_add.add_argument("--closeness", type=int, default=None)
    p_add.add_argument("--tags", default="")
    p_add.add_argument("--notes", default="")

    # update
    p_up = sub.add_parser("update", help="更新人物")
    p_up.add_argument("name")
    p_up.add_argument("--aliases", default=None)
    p_up.add_argument("--rel", default=None)
    p_up.add_argument("--context", default=None)
    p_up.add_argument("--trust", type=int, default=None)
    p_up.add_argument("--closeness", type=int, default=None)
    p_up.add_argument("--tags", default=None)
    p_up.add_argument("--notes", default=None)
    p_up.add_argument("--next-steps", default=None, help="分號分隔")

    # log
    p_log = sub.add_parser("log", help="記錄互動事件")
    p_log.add_argument("name")
    p_log.add_argument("--date", default=None)
    p_log.add_argument("--type", default="interaction",
                       choices=["meeting", "chat", "meal", "conflict", "favor",
                                "milestone", "work", "social", "interaction"])
    p_log.add_argument("--summary", default="")
    p_log.add_argument("--sentiment", default="neutral",
                       choices=["positive", "negative", "mixed", "neutral"])
    p_log.add_argument("--tags", default="")
    p_log.add_argument("--source", default="manual")

    # show
    p_show = sub.add_parser("show", help="顯示人物完整資料")
    p_show.add_argument("name")
    p_show.add_argument("--limit", type=int, default=10)

    # list
    sub.add_parser("list", help="列出所有人物")

    # scan
    p_scan = sub.add_parser("scan", help="掃描日記中的提及")
    p_scan.add_argument("name")
    p_scan.add_argument("--start", default=None)
    p_scan.add_argument("--end", default=None)
    p_scan.add_argument("--max", type=int, default=100)
    p_scan.add_argument("--context", type=int, default=120)
    p_scan.add_argument("--output", default=None)

    # import-scan
    p_imp = sub.add_parser("import-scan", help="匯入掃描結果為事件")
    p_imp.add_argument("name")
    p_imp.add_argument("--file", required=True)

    # timeline
    p_tl = sub.add_parser("timeline", help="顯示互動時間軸")
    p_tl.add_argument("name")

    # delete
    p_del = sub.add_parser("delete", help="刪除人物或事件")
    p_del.add_argument("target", help="人名 或 事件 ID (E001)")
    p_del.add_argument("--confirm", action="store_true", help="跳過確認")

    # profile
    p_prof = sub.add_parser("profile", help="生成人物 profile markdown")
    p_prof.add_argument("name")
    p_prof.add_argument("--output", default=None, help="輸出路徑（預設 memory/people/profiles/）")

    # stats
    sub.add_parser("stats", help="統計概覽")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    {
        "add": cmd_add,
        "update": cmd_update,
        "log": cmd_log,
        "show": cmd_show,
        "list": cmd_list,
        "scan": cmd_scan,
        "import-scan": cmd_import_scan,
        "timeline": cmd_timeline,
        "delete": cmd_delete,
        "profile": cmd_profile,
        "stats": cmd_stats,
    }[args.command](args)


if __name__ == "__main__":
    main()
