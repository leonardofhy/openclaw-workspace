#!/usr/bin/env python3
"""
Leo 日記深度分析報告
分析：睡眠品質相關性、習慣影響、星期效應、月度趨勢、最佳/最差條件、人物×心情
用法：
  python3 diary_deep_analysis.py              # 完整報告
  python3 diary_deep_analysis.py --days 30    # 最近 30 天
  python3 diary_deep_analysis.py --json       # JSON 輸出
  python3 diary_deep_analysis.py --section sleep  # 只看睡眠
"""
import json
import statistics
import sys
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from read_diary import load_diary
from sleep_calc import sleep_duration_minutes, parse_hhmm

TAGS_DIR = Path(__file__).parent.parent.parent.parent / 'memory' / 'tags'
DOW_NAMES = ['一', '二', '三', '四', '五', '六', '日']


def load_entries(days=None):
    start = None
    if days:
        start = (date.today() - timedelta(days=days)).isoformat()
    return load_diary(start_date=start, has_diary_only=False)


def pearson_r(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sx, sy = statistics.stdev(xs), statistics.stdev(ys)
    if sx == 0 or sy == 0:
        return None
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / n
    return cov / (sx * sy)


def section_sleep(entries):
    """Sleep quality & duration analysis."""
    lines = []
    lines.append("## 😴 睡眠分析")
    lines.append("")

    # Sleep quality vs mood
    sq_mood = []
    for e in entries:
        sq = e.get('sleep_quality', '')
        mood = e.get('mood', '')
        energy = e.get('energy', '')
        if sq.strip().isdigit() and mood.strip().isdigit():
            sq_mood.append({
                'sq': int(sq), 'mood': int(mood),
                'energy': int(energy) if energy.strip().isdigit() else None
            })

    if sq_mood:
        lines.append("### 睡眠品質 vs 心情")
        lines.append(f"  {'品質':6} {'天數':5} {'平均心情':8} {'平均精力':8}")
        for q in [1, 2, 3, 4, 5]:
            days = [d for d in sq_mood if d['sq'] == q]
            if days:
                avg_mood = statistics.mean(d['mood'] for d in days)
                energy_days = [d for d in days if d['energy'] is not None]
                avg_energy = statistics.mean(d['energy'] for d in energy_days) if energy_days else 0
                lines.append(f"  {q}/5    {len(days):5d} {avg_mood:8.2f} {avg_energy:8.2f}")

        r_sq = pearson_r([d['sq'] for d in sq_mood], [d['mood'] for d in sq_mood])
        if r_sq is not None:
            lines.append(f"\n  Pearson r (品質 vs 心情): {r_sq:.3f}")

    # Sleep duration vs mood
    dur_mood = []
    for e in entries:
        dur = sleep_duration_minutes(e.get('sleep_in'), e.get('wake_up'))
        mood = e.get('mood', '')
        if dur and mood.strip().isdigit():
            dur_mood.append({'dur': dur / 60, 'mood': int(mood)})

    if dur_mood:
        r_dur = pearson_r([d['dur'] for d in dur_mood], [d['mood'] for d in dur_mood])
        if r_dur is not None:
            lines.append(f"  Pearson r (時長 vs 心情): {r_dur:.3f}")
            if r_sq is not None:
                better = "品質" if abs(r_sq) > abs(r_dur) else "時長"
                lines.append(f"  → 睡眠{better}更能預測心情")

    # Duration buckets
    if dur_mood:
        lines.append("\n### 睡眠時長 vs 心情")
        buckets = {'<5h': [], '5-6h': [], '6-7h': [], '7-8h': [], '>8h': []}
        for d in dur_mood:
            h = d['dur']
            if h < 5: buckets['<5h'].append(d)
            elif h < 6: buckets['5-6h'].append(d)
            elif h < 7: buckets['6-7h'].append(d)
            elif h < 8: buckets['7-8h'].append(d)
            else: buckets['>8h'].append(d)

        lines.append(f"  {'區間':8} {'天數':5} {'平均心情':8}")
        for bucket, days in buckets.items():
            if days:
                avg = statistics.mean(d['mood'] for d in days)
                lines.append(f"  {bucket:8} {len(days):5d} {avg:8.2f}")

    # Best/worst sleep conditions
    combined = []
    for e in entries:
        dur = sleep_duration_minutes(e.get('sleep_in'), e.get('wake_up'))
        sq = e.get('sleep_quality', '')
        mood = e.get('mood', '')
        if dur and sq.strip().isdigit() and mood.strip().isdigit():
            combined.append({'dur_h': dur / 60, 'sq': int(sq), 'mood': int(mood)})

    if combined:
        best = [c for c in combined if c['sq'] >= 4 and c['dur_h'] >= 6.5]
        worst = [c for c in combined if c['sq'] <= 3 and c['dur_h'] < 6.5]
        lines.append("\n### 最佳/最差睡眠組合")
        if best:
            lines.append(f"  品質≥4 + ≥6.5h: mood {statistics.mean(c['mood'] for c in best):.2f} (n={len(best)})")
        if worst:
            lines.append(f"  品質≤3 + <6.5h: mood {statistics.mean(c['mood'] for c in worst):.2f} (n={len(worst)})")
        if best and worst:
            gap = statistics.mean(c['mood'] for c in best) - statistics.mean(c['mood'] for c in worst)
            lines.append(f"  差距: {gap:.2f}")

    lines.append("")
    return lines


def section_habits(entries):
    """Habit tracking analysis from 'completed' field."""
    lines = []
    lines.append("## 📋 習慣追蹤分析")
    lines.append("")

    overall_moods = [int(e['mood']) for e in entries if e.get('mood', '').strip().isdigit()]
    overall_energies = [int(e['energy']) for e in entries if e.get('energy', '').strip().isdigit()]
    if not overall_moods:
        lines.append("  (無數據)")
        return lines

    overall_mood = statistics.mean(overall_moods)
    overall_energy = statistics.mean(overall_energies) if overall_energies else 0

    habit_data = defaultdict(lambda: {'moods': [], 'energies': []})
    has_habits = 0
    for e in entries:
        completed = e.get('completed', '')
        mood = e.get('mood', '')
        energy = e.get('energy', '')
        if not completed.strip() or not mood.strip().isdigit():
            continue
        has_habits += 1
        m = int(mood)
        en = int(energy) if energy.strip().isdigit() else None
        for h in (h.strip() for h in completed.split(',') if h.strip()):
            habit_data[h]['moods'].append(m)
            if en is not None:
                habit_data[h]['energies'].append(en)

    if not has_habits:
        lines.append(f"  (目前時間範圍內無習慣數據)")
        return lines

    lines.append(f"  有習慣記錄的天數: {has_habits}")
    lines.append(f"  整體平均: mood={overall_mood:.2f}, energy={overall_energy:.2f}")
    lines.append("")

    # Sort by mood impact
    ranked = []
    for habit, data in habit_data.items():
        if len(data['moods']) >= 5:
            avg_mood = statistics.mean(data['moods'])
            avg_energy = statistics.mean(data['energies']) if data['energies'] else 0
            ranked.append((habit, len(data['moods']), avg_mood, avg_mood - overall_mood, avg_energy))

    ranked.sort(key=lambda x: -x[3])  # sort by mood impact

    lines.append(f"  {'習慣':22} {'天數':5} {'心情':7} {'差異':7} {'精力':7}")
    for habit, count, mood, diff, energy in ranked[:12]:
        icon = "↑" if diff > 0.05 else "↓" if diff < -0.05 else "="
        lines.append(f"  {habit:22} {count:5d} {mood:7.2f} {diff:+7.2f}{icon} {energy:7.2f}")

    lines.append("")
    return lines


def section_dow(entries):
    """Day of week analysis."""
    lines = []
    lines.append("## 📅 星期幾效應")
    lines.append("")

    dow_data = defaultdict(list)
    for e in entries:
        d = datetime.strptime(e['date'], '%Y-%m-%d')
        dow = d.weekday()
        mood = int(e['mood']) if e.get('mood', '').strip().isdigit() else None
        energy = int(e['energy']) if e.get('energy', '').strip().isdigit() else None
        dur = sleep_duration_minutes(e.get('sleep_in'), e.get('wake_up'))
        dow_data[dow].append({'mood': mood, 'energy': energy, 'sleep': dur})

    lines.append(f"  {'星期':6} {'天數':5} {'心情':6} {'精力':6} {'睡眠h':7}")
    best_dow = None
    best_mood = 0
    worst_dow = None
    worst_mood = 5

    for dow in range(7):
        days = dow_data[dow]
        moods = [d['mood'] for d in days if d['mood']]
        energies = [d['energy'] for d in days if d['energy']]
        sleeps = [d['sleep'] / 60 for d in days if d['sleep']]
        m = statistics.mean(moods) if moods else 0
        en = statistics.mean(energies) if energies else 0
        sl = statistics.mean(sleeps) if sleeps else 0
        marker = ""
        if m > best_mood and moods:
            best_mood = m
            best_dow = dow
        if m < worst_mood and moods:
            worst_mood = m
            worst_dow = dow
        lines.append(f"  週{DOW_NAMES[dow]} {len(days):5d} {m:6.2f} {en:6.2f} {sl:7.1f}")

    if best_dow is not None and worst_dow is not None:
        lines.append(f"\n  最佳: 週{DOW_NAMES[best_dow]} ({best_mood:.2f})")
        lines.append(f"  最差: 週{DOW_NAMES[worst_dow]} ({worst_mood:.2f})")
        lines.append(f"  差距: {best_mood - worst_mood:.2f}")

    lines.append("")
    return lines


def section_monthly(entries):
    """Monthly trend analysis."""
    lines = []
    lines.append("## 📈 月度趨勢")
    lines.append("")

    monthly = defaultdict(list)
    for e in entries:
        month = e['date'][:7]
        mood = int(e['mood']) if e.get('mood', '').strip().isdigit() else None
        energy = int(e['energy']) if e.get('energy', '').strip().isdigit() else None
        dur = sleep_duration_minutes(e.get('sleep_in'), e.get('wake_up'))
        monthly[month].append({'mood': mood, 'energy': energy, 'sleep': dur})

    prev_mood = None
    lines.append(f"  {'月份':8} {'天':4} {'心情':6} {'精力':6} {'睡眠h':7} {'趨勢':8}")
    for month in sorted(monthly.keys()):
        days = monthly[month]
        moods = [d['mood'] for d in days if d['mood']]
        energies = [d['energy'] for d in days if d['energy']]
        sleeps = [d['sleep'] / 60 for d in days if d['sleep']]
        m = statistics.mean(moods) if moods else 0
        en = statistics.mean(energies) if energies else 0
        sl = statistics.mean(sleeps) if sleeps else 0
        trend = ""
        if prev_mood is not None:
            diff = m - prev_mood
            trend = f"{'📈' if diff > 0.1 else '📉' if diff < -0.1 else '➡️'}{diff:+.2f}"
        prev_mood = m
        bar = '█' * round(m * 2) + '░' * (10 - round(m * 2))
        lines.append(f"  {month} {len(days):4d} {m:6.2f} {en:6.2f} {sl:7.1f}  {bar} {trend}")

    lines.append("")
    return lines


def section_people(entries):
    """People × mood/energy correlation using tags."""
    lines = []
    lines.append("## 👥 人物 × 心情相關性")
    lines.append("")

    overall_moods = [int(e['mood']) for e in entries if e.get('mood', '').strip().isdigit()]
    if not overall_moods:
        return lines
    overall_mood = statistics.mean(overall_moods)

    # Load tags and match with diary entries
    entry_by_date = {e['date']: e for e in entries}
    people_data = defaultdict(lambda: {'moods': [], 'energies': []})

    for tag_file in TAGS_DIR.glob('*.json'):
        d = tag_file.stem
        if d not in entry_by_date:
            continue
        e = entry_by_date[d]
        mood = e.get('mood', '')
        energy = e.get('energy', '')
        if not mood.strip().isdigit():
            continue

        tag = json.loads(tag_file.read_text())
        m = int(mood)
        en = int(energy) if energy.strip().isdigit() else None

        for person in tag.get('people', []):
            people_data[person]['moods'].append(m)
            if en is not None:
                people_data[person]['energies'].append(en)

    ranked = []
    for person, data in people_data.items():
        if len(data['moods']) >= 3:
            avg_mood = statistics.mean(data['moods'])
            avg_energy = statistics.mean(data['energies']) if data['energies'] else 0
            ranked.append((person, len(data['moods']), avg_mood, avg_mood - overall_mood, avg_energy))

    ranked.sort(key=lambda x: -x[1])  # sort by frequency

    tag_method_counts = Counter()
    for tf in TAGS_DIR.glob('*.json'):
        t = json.loads(tf.read_text())
        tag_method_counts[t.get('method', 'unknown')] += 1

    lines.append(f"  標籤品質: {dict(tag_method_counts)}")
    lines.append(f"  整體平均心情: {overall_mood:.2f}")
    lines.append("")
    lines.append(f"  {'人物':12} {'出現天數':8} {'平均心情':8} {'差異':8}")

    for person, count, mood, diff, energy in ranked[:15]:
        icon = "↑" if diff > 0.05 else "↓" if diff < -0.05 else "="
        lines.append(f"  {person:12} {count:8d} {mood:8.2f} {diff:+8.2f}{icon}")

    lines.append("")
    return lines


def section_research(entries):
    """Research momentum tracking from tags."""
    lines = []
    lines.append("## 🔬 研究動能追蹤")
    lines.append("")

    entry_dates = set(e['date'] for e in entries)
    weeks = defaultdict(lambda: {'total': 0, 'research': 0, 'audiomatters': 0})

    for tag_file in sorted(TAGS_DIR.glob('*.json')):
        d = tag_file.stem
        if d not in entry_dates:
            continue
        tag = json.loads(tag_file.read_text())
        dt = datetime.strptime(d, '%Y-%m-%d').date()
        week_start = (dt - timedelta(days=dt.weekday())).isoformat()

        weeks[week_start]['total'] += 1
        topics = tag.get('topics', [])
        if '研究/實驗' in topics or 'AudioMatters' in topics:
            weeks[week_start]['research'] += 1
        if 'AudioMatters' in topics:
            weeks[week_start]['audiomatters'] += 1

    sorted_weeks = sorted(weeks.items())[-12:]
    if sorted_weeks:
        lines.append(f"  {'週':12} {'天數':4} {'研究天':6} {'AM天':5} {'研究率':6}")
        for w, data in sorted_weeks:
            total = data['total']
            res = data['research']
            am = data['audiomatters']
            rate = res / total * 100 if total else 0
            bar = '█' * am + '▒' * (res - am) + '░' * (total - res)
            lines.append(f"  {w} {total:4d} {res:6d} {am:5d} {rate:5.0f}%  {bar}")
        lines.append(f"\n  █=AudioMatters ▒=其他研究 ░=非研究")

    lines.append("")
    return lines


def generate_report(days=None, sections=None):
    entries = load_entries(days)
    if not entries:
        return "No data available."

    all_sections = {
        'sleep': section_sleep,
        'habits': section_habits,
        'dow': section_dow,
        'monthly': section_monthly,
        'people': section_people,
        'research': section_research,
    }

    lines = []
    period = f"最近 {days} 天" if days else f"全部 ({entries[0]['date']} → {entries[-1]['date']})"
    lines.append(f"# 📊 Leo 日記深度分析報告")
    lines.append(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"分析範圍: {period} ({len(entries)} 條)")
    lines.append("")

    targets = sections if sections else list(all_sections.keys())
    for s in targets:
        if s in all_sections:
            lines.extend(all_sections[s](entries))

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Leo 日記深度分析')
    parser.add_argument('--days', type=int, help='最近 N 天')
    parser.add_argument('--section', type=str, help='只看特定段: sleep|habits|dow|monthly|people|research')
    parser.add_argument('--json', action='store_true', help='JSON output')
    args = parser.parse_args()

    sections = [args.section] if args.section else None
    report = generate_report(days=args.days, sections=sections)
    print(report)


if __name__ == '__main__':
    main()
