#!/usr/bin/env python3
"""Todoist task sync: list active tasks and optionally today's completed tasks."""
import os, json, sys, requests, argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'lib'))
from common import TZ, now as _now, SECRETS

ENV_PATH = SECRETS / 'todoist.env'
API_BASE = 'https://api.todoist.com/api/v1'


def load_token():
    token = os.environ.get('TODOIST_API_TOKEN')
    if token:
        return token
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if line.startswith('TODOIST_API_TOKEN='):
                return line.split('=', 1)[1].strip()
    raise RuntimeError('TODOIST_API_TOKEN not found')


def get(path, token, params=None):
    r = requests.get(f'{API_BASE}{path}',
                     headers={'Authorization': f'Bearer {token}'},
                     params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def get_completed_today(token):
    """Fetch tasks completed today (Asia/Taipei)."""
    now_local = _now()
    start_of_day = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    # Convert to UTC ISO for API
    since_utc = start_of_day.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')

    items = []
    try:
        data = get('/tasks/completed', token, params={
            'since': since_utc,
            'limit': 50
        })
        for item in data.get('items', []):
            items.append({
                'id': item.get('task_id'),
                'content': item.get('content'),
                'completed_at': item.get('completed_at'),
                'project_id': item.get('project_id'),
            })
    except Exception as e:
        print(f"Warning: could not fetch completed tasks: {e}", file=__import__('sys').stderr)
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=10)
    ap.add_argument('--completed-today', action='store_true',
                    help='Include tasks completed today')
    args = ap.parse_args()

    token = load_token()
    tasks = get('/tasks', token).get('results', [])
    projects = {p['id']: p for p in get('/projects', token).get('results', [])}

    def due_key(t):
        d = (t.get('due') or {}).get('date')
        return d or '9999-12-31'

    tasks = [t for t in tasks if not t.get('completed_at')]
    tasks.sort(key=lambda t: (-int(t.get('priority', 1)), due_key(t)))

    out = []
    for t in tasks[:args.limit]:
        out.append({
            'id': t.get('id'),
            'content': t.get('content'),
            'priority': t.get('priority'),
            'due': (t.get('due') or {}).get('date'),
            'project': projects.get(t.get('project_id'), {}).get('name')
        })

    result = {'count': len(tasks), 'top': out}

    if args.completed_today:
        completed = get_completed_today(token)
        # Enrich with project names
        for c in completed:
            c['project'] = projects.get(c.get('project_id'), {}).get('name')
            c.pop('project_id', None)
        result['completed_today'] = completed
        result['completed_today_count'] = len(completed)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
