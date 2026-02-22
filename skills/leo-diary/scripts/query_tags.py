#!/usr/bin/env python3
"""
標籤查詢工具 — 快速從 memory/tags/*.json 搜尋

用法：
  python3 query_tags.py --person 智凱                    # 智凱出現的所有日期
  python3 query_tags.py --person 智凱 --topic AudioMatters  # AND: 同時出現
  python3 query_tags.py --topic 游泳 --start 2025-10-01   # 10月後游泳的日子
  python3 query_tags.py --late-sleep                      # 所有晚睡的日子
  python3 query_tags.py --late-sleep --recent 30          # 最近30天晚睡
  python3 query_tags.py --summary                         # 全局統計摘要
  python3 query_tags.py --person 智凱 --json              # JSON 輸出
  python3 query_tags.py --person 智凱 --timeline          # 互動頻率時間線
"""
import json
import os
import sys
import glob
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta

TAGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "memory", "tags")


def load_all_tags(start_date=None, end_date=None, recent_days=None) -> list[dict]:
    """載入所有標籤"""
    if recent_days:
        start_date = (datetime.now() - timedelta(days=recent_days)).strftime("%Y-%m-%d")

    tags = []
    for path in sorted(glob.glob(os.path.join(TAGS_DIR, "????-??-??.json"))):
        date = os.path.basename(path).replace(".json", "")
        if start_date and date < start_date:
            continue
        if end_date and date > end_date:
            continue
        with open(path, "r", encoding="utf-8") as f:
            tag = json.load(f)
        tags.append(tag)
    return tags


def filter_tags(tags: list[dict], person=None, topic=None, late_sleep=None) -> list[dict]:
    """篩選標籤"""
    results = tags
    if person:
        results = [t for t in results if person in t.get("people", [])]
    if topic:
        results = [t for t in results if topic in t.get("topics", [])]
    if late_sleep is not None:
        results = [t for t in results if t.get("late_sleep") == late_sleep]
    return results


def print_timeline(tags: list[dict], label: str):
    """列印月度頻率時間線"""
    monthly = defaultdict(int)
    for t in tags:
        month = t["date"][:7]
        monthly[month] += 1

    print(f"\n📈 {label} 月度頻率：")
    for month in sorted(monthly.keys()):
        count = monthly[month]
        bar = "█" * count
        print(f"   {month}  {count:2d} {bar}")


def print_summary(tags: list[dict]):
    """全局統計"""
    people_counter = Counter()
    topic_counter = Counter()
    late_sleep_count = 0
    total_chars = 0

    for t in tags:
        for p in t.get("people", []):
            people_counter[p] += 1
        for tp in t.get("topics", []):
            topic_counter[tp] += 1
        if t.get("late_sleep"):
            late_sleep_count += 1
        total_chars += t.get("diary_chars", 0)

    print(f"📊 標籤資料庫統計")
    print(f"   日記總數：{len(tags)}")
    print(f"   日期範圍：{tags[0]['date']} ~ {tags[-1]['date']}")
    print(f"   總字數：{total_chars:,}")
    print(f"   平均字數：{total_chars // len(tags):,}/篇")
    print(f"   晚睡天數：{late_sleep_count}/{len(tags)} ({late_sleep_count*100//len(tags)}%)")

    print(f"\n👥 人物 top 10：")
    for name, count in people_counter.most_common(10):
        print(f"   {name:10s} {count:3d} 天")

    print(f"\n📋 主題 top 10：")
    for topic, count in topic_counter.most_common(10):
        print(f"   {topic:14s} {count:3d} 天")


def co_occurrence(tags: list[dict], entity: str, entity_type: str = "person") -> dict:
    """計算共現（某人常和誰/什麼主題一起出現）"""
    people_co = Counter()
    topic_co = Counter()

    for t in tags:
        people = t.get("people", [])
        topics = t.get("topics", [])

        if entity_type == "person" and entity in people:
            for p in people:
                if p != entity:
                    people_co[p] += 1
            for tp in topics:
                topic_co[tp] += 1
        elif entity_type == "topic" and entity in topics:
            for p in people:
                people_co[p] += 1
            for tp in topics:
                if tp != entity:
                    topic_co[tp] += 1

    return {"co_people": people_co, "co_topics": topic_co}


def main():
    parser = argparse.ArgumentParser(description="標籤查詢工具")
    parser.add_argument("--person", "-p", help="篩選人物")
    parser.add_argument("--topic", "-t", help="篩選主題")
    parser.add_argument("--late-sleep", action="store_true", help="只看晚睡的日子")
    parser.add_argument("--start", help="起始日期")
    parser.add_argument("--end", help="結束日期")
    parser.add_argument("--recent", type=int, help="最近 N 天")
    parser.add_argument("--json", action="store_true", help="JSON 輸出")
    parser.add_argument("--summary", action="store_true", help="全局統計")
    parser.add_argument("--timeline", action="store_true", help="月度頻率時間線")
    parser.add_argument("--co", action="store_true", help="共現分析")
    args = parser.parse_args()

    tags = load_all_tags(start_date=args.start, end_date=args.end, recent_days=args.recent)
    if not tags:
        print("沒有找到標籤。先跑 generate_tags.py 回填。")
        sys.exit(1)

    if args.summary:
        print_summary(tags)
        return

    # 篩選
    filtered = filter_tags(
        tags,
        person=args.person,
        topic=args.topic,
        late_sleep=True if args.late_sleep else None,
    )

    if args.json:
        print(json.dumps(filtered, ensure_ascii=False, indent=2))
        return

    # 共現分析
    if args.co and (args.person or args.topic):
        entity = args.person or args.topic
        etype = "person" if args.person else "topic"
        co = co_occurrence(tags, entity, etype)
        print(f"🔗 {entity} 的共現分析（{len(filtered)} 天）：\n")
        print(f"   常一起出現的人：")
        for name, count in co["co_people"].most_common(8):
            print(f"     {name:10s} {count:2d} 天")
        print(f"\n   常一起出現的主題：")
        for topic, count in co["co_topics"].most_common(8):
            print(f"     {topic:14s} {count:2d} 天")
        return

    # 時間線
    if args.timeline and filtered:
        label = args.person or args.topic or "晚睡" if args.late_sleep else "結果"
        print_timeline(filtered, label)
        return

    # 一般列表輸出
    label_parts = []
    if args.person:
        label_parts.append(f"人物={args.person}")
    if args.topic:
        label_parts.append(f"主題={args.topic}")
    if args.late_sleep:
        label_parts.append("晚睡")
    label = " & ".join(label_parts) or "全部"

    print(f"🔍 查詢：{label}")
    print(f"📊 找到 {len(filtered)}/{len(tags)} 天\n")

    for t in filtered:
        people_str = ", ".join(t.get("people", []))
        topics_short = ", ".join(t.get("topics", [])[:5])
        late = " 🌙晚睡" if t.get("late_sleep") else ""
        metrics = t.get("metrics", {})
        mood_str = f" 心情:{metrics['mood']}" if "mood" in metrics else ""
        print(f"  {t['date']}{mood_str}{late}")
        if args.person:
            print(f"    主題: {topics_short}")
        elif args.topic:
            print(f"    人物: {people_str}")
        else:
            print(f"    人物: {people_str}")
            print(f"    主題: {topics_short}")


if __name__ == "__main__":
    main()
