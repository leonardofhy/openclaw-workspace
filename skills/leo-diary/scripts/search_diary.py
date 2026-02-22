#!/usr/bin/env python3
"""
搜尋 Leo 日記 — 增強版
支援多關鍵詞 (AND/OR)、人物別名、日期範圍、正則表達式

用法：
  python3 search_diary.py 智凱                    # 基本搜尋（含別名展開）
  python3 search_diary.py 智凱 游泳               # AND: 同時出現
  python3 search_diary.py 智凱 游泳 --or          # OR: 任一出現
  python3 search_diary.py 論文 --start 2026-01-01  # 日期範圍
  python3 search_diary.py "凌晨[3-5]點" --regex   # 正則
  python3 search_diary.py 智凱 --json             # JSON 輸出（供腳本用）
  python3 search_diary.py --people                 # 列出已知人物別名表
  python3 search_diary.py 智凱 --field completed   # 搜尋特定欄位
"""
import sys
import os
import re
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from read_diary import load_diary

# ─── 人物別名表 ───────────────────────────────────────────
# key = 標準名, value = 所有可能出現的稱呼
ALIASES = {
    "智凱": ["智凱", "智凱哥", "凱哥", "zhikai"],
    "晨安": ["晨安", "晨安哥", "chenan"],
    "康哥": ["康哥", "康", "kang"],
    "李宏毅": ["李宏毅", "宏毅", "宏毅老師", "老師", "李老師", "hungyi", "hung-yi"],
    "明淵": ["明淵", "mingyuan"],
    "朗軒": ["朗軒", "langxuan"],
    "Rocky": ["Rocky", "rocky"],
    "Wilson": ["Wilson", "wilson"],
    "Howard": ["Howard", "howard"],
    "David": ["David", "david"],
    "Ziya": ["Ziya", "ziya"],
    "Christine": ["Christine", "christine"],
    "Teddy": ["Teddy", "teddy"],
    "Zen": ["Zen", "zen"],
    "陳縕儂": ["陳縕儂", "縕儂", "yunnnung", "vivian"],
    "專題生": ["專題生"],
    "媽": ["我媽", "媽媽", "老媽"],
    "爸": ["我爸", "爸爸", "老爸"],
}

# 搜尋欄位映射
SEARCHABLE_FIELDS = {
    "diary": "diary",
    "completed": "completed",
    "all": None,  # special: search diary + completed
}


def expand_keyword(keyword: str) -> list[str]:
    """如果關鍵詞匹配某人的任一別名，展開為該人的所有別名"""
    kw_lower = keyword.lower()
    for canonical, aliases in ALIASES.items():
        if any(a.lower() == kw_lower for a in aliases):
            return aliases
    return [keyword]


def matches_text(text: str, patterns: list[str], use_regex: bool) -> list[str]:
    """回傳在 text 中命中的 pattern 列表"""
    hits = []
    for p in patterns:
        if use_regex:
            if re.search(p, text, re.IGNORECASE):
                hits.append(p)
        else:
            if p.lower() in text.lower():
                hits.append(p)
    return hits


def extract_context(text: str, pattern: str, context_chars: int = 80, use_regex: bool = False) -> list[str]:
    """提取關鍵詞周圍的文字片段"""
    snippets = []
    if use_regex:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            start = max(0, m.start() - context_chars)
            end = min(len(text), m.end() + context_chars)
            snippet = text[start:end].replace('\n', ' ')
            if start > 0:
                snippet = "…" + snippet
            if end < len(text):
                snippet = snippet + "…"
            snippets.append(snippet)
    else:
        p_lower = pattern.lower()
        t_lower = text.lower()
        idx = 0
        while True:
            pos = t_lower.find(p_lower, idx)
            if pos == -1:
                break
            start = max(0, pos - context_chars)
            end = min(len(text), pos + len(pattern) + context_chars)
            snippet = text[start:end].replace('\n', ' ')
            if start > 0:
                snippet = "…" + snippet
            if end < len(text):
                snippet = snippet + "…"
            snippets.append(snippet)
            idx = pos + 1
            if len(snippets) >= 3:
                break
    return snippets


