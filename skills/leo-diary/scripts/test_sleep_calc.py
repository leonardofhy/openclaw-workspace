#!/usr/bin/env python3
"""
Unit tests for skills/leo-diary/scripts/sleep_calc.py

sleep_calc.py imports read_diary at module level, which in turn tries to
reach Google Sheets and the local filesystem. This test module injects a
stub for read_diary *before* importing sleep_calc so no external calls are
made during the test run.

Covers:
- parse_hhmm()             — valid formats, edge cases, invalid inputs, None
- sleep_duration_minutes() — normal night sleep, after-midnight sleep,
                             cross-midnight, sanity-check boundaries
- format_duration()        — formatting and None handling
- analyze_sleep()          — logic layer tested via mocked load_diary

Usage:
    python3 -m pytest skills/leo-diary/scripts/test_sleep_calc.py -v
    python3 skills/leo-diary/scripts/test_sleep_calc.py
"""

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Stub out read_diary before sleep_calc can import it
# ---------------------------------------------------------------------------
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

# Create a lightweight fake module so the top-level import inside sleep_calc
# ("from read_diary import load_diary") succeeds without real I/O.
_fake_read_diary = types.ModuleType("read_diary")
_fake_read_diary.load_diary = lambda *a, **kw: []
sys.modules.setdefault("read_diary", _fake_read_diary)

# Now safe to import the module under test
import sleep_calc  # noqa: E402
from sleep_calc import (  # noqa: E402
    parse_hhmm,
    sleep_duration_minutes,
    format_duration,
    analyze_sleep,
)


# ---------------------------------------------------------------------------
# Tests: parse_hhmm()
# ---------------------------------------------------------------------------

class TestParseHhmm(unittest.TestCase):
    """parse_hhmm(val) → (hour, minute) or None."""

    # ---- valid integer inputs ----

    def test_midnight(self):
        self.assertEqual(parse_hhmm(0), (0, 0))

    def test_single_digit_minute(self):
        # 5 → 00:05
        self.assertEqual(parse_hhmm(5), (0, 5))

    def test_three_digit_time(self):
        # 305 → 03:05
        self.assertEqual(parse_hhmm(305), (3, 5))

    def test_four_digit_time(self):
        # 2334 → 23:34
        self.assertEqual(parse_hhmm(2334), (23, 34))

    def test_noon(self):
        self.assertEqual(parse_hhmm(1200), (12, 0))

    def test_late_night(self):
        self.assertEqual(parse_hhmm(2359), (23, 59))

    def test_early_morning(self):
        self.assertEqual(parse_hhmm(130), (1, 30))

    # ---- string inputs (the function strips and removes colons) ----

    def test_string_integer(self):
        self.assertEqual(parse_hhmm("730"), (7, 30))

    def test_string_with_colon(self):
        # "07:30" → stripped of colon → "0730" → 730 → (7, 30)
        self.assertEqual(parse_hhmm("07:30"), (7, 30))

    def test_string_with_leading_whitespace(self):
        self.assertEqual(parse_hhmm("  800"), (8, 0))

    def test_string_full_colon_format(self):
        self.assertEqual(parse_hhmm("23:59"), (23, 59))

    # ---- boundary values ----

    def test_hour_boundary_23(self):
        self.assertEqual(parse_hhmm(2300), (23, 0))

    def test_minute_boundary_59(self):
        self.assertEqual(parse_hhmm(59), (0, 59))

    def test_zero_zero(self):
        self.assertEqual(parse_hhmm("00:00"), (0, 0))

    # ---- invalid inputs → None ----

    def test_invalid_hour_24(self):
        self.assertIsNone(parse_hhmm(2400))

    def test_invalid_hour_99(self):
        self.assertIsNone(parse_hhmm(9900))

    def test_invalid_minute_60(self):
        self.assertIsNone(parse_hhmm(1260))

    def test_negative_value(self):
        self.assertIsNone(parse_hhmm(-1))

    def test_none_input(self):
        self.assertIsNone(parse_hhmm(None))

    def test_empty_string(self):
        self.assertIsNone(parse_hhmm(""))

    def test_non_numeric_string(self):
        self.assertIsNone(parse_hhmm("abc"))

    def test_float_string(self):
        # "7.5" is not a clean integer representation — should fail
        self.assertIsNone(parse_hhmm("7.5"))

    def test_list_input(self):
        self.assertIsNone(parse_hhmm([7, 30]))

    def test_dict_input(self):
        self.assertIsNone(parse_hhmm({"h": 7}))

    def test_returns_tuple(self):
        result = parse_hhmm(800)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)


