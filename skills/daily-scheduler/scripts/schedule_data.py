#!/usr/bin/env python3
"""schedule_data.py — fetch all data needed for daily scheduling.

Outputs a JSON snapshot of:
  - Current time + remaining hours today
  - Google Calendar events (today + tomorrow)
  - Todoist tasks (due today, overdue, high priority)
  - Today's memory context (health, mood, energy)
  - Known upcoming deadlines
  - Medication schedule (if active)

Usage:
  python3 schedule_data.py
  python3 schedule_data.py --tomorrow   # include tomorrow's calendar
"""
import json
import sys
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
SCRIPTS   = WORKSPACE / 'skills' / 'leo-diary' / 'scripts'
MEMORY    = WORKSPACE / 'memory'
TZ        = timezone(timedelta(hours=8))
NOW       = datetime.now(TZ)

sys.path.insert(0, str(SCRIPTS))


def get_calendar(days_range=1):
    try:
        from gcal_today import get_events
        events = get_events(days_ahead=0, days_range=days_range)
        result = []
        for e in events:
            result.append({
                'title':    e.get('summary', '?'),
                'start':    e.get('start', ''),
                'end':      e.get('end', ''),
                'location': e.get('location', ''),
                'all_day':  e.get('all_day', False),
            })
        return sorted(result, key=lambda x: x['start'])
    except Exception as ex:
        return [{'error': str(ex)}]


def get_todoist():
    try:
        env_path = WORKSPACE / 'secrets' / 'todoist.env'
        token = None
        for line in env_path.read_text().splitlines():
            if 'TODOIST_API_TOKEN' in line:
                token = line.split('=', 1)[-1].strip()
        if not token:
            return {'error': 'no token'}

        import urllib.request
        today_str = NOW.strftime('%Y-%m-%d')

        req = urllib.request.Request(
            'https://api.todoist.com/api/v1/tasks?limit=50',
            headers={'Authorization': f'Bearer {token}'}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            # v1 API returns {"results": [...], "next_cursor": ...}
            tasks = data.get('results', data) if isinstance(data, dict) else data

        due_today, overdue, high_priority, no_due = [], [], [], []
        for t in tasks:
            due_raw = t.get('due')
            due = (due_raw.get('date', '') if isinstance(due_raw, dict) else '') if due_raw else ''
            content = t.get('content', '')
            priority = t.get('priority', 1)  # 4=P1, 3=P2, 2=P3, 1=P4
            item = {'content': content, 'due': due, 'priority': priority, 'id': t.get('id')}

            if due == today_str:
                due_today.append(item)
            elif due and due < today_str:
                overdue.append(item)
            elif priority >= 3:
                high_priority.append(item)
            elif not due:
                no_due.append(item)

        # Sort by priority desc
        for lst in [due_today, overdue, high_priority]:
            lst.sort(key=lambda x: -x['priority'])

        return {
            'due_today':      due_today[:15],
            'overdue':        overdue[:10],
            'high_priority':  high_priority[:5],
            'total_tasks':    len(tasks),
        }
    except Exception as ex:
        return {'error': str(ex)}


def get_memory_context():
    """Read today's and yesterday's memory for health/mood context."""
    today     = NOW.strftime('%Y-%m-%d')
    yesterday = (NOW - timedelta(days=1)).strftime('%Y-%m-%d')
    context   = {}

    for label, date_str in [('today', today), ('yesterday', yesterday)]:
        p = MEMORY / f'{date_str}.md'
        if p.exists():
            text = p.read_text()[:2000]  # first 2000 chars
            context[label] = {'date': date_str, 'preview': text}

    # Also check tags for mood/energy/sleep
    tags_dir = MEMORY / 'tags'
    today_tag = tags_dir / f'{today}.json'
    if today_tag.exists():
        try:
            context['metrics_today'] = json.loads(today_tag.read_text()).get('metrics', {})
        except Exception:
            pass

    yesterday_tag = tags_dir / f'{yesterday}.json'
    if yesterday_tag.exists():
        try:
            context['metrics_yesterday'] = json.loads(yesterday_tag.read_text()).get('metrics', {})
        except Exception:
            pass

    return context


def get_time_info():
    now_str    = NOW.strftime('%H:%M')
    now_hour   = NOW.hour + NOW.minute / 60
    bedtime    = 23.0  # Leo's target bedtime
    remaining  = max(0, bedtime - now_hour)
    return {
        'now':              now_str,
        'date':             NOW.strftime('%Y-%m-%d (%A)'),
        'hour_float':       round(now_hour, 2),
        'remaining_hours':  round(remaining, 1),
        'bedtime_target':   '23:00',
        'phase': (
            'morning'   if now_hour < 12 else
            'afternoon' if now_hour < 17 else
            'evening'   if now_hour < 21 else
            'night'
        ),
    }


def get_medication_schedule():
    """Return any active medication reminders (hardcoded for current prescription)."""
    # Check if there's an active prescription in memory
    today = NOW.strftime('%Y-%m-%d')
    # Active until 2026-02-25 (3-day prescription from 2026-02-23)
    prescription_end = '2026-02-25'
    if today > prescription_end:
        return None

    now_hour = NOW.hour
    slots = [
        {'time': '09:00', 'drugs': ['甘草藥水 10CC', 'REGROW SR 1粒', 'ALLEGRA 1粒']},
        {'time': '13:00', 'drugs': ['甘草藥水 10CC']},
        {'time': '17:00', 'drugs': ['甘草藥水 10CC']},
        {'time': '21:00', 'drugs': ['甘草藥水 10CC', 'REGROW SR 1粒', 'ALLEGRA 1粒']},
    ]
    upcoming = [s for s in slots if int(s['time'][:2]) > now_hour]
    return {'upcoming_today': upcoming, 'prescription_end': prescription_end}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tomorrow', action='store_true', help='Include tomorrow calendar')
    parser.add_argument('--no-memory', action='store_true', help='Skip memory context')
    args = parser.parse_args()

    days = 2 if args.tomorrow else 1
    output = {
        'time':       get_time_info(),
        'calendar':   get_calendar(days_range=days),
        'todoist':    get_todoist(),
        'medication': get_medication_schedule(),
    }
    if not args.no_memory:
        output['memory'] = get_memory_context()

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
