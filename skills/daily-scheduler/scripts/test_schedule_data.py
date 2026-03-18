#!/usr/bin/env python3
"""Comprehensive pytest unit tests for schedule_data.py.

Bootstrap stubs common in sys.modules before importing the module under test,
since schedule_data does module-level imports from common and captures NOW at
import time.
"""
import io
import json
import types
import sys
import pathlib
from datetime import timezone, timedelta, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open, PropertyMock

# ---------------------------------------------------------------------------
# Bootstrap: stub `common` before schedule_data is imported
# ---------------------------------------------------------------------------
_TZ = timezone(timedelta(hours=8), name='Asia/Taipei')
_NOW = datetime(2026, 3, 15, 14, 30, tzinfo=_TZ)

_common = types.ModuleType("common")
_common.TZ = _TZ
_common.now = MagicMock(return_value=_NOW)
_common.today_str = MagicMock(return_value='2026-03-15')
_common.WORKSPACE = Path('/tmp/test_workspace')
_common.MEMORY = Path('/tmp/test_workspace/memory')
_common.SECRETS = Path('/tmp/test_workspace/secrets')
_common.SCRIPTS = Path('/tmp/test_workspace/skills/leo-diary/scripts')
sys.modules["common"] = _common

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import schedule_data  # noqa: E402  (must come after sys.modules stub)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_EVENTS_UNSORTED = [
    {
        'summary': 'Meeting B',
        'start': '2026-03-15T15:00:00+08:00',
        'end': '2026-03-15T16:00:00+08:00',
        'location': 'Room 2',
        'all_day': False,
    },
    {
        'summary': 'Meeting A',
        'start': '2026-03-15T09:00:00+08:00',
        'end': '2026-03-15T10:00:00+08:00',
        'location': 'Room 1',
        'all_day': False,
    },
]

_SAMPLE_TODOIST_RESPONSE = {
    'results': [
        # due today
        {
            'id': '1',
            'content': 'Task due today P2',
            'priority': 3,
            'due': {'date': '2026-03-15'},
        },
        # overdue
        {
            'id': '2',
            'content': 'Overdue task P1',
            'priority': 4,
            'due': {'date': '2026-03-10'},
        },
        # high priority, no due date
        {
            'id': '3',
            'content': 'High priority no due',
            'priority': 3,
            'due': None,
        },
        # low priority, no due date
        {
            'id': '4',
            'content': 'Low prio no due',
            'priority': 1,
            'due': None,
        },
    ]
}


def _make_urlopen_mock(payload: dict):
    """Return a mock suitable for use as urllib.request.urlopen context manager."""
    raw = json.dumps(payload).encode()
    resp_mock = MagicMock()
    resp_mock.read.return_value = raw
    resp_mock.__enter__ = MagicMock(return_value=resp_mock)
    resp_mock.__exit__ = MagicMock(return_value=False)
    return resp_mock


# ===========================================================================
# TestGetCalendar
# ===========================================================================

