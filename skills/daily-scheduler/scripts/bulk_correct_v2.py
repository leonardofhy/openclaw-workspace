#!/usr/bin/env python3
"""Deterministic bulk-correction MVP for daily-scheduler v2.

Phase-1 scope (safe/minimal):
- Parse multiple time statements from one paragraph
- Append parseable entries to `## ACTUAL -> ### Timeline`
- Route unparseable statements to `## Inbox`
- Atomic write + archive backup

Usage:
  python3 bulk_correct_v2.py --date 2026-03-01 --text "13:00-14:30 Results; 15:00-15:30 review"
  python3 bulk_correct_v2.py --date 2026-03-01 --text-file /tmp/corrections.txt --dry-run
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
class ParsedCorrection:
    start: str
    end: str
    plus_1d: bool
    title: str
    ps: str
    pe: str


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


def _split_statements(text: str) -> list[str]:
    parts = re.split(r'[\n；;。]+', text)
    return [p.strip(' -\t') for p in parts if p.strip()]


def _norm_hhmm(hhmm: str) -> str:
    h, m = hhmm.split(':')
    return f'{int(h):02d}:{int(m):02d}'


def _parse_statement(stmt: str) -> ParsedCorrection | None:
    # range pattern first
    m = re.search(
        r'(?P<sapprox>~)?(?P<start>\d{1,2}:\d{2})\s*(?:-|–|到|to)\s*'
        r'(?P<eapprox>~)?(?P<end>\d{1,2}:\d{2})(?P<plus>\(\+1d\))?\s*(?P<title>.*)$',
        stmt,
        flags=re.I,
    )
    if m:
        title = (m.group('title') or '').strip(' ：:，,')
        if not title:
            title = 'Untitled'
        return ParsedCorrection(
            start=_norm_hhmm(m.group('start')),
            end=_norm_hhmm(m.group('end')),
            plus_1d=bool(m.group('plus')),
            title=title,
            ps='approx' if m.group('sapprox') else 'exact',
            pe='approx' if m.group('eapprox') else 'exact',
        )

    # single time fallback => 1-minute note event
    m2 = re.search(r'(?P<t>\d{1,2}:\d{2})\s*(?P<title>.*)$', stmt)
    if m2:
        t = _norm_hhmm(m2.group('t'))
        h, mm = map(int, t.split(':'))
        end_m = mm + 1
        end_h = h + (end_m // 60)
        end_m = end_m % 60
        end_h = end_h % 24
        end = f'{end_h:02d}:{end_m:02d}'
        title = (m2.group('title') or 'Quick note').strip(' ：:，,') or 'Quick note'
        return ParsedCorrection(start=t, end=end, plus_1d=False, title=title, ps='exact', pe='inferred')

    return None


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


def apply_bulk_correction(date_str: str, raw_text: str, dry_run: bool = False) -> dict:
    path = SCHEDULES_DIR / f'{date_str}.md'
    if not path.exists():
        raise FileNotFoundError(f'schedule file not found: {path}')

    text = _ensure_v2_sections(path.read_text())

    statements = _split_statements(raw_text)
    parsed: list[ParsedCorrection] = []
    unresolved: list[str] = []

    for s in statements:
        p = _parse_statement(s)
        if p is None:
            unresolved.append(s)
        else:
            parsed.append(p)

    # Build lines for ACTUAL timeline
    new_lines = []
    for i, p in enumerate(parsed, start=1):
        uid = _mint_uid(date_str, p.start, p.end, p.title, i)
        end_label = f"{p.end}(+1d)" if p.plus_1d else p.end
        s_label = f"~{p.start}" if p.ps == 'approx' else p.start
        e_label = f"~{end_label}" if p.pe == 'approx' else end_label
        new_lines.append(
            f"- [A] {s_label}-{e_label} {p.title} "
            f"{{uid:{uid}, ps:{p.ps}, pe:{p.pe}, status:done}}"
        )

    if new_lines:
        if re.search(r'^###\s+Timeline\s*$', text, flags=re.M):
            text = re.sub(
                r'(^###\s+Timeline\s*$)',
                '\\1\n' + '\n'.join(new_lines),
                text,
                count=1,
                flags=re.M,
            )

    if unresolved:
        inbox_lines = [f"- [needs_resolution] {u}" for u in unresolved]
        if re.search(r'^##\s+Inbox\s*$', text, flags=re.M):
            text = re.sub(
                r'(^##\s+Inbox\s*$)',
                '\\1\n' + '\n'.join(inbox_lines),
                text,
                count=1,
                flags=re.M,
            )
        else:
            text = text.rstrip() + '\n\n## Inbox\n' + '\n'.join(inbox_lines) + '\n'

    archive = None
    if not dry_run:
        archive = _archive_and_atomic_write(path, text)

    return {
        'date': date_str,
        'schedule_file': str(path),
        'added_actual': len(new_lines),
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
