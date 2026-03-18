#!/usr/bin/env python3
"""
Unit tests for skills/daily-scheduler/scripts/weekly_data.py

weekly_data.py imports from common at module level, which requires filesystem
access and external dependencies. This test module stubs the common module
in sys.modules BEFORE importing weekly_data so no external calls are made.

Covers:
- get_calendar_range()   — grouping, sorting, error handling, days_ahead calc
- get_todoist_range()    — task grouping by due date, overdue, high priority,
                           missing token, API error, priority sorting
- get_existing_schedules() — file detection, preview content, empty case
- build_day_meta()       — weekday/weekend metadata, ZH names, day count

Usage:
    python3 -m pytest skills/daily-scheduler/scripts/test_weekly_data.py -v
    python3 skills/daily-scheduler/scripts/test_weekly_data.py
"""

import types
import sys
import pathlib
import json
from datetime import timezone, timedelta, datetime, date
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Bootstrap: stub common before weekly_data can import it
# ---------------------------------------------------------------------------

_TZ = timezone(timedelta(hours=8), name='Asia/Taipei')
_NOW = datetime(2026, 3, 15, 14, 30, tzinfo=_TZ)

_common = types.ModuleType("common")
_common.TZ = _TZ
_common.now = MagicMock(return_value=_NOW)
_common.WORKSPACE = Path('/tmp/test_workspace')
_common.SECRETS = Path('/tmp/test_workspace/secrets')
_common.SCRIPTS = Path('/tmp/test_workspace/skills/leo-diary/scripts')
sys.modules["common"] = _common

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import weekly_data  # noqa: E402

import pytest  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_START_DATE = date(2026, 3, 15)  # same day as _NOW

def _make_event(summary, start, end='', location='', all_day=False):
    """Build a minimal calendar event dict."""
    return {
        'summary': summary,
        'start': start,
        'end': end,
        'location': location,
        'all_day': all_day,
    }


def _make_task(content, due_date=None, priority=1, task_id='1'):
    """Build a minimal Todoist task dict."""
    due = {'date': due_date} if due_date else None
    return {
        'content': content,
        'due': due,
        'priority': priority,
        'id': task_id,
    }


# ---------------------------------------------------------------------------
# TestGetCalendarRange
# ---------------------------------------------------------------------------