class TestGetCalendar:
    """Tests for schedule_data.get_calendar()."""

    def test_returns_sorted_events(self):
        """Events returned by get_events should be sorted by start time."""
        gcal_mock = MagicMock()
        gcal_mock.get_events.return_value = _SAMPLE_EVENTS_UNSORTED

        with patch.dict(sys.modules, {'gcal_today': gcal_mock}):
            result = schedule_data.get_calendar(days_range=1)

        assert len(result) == 2
        assert result[0]['start'] < result[1]['start'], (
            "Events must be sorted by start field ascending"
        )
        assert result[0]['title'] == 'Meeting A'
        assert result[1]['title'] == 'Meeting B'

    def test_maps_event_fields_correctly(self):
        """Each event dict must have title, start, end, location, all_day keys."""
        raw_event = {
            'summary': 'Doctor Appointment',
            'start': '2026-03-15T11:00:00+08:00',
            'end': '2026-03-15T12:00:00+08:00',
            'location': 'Clinic A',
            'all_day': False,
        }
        gcal_mock = MagicMock()
        gcal_mock.get_events.return_value = [raw_event]

        with patch.dict(sys.modules, {'gcal_today': gcal_mock}):
            result = schedule_data.get_calendar()

        assert len(result) == 1
        ev = result[0]
        assert ev['title'] == 'Doctor Appointment'
        assert ev['start'] == '2026-03-15T11:00:00+08:00'
        assert ev['end'] == '2026-03-15T12:00:00+08:00'
        assert ev['location'] == 'Clinic A'
        assert ev['all_day'] is False

    def test_uses_question_mark_for_missing_summary(self):
        """Events without a summary field should have title='?'."""
        raw_event = {
            'start': '2026-03-15T10:00:00+08:00',
            'end': '2026-03-15T11:00:00+08:00',
        }
        gcal_mock = MagicMock()
        gcal_mock.get_events.return_value = [raw_event]

        with patch.dict(sys.modules, {'gcal_today': gcal_mock}):
            result = schedule_data.get_calendar()

        assert result[0]['title'] == '?'

    def test_returns_error_on_exception(self):
        """When get_events raises, get_calendar returns a single error dict."""
        gcal_mock = MagicMock()
        gcal_mock.get_events.side_effect = RuntimeError("Google API down")

        with patch.dict(sys.modules, {'gcal_today': gcal_mock}):
            result = schedule_data.get_calendar()

        assert len(result) == 1
        assert 'error' in result[0]
        assert 'Google API down' in result[0]['error']

    def test_passes_days_range_to_get_events(self):
        """get_calendar(days_range=3) must call get_events with days_ahead=0, days_range=3."""
        gcal_mock = MagicMock()
        gcal_mock.get_events.return_value = []

        with patch.dict(sys.modules, {'gcal_today': gcal_mock}):
            schedule_data.get_calendar(days_range=3)

        gcal_mock.get_events.assert_called_once_with(days_ahead=0, days_range=3)

    def test_default_days_range_is_one(self):
        """Default call passes days_range=1 to get_events."""
        gcal_mock = MagicMock()
        gcal_mock.get_events.return_value = []

        with patch.dict(sys.modules, {'gcal_today': gcal_mock}):
            schedule_data.get_calendar()

        gcal_mock.get_events.assert_called_once_with(days_ahead=0, days_range=1)


# ===========================================================================
# TestGetTodoist
# ===========================================================================

