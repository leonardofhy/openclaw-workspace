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
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'lib'))

from read_diary import load_diary
from email_utils import send_email
from sleep_calc import analyze_sleep, format_duration, parse_hhmm, sleep_duration_minutes
from common import TZ, now as _now, TAGS_DIR


def check_trends(days=7):
    """Read recent tags and detect actionable patterns. Pure Python, no LLM.

    Returns list of alert strings (empty = nothing notable).
    """
    import glob

    alerts = []
    today = _now().date()

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

        today = _now().strftime('%Y-%m-%d')
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


def _parse_last_entry(entries, today_str, yesterday_str):
    """Extract and parse the latest diary entry. Returns dict or None."""
    if not entries:
        return None
    last = entries[0]
    last_date = last.get('date', '')
    if last_date < yesterday_str:
        print(f"📅 Last diary is old ({last_date}). No coaching today.")
        return None

    def safe_float(val, default=4.0):
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    mood_raw = last.get('mood', '?')
    energy_raw = last.get('energy', '?')
    si = last.get('sleep_in', '')
    wu = last.get('wake_up', '')
    si_parsed = parse_hhmm(si)
    wu_parsed = parse_hhmm(wu)
    sq_raw = last.get('sleep_quality', '')

    # Late sleep streak
    late_streak = 0
    for e in entries[:7]:
        s = parse_hhmm(e.get('sleep_in', ''))
        if s and 2 <= s[0] < 8:
            late_streak += 1
        else:
            break

    return {
        'date': last_date,
        'day_label': "今日" if last_date == today_str else "昨日",
        'mood_raw': mood_raw,
        'energy_raw': energy_raw,
        'mood': safe_float(mood_raw),
        'energy': safe_float(energy_raw),
        'si_fmt': f"{si_parsed[0]:02d}:{si_parsed[1]:02d}" if si_parsed else str(si),
        'wu_fmt': f"{wu_parsed[0]:02d}:{wu_parsed[1]:02d}" if wu_parsed else str(wu),
        'duration': sleep_duration_minutes(si, wu),
        'sq': int(sq_raw) if sq_raw.strip().isdigit() and 1 <= int(sq_raw) <= 5 else None,
        'late_streak': late_streak,
    }


def _build_status_block(ctx):
    """Status + sleep quality section."""
    lines = []
    lines.append(f"📊 **{ctx['day_label']}狀態** ({ctx['date']})")
    lines.append(f"  心情：{'⭐' * int(ctx['mood'])}{'☆' * (5-int(ctx['mood']))} {ctx['mood_raw']}/5")
    lines.append(f"  精力：{'⚡' * int(ctx['energy'])}{'·' * (5-int(ctx['energy']))} {ctx['energy_raw']}/5")
    dur_fmt = format_duration(ctx['duration'])
    sleep_line = f"  昨晚睡眠：{ctx['si_fmt']} 入睡 → {ctx['wu_fmt']} 起床（共 {dur_fmt}）"
    if ctx['sq'] is not None:
        sq_stars = '★' * ctx['sq'] + '☆' * (5 - ctx['sq'])
        sleep_line += f"\n  睡眠品質：{sq_stars} {ctx['sq']}/5"
    lines.append(sleep_line)
    return lines


def _build_sleep_alert(ctx, sleep_stats):
    """Late sleep warning section. Returns list of lines (may be empty)."""
    lines = []
    late = ctx['late_streak']
    if late >= 3:
        lines.append(f"🛑 **晚睡警報** — 連續 {late} 天凌晨 2 點後才睡！")
        if sleep_stats:
            lines.append(f"  近 7 天平均睡眠：{sleep_stats['avg_duration_fmt']}，"
                         f"晚睡率 {sleep_stats['late_sleep_ratio']*100:.0f}%")
        lines.append(f"  今晚目標：01:00 前上床。手機放遠一點。")
    elif sleep_stats and sleep_stats['late_sleep_ratio'] > 0.5:
        lines.append(f"⚠️ 近 7 天晚睡率 {sleep_stats['late_sleep_ratio']*100:.0f}%，"
                     f"平均睡 {sleep_stats['avg_duration_fmt']}。注意作息。")
    return lines


