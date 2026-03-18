"""
Unit tests for schedule_engine.py — deterministic schedule logic.

Mocking strategy
----------------
The `common` module is stubbed into sys.modules *before* schedule_engine is
imported so that the module-level bindings (TZ, _now, _today_str, WORKSPACE,
MEMORY, SCHEDULES_DIR) all resolve to our controlled values.  Per-test
patching is done via @patch("schedule_engine.<name>") where needed.
"""

import types
import sys
import pathlib
from datetime import timezone, timedelta, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Bootstrap: stub the `common` module before schedule_engine is imported
# ---------------------------------------------------------------------------

_common = types.ModuleType("common")
_TZ = timezone(timedelta(hours=8), name='Asia/Taipei')
_common.TZ = _TZ
_common.now = MagicMock(return_value=datetime(2026, 3, 15, 14, 30, tzinfo=_TZ))
_common.today_str = MagicMock(return_value='2026-03-15')
_common.WORKSPACE = Path('/tmp/test_workspace')
_common.MEMORY = Path('/tmp/test_workspace/memory')
sys.modules["common"] = _common

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import schedule_engine  # noqa: E402  (must come after sys.modules manipulation)

from schedule_engine import (  # noqa: E402
    TimeBlock,
    DaySchedule,
    parse_schedule,
    detect_conflicts,
    get_spillover,
    render_display,
    render_review,
    write_with_archive_atomic,
    SCHEDULES_DIR,
)


# ===========================================================================
# TestTimeBlock — property calculations
# ===========================================================================

class TestTimeBlock:
    def test_start_minutes_basic(self):
        """09:30 → 9*60+30 = 570."""
        block = TimeBlock("09:30", "12:00", "test")
        assert block.start_minutes == 570

    def test_end_minutes_basic(self):
        """12:00 → 12*60+0 = 720."""
        block = TimeBlock("09:30", "12:00", "test")
        assert block.end_minutes == 720

    def test_duration_normal(self):
        """12:00 - 09:30 = 150 minutes."""
        block = TimeBlock("09:30", "12:00", "test")
        assert block.duration == 150

    def test_duration_cross_midnight(self):
        """23:00 to 01:00 spans midnight: 60 + 60 = 120 minutes."""
        block = TimeBlock("23:00", "01:00", "sleep")
        assert block.duration == 120

    def test_duration_zero(self):
        """start == end: d = 0, not negative, so no wraparound → returns 0.

        The cross-midnight branch requires d < 0; identical times give d == 0,
        which is not < 0, so the result is 0 (no wrap).
        """
        block = TimeBlock("10:00", "10:00", "x")
        assert block.duration == 0

    def test_midnight_end(self):
        """22:00 to 00:00: end_minutes=0, d=0-1320=-1320, +1440=120."""
        block = TimeBlock("22:00", "00:00", "x")
        assert block.end_minutes == 0
        assert block.duration == 120

    def test_start_minutes_midnight(self):
        """00:00 → 0 minutes."""
        block = TimeBlock("00:00", "01:00", "early")
        assert block.start_minutes == 0

    def test_end_minutes_end_of_day(self):
        """23:59 → 23*60+59 = 1439."""
        block = TimeBlock("22:00", "23:59", "late")
        assert block.end_minutes == 1439


# ===========================================================================
# TestParseSchedule — parsing .md files into DaySchedule
# ===========================================================================

_BASIC_MD = """\
# 2026-03-15（日）

## v1

• 09:00–10:30 🔬 AudioMatters 深度工作
• 10:30–11:00 ☕ 緩衝休息
• 12:00–13:00 🍜 午餐

> 今天需要注意睡眠
"""

_VERSIONED_MD = """\
# 2026-03-15（日）

## v1

• 09:00–10:30 🔬 任務A

## v2

• 09:00–10:30 🔬 任務B覆蓋
• 11:00–12:00 📅 會議

## v3

• 14:00–15:00 💊 藥
"""