class TestGetTodoist:
    """Tests for schedule_data.get_todoist()."""

    _TOKEN_LINE = "TODOIST_API_TOKEN=test-secret-token\n"

    def test_due_today_tasks(self):
        """Tasks with due.date == '2026-03-15' must appear in due_today."""
        urlopen_mock = _make_urlopen_mock(_SAMPLE_TODOIST_RESPONSE)

        with (
            patch.object(Path, 'read_text', return_value=self._TOKEN_LINE),
            patch('urllib.request.urlopen', return_value=urlopen_mock),
        ):
            result = schedule_data.get_todoist()

        assert 'error' not in result
        assert any(t['content'] == 'Task due today P2' for t in result['due_today'])

    def test_overdue_tasks(self):
        """Tasks with due.date < today must appear in overdue."""
        urlopen_mock = _make_urlopen_mock(_SAMPLE_TODOIST_RESPONSE)

        with (
            patch.object(Path, 'read_text', return_value=self._TOKEN_LINE),
            patch('urllib.request.urlopen', return_value=urlopen_mock),
        ):
            result = schedule_data.get_todoist()

        assert 'error' not in result
        assert any(t['content'] == 'Overdue task P1' for t in result['overdue'])

    def test_high_priority_no_due(self):
        """Tasks with priority >= 3 and no due date must appear in high_priority."""
        urlopen_mock = _make_urlopen_mock(_SAMPLE_TODOIST_RESPONSE)

        with (
            patch.object(Path, 'read_text', return_value=self._TOKEN_LINE),
            patch('urllib.request.urlopen', return_value=urlopen_mock),
        ):
            result = schedule_data.get_todoist()

        assert 'error' not in result
        assert any(t['content'] == 'High priority no due' for t in result['high_priority'])

    def test_low_priority_no_due_not_in_high_priority(self):
        """Tasks with priority < 3 and no due date must NOT appear in high_priority."""
        urlopen_mock = _make_urlopen_mock(_SAMPLE_TODOIST_RESPONSE)

        with (
            patch.object(Path, 'read_text', return_value=self._TOKEN_LINE),
            patch('urllib.request.urlopen', return_value=urlopen_mock),
        ):
            result = schedule_data.get_todoist()

        high_contents = [t['content'] for t in result['high_priority']]
        assert 'Low prio no due' not in high_contents

    def test_no_token_returns_error(self):
        """When todoist.env has no TODOIST_API_TOKEN line, result must have error key."""
        with patch.object(Path, 'read_text', return_value="# no token here\n"):
            result = schedule_data.get_todoist()

        assert 'error' in result
        assert result['error'] == 'no token'

    def test_api_error_returns_error(self):
        """When urlopen raises, get_todoist returns {'error': <message>}."""
        import urllib.request as _ur

        with (
            patch.object(Path, 'read_text', return_value=self._TOKEN_LINE),
            patch('urllib.request.urlopen', side_effect=OSError("connection refused")),
        ):
            result = schedule_data.get_todoist()

        assert 'error' in result
        assert 'connection refused' in result['error']

    def test_sorted_by_priority_desc(self):
        """due_today, overdue, and high_priority lists must be sorted by -priority."""
        payload = {
            'results': [
                # due today, mixed priorities
                {'id': '10', 'content': 'Today P4', 'priority': 4, 'due': {'date': '2026-03-15'}},
                {'id': '11', 'content': 'Today P1', 'priority': 1, 'due': {'date': '2026-03-15'}},
                {'id': '12', 'content': 'Today P3', 'priority': 3, 'due': {'date': '2026-03-15'}},
            ]
        }
        urlopen_mock = _make_urlopen_mock(payload)

        with (
            patch.object(Path, 'read_text', return_value=self._TOKEN_LINE),
            patch('urllib.request.urlopen', return_value=urlopen_mock),
        ):
            result = schedule_data.get_todoist()

        priorities = [t['priority'] for t in result['due_today']]
        assert priorities == sorted(priorities, reverse=True), (
            "due_today must be sorted by priority descending"
        )

    def test_total_tasks_count(self):
        """total_tasks reflects the full length of the API results list."""
        urlopen_mock = _make_urlopen_mock(_SAMPLE_TODOIST_RESPONSE)

        with (
            patch.object(Path, 'read_text', return_value=self._TOKEN_LINE),
            patch('urllib.request.urlopen', return_value=urlopen_mock),
        ):
            result = schedule_data.get_todoist()

        assert result['total_tasks'] == len(_SAMPLE_TODOIST_RESPONSE['results'])

    def test_handles_flat_api_response(self):
        """Todoist API returning a plain list (not wrapped in 'results') is handled."""
        payload = [
            {'id': '20', 'content': 'Flat task', 'priority': 2, 'due': {'date': '2026-03-15'}},
        ]
        urlopen_mock = _make_urlopen_mock(payload)

        with (
            patch.object(Path, 'read_text', return_value=self._TOKEN_LINE),
            patch('urllib.request.urlopen', return_value=urlopen_mock),
        ):
            result = schedule_data.get_todoist()

        assert 'error' not in result
        assert result['total_tasks'] == 1


# ===========================================================================
# TestGetMemoryContext
# ===========================================================================

