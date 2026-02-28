#!/usr/bin/env python3
"""Conflict-safe Google Calendar sync for daily-scheduler.

Phase-1 behavior (compatibility-first):
- Prefer syncing ACTUAL(v2) timeline blocks: `## ACTUAL` -> `### Timeline`
- Fallback to legacy latest `## vN` bullets when ACTUAL(v2) is absent
- Create / update only (NO delete)
- Cross-midnight-safe normalization (prevents timeRangeEmpty)
- Managed-event safety: only update events with matching managed marker + uid

Usage:
  python3 sync_schedule_to_gcal.py --date 2026-03-01
  python3 sync_schedule_to_gcal.py --date 2026-03-01 --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
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
META_DIR = SCHEDULES_DIR / '.meta'
MANAGED_TAG = 'daily-scheduler/v2'

# Legacy parser skip rules (kept for backward compatibility)
SKIP_EMOJIS = {'🍜', '🚿', '🌙', '💪', '📅'}
SKIP_KEYWORDS = {'午餐', '晚餐', '洗漱', '洗澡', '就寢', '睡眠', '離線', 'lab dinner'}


@dataclass
class Block:
    uid: str
    start_dt: datetime
    end_dt: datetime
    title: str
    status: str = 'done'
    precision_start: str = 'exact'  # exact|approx|inferred
    precision_end: str = 'exact'

    @property
    def approx(self) -> bool:
        return self.precision_start != 'exact' or self.precision_end != 'exact'


# --------------------------
# Parsing helpers
# --------------------------

def _extract_actual_timeline_section(md_text: str) -> str:
    m_actual = re.search(r'^##\s+ACTUAL\s*\n(.*?)(?=^##\s+|\Z)', md_text, flags=re.M | re.S)
    if not m_actual:
        return ''
    actual_body = m_actual.group(1)
    m_timeline = re.search(r'^###\s+Timeline\s*\n(.*?)(?=^###\s+|\Z)', actual_body, flags=re.M | re.S)
    return m_timeline.group(1) if m_timeline else ''


def _parse_meta_object(meta_text: str) -> dict:
    """Best-effort parse for `{uid:A-..., ps:approx, status:done}` style."""
    out: dict[str, str] = {}
    if not meta_text:
        return out
    body = meta_text.strip().strip('{}').strip()
    if not body:
        return out
    for part in re.split(r'\s*,\s*', body):
        if ':' not in part:
            continue
        k, v = part.split(':', 1)
        out[k.strip()] = v.strip().strip('"\'')
    return out


def _mint_uid(date_str: str, title: str, start_label: str, line_no: int) -> str:
    raw = f'{date_str}|{start_label}|{title}|{line_no}'
    digest = hashlib.sha1(raw.encode('utf-8')).hexdigest()[:10]
    return f'A-{digest}'


def _normalize_range(date_str: str, start_hhmm: str, end_hhmm: str, plus_1d: bool) -> tuple[datetime, datetime]:
    d = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=TZ)

    sh, sm = map(int, start_hhmm.split(':'))
    eh, em = map(int, end_hhmm.split(':'))

    start_dt = d.replace(hour=sh, minute=sm, second=0, microsecond=0)
    end_dt = d.replace(hour=eh, minute=em, second=0, microsecond=0)

    # Explicit +1d wins
    if plus_1d:
        end_dt += timedelta(days=1)
    # Implicit cross-midnight protection
    elif end_dt <= start_dt:
        end_dt += timedelta(days=1)

    # Final guard against empty/negative ranges
    if end_dt <= start_dt:
        end_dt = start_dt + timedelta(minutes=1)

    return start_dt, end_dt


def _parse_actual_blocks(md_text: str, date_str: str) -> list[Block]:
    timeline = _extract_actual_timeline_section(md_text)
    if not timeline:
        return []

    blocks: list[Block] = []
    # Example:
    # - [A] 23:45-01:30(+1d) Debugging {uid:A-1, ps:exact, pe:exact, status:done}
    pat = re.compile(
        r'^\s*-\s*\[A\]\s*'
        r'(~?)(\d{2}:\d{2})\s*[–-]\s*(~?)(\d{2}:\d{2})(\(\+1d\))?\s+'
        r'(.+?)\s*'
        r'(\{.*\})?\s*$',
        flags=re.M,
    )

    for i, m in enumerate(pat.finditer(timeline), start=1):
        s_approx_mark, start_hhmm, e_approx_mark, end_hhmm, plus_1d_raw, title, meta_raw = m.groups()
        meta = _parse_meta_object(meta_raw or '')

        uid = meta.get('uid') or _mint_uid(date_str, title.strip(), start_hhmm, i)
        ps = meta.get('ps', 'approx' if s_approx_mark else 'exact')
        pe = meta.get('pe', 'approx' if e_approx_mark else 'exact')
        status = meta.get('status', 'done')

        if status in {'skipped', 'cancelled', 'superseded'}:
            continue

        start_dt, end_dt = _normalize_range(
            date_str=date_str,
            start_hhmm=start_hhmm,
            end_hhmm=end_hhmm,
            plus_1d=bool(plus_1d_raw),
        )

        blocks.append(
            Block(
                uid=uid,
                start_dt=start_dt,
                end_dt=end_dt,
                title=title.strip(),
                status=status,
                precision_start=ps,
                precision_end=pe,
            )
        )

    return blocks


def _parse_latest_version_section(md_text: str) -> str:
    matches = list(re.finditer(r'^## v\d+[^\n]*\n(.*?)(?=^## |\Z)', md_text, flags=re.M | re.S))
    if not matches:
        return ''
    return matches[-1].group(1)


def _parse_legacy_blocks(md_text: str, date_str: str) -> list[Block]:
    section = _parse_latest_version_section(md_text)
    if not section:
        return []

    pattern = re.compile(r'^\s*•\s*(\d{2}:\d{2})[–-](\d{2}:\d{2})\s+(\S+)\s+(.*)$', re.M)
    blocks: list[Block] = []
    for i, m in enumerate(pattern.finditer(section), start=1):
        start, end, emoji, title = m.groups()
        title = re.sub(r'\*\*(.*?)\*\*', r'\1', title).strip()
        lower_title = title.lower()

        if emoji in SKIP_EMOJIS:
            continue
        if any(k in title for k in SKIP_KEYWORDS) or any(k in lower_title for k in SKIP_KEYWORDS):
            continue

        start_dt, end_dt = _normalize_range(date_str, start, end, plus_1d=False)
        uid = _mint_uid(date_str, f'{emoji} {title}', start, i)
        blocks.append(Block(uid=uid, start_dt=start_dt, end_dt=end_dt, title=f'{emoji} {title}'))

    return blocks


# --------------------------
# Google Calendar helpers
# --------------------------

def _extract_uid(event: dict) -> str | None:
    desc = event.get('description') or ''
    m = re.search(r'^daily-scheduler uid=([A-Za-z0-9._-]+)$', desc, flags=re.M)
    return m.group(1) if m else None


def _is_managed_event(event: dict) -> bool:
    desc = event.get('description') or ''
    return MANAGED_TAG in desc


def _event_summary(block: Block) -> str:
    prefix = '≈ ' if block.approx else ''
    return f'{prefix}{block.title}'


def _event_description(date_str: str, block: Block, source_file: Path) -> str:
    return (
        f'{MANAGED_TAG}\n'
        f'daily-scheduler uid={block.uid}\n'
        f'date={date_str}\n'
        f'source={source_file}\n'
        f'precision_start={block.precision_start}\n'
        f'precision_end={block.precision_end}\n'
    )


def _payload_hash(body: dict) -> str:
    stable = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha1(stable.encode('utf-8')).hexdigest()


def _meta_path(date_str: str) -> Path:
    return META_DIR / f'{date_str}.json'


def _load_meta(date_str: str) -> dict:
    path = _meta_path(date_str)
    if not path.exists():
        return {
            'schema': 'daily-scheduler/meta-v2',
            'date': date_str,
            'gcal': {'events': {}},
        }
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            raise ValueError('meta root must be object')
    except Exception:
        # Corrupt meta should not block sync; start fresh with minimal skeleton.
        data = {'schema': 'daily-scheduler/meta-v2', 'date': date_str, 'gcal': {'events': {}}}

    data.setdefault('schema', 'daily-scheduler/meta-v2')
    data.setdefault('date', date_str)
    data.setdefault('gcal', {})
    data['gcal'].setdefault('events', {})
    return data


def _save_meta(date_str: str, data: dict) -> None:
    path = _meta_path(date_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    tmp.replace(path)


def sync(date_str: str, dry_run: bool = False) -> dict:
    schedule_file = SCHEDULES_DIR / f'{date_str}.md'
    if not schedule_file.exists():
        raise FileNotFoundError(f'schedule file not found: {schedule_file}')

    text = schedule_file.read_text()

    blocks = _parse_actual_blocks(text, date_str)
    source_mode = 'actual_v2'
    if not blocks:
        # Phase-1 fallback for legacy files
        blocks = _parse_legacy_blocks(text, date_str)
        source_mode = 'legacy_vN_fallback'

    creds = Credentials.from_service_account_file(
        str(CREDS_PATH), scopes=['https://www.googleapis.com/auth/calendar']
    )
    service = build('calendar', 'v3', credentials=creds)

    day_start = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=TZ) - timedelta(days=1)
    day_end = day_start + timedelta(days=3)

    existing = service.events().list(
        calendarId=CAL_ID,
        timeMin=day_start.isoformat(),
        timeMax=day_end.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute().get('items', [])

    managed_existing: dict[str, dict] = {}
    for e in existing:
        if not _is_managed_event(e):
            continue
        uid = _extract_uid(e)
        if uid:
            managed_existing[uid] = e

    meta = _load_meta(date_str)
    meta_events: dict = meta.setdefault('gcal', {}).setdefault('events', {})

    actions = {'create': [], 'update': [], 'kept': [], 'skipped': [], 'delete': [], 'warnings': []}

    for block in blocks:
        body = {
            'summary': _event_summary(block),
            'description': _event_description(date_str, block, schedule_file),
            'start': {'dateTime': block.start_dt.isoformat(), 'timeZone': 'Asia/Taipei'},
            'end': {'dateTime': block.end_dt.isoformat(), 'timeZone': 'Asia/Taipei'},
        }
        new_hash = _payload_hash(body)

        meta_row = meta_events.setdefault(block.uid, {
            'gcal_event_id': None,
            'last_synced_hash': None,
            'locked': False,
            'changed_by_user': False,
            'managed': True,
        })

        existing_event = None

        # Prefer meta-linked event id first, with uid safety check.
        meta_event_id = meta_row.get('gcal_event_id')
        if meta_event_id:
            try:
                e = service.events().get(calendarId=CAL_ID, eventId=meta_event_id).execute()
                if _is_managed_event(e) and _extract_uid(e) == block.uid:
                    existing_event = e
                else:
                    actions['warnings'].append({'uid': block.uid, 'reason': 'meta_event_uid_mismatch'})
            except Exception:
                actions['warnings'].append({'uid': block.uid, 'reason': 'meta_event_not_found'})

        # Fallback by uid scan result.
        if existing_event is None:
            existing_event = managed_existing.get(block.uid)

        if meta_row.get('locked') and not meta_row.get('changed_by_user') and existing_event is not None:
            actions['skipped'].append({'uid': block.uid, 'reason': 'locked_no_user_change'})
            continue

        if existing_event:
            if meta_row.get('last_synced_hash') == new_hash:
                actions['kept'].append(block.uid)
            else:
                actions['update'].append(block.uid)
                if not dry_run:
                    updated = service.events().update(
                        calendarId=CAL_ID,
                        eventId=existing_event['id'],
                        body=body,
                    ).execute()
                    meta_row['gcal_event_id'] = updated.get('id')
                    meta_row['last_synced_hash'] = new_hash
                    meta_row['managed'] = True
                    meta_row['changed_by_user'] = False
        else:
            actions['create'].append(block.uid)
            if not dry_run:
                created = service.events().insert(calendarId=CAL_ID, body=body).execute()
                meta_row['gcal_event_id'] = created.get('id')
                meta_row['last_synced_hash'] = new_hash
                meta_row['managed'] = True
                meta_row['changed_by_user'] = False

    # Phase-1 safety: do not delete managed events automatically.
    # We report potential orphans for visibility only.
    desired_uids = {b.uid for b in blocks}
    for uid in managed_existing:
        if uid not in desired_uids:
            actions['skipped'].append({'uid': uid, 'reason': 'orphan_not_deleted_phase1'})

    if not dry_run:
        _save_meta(date_str, meta)

    return {
        'date': date_str,
        'schedule_file': str(schedule_file),
        'source_mode': source_mode,
        'meta_file': str(_meta_path(date_str)),
        'parsed_blocks': [
            {
                'uid': b.uid,
                'start': b.start_dt.isoformat(),
                'end': b.end_dt.isoformat(),
                'title': b.title,
                'status': b.status,
                'ps': b.precision_start,
                'pe': b.precision_end,
            }
            for b in blocks
        ],
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