_SUPERSEDED_MD = """\
# 2026-03-15（日）

## v1 [已被 v2 取代]

• 09:00–10:00 🔬 舊版任務

## v2

• 09:00–10:00 🔬 新版任務
"""

_UNSCHEDULED_MD = """\
# 2026-03-15（日）

## v1

• 09:00–10:00 🔬 任務A

⚠️ 未排入：任務X、任務Y、任務Z
"""

_ACTUAL_LOG_MD = """\
# 2026-03-15（日）

## v1

• 09:00–10:00 🔬 任務A

## 實際紀錄

- ✅ 09:00–10:00 完成了任務A
- ❌ 10:30–11:00 跳過了休息
- 一般備注
"""

_CONTEXT_NOTES_MD = """\
# 2026-03-15（日）

> 第一條備注
> 第二條備注

## v1

• 09:00–10:00 🔬 任務A
"""


class TestParseSchedule:
    def test_nonexistent_file_returns_none(self, tmp_path):
        """A path that does not exist on disk returns None."""
        result = parse_schedule(tmp_path / "no-such-file.md")
        assert result is None

    def test_basic_parse_date(self, tmp_path):
        """Date is extracted from filename stem."""
        f = tmp_path / "2026-03-15.md"
        f.write_text(_BASIC_MD)
        sched = parse_schedule(f)
        assert sched is not None
        assert sched.date == "2026-03-15"

    def test_basic_parse_weekday(self, tmp_path):
        """2026-03-15 is a Sunday → 日."""
        f = tmp_path / "2026-03-15.md"
        f.write_text(_BASIC_MD)
        sched = parse_schedule(f)
        assert sched.weekday == "日"

    def test_basic_parse_version(self, tmp_path):
        """Single '## v1' header → version == 1."""
        f = tmp_path / "2026-03-15.md"
        f.write_text(_BASIC_MD)
        sched = parse_schedule(f)
        assert sched.version == 1

    def test_version_extraction_picks_maximum(self, tmp_path):
        """Multiple version headers → version is the highest one found."""
        f = tmp_path / "2026-03-15.md"
        f.write_text(_VERSIONED_MD)
        sched = parse_schedule(f)
        assert sched.version == 3

    def test_block_parsing_count(self, tmp_path):
        """Three bullet blocks in _BASIC_MD → three TimeBlock objects."""
        f = tmp_path / "2026-03-15.md"
        f.write_text(_BASIC_MD)
        sched = parse_schedule(f)
        assert len(sched.blocks) == 3

    def test_block_parsing_fields(self, tmp_path):
        """First block: start=09:00, end=10:30, emoji=🔬."""
        f = tmp_path / "2026-03-15.md"
        f.write_text(_BASIC_MD)
        sched = parse_schedule(f)
        first = sched.blocks[0]
        assert first.start == "09:00"
        assert first.end == "10:30"
        assert first.emoji == "🔬"
        assert "AudioMatters" in first.title

    def test_blocks_sorted_by_start(self, tmp_path):
        """Blocks come out sorted by start_minutes regardless of file order."""
        f = tmp_path / "2026-03-15.md"
        f.write_text(_BASIC_MD)
        sched = parse_schedule(f)
        starts = [b.start_minutes for b in sched.blocks]
        assert starts == sorted(starts)

    def test_superseded_version_skipped(self, tmp_path):
        """Section with '已被' and '取代' must not contribute blocks."""
        f = tmp_path / "2026-03-15.md"
        f.write_text(_SUPERSEDED_MD)
        sched = parse_schedule(f)
        # v1 is superseded; only v2's block should appear
        assert len(sched.blocks) == 1
        assert sched.blocks[0].title == "新版任務"

    def test_latest_version_overwrites_earlier(self, tmp_path):
        """Same start time in v1 and v2 → only v2's title survives."""
        f = tmp_path / "2026-03-15.md"
        f.write_text(_VERSIONED_MD)
        sched = parse_schedule(f)
        block_09 = next(b for b in sched.blocks if b.start == "09:00")
        assert block_09.title == "任務B覆蓋"

    def test_unscheduled_parsing(self, tmp_path):
        """⚠️ 未排入 items are split by '、' and stored in unscheduled."""
        f = tmp_path / "2026-03-15.md"
        f.write_text(_UNSCHEDULED_MD)
        sched = parse_schedule(f)
        assert sched.unscheduled == ["任務X", "任務Y", "任務Z"]

    def test_actual_log_parsing(self, tmp_path):
        """Lines starting with '- ' in 實際紀錄 section are captured."""
        f = tmp_path / "2026-03-15.md"
        f.write_text(_ACTUAL_LOG_MD)
        sched = parse_schedule(f)
        assert len(sched.actual_log) == 3
        assert sched.actual_log[0].startswith("✅")
        assert sched.actual_log[1].startswith("❌")

    def test_context_notes_parsing(self, tmp_path):
        """Lines starting with '> ' are captured as context_notes."""
        f = tmp_path / "2026-03-15.md"
        f.write_text(_CONTEXT_NOTES_MD)
        sched = parse_schedule(f)
        assert sched.context_notes == ["第一條備注", "第二條備注"]

    def test_empty_file(self, tmp_path):
        """Empty .md file returns a schedule with empty blocks and version 0."""
        f = tmp_path / "2026-03-15.md"
        f.write_text("")
        sched = parse_schedule(f)
        assert sched is not None
        assert sched.blocks == []
        assert sched.version == 0

    def test_raw_text_preserved(self, tmp_path):
        """The original file text is stored in raw_text."""
        f = tmp_path / "2026-03-15.md"
        f.write_text(_BASIC_MD)
        sched = parse_schedule(f)
        assert sched.raw_text == _BASIC_MD

    def test_bold_markup_stripped_from_title(self, tmp_path):
        """**bold** markers inside a block title are removed."""
        content = "## v1\n\n• 09:00–10:00 🔬 **重要** 任務\n"
        f = tmp_path / "2026-03-15.md"
        f.write_text(content)
        sched = parse_schedule(f)
        assert "**" not in sched.blocks[0].title
        assert "重要" in sched.blocks[0].title

    def test_is_fixed_set_for_calendar_emoji(self, tmp_path):
        """Blocks with 📅 emoji have is_fixed=True."""
        content = "## v1\n\n• 10:00–11:00 📅 固定會議\n"
        f = tmp_path / "2026-03-15.md"
        f.write_text(content)
        sched = parse_schedule(f)
        assert sched.blocks[0].is_fixed is True

    def test_is_fixed_false_for_research_emoji(self, tmp_path):
        """Blocks with 🔬 emoji have is_fixed=False."""
        content = "## v1\n\n• 10:00–11:00 🔬 研究任務\n"
        f = tmp_path / "2026-03-15.md"
        f.write_text(content)
        sched = parse_schedule(f)
        assert sched.blocks[0].is_fixed is False