class TestGetMemoryContext:
    """Tests for schedule_data.get_memory_context()."""

    # With _NOW = 2026-03-15, today='2026-03-15', yesterday='2026-03-14'
    _TODAY_MD = "# 2026-03-15\nFeel good today."
    _YESTERDAY_MD = "# 2026-03-14\nSlept well."
    _TODAY_TAG = json.dumps({'metrics': {'sleep': 7, 'mood': 8}})
    _YESTERDAY_TAG = json.dumps({'metrics': {'sleep': 6, 'mood': 7}})

    def test_reads_today_file(self):
        """When today's .md file exists it should appear in context['today']."""
        def fake_exists(self_path):
            name = self_path.name
            return name in ('2026-03-15.md',)

        def fake_read_text(self_path, *a, **kw):
            return self.__class__._TODAY_MD

        with (
            patch.object(Path, 'exists', fake_exists),
            patch.object(Path, 'read_text', fake_read_text),
        ):
            ctx = schedule_data.get_memory_context()

        assert 'today' in ctx
        assert ctx['today']['date'] == '2026-03-15'
        assert 'Feel good' in ctx['today']['preview']

    def test_reads_yesterday_file(self):
        """When yesterday's .md file exists it should appear in context['yesterday']."""
        def fake_exists(self_path):
            return self_path.name == '2026-03-14.md'

        def fake_read_text(self_path, *a, **kw):
            return self.__class__._YESTERDAY_MD

        with (
            patch.object(Path, 'exists', fake_exists),
            patch.object(Path, 'read_text', fake_read_text),
        ):
            ctx = schedule_data.get_memory_context()

        assert 'yesterday' in ctx
        assert ctx['yesterday']['date'] == '2026-03-14'

    def test_reads_tag_files(self):
        """When tag JSON files exist, metrics_today and metrics_yesterday are populated."""
        def fake_exists(self_path):
            return self_path.suffix == '.json'

        def fake_read_text(self_path, *a, **kw):
            if '2026-03-15' in self_path.name:
                return self.__class__._TODAY_TAG
            return self.__class__._YESTERDAY_TAG

        with (
            patch.object(Path, 'exists', fake_exists),
            patch.object(Path, 'read_text', fake_read_text),
        ):
            ctx = schedule_data.get_memory_context()

        assert 'metrics_today' in ctx
        assert ctx['metrics_today']['sleep'] == 7
        assert 'metrics_yesterday' in ctx
        assert ctx['metrics_yesterday']['mood'] == 7

    def test_handles_missing_files(self):
        """When no memory files exist, context dict should be empty (no crash)."""
        with patch.object(Path, 'exists', return_value=False):
            ctx = schedule_data.get_memory_context()

        assert ctx == {}

    def test_handles_malformed_json_tags(self):
        """JSONDecodeError in a tag file must not crash; that key is simply absent."""
        def fake_exists(self_path):
            return self_path.suffix == '.json'

        def fake_read_text(self_path, *a, **kw):
            return "{ not valid json !!!"

        with (
            patch.object(Path, 'exists', fake_exists),
            patch.object(Path, 'read_text', fake_read_text),
        ):
            ctx = schedule_data.get_memory_context()

        # Should not raise; metric keys simply absent
        assert 'metrics_today' not in ctx
        assert 'metrics_yesterday' not in ctx

    def test_truncates_md_preview_at_2000_chars(self):
        """Preview content is truncated to the first 2000 characters."""
        long_text = 'x' * 5000

        def fake_exists(self_path):
            return self_path.name == '2026-03-15.md'

        def fake_read_text(self_path, *a, **kw):
            return long_text

        with (
            patch.object(Path, 'exists', fake_exists),
            patch.object(Path, 'read_text', fake_read_text),
        ):
            ctx = schedule_data.get_memory_context()

        assert len(ctx['today']['preview']) == 2000


# ===========================================================================
# TestGetTimeInfo
# ===========================================================================

class TestGetTimeInfo:
    """Tests for schedule_data.get_time_info().

    Because NOW is captured at module import time we use patch.object to
    override schedule_data.NOW for each test.
    """

    def _make_now(self, hour: int, minute: int = 0) -> datetime:
        return datetime(2026, 3, 15, hour, minute, tzinfo=_TZ)

    def test_morning_phase(self):
        """Hour < 12 → phase == 'morning'."""
        with patch.object(schedule_data, 'NOW', self._make_now(10, 0)):
            info = schedule_data.get_time_info()
        assert info['phase'] == 'morning'

    def test_afternoon_phase(self):
        """12 <= hour < 17 → phase == 'afternoon'."""
        with patch.object(schedule_data, 'NOW', self._make_now(14, 0)):
            info = schedule_data.get_time_info()
        assert info['phase'] == 'afternoon'

    def test_evening_phase(self):
        """17 <= hour < 21 → phase == 'evening'."""
        with patch.object(schedule_data, 'NOW', self._make_now(19, 0)):
            info = schedule_data.get_time_info()
        assert info['phase'] == 'evening'

    def test_night_phase(self):
        """hour >= 21 → phase == 'night'."""
        with patch.object(schedule_data, 'NOW', self._make_now(22, 0)):
            info = schedule_data.get_time_info()
        assert info['phase'] == 'night'

    def test_remaining_hours_at_14_30(self):
        """At 14:30 with bedtime 23:00, remaining == 8.5 hours."""
        with patch.object(schedule_data, 'NOW', self._make_now(14, 30)):
            info = schedule_data.get_time_info()
        assert info['remaining_hours'] == 8.5

    def test_remaining_hours_is_zero_after_bedtime(self):
        """After 23:00 remaining_hours clamps to 0."""
        with patch.object(schedule_data, 'NOW', self._make_now(23, 30)):
            info = schedule_data.get_time_info()
        assert info['remaining_hours'] == 0.0

    def test_now_field_format(self):
        """'now' field must be HH:MM formatted."""
        with patch.object(schedule_data, 'NOW', self._make_now(9, 5)):
            info = schedule_data.get_time_info()
        assert info['now'] == '09:05'

    def test_date_field_includes_weekday(self):
        """'date' field includes the weekday name in parentheses."""
        with patch.object(schedule_data, 'NOW', self._make_now(10, 0)):
            info = schedule_data.get_time_info()
        # 2026-03-15 is a Sunday
        assert '2026-03-15' in info['date']
        assert '(' in info['date'] and ')' in info['date']

    def test_hour_float_correct(self):
        """hour_float at 14:30 == 14.5."""
        with patch.object(schedule_data, 'NOW', self._make_now(14, 30)):
            info = schedule_data.get_time_info()
        assert info['hour_float'] == 14.5

    def test_bedtime_target_field(self):
        """bedtime_target is always '23:00'."""
        with patch.object(schedule_data, 'NOW', self._make_now(10, 0)):
            info = schedule_data.get_time_info()
        assert info['bedtime_target'] == '23:00'


