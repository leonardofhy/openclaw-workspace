#!/usr/bin/env python3
"""Deterministic bulk-correction engine for daily-scheduler v2.

Supports in one pass:
- INSERT actual blocks from time statements
- ADJUST existing block time by uid
- SPLIT an existing block by uid + split time
- MERGE two existing blocks by uids

Safety:
- Unparseable / unmatched statements go to `## Inbox`
- Archive backup + atomic write

Usage examples:
  python3 bulk_correct_v2.py --date 2026-03-01 --text "13:00-14:30 Results; 15:00-15:30 review"
  python3 bulk_correct_v2.py --date 2026-03-01 --text "adjust A-123abc to 14:00-15:10"
  python3 bulk_correct_v2.py --date 2026-03-01 --text "split A-123abc at 15:30"
  python3 bulk_correct_v2.py --date 2026-03-01 --text "merge A-111,A-222 as Experiment"
"""
from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'lib'))
from common import today_str as _today_str, MEMORY, now as _now

SCHEDULES_DIR = MEMORY / 'schedules'


@dataclass
class ActualBlock:
    uid: str
    start: str
    end: str
    plus_1d: bool
    title: str
    ps: str
    pe: str
    status: str


@dataclass
class Op:
    kind: str  # insert|adjust|split|merge
    raw: str
    data: dict


def _mint_uid(date_str: str, start: str, end: str, title: str, idx: int) -> str:
    raw = f'{date_str}|{start}|{end}|{title}|{idx}'
    return 'A-' + hashlib.sha1(raw.encode('utf-8')).hexdigest()[:10]


def _archive_and_atomic_write(path: Path, content: str) -> Path | None:
    archive = None
    if path.exists():
        archive_dir = SCHEDULES_DIR / '.archive' / path.stem
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive = archive_dir / f"{_now().strftime('%Y%m%dT%H%M%S')}.md"
        shutil.copy2(path, archive)

    tmp = path.with_suffix('.md.tmp')
    tmp.write_text(content)
    tmp.replace(path)
    return archive


def _ensure_v2_sections(text: str) -> str:
    if '## ACTUAL' in text:
        if '### Timeline' not in text:
            text = text.rstrip() + '\n\n### Timeline\n\n### Skipped / Deferred (actual)\n'
        if '## Inbox' not in text:
            text = text.rstrip() + '\n\n## Inbox\n'
        return text

    scaffold = (
        '\n\n## ACTUAL\n'
        '### Timeline\n'
        '\n'
        '### Skipped / Deferred (actual)\n'
        '\n'
        '## Inbox\n'
    )
    return text.rstrip() + scaffold


def _extract_timeline_body(text: str) -> str:
    m_actual = re.search(r'^##\s+ACTUAL\s*\n(.*?)(?=^##\s+|\Z)', text, flags=re.M | re.S)
    if not m_actual:
        return ''
    m_timeline = re.search(r'^###\s+Timeline\s*\n(.*?)(?=^###\s+|\Z)', m_actual.group(1), flags=re.M | re.S)
    return m_timeline.group(1) if m_timeline else ''


def _parse_actual_blocks(text: str, date_str: str) -> list[ActualBlock]:
    body = _extract_timeline_body(text)
    if not body:
        return []

    pat = re.compile(
        r'^\s*-\s*\[A\]\s*'
        r'(~?)(\d{2}:\d{2})\s*[–-]\s*(~?)(\d{2}:\d{2})(\(\+1d\))?\s+'
        r'(.+?)\s*'
        r'(?:\{([^}]*)\})?\s*$',
        flags=re.M,
    )

    out: list[ActualBlock] = []
    for idx, m in enumerate(pat.finditer(body), start=1):
        s_mark, start, e_mark, end, plus_raw, title, meta_body = m.groups()
        meta = {}
        if meta_body:
            for part in re.split(r'\s*,\s*', meta_body.strip()):
                if ':' in part:
                    k, v = part.split(':', 1)
                    meta[k.strip()] = v.strip().strip('"\'')

        uid = meta.get('uid') or _mint_uid(date_str, start, end, title.strip(), idx)
        out.append(
            ActualBlock(
                uid=uid,
                start=start,
                end=end,
                plus_1d=bool(plus_raw),
                title=title.strip(),
                ps=meta.get('ps', 'approx' if s_mark else 'exact'),
                pe=meta.get('pe', 'approx' if e_mark else 'exact'),
                status=meta.get('status', 'done'),
            )
        )
    return out