# ===========================================================================
# TestDetectConflicts — overlapping time block detection
# ===========================================================================

class TestDetectConflicts:
    def test_no_conflicts_returns_empty(self):
        """Non-overlapping blocks → empty conflict list."""
        blocks = [
            TimeBlock("09:00", "10:00", "A"),
            TimeBlock("10:00", "11:00", "B"),
            TimeBlock("11:30", "12:30", "C"),
        ]
        assert detect_conflicts(blocks) == []

    def test_one_conflict(self):
        """Two overlapping blocks return one conflict pair."""
        a = TimeBlock("09:00", "10:30", "A")
        b = TimeBlock("10:00", "11:00", "B")
        conflicts = detect_conflicts([a, b])
        assert len(conflicts) == 1
        # The pair should contain both blocks (order may vary inside the tuple)
        pair = conflicts[0]
        assert a in pair
        assert b in pair

    def test_adjacent_blocks_no_conflict(self):
        """Block ending exactly when the next starts is not a conflict."""
        blocks = [
            TimeBlock("09:00", "10:00", "A"),
            TimeBlock("10:00", "11:00", "B"),
        ]
        # a.end_minutes == b.start_minutes → not a.end_minutes > b.start_minutes
        assert detect_conflicts(blocks) == []

    def test_multiple_conflicts(self):
        """Three mutually overlapping blocks produce two conflict pairs."""
        a = TimeBlock("09:00", "11:00", "A")
        b = TimeBlock("10:00", "12:00", "B")
        c = TimeBlock("11:30", "13:00", "C")
        # a overlaps b, b overlaps c
        conflicts = detect_conflicts([a, b, c])
        assert len(conflicts) == 2

    def test_single_block_no_conflict(self):
        """A single block cannot conflict with itself."""
        blocks = [TimeBlock("09:00", "10:00", "solo")]
        assert detect_conflicts(blocks) == []

    def test_empty_blocks_no_conflict(self):
        """Empty list → no conflicts."""
        assert detect_conflicts([]) == []

    def test_unsorted_input_still_detects_conflict(self):
        """detect_conflicts internally sorts, so order of input doesn't matter."""
        b = TimeBlock("10:00", "11:30", "B")
        a = TimeBlock("09:00", "10:30", "A")
        conflicts = detect_conflicts([b, a])  # reversed order
        assert len(conflicts) == 1


