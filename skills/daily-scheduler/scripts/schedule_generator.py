"""schedule_generator.py — conflict detection, spillover, and file writing."""
import re
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'lib'))
from common import now as _now, today_str as _today_str

sys.path.insert(0, str(Path(__file__).resolve().parent))
from schedule_parser import TimeBlock, DaySchedule, SCHEDULES_DIR, parse_schedule


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
