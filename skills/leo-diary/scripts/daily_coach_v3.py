#!/usr/bin/env python3
"""Daily Coach v3 — comprehensive morning briefing.

Integrates: diary, sleep analysis, Todoist, Google Calendar.
Outputs: rich email with actionable insights.
"""
import sys
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPTS = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS))

from read_diary import load_diary
from email_utils import send_email
from sleep_calc import analyze_sleep, format_duration, parse_hhmm, sleep_duration_minutes

TZ = timezone(timedelta(hours=8))
TAGS_DIR = SCRIPTS.parent.parent.parent / 'memory' / 'tags'


def check_trends(days=7):
    """Read recent tags and detect actionable patterns. Pure Python, no LLM.

    Returns list of alert strings (empty = nothing notable).
    """
    import glob

    alerts = []
    today = datetime.now(TZ).date()

    # Load tags for [days] and [days*2] windows
    def load_window(n):
        tags = []
        for i in range(n):
            d = (today - timedelta(days=i+1)).strftime('%Y-%m-%d')
            p = TAGS_DIR / f'{d}.json'
            if p.exists():
                with open(p, 'r') as f:
                    tags.append(json.load(f))
        return tags

    this_week = load_window(days)
    last_week = load_window(days * 2)[days:]  # previous window

    if len(this_week) < 3:
        return []  # not enough data

    # --- 1. Exercise gap ---
    exercise_topics = {'游泳', '運動'}
    exercise_days = sum(1 for t in this_week
                        if exercise_topics & set(t.get('topics', [])))
    last_exercise = None
    for i in range(days * 3):
        d = (today - timedelta(days=i+1)).strftime('%Y-%m-%d')
        p = TAGS_DIR / f'{d}.json'
        if p.exists():
            with open(p, 'r') as f:
                t = json.load(f)
            if exercise_topics & set(t.get('topics', [])):
                last_exercise = i + 1
                break

    if last_exercise and last_exercise >= 14:
        alerts.append(f"🏊 已經 {last_exercise} 天沒有運動/游泳記錄了。動一動？")
    elif exercise_days == 0 and len(this_week) >= 5:
        alerts.append("🏊 本週尚無運動記錄。找個時間去游泳吧。")

    # --- 2. Mood trend ---
    def avg_metric(tags, key):
        vals = []
        for t in tags:
            m = t.get('metrics', {}).get(key)
            if m is not None:
                vals.append(m)
        return sum(vals) / len(vals) if vals else None

    mood_now = avg_metric(this_week, 'mood')
    mood_prev = avg_metric(last_week, 'mood')

    if mood_now is not None and mood_now <= 3.0:
        alerts.append(f"😔 近 {days} 天心情均值 {mood_now:.1f}/5，偏低。今天對自己好一點。")
    elif mood_now and mood_prev and (mood_prev - mood_now) >= 1.0:
        alerts.append(f"📉 心情趨勢下降：上週 {mood_prev:.1f} → 本週 {mood_now:.1f}。留意狀態。")

    # --- 3. Social check ---
    social_days = sum(1 for t in this_week
                      if '社交/聚餐' in t.get('topics', []))
    if social_days == 0 and len(this_week) >= 5:
        alerts.append("👥 本週還沒有社交記錄。找明淵或朗軒吃個飯？")

    # --- 4. Late sleep ratio (7-day) ---
    late_days = sum(1 for t in this_week if t.get('late_sleep'))
    if late_days >= 5:
        alerts.append(f"🌙 本週 {late_days}/{len(this_week)} 天晚睡。作息需要調整。")

    return alerts


