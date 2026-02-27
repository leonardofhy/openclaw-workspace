#!/usr/bin/env python3
"""Sync latest daily schedule blocks to Google Calendar.

Source of truth:
  memory/schedules/YYYY-MM-DD.md (latest vN section only)

Behavior:
- Parse latest schedule version block (## vN ...)
- Convert actionable time blocks to calendar events
- Upsert events with stable slot keys
- Remove stale synced events not in latest schedule

Usage:
  python3 sync_schedule_to_gcal.py --date 2026-02-27
  python3 sync_schedule_to_gcal.py --date 2026-02-27 --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'lib'))
from common import TZ, today_str as _today_str, WORKSPACE, SECRETS

CAL_ID = 'leonardofoohy@gmail.com'
CREDS_PATH = SECRETS / 'google-service-account.json'
SCHEDULES_DIR = WORKSPACE / 'memory' / 'schedules'
SYNC_MARKER = '[openclaw-schedule-sync]'

# Skip routine blocks to avoid calendar noise
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


def _parse_latest_version_section(md_text: str) -> str:
    # capture each vN section body until next ##
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


def _to_dt(date_str: str, hhmm: str) -> datetime:
    h, m = map(int, hhmm.split(':'))
    d = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=TZ)
    return d.replace(hour=h, minute=m, second=0, microsecond=0)


def _event_summary(block: Block) -> str:
    # keep concise summary in calendar
    return f"{block.emoji} {block.title}"


def _event_description(date_str: str, block: Block, source_file: Path) -> str:
    return (
        f"{SYNC_MARKER}\n"
        f"date={date_str}\n"
        f"slot={block.slot}\n"
        f"source={source_file}\n"
    )


def _extract_slot(event: dict) -> str | None:
    desc = event.get('description') or ''
    m = re.search(r'^slot=(\d{2}:\d{2}-\d{2}:\d{2})$', desc, flags=re.M)
    return m.group(1) if m else None


def _is_synced_event(event: dict) -> bool:
    desc = event.get('description') or ''
    return SYNC_MARKER in desc


def sync(date_str: str, dry_run: bool = False) -> dict:
    schedule_file = SCHEDULES_DIR / f'{date_str}.md'
    if not schedule_file.exists():
        raise FileNotFoundError(f'schedule file not found: {schedule_file}')

    text = schedule_file.read_text()
    latest_section = _parse_latest_version_section(text)
    if not latest_section:
        raise RuntimeError('no vN schedule section found')

    blocks = _parse_blocks(latest_section)

    creds = Credentials.from_service_account_file(
        str(CREDS_PATH), scopes=['https://www.googleapis.com/auth/calendar']
    )
    service = build('calendar', 'v3', credentials=creds)

    day_start = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=TZ)
    day_end = day_start + timedelta(days=1)

    existing = service.events().list(
        calendarId=CAL_ID,
        timeMin=day_start.isoformat(),
        timeMax=day_end.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute().get('items', [])

    synced_existing = { _extract_slot(e): e for e in existing if _is_synced_event(e) and _extract_slot(e) }
    target_slots = { b.slot: b for b in blocks }

    actions = {'create': [], 'update': [], 'delete': [], 'kept': []}

    # upsert targets
    for slot, block in target_slots.items():
        start_dt = _to_dt(date_str, block.start)
        end_dt = _to_dt(date_str, block.end)
        body = {
            'summary': _event_summary(block),
            'description': _event_description(date_str, block, schedule_file),
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Asia/Taipei'},
            'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'Asia/Taipei'},
        }

        existing_event = synced_existing.get(slot)
        if existing_event:
            changed = (
                existing_event.get('summary') != body['summary'] or
                (existing_event.get('description') or '') != body['description'] or
                existing_event.get('start', {}).get('dateTime') != body['start']['dateTime'] or
                existing_event.get('end', {}).get('dateTime') != body['end']['dateTime']
            )
            if changed:
                actions['update'].append(slot)
                if not dry_run:
                    service.events().update(
                        calendarId=CAL_ID,
                        eventId=existing_event['id'],
                        body=body
                    ).execute()
            else:
                actions['kept'].append(slot)
        else:
            actions['create'].append(slot)
            if not dry_run:
                service.events().insert(calendarId=CAL_ID, body=body).execute()

    # delete stale synced events
    for slot, event in synced_existing.items():
        if slot not in target_slots:
            actions['delete'].append(slot)
            if not dry_run:
                service.events().delete(calendarId=CAL_ID, eventId=event['id']).execute()

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
