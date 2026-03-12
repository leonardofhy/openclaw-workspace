#!/usr/bin/env python3
"""schedule_data.py — fetch all data needed for daily scheduling.

Outputs a JSON snapshot of:
  - Current time + remaining hours today
  - Google Calendar events (today + tomorrow)
  - Todoist tasks (due today, overdue, high priority)
  - Today's memory context
  - Known upcoming deadlines

Usage:
  python3 schedule_data.py
  python3 schedule_data.py --tomorrow   # include tomorrow's calendar

Configuration:
  Set these environment variables or update the constants below:
    OPENCLAW_CAL_ID    — Google Calendar ID (e.g. your-email@gmail.com)
    TODOIST_API_TOKEN  — from secrets/todoist.env
"""
import json
import sys
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────
# Update these to match your setup, or set environment variables.
import os

TZ_OFFSET_HOURS = 8  # Change to your UTC offset (e.g. -5 for EST, 8 for CST/SGT)
TZ = timezone(timedelta(hours=TZ_OFFSET_HOURS))

def find_workspace():
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        if os.path.isdir(os.path.join(d, '.git')):
            return Path(d)
        d = os.path.dirname(d)
    return Path.home() / '.openclaw' / 'workspace'

WORKSPACE = find_workspace()
MEMORY = WORKSPACE / 'memory'
SECRETS = WORKSPACE / 'secrets'

CAL_ID = os.environ.get('OPENCLAW_CAL_ID', '{{GCAL_ID}}')
TODOIST_ENV = SECRETS / 'todoist.env'

def now():
    return datetime.now(TZ)

def today_str():
    return now().strftime('%Y-%m-%d')

# ── Data fetchers ──────────────────────────────────────────────────────────

def get_calendar(days_range=1):
    """Fetch Google Calendar events. Requires google-service-account.json."""
    try:
        # Add gcal_today.py path — adjust if using a different script
        gcal_script = WORKSPACE / 'skills' / 'personal-tools' / 'scripts' / 'gcal_today.py'
        if not gcal_script.exists():
            return [{'error': 'gcal_today.py not found — add your calendar fetcher'}]

        sys.path.insert(0, str(gcal_script.parent))
        from gcal_today import get_events
        events = get_events(days_ahead=0, days_range=days_range)
        return sorted([{
            'title':    e.get('summary', '?'),
            'start':    e.get('start', ''),
            'end':      e.get('end', ''),
            'location': e.get('location', ''),
            'all_day':  e.get('all_day', False),
        } for e in events], key=lambda x: x['start'])
    except Exception as ex:
        return [{'error': str(ex)}]


def get_todoist():
    """Fetch Todoist tasks. Requires TODOIST_API_TOKEN in secrets/todoist.env."""
    try:
        token = None
        if TODOIST_ENV.exists():
            for line in TODOIST_ENV.read_text().splitlines():
                if 'TODOIST_API_TOKEN' in line:
                    token = line.split('=', 1)[-1].strip().strip('"').strip("'")

        if not token:
            return {'error': 'no token — add TODOIST_API_TOKEN to secrets/todoist.env'}

        import urllib.request
        req = urllib.request.Request(
            'https://api.todoist.com/api/v1/tasks?filter=today|overdue',
            headers={'Authorization': f'Bearer {token}'}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            tasks = json.loads(resp.read())

        today = today_str()
        result = {'due_today': [], 'overdue': [], 'high_priority': []}
        for t in tasks:
            due = (t.get('due') or {}).get('date', '')
            item = {'id': t.get('id'), 'content': t.get('content', ''), 'priority': t.get('priority', 1), 'due': due}
            if due == today:
                result['due_today'].append(item)
            elif due and due < today:
                result['overdue'].append(item)
            if t.get('priority', 1) >= 3:
                result['high_priority'].append(item)
        return result
    except Exception as ex:
        return {'error': str(ex)}


def get_memory_context():
    """Load today's memory file for context."""
    try:
        today_file = MEMORY / f"{today_str()}.md"
        if today_file.exists():
            content = today_file.read_text(encoding='utf-8')
            # Return first 500 chars as context
            return content[:500] + ('...' if len(content) > 500 else '')
        return None
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tomorrow', action='store_true', help='Include tomorrow calendar')
    args = parser.parse_args()

    current = now()
    end_of_day = current.replace(hour=23, minute=59, second=59)
    hours_remaining = max(0, (end_of_day - current).seconds / 3600)

    snapshot = {
        'generated_at': current.isoformat(),
        'date': today_str(),
        'time': current.strftime('%H:%M'),
        'hours_remaining_today': round(hours_remaining, 1),
        'calendar': get_calendar(days_range=2 if args.tomorrow else 1),
        'todoist': get_todoist(),
        'memory_context': get_memory_context(),
    }

    print(json.dumps(snapshot, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