def get_todoist_summary():
    """Get today's tasks and overdue count."""
    try:
        from todoist_sync import load_token, get
        token = load_token()
        tasks = get('/tasks', token).get('results', [])
        tasks = [t for t in tasks if not t.get('completed_at')]

        today = datetime.now(TZ).strftime('%Y-%m-%d')
        today_tasks = []
        overdue_tasks = []

        for t in tasks:
            due = (t.get('due') or {}).get('date', '')
            if due.startswith(today):
                today_tasks.append(t['content'])
            elif due and due < today:
                overdue_tasks.append(t['content'])

        return {
            'total': len(tasks),
            'today': today_tasks,
            'today_count': len(today_tasks),
            'overdue': overdue_tasks,
            'overdue_count': len(overdue_tasks),
        }
    except Exception as e:
        return {'error': str(e)}


def get_calendar_summary():
    """Get today's calendar events."""
    try:
        from gcal_today import get_events
        events = get_events(days_ahead=0, days_range=1)
        return [{
            'summary': e['summary'],
            'start': e['start'],
            'all_day': e['all_day'],
        } for e in events]
    except Exception as e:
        return []


def get_diary_data():
    """Get recent diary entries, deduplicated by date."""
    entries = load_diary()
    if not entries:
        return []

    entries.sort(key=lambda x: x.get('date', ''), reverse=True)
    seen = set()
    unique = []
    for e in entries:
        d = e.get('date', '')
        if d not in seen:
            seen.add(d)
            unique.append(e)
    return unique