# ===========================================================================
# TestGetMedicationSchedule
# ===========================================================================

class TestGetMedicationSchedule:
    """Tests for schedule_data.get_medication_schedule()."""

    def test_after_prescription_end_returns_none(self):
        """With NOW = 2026-03-15 (after 2026-02-25), returns None."""
        # The module-level _NOW is already 2026-03-15, which is > prescription_end
        with patch.object(schedule_data, 'NOW', _NOW):
            result = schedule_data.get_medication_schedule()
        assert result is None

    def test_during_prescription_returns_upcoming_slots(self):
        """With NOW inside prescription period, returns dict with upcoming_today slots."""
        in_period = datetime(2026, 2, 24, 10, 0, tzinfo=_TZ)  # before prescription_end
        with patch.object(schedule_data, 'NOW', in_period):
            result = schedule_data.get_medication_schedule()

        assert result is not None
        assert 'upcoming_today' in result
        assert 'prescription_end' in result
        assert result['prescription_end'] == '2026-02-25'

    def test_during_prescription_slots_are_future_only(self):
        """At 10:00, only slots with hour > 10 are returned as upcoming."""
        # At 10:00 on 2026-02-24, slots at 09:00 should be excluded
        in_period = datetime(2026, 2, 24, 10, 0, tzinfo=_TZ)
        with patch.object(schedule_data, 'NOW', in_period):
            result = schedule_data.get_medication_schedule()

        upcoming_times = [s['time'] for s in result['upcoming_today']]
        assert '09:00' not in upcoming_times
        assert '13:00' in upcoming_times
        assert '17:00' in upcoming_times
        assert '21:00' in upcoming_times

    def test_late_night_no_upcoming_slots(self):
        """At 22:00, the 21:00 slot has passed; upcoming_today is empty."""
        in_period = datetime(2026, 2, 24, 22, 0, tzinfo=_TZ)
        with patch.object(schedule_data, 'NOW', in_period):
            result = schedule_data.get_medication_schedule()

        assert result is not None
        assert result['upcoming_today'] == []


# ===========================================================================
# TestFormatDisplay
# ===========================================================================

