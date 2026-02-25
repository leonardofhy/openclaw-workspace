#!/usr/bin/env python3
"""schedule_engine.py — deterministic schedule logic.

Handles parsing, generating, conflict detection, spillover, and rendering
of daily schedule files. Reduces LLM token usage for routine operations.

Usage:
  # As library
  from schedule_engine import parse_schedule, generate_day, render_display

  # CLI: view today's schedule from file
  python3 schedule_engine.py view
  python3 schedule_engine.py view --date 2026-02-27

  # CLI: detect conflicts
  python3 schedule_engine.py conflicts --date 2026-02-26

  # CLI: spillover from yesterday
  python3 schedule_engine.py spillover

  # CLI: day-end review
  python3 schedule_engine.py review
"""
import re
import sys
import json
import argparse
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'lib'))
from common import TZ, now as _now, today_str as _today_str, WORKSPACE, MEMORY

SCHEDULES_DIR = MEMORY / 'schedules'
WEEKDAYS_ZH = ['一', '二', '三', '四', '五', '六', '日']

EMOJI_MAP = {
    'research':   '🔬',
    'meeting':    '📅',
    'admin':      '📋',
    'meal':       '🍜',
    'medication': '💊',
    'exercise':   '💪',
    'hygiene':    '🚿',
    'rest':       '🎮',
    'sleep':      '🌙',
    'email':      '✉️',
    'travel':     '🚶',
    'buffer':     '☕',
}


# ── Data Model ──

@dataclass
class TimeBlock:
    start: str           # "09:30"
    end: str             # "12:00"
    title: str           # "AudioMatters 深度工作"
    category: str = ""   # research|meeting|admin|meal|health|rest
    emoji: str = ""
    source: str = ""     # calendar|todoist|pattern|manual
    priority: int = 0    # 0=fixed, 1-4 from todoist
    is_fixed: bool = False
    task_id: str = ""
    notes: str = ""

    @property
    def start_minutes(self) -> int:
        h, m = self.start.split(':')
        return int(h) * 60 + int(m)

    @property
    def end_minutes(self) -> int:
        h, m = self.end.split(':')
        return int(h) * 60 + int(m)

    @property
    def duration(self) -> int:
        return self.end_minutes - self.start_minutes


@dataclass
class DaySchedule:
    date: str = ""
    weekday: str = ""
    version: int = 0
    blocks: list = field(default_factory=list)
    unscheduled: list = field(default_factory=list)
    context_notes: list = field(default_factory=list)
    actual_log: list = field(default_factory=list)
    raw_text: str = ""


# ── Parsing ──

def parse_schedule(filepath: Path) -> DaySchedule | None:
    """Parse a schedule .md file into structured DaySchedule."""
    if not filepath.exists():
        return None

    text = filepath.read_text()
    schedule = DaySchedule(raw_text=text)

    # Extract date from filename
    stem = filepath.stem  # "2026-02-26"
    schedule.date = stem
    try:
        dt = datetime.strptime(stem, '%Y-%m-%d')
        schedule.weekday = WEEKDAYS_ZH[dt.weekday()]
    except ValueError:
        pass

    # Find latest version number
    versions = re.findall(r'## v(\d+)', text)
    schedule.version = max(int(v) for v in versions) if versions else 0

    # Extract blocks from latest version section
    # Find the last ## vN section (before ## 實際紀錄)
    sections = re.split(r'^## ', text, flags=re.MULTILINE)
    latest_schedule_section = ""
    for section in reversed(sections):
        if section.startswith('v') and '實際紀錄' not in section:
            latest_schedule_section = section
            break

    # Parse bullet items as blocks
    block_pattern = re.compile(
        r'• (\d{2}:\d{2})[–-](\d{2}:\d{2})\s+(\S+)\s+(.*?)(?:\n|$)'
    )
    for match in block_pattern.finditer(latest_schedule_section):
        start, end, emoji, title = match.groups()
        title = title.strip()
        # Remove markdown bold
        title = re.sub(r'\*\*(.*?)\*\*', r'\1', title)
        block = TimeBlock(
            start=start, end=end, emoji=emoji,
            title=title, is_fixed='📅' in emoji or '💊' in emoji or '💧' in emoji,
        )
        schedule.blocks.append(block)

    # Parse 未排入
    unscheduled_match = re.search(r'⚠️ 未排入[：:]?\s*(.*?)(?:\n\n|\n>|\n##|$)', text, re.DOTALL)
    if unscheduled_match:
        items = unscheduled_match.group(1).strip()
        schedule.unscheduled = [i.strip() for i in items.split('、') if i.strip()]

    # Parse 實際紀錄
    log_match = re.search(r'## 實際紀錄\s*\n(.*?)(?:\n## |$)', text, re.DOTALL)
    if log_match:
        for line in log_match.group(1).strip().splitlines():
            line = line.strip()
            if line.startswith('- '):
                schedule.actual_log.append(line[2:])

    # Parse context notes
    note_matches = re.findall(r'^> (.+)$', text, re.MULTILINE)
    schedule.context_notes = note_matches

    return schedule


