#!/usr/bin/env python3
"""Opportunity Watchdog — unified tracker for all opportunities.

Tracks: scholarships, fellowships, grants, CFPs, TA/RA, internships,
competitions, workshops, freelance gigs.

Data: memory/opportunities/opportunities.jsonl

Usage:
  watchdog.py add "MATS Autumn 2026" --cat fellowship --amount "USD 15k" \
    --deadline 2026-04-30 --priority 1 --url https://matsprogram.org
  watchdog.py list [--cat fellowship] [--status eligible] [--due-in 30]
  watchdog.py show O001
  watchdog.py update O001 --status applying --next-step "Fill general app"
  watchdog.py check [--days 14]     # upcoming deadlines, for cron/heartbeat
  watchdog.py stats
  watchdog.py archive               # move expired/rejected to archive
"""

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ)
TODAY = NOW.strftime("%Y-%m-%d")

WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = WORKSPACE / "memory" / "opportunities"
OPP_FILE = DATA_DIR / "opportunities.jsonl"
ARCHIVE_FILE = DATA_DIR / "archive.jsonl"

CATEGORIES = ["scholarship", "fellowship", "grant", "cfp", "ta_ra",
              "internship", "competition", "workshop", "freelance", "other"]
STATUSES = ["discovered", "evaluating", "eligible", "preparing", "applying",
            "submitted", "accepted", "rejected", "expired", "ineligible"]
PRIORITIES = range(1, 6)  # P1=must apply, P5=nice-to-have

# --- JSONL helpers ---

def _load(path: Path) -> list[dict]:
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


def _save(path: Path, items: list[dict]):
    import tempfile, os
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(json.dumps(i, ensure_ascii=False) for i in items) + "\n"
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        os.replace(tmp, path)
    except:
        try: os.close(fd)
        except: pass
        try: os.unlink(tmp)
        except: pass
        raise


