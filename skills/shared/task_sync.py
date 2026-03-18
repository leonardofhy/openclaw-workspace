#!/usr/bin/env python3
"""task_sync.py — Bidirectional sync between memory/task-board.md and Todoist.

Usage:
    python3 skills/shared/task_sync.py --push       # board → Todoist
    python3 skills/shared/task_sync.py --pull       # Todoist → board
    python3 skills/shared/task_sync.py --sync       # both directions
    python3 skills/shared/task_sync.py --sync --dry-run
    python3 skills/shared/task_sync.py --status     # show sync state (JSON)
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from urllib import request as urllib_request, error as urllib_error

# ── Paths ──────────────────────────────────────────────────────────────────────
WORKSPACE = Path(__file__).resolve().parent.parent.parent
TASK_BOARD = WORKSPACE / 'memory' / 'task-board.md'
SECRETS_ENV = WORKSPACE / 'secrets' / 'todoist.env'

# ── Todoist API ────────────────────────────────────────────────────────────────
API_BASE = 'https://api.todoist.com/api/v1'
LABEL_PREFIX = 'TB_'        # TB_M-02, TB_L-08  (no colons in Todoist labels)
TZ = timezone(timedelta(hours=8))

ACTIVE_STATUSES = {'ACTIVE'}
SKIP_PUSH_STATUSES = {'PARKED', 'DONE', 'WAITING', 'BLOCKED'}
PRIORITY_MAP = {'P0': 4, 'P1': 3, 'P2': 2, 'P3': 1}


# ── Token loading ──────────────────────────────────────────────────────────────

def load_token() -> str:
    import os
    token = os.environ.get('TODOIST_API_TOKEN')
    if token:
        return token
    if SECRETS_ENV.exists():
        for line in SECRETS_ENV.read_text().splitlines():
            if line.startswith('TODOIST_API_TOKEN='):
                return line.split('=', 1)[1].strip()
    raise RuntimeError('TODOIST_API_TOKEN not found in env or secrets/todoist.env')


# ── HTTP helpers ───────────────────────────────────────────────────────────────

def _request(method: str, path: str, token: str, payload: Optional[dict] = None,
             params: Optional[dict] = None) -> dict:
    url = f'{API_BASE}{path}'
    if params:
        from urllib.parse import urlencode
        url = f'{url}?{urlencode(params)}'
    data = json.dumps(payload).encode() if payload else None
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    req = urllib_request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib_request.urlopen(req, timeout=20) as resp:
            body = resp.read()
            return json.loads(body) if body else {}
    except urllib_error.HTTPError as e:
        body = e.read().decode(errors='replace')
        raise RuntimeError(f'HTTP {e.code} {method} {path}: {body}') from e


def api_get(path: str, token: str, params: Optional[dict] = None) -> dict:
    return _request('GET', path, token, params=params)


def api_post(path: str, token: str, payload: dict) -> dict:
    return _request('POST', path, token, payload=payload)


# ── Todoist helpers ────────────────────────────────────────────────────────────

def get_all_labels(token: str) -> dict[str, dict]:
    """Return {label_name: label_obj}."""
    data = api_get('/labels', token)
    results = data.get('results', data) if isinstance(data, dict) else data
    return {lbl['name']: lbl for lbl in results}


def ensure_label(name: str, token: str, labels_cache: dict, dry_run: bool) -> Optional[str]:
    """Return label ID for `name`, creating it if needed."""
    if name in labels_cache:
        return labels_cache[name]['id']
    if dry_run:
        print(f'  [dry-run] would create label: {name}', file=sys.stderr)
        return None
    lbl = api_post('/labels', token, {'name': name, 'color': 'blue'})
    labels_cache[name] = lbl
    print(f'  created label: {name}', file=sys.stderr)
    return lbl['id']


def get_tasks_by_label(label_name: str, token: str) -> list[dict]:
    """Return active Todoist tasks that have the given label."""
    data = api_get('/tasks', token, params={'label': label_name})
    results = data.get('results', data) if isinstance(data, dict) else data
    return results


def close_task(task_id: str, token: str, dry_run: bool) -> None:
    if dry_run:
        print(f'  [dry-run] would close task {task_id}', file=sys.stderr)
        return
    api_post(f'/tasks/{task_id}/close', token, {})


def create_task(content: str, label_name: str, label_id: Optional[str],
                priority: int, token: str, dry_run: bool) -> Optional[dict]:
    if dry_run:
        print(f'  [dry-run] would create task: "{content}" label={label_name} pri={priority}',
              file=sys.stderr)
        return None
    labels = [label_name] if label_id is None else [label_name]
    payload: dict = {'content': content, 'priority': priority, 'labels': labels}
    task = api_post('/tasks', token, payload)
    return task


def get_completed_tasks(token: str) -> list[dict]:
    """Fetch completed tasks (up to 200, client-side filtered for TB_ labels)."""
    try:
        data = api_get('/tasks/completed', token, params={'limit': 200})
        items = data.get('items', data.get('results', []))
        return items
    except RuntimeError as e:
        print(f'Warning: could not fetch completed tasks: {e}', file=sys.stderr)
        return []


# ── Task-board parser ──────────────────────────────────────────────────────────

def parse_task_board(path: Path) -> tuple[list[dict], str]:
    """Parse task-board.md into list of task dicts. Returns (tasks, raw_text).

    Each task dict:
        id, title, status, owner, priority, created, last_touched,
        description, progress, next_action, raw_lines (list of str, including header)
        section_start (line index of ### header), section_end (exclusive)
    """
    text = path.read_text()

    # Detect merge conflicts
    if '<<<<<<<' in text or '=======' in text or '>>>>>>>' in text:
        raise ValueError('task-board.md contains git merge conflict markers — resolve first')

    lines = text.splitlines(keepends=True)
    tasks = []

    # Identify section headers (## ACTIVE, ## WAITING, etc.)
    section_status = None
    task_start = None
    task_header_re = re.compile(r'^### ([A-Z]-\d+) \| (.+)$')
    section_re = re.compile(r'^## (ACTIVE|WAITING|BLOCKED|PARKED|DONE)\s*$')

    def flush_task(start: int, end: int, status: str) -> None:
        header_line = lines[start].rstrip('\n')
        m = task_header_re.match(header_line)
        if not m:
            return
        task_id, title = m.group(1), m.group(2)
        fields: dict = {
            'id': task_id,
            'title': title,
            'status': status,
            'section_start': start,
            'section_end': end,
        }
        for line in lines[start + 1:end]:
            fm = re.match(r'^- \*\*(.+?)\*\*: (.*)$', line.rstrip('\n'))
            if fm:
                key, val = fm.group(1), fm.group(2).strip()
                # Normalize field names
                key_map = {
                    'owner': 'owner', 'priority': 'priority',
                    'created': 'created', 'last_touched': 'last_touched',
                    '描述': 'description', 'progress': 'progress',
                    'next_action': 'next_action',
                }
                norm = key_map.get(key, key)
                fields[norm] = val
        tasks.append(fields)

    for i, raw in enumerate(lines):
        line = raw.rstrip('\n')
        sm = section_re.match(line)
        if sm:
            if task_start is not None:
                flush_task(task_start, i, section_status or 'UNKNOWN')
                task_start = None
            section_status = sm.group(1)
            continue

        tm = task_header_re.match(line)
        if tm and section_status:
            if task_start is not None:
                flush_task(task_start, i, section_status)
            task_start = i

    # Flush last task
    if task_start is not None and section_status:
        flush_task(task_start, len(lines), section_status)

    return tasks, text


# ── Write-back helpers ─────────────────────────────────────────────────────────

def update_task_board_field(path: Path, task: dict, field: str, new_value: str,
                            dry_run: bool) -> None:
    """Update a single field in task-board.md for the given task in-place."""
    text = path.read_text()
    lines = text.splitlines(keepends=True)

    field_re = re.compile(rf'^(- \*\*{re.escape(field)}\*\*: )(.*)(\n?)$')
    found = False
    for i in range(task['section_start'], task['section_end']):
        m = field_re.match(lines[i])
        if m:
            old_val = m.group(2)
            if old_val == new_value:
                return  # already up to date
            if dry_run:
                print(f'  [dry-run] {task["id"]}: {field}: {old_val!r} → {new_value!r}',
                      file=sys.stderr)
                return
            lines[i] = f'{m.group(1)}{new_value}{m.group(3)}'
            found = True
            break

    if not found:
        # Insert field after section header (first ### line)
        insert_at = task['section_start'] + 1
        new_line = f'- **{field}**: {new_value}\n'
        if dry_run:
            print(f'  [dry-run] {task["id"]}: insert {field}={new_value!r}', file=sys.stderr)
            return
        lines.insert(insert_at, new_line)

    path.write_text(''.join(lines))


def append_progress(path: Path, task: dict, note: str, dry_run: bool) -> None:
    """Append a note to the progress field of a task."""
    current = task.get('progress', '')
    if note in current:
        return  # already recorded
    new_progress = f'{current}; {note}' if current else note
    update_task_board_field(path, task, 'progress', new_progress, dry_run)


# ── Push (board → Todoist) ─────────────────────────────────────────────────────

def do_push(tasks: list[dict], token: str, dry_run: bool) -> list[dict]:
    """Push next_action items from ACTIVE tasks to Todoist. Returns action log."""
    labels_cache = get_all_labels(token)
    log = []

    active_tasks = [t for t in tasks if t['status'] == 'ACTIVE']
    for task in active_tasks:
        next_action = task.get('next_action', '').strip()
        if not next_action:
            print(f'  skip {task["id"]}: no next_action', file=sys.stderr)
            continue

        label_name = f'{LABEL_PREFIX}{task["id"]}'  # e.g. TB_M-02
        priority = PRIORITY_MAP.get(task.get('priority', 'P2'), 2)

        # Check existing Todoist tasks with this label
        try:
            existing = get_tasks_by_label(label_name, token)
        except RuntimeError as e:
            print(f'  error fetching tasks for {label_name}: {e}', file=sys.stderr)
            log.append({'task_id': task['id'], 'action': 'error', 'error': str(e)})
            time.sleep(0.5)
            continue

        time.sleep(0.5)

        if not existing:
            # Create new
            t = create_task(next_action, label_name, None, priority, token, dry_run)
            todoist_id = t['id'] if t else None
            print(f'  push {task["id"]}: created "{next_action[:60]}"', file=sys.stderr)
            log.append({'task_id': task['id'], 'action': 'created',
                        'content': next_action, 'todoist_id': todoist_id})
        else:
            # Check if content matches
            existing_task = existing[0]
            if existing_task['content'] == next_action:
                print(f'  skip {task["id"]}: already synced', file=sys.stderr)
                log.append({'task_id': task['id'], 'action': 'skipped'})
            else:
                # Close old, create new
                print(f'  push {task["id"]}: content changed, replacing', file=sys.stderr)
                try:
                    close_task(existing_task['id'], token, dry_run)
                    time.sleep(0.5)
                except RuntimeError as e:
                    print(f'  warning: could not close old task: {e}', file=sys.stderr)
                t = create_task(next_action, label_name, None, priority, token, dry_run)
                todoist_id = t['id'] if t else None
                log.append({'task_id': task['id'], 'action': 'replaced',
                            'old_content': existing_task['content'],
                            'new_content': next_action, 'todoist_id': todoist_id})

        time.sleep(0.5)

    return log


# ── Pull (Todoist → board) ─────────────────────────────────────────────────────

def do_pull(tasks: list[dict], token: str, dry_run: bool) -> list[dict]:
    """Pull completed Todoist tasks back into task-board.md. Returns action log."""
    completed = get_completed_tasks(token)
    log = []
    today = datetime.now(TZ).strftime('%Y-%m-%d')

    task_index = {t['id']: t for t in tasks}
    tb_label_re = re.compile(rf'^{re.escape(LABEL_PREFIX)}([A-Z]-\d+)$')

    for item in completed:
        labels = item.get('labels', [])
        task_id = None
        for lbl in labels:
            m = tb_label_re.match(lbl)
            if m:
                task_id = m.group(1)
                break

        if not task_id:
            continue

        board_task = task_index.get(task_id)
        if not board_task:
            print(f'  pull: completed Todoist item references unknown task {task_id}',
                  file=sys.stderr)
            continue

        content = item.get('content', '')
        completed_at = item.get('completed_at', '')
        date_str = completed_at[:10] if completed_at else today
        note = f'Todoist: {content} (completed {date_str})'

        print(f'  pull {task_id}: "{content[:60]}" completed {date_str}', file=sys.stderr)

        # Re-read task section_start/section_end since file may have changed
        updated_tasks, _ = parse_task_board(TASK_BOARD)
        updated_index = {t['id']: t for t in updated_tasks}
        current = updated_index.get(task_id)
        if current is None:
            continue

        update_task_board_field(TASK_BOARD, current, 'last_touched', today, dry_run)
        # Re-read again for progress update (last_touched may have shifted lines)
        updated_tasks2, _ = parse_task_board(TASK_BOARD)
        updated_index2 = {t['id']: t for t in updated_tasks2}
        current2 = updated_index2.get(task_id)
        if current2:
            append_progress(TASK_BOARD, current2, note, dry_run)

        log.append({'task_id': task_id, 'action': 'pulled',
                    'content': content, 'date': date_str})

    return log


# ── Status ─────────────────────────────────────────────────────────────────────

def do_status(tasks: list[dict], token: str) -> dict:
    """Return a dict describing the current sync state."""
    labels_cache = get_all_labels(token)
    rows = []
    for task in tasks:
        label_name = f'{LABEL_PREFIX}{task["id"]}'
        synced = False
        todoist_content = None
        if task['status'] == 'ACTIVE' and task.get('next_action'):
            try:
                existing = get_tasks_by_label(label_name, token)
                time.sleep(0.3)
                if existing:
                    synced = existing[0]['content'] == task.get('next_action', '')
                    todoist_content = existing[0]['content']
            except RuntimeError:
                pass

        rows.append({
            'id': task['id'],
            'status': task['status'],
            'priority': task.get('priority'),
            'next_action': task.get('next_action'),
            'label': label_name,
            'label_exists': label_name in labels_cache,
            'todoist_synced': synced,
            'todoist_content': todoist_content,
            'last_touched': task.get('last_touched'),
        })

    return {'tasks': rows, 'generated_at': datetime.now(TZ).isoformat()}


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description='Sync task-board.md ↔ Todoist')
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--push', action='store_true', help='board → Todoist')
    mode.add_argument('--pull', action='store_true', help='Todoist → board')
    mode.add_argument('--sync', action='store_true', help='both directions')
    mode.add_argument('--status', action='store_true', help='show sync state (JSON to stdout)')
    ap.add_argument('--dry-run', action='store_true', help='show what would happen, no writes')
    args = ap.parse_args()

    if not TASK_BOARD.exists():
        print(f'Error: task-board not found at {TASK_BOARD}', file=sys.stderr)
        sys.exit(1)

    try:
        tasks, _ = parse_task_board(TASK_BOARD)
    except ValueError as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)

    if not tasks:
        print('task-board is empty, nothing to sync.', file=sys.stderr)
        sys.exit(0)

    token = load_token()
    log: list[dict] = []

    if args.status:
        state = do_status(tasks, token)
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return

    if args.push or args.sync:
        print('==> Push (board → Todoist)', file=sys.stderr)
        push_log = do_push(tasks, token, args.dry_run)
        log.extend(push_log)

    if args.pull or args.sync:
        print('==> Pull (Todoist → board)', file=sys.stderr)
        pull_log = do_pull(tasks, token, args.dry_run)
        log.extend(pull_log)

    summary = {
        'dry_run': args.dry_run,
        'actions': log,
        'created': sum(1 for x in log if x.get('action') == 'created'),
        'replaced': sum(1 for x in log if x.get('action') == 'replaced'),
        'skipped': sum(1 for x in log if x.get('action') == 'skipped'),
        'pulled': sum(1 for x in log if x.get('action') == 'pulled'),
        'errors': sum(1 for x in log if x.get('action') == 'error'),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