def search(keywords: list[str], start_date=None, end_date=None,
           use_or=False, use_regex=False, context_chars=80,
           field="diary", max_results=50) -> list[dict]:
    """
    搜尋日記。
    keywords: 搜尋詞列表
    use_or: True=任一命中即可, False=全部都要命中
    """
    entries = load_diary(start_date=start_date, end_date=end_date, has_diary_only=True)

    # 展開別名（非 regex 模式）
    all_patterns = []
    keyword_to_patterns = {}
    for kw in keywords:
        if use_regex:
            patterns = [kw]
        else:
            patterns = expand_keyword(kw)
        keyword_to_patterns[kw] = patterns
        all_patterns.extend(patterns)

    results = []
    for entry in entries:
        # 決定搜尋的文字範圍
        if field == "all":
            search_text = (entry.get("diary", "") + "\n" + entry.get("completed", ""))
        else:
            search_text = entry.get(field, "")

        if not search_text.strip():
            continue

        # 對每個原始關鍵詞，檢查其 patterns 是否有命中
        kw_hits = {}
        for kw, patterns in keyword_to_patterns.items():
            hits = matches_text(search_text, patterns, use_regex)
            if hits:
                kw_hits[kw] = hits

        # AND/OR 判斷
        if use_or:
            if not kw_hits:
                continue
        else:
            if len(kw_hits) < len(keywords):
                continue

        # 提取 context snippets
        snippets = []
        seen_patterns = set()
        for kw, hits in kw_hits.items():
            for h in hits:
                if h not in seen_patterns:
                    seen_patterns.add(h)
                    snippets.extend(extract_context(search_text, h, context_chars, use_regex))

        results.append({
            "date": entry["date"],
            "mood": entry.get("mood", ""),
            "energy": entry.get("energy", ""),
            "matched_keywords": list(kw_hits.keys()),
            "matched_aliases": [a for hits in kw_hits.values() for a in hits],
            "snippets": snippets[:5],
            "diary_length": len(entry.get("diary", "")),
        })

        if len(results) >= max_results:
            break

    return results


def print_people():
    """列印人物別名表"""
    print("📋 已知人物別名表：\n")
    for canonical, aliases in sorted(ALIASES.items()):
        print(f"  {canonical}: {', '.join(aliases)}")
    print(f"\n共 {len(ALIASES)} 人。編輯 search_diary.py 的 ALIASES 可新增。")


def main():
    parser = argparse.ArgumentParser(description="搜尋 Leo 日記")
    parser.add_argument("keywords", nargs="*", help="搜尋關鍵詞（多個=AND）")
    parser.add_argument("--or", dest="use_or", action="store_true", help="多關鍵詞用 OR（預設 AND）")
    parser.add_argument("--regex", action="store_true", help="關鍵詞視為正則表達式")
    parser.add_argument("--start", help="起始日期 YYYY-MM-DD")
    parser.add_argument("--end", help="結束日期 YYYY-MM-DD")
    parser.add_argument("--context", type=int, default=80, help="前後文字數（預設 80）")
    parser.add_argument("--field", choices=["diary", "completed", "all"], default="diary",
                        help="搜尋欄位（預設 diary）")
    parser.add_argument("--max", type=int, default=50, help="最多回傳筆數（預設 50）")
    parser.add_argument("--json", action="store_true", help="JSON 輸出")
    parser.add_argument("--people", action="store_true", help="列出已知人物別名表")
    parser.add_argument("--stats", action="store_true", help="只顯示統計（日期列表+次數）")
    args = parser.parse_args()

    if args.people:
        print_people()
        return

    if not args.keywords:
        parser.print_help()
        sys.exit(1)

    results = search(
        keywords=args.keywords,
        start_date=args.start,
        end_date=args.end,
        use_or=args.use_or,
        use_regex=args.regex,
        context_chars=args.context,
        field=args.field,
        max_results=args.max,
    )

    if args.json:
        print(json.dumps({
            "query": args.keywords,
            "mode": "OR" if args.use_or else "AND",
            "count": len(results),
            "results": results,
        }, ensure_ascii=False, indent=2))
        return

    if args.stats:
        print(f"找到 {len(results)} 筆包含 {'|'.join(args.keywords)} 的日記")
        print(f"日期範圍：{results[0]['date']} ~ {results[-1]['date']}" if results else "無結果")
        if results:
            print(f"\n日期列表：")
            for r in results:
                print(f"  {r['date']} (心情:{r['mood']} 精力:{r['energy']})")
        return

    # 人類友好輸出
    print(f"🔍 搜尋：{'|'.join(args.keywords)}（{'OR' if args.use_or else 'AND'}模式）")
    if args.start or args.end:
        print(f"📅 範圍：{args.start or '...'} ~ {args.end or '...'}")
    print(f"📊 找到 {len(results)} 筆\n")

    for r in results:
        matched_info = ""
        aliases_used = set(r["matched_aliases"]) - set(r["matched_keywords"])
        if aliases_used:
            matched_info = f" [別名命中: {', '.join(aliases_used)}]"

        print(f"📅 {r['date']} (心情:{r['mood']}/5 精力:{r['energy']}/5){matched_info}")
        for s in r["snippets"]:
            print(f"   → {s[:300]}")
        print()


if __name__ == "__main__":
    main()