def _append(path: Path, item: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def _next_id(items: list[dict]) -> str:
    nums = []
    for i in items:
        id_ = i.get("id", "")
        if id_.startswith("O"):
            try:
                nums.append(int(id_[1:]))
            except ValueError:
                pass
    return f"O{max(nums, default=0) + 1:03d}"


def _find(items: list[dict], id_or_name: str) -> dict | None:
    """Find by ID (exact) or title (case-insensitive partial match)."""
    for i in items:
        if i.get("id") == id_or_name:
            return i
    # Fuzzy match on title
    query = id_or_name.lower()
    for i in items:
        if query in i.get("title", "").lower():
            return i
    return None


def _days_until(deadline: str) -> int | None:
    """Days from today to deadline. None if no/invalid deadline."""
    if not deadline:
        return None
    try:
        dl = datetime.strptime(deadline[:10], "%Y-%m-%d").replace(tzinfo=TZ)
        return (dl - NOW).days
    except (ValueError, TypeError):
        return None


def _urgency_icon(days: int | None) -> str:
    if days is None:
        return "⚪"
    if days < 0:
        return "💀"
    if days <= 7:
        return "🔴"
    if days <= 14:
        return "🟠"
    if days <= 30:
        return "🟡"
    return "🟢"


# --- Commands ---

def cmd_add(args):
    if not args.title or not args.title.strip():
        print("❌ Title 不能為空", file=sys.stderr)
        sys.exit(1)
    if args.cat not in CATEGORIES:
        print(f"❌ Category 必須是: {', '.join(CATEGORIES)}", file=sys.stderr)
        sys.exit(1)
    if args.priority and args.priority not in PRIORITIES:
        print(f"❌ Priority 必須是 1-5", file=sys.stderr)
        sys.exit(1)

    opps = _load(OPP_FILE)

    # Check for duplicates
    for o in opps:
        if o.get("title", "").lower() == args.title.strip().lower():
            print(f"⚠️  '{args.title}' 已存在 (ID: {o['id']})", file=sys.stderr)
            sys.exit(1)

    opp = {
        "id": _next_id(opps),
        "title": args.title.strip(),
        "category": args.cat,
        "amount": args.amount or "",
        "deadline": args.deadline or "",
        "deadline_type": args.deadline_type or "hard",
        "status": args.status or "discovered",
        "eligible": True if args.eligible else (None if args.eligible is None else False),
        "priority": args.priority or 3,
        "effort_hours": args.effort or 0,
        "win_rate": args.win_rate or 0,
        "url": args.url or "",
        "notes": args.notes or "",
        "next_step": args.next_step or "",
        "next_step_due": args.next_step_due or "",
        "tags": [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else [],
        "source": args.source or "manual",
        "created_at": TODAY,
        "updated_at": TODAY,
    }
    _append(OPP_FILE, opp)
    days = _days_until(opp["deadline"])
    days_str = f" ({days}d)" if days is not None else ""
    print(f"✅ {opp['id']}: {opp['title']} [{opp['category']}] deadline={opp['deadline']}{days_str}")


def cmd_update(args):
    opps = _load(OPP_FILE)
    o = _find(opps, args.target)
    if not o:
        print(f"❌ 找不到: {args.target}", file=sys.stderr)
        sys.exit(1)

    if args.status:
        if args.status not in STATUSES:
            print(f"❌ Status 必須是: {', '.join(STATUSES)}", file=sys.stderr)
            sys.exit(1)
        o["status"] = args.status
    if args.priority:
        o["priority"] = args.priority
    if args.deadline:
        o["deadline"] = args.deadline
    if args.next_step:
        o["next_step"] = args.next_step
    if args.next_step_due:
        o["next_step_due"] = args.next_step_due
    if args.notes:
        o["notes"] = args.notes
    if args.amount:
        o["amount"] = args.amount
    if args.eligible is not None:
        o["eligible"] = args.eligible
    if args.url:
        o["url"] = args.url
    if args.effort:
        o["effort_hours"] = args.effort
    if args.win_rate:
        o["win_rate"] = args.win_rate
    o["updated_at"] = TODAY

    _save(OPP_FILE, opps)
    print(f"✅ Updated {o['id']}: {o['title']}")


def cmd_list(args):
    opps = _load(OPP_FILE)

    # Filters
    if args.cat:
        opps = [o for o in opps if o.get("category") == args.cat]
    if args.status:
        opps = [o for o in opps if o.get("status") == args.status]
    if args.due_in is not None:
        opps = [o for o in opps if (_days_until(o.get("deadline","")) or 999) <= args.due_in]
    if args.eligible_only:
        opps = [o for o in opps if o.get("eligible") is not False]

    # Exclude terminal statuses unless asked
    if not args.all:
        opps = [o for o in opps if o.get("status") not in ("expired", "rejected", "ineligible", "accepted")]

    # Sort: by deadline (soonest first), then priority
    def sort_key(o):
        days = _days_until(o.get("deadline", "")) or 9999
        return (days, o.get("priority", 5))

    opps.sort(key=sort_key)

    if args.json:
        json.dump(opps, sys.stdout, ensure_ascii=False, indent=2)
        return

    if not opps:
        print("沒有符合條件的機會。")
        return

    print(f"📋 機會清單 ({len(opps)} 筆)\n")
    for o in opps:
        days = _days_until(o.get("deadline", ""))
        icon = _urgency_icon(days)
        days_str = f"{days}d" if days is not None else "---"
        prio = f"P{o.get('priority', '?')}"
        status = o.get("status", "?")[:8]
        cat = o.get("category", "?")[:10]
        amount = o.get("amount", "")[:15]
        print(f"  {icon} {o['id']} {prio} [{cat:10s}] {status:8s} | "
              f"⏰{days_str:>5s} | {amount:15s} | {o.get('title','')[:40]}")
        if o.get("next_step"):
            ns_due = o.get("next_step_due", "")
            ns_str = f" (by {ns_due})" if ns_due else ""
            print(f"     → {o['next_step'][:60]}{ns_str}")


def cmd_show(args):
    opps = _load(OPP_FILE)
    o = _find(opps, args.target)
    if not o:
        print(f"❌ 找不到: {args.target}", file=sys.stderr)
        sys.exit(1)

    days = _days_until(o.get("deadline", ""))
    icon = _urgency_icon(days)

    print(f"{'='*55}")
    print(f"{icon} {o['id']}: {o['title']}")
    print(f"   類別: {o.get('category', '-')}")
    print(f"   金額: {o.get('amount', '-')}")
    dl = o.get("deadline", "-")
    dl_type = o.get("deadline_type", "")
    days_str = f" ({days} days)" if days is not None else ""
    print(f"   截止: {dl} ({dl_type}){days_str}")
    print(f"   狀態: {o.get('status', '-')}")
    print(f"   優先: P{o.get('priority', '?')} | 勝率: {'⭐'*o.get('win_rate',0) or '-'}")
    print(f"   預估: {o.get('effort_hours', 0)}h | 資格: {'✅' if o.get('eligible') else '❓' if o.get('eligible') is None else '❌'}")
    if o.get("url"):
        print(f"   連結: {o['url']}")
    if o.get("notes"):
        print(f"   備註: {o['notes']}")
    if o.get("next_step"):
        ns_due = o.get("next_step_due", "")
        ns_str = f" (by {ns_due})" if ns_due else ""
        print(f"   下一步: {o['next_step']}{ns_str}")
    if o.get("tags"):
        print(f"   標籤: {', '.join(o['tags'])}")
    print(f"   來源: {o.get('source', '-')} | 建立: {o.get('created_at', '-')} | 更新: {o.get('updated_at', '-')}")
    print(f"{'='*55}")


def cmd_check(args):
    """Check upcoming deadlines — designed for cron/heartbeat."""
    opps = _load(OPP_FILE)
    days_threshold = args.days or 14

    # Active opportunities with deadlines
    active = [o for o in opps if o.get("status") not in
              ("expired", "rejected", "ineligible", "accepted")]

    alerts = []
    for o in active:
        # Check main deadline
        days = _days_until(o.get("deadline", ""))
        if days is not None and days <= days_threshold:
            alerts.append(("deadline", o, days))

        # Check next_step_due
        ns_days = _days_until(o.get("next_step_due", ""))
        if ns_days is not None and ns_days <= 7:
            alerts.append(("next_step", o, ns_days))

    if not alerts:
        if args.json:
            json.dump({"alerts": [], "count": 0}, sys.stdout)
        else:
            print(f"✅ 未來 {days_threshold} 天沒有即將到期的機會。")
        return

    alerts.sort(key=lambda x: x[2])

    if args.json:
        json.dump({
            "alerts": [
                {"type": t, "id": o["id"], "title": o["title"],
                 "days": d, "deadline": o.get("deadline", ""),
                 "status": o.get("status", ""), "next_step": o.get("next_step", "")}
                for t, o, d in alerts
            ],
            "count": len(alerts),
        }, sys.stdout, ensure_ascii=False, indent=2)
        return

    print(f"⚠️ {len(alerts)} 個機會需要注意（{days_threshold} 天內）:\n")
    for alert_type, o, days in alerts:
        icon = _urgency_icon(days)
        if alert_type == "deadline":
            label = f"截止 {o.get('deadline','')}"
        else:
            label = f"下一步 by {o.get('next_step_due','')}: {o.get('next_step','')[:40]}"
        overdue = " ⚡OVERDUE" if days < 0 else ""
        print(f"  {icon} {o['id']} {o['title'][:35]} — {label} ({days}d){overdue}")


def cmd_archive(args):
    opps = _load(OPP_FILE)
    to_archive = [o for o in opps if o.get("status") in ("expired", "rejected", "ineligible")]

    if not to_archive:
        print("沒有需要歸檔的機會。")
        return

    remaining = [o for o in opps if o not in to_archive]

    # Append to archive
    for o in to_archive:
        o["archived_at"] = TODAY
        _append(ARCHIVE_FILE, o)

    _save(OPP_FILE, remaining)
    print(f"📦 歸檔 {len(to_archive)} 筆: {', '.join(o['id'] for o in to_archive)}")


def cmd_stats(args):
    opps = _load(OPP_FILE)
    archived = _load(ARCHIVE_FILE)

    from collections import Counter
    cats = Counter(o.get("category", "") for o in opps)
    statuses = Counter(o.get("status", "") for o in opps)

    print(f"📊 Opportunity Watchdog 統計\n")
    print(f"  活躍: {len(opps)} | 歸檔: {len(archived)}")

    # Upcoming deadlines
    upcoming = []
    for o in opps:
        d = _days_until(o.get("deadline", ""))
        if d is not None and d >= 0:
            upcoming.append((d, o))
    upcoming.sort(key=lambda x: x[0])

    if upcoming:
        print(f"\n  最近截止:")
        for days, o in upcoming[:5]:
            icon = _urgency_icon(days)
            print(f"    {icon} {days:3d}d | {o['id']} {o['title'][:35]}")

    if cats:
        print(f"\n  類別: {', '.join(f'{k}({v})' for k, v in cats.most_common())}")
    if statuses:
        print(f"  狀態: {', '.join(f'{k}({v})' for k, v in statuses.most_common())}")

    # Total potential amount (rough)
    print(f"\n  待處理 next_step:")
    for o in opps:
        if o.get("next_step") and o.get("status") not in ("expired", "rejected", "ineligible"):
            ns_due = o.get("next_step_due", "")
            print(f"    {o['id']} {o['title'][:30]} → {o['next_step'][:40]} {'('+ns_due+')' if ns_due else ''}")


# --- CLI ---

def main():
    parser = argparse.ArgumentParser(description="Opportunity Watchdog")
    sub = parser.add_subparsers(dest="command")

    # add
    p_add = sub.add_parser("add", help="新增機會")
    p_add.add_argument("title")
    p_add.add_argument("--cat", required=True, choices=CATEGORIES)
    p_add.add_argument("--amount", default="")
    p_add.add_argument("--deadline", default="")
    p_add.add_argument("--deadline-type", default="hard", choices=["hard", "rolling", "recurring"])
    p_add.add_argument("--status", default="discovered", choices=STATUSES)
    p_add.add_argument("--eligible", type=lambda x: x.lower() == "true", default=None)
    p_add.add_argument("--priority", type=int, default=3)
    p_add.add_argument("--effort", type=float, default=0, help="Estimated hours")
    p_add.add_argument("--win-rate", type=int, default=0, choices=[0,1,2,3,4,5])
    p_add.add_argument("--url", default="")
    p_add.add_argument("--notes", default="")
    p_add.add_argument("--next-step", default="")
    p_add.add_argument("--next-step-due", default="")
    p_add.add_argument("--tags", default="")
    p_add.add_argument("--source", default="manual")

    # update
    p_up = sub.add_parser("update", help="更新機會")
    p_up.add_argument("target", help="ID (O001) 或 title 關鍵字")
    p_up.add_argument("--status", choices=STATUSES)
    p_up.add_argument("--priority", type=int)
    p_up.add_argument("--deadline", default=None)
    p_up.add_argument("--next-step", default=None)
    p_up.add_argument("--next-step-due", default=None)
    p_up.add_argument("--notes", default=None)
    p_up.add_argument("--amount", default=None)
    p_up.add_argument("--eligible", type=lambda x: x.lower() == "true", default=None)
    p_up.add_argument("--url", default=None)
    p_up.add_argument("--effort", type=float, default=None)
    p_up.add_argument("--win-rate", type=int, default=None)

    # list
    p_list = sub.add_parser("list", help="列出機會")
    p_list.add_argument("--cat", choices=CATEGORIES, default=None)
    p_list.add_argument("--status", choices=STATUSES, default=None)
    p_list.add_argument("--due-in", type=int, default=None, help="Days until deadline")
    p_list.add_argument("--eligible-only", action="store_true")
    p_list.add_argument("--all", action="store_true", help="Include expired/rejected")
    p_list.add_argument("--json", action="store_true")

    # show
    p_show = sub.add_parser("show", help="顯示機會詳情")
    p_show.add_argument("target")

    # check
    p_check = sub.add_parser("check", help="檢查即將到期（cron 用）")
    p_check.add_argument("--days", type=int, default=14)
    p_check.add_argument("--json", action="store_true")

    # archive
    sub.add_parser("archive", help="歸檔已結束的機會")

    # stats
    sub.add_parser("stats", help="統計")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    {"add": cmd_add, "update": cmd_update, "list": cmd_list,
     "show": cmd_show, "check": cmd_check, "archive": cmd_archive,
     "stats": cmd_stats}[args.command](args)


if __name__ == "__main__":
    main()
