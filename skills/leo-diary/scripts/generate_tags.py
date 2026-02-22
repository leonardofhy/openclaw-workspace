#!/usr/bin/env python3
"""
日記標籤提取器（純 Python，不依賴 LLM）
用途：批量回填歷史標籤 / 作為 LLM 標籤的 fallback

用法：
  python3 generate_tags.py                    # 處理所有日記
  python3 generate_tags.py --date 2026-02-22  # 處理指定日期
  python3 generate_tags.py --recent 7         # 最近 7 天
  python3 generate_tags.py --dry-run          # 預覽不寫入
"""
import json
import os
import sys
import re
import glob
import argparse
from datetime import datetime, timedelta
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MEMORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "memory")
TAGS_DIR = os.path.join(MEMORY_DIR, "tags")

# Diary metrics cache (loaded once from Google Sheets / CSV)
_diary_metrics_cache = None

def _load_diary_metrics():
    """Load mood/energy from diary source (Sheets or CSV). Cached."""
    global _diary_metrics_cache
    if _diary_metrics_cache is not None:
        return _diary_metrics_cache
    try:
        from read_diary import load_diary
        entries = load_diary(has_diary_only=False)
        _diary_metrics_cache = {}
        for e in entries:
            d = e.get('date', '')
            if d and d not in _diary_metrics_cache:
                metrics = {}
                try:
                    m = int(e.get('mood', ''))
                    if 1 <= m <= 5:
                        metrics['mood'] = m
                except (ValueError, TypeError):
                    pass
                try:
                    en = int(e.get('energy', ''))
                    if 1 <= en <= 5:
                        metrics['energy'] = en
                except (ValueError, TypeError):
                    pass
                if metrics:
                    _diary_metrics_cache[d] = metrics
    except Exception as ex:
        print(f"[warn] Could not load diary metrics: {ex}", file=sys.stderr)
        _diary_metrics_cache = {}
    return _diary_metrics_cache

