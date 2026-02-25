#!/usr/bin/env python3
"""weekly_data.py — fetch 7 days of scheduling data for weekly plan generation.

Outputs a JSON object with per-day data blocks including:
  - Calendar events
  - Todoist tasks (due on that day, overdue, high priority)
  - Day metadata (weekday, phase suggestions)

Usage:
  python3 weekly_data.py                    # next 7 days starting today
  python3 weekly_data.py --start 2026-03-01 # from specific date
  python3 weekly_data.py --days 14          # 14-day lookahead
"""
import json
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'lib'))
from common import TZ, now as _now, WORKSPACE, SECRETS, SCRIPTS

sys.path.insert(0, str(SCRIPTS))

NOW = _now()

# --- Calendar ---
def get_calendar_range(start_date, days):
    """Fetch calendar events for a date range, grouped by day."""
    try:
        from gcal_today import get_events
        events = get_events(
            days_ahead=(start_date - NOW.date()).days,
            days_range=days
        )
        # Group by date
        by_date = {}
        for e in events:
            raw_start = e.get('start', '')
            if 'T' in raw_start:
                date_key = raw_start[:10]
            elif raw_start:
                date_key = raw_start[:10]
            else:
                continue
            by_date.setdefault(date_key, []).append({
                'title':    e.get('summary', '?'),
                'start':    raw_start,
                'end':      e.get('end', ''),
                'location': e.get('location', ''),
                'all_day':  e.get('all_day', False),
            })
        # Sort events within each day
        for d in by_date:
            by_date[d].sort(key=lambda x: x['start'])
        return by_date
    except Exception as ex:
        return {'error': str(ex)}


# --- Todoist ---
def get_todoist_range(start_date, days):
    """Fetch all open tasks, group by due date within range."""
    try:
        env_path = WORKSPACE / 'secrets' / 'todoist.env'
        token = None
        for line in env_path.read_text().splitlines():
            if 'TODOIST_API_TOKEN' in line:
                token = line.split('=', 1)[-1].strip()
        if not token:
            return {'error': 'no token'}

        import urllib.request
        req = urllib.request.Request(
            'https://api.todoist.com/api/v1/tasks?limit=100',
            headers={'Authorization': f'Bearer {token}'}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            tasks = data.get('results', data) if isinstance(data, dict) else data

        end_date = start_date + timedelta(days=days)
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()
        today_str = NOW.strftime('%Y-%m-%d')

        by_date = {}      # date_str -> [task]
        overdue = []       # before start_date
        no_due_hp = []     # no due date but high priority

        for t in tasks:
            due_raw = t.get('due')
            due = (due_raw.get('date', '')[:10] if isinstance(due_raw, dict) else '') if due_raw else ''
            content = t.get('content', '')
            priority = t.get('priority', 1)
            item = {
                'content': content,
                'due': due,
                'priority': priority,
                'id': t.get('id'),
            }

            if due and due < today_str:
                overdue.append(item)
            elif due and start_str <= due < end_str:
                by_date.setdefault(due, []).append(item)
            elif not due and priority >= 3:
                no_due_hp.append(item)

        # Sort each day's tasks by priority desc
        for d in by_date:
            by_date[d].sort(key=lambda x: -x['priority'])
        overdue.sort(key=lambda x: -x['priority'])
        no_due_hp.sort(key=lambda x: -x['priority'])

        return {
            'by_date': by_date,
            'overdue': overdue[:10],
            'no_due_high_priority': no_due_hp[:5],
            'total_tasks': len(tasks),
        }
    except Exception as ex:
        return {'error': str(ex)}


# --- Existing schedules ---
def get_existing_schedules(start_date, days):
    """Check which days already have schedule files."""
    schedules_dir = WORKSPACE / 'memory' / 'schedules'
    existing = {}
    for i in range(days):
        d = start_date + timedelta(days=i)
        d_str = d.isoformat()
        path = schedules_dir / f'{d_str}.md'
        if path.exists():
            existing[d_str] = {
                'exists': True,
                'size': path.stat().st_size,
                'preview': path.read_text()[:200],
            }
    return existing


# --- Day metadata ---
def build_day_meta(start_date, days):
    """Generate metadata for each day in range."""
    WEEKDAYS_ZH = ['一', '二', '三', '四', '五', '六', '日']
    result = {}
    for i in range(days):
        d = start_date + timedelta(days=i)
        d_str = d.isoformat()
        wd = d.weekday()  # 0=Mon
        result[d_str] = {
            'weekday_zh': f'週{WEEKDAYS_ZH[wd]}',
            'weekday_en': d.strftime('%A'),
            'is_weekend': wd >= 5,
            'day_type': 'weekend' if wd >= 5 else 'weekday',
        }
    return result


def main():
    parser = argparse.ArgumentParser(description='Fetch weekly scheduling data')
    parser.add_argument('--start', type=str, default=None,
                        help='Start date (YYYY-MM-DD), default=today')
    parser.add_argument('--days', type=int, default=7,
                        help='Number of days to look ahead (default=7)')
    args = parser.parse_args()

    if args.start:
        start_date = datetime.strptime(args.start, '%Y-%m-%d').date()
    else:
        start_date = NOW.date()

    calendar_data = get_calendar_range(start_date, args.days)
    todoist_data = get_todoist_range(start_date, args.days)
    existing = get_existing_schedules(start_date, args.days)
    day_meta = build_day_meta(start_date, args.days)

    output = {
        'generated_at': NOW.isoformat(),
        'range': {
            'start': start_date.isoformat(),
            'end': (start_date + timedelta(days=args.days)).isoformat(),
            'days': args.days,
        },
        'day_meta': day_meta,
        'calendar': calendar_data if not isinstance(calendar_data, dict) or 'error' not in calendar_data else calendar_data,
        'todoist': todoist_data,
        'existing_schedules': existing,
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
