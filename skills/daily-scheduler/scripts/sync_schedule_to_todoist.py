#!/usr/bin/env python3
"""Sync latest daily schedule blocks to Todoist.

Source of truth:
  memory/schedules/YYYY-MM-DD.md (latest vN section only)

Behavior:
- Parse latest schedule version block (## vN ...)
- Upsert actionable blocks as Todoist tasks (due at block start)
- Remove stale synced tasks no longer present in latest schedule

Usage:
  python3 sync_schedule_to_todoist.py --date 2026-02-27
  python3 sync_schedule_to_todoist.py --date 2026-02-27 --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests

# workspace shared helpers
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'lib'))
from common import TZ, today_str as _today_str, WORKSPACE, SECRETS

API_BASE = 'https://api.todoist.com/api/v1'
ENV_PATH = SECRETS / 'todoist.env'
SCHEDULES_DIR = WORKSPACE / 'memory' / 'schedules'
SYNC_MARKER = '[openclaw-schedule-sync]'

# Skip routine/noise blocks
SKIP_EMOJIS = {'🍜', '🚿', '🌙', '💪', '📅'}
SKIP_KEYWORDS = {'午餐', '晚餐', '洗漱', '洗澡', '就寢', '睡眠', '離線', 'lab dinner'}


@dataclass
class Block:
    start: str
    end: str
    emoji: str
    title: str

    @property
    def slot(self) -> str:
        return f"{self.start}-{self.end}"


def load_token() -> str:
    token = os.environ.get('TODOIST_API_TOKEN')
    if token:
        return token
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if line.startswith('TODOIST_API_TOKEN='):
                return line.split('=', 1)[1].strip()
    raise RuntimeError('TODOIST_API_TOKEN not found')


def _req(method: str, path: str, token: str, payload: dict | None = None, params: dict | None = None):
    r = requests.request(
        method,
        f'{API_BASE}{path}',
        headers={'Authorization': f'Bearer {token}'},
        json=payload,
        params=params,
        timeout=20,
    )
    if r.status_code >= 300:
        raise RuntimeError(f'{method} {path} -> {r.status_code}: {r.text[:300]}')
    if r.status_code == 204:
        return None
    return r.json()


def _parse_latest_version_section(md_text: str) -> str:
    matches = list(re.finditer(r'^## v\d+[^\n]*\n(.*?)(?=^## |\Z)', md_text, flags=re.M | re.S))
    if not matches:
        return ''
    return matches[-1].group(1)


def _parse_blocks(section_text: str) -> list[Block]:
    blocks: list[Block] = []
    pattern = re.compile(r'^\s*•\s*(\d{2}:\d{2})[–-](\d{2}:\d{2})\s+(\S+)\s+(.*)$', re.M)
    for m in pattern.finditer(section_text):
        start, end, emoji, title = m.groups()
        title = re.sub(r'\*\*(.*?)\*\*', r'\1', title).strip()
        lower_title = title.lower()
        if emoji in SKIP_EMOJIS:
            continue
        if any(k in title for k in SKIP_KEYWORDS) or any(k in lower_title for k in SKIP_KEYWORDS):
            continue
        blocks.append(Block(start=start, end=end, emoji=emoji, title=title))
    return blocks


def _description(date_str: str, slot: str, source_file: Path) -> str:
    return (
        f"{SYNC_MARKER}\n"
        f"date={date_str}\n"
        f"slot={slot}\n"
        f"source={source_file}\n"
    )


def _extract_slot(task: dict) -> str | None:
    desc = task.get('description') or ''
    m = re.search(r'^slot=(\d{2}:\d{2}-\d{2}:\d{2})$', desc, flags=re.M)
    return m.group(1) if m else None


def _extract_date(task: dict) -> str | None:
    desc = task.get('description') or ''
    m = re.search(r'^date=(\d{4}-\d{2}-\d{2})$', desc, flags=re.M)
    return m.group(1) if m else None


def _is_synced_task(task: dict) -> bool:
    return SYNC_MARKER in (task.get('description') or '')


def _priority_for(block: Block) -> int:
    if block.emoji in {'✉️', '📤'}:
        return 4
    if block.emoji in {'📋'}:
        return 3
    if block.emoji in {'🔬'}:
        return 4
    return 2


def _list_all_active_tasks(token: str) -> list[dict]:
    """Fetch all active tasks via Todoist cursor pagination."""
    out: list[dict] = []
    cursor = None
    while True:
        params = {'limit': 200}
        if cursor:
            params['cursor'] = cursor
        page = _req('GET', '/tasks', token, params=params) or {}
        out.extend(page.get('results', []))
        cursor = page.get('next_cursor')
        if not cursor:
            break
    return out


def _due_datetime(date_str: str, hhmm: str) -> str:
    h, m = map(int, hhmm.split(':'))
    dt = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=TZ, hour=h, minute=m)
    return dt.isoformat(timespec='seconds')


def sync(date_str: str, dry_run: bool = False) -> dict:
    schedule_file = SCHEDULES_DIR / f'{date_str}.md'
    if not schedule_file.exists():
        raise FileNotFoundError(f'schedule file not found: {schedule_file}')

    text = schedule_file.read_text()
    latest_section = _parse_latest_version_section(text)
    if not latest_section:
        raise RuntimeError('no vN schedule section found')

    blocks = _parse_blocks(latest_section)
    target_slots = {b.slot: b for b in blocks}

    token = load_token()
    tasks = _list_all_active_tasks(token)

    synced_existing_multi: dict[str, list[dict]] = {}
    for t in tasks:
        if not _is_synced_task(t):
            continue
        slot = _extract_slot(t)
        if not slot:
            continue
        if _extract_date(t) != date_str:
            continue
        synced_existing_multi.setdefault(slot, []).append(t)

    # choose one canonical task per slot; extra duplicates will be deleted
    synced_existing: dict[str, dict] = {}
    duplicate_ids: list[str] = []
    for slot, arr in synced_existing_multi.items():
        arr_sorted = sorted(arr, key=lambda x: x.get('updated_at') or x.get('added_at') or '')
        synced_existing[slot] = arr_sorted[-1]
        for extra in arr_sorted[:-1]:
            if extra.get('id'):
                duplicate_ids.append(extra['id'])

    actions = {'create': [], 'update': [], 'delete': [], 'kept': [], 'dedupe_delete': []}

    # upsert
    for slot, block in target_slots.items():
        content = f"{block.emoji} {block.start} {block.title}"
        due_dt = _due_datetime(date_str, block.start)
        body = {
            'content': content,
            'description': _description(date_str, slot, schedule_file),
            'due_datetime': due_dt,
            'priority': _priority_for(block),
        }
        existing = synced_existing.get(slot)
        if existing:
            due_obj = existing.get('due') or {}
            existing_due = due_obj.get('datetime') or due_obj.get('date')
            changed = (
                existing.get('content') != body['content'] or
                (existing.get('description') or '') != body['description'] or
                existing.get('priority') != body['priority'] or
                existing_due != body['due_datetime']
            )
            if changed:
                actions['update'].append(slot)
                if not dry_run:
                    _req('POST', f"/tasks/{existing['id']}", token, body)
            else:
                actions['kept'].append(slot)
        else:
            actions['create'].append(slot)
            if not dry_run:
                _req('POST', '/tasks', token, body)

    # delete duplicate tasks for same slot
    for tid in duplicate_ids:
        actions['dedupe_delete'].append(tid)
        if not dry_run:
            _req('DELETE', f"/tasks/{tid}", token)

    # delete stale
    for slot, task in synced_existing.items():
        if slot not in target_slots:
            actions['delete'].append(slot)
            if not dry_run:
                _req('DELETE', f"/tasks/{task['id']}", token)

    return {
        'date': date_str,
        'schedule_file': str(schedule_file),
        'parsed_blocks': [vars(b) for b in blocks],
        'actions': actions,
        'dry_run': dry_run,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=_today_str(), help='YYYY-MM-DD')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    result = sync(args.date, dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