# ── Conflict Detection ──

def detect_conflicts(blocks: list[TimeBlock]) -> list[tuple[TimeBlock, TimeBlock]]:
    """Find overlapping time blocks."""
    conflicts = []
    sorted_blocks = sorted(blocks, key=lambda b: b.start_minutes)
    for i in range(len(sorted_blocks) - 1):
        a = sorted_blocks[i]
        b = sorted_blocks[i + 1]
        if a.end_minutes > b.start_minutes:
            conflicts.append((a, b))
    return conflicts


# ── Spillover ──

def get_spillover(date_str: str | None = None) -> list[dict]:
    """Extract unfinished tasks from a day's schedule.

    Compares planned blocks vs actual_log to find what wasn't completed.
    """
    if date_str is None:
        yesterday = (datetime.strptime(_today_str(), '%Y-%m-%d') - timedelta(days=1))
        date_str = yesterday.strftime('%Y-%m-%d')

    filepath = SCHEDULES_DIR / f'{date_str}.md'
    schedule = parse_schedule(filepath)
    if not schedule:
        return []

    # Collect completed items from log
    completed_text = ' '.join(schedule.actual_log)

    # Skip blocks that are routine (not actionable tasks)
    SKIP_EMOJIS = {'🚿', '🍜', '🍽️', '☕', '🌙', '🎮', '🚶', '💊', '💧'}
    SKIP_KEYWORDS = {'起床', '洗漱', '洗澡', '午餐', '晚餐', '就寢', '睡', '緩衝', '休息', 'Dinner', 'dinner'}

    unfinished = []
    for block in schedule.blocks:
        # Skip routine blocks
        if block.emoji in SKIP_EMOJIS:
            continue
        if any(kw in block.title for kw in SKIP_KEYWORDS):
            continue

        # Check if any log entry references this block's title (fuzzy match)
        title_keywords = [kw for kw in re.findall(r'[\w\u4e00-\u9fff]{2,}', block.title)
                          if kw not in ('deadline', '截止', '今天', '明天')]
        if title_keywords:
            match_count = sum(1 for kw in title_keywords if kw in completed_text)
            if match_count < len(title_keywords) * 0.3:
                unfinished.append({
                    'title': block.title,
                    'emoji': block.emoji,
                    'source': 'spillover',
                    'original_date': date_str,
                })

    # Also include items from 未排入
    for item in schedule.unscheduled:
        unfinished.append({
            'title': item,
            'emoji': '📋',
            'source': 'unscheduled',
            'original_date': date_str,
        })

    return unfinished


# ── Rendering ──

def render_display(schedule: DaySchedule, now_str: str | None = None) -> str:
    """Render schedule with ✅/▶/⏳ markers based on current time."""
    if now_str is None:
        now_str = _now().strftime('%H:%M')

    now_min = int(now_str[:2]) * 60 + int(now_str[3:5])
    lines = []

    lines.append(f"📅 {schedule.date}（{schedule.weekday}）")
    lines.append("")

    # Completed items
    for log_entry in schedule.actual_log:
        if log_entry.startswith('✅'):
            lines.append(f"- {log_entry}")

    # Current + future blocks
    now_printed = False
    for block in sorted(schedule.blocks, key=lambda b: b.start_minutes):
        if not now_printed and block.start_minutes > now_min:
            lines.append(f"▶ **{now_str} ← 現在**")
            now_printed = True

        end_min = block.end_minutes
        if block.start_minutes <= now_min < end_min:
            icon = "🔵"
            remaining = end_min - now_min
            suffix = f" ({remaining}m 後結束)"
        elif now_min >= end_min:
            icon = "✅"
            suffix = ""
        else:
            icon = "⏳"
            suffix = ""

        lines.append(f"• {icon} {block.start}–{block.end} {block.emoji} {block.title}{suffix}")

    if not now_printed:
        lines.append(f"▶ **{now_str} ← 現在（行程已結束）**")

    # Unscheduled
    if schedule.unscheduled:
        lines.append("")
        lines.append(f"⚠️ 未排入：{'、'.join(schedule.unscheduled)}")

    return '\n'.join(lines)