# ─── 人物別名表（與 search_diary.py 同步）─────────────────
PEOPLE_ALIASES = {
    "智凱": ["智凱", "智凱哥", "凱哥", "zhikai"],
    "晨安": ["晨安", "晨安哥", "chenan"],
    "康哥": ["康哥", "kang"],
    "李宏毅": ["李宏毅", "宏毅", "宏毅老師", "李老師", "hungyi", "hung-yi"],
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

# ─── 主題關鍵詞 ──────────────────────────────────────────
TOPIC_KEYWORDS = {
    "AudioMatters": ["audiomatters", "audio matters", "benchmark", "語音評估"],
    "研究/實驗": ["實驗", "跑實驗", "模型", "training", "dataset", "論文", "paper"],
    "上課": ["上課", "lecture", "課程", "教室", "專題討論", "深度學習", "強化學習"],
    "游泳": ["游泳", "泳池", "游了"],
    "運動": ["健身", "俯臥撐", "跑步", "運動"],
    "社交/聚餐": ["lab dinner", "吃飯", "聚餐", "喝酒", "聊天"],
    "LOL": ["lol", "LOL", "英雄聯盟"],
    "動畫": ["動畫", "anime", "看番", "追番", "新番", "番劇"],
    "西洋棋": ["西洋棋", "chess", "lichess"],
    "NTUAIS": ["ntuais", "NTU AI Safety", "ai safety"],
    "獎學金": ["獎學金", "scholarship"],
    "行政": ["居留證", "簽證", "visa", "戶政", "銀行", "開戶"],
    "Todoist": ["todoist"],
    "OpenClaw": ["openclaw", "cron", "little leo", "bot"],
    "Duolingo": ["duolingo"],
    "螺螄粉": ["螺螄粉", "螺蛳粉"],
    "麥當勞": ["麥當勞", "mcdonald"],
    "實驗室": ["實驗室", "lab", "531", "552"],
    "睡眠議題": ["失眠", "睡不著", "熬夜", "晚睡", "作息亂"],
    "生病": ["感冒", "發燒", "咳嗽", "喉嚨痛", "頭痛", "生病", "看醫生"],
    "馬來西亞": ["馬來西亞", "malaysia", "新山", "回馬", "大馬", "馬來"],
    "Compass": ["compass", "營隊"],
    "email": ["email", "寄信", "回信"],
    "記帳": ["記帳", "花費", "支出", "存款"],
}

# ─── 晚睡判定 ──────────────────────────────────────────
LATE_SLEEP_PATTERNS = [
    r"凌晨[2-7]點",
    r"[2-7]點.*才睡",
    r"[2-7]點.*入睡",
    r"熬夜",
    r"很晚.*睡",
]


def extract_people(text: str) -> list[str]:
    """提取提及的人物"""
    found = []
    for canonical, aliases in PEOPLE_ALIASES.items():
        for alias in aliases:
            if alias in text:
                found.append(canonical)
                break
    return sorted(set(found))


def extract_topics(text: str) -> list[str]:
    """提取主題標籤"""
    text_lower = text.lower()
    found = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                found.append(topic)
                break
    return sorted(set(found))


def detect_late_sleep(text: str) -> bool:
    """偵測是否提到晚睡"""
    for pat in LATE_SLEEP_PATTERNS:
        if re.search(pat, text):
            return True
    return False


def extract_metrics_from_header(content: str) -> dict:
    """從 memory/*.md 的 YAML-like header 提取指標"""
    metrics = {}
    # 嘗試抓 mood/energy/sleep 等 (格式不固定，盡力而為)
    mood_m = re.search(r"心情[：:]\s*(\d)", content[:500])
    energy_m = re.search(r"精力[：:]\s*(\d)", content[:500])
    if mood_m:
        metrics["mood"] = int(mood_m.group(1))
    if energy_m:
        metrics["energy"] = int(energy_m.group(1))
    return metrics


def generate_tag(date: str, content: str) -> dict:
    """為一篇日記生成標籤"""
    tag = {
        "date": date,
        "people": extract_people(content),
        "topics": extract_topics(content),
        "late_sleep": detect_late_sleep(content),
        "diary_chars": len(content),
        "method": "python-rules",  # 區分 LLM 生成 vs 純規則
    }

    # Metrics: try diary source first (accurate), fall back to header parsing
    diary_metrics = _load_diary_metrics().get(date, {})
    if diary_metrics:
        tag["metrics"] = diary_metrics
    else:
        header_metrics = extract_metrics_from_header(content)
        if header_metrics:
            tag["metrics"] = header_metrics

    return tag


def process_diary_file(filepath: str) -> tuple[str, dict] | None:
    """處理一個 memory/YYYY-MM-DD.md 檔案"""
    basename = os.path.basename(filepath)
    date_match = re.match(r"(\d{4}-\d{2}-\d{2})\.md$", basename)
    if not date_match:
        return None

    date = date_match.group(1)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if len(content.strip()) < 50:  # 太短的忽略
        return None

    return date, generate_tag(date, content)


def main():
    parser = argparse.ArgumentParser(description="日記標籤提取器")
    parser.add_argument("--date", help="指定日期 YYYY-MM-DD")
    parser.add_argument("--recent", type=int, help="最近 N 天")
    parser.add_argument("--dry-run", action="store_true", help="預覽不寫入")
    parser.add_argument("--force", action="store_true", help="覆蓋已有標籤")
    parser.add_argument("--stats", action="store_true", help="只顯示統計")
    args = parser.parse_args()

    os.makedirs(TAGS_DIR, exist_ok=True)

    # 收集要處理的檔案
    if args.date:
        files = [os.path.join(MEMORY_DIR, f"{args.date}.md")]
        files = [f for f in files if os.path.exists(f)]
    elif args.recent:
        today = datetime.now()
        dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(args.recent)]
        files = [os.path.join(MEMORY_DIR, f"{d}.md") for d in dates]
        files = [f for f in files if os.path.exists(f)]
    else:
        files = sorted(glob.glob(os.path.join(MEMORY_DIR, "????-??-??.md")))

    processed = 0
    skipped = 0
    people_counter = Counter()
    topic_counter = Counter()

    for filepath in files:
        result = process_diary_file(filepath)
        if result is None:
            continue

        date, tag = result
        tag_path = os.path.join(TAGS_DIR, f"{date}.json")

        # 跳過已有 LLM 標籤（除非 force）
        if os.path.exists(tag_path) and not args.force:
            with open(tag_path, "r") as f:
                existing = json.load(f)
            if existing.get("method") == "llm" and not args.force:
                skipped += 1
                continue
            if not args.force:
                skipped += 1
                continue

        # 統計
        for p in tag["people"]:
            people_counter[p] += 1
        for t in tag["topics"]:
            topic_counter[t] += 1

        if not args.dry_run:
            with open(tag_path, "w", encoding="utf-8") as f:
                json.dump(tag, f, ensure_ascii=False, indent=2)

        processed += 1

    # 輸出
    if args.stats or args.dry_run:
        print(f"📊 標籤統計：")
        print(f"   處理：{processed} 筆  跳過：{skipped} 筆\n")

        if people_counter:
            print(f"👥 人物出現次數 (top 15):")
            for name, count in people_counter.most_common(15):
                bar = "█" * min(count, 40)
                print(f"   {name:8s} {count:3d} {bar}")

        print()
        if topic_counter:
            print(f"📋 主題出現次數 (top 15):")
            for topic, count in topic_counter.most_common(15):
                bar = "█" * min(count, 40)
                print(f"   {topic:12s} {count:3d} {bar}")

        if not args.dry_run:
            print(f"\n✅ 已寫入 {processed} 個標籤到 {TAGS_DIR}/")
    else:
        print(f"✅ 已生成 {processed} 個標籤，跳過 {skipped} 個（已存在）")


if __name__ == "__main__":
    main()
