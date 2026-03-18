#!/usr/bin/env python3
"""
Unit tests for skills/lib/common.py

Covers:
- TZ constant — correct UTC+8 offset and name
- now() — returns datetime in Asia/Taipei timezone
- today_str() — YYYY-MM-DD format in Taipei time
- yesterday_str() — one day before today_str()
- remaining_hours() — countdown arithmetic, floor at 0
- is_quiet_hours() — boundary behaviour at 23:00 and 08:00
- load_todoist_token() — env-var path, file path, missing-token error
- Config constants — CAL_ID, SHEET_ID, DISCORD_BOT_IDS, DISCORD_BOT_SYNC_CHANNEL

Usage:
    python3 -m pytest skills/lib/test_common.py -v
    python3 skills/lib/test_common.py
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Make common importable regardless of cwd
# (Force-load from this directory to avoid stale sys.modules stubs.)
# ---------------------------------------------------------------------------
LIB_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB_DIR))

import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("common", LIB_DIR / "common.py")
common = importlib.util.module_from_spec(_spec)
sys.modules["common"] = common
_spec.loader.exec_module(common)
from common import (  # noqa: E402
    TZ, now, today_str, yesterday_str,
    remaining_hours, is_quiet_hours,
    load_todoist_token,
    CAL_ID, SHEET_ID, DISCORD_BOT_IDS, DISCORD_BOT_SYNC_CHANNEL,
    WORKSPACE, MEMORY, TAGS_DIR, SECRETS, SCRIPTS,
)

# Convenience: UTC+8 as a timezone object
TAIPEI_UTC8 = timezone(timedelta(hours=8))


# ---------------------------------------------------------------------------
# Tests: TZ constant
# ---------------------------------------------------------------------------

class TestTZConstant(unittest.TestCase):

    def test_tz_is_timezone_instance(self):
        self.assertIsInstance(TZ, timezone)

    def test_tz_offset_is_utc_plus_8(self):
        # Create a probe datetime and check its UTC offset
        probe = datetime(2024, 1, 1, tzinfo=TZ)
        self.assertEqual(probe.utcoffset(), timedelta(hours=8))

    def test_tz_name_contains_taipei(self):
        # The name should reference Asia/Taipei
        self.assertIn("Taipei", str(TZ))


# ---------------------------------------------------------------------------
# Tests: now()
# ---------------------------------------------------------------------------

class TestNow(unittest.TestCase):

    def test_now_returns_datetime(self):
        result = now()
        self.assertIsInstance(result, datetime)

    def test_now_is_timezone_aware(self):
        result = now()
        self.assertIsNotNone(result.tzinfo)

    def test_now_utc_offset_is_8_hours(self):
        result = now()
        self.assertEqual(result.utcoffset(), timedelta(hours=8))

    def test_now_is_recent(self):
        # Should be within 5 seconds of the real wall clock in UTC+8
        result = now()
        real_taipei = datetime.now(TAIPEI_UTC8)
        delta = abs((result - real_taipei).total_seconds())
        self.assertLess(delta, 5.0, "now() is more than 5 seconds off")

    def test_now_returns_fresh_value_on_each_call(self):
        t1 = now()
        t2 = now()
        # t2 must be >= t1 (time moves forward)
        self.assertGreaterEqual(t2, t1)


# ---------------------------------------------------------------------------
# Tests: today_str()
# ---------------------------------------------------------------------------

class TestTodayStr(unittest.TestCase):

    def test_today_str_format_yyyy_mm_dd(self):
        result = today_str()
        # Must match YYYY-MM-DD exactly
        parts = result.split("-")
        self.assertEqual(len(parts), 3,
                         f"today_str() '{result}' is not YYYY-MM-DD")
        year, month, day = parts
        self.assertEqual(len(year), 4)
        self.assertEqual(len(month), 2)
        self.assertEqual(len(day), 2)

    def test_today_str_is_parseable_date(self):
        from datetime import date
        result = today_str()
        # Should not raise
        parsed = date.fromisoformat(result)
        self.assertIsNotNone(parsed)

    def test_today_str_matches_now(self):
        expected = now().strftime("%Y-%m-%d")
        self.assertEqual(today_str(), expected)

    def test_today_str_frozen_clock(self):
        """Patch datetime.now so today_str is deterministic."""
        fake_dt = datetime(2025, 6, 15, 14, 30, 0, tzinfo=TZ)
        with patch.object(common, "now", return_value=fake_dt):
            self.assertEqual(today_str(), "2025-06-15")


# ---------------------------------------------------------------------------
# Tests: yesterday_str()
# ---------------------------------------------------------------------------

class TestYesterdayStr(unittest.TestCase):

    def test_yesterday_str_format(self):
        result = yesterday_str()
        from datetime import date
        parsed = date.fromisoformat(result)
        self.assertIsNotNone(parsed)

    def test_yesterday_is_one_day_before_today(self):
        from datetime import date
        today = date.fromisoformat(today_str())
        yest = date.fromisoformat(yesterday_str())
        self.assertEqual((today - yest).days, 1)

    def test_yesterday_str_frozen_clock(self):
        fake_dt = datetime(2025, 1, 1, 10, 0, 0, tzinfo=TZ)
        with patch.object(common, "now", return_value=fake_dt):
            self.assertEqual(yesterday_str(), "2024-12-31")


# ---------------------------------------------------------------------------
# Tests: remaining_hours()
# ---------------------------------------------------------------------------

class TestRemainingHours(unittest.TestCase):

    def _frozen(self, hour: int, minute: int = 0):
        return datetime(2025, 3, 10, hour, minute, tzinfo=TZ)

    def test_remaining_hours_early_afternoon(self):
        with patch.object(common, "now", return_value=self._frozen(14, 0)):
            result = remaining_hours(23.0)
        self.assertAlmostEqual(result, 9.0, places=1)

    def test_remaining_hours_at_target_is_zero(self):
        with patch.object(common, "now", return_value=self._frozen(23, 0)):
            result = remaining_hours(23.0)
        self.assertAlmostEqual(result, 0.0, places=1)

    def test_remaining_hours_past_target_is_zero(self):
        with patch.object(common, "now", return_value=self._frozen(23, 30)):
            result = remaining_hours(23.0)
        self.assertEqual(result, 0.0)

    def test_remaining_hours_custom_target(self):
        with patch.object(common, "now", return_value=self._frozen(10, 0)):
            result = remaining_hours(12.0)
        self.assertAlmostEqual(result, 2.0, places=1)

    def test_remaining_hours_with_minutes(self):
        # 14:30 → 8.5h until 23:00
        with patch.object(common, "now", return_value=self._frozen(14, 30)):
            result = remaining_hours(23.0)
        self.assertAlmostEqual(result, 8.5, places=1)

    def test_remaining_hours_returns_float(self):
        result = remaining_hours()
        self.assertIsInstance(result, float)

    def test_remaining_hours_never_negative(self):
        # Midnight (hour=0) with target 23 — already past
        with patch.object(common, "now", return_value=self._frozen(23, 59)):
            result = remaining_hours(23.0)
        self.assertGreaterEqual(result, 0.0)


# ---------------------------------------------------------------------------
# Tests: is_quiet_hours()
# ---------------------------------------------------------------------------

class TestIsQuietHours(unittest.TestCase):

    def _frozen(self, hour: int):
        return datetime(2025, 3, 10, hour, 0, tzinfo=TZ)

    def test_quiet_at_23(self):
        with patch.object(common, "now", return_value=self._frozen(23)):
            self.assertTrue(is_quiet_hours())

    def test_quiet_at_midnight(self):
        with patch.object(common, "now", return_value=self._frozen(0)):
            self.assertTrue(is_quiet_hours())

    def test_quiet_at_3am(self):
        with patch.object(common, "now", return_value=self._frozen(3)):
            self.assertTrue(is_quiet_hours())

    def test_quiet_at_7am(self):
        with patch.object(common, "now", return_value=self._frozen(7)):
            self.assertTrue(is_quiet_hours())

    def test_not_quiet_at_8am(self):
        with patch.object(common, "now", return_value=self._frozen(8)):
            self.assertFalse(is_quiet_hours())

    def test_not_quiet_at_noon(self):
        with patch.object(common, "now", return_value=self._frozen(12)):
            self.assertFalse(is_quiet_hours())

    def test_not_quiet_at_22(self):
        with patch.object(common, "now", return_value=self._frozen(22)):
            self.assertFalse(is_quiet_hours())

    def test_returns_bool(self):
        self.assertIsInstance(is_quiet_hours(), bool)


# ---------------------------------------------------------------------------
# Tests: load_todoist_token()
# ---------------------------------------------------------------------------

class TestLoadTodoistToken(unittest.TestCase):

    def setUp(self):
        # Clear env var before each test
        os.environ.pop("TODOIST_API_TOKEN", None)

    def tearDown(self):
        os.environ.pop("TODOIST_API_TOKEN", None)

    def test_returns_env_var_when_set(self):
        os.environ["TODOIST_API_TOKEN"] = "env_token_abc123"
        token = load_todoist_token()
        self.assertEqual(token, "env_token_abc123")

    def test_env_var_takes_priority_over_file(self):
        os.environ["TODOIST_API_TOKEN"] = "from_env"
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "todoist.env"
            env_file.write_text("TODOIST_API_TOKEN=from_file\n")
            with patch.object(common, "SECRETS", Path(tmp)):
                token = load_todoist_token()
        self.assertEqual(token, "from_env")

    def test_reads_token_from_env_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "todoist.env"
            env_file.write_text("TODOIST_API_TOKEN=file_token_xyz\n")
            with patch.object(common, "SECRETS", Path(tmp)):
                token = load_todoist_token()
        self.assertEqual(token, "file_token_xyz")

    def test_reads_token_with_surrounding_whitespace_in_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "todoist.env"
            env_file.write_text("TODOIST_API_TOKEN=  padded_token  \n")
            with patch.object(common, "SECRETS", Path(tmp)):
                token = load_todoist_token()
        self.assertEqual(token, "padded_token")

    def test_reads_token_from_file_with_other_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "todoist.env"
            env_file.write_text(
                "# comment\n"
                "OTHER_VAR=ignored\n"
                "TODOIST_API_TOKEN=secret_tok\n"
            )
            with patch.object(common, "SECRETS", Path(tmp)):
                token = load_todoist_token()
        self.assertEqual(token, "secret_tok")

    def test_raises_runtime_error_when_no_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Directory exists but todoist.env does not
            with patch.object(common, "SECRETS", Path(tmp)):
                with self.assertRaises(RuntimeError) as ctx:
                    load_todoist_token()
        self.assertIn("TODOIST_API_TOKEN", str(ctx.exception))

    def test_raises_when_file_exists_but_key_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "todoist.env"
            env_file.write_text("SOME_OTHER_TOKEN=abc\n")
            with patch.object(common, "SECRETS", Path(tmp)):
                with self.assertRaises(RuntimeError):
                    load_todoist_token()

    def test_raises_when_secrets_dir_does_not_exist(self):
        non_existent = Path("/tmp/__non_existent_dir_abc123__")
        with patch.object(common, "SECRETS", non_existent):
            with self.assertRaises(RuntimeError):
                load_todoist_token()


# ---------------------------------------------------------------------------
# Tests: Config constants
# ---------------------------------------------------------------------------

class TestConfigConstants(unittest.TestCase):

    def test_cal_id_is_str(self):
        self.assertIsInstance(CAL_ID, str)

    def test_cal_id_not_empty(self):
        self.assertTrue(len(CAL_ID) > 0)

    def test_sheet_id_is_str(self):
        self.assertIsInstance(SHEET_ID, str)

    def test_sheet_id_not_empty(self):
        self.assertTrue(len(SHEET_ID) > 0)

    def test_discord_bot_ids_is_dict(self):
        self.assertIsInstance(DISCORD_BOT_IDS, dict)

    def test_discord_bot_ids_has_lab_and_mac(self):
        self.assertIn("lab", DISCORD_BOT_IDS)
        self.assertIn("mac", DISCORD_BOT_IDS)

    def test_discord_bot_ids_values_are_strings(self):
        for key, val in DISCORD_BOT_IDS.items():
            self.assertIsInstance(val, str, f"DISCORD_BOT_IDS[{key!r}] is not a str")

    def test_discord_sync_channel_is_str(self):
        self.assertIsInstance(DISCORD_BOT_SYNC_CHANNEL, str)

    def test_discord_sync_channel_not_empty(self):
        self.assertTrue(len(DISCORD_BOT_SYNC_CHANNEL) > 0)


# ---------------------------------------------------------------------------
# Tests: Path constants
# ---------------------------------------------------------------------------

class TestPathConstants(unittest.TestCase):

    def test_workspace_is_path(self):
        self.assertIsInstance(WORKSPACE, Path)

    def test_memory_is_path(self):
        self.assertIsInstance(MEMORY, Path)

    def test_memory_is_under_workspace(self):
        self.assertTrue(str(MEMORY).startswith(str(WORKSPACE)))

    def test_tags_dir_is_path(self):
        self.assertIsInstance(TAGS_DIR, Path)

    def test_tags_dir_under_memory(self):
        self.assertTrue(str(TAGS_DIR).startswith(str(MEMORY)))

    def test_secrets_is_path(self):
        self.assertIsInstance(SECRETS, Path)

    def test_scripts_is_path(self):
        self.assertIsInstance(SCRIPTS, Path)

    def test_scripts_under_workspace(self):
        self.assertTrue(str(SCRIPTS).startswith(str(WORKSPACE)))


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in (
        TestTZConstant,
        TestNow,
        TestTodayStr,
        TestYesterdayStr,
        TestRemainingHours,
        TestIsQuietHours,
        TestLoadTodoistToken,
        TestConfigConstants,
        TestPathConstants,
    ):
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
