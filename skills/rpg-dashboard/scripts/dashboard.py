#!/usr/bin/env python3
"""Unified dashboard — single process, single API call, all data shared.

Usage:
  python3 dashboard.py              # full dashboard (schedule + RPG)
  python3 dashboard.py --schedule   # schedule only
  python3 dashboard.py --rpg        # RPG panel only
"""
import sys
import argparse
from pathlib import Path

# Wire up imports
WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(WORKSPACE / 'skills' / 'lib'))
sys.path.insert(0, str(WORKSPACE / 'skills' / 'daily-scheduler' / 'scripts'))
sys.path.insert(0, str(WORKSPACE / 'skills' / 'leo-diary' / 'scripts'))

from common import now as _now, TZ, today_str as _today_str


def fetch_all():
    """Single data fetch — one API call per service, shared across panels."""
    from schedule_data import get_calendar, get_todoist, get_medication_schedule, get_time_info
    from rpg_dashboard import build_status

    todoist_raw = get_todoist()

    # Convert schedule_data todoist format → rpg_dashboard prefetch tuple
    todoist_prefetch = None
    if todoist_raw and 'error' not in todoist_raw:
        today_count = len(todoist_raw.get('due_today', []))
        overdue_count = len(todoist_raw.get('overdue', []))
        hp = todoist_raw.get('high_priority', [])
        quests = [t['content'][:50] for t in hp[:3]]
        todoist_prefetch = (today_count, overdue_count, quests)

    data = {
        'time':       get_time_info(),
        'calendar':   get_calendar(days_range=1),
        'todoist':    todoist_raw,
        'medication': get_medication_schedule(),
        'status':     build_status(todoist_prefetch=todoist_prefetch),
    }
    return data


def render_schedule(data):
    """Pretty-print schedule with NOW marker and countdown.

    Priority: read from schedule file (memory/schedules/YYYY-MM-DD.md).
    Fallback: raw calendar events (when no schedule file exists).
    """
    time_info = data['time']
    now_str = time_info['now']

    print(f"📅 {time_info['date']}  ⏰ 現在 {now_str}")
    print(f"   剩餘可用時間：~{time_info['remaining_hours']}h（目標 {time_info['bedtime_target']} 前就寢）")
    print()

    # ── Try reading from schedule file first ──
    schedule_rendered = False
    try:
        from schedule_engine import parse_schedule, render_display
        today = _today_str()
        schedule_path = WORKSPACE / 'memory' / 'schedules' / f'{today}.md'
        schedule = parse_schedule(schedule_path)
        if schedule and schedule.blocks:
            print("── 時間軸（排程檔案）──")
            print(render_display(schedule, now_str))
            print()
            schedule_rendered = True
    except Exception as e:
        # Import or parse failure — fall through to calendar fallback
        import sys as _sys
        print(f"  ⚠️ 排程檔案讀取失敗：{e}，改用行事曆", file=_sys.stderr)

    # ── Fallback: raw calendar rendering ──
    if not schedule_rendered:
        now_minutes = int(now_str[:2]) * 60 + int(now_str[3:5])

        # Build timeline
        timeline = []
        for ev in data.get('calendar', []):
            if ev.get('error'):
                continue
            start = ev['start']
            if 'T' in start:
                t = start.split('T')[1][:5]
                t_min = int(t[:2]) * 60 + int(t[3:5])
            else:
                t = '全天'
                t_min = 0
            end_t = ''
            end_min = 0
            if 'T' in ev.get('end', ''):
                end_t = ev['end'].split('T')[1][:5]
                end_min = int(end_t[:2]) * 60 + int(end_t[3:5])
            timeline.append({
                'time': t, 'minutes': t_min, 'end': end_t, 'end_minutes': end_min,
                'title': ev['title'], 'location': ev.get('location', ''),
            })
        timeline.sort(key=lambda x: x['minutes'])

        # Find next upcoming event for countdown
        next_event = None
        active_event = None
        for item in timeline:
            end_min = item.get('end_minutes', 0)
            if end_min and item['minutes'] <= now_minutes < end_min:
                active_event = item
            elif item['minutes'] > now_minutes and next_event is None:
                next_event = item

        # Print timeline
        print("── 時間軸（行事曆）──")
        now_printed = False
        for item in timeline:
            if not now_printed and item['minutes'] > now_minutes:
                print(f"  ▶ {now_str}  ← 現在")
                now_printed = True

            end_min = item.get('end_minutes', 0)
            if end_min and item['minutes'] <= now_minutes < end_min:
                elapsed = now_minutes - item['minutes']
                total = end_min - item['minutes']
                remaining = end_min - now_minutes
                pct = int(elapsed / total * 100) if total else 0
                icon = "🔵"
                suffix = f"  ({remaining}m 後結束)"
            elif item['minutes'] <= now_minutes and (not end_min or now_minutes >= end_min):
                icon = "✅"
                suffix = ""
            else:
                icon = "⏳"
                suffix = ""

            loc = f" @ {item['location']}" if item['location'] else ""
            end = f"–{item['end']}" if item['end'] else ""
            print(f"  {icon} {item['time']}{end}  {item['title']}{loc}{suffix}")

        if not now_printed:
            print(f"  ▶ {now_str}  ← 現在（今日行程已結束）")

        # Next event countdown
        if next_event:
            delta = next_event['minutes'] - now_minutes
            h, m = divmod(delta, 60)
            countdown = f"{h}h{m:02d}m" if h else f"{m}m"
            print(f"\n  ⏭️  下一個：{next_event['time']}  {next_event['title']}（{countdown} 後）")
        print()

    # Todoist
    todoist = data.get('todoist', {})
    if todoist and 'error' not in todoist:
        sections = [
            ('🔴 逾期', todoist.get('overdue', [])),
            ('📋 今日', todoist.get('due_today', [])),
            ('⭐ 高優先', todoist.get('high_priority', [])),
        ]
        has_tasks = any(items for _, items in sections)
        if has_tasks:
            print("── 待辦 ──")
            for label, items in sections:
                if items:
                    print(f"  {label}:")
                    for t in items[:5]:
                        p = {4: '🔴', 3: '🟡', 2: '🔵', 1: '⚪'}.get(t['priority'], '⚪')
                        print(f"    {p} {t['content']}")
            print()

    # Medication
    meds = data.get('medication')
    if meds and meds.get('upcoming_today'):
        print("── 💊 吃藥提醒 ──")
        for s in meds['upcoming_today']:
            print(f"  {s['time']}  {', '.join(s['drugs'])}")
        print()


def render_rpg(data):
    """Print RPG panel from pre-fetched status."""
    from rpg_dashboard import render_discord
    s = data['status']
    print(render_discord(s))


def main():
    parser = argparse.ArgumentParser(description='Unified dashboard')
    parser.add_argument('--schedule', action='store_true', help='Schedule only')
    parser.add_argument('--rpg', action='store_true', help='RPG panel only')
    args = parser.parse_args()

    show_all = not args.schedule and not args.rpg

    try:
        data = fetch_all()
    except Exception as e:
        print(f"❌ 資料取得失敗：{e}", file=sys.stderr)
        return

    if show_all or args.schedule:
        try:
            render_schedule(data)
        except Exception as e:
            print(f"⚠️ 時間軸渲染失敗：{e}", file=sys.stderr)

    if show_all or args.rpg:
        try:
            render_rpg(data)
        except Exception as e:
            print(f"⚠️ RPG 面板渲染失敗：{e}", file=sys.stderr)


if __name__ == '__main__':
    main()