class TestGetCalendarRange:
    """Tests for get_calendar_range(start_date, days)."""

    def test_groups_events_by_date(self):
        """Events on two different dates are placed in separate date buckets."""
        mock_gcal = MagicMock()
        mock_gcal.get_events.return_value = [
            _make_event('Event A', '2026-03-15T09:00:00'),
            _make_event('Event B', '2026-03-16T10:00:00'),
            _make_event('Event C', '2026-03-15T14:00:00'),
        ]
        with patch.dict(sys.modules, {'gcal_today': mock_gcal}):
            result = weekly_data.get_calendar_range(_START_DATE, 7)

        assert '2026-03-15' in result
        assert '2026-03-16' in result
        assert len(result['2026-03-15']) == 2
        assert len(result['2026-03-16']) == 1

    def test_sorts_events_within_day(self):
        """Events returned out of chronological order are sorted by start time."""
        mock_gcal = MagicMock()
        mock_gcal.get_events.return_value = [
            _make_event('Late Event',  '2026-03-15T15:00:00'),
            _make_event('Early Event', '2026-03-15T08:00:00'),
            _make_event('Noon Event',  '2026-03-15T12:00:00'),
        ]
        with patch.dict(sys.modules, {'gcal_today': mock_gcal}):
            result = weekly_data.get_calendar_range(_START_DATE, 7)

        titles = [e['title'] for e in result['2026-03-15']]
        assert titles == ['Early Event', 'Noon Event', 'Late Event']

    def test_returns_error_on_exception(self):
        """When get_events raises, the function returns {'error': str}."""
        mock_gcal = MagicMock()
        mock_gcal.get_events.side_effect = RuntimeError('API failure')
        with patch.dict(sys.modules, {'gcal_today': mock_gcal}):
            result = weekly_data.get_calendar_range(_START_DATE, 7)

        assert 'error' in result
        assert 'API failure' in result['error']

    def test_passes_correct_days_ahead(self):
        """days_ahead is calculated as (start_date - NOW.date()).days."""
        mock_gcal = MagicMock()
        mock_gcal.get_events.return_value = []
        # Use a start_date 3 days ahead of _NOW (which is 2026-03-15)
        future_date = date(2026, 3, 18)
        with patch.dict(sys.modules, {'gcal_today': mock_gcal}):
            weekly_data.get_calendar_range(future_date, 5)

        call_kwargs = mock_gcal.get_events.call_args
        # Accept both positional and keyword arguments
        kwargs = call_kwargs[1] if call_kwargs[1] else {}
        args = call_kwargs[0] if call_kwargs[0] else ()
        days_ahead = kwargs.get('days_ahead', args[0] if args else None)
        assert days_ahead == 3

    def test_all_day_event_date_parsed(self):
        """All-day events (no 'T' in start) are still grouped by date."""
        mock_gcal = MagicMock()
        mock_gcal.get_events.return_value = [
            _make_event('Holiday', '2026-03-15', all_day=True),
        ]
        with patch.dict(sys.modules, {'gcal_today': mock_gcal}):
            result = weekly_data.get_calendar_range(_START_DATE, 7)

        assert '2026-03-15' in result
        assert result['2026-03-15'][0]['all_day'] is True

    def test_event_with_empty_start_is_skipped(self):
        """Events with no start value are silently skipped."""
        mock_gcal = MagicMock()
        mock_gcal.get_events.return_value = [
            {'summary': 'No Start', 'start': '', 'end': ''},
        ]
        with patch.dict(sys.modules, {'gcal_today': mock_gcal}):
            result = weekly_data.get_calendar_range(_START_DATE, 7)

        assert isinstance(result, dict)
        assert 'error' not in result
        assert len(result) == 0

    def test_event_fields_mapped_correctly(self):
        """Each event dict contains title, start, end, location, all_day."""
        mock_gcal = MagicMock()
        mock_gcal.get_events.return_value = [
            _make_event('Meeting', '2026-03-15T10:00:00', '2026-03-15T11:00:00',
                        location='Conference Room', all_day=False),
        ]
        with patch.dict(sys.modules, {'gcal_today': mock_gcal}):
            result = weekly_data.get_calendar_range(_START_DATE, 7)

        event = result['2026-03-15'][0]
        assert event['title'] == 'Meeting'
        assert event['start'] == '2026-03-15T10:00:00'
        assert event['end'] == '2026-03-15T11:00:00'
        assert event['location'] == 'Conference Room'
        assert event['all_day'] is False


# ---------------------------------------------------------------------------
# TestGetTodoistRange
# ---------------------------------------------------------------------------