# ===========================================================================
# TestGetSpillover — unfinished task extraction
# ===========================================================================

class TestGetSpillover:
    def test_no_schedule_returns_empty(self, tmp_path):
        """When parse_schedule returns None, get_spillover returns []."""
        nonexistent = "2020-01-01"
        with patch("schedule_engine.parse_schedule", return_value=None):
            result = get_spillover(nonexistent)
        assert result == []

    def test_routine_blocks_skipped_by_emoji(self):
        """Blocks with routine emojis (🚿, 🍜, etc.) are excluded from spillover."""
        skip_emojis = ['🚿', '🍜', '🍽️', '☕', '🌙', '🎮', '🚶', '💊', '💧']
        for emoji in skip_emojis:
            block = TimeBlock("09:00", "10:00", f"例行任務{emoji}", emoji=emoji)
            sched = DaySchedule(
                date="2026-03-14",
                blocks=[block],
                actual_log=[],
                unscheduled=[],
            )
            with patch("schedule_engine.parse_schedule", return_value=sched):
                result = get_spillover("2026-03-14")
            assert result == [], f"Expected {emoji} block to be skipped"

    def test_routine_blocks_skipped_by_keyword(self):
        """Blocks with skip keywords in title are excluded."""
        skip_keywords = ['午餐', '晚餐', '就寢', '洗澡', '緩衝', '休息']
        for kw in skip_keywords:
            block = TimeBlock("12:00", "13:00", kw, emoji="📋")
            sched = DaySchedule(
                date="2026-03-14",
                blocks=[block],
                actual_log=[],
                unscheduled=[],
            )
            with patch("schedule_engine.parse_schedule", return_value=sched):
                result = get_spillover("2026-03-14")
            assert result == [], f"Expected '{kw}' block to be skipped"

    def test_unfinished_task_detected(self):
        """A task block whose title keywords don't appear in actual_log is spillover."""
        block = TimeBlock("09:00", "10:00", "AudioMatters 深度工作", emoji="🔬")
        sched = DaySchedule(
            date="2026-03-14",
            blocks=[block],
            actual_log=["✅ 09:30–10:00 完全不相關的事情"],
            unscheduled=[],
        )
        with patch("schedule_engine.parse_schedule", return_value=sched):
            result = get_spillover("2026-03-14")
        assert len(result) == 1
        assert result[0]["title"] == "AudioMatters 深度工作"
        assert result[0]["source"] == "spillover"

    def test_completed_task_not_in_spillover(self):
        """A task whose keywords appear sufficiently in actual_log is excluded."""
        block = TimeBlock("09:00", "10:00", "AudioMatters", emoji="🔬")
        sched = DaySchedule(
            date="2026-03-14",
            blocks=[block],
            # 'AudioMatters' appears in the log → match_count >= threshold
            actual_log=["✅ 09:00–10:00 AudioMatters 完成"],
            unscheduled=[],
        )
        with patch("schedule_engine.parse_schedule", return_value=sched):
            result = get_spillover("2026-03-14")
        assert all(r["title"] != "AudioMatters" for r in result)

    def test_unscheduled_items_included(self):
        """Items in schedule.unscheduled appear in spillover with source='unscheduled'."""
        sched = DaySchedule(
            date="2026-03-14",
            blocks=[],
            actual_log=[],
            unscheduled=["待辦A", "待辦B"],
        )
        with patch("schedule_engine.parse_schedule", return_value=sched):
            result = get_spillover("2026-03-14")
        sources = [r["source"] for r in result]
        titles = [r["title"] for r in result]
        assert "unscheduled" in sources
        assert "待辦A" in titles
        assert "待辦B" in titles

    def test_spillover_item_has_original_date(self):
        """Each spillover item carries the original_date of the queried day."""
        block = TimeBlock("09:00", "10:00", "未完成任務XYZ", emoji="🔬")
        sched = DaySchedule(
            date="2026-03-14",
            blocks=[block],
            actual_log=[],
            unscheduled=[],
        )
        with patch("schedule_engine.parse_schedule", return_value=sched):
            result = get_spillover("2026-03-14")
        for item in result:
            assert item["original_date"] == "2026-03-14"

    def test_uses_yesterday_when_date_not_given(self):
        """When date_str=None, get_spillover targets yesterday's file."""
        with patch("schedule_engine._today_str", return_value="2026-03-15"):
            with patch("schedule_engine.parse_schedule", return_value=None) as mock_parse:
                get_spillover(None)
        called_path = mock_parse.call_args[0][0]
        assert "2026-03-14" in str(called_path)


