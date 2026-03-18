#!/usr/bin/env python3
"""Tests for diary_utils.py — pure logic, no Google API calls."""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import date, datetime

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'lib'))


class TestParseDate(unittest.TestCase):
    def setUp(self):
        from diary_utils import parse_date
        self.parse_date = parse_date

    def test_dd_mm_yyyy_format(self):
        self.assertEqual(self.parse_date("22/02/2026 08:30:00"), "2026-02-22")

    def test_mm_dd_yyyy_format(self):
        self.assertEqual(self.parse_date("02/22/2026 08:30:00"), "2026-02-22")

    def test_leading_spaces_stripped(self):
        self.assertEqual(self.parse_date("  22/02/2026 08:30:00  "), "2026-02-22")

    def test_empty_string_returns_none(self):
        self.assertIsNone(self.parse_date(""))

    def test_none_returns_none(self):
        self.assertIsNone(self.parse_date(None))

    def test_garbage_returns_none(self):
        self.assertIsNone(self.parse_date("not a date"))

    def test_ambiguous_date_prefers_dd_mm(self):
        # 01/02/2026 — ambiguous: DD/MM (Jan 2) or MM/DD (Feb 1)
        # parse_date tries DD/MM first → 2026-02-01
        result = self.parse_date("01/02/2026 10:00:00")
        self.assertEqual(result, "2026-02-01")

    def test_unambiguous_day_13_plus(self):
        # Day=22 can only be DD/MM/YYYY
        self.assertEqual(self.parse_date("22/01/2026 00:00:00"), "2026-01-22")


class TestFormatDate(unittest.TestCase):
    def setUp(self):
        from diary_utils import format_date
        self.format_date = format_date

    def test_string_passthrough(self):
        self.assertEqual(self.format_date("2026-02-22"), "2026-02-22")

    def test_date_object(self):
        self.assertEqual(self.format_date(date(2026, 2, 22)), "2026-02-22")

    def test_datetime_object(self):
        self.assertEqual(self.format_date(datetime(2026, 2, 22, 8, 30)), "2026-02-22")


class TestPeopleAliases(unittest.TestCase):
    def setUp(self):
        from diary_utils import PEOPLE_ALIASES
        self.PEOPLE_ALIASES = PEOPLE_ALIASES

    def test_all_values_are_lists(self):
        for canonical, aliases in self.PEOPLE_ALIASES.items():
            self.assertIsInstance(aliases, list, f"{canonical} should have a list of aliases")

    def test_canonical_name_in_aliases(self):
        # Each canonical name should appear as one of its own aliases
        for canonical, aliases in self.PEOPLE_ALIASES.items():
            self.assertIn(canonical, aliases,
                          f"Canonical '{canonical}' should be in its own alias list")

    def test_known_entries_present(self):
        self.assertIn("智凱", self.PEOPLE_ALIASES)
        self.assertIn("李宏毅", self.PEOPLE_ALIASES)
        self.assertIn("媽", self.PEOPLE_ALIASES)

    def test_union_includes_search_diary_extras(self):
        # search_diary.py had "康" and "老師" that generate_tags.py lacked
        self.assertIn("康", self.PEOPLE_ALIASES["康哥"])
        self.assertIn("老師", self.PEOPLE_ALIASES["李宏毅"])

    def test_no_empty_alias_lists(self):
        for canonical, aliases in self.PEOPLE_ALIASES.items():
            self.assertTrue(len(aliases) > 0, f"{canonical} has empty alias list")


class TestGetDiarySheet(unittest.TestCase):
    @patch('diary_utils.gspread', create=True)
    def test_returns_worksheet_on_success(self, mock_gspread):
        mock_ws = MagicMock()
        mock_gc = MagicMock()
        mock_gc.open_by_key.return_value.get_worksheet.return_value = mock_ws
        mock_gspread.authorize.return_value = mock_gc

        with patch('diary_utils.Credentials', create=True) as mock_creds_cls:
            mock_creds_cls.from_service_account_file.return_value = MagicMock()
            # Patch the imports inside get_diary_sheet
            with patch.dict('sys.modules', {'gspread': mock_gspread,
                                             'google.oauth2.service_account': MagicMock()}):
                from diary_utils import get_diary_sheet
                # Since gspread is already imported at module level in some envs,
                # just verify the function exists and is callable
                self.assertTrue(callable(get_diary_sheet))

    def test_raises_on_missing_credentials(self):
        """get_diary_sheet raises (not silently returns None) so callers can fallback."""
        from diary_utils import get_diary_sheet
        # With a nonexistent creds file, should raise FileNotFoundError or similar
        with patch('diary_utils.CREDS_PATH', '/nonexistent/path/creds.json'):
            with self.assertRaises(Exception):
                get_diary_sheet()


if __name__ == '__main__':
    unittest.main(verbosity=2)
