#!/usr/bin/env python3
"""
Leo 日記洞察引擎 — 模仿 Claude Code /insights 風格
分析最近 7/30 天的日記，給出有意思的觀察
"""
import sys
import json
import statistics
from datetime import datetime, timedelta, date

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from read_diary import load_diary

def insights(days=7):
    today = date.today()
    start = (today - timedelta(days=days)).strftime('%Y-%m-%d')
    
    recent = load_diary(start_date=start, has_diary_only=False)
    all_entries = load_diary(has_diary_only=False)
    
    if not recent:
        print(f"最近 {days} 天沒有日記資料")
        return

    # 計算指標
    moods = [int(e['mood']) for e in recent if e['mood'].isdigit()]
    energies = [int(e['energy']) for e in recent if e['energy'].isdigit()]
    
    all_moods = [int(e['mood']) for e in all_entries if e['mood'].isdigit()]
    all_avg_mood = statistics.mean(all_moods) if all_moods else 0
    
    recent_avg_mood = statistics.mean(moods) if moods else 0
    recent_avg_energy = statistics.mean(energies) if energies else 0
    
    # 睡眠解析
    def parse_sleep(t):
        t = str(t).strip().replace(':', '')
        if not t or not t.isdigit(): return None
        t = t.zfill(4)
        h, m = int(t[:2]), int(t[2:])
        mins = h * 60 + m
        return mins + 1440 if mins < 12 * 60 else mins

    sleep_times = [parse_sleep(e['sleep_in']) for e in recent if parse_sleep(e['sleep_in'])]
    avg_sleep = statistics.mean(sleep_times) % 1440 if sleep_times else None

    def mins_to_str(m):
        if m is None: return "N/A"
        return f"{int(m//60):02d}:{int(m%60):02d}"

    # 日記有無
    has_diary = [e for e in recent if e['diary']]
    
    # 輸出洞察
    print(f"\n{'='*50}")
    print(f"📔 Leo 日記洞察（最近 {days} 天）")
    print(f"{'='*50}")
    print(f"📅 期間：{start} ～ {today}")
    print(f"📝 有填日記：{len(has_diary)}/{len(recent)} 天")

    print(f"\n{'─'*40}")
    print(f"😊 心情")
    if moods:
        mood_delta = recent_avg_mood - all_avg_mood
        arrow = "↑" if mood_delta > 0.1 else ("↓" if mood_delta < -0.1 else "→")
        print(f"   近期平均：{recent_avg_mood:.1f}  {arrow}（整體均值 {all_avg_mood:.1f}）")
        print(f"   最高：{max(moods)}  最低：{min(moods)}")
        best_day = max(recent, key=lambda e: int(e['mood']) if e['mood'].isdigit() else 0)
        worst_day = min(recent, key=lambda e: int(e['mood']) if e['mood'].isdigit() else 5)
        print(f"   最好的一天：{best_day['date']}（{best_day['mood']} 分）")

    print(f"\n{'─'*40}")
    print(f"⚡ 精力")
    if energies:
        print(f"   近期平均：{recent_avg_energy:.1f}")

    print(f"\n{'─'*40}")
    print(f"🌙 睡眠")
    if sleep_times:
        print(f"   平均入睡：{mins_to_str(avg_sleep)}")
        late_nights = sum(1 for s in sleep_times if s % 1440 >= 4 * 60)
        print(f"   4am 後才睡：{late_nights}/{len(sleep_times)} 天")

    # 近期日記摘要（最後一篇）
    if has_diary:
        latest = sorted(has_diary, key=lambda e: e['date'])[-1]
        snippet = latest['diary'][:150].replace('\n', ' ')
        print(f"\n{'─'*40}")
        print(f"📖 最近一篇日記（{latest['date']}）")
        print(f"   「{snippet}...」")

    print(f"\n{'='*50}\n")

if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    insights(days)