# ===========================================================================
# TestRenderDisplay — time-aware rendering
# ===========================================================================

def _make_schedule(blocks=None, actual_log=None, unscheduled=None,
                   date="2026-03-15", weekday="日"):
    """Helper to build a DaySchedule for rendering tests."""
    return DaySchedule(
        date=date,
        weekday=weekday,
        blocks=blocks or [],
        actual_log=actual_log or [],
        unscheduled=unscheduled or [],
    )


class TestRenderDisplay:
    def test_past_block_gets_checkmark(self):
        """A block that ended before now_str renders with ✅ icon."""
        block = TimeBlock("09:00", "10:00", "已完成任務", emoji="🔬")
        sched = _make_schedule(blocks=[block])
        output = render_display(sched, now_str="11:00")
        assert "✅" in output
        assert "09:00–10:00" in output

    def test_current_block_gets_blue(self):
        """A block spanning now_str renders with 🔵 icon."""
        block = TimeBlock("10:00", "12:00", "進行中任務", emoji="🔬")
        sched = _make_schedule(blocks=[block])
        output = render_display(sched, now_str="11:00")
        assert "🔵" in output

    def test_future_block_gets_hourglass(self):
        """A block starting after now_str renders with ⏳ icon."""
        block = TimeBlock("14:00", "15:00", "未來任務", emoji="🔬")
        sched = _make_schedule(blocks=[block])
        output = render_display(sched, now_str="11:00")
        assert "⏳" in output
        assert "14:00–15:00" in output

    def test_now_marker_appears_before_first_future_block(self):
        """'▶' marker is inserted before the first block whose start > now."""
        past = TimeBlock("09:00", "10:00", "過去任務", emoji="🔬")
        future = TimeBlock("12:00", "13:00", "未來任務", emoji="🔬")
        sched = _make_schedule(blocks=[past, future])
        output = render_display(sched, now_str="11:00")
        assert "▶" in output
        # The marker must appear before the future block line
        marker_pos = output.index("▶")
        future_pos = output.index("12:00–13:00")
        assert marker_pos < future_pos

    def test_now_marker_at_end_when_all_blocks_past(self):
        """When all blocks have ended, the marker appears at the end."""
        block = TimeBlock("09:00", "10:00", "完成任務", emoji="🔬")
        sched = _make_schedule(blocks=[block])
        output = render_display(sched, now_str="23:00")
        assert "行程已結束" in output

    def test_current_block_shows_remaining_minutes(self):
        """Current block line includes remaining minutes until it ends."""
        block = TimeBlock("10:00", "12:00", "長時工作", emoji="🔬")
        sched = _make_schedule(blocks=[block])
        output = render_display(sched, now_str="11:00")
        # 60 minutes remaining
        assert "60m 後結束" in output

    def test_header_contains_date_and_weekday(self):
        """First line of output contains the date and weekday."""
        sched = _make_schedule(date="2026-03-15", weekday="日")
        output = render_display(sched, now_str="09:00")
        assert "2026-03-15" in output
        assert "日" in output

    def test_unscheduled_items_appear_at_end(self):
        """⚠️ 未排入 section with joined items appears when unscheduled is non-empty."""
        sched = _make_schedule(unscheduled=["項目A", "項目B"])
        output = render_display(sched, now_str="09:00")
        assert "⚠️ 未排入" in output
        assert "項目A" in output
        assert "項目B" in output

    def test_completed_log_entries_shown(self):
        """Actual log entries starting with ✅ are rendered at the top."""
        sched = _make_schedule(actual_log=["✅ 09:00–10:00 完成任務"])
        output = render_display(sched, now_str="11:00")
        assert "✅ 09:00–10:00 完成任務" in output

    def test_uses_now_from_module_when_not_provided(self):
        """When now_str is not passed, _now() from the module is called."""
        sched = _make_schedule()
        with patch("schedule_engine._now",
                   return_value=datetime(2026, 3, 15, 9, 0, tzinfo=_TZ)) as mock_now:
            output = render_display(sched)
        mock_now.assert_called_once()
        assert "09:00" in output