def _render_actual_line(b: ActualBlock) -> str:
    s = f'~{b.start}' if b.ps == 'approx' else b.start
    end_label = f'{b.end}(+1d)' if b.plus_1d else b.end
    e = f'~{end_label}' if b.pe == 'approx' else end_label
    return (
        f'- [A] {s}-{e} {b.title} '
        f'{{uid:{b.uid}, ps:{b.ps}, pe:{b.pe}, status:{b.status}}}'
    )


def _replace_timeline(text: str, new_lines: list[str]) -> str:
    body = '\n'.join(new_lines)
    return re.sub(
        r'(^###\s+Timeline\s*\n)(.*?)(?=^###\s+|^##\s+|\Z)',
        lambda m: m.group(1) + body + ('\n' if body else '\n'),
        text,
        count=1,
        flags=re.M | re.S,
    )


def _append_inbox(text: str, unresolved: list[str]) -> str:
    if not unresolved:
        return text
    lines = '\n'.join(f'- [needs_resolution] {u}' for u in unresolved)
    if re.search(r'^##\s+Inbox\s*$', text, flags=re.M):
        return re.sub(r'(^##\s+Inbox\s*$)', '\\1\n' + lines, text, count=1, flags=re.M)
    return text.rstrip() + '\n\n## Inbox\n' + lines + '\n'


def _split_statements(text: str) -> list[str]:
    parts = re.split(r'[\n；;。]+', text)
    return [p.strip(' -\t') for p in parts if p.strip()]


def _norm_hhmm(hhmm: str) -> str:
    h, m = hhmm.split(':')
    return f'{int(h):02d}:{int(m):02d}'


def _to_minutes(start: str, end: str, plus_1d: bool) -> tuple[int, int]:
    sh, sm = map(int, start.split(':'))
    eh, em = map(int, end.split(':'))
    s = sh * 60 + sm
    e = eh * 60 + em
    if plus_1d or e <= s:
        e += 24 * 60
    return s, e


def _minutes_to_hhmm(m: int) -> tuple[str, bool]:
    plus = m >= 24 * 60
    m = m % (24 * 60)
    return f'{m // 60:02d}:{m % 60:02d}', plus


def _parse_statement(stmt: str) -> Op | None:
    # merge A-1,A-2 as New Title
    mm = re.match(r'^merge\s+([A-Za-z0-9._-]+)\s*[,\s]+([A-Za-z0-9._-]+)(?:\s+as\s+(.+))?$', stmt, flags=re.I)
    if mm:
        u1, u2, title = mm.groups()
        return Op('merge', stmt, {'uid1': u1, 'uid2': u2, 'title': (title or '').strip()})

    # split A-1 at 15:30
    ms = re.match(r'^split\s+([A-Za-z0-9._-]+)\s+(?:at|@)\s*(\d{1,2}:\d{2})$', stmt, flags=re.I)
    if ms:
        uid, t = ms.groups()
        return Op('split', stmt, {'uid': uid, 'split_at': _norm_hhmm(t)})

    # adjust A-1 to 14:00-15:10 New Title(optional)
    ma = re.match(
        r'^(?:adjust\s+)?([A-Za-z0-9._-]+)\s+to\s+(~?\d{1,2}:\d{2})\s*(?:-|–|to)\s*(~?\d{1,2}:\d{2})(\(\+1d\))?(?:\s+(.+))?$',
        stmt,
        flags=re.I,
    )
    if ma:
        uid, s, e, plus, title = ma.groups()
        return Op('adjust', stmt, {
            'uid': uid,
            'start': _norm_hhmm(s.replace('~', '')),
            'end': _norm_hhmm(e.replace('~', '')),
            'ps': 'approx' if s.startswith('~') else 'exact',
            'pe': 'approx' if e.startswith('~') else 'exact',
            'plus_1d': bool(plus),
            'title': (title or '').strip(),
        })

    # insert: 13:00-14:00 Title
    mi = re.search(
        r'(?P<sapprox>~)?(?P<start>\d{1,2}:\d{2})\s*(?:-|–|到|to)\s*'
        r'(?P<eapprox>~)?(?P<end>\d{1,2}:\d{2})(?P<plus>\(\+1d\))?\s*(?P<title>.*)$',
        stmt,
        flags=re.I,
    )
    if mi:
        title = (mi.group('title') or '').strip(' ：:，,') or 'Untitled'
        return Op('insert', stmt, {
            'start': _norm_hhmm(mi.group('start')),
            'end': _norm_hhmm(mi.group('end')),
            'plus_1d': bool(mi.group('plus')),
            'title': title,
            'ps': 'approx' if mi.group('sapprox') else 'exact',
            'pe': 'approx' if mi.group('eapprox') else 'exact',
        })

    return None