def _build_observations(ctx):
    """Coach observations based on sleep, mood, energy."""
    obs = []
    dur = ctx['duration']
    sq = ctx['sq']
    dur_fmt = format_duration(dur)

    if dur and dur < 360:
        obs.append(f"昨晚只睡了 {dur_fmt}，今天下午可能會有睡意，記得補個短午覺。")
    elif sq is not None and sq <= 3 and dur and dur >= 360:
        obs.append(f"睡眠時間夠但品質不佳（{sq}/5）。品質比時長更影響你的心情，留意今天狀態。")
    elif sq is not None and sq >= 5 and dur and dur >= 420:
        obs.append(f"睡眠品質滿分 + 充足時長，今天是最佳狀態日！適合衝刺重要任務。")

    if ctx['mood'] >= 5:
        obs.append("心情滿分！保持這個狀態，今天適合做核心任務。")
    elif ctx['mood'] <= 3:
        obs.append("心情偏低。今天允許自己「低空飛過」，完成一件小事就好。")

    if ctx['energy'] >= 5:
        obs.append("精力充沛，是衝刺的好時機。")
    elif ctx['energy'] <= 3:
        obs.append("精力偏低，優先做輕量任務，避免高消耗。")

    return obs or ["平穩的一天。試著在中午前完成一件重要的事吧。"]


def _build_calendar_block(calendar):
    """Format calendar events."""
    if not calendar:
        return []
    lines = ["📅 **今日行程**"]
    for ev in calendar:
        if ev['all_day']:
            lines.append(f"  • [全天] {ev['summary']}")
        else:
            t = ev['start'].split('T')[1][:5] if 'T' in ev['start'] else ev['start']
            lines.append(f"  • [{t}] {ev['summary']}")
    return lines


def _build_todoist_block(todoist):
    """Format Todoist tasks."""
    if not todoist or 'error' in todoist:
        return []
    lines = []
    if todoist['today_count'] > 0:
        lines.append(f"📋 **今日待辦** ({todoist['today_count']} 項)")
        for t in todoist['today'][:5]:
            lines.append(f"  □ {t}")
        if todoist['today_count'] > 5:
            lines.append(f"  ...及其他 {todoist['today_count']-5} 項")

    if todoist['overdue_count'] > 0:
        if lines:
            lines.append("")
        lines.append(f"⚠️ **過期未完成** ({todoist['overdue_count']} 項)")
        for t in todoist['overdue'][:3]:
            lines.append(f"  □ {t}")
        if todoist['overdue_count'] > 3:
            lines.append(f"  ...及其他 {todoist['overdue_count']-3} 項")
    return lines


def build_email():
    """Build the daily coach email content."""
    now = _now()
    today_str = now.strftime('%Y-%m-%d')
    yesterday_str = (now - timedelta(days=1)).strftime('%Y-%m-%d')

    # Gather data
    entries = get_diary_data()
    ctx = _parse_last_entry(entries, today_str, yesterday_str)
    if ctx is None:
        return None, None

    sleep_stats = analyze_sleep(7)
    todoist = get_todoist_summary()
    calendar = get_calendar_summary()

    # Subject
    if ctx['late_streak'] >= 3:
        subject = f"🚨 警報！連續 {ctx['late_streak']} 天晚睡 ({today_str})"
    else:
        subject = f"🦁 Daily Coach ({today_str})"

    # Assemble sections
    sections = []
    sections.append([f"Leo，{'午' if now.hour >= 12 else '早'}安！"])
    sections.append(_build_status_block(ctx))
    sections.append(_build_sleep_alert(ctx, sleep_stats))

    obs = _build_observations(ctx)
    sections.append(["🦁 **教練觀察**"] + [f"  • {o}" for o in obs])

    trends = check_trends(7)
    if trends:
        sections.append(["📈 **趨勢提醒**"] + [f"  • {t}" for t in trends])

    sections.append(_build_calendar_block(calendar))
    sections.append(_build_todoist_block(todoist))

    # Daily tip
    tip_lines = ["💡 **今日建議**"]
    if ctx['late_streak'] > 0:
        tip_lines.append("  今晚試著比昨天早 30 分鐘上床。短影音是最大的敵人。")
    elif ctx['duration'] and ctx['duration'] > 480:
        tip_lines.append("  睡眠充足！趁狀態好，挑一件一直拖延的事，今天搞定它。")
    else:
        tip_lines.append("  出門走走，曬曬太陽。動一動對調整作息和心情都有幫助。")
    sections.append(tip_lines)

    sections.append(["-- Little Leo 🦁"])

    # Join non-empty sections with blank lines
    body = "\n\n".join("\n".join(s) for s in sections if s)
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