class TestGetTodoistRange:
    """Tests for get_todoist_range(start_date, days)."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _patch_token(self, tmp_path, token='test-token-abc'):
        """Create a fake todoist.env and patch WORKSPACE to point to tmp_path."""
        secrets_dir = tmp_path / 'secrets'
        secrets_dir.mkdir(parents=True)
        env_file = secrets_dir / 'todoist.env'
        env_file.write_text(f'TODOIST_API_TOKEN={token}\n')
        return tmp_path

    def _mock_urlopen(self, tasks):
        """Return a context manager mock that yields a fake HTTP response."""
        response_data = json.dumps(tasks).encode()
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=cm)
        cm.__exit__ = MagicMock(return_value=False)
        cm.read = MagicMock(return_value=response_data)
        return cm

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_groups_by_due_date(self, tmp_path):
        """Tasks with due dates in range are grouped by date."""
        ws = self._patch_token(tmp_path)
        tasks = [
            _make_task('Task A', '2026-03-15', priority=1, task_id='1'),
            _make_task('Task B', '2026-03-16', priority=1, task_id='2'),
            _make_task('Task C', '2026-03-15', priority=2, task_id='3'),
        ]
        with patch('weekly_data.WORKSPACE', ws):
            with patch('urllib.request.urlopen', return_value=self._mock_urlopen(tasks)):
                result = weekly_data.get_todoist_range(_START_DATE, 7)

        assert 'error' not in result
        assert '2026-03-15' in result['by_date']
        assert '2026-03-16' in result['by_date']
        assert len(result['by_date']['2026-03-15']) == 2

    def test_overdue_tasks(self, tmp_path):
        """Tasks with due dates before today are placed in overdue list."""
        ws = self._patch_token(tmp_path)
        # _NOW is 2026-03-15 so 2026-03-10 is overdue
        tasks = [
            _make_task('Old Task', '2026-03-10', priority=2, task_id='1'),
            _make_task('Current Task', '2026-03-15', priority=1, task_id='2'),
        ]
        with patch('weekly_data.WORKSPACE', ws):
            with patch('urllib.request.urlopen', return_value=self._mock_urlopen(tasks)):
                result = weekly_data.get_todoist_range(_START_DATE, 7)

        assert len(result['overdue']) == 1
        assert result['overdue'][0]['content'] == 'Old Task'

    def test_no_due_high_priority(self, tmp_path):
        """Tasks with no due date and priority >= 3 go to no_due_high_priority."""
        ws = self._patch_token(tmp_path)
        tasks = [
            _make_task('Urgent No Due', due_date=None, priority=4, task_id='1'),
            _make_task('Low No Due',    due_date=None, priority=1, task_id='2'),
            _make_task('Med No Due',    due_date=None, priority=3, task_id='3'),
        ]
        with patch('weekly_data.WORKSPACE', ws):
            with patch('urllib.request.urlopen', return_value=self._mock_urlopen(tasks)):
                result = weekly_data.get_todoist_range(_START_DATE, 7)

        hp = result['no_due_high_priority']
        contents = [t['content'] for t in hp]
        assert 'Urgent No Due' in contents
        assert 'Med No Due' in contents
        assert 'Low No Due' not in contents

    def test_no_token_returns_error(self, tmp_path):
        """When the token file is missing, the function returns {'error': ...}."""
        # Point WORKSPACE to tmp_path where no secrets/todoist.env exists
        with patch('weekly_data.WORKSPACE', tmp_path):
            result = weekly_data.get_todoist_range(_START_DATE, 7)

        assert 'error' in result

    def test_api_error_returns_error(self, tmp_path):
        """When urlopen raises, the function returns {'error': ...}."""
        ws = self._patch_token(tmp_path)
        with patch('weekly_data.WORKSPACE', ws):
            with patch('urllib.request.urlopen', side_effect=OSError('connection refused')):
                result = weekly_data.get_todoist_range(_START_DATE, 7)

        assert 'error' in result
        assert 'connection refused' in result['error']

    def test_sorted_by_priority(self, tmp_path):
        """Tasks within each date bucket are sorted by priority descending."""
        ws = self._patch_token(tmp_path)
        tasks = [
            _make_task('Low',    '2026-03-15', priority=1, task_id='1'),
            _make_task('High',   '2026-03-15', priority=4, task_id='2'),
            _make_task('Medium', '2026-03-15', priority=2, task_id='3'),
        ]
        with patch('weekly_data.WORKSPACE', ws):
            with patch('urllib.request.urlopen', return_value=self._mock_urlopen(tasks)):
                result = weekly_data.get_todoist_range(_START_DATE, 7)

        day_tasks = result['by_date']['2026-03-15']
        priorities = [t['priority'] for t in day_tasks]
        assert priorities == sorted(priorities, reverse=True)

    def test_total_tasks_count(self, tmp_path):
        """Result includes total_tasks count from the API response."""
        ws = self._patch_token(tmp_path)
        tasks = [
            _make_task('Task 1', '2026-03-15', task_id='1'),
            _make_task('Task 2', '2026-03-16', task_id='2'),
            _make_task('Task 3', due_date=None, priority=4, task_id='3'),
        ]
        with patch('weekly_data.WORKSPACE', ws):
            with patch('urllib.request.urlopen', return_value=self._mock_urlopen(tasks)):
                result = weekly_data.get_todoist_range(_START_DATE, 7)

        assert result['total_tasks'] == 3

    def test_tasks_outside_range_excluded(self, tmp_path):
        """Tasks with due dates beyond the requested range are not included."""
        ws = self._patch_token(tmp_path)
        # Range is _START_DATE + 7 days: 2026-03-15 through 2026-03-21
        tasks = [
            _make_task('In Range',  '2026-03-17', task_id='1'),
            _make_task('Out Range', '2026-03-25', task_id='2'),
        ]
        with patch('weekly_data.WORKSPACE', ws):
            with patch('urllib.request.urlopen', return_value=self._mock_urlopen(tasks)):
                result = weekly_data.get_todoist_range(_START_DATE, 7)

        by_date = result['by_date']
        assert '2026-03-17' in by_date
        assert '2026-03-25' not in by_date

    def test_overdue_capped_at_10(self, tmp_path):
        """Overdue list is capped at 10 items."""
        ws = self._patch_token(tmp_path)
        tasks = [
            _make_task(f'Old {i}', f'2026-03-0{i}' if i >= 1 else '2026-03-01',
                       task_id=str(i))
            for i in range(1, 16)
        ]
        # Force all to be overdue by making due dates old enough
        for t in tasks:
            t['due'] = {'date': '2026-03-01'}

        with patch('weekly_data.WORKSPACE', ws):
            with patch('urllib.request.urlopen', return_value=self._mock_urlopen(tasks)):
                result = weekly_data.get_todoist_range(_START_DATE, 7)

        assert len(result['overdue']) <= 10

    def test_no_due_hp_capped_at_5(self, tmp_path):
        """no_due_high_priority list is capped at 5 items."""
        ws = self._patch_token(tmp_path)
        tasks = [
            _make_task(f'HP {i}', due_date=None, priority=4, task_id=str(i))
            for i in range(10)
        ]
        with patch('weekly_data.WORKSPACE', ws):
            with patch('urllib.request.urlopen', return_value=self._mock_urlopen(tasks)):
                result = weekly_data.get_todoist_range(_START_DATE, 7)

        assert len(result['no_due_high_priority']) <= 5


# ---------------------------------------------------------------------------
# TestGetExistingSchedules
# ---------------------------------------------------------------------------

class TestGetExistingSchedules:
    """Tests for get_existing_schedules(start_date, days)."""

    def test_finds_existing_files(self, tmp_path):
        """Days with .md schedule files are reported as existing."""
        schedules_dir = tmp_path / 'memory' / 'schedules'
        schedules_dir.mkdir(parents=True)
        (schedules_dir / '2026-03-15.md').write_text('# Schedule for March 15')
        (schedules_dir / '2026-03-17.md').write_text('# Schedule for March 17')

        with patch('weekly_data.WORKSPACE', tmp_path):
            result = weekly_data.get_existing_schedules(_START_DATE, 7)

        assert '2026-03-15' in result
        assert '2026-03-17' in result
        assert result['2026-03-15']['exists'] is True
        assert result['2026-03-17']['exists'] is True

    def test_no_files_returns_empty(self, tmp_path):
        """When no .md files exist, an empty dict is returned."""
        schedules_dir = tmp_path / 'memory' / 'schedules'
        schedules_dir.mkdir(parents=True)

        with patch('weekly_data.WORKSPACE', tmp_path):
            result = weekly_data.get_existing_schedules(_START_DATE, 7)

        assert result == {}

    def test_reads_preview(self, tmp_path):
        """Preview contains the first 200 characters of the file."""
        schedules_dir = tmp_path / 'memory' / 'schedules'
        schedules_dir.mkdir(parents=True)
        long_content = 'A' * 300
        (schedules_dir / '2026-03-15.md').write_text(long_content)

        with patch('weekly_data.WORKSPACE', tmp_path):
            result = weekly_data.get_existing_schedules(_START_DATE, 7)

        preview = result['2026-03-15']['preview']
        assert len(preview) == 200
        assert preview == 'A' * 200

    def test_reports_file_size(self, tmp_path):
        """Each found file entry includes a non-negative size."""
        schedules_dir = tmp_path / 'memory' / 'schedules'
        schedules_dir.mkdir(parents=True)
        content = '# My Schedule\n\nContent here.'
        (schedules_dir / '2026-03-15.md').write_text(content)

        with patch('weekly_data.WORKSPACE', tmp_path):
            result = weekly_data.get_existing_schedules(_START_DATE, 7)

        assert result['2026-03-15']['size'] == len(content)

    def test_only_dates_in_range_checked(self, tmp_path):
        """Files outside the requested date range are not reported."""
        schedules_dir = tmp_path / 'memory' / 'schedules'
        schedules_dir.mkdir(parents=True)
        # This date is outside the 3-day range starting 2026-03-15
        (schedules_dir / '2026-03-20.md').write_text('Out of range')
        (schedules_dir / '2026-03-15.md').write_text('In range')

        with patch('weekly_data.WORKSPACE', tmp_path):
            result = weekly_data.get_existing_schedules(_START_DATE, days=3)

        assert '2026-03-15' in result
        assert '2026-03-20' not in result

    def test_missing_schedules_dir_returns_empty(self, tmp_path):
        """When the schedules directory does not exist, returns empty dict."""
        # Do NOT create the schedules directory
        with patch('weekly_data.WORKSPACE', tmp_path):
            result = weekly_data.get_existing_schedules(_START_DATE, 7)

        assert result == {}


# ---------------------------------------------------------------------------
# TestBuildDayMeta
# ---------------------------------------------------------------------------

class TestBuildDayMeta:
    """Tests for build_day_meta(start_date, days)."""

    def test_weekday_metadata(self):
        """Monday 2026-03-16 has correct weekday_en and is_weekend=False."""
        monday = date(2026, 3, 16)  # confirmed Monday
        result = weekly_data.build_day_meta(monday, 1)

        meta = result['2026-03-16']
        assert meta['weekday_en'] == 'Monday'
        assert meta['is_weekend'] is False
        assert meta['day_type'] == 'weekday'

    def test_weekend_detection(self):
        """Saturday and Sunday are marked as is_weekend=True with day_type='weekend'."""
        # 2026-03-21 is a Saturday, 2026-03-22 is a Sunday
        saturday = date(2026, 3, 21)
        result = weekly_data.build_day_meta(saturday, 2)

        saturday_meta = result['2026-03-21']
        sunday_meta = result['2026-03-22']

        assert saturday_meta['is_weekend'] is True
        assert saturday_meta['day_type'] == 'weekend'
        assert sunday_meta['is_weekend'] is True
        assert sunday_meta['day_type'] == 'weekend'

    def test_correct_number_of_days(self):
        """Requesting 7 days produces exactly 7 entries."""
        result = weekly_data.build_day_meta(_START_DATE, 7)
        assert len(result) == 7

    def test_correct_number_of_days_custom(self):
        """Requesting 14 days produces exactly 14 entries."""
        result = weekly_data.build_day_meta(_START_DATE, 14)
        assert len(result) == 14

    def test_zh_weekday_names(self):
        """Verify Chinese weekday names for Monday and Sunday."""
        # 2026-03-16 is Monday, 2026-03-22 is Sunday
        monday = date(2026, 3, 16)
        result = weekly_data.build_day_meta(monday, 7)

        assert result['2026-03-16']['weekday_zh'] == '週一'
        assert result['2026-03-22']['weekday_zh'] == '週日'

    def test_zh_weekday_all_names(self):
        """All 7 Chinese weekday names appear correctly in a full week."""
        monday = date(2026, 3, 16)  # Monday
        result = weekly_data.build_day_meta(monday, 7)

        expected = {
            '2026-03-16': '週一',
            '2026-03-17': '週二',
            '2026-03-18': '週三',
            '2026-03-19': '週四',
            '2026-03-20': '週五',
            '2026-03-21': '週六',
            '2026-03-22': '週日',
        }
        for date_str, zh_name in expected.items():
            assert result[date_str]['weekday_zh'] == zh_name, (
                f"{date_str} expected {zh_name}, got {result[date_str]['weekday_zh']}"
            )

    def test_weekday_en_names_correct(self):
        """English weekday names match for a known week."""
        monday = date(2026, 3, 16)
        result = weekly_data.build_day_meta(monday, 7)

        assert result['2026-03-16']['weekday_en'] == 'Monday'
        assert result['2026-03-17']['weekday_en'] == 'Tuesday'
        assert result['2026-03-18']['weekday_en'] == 'Wednesday'
        assert result['2026-03-19']['weekday_en'] == 'Thursday'
        assert result['2026-03-20']['weekday_en'] == 'Friday'
        assert result['2026-03-21']['weekday_en'] == 'Saturday'
        assert result['2026-03-22']['weekday_en'] == 'Sunday'

    def test_weekdays_are_not_weekend(self):
        """Monday through Friday must have is_weekend=False."""
        monday = date(2026, 3, 16)
        result = weekly_data.build_day_meta(monday, 5)

        for date_str, meta in result.items():
            assert meta['is_weekend'] is False, f"{date_str} incorrectly flagged as weekend"
            assert meta['day_type'] == 'weekday'

    def test_single_day(self):
        """Requesting 1 day returns exactly 1 entry with all required keys."""
        result = weekly_data.build_day_meta(_START_DATE, 1)

        assert len(result) == 1
        meta = list(result.values())[0]
        assert 'weekday_zh' in meta
        assert 'weekday_en' in meta
        assert 'is_weekend' in meta
        assert 'day_type' in meta

    def test_date_keys_are_iso_format(self):
        """All keys in the result are ISO-formatted date strings (YYYY-MM-DD)."""
        result = weekly_data.build_day_meta(_START_DATE, 7)

        for key in result:
            # Should parse without error as a date
            parsed = date.fromisoformat(key)
            assert parsed is not None


# ---------------------------------------------------------------------------
# Run directly
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import unittest
    pytest.main([__file__, '-v'])