# ---------------------------------------------------------------------------
# Tests: sleep_duration_minutes()
# ---------------------------------------------------------------------------

class TestSleepDurationMinutes(unittest.TestCase):
    """sleep_duration_minutes(sleep_in, wake_up) → int (minutes) or None."""

    # ---- after-midnight sleep (sleep_in hour <= 12) ----

    def test_after_midnight_simple(self):
        # Sleep 02:00, wake 10:00 → 8h = 480 min
        self.assertEqual(sleep_duration_minutes(200, 1000), 480)

    def test_after_midnight_short(self):
        # Sleep 01:00, wake 07:00 → 6h = 360 min
        self.assertEqual(sleep_duration_minutes(100, 700), 360)

    def test_after_midnight_with_minutes(self):
        # Sleep 02:30, wake 10:15 → 7h 45m = 465 min
        self.assertEqual(sleep_duration_minutes(230, 1015), 465)

    # ---- before-midnight sleep (sleep_in hour > 12) ----

    def test_before_midnight_simple(self):
        # Sleep 23:00, wake 07:00 → (60 min to midnight) + 420 = 480 min
        self.assertEqual(sleep_duration_minutes(2300, 700), 480)

    def test_before_midnight_early_evening(self):
        # Sleep 22:00, wake 06:30 → 2h to midnight + 6.5h = 510 min
        self.assertEqual(sleep_duration_minutes(2200, 630), 510)

    def test_before_midnight_with_minutes(self):
        # Sleep 23:30, wake 07:30 → 30min + 450min = 480 min
        self.assertEqual(sleep_duration_minutes(2330, 730), 480)

    # ---- sanity-check clamps ----

    def test_too_short_returns_none(self):
        # 30 minutes is below the 60-minute floor
        self.assertIsNone(sleep_duration_minutes(230, 300))

    def test_too_long_returns_none(self):
        # Sleep 01:00, wake 23:00 → 22h = 1320 min, above 16h cap
        self.assertIsNone(sleep_duration_minutes(100, 2300))

    def test_invalid_sleep_in_returns_none(self):
        self.assertIsNone(sleep_duration_minutes(None, 800))

    def test_invalid_wake_up_returns_none(self):
        self.assertIsNone(sleep_duration_minutes(100, None))

    def test_both_invalid_returns_none(self):
        self.assertIsNone(sleep_duration_minutes("abc", "xyz"))

    def test_returns_int_or_none(self):
        result = sleep_duration_minutes(100, 900)
        self.assertIsInstance(result, int)

    def test_minimum_valid_duration(self):
        # Exactly 60 minutes: sleep 08:00, wake 09:00
        self.assertEqual(sleep_duration_minutes(800, 900), 60)

    def test_maximum_valid_duration(self):
        # 16h exactly: sleep 02:00, wake 18:00
        self.assertEqual(sleep_duration_minutes(200, 1800), 960)


# ---------------------------------------------------------------------------
# Tests: format_duration()
# ---------------------------------------------------------------------------