class TestFormatDisplay:
    """Tests for schedule_data.format_display()."""

    def _make_data(self, now_str='14:30', calendar=None, todoist=None, medication=None):
        """Build a minimal data dict for format_display."""
        return {
            'time': {
                'now': now_str,
                'date': '2026-03-15 (Sunday)',
                'remaining_hours': 8.5,
                'bedtime_target': '23:00',
                'phase': 'afternoon',
                'hour_float': 14.5,
            },
            'calendar': calendar or [],
            'todoist': todoist or {},
            'medication': medication,
        }

    def test_prints_date_and_time(self, capsys):
        """Output header must contain the date string and current time."""
        data = self._make_data()
        schedule_data.format_display(data)
        captured = capsys.readouterr()
        assert '2026-03-15' in captured.out
        assert '14:30' in captured.out

    def test_prints_remaining_hours(self, capsys):
        """Output must mention remaining hours."""
        data = self._make_data()
        schedule_data.format_display(data)
        captured = capsys.readouterr()
        assert '8.5' in captured.out

    def test_prints_timeline_section(self, capsys):
        """Timeline section header must appear in output."""
        data = self._make_data()
        schedule_data.format_display(data)
        captured = capsys.readouterr()
        assert '時間軸' in captured.out

    def test_now_marker_inserted_before_future_event(self, capsys):
        """The NOW marker (▶) appears before events that start after now."""
        future_event = {
            'title': 'Evening Meeting',
            'start': '2026-03-15T18:00:00+08:00',
            'end': '2026-03-15T19:00:00+08:00',
            'location': '',
            'all_day': False,
        }
        data = self._make_data(calendar=[future_event])
        schedule_data.format_display(data)
        captured = capsys.readouterr()
        # ▶ marker should appear
        assert '▶' in captured.out
        # Marker must appear before the event title in output
        marker_pos = captured.out.index('▶')
        title_pos = captured.out.index('Evening Meeting')
        assert marker_pos < title_pos

    def test_past_event_marked_done(self, capsys):
        """Events that ended before now get the done icon (✅)."""
        past_event = {
            'title': 'Morning Standup',
            'start': '2026-03-15T09:00:00+08:00',
            'end': '2026-03-15T10:00:00+08:00',
            'location': '',
            'all_day': False,
        }
        data = self._make_data(calendar=[past_event])
        schedule_data.format_display(data)
        captured = capsys.readouterr()
        assert '✅' in captured.out

    def test_ongoing_event_marked_in_progress(self, capsys):
        """Event spanning now (14:30) gets the in-progress icon (🔵)."""
        ongoing_event = {
            'title': 'Ongoing Workshop',
            'start': '2026-03-15T13:00:00+08:00',
            'end': '2026-03-15T16:00:00+08:00',
            'location': '',
            'all_day': False,
        }
        data = self._make_data(calendar=[ongoing_event])
        schedule_data.format_display(data)
        captured = capsys.readouterr()
        assert '🔵' in captured.out

    def test_todoist_section_appears(self, capsys):
        """When there are tasks, the todoist section is printed."""
        todoist = {
            'due_today': [{'content': 'Buy groceries', 'priority': 2, 'due': '2026-03-15', 'id': '1'}],
            'overdue': [],
            'high_priority': [],
            'total_tasks': 1,
        }
        data = self._make_data(todoist=todoist)
        schedule_data.format_display(data)
        captured = capsys.readouterr()
        assert '待辦' in captured.out
        assert 'Buy groceries' in captured.out

    def test_medication_section_appears(self, capsys):
        """When medication has upcoming_today, medication section is printed."""
        meds = {
            'upcoming_today': [
                {'time': '21:00', 'drugs': ['ALLEGRA 1粒']},
            ],
            'prescription_end': '2026-02-25',
        }
        data = self._make_data(medication=meds)
        schedule_data.format_display(data)
        captured = capsys.readouterr()
        assert '吃藥提醒' in captured.out
        assert '21:00' in captured.out
        assert 'ALLEGRA 1粒' in captured.out

    def test_no_medication_section_when_none(self, capsys):
        """When medication is None, no medication section is printed."""
        data = self._make_data(medication=None)
        schedule_data.format_display(data)
        captured = capsys.readouterr()
        assert '吃藥提醒' not in captured.out

    def test_error_calendar_event_skipped(self, capsys):
        """Calendar events with 'error' key are silently skipped in the timeline."""
        data = self._make_data(calendar=[{'error': 'API failure'}])
        schedule_data.format_display(data)
        captured = capsys.readouterr()
        # No crash; the error dict should not show as a regular event
        assert 'API failure' not in captured.out

    def test_empty_calendar_shows_end_of_day_marker(self, capsys):
        """With no calendar events, the NOW marker with end-of-day message appears."""
        data = self._make_data(calendar=[])
        schedule_data.format_display(data)
        captured = capsys.readouterr()
        assert '▶' in captured.out
        assert '今日行程已結束' in captured.out
