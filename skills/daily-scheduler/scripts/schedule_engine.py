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
import shutil

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


def write_with_archive_atomic(path: Path, content: str) -> Path | None:
    """Write file via temp+rename and archive previous version if it exists.

    Returns archive path when backup was created, else None.
    """
    archive_path = None
    if path.exists():
        archive_dir = SCHEDULES_DIR / '.archive' / path.stem
        archive_dir.mkdir(parents=True, exist_ok=True)
        ts = _now().strftime('%Y%m%dT%H%M%S')
        archive_path = archive_dir / f'{ts}.md'
        shutil.copy2(path, archive_path)

    tmp_path = path.with_suffix(path.suffix + '.tmp')
    tmp_path.write_text(content)
    tmp_path.replace(path)
    return archive_path


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

    # Extract blocks from ALL version sections (not just latest)
    # This gives accurate block count for completion rate calculation
    sections = re.split(r'^## ', text, flags=re.MULTILINE)

    # Collect blocks from all versions, latest version wins for duplicates
    all_blocks = {}  # key: start_time -> TimeBlock (latest version wins)
    block_pattern = re.compile(
        r'• (\d{2}:\d{2})[–-](\d{2}:\d{2})\s+(\S+)\s+(.*?)(?:\n|$)'
    )

    for section in sections:
        if not section.startswith('v'):
            continue
        if '已被' in section and '取代' in section:
            continue  # Skip superseded versions like "v2 [已被 v3 取代]"
        if '實際紀錄' in section:
            continue

        for match in block_pattern.finditer(section):
            start, end, emoji, title = match.groups()
            title = title.strip()
            title = re.sub(r'\*\*(.*?)\*\*', r'\1', title)
            block = TimeBlock(
                start=start, end=end, emoji=emoji,
                title=title, is_fixed='📅' in emoji or '💊' in emoji or '💧' in emoji,
            )
            all_blocks[start] = block  # Latest version overwrites earlier

    schedule.blocks = sorted(all_blocks.values(), key=lambda b: b.start_minutes)

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


