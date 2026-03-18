"""schedule_parser.py — data model and markdown parsing for daily schedules."""
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'lib'))
from common import MEMORY

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
        d = self.end_minutes - self.start_minutes
        if d < 0:
            d += 24 * 60  # cross-midnight
        return d


@dataclass
class DaySchedule:
    date: str = ""
    weekday: str = ""
    version: int = 0
    blocks: list[TimeBlock] = field(default_factory=list)
    unscheduled: list[str] = field(default_factory=list)
    context_notes: list[str] = field(default_factory=list)
    actual_log: list[str] = field(default_factory=list)
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