# ===========================================================================
# TestRenderReview — day-end review generation
# ===========================================================================

class TestRenderReview:
    def test_completion_rate_calculation(self):
        """3 blocks, 2 ✅ log entries → 66% rate."""
        blocks = [
            TimeBlock("09:00", "10:00", "A", emoji="🔬"),
            TimeBlock("10:00", "11:00", "B", emoji="🔬"),
            TimeBlock("11:00", "12:00", "C", emoji="🔬"),
        ]
        sched = DaySchedule(
            date="2026-03-15",
            weekday="日",
            blocks=blocks,
            actual_log=["✅ A完成", "✅ B完成", "其他備注"],
        )
        # Mock get_spillover to avoid file I/O
        with patch("schedule_engine.get_spillover", return_value=[]):
            output = render_review(sched)
        assert "2/3" in output
        assert "66%" in output

    def test_zero_blocks_zero_percent(self):
        """Schedule with no blocks → 0% completion rate."""
        sched = DaySchedule(
            date="2026-03-15",
            weekday="日",
            blocks=[],
            actual_log=["✅ 某件事"],
        )
        with patch("schedule_engine.get_spillover", return_value=[]):
            output = render_review(sched)
        assert "0%" in output

    def test_output_contains_review_header(self):
        """Output starts with the 日終回顧 header."""
        sched = DaySchedule(date="2026-03-15", weekday="日", blocks=[], actual_log=[])
        with patch("schedule_engine.get_spillover", return_value=[]):
            with patch("schedule_engine._now",
                       return_value=datetime(2026, 3, 15, 22, 0, tzinfo=_TZ)):
                output = render_review(sched)
        assert "日終回顧" in output

    def test_spillover_items_appear_when_present(self):
        """When get_spillover returns items, they appear in the review."""
        sched = DaySchedule(
            date="2026-03-15",
            weekday="日",
            blocks=[TimeBlock("09:00", "10:00", "任務", emoji="🔬")],
            actual_log=[],
        )
        spillover = [{"title": "未完成任務", "emoji": "🔬",
                      "source": "spillover", "original_date": "2026-03-15"}]
        with patch("schedule_engine.get_spillover", return_value=spillover):
            output = render_review(sched)
        assert "未完成任務" in output
        assert "明日" in output

    def test_no_spillover_section_when_empty(self):
        """When get_spillover returns [], the 未完成 line is absent."""
        sched = DaySchedule(
            date="2026-03-15",
            weekday="日",
            blocks=[TimeBlock("09:00", "10:00", "任務", emoji="🔬")],
            actual_log=["✅ 任務"],
        )
        with patch("schedule_engine.get_spillover", return_value=[]):
            output = render_review(sched)
        assert "明日" not in output

    def test_full_completion(self):
        """All blocks matched by ✅ log entries → 100%."""
        blocks = [TimeBlock("09:00", "10:00", "A", emoji="🔬")]
        sched = DaySchedule(
            date="2026-03-15",
            weekday="日",
            blocks=blocks,
            actual_log=["✅ A完成"],
        )
        with patch("schedule_engine.get_spillover", return_value=[]):
            output = render_review(sched)
        assert "100%" in output