def cmd_dayend(args):
    """Run day-end review: append review to today, spillover to tomorrow."""
    today = args.date or _today_str()
    dry_run = args.dry_run
    tomorrow = (datetime.strptime(today, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')

    today_path = SCHEDULES_DIR / f'{today}.md'
    tomorrow_path = SCHEDULES_DIR / f'{tomorrow}.md'

    # 1. Parse today's schedule
    schedule = parse_schedule(today_path)
    if not schedule:
        print(f"❌ No schedule file for {today}", file=sys.stderr)
        sys.exit(1)

    # 2. Build review section
    total_blocks = len(schedule.blocks)
    completed = len([l for l in schedule.actual_log if '✅' in l])
    rate = int(completed / total_blocks * 100) if total_blocks else 0
    now_ts = _now().strftime('%H:%M')

    review_lines = [
        f"## 日終回顧 (auto, {now_ts})",
        f"- 完成率: {completed}/{total_blocks} ({rate}%)",
    ]

    # Spillover items (cap at 5 to avoid avalanche)
    spill_items = get_spillover(today)[:5]
    if spill_items:
        spill_titles = [s['title'][:30] for s in spill_items]
        review_lines.append(f"- 未完成 → 明日: {', '.join(spill_titles)}")

    # Highlights: entries with 🏆 or notable achievement keywords
    HIGHLIGHT_KEYWORDS = {'突破', '成功', '🏆', '重大', '卡位', '達成', '第一名', '錄取'}
    highlights = []
    for entry in schedule.actual_log:
        if any(kw in entry for kw in HIGHLIGHT_KEYWORDS):
            clean = re.sub(r'^✅\s*[\d:–-]+\s*', '', entry).strip()
            clean = re.sub(r'\*\*(.*?)\*\*', r'\1', clean).strip()
            if clean:
                highlights.append(clean[:60])
    if highlights:
        review_lines.append(f"- 亮點: {'; '.join(highlights[:3])}")

    review_section = '\n'.join(review_lines)

    # 3. Append/replace 日終回顧 in today's file (idempotent)
    today_text = today_path.read_text()
    if '## 日終回顧' in today_text:
        new_today_text = re.sub(
            r'## 日終回顧.*?(?=\n## |\Z)',
            review_section + '\n',
            today_text,
            flags=re.DOTALL,
        )
    else:
        new_today_text = today_text.rstrip('\n') + '\n\n' + review_section + '\n'

    print("=== 日終回顧 ===")
    print(review_section)

    # 4. Build spillover note for tomorrow (same items, formatted)
    spillover_note = ''
    if spill_items:
        spill_names = '、'.join(s['title'][:20] for s in spill_items)
        spillover_note = f"> 📥 昨日未完成：{spill_names}"

    # 5. Prepend spillover note to tomorrow's latest version section
    new_tomorrow_text = None
    if not tomorrow_path.exists():
        print(f"\n⚠️  Tomorrow's file ({tomorrow}) not found — spillover note skipped")
    elif not spillover_note:
        print(f"\n✅ No spillover items — tomorrow's file unchanged")
    else:
        tomorrow_text = tomorrow_path.read_text()
        # Find the last ## vN header line and insert note right after it
        v_matches = list(re.finditer(r'^(## v\d+[^\n]*\n)', tomorrow_text, re.MULTILINE))
        if v_matches:
            insert_pos = v_matches[-1].end()
            if '📥 昨日未完成' in tomorrow_text:
                # Replace existing spillover note (idempotent)
                new_tomorrow_text = re.sub(
                    r'> 📥 昨日未完成：[^\n]*\n?',
                    spillover_note + '\n',
                    tomorrow_text,
                )
            else:
                new_tomorrow_text = (
                    tomorrow_text[:insert_pos]
                    + spillover_note + '\n'
                    + tomorrow_text[insert_pos:]
                )
        else:
            # No version section found — prepend to file body
            new_tomorrow_text = spillover_note + '\n\n' + tomorrow_text
        print(f"\n=== 明日 ({tomorrow}) 溢出備注 ===")
        print(spillover_note)

    # 6. Print summary
    print(f"\n=== 摘要 ===")
    print(f"📊 {today}: {completed}/{total_blocks} 完成 ({rate}%)")
    if spill_items:
        print(f"📥 {len(spill_items)} 項 spillover → {tomorrow}")
    else:
        print(f"🎉 今日全勤，無溢出項目")

    if dry_run:
        print("\n[dry-run] 未寫入任何文件")
        return

    today_archive = write_with_archive_atomic(today_path, new_today_text)
    if today_archive:
        print(f"🗂️ 備份：{today_archive}")
    print(f"✅ 已寫入 {today_path.name}")
    if new_tomorrow_text is not None:
        tomorrow_archive = write_with_archive_atomic(tomorrow_path, new_tomorrow_text)
        if tomorrow_archive:
            print(f"🗂️ 備份：{tomorrow_archive}")
        print(f"✅ 已更新 {tomorrow_path.name}")


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


def cmd_update(args):
    """Generate a new schedule version based on current progress.

    Reads the schedule file, classifies blocks by time/completion status,
    shifts remaining blocks if behind, and outputs a ready-to-paste vN section.

    Trade-offs:
    - Deterministic (no LLM): fast, zero tokens, but can't intelligently
      reorder tasks by energy or priority — just shifts them in time.
    - Gaps between blocks are preserved (intentional buffers kept as-is).
    - Overflow blocks go to ⚠️ 未排入, not dropped silently.
    """
    date = args.date or _today_str()
    filepath = SCHEDULES_DIR / f'{date}.md'
    schedule = parse_schedule(filepath)

    if not schedule:
        print(f"❌ No schedule file for {date}", file=sys.stderr)
        print(f"   Expected: {filepath}", file=sys.stderr)
        sys.exit(1)

    # ── 1. Determine current time ──
    now_str = args.now or _now().strftime('%H:%M')
    try:
        now_h, now_m = int(now_str[:2]), int(now_str[3:5])
    except (ValueError, IndexError):
        print(f"❌ Invalid --now format: {now_str!r} (expected HH:MM)", file=sys.stderr)
        sys.exit(1)
    now_min = now_h * 60 + now_m

    # ── 2. Parse completed keywords ──
    completed_keywords: list[str] = []
    if args.completed:
        completed_keywords = [k.strip() for k in args.completed.split(',') if k.strip()]

    def _matches_completed(title: str) -> bool:
        """Case-insensitive substring match for completed keywords."""
        tl = title.lower()
        return any(kw.lower() in tl for kw in completed_keywords)

    # ── 3. Classify blocks by time ──
    sorted_blocks = sorted(schedule.blocks, key=lambda b: b.start_minutes)
    past_blocks: list[TimeBlock] = []
    current_block: TimeBlock | None = None
    future_blocks: list[TimeBlock] = []

    for block in sorted_blocks:
        if block.end_minutes <= now_min:
            past_blocks.append(block)
        elif block.start_minutes <= now_min < block.end_minutes:
            current_block = block
        else:
            future_blocks.append(block)

    # ── 4. Handle completed keywords against current/future blocks ──
    # If current block is in completed list, user finished it early → treat as past
    if current_block and _matches_completed(current_block.title):
        past_blocks.append(current_block)
        current_block = None

    # Future blocks: split into explicitly-done vs still-remaining
    explicitly_done: list[TimeBlock] = []
    remaining_blocks: list[TimeBlock] = []
    for block in future_blocks:
        if _matches_completed(block.title):
            explicitly_done.append(block)
        else:
            remaining_blocks.append(block)

    # ── 5. Build shifted schedule ──
    END_OF_DAY = 23 * 60  # 23:00 hard stop

    # Cursor starts at: end of current block (if active), else now
    if current_block:
        cursor = current_block.end_minutes
    else:
        cursor = now_min

    shifted_blocks: list[tuple[TimeBlock, str, str, bool]] = []  # (block, start, end, was_shifted)
    overflow_blocks: list[TimeBlock] = []

    for block in remaining_blocks:
        if block.start_minutes >= cursor:
            # No shift needed — planned start is still in the future
            # But check if the block itself overflows end-of-day
            if block.end_minutes > END_OF_DAY:
                overflow_blocks.append(block)
            else:
                shifted_blocks.append((block, block.start, block.end, False))
                cursor = block.end_minutes
        else:
            # Block planned start is before cursor → needs shift
            new_start_min = cursor
            new_end_min = cursor + block.duration
            if new_end_min <= END_OF_DAY:
                new_start = f"{new_start_min // 60:02d}:{new_start_min % 60:02d}"
                new_end   = f"{new_end_min   // 60:02d}:{new_end_min   % 60:02d}"
                shifted_blocks.append((block, new_start, new_end, True))
                cursor = new_end_min
            else:
                overflow_blocks.append(block)

    # ── 6. Calculate remaining time ──
    remaining_total_min = END_OF_DAY - (current_block.end_minutes if current_block else now_min)
    remaining_total_min = max(0, remaining_total_min)
    remaining_h_raw = remaining_total_min / 60
    # Format: "6h" or "6.5h" (strip trailing zero)
    remaining_label = (f"{remaining_h_raw:.1f}".rstrip('0').rstrip('.')) + 'h'

    # ── 7. Determine next version number ──
    next_version = schedule.version + 1

    # ── 8. Build output ──
    lines: list[str] = []

    lines.append(f"## v{next_version} — 即時更新 ({now_str})")
    lines.append("")
    lines.append(f"📅 {schedule.date}（{schedule.weekday}）剩餘行程（{remaining_label}）")
    lines.append("")

    # Edge case: nothing left
    if not current_block and not shifted_blocks:
        lines.append("✅ 今日行程已全部完成！")
    else:
        # Currently active block
        if current_block:
            remaining_in_block = current_block.end_minutes - now_min
            lines.append(
                f"• {current_block.start}–{current_block.end} 🔵 "
                f"{current_block.emoji} {current_block.title}"
                f"（進行中，{remaining_in_block}min 後結束）"
            )

        # Remaining / shifted blocks
        for block, start, end, was_shifted in shifted_blocks:
            suffix = "（⚡ 順延）" if was_shifted else ""
            lines.append(f"• {start}–{end} {block.emoji} {block.title}{suffix}")

    # Unscheduled: original + overflow from this update
    all_unscheduled = list(schedule.unscheduled)
    for block in overflow_blocks:
        all_unscheduled.append(block.title)

    if all_unscheduled:
        lines.append("")
        lines.append(f"⚠️ 未排入：{'、'.join(all_unscheduled)}")

    # Update reason
    lines.append("")
    reason_parts: list[str] = []
    if args.context:
        reason_parts.append(args.context)
    if completed_keywords:
        reason_parts.append(f"已完成：{', '.join(completed_keywords)}")
    if current_block:
        reason_parts.append(f"進行中：{current_block.title}")
    shifted_count = sum(1 for _, _, _, shifted in shifted_blocks if shifted)
    if shifted_count:
        reason_parts.append(f"{shifted_count} 個區塊順延")
    if overflow_blocks:
        reason_parts.append(f"{len(overflow_blocks)} 個區塊移出（時間不足）")
    if not reason_parts:
        reason_parts.append(f"基於 {now_str} 現況更新")

    lines.append(f"> 更新原因：{'；'.join(reason_parts)}")

    print('\n'.join(lines))


def cmd_stats(args):
    """Show weekly completion statistics across multiple days."""
    days = args.days
    today = datetime.strptime(_today_str(), '%Y-%m-%d')

    total_blocks_all = 0
    total_completed_all = 0
    total_skipped_all = 0
    day_stats = []

    for i in range(days - 1, -1, -1):
        d = (today - timedelta(days=i)).strftime('%Y-%m-%d')
        filepath = SCHEDULES_DIR / f'{d}.md'
        schedule = parse_schedule(filepath)

        if not schedule or not schedule.blocks:
            day_stats.append((d, None, None, None, False))
            continue

        blocks = len(schedule.blocks)
        completed = len([l for l in schedule.actual_log if '✅' in l])
        skipped = len([l for l in schedule.actual_log if '❌' in l])
        has_log = len(schedule.actual_log) > 0

        total_blocks_all += blocks
        total_completed_all += completed
        total_skipped_all += skipped
        day_stats.append((d, blocks, completed, skipped, has_log))

    # Render
    print(f"📊 Schedule Stats ({days} days)")
    print("━" * 45)

    for d, blocks, completed, skipped, has_log in day_stats:
        weekday = WEEKDAYS_ZH[datetime.strptime(d, '%Y-%m-%d').weekday()]
        if blocks is None:
            print(f"  {d}（{weekday}）  — 無排程")
            continue
        if not has_log:
            print(f"  {d}（{weekday}）  📋 {blocks} blocks（未記錄）")
            continue

        rate = int(completed / blocks * 100) if blocks else 0
        bar_len = 10
        filled = min(bar_len, int(rate / 100 * bar_len))
        bar = '█' * filled + '░' * (bar_len - filled)

        status = '🎉' if rate >= 80 else '👍' if rate >= 50 else '⚠️'
        skip_note = f'  ❌{skipped}' if skipped else ''
        print(f"  {d}（{weekday}）  {bar} {rate:3d}% ({completed}/{blocks}) {status}{skip_note}")

    print("━" * 45)

    if total_blocks_all > 0:
        overall_rate = int(total_completed_all / total_blocks_all * 100)
        print(f"  Overall: {total_completed_all}/{total_blocks_all} ({overall_rate}%)")
        active_days = sum(1 for _, b, _, _, hl in day_stats if b and hl)
        print(f"  Active days: {active_days}/{days}")
    else:
        print("  No schedule data found")


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

    p_dayend = sub.add_parser('dayend', help='Day-end review + spillover to tomorrow')
    p_dayend.add_argument('--date', type=str, default=None)
    p_dayend.add_argument('--dry-run', action='store_true', help='Print without writing files')

    p_stats = sub.add_parser('stats', help='Weekly completion stats')
    p_stats.add_argument('--days', type=int, default=7, help='Number of days to look back')

    p_update = sub.add_parser('update', help='Generate schedule update based on current progress')
    p_update.add_argument('--date', type=str, default=None)
    p_update.add_argument('--now', type=str, default=None, help='Current time (HH:MM)')
    p_update.add_argument('--completed', type=str, default=None,
                          help='Comma-separated completed items (keyword match)')
    p_update.add_argument('--context', type=str, default=None,
                          help='Context note for the update reason')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    {'view': cmd_view, 'conflicts': cmd_conflicts, 'spillover': cmd_spillover,
     'review': cmd_review, 'parse': cmd_parse, 'dayend': cmd_dayend,
     'update': cmd_update, 'stats': cmd_stats}[args.command](args)


if __name__ == '__main__':
    main()