def apply_bulk_correction(date_str: str, raw_text: str, dry_run: bool = False) -> dict:
    path = SCHEDULES_DIR / f'{date_str}.md'
    if not path.exists():
        raise FileNotFoundError(f'schedule file not found: {path}')

    text = _ensure_v2_sections(path.read_text())
    actual = _parse_actual_blocks(text, date_str)
    uid_map = {b.uid: b for b in actual}

    statements = _split_statements(raw_text)
    unresolved: list[str] = []
    counts = {'insert': 0, 'adjust': 0, 'split': 0, 'merge': 0}

    for i, stmt in enumerate(statements, start=1):
        op = _parse_statement(stmt)
        if op is None:
            unresolved.append(stmt)
            continue

        if op.kind == 'insert':
            d = op.data
            uid = _mint_uid(date_str, d['start'], d['end'], d['title'], i)
            b = ActualBlock(
                uid=uid,
                start=d['start'],
                end=d['end'],
                plus_1d=d['plus_1d'],
                title=d['title'],
                ps=d['ps'],
                pe=d['pe'],
                status='done',
            )
            actual.append(b)
            uid_map[b.uid] = b
            counts['insert'] += 1

        elif op.kind == 'adjust':
            d = op.data
            b = uid_map.get(d['uid'])
            if b is None:
                unresolved.append(stmt)
                continue
            b.start = d['start']
            b.end = d['end']
            b.plus_1d = d['plus_1d']
            b.ps = d['ps']
            b.pe = d['pe']
            if d['title']:
                b.title = d['title']
            counts['adjust'] += 1

        elif op.kind == 'split':
            d = op.data
            b = uid_map.get(d['uid'])
            if b is None:
                unresolved.append(stmt)
                continue
            s_min, e_min = _to_minutes(b.start, b.end, b.plus_1d)
            split_min, _ = _to_minutes(d['split_at'], d['split_at'], False)
            if split_min <= s_min:
                split_min += 24 * 60
            if not (s_min < split_min < e_min):
                unresolved.append(stmt)
                continue

            end1, plus1 = _minutes_to_hhmm(split_min)
            start2, _ = _minutes_to_hhmm(split_min)
            end2, plus2 = _minutes_to_hhmm(e_min)

            b.end = end1
            b.plus_1d = plus1
            uid2 = _mint_uid(date_str, start2, end2, b.title, i)
            b2 = ActualBlock(
                uid=uid2,
                start=start2,
                end=end2,
                plus_1d=plus2,
                title=b.title,
                ps=b.ps,
                pe=b.pe,
                status='done',
            )
            actual.append(b2)
            uid_map[b2.uid] = b2
            counts['split'] += 1

        elif op.kind == 'merge':
            d = op.data
            b1 = uid_map.get(d['uid1'])
            b2 = uid_map.get(d['uid2'])
            if b1 is None or b2 is None:
                unresolved.append(stmt)
                continue
            s1, e1 = _to_minutes(b1.start, b1.end, b1.plus_1d)
            s2, e2 = _to_minutes(b2.start, b2.end, b2.plus_1d)
            if s2 < s1:
                b1, b2 = b2, b1
                s1, e1, s2, e2 = s2, e2, s1, e1

            b1.start, _ = _minutes_to_hhmm(min(s1, s2))
            b1.end, b1.plus_1d = _minutes_to_hhmm(max(e1, e2))
            if d['title']:
                b1.title = d['title']
            b2.status = 'superseded'
            counts['merge'] += 1

    # Sort by normalized start time for stable timeline rendering.
    actual.sort(key=lambda b: _to_minutes(b.start, b.end, b.plus_1d)[0])

    new_lines = [_render_actual_line(b) for b in actual]
    text = _replace_timeline(text, new_lines)
    text = _append_inbox(text, unresolved)

    archive = None
    if not dry_run:
        archive = _archive_and_atomic_write(path, text)

    return {
        'date': date_str,
        'schedule_file': str(path),
        'ops_applied': counts,
        'unresolved': len(unresolved),
        'archive': str(archive) if archive else None,
        'dry_run': dry_run,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=_today_str(), help='YYYY-MM-DD')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--text', help='Bulk correction text')
    g.add_argument('--text-file', help='Path to bulk correction text file')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    raw = args.text if args.text is not None else Path(args.text_file).read_text()
    result = apply_bulk_correction(args.date, raw, dry_run=args.dry_run)
    print(result)


if __name__ == '__main__':
    main()