def build_email():
    """Build the daily coach email content."""
    now = datetime.now(TZ)
    today_str = now.strftime('%Y-%m-%d')
    yesterday_str = (now - timedelta(days=1)).strftime('%Y-%m-%d')

    # Gather data
    entries = get_diary_data()
    sleep = analyze_sleep(7)
    todoist = get_todoist_summary()
    calendar = get_calendar_summary()

    # Find latest entry
    if not entries:
        return None, None

    last = entries[0]
    last_date = last.get('date', '')

    if last_date < yesterday_str:
        print(f"📅 Last diary is old ({last_date}). No coaching today.")
        return None, None

    day_label = "今日" if last_date == today_str else "昨日"

    # Parse mood/energy
    mood = last.get('mood', '?')
    energy = last.get('energy', '?')
    try:
        mood_val = float(mood)
    except (ValueError, TypeError):
        mood_val = 4.0
    try:
        energy_val = float(energy)
    except (ValueError, TypeError):
        energy_val = 4.0

    # Sleep data for last night
    si = last.get('sleep_in', '')
    wu = last.get('wake_up', '')
    si_parsed = parse_hhmm(si)
    wu_parsed = parse_hhmm(wu)
    si_fmt = f"{si_parsed[0]:02d}:{si_parsed[1]:02d}" if si_parsed else str(si)
    wu_fmt = f"{wu_parsed[0]:02d}:{wu_parsed[1]:02d}" if wu_parsed else str(wu)
    duration = sleep_duration_minutes(si, wu)
    dur_fmt = format_duration(duration)

    # Check late sleep streak
    late_streak = 0
    for e in entries[:7]:
        s = parse_hhmm(e.get('sleep_in', ''))
        if s and 2 <= s[0] < 8:
            late_streak += 1
        else:
            break

    # === Build Email ===
    is_alert = late_streak >= 3

    if is_alert:
        subject = f"🚨 警報！連續 {late_streak} 天晚睡 ({today_str})"
    else:
        subject = f"🦁 Daily Coach ({today_str})"

    lines = []
    lines.append(f"Leo，{'午' if now.hour >= 12 else '早'}安！\n")

    # --- Status Block ---
    lines.append(f"📊 **{day_label}狀態** ({last_date})")
    lines.append(f"  心情：{'⭐' * int(mood_val)}{'☆' * (5-int(mood_val))} {mood}/5")
    lines.append(f"  精力：{'⚡' * int(energy_val)}{'·' * (5-int(energy_val))} {energy}/5")
    lines.append(f"  昨晚睡眠：{si_fmt} 入睡 → {wu_fmt} 起床（共 {dur_fmt}）")
    lines.append("")

    # --- Sleep Alert ---
    if is_alert:
        lines.append(f"🛑 **晚睡警報** — 連續 {late_streak} 天凌晨 2 點後才睡！")
        if sleep:
            lines.append(f"  近 7 天平均睡眠：{sleep['avg_duration_fmt']}，"
                        f"晚睡率 {sleep['late_sleep_ratio']*100:.0f}%")
        lines.append(f"  今晚目標：01:00 前上床。手機放遠一點。")
        lines.append("")
    elif sleep and sleep['late_sleep_ratio'] > 0.5:
        lines.append(f"⚠️ 近 7 天晚睡率 {sleep['late_sleep_ratio']*100:.0f}%，"
                    f"平均睡 {sleep['avg_duration_fmt']}。注意作息。")
        lines.append("")

    # --- Coach Observation ---
    lines.append("🦁 **教練觀察**")
    observations = []

    if duration and duration < 360:  # < 6 hours
        observations.append(f"昨晚只睡了 {dur_fmt}，今天下午可能會有睡意，記得補個短午覺。")
    
    if mood_val >= 5:
        observations.append(f"心情滿分！保持這個狀態，今天適合做核心任務。")
    elif mood_val <= 3:
        observations.append(f"心情偏低。今天允許自己「低空飛過」，完成一件小事就好。")

    if energy_val >= 5:
        observations.append("精力充沛，是衝刺的好時機。")
    elif energy_val <= 3:
        observations.append("精力偏低，優先做輕量任務，避免高消耗。")

    if not observations:
        observations.append("平穩的一天。試著在中午前完成一件重要的事吧。")

    for obs in observations:
        lines.append(f"  • {obs}")
    lines.append("")

    # --- Trend Alerts (from tags) ---
    trends = check_trends(7)
    if trends:
        lines.append("📈 **趨勢提醒**")
        for t in trends:
            lines.append(f"  • {t}")
        lines.append("")

    # --- Calendar ---
    if calendar:
        lines.append("📅 **今日行程**")
        for ev in calendar:
            if ev['all_day']:
                lines.append(f"  • [全天] {ev['summary']}")
            else:
                t = ev['start'].split('T')[1][:5] if 'T' in ev['start'] else ev['start']
                lines.append(f"  • [{t}] {ev['summary']}")
        lines.append("")

    # --- Todoist ---
    if todoist and 'error' not in todoist:
        if todoist['today_count'] > 0:
            lines.append(f"📋 **今日待辦** ({todoist['today_count']} 項)")
            for t in todoist['today'][:5]:
                lines.append(f"  □ {t}")
            if todoist['today_count'] > 5:
                lines.append(f"  ...及其他 {todoist['today_count']-5} 項")
            lines.append("")

        if todoist['overdue_count'] > 0:
            lines.append(f"⚠️ **過期未完成** ({todoist['overdue_count']} 項)")
            for t in todoist['overdue'][:3]:
                lines.append(f"  □ {t}")
            if todoist['overdue_count'] > 3:
                lines.append(f"  ...及其他 {todoist['overdue_count']-3} 項")
            lines.append("")

    # --- Tip ---
    lines.append("💡 **今日建議**")
    if late_streak > 0:
        lines.append("  今晚試著比昨天早 30 分鐘上床。短影音是最大的敵人。")
    elif duration and duration > 480:
        lines.append("  睡眠充足！趁狀態好，挑一件一直拖延的事，今天搞定它。")
    else:
        lines.append("  出門走走，曬曬太陽。動一動對調整作息和心情都有幫助。")

    lines.append("")
    lines.append("-- Little Leo 🦁")

    body = "\n".join(lines)
    return subject, body


def main():
    subject, body = build_email()
    if not subject:
        print("No coaching today (diary too old).")
        return

    print(f"Subject: {subject}")
    print("=" * 50)
    print(body)
    print("=" * 50)

    if send_email(subject, body, sender_label='Little Leo Coach'):
        print("✅ Notification sent.")
    else:
        print("❌ Notification failed.")


if __name__ == "__main__":
    main()
