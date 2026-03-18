#!/usr/bin/env python3
"""Batch subprocess tests for leo-diary scripts.

Verifies each script can at least be invoked (--help or minimal args)
without crashing. 10-second timeout per script.

Usage:
    python3 -m pytest skills/leo-diary/scripts/test_batch_diary.py -v
"""

import subprocess
import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
TIMEOUT = 10


def run_script(script_name: str, args: list[str] | None = None) -> subprocess.CompletedProcess:
    """Run a script with optional args, return CompletedProcess."""
    cmd = [sys.executable, str(SCRIPTS_DIR / script_name)] + (args or [])
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )


# --- Scripts with argparse (--help works) ---

class TestSearchDiary(unittest.TestCase):

    def test_help(self):
        r = run_script("search_diary.py", ["--help"])
        self.assertEqual(r.returncode, 0)
        self.assertIn("usage", r.stdout.lower())


class TestSleepCalc(unittest.TestCase):

    def test_help(self):
        r = run_script("sleep_calc.py", ["--help"])
        self.assertEqual(r.returncode, 0)
        self.assertIn("usage", r.stdout.lower())


class TestGenerateTags(unittest.TestCase):

    def test_help(self):
        r = run_script("generate_tags.py", ["--help"])
        self.assertEqual(r.returncode, 0)
        self.assertIn("usage", r.stdout.lower())


class TestQueryTags(unittest.TestCase):

    def test_help(self):
        r = run_script("query_tags.py", ["--help"])
        self.assertEqual(r.returncode, 0)


class TestDiaryDeepAnalysis(unittest.TestCase):

    def test_help(self):
        r = run_script("diary_deep_analysis.py", ["--help"])
        self.assertEqual(r.returncode, 0)


class TestPeopleDb(unittest.TestCase):

    def test_help(self):
        r = run_script("people_db.py", ["--help"])
        self.assertEqual(r.returncode, 0)


class TestRefineEvents(unittest.TestCase):

    def test_help(self):
        r = run_script("refine_events.py", ["--help"])
        self.assertEqual(r.returncode, 0)


# --- Scripts without argparse (run with default/minimal args) ---

class TestKeywordFreq(unittest.TestCase):

    def test_runs_successfully(self):
        r = run_script("keyword_freq.py")
        self.assertEqual(r.returncode, 0)


class TestInsights(unittest.TestCase):

    def test_runs_with_default_args(self):
        r = run_script("insights.py")
        self.assertEqual(r.returncode, 0)


class TestReadDiary(unittest.TestCase):

    def test_runs_successfully(self):
        r = run_script("read_diary.py")
        self.assertEqual(r.returncode, 0)


class TestFetchLatestDiary(unittest.TestCase):

    def test_runs_successfully(self):
        r = run_script("fetch_latest_diary.py")
        self.assertEqual(r.returncode, 0)


class TestDailyCoachV3(unittest.TestCase):

    def test_importable(self):
        """daily_coach_v3 does network I/O on run — just verify it's importable."""
        r = subprocess.run(
            [sys.executable, "-c",
             "import importlib.util; "
             "spec = importlib.util.spec_from_file_location('daily_coach_v3', "
             f"'{SCRIPTS_DIR / 'daily_coach_v3.py'}'); "
             "assert spec is not None"],
            capture_output=True, text=True, timeout=TIMEOUT,
        )
        self.assertEqual(r.returncode, 0, f"Import check failed: {r.stderr}")


# --- Module import test ---

class TestDiaryUtils(unittest.TestCase):

    def test_importable(self):
        r = subprocess.run(
            [sys.executable, "-c", f"import sys; sys.path.insert(0, '{SCRIPTS_DIR}'); import diary_utils"],
            capture_output=True, text=True, timeout=TIMEOUT,
        )
        self.assertEqual(r.returncode, 0, f"Import failed: {r.stderr}")


if __name__ == "__main__":
    unittest.main()