def render_review(schedule: DaySchedule) -> str:
    """Generate day-end review section."""
    total_blocks = len(schedule.blocks)
    completed = len([l for l in schedule.actual_log if '✅' in l])
    skipped = len([l for l in schedule.actual_log if '❌' in l])

    rate = int(completed / total_blocks * 100) if total_blocks else 0

    lines = [
        f"## 日終回顧 (auto, {_now().strftime('%H:%M')})",
        f"- 完成率: {completed}/{total_blocks} ({rate}%)",
    ]

    # Find unfinished items
    spillover = get_spillover(schedule.date)
    if spillover:
        spill_titles = [s['title'][:30] for s in spillover[:3]]
        lines.append(f"- 未完成 → 明日: {', '.join(spill_titles)}")

    return '\n'.join(lines)


# ── CLI ──

def cmd_view(args):
    date = args.date or _today_str()
    filepath = SCHEDULES_DIR / f'{date}.md'
    schedule = parse_schedule(filepath)
    if not schedule:
        print(f"❌ No schedule file for {date}", file=sys.stderr)
        sys.exit(1)

    now_str = args.now or _now().strftime('%H:%M')
    print(render_display(schedule, now_str))


def cmd_conflicts(args):
    date = args.date or _today_str()
    filepath = SCHEDULES_DIR / f'{date}.md'
    schedule = parse_schedule(filepath)
    if not schedule:
        print(f"❌ No schedule file for {date}", file=sys.stderr)
        sys.exit(1)

    conflicts = detect_conflicts(schedule.blocks)
    if conflicts:
        print(f"⚠️ {len(conflicts)} conflict(s) found in {date}:")
        for a, b in conflicts:
            print(f"  {a.start}–{a.end} {a.title}")
            print(f"  ↔ {b.start}–{b.end} {b.title}")
    else:
        print(f"✅ No conflicts in {date}")


def cmd_spillover(args):
    date = args.date  # defaults to yesterday
    items = get_spillover(date)
    if items:
        print(f"📥 {len(items)} spillover item(s):")
        for item in items:
            print(f"  {item['emoji']} {item['title']} (from {item['original_date']})")
    else:
        print("✅ No spillover")


def cmd_review(args):
    date = args.date or _today_str()
    filepath = SCHEDULES_DIR / f'{date}.md'
    schedule = parse_schedule(filepath)
    if not schedule:
        print(f"❌ No schedule file for {date}", file=sys.stderr)
        sys.exit(1)
    print(render_review(schedule))


def cmd_parse(args):
    """Debug: dump parsed schedule as JSON."""
    date = args.date or _today_str()
    filepath = SCHEDULES_DIR / f'{date}.md'
    schedule = parse_schedule(filepath)
    if not schedule:
        print(f"❌ No schedule file for {date}", file=sys.stderr)
        sys.exit(1)

    output = {
        'date': schedule.date,
        'weekday': schedule.weekday,
        'version': schedule.version,
        'blocks': [asdict(b) for b in schedule.blocks],
        'unscheduled': schedule.unscheduled,
        'actual_log': schedule.actual_log,
        'context_notes': schedule.context_notes,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description='Schedule engine CLI')
    sub = parser.add_subparsers(dest='command')

    p_view = sub.add_parser('view', help='View schedule with time markers')
    p_view.add_argument('--date', type=str, default=None)
    p_view.add_argument('--now', type=str, default=None, help='Override current time (HH:MM)')

    p_conflicts = sub.add_parser('conflicts', help='Detect scheduling conflicts')
    p_conflicts.add_argument('--date', type=str, default=None)

    p_spill = sub.add_parser('spillover', help='Show unfinished tasks from yesterday')
    p_spill.add_argument('--date', type=str, default=None, help='Check specific date')

    p_review = sub.add_parser('review', help='Generate day-end review')
    p_review.add_argument('--date', type=str, default=None)

    p_parse = sub.add_parser('parse', help='Debug: dump parsed schedule')
    p_parse.add_argument('--date', type=str, default=None)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    {'view': cmd_view, 'conflicts': cmd_conflicts, 'spillover': cmd_spillover,
     'review': cmd_review, 'parse': cmd_parse}[args.command](args)


if __name__ == '__main__':
    main()