# ===========================================================================
# TestWriteWithArchiveAtomic — atomic file write with backup
# ===========================================================================

class TestWriteWithArchiveAtomic:
    def test_creates_file_when_not_exists(self, tmp_path):
        """Writing to a new path creates the file with the given content."""
        target = tmp_path / "2026-03-15.md"
        with patch("schedule_engine.SCHEDULES_DIR", tmp_path / "schedules"):
            write_with_archive_atomic(target, "hello world")
        assert target.exists()
        assert target.read_text() == "hello world"

    def test_returns_none_when_no_prior_file(self, tmp_path):
        """No existing file → no archive created → returns None."""
        target = tmp_path / "2026-03-15.md"
        with patch("schedule_engine.SCHEDULES_DIR", tmp_path / "schedules"):
            result = write_with_archive_atomic(target, "content")
        assert result is None

    def test_archives_existing_file_before_overwrite(self, tmp_path):
        """Existing file is copied to .archive before being replaced."""
        target = tmp_path / "2026-03-15.md"
        target.write_text("original content")
        schedules_dir = tmp_path / "schedules"
        with patch("schedule_engine.SCHEDULES_DIR", schedules_dir):
            with patch("schedule_engine._now",
                       return_value=datetime(2026, 3, 15, 14, 30, tzinfo=_TZ)):
                archive_path = write_with_archive_atomic(target, "new content")
        assert archive_path is not None
        assert archive_path.exists()
        assert archive_path.read_text() == "original content"

    def test_new_content_replaces_old(self, tmp_path):
        """After writing, target file contains the new content."""
        target = tmp_path / "2026-03-15.md"
        target.write_text("old content")
        schedules_dir = tmp_path / "schedules"
        with patch("schedule_engine.SCHEDULES_DIR", schedules_dir):
            with patch("schedule_engine._now",
                       return_value=datetime(2026, 3, 15, 14, 30, tzinfo=_TZ)):
                write_with_archive_atomic(target, "brand new content")
        assert target.read_text() == "brand new content"

    def test_no_temp_file_left_behind(self, tmp_path):
        """The .tmp intermediate file is cleaned up after atomic replace."""
        target = tmp_path / "2026-03-15.md"
        with patch("schedule_engine.SCHEDULES_DIR", tmp_path / "schedules"):
            write_with_archive_atomic(target, "data")
        tmp_file = target.with_suffix(".md.tmp")
        assert not tmp_file.exists()

    def test_archive_filename_uses_timestamp(self, tmp_path):
        """Archive filename matches the strftime format '%Y%m%dT%H%M%S'."""
        target = tmp_path / "2026-03-15.md"
        target.write_text("v1 content")
        schedules_dir = tmp_path / "schedules"
        fixed_now = datetime(2026, 3, 15, 14, 30, 45, tzinfo=_TZ)
        with patch("schedule_engine.SCHEDULES_DIR", schedules_dir):
            with patch("schedule_engine._now", return_value=fixed_now):
                archive_path = write_with_archive_atomic(target, "v2 content")
        assert archive_path is not None
        assert archive_path.name == "20260315T143045.md"