class TestFormatDuration(unittest.TestCase):

    def test_none_returns_question_mark(self):
        self.assertEqual(format_duration(None), "?")

    def test_zero_minutes(self):
        self.assertEqual(format_duration(0), "0h 00m")

    def test_sixty_minutes(self):
        self.assertEqual(format_duration(60), "1h 00m")

    def test_ninety_minutes(self):
        self.assertEqual(format_duration(90), "1h 30m")

    def test_eight_hours(self):
        self.assertEqual(format_duration(480), "8h 00m")

    def test_seven_hours_45_minutes(self):
        self.assertEqual(format_duration(465), "7h 45m")

    def test_single_digit_minutes_padded(self):
        # 61 → "1h 01m" — minutes should be zero-padded to 2 digits
        self.assertEqual(format_duration(61), "1h 01m")

    def test_format_returns_string(self):
        self.assertIsInstance(format_duration(120), str)

    def test_large_duration(self):
        # 960 = 16h 00m
        self.assertEqual(format_duration(960), "16h 00m")


# ---------------------------------------------------------------------------
# Tests: analyze_sleep() — via mocked load_diary
# ---------------------------------------------------------------------------

class TestAnalyzeSleep(unittest.TestCase):
    """
    analyze_sleep() pulls data through load_diary. We mock it to return
    controlled diary entries so the aggregation logic is tested in isolation.
    """

    # ----- helpers -----

    @staticmethod
    def _entry(date, sleep_in, wake_up, quality="", mood="", energy=""):
        return {
            "date": date,
            "sleep_in": str(sleep_in),
            "wake_up": str(wake_up),
            "sleep_quality": str(quality),
            "mood": mood,
            "energy": energy,
            "diary": "",
            "completed": "",
        }

    def _run_with_entries(self, entries, days=7):
        with patch.object(sleep_calc, "load_diary", return_value=entries):
            return analyze_sleep(days)

    # ----- tests -----

    def test_empty_diary_returns_none(self):
        result = self._run_with_entries([])
        self.assertIsNone(result)

    def test_single_valid_entry_structure(self):
        entries = [self._entry("2025-03-01", 200, 1000)]
        result = self._run_with_entries(entries, days=7)
        self.assertIsNotNone(result)
        self.assertIn("entries", result)
        self.assertIn("avg_duration_min", result)

    def test_avg_duration_single_entry(self):
        # Sleep 02:00, wake 10:00 → 480 min
        entries = [self._entry("2025-03-01", 200, 1000)]
        result = self._run_with_entries(entries)
        self.assertAlmostEqual(result["avg_duration_min"], 480.0, places=0)

    def test_avg_duration_multiple_entries(self):
        # 480 min + 360 min = avg 420 min
        entries = [
            self._entry("2025-03-01", 200, 1000),  # 8h = 480
            self._entry("2025-03-02", 200, 800),   # 6h = 360
        ]
        result = self._run_with_entries(entries)
        self.assertAlmostEqual(result["avg_duration_min"], 420.0, places=0)

    def test_period_days_in_result(self):
        entries = [self._entry("2025-03-01", 200, 1000)]
        result = self._run_with_entries(entries, days=14)
        self.assertEqual(result["period_days"], 14)

    def test_late_sleep_detection(self):
        # Hours 2–7 are considered late sleep
        entries = [
            self._entry("2025-03-01", 300,  1100),  # late: 03:00
            self._entry("2025-03-02", 2300, 700),   # not late: 23:00
        ]
        result = self._run_with_entries(entries)
        self.assertEqual(result["late_sleep_days"], 1)

    def test_late_sleep_ratio(self):
        entries = [
            self._entry("2025-03-01", 300, 1100),  # late
            self._entry("2025-03-02", 300, 1100),  # late
            self._entry("2025-03-03", 2300, 700),  # not late
            self._entry("2025-03-04", 2300, 700),  # not late
        ]
        result = self._run_with_entries(entries)
        self.assertAlmostEqual(result["late_sleep_ratio"], 0.5, places=2)

    def test_duplicate_dates_deduplicated(self):
        # Two entries for the same date — only one should be kept
        entries = [
            self._entry("2025-03-01", 200, 1000),
            self._entry("2025-03-01", 300, 1100),  # duplicate date
        ]
        result = self._run_with_entries(entries)
        self.assertEqual(result["entries_analyzed"], 1)

    def test_entries_limited_to_days_param(self):
        entries = [
            self._entry(f"2025-02-{i:02d}", 200, 1000)
            for i in range(1, 11)  # 10 entries
        ]
        result = self._run_with_entries(entries, days=5)
        self.assertEqual(result["entries_analyzed"], 5)

    def test_sleep_quality_average(self):
        entries = [
            self._entry("2025-03-01", 200, 1000, quality="4"),
            self._entry("2025-03-02", 200, 1000, quality="2"),
        ]
        result = self._run_with_entries(entries)
        self.assertAlmostEqual(result["avg_quality"], 3.0, places=1)

    def test_invalid_quality_excluded_from_average(self):
        entries = [
            self._entry("2025-03-01", 200, 1000, quality="5"),
            self._entry("2025-03-02", 200, 1000, quality="bad"),
        ]
        result = self._run_with_entries(entries)
        self.assertEqual(result["quality_entries"], 1)
        self.assertAlmostEqual(result["avg_quality"], 5.0, places=1)

    def test_quality_none_when_no_valid_quality(self):
        entries = [self._entry("2025-03-01", 200, 1000, quality="")]
        result = self._run_with_entries(entries)
        self.assertIsNone(result["avg_quality"])

    def test_avg_duration_none_when_all_durations_invalid(self):
        # Provide times that fail sanity check (duration > 16h or unparseable)
        entries = [self._entry("2025-03-01", "abc", "xyz")]
        result = self._run_with_entries(entries)
        self.assertIsNone(result["avg_duration_min"])

    def test_result_contains_formatted_durations(self):
        entries = [self._entry("2025-03-01", 200, 1000)]
        result = self._run_with_entries(entries)
        self.assertIn("avg_duration_fmt", result)
        self.assertIn("min_duration_fmt", result)
        self.assertIn("max_duration_fmt", result)

    def test_entry_dict_keys(self):
        expected_keys = {
            "date", "sleep_in", "wake_up",
            "duration_min", "duration_fmt",
            "sleep_quality", "is_late",
            "mood", "energy",
        }
        entries = [self._entry("2025-03-01", 200, 1000, quality="3",
                               mood="good", energy="high")]
        result = self._run_with_entries(entries)
        entry = result["entries"][0]
        for k in expected_keys:
            self.assertIn(k, entry, f"Missing key '{k}' in entry dict")

    def test_entry_sleep_in_formatted_as_hh_mm(self):
        entries = [self._entry("2025-03-01", 200, 1000)]
        result = self._run_with_entries(entries)
        # parse_hhmm(200) → (2, 0) → should be formatted "02:00"
        self.assertEqual(result["entries"][0]["sleep_in"], "02:00")

    def test_entry_wake_up_formatted_as_hh_mm(self):
        entries = [self._entry("2025-03-01", 200, 1000)]
        result = self._run_with_entries(entries)
        self.assertEqual(result["entries"][0]["wake_up"], "10:00")

    def test_late_sleep_false_for_evening_bedtime(self):
        # 23:00 is before midnight → not "late" by the is_late definition
        entries = [self._entry("2025-03-01", 2300, 700)]
        result = self._run_with_entries(entries)
        self.assertFalse(result["entries"][0]["is_late"])

    def test_late_sleep_true_for_post_midnight(self):
        # 04:00 is after midnight in hours 2–7 range
        entries = [self._entry("2025-03-01", 400, 1200)]
        result = self._run_with_entries(entries)
        self.assertTrue(result["entries"][0]["is_late"])

    def test_entries_sorted_most_recent_first(self):
        entries = [
            self._entry("2025-03-01", 200, 1000),
            self._entry("2025-03-05", 200, 1000),
            self._entry("2025-03-03", 200, 1000),
        ]
        result = self._run_with_entries(entries)
        dates = [e["date"] for e in result["entries"]]
        self.assertEqual(dates, sorted(dates, reverse=True))


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in (
        TestParseHhmm,
        TestSleepDurationMinutes,
        TestFormatDuration,
        TestAnalyzeSleep,
    ):
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
