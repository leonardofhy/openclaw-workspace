#!/usr/bin/env python3
"""
Unit tests for skills/shared/daily_digest.py

Covers:
- collect_git() — commit parsing, empty output, subprocess failure
- collect_autodidact() — event filtering by date, action counting, highlights
- collect_active_state() — JSON loading, missing file
- collect_queue() — task status aggregation, missing file
- collect_tests() — test count parsing, error handling
- collect_paper() — word counts, TODO counts
- collect_daily_notes() — existing and missing briefings
- collect_cycle_files() — prefix matching
- extract_highlights() — top 3 selection, fallback
- infer_priorities() — blocked tasks, TODOs, budget exhaustion
- format_terminal() — structure, key sections present
- format_discord() — no markdown tables, bullets only
- format_email() — HTML structure
- format_json() — valid JSON roundtrip
- save_digest() — file append
- parse_args() — flag parsing, defaults
- main() — integration with --skip-tests

Usage:
    python3 -m pytest skills/shared/test_daily_digest.py -v
    python3 skills/shared/test_daily_digest.py
"""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Import daily_digest from this directory
# ---------------------------------------------------------------------------
SHARED_DIR = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("daily_digest", SHARED_DIR / "daily_digest.py")
daily_digest = importlib.util.module_from_spec(_spec)
sys.modules["daily_digest"] = daily_digest
_spec.loader.exec_module(daily_digest)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_events_jsonl(tmp: Path, events: list[dict]) -> Path:
    p = tmp / "events.jsonl"
    with open(p, "w") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")
    return p


def _make_queue_json(tmp: Path, tasks: list[dict], archived: int = 0) -> Path:
    p = tmp / "queue.json"
    with open(p, "w") as f:
        json.dump({"version": 1, "max_tasks": 25, "tasks": tasks,
                    "archived_count": archived, "last_updated": "2026-03-18"}, f)
    return p


def _make_active_json(tmp: Path, phase: str = "converge", budgets: dict | None = None) -> Path:
    p = tmp / "active.json"
    data = {
        "version": 1, "phase": phase,
        "budgets": budgets or {"learn_remaining_today": 3, "build_remaining_today": 5,
                                "reflect_remaining_today": 2},
        "stats": {"total_cycles": 100, "papers_read_deep": 30, "code_artifacts": 40},
        "last_cycle": {"id": "c-20260318-1315", "action": "learn",
                       "summary": "Deep read some paper"},
    }
    with open(p, "w") as f:
        json.dump(data, f)
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCollectGit(unittest.TestCase):
    @patch("daily_digest.subprocess.run")
    def test_parses_commits(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2|feat: add thing\n"
                " 3 files changed, 50 insertions(+), 10 deletions(-)\n"
                "\n"
                "f1e2d3c4b5a6f1e2d3c4b5a6f1e2d3c4b5a6f1e2|fix: bug\n"
                " 1 file changed, 5 insertions(+)\n"
            ),
        )
        result = daily_digest.collect_git(date(2026, 3, 18))
        self.assertEqual(result["commits"], 2)
        self.assertEqual(result["added"], 55)
        self.assertEqual(result["removed"], 10)
        self.assertEqual(result["files_changed"], 4)
        self.assertEqual(len(result["messages"]), 2)

    @patch("daily_digest.subprocess.run")
    def test_empty_log(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        result = daily_digest.collect_git(date(2026, 3, 18))
        self.assertEqual(result["commits"], 0)

    @patch("daily_digest.subprocess.run", side_effect=FileNotFoundError)
    def test_git_not_found(self, mock_run):
        result = daily_digest.collect_git(date(2026, 3, 18))
        self.assertEqual(result["commits"], 0)


class TestCollectAutodidact(unittest.TestCase):
    def test_filters_by_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = _make_events_jsonl(Path(tmp), [
                {"v": 1, "ts": "2026-03-18T10:00:00+08:00", "action": "learn",
                 "summary": "Read paper X", "phase": "converge", "blocked": False},
                {"v": 1, "ts": "2026-03-18T11:00:00+08:00", "action": "build",
                 "summary": "Built thing Y", "phase": "converge", "blocked": False},
                {"v": 1, "ts": "2026-03-17T10:00:00+08:00", "action": "learn",
                 "summary": "Yesterday event", "phase": "explore", "blocked": False},
            ])
            with patch.object(daily_digest, "EVENTS_JSONL", p):
                result = daily_digest.collect_autodidact(date(2026, 3, 18))
            self.assertEqual(result["cycles"], 2)
            self.assertEqual(result["actions"]["learn"], 1)
            self.assertEqual(result["actions"]["build"], 1)
            self.assertEqual(len(result["highlights"]), 2)

    def test_missing_file(self):
        with patch.object(daily_digest, "EVENTS_JSONL", Path("/nonexistent")):
            result = daily_digest.collect_autodidact(date(2026, 3, 18))
        self.assertEqual(result["cycles"], 0)

    def test_skip_action_excluded_from_highlights(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = _make_events_jsonl(Path(tmp), [
                {"v": 1, "ts": "2026-03-18T10:00:00+08:00", "action": "skip",
                 "summary": "Budget exhausted", "phase": "converge", "blocked": True},
            ])
            with patch.object(daily_digest, "EVENTS_JSONL", p):
                result = daily_digest.collect_autodidact(date(2026, 3, 18))
            self.assertEqual(result["cycles"], 1)
            self.assertEqual(result["highlights"], [])
            self.assertEqual(result["blocked_count"], 1)

    def test_corrupt_line_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "events.jsonl"
            with open(p, "w") as f:
                f.write("NOT JSON\n")
                f.write(json.dumps({"v": 1, "ts": "2026-03-18T12:00:00", "action": "learn",
                                    "summary": "OK", "blocked": False}) + "\n")
            with patch.object(daily_digest, "EVENTS_JSONL", p):
                result = daily_digest.collect_autodidact(date(2026, 3, 18))
            self.assertEqual(result["cycles"], 1)


class TestCollectActiveState(unittest.TestCase):
    def test_reads_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = _make_active_json(Path(tmp))
            with patch.object(daily_digest, "ACTIVE_JSON", p):
                result = daily_digest.collect_active_state()
            self.assertEqual(result["phase"], "converge")

    def test_missing_file(self):
        with patch.object(daily_digest, "ACTIVE_JSON", Path("/nonexistent")):
            result = daily_digest.collect_active_state()
        self.assertEqual(result, {})


class TestCollectQueue(unittest.TestCase):
    def test_status_aggregation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = _make_queue_json(Path(tmp), [
                {"id": "Q1", "status": "blocked"},
                {"id": "Q2", "status": "blocked"},
                {"id": "Q3", "status": "ready"},
            ], archived=50)
            with patch.object(daily_digest, "QUEUE_JSON", p):
                result = daily_digest.collect_queue()
            self.assertEqual(result["total"], 3)
            self.assertEqual(result["archived"], 50)
            self.assertEqual(result["by_status"]["blocked"], 2)
            self.assertEqual(result["by_status"]["ready"], 1)

    def test_missing_file(self):
        with patch.object(daily_digest, "QUEUE_JSON", Path("/nonexistent")):
            result = daily_digest.collect_queue()
        self.assertEqual(result["total"], 0)


class TestCollectTests(unittest.TestCase):
    @patch("daily_digest.subprocess.run")
    def test_parses_count(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="150 tests collected\n")
        result = daily_digest.collect_tests()
        self.assertEqual(result["total"], 150)

    @patch("daily_digest.subprocess.run", side_effect=FileNotFoundError)
    def test_pytest_not_found(self, mock_run):
        result = daily_digest.collect_tests()
        self.assertEqual(result["error"], "pytest not available")


class TestCollectPaper(unittest.TestCase):
    def test_word_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp)
            (docs / "paper-a-abstract.md").write_text("word " * 300)
            (docs / "paper-a-intro-rw.md").write_text("word " * 1000 + "\nTODO: fix this\n")
            with patch.object(daily_digest, "DOCS_DIR", docs):
                result = daily_digest.collect_paper()
            self.assertEqual(result["sections"]["Abstract"]["words"], 300)
            self.assertGreaterEqual(result["sections"]["Intro & RW"]["todos"], 1)
            self.assertGreater(result["total_words"], 1000)

    def test_missing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(daily_digest, "DOCS_DIR", Path(tmp)):
                result = daily_digest.collect_paper()
            self.assertEqual(result["total_words"], 0)


class TestCollectDailyNotes(unittest.TestCase):
    def test_existing_briefing(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "2026-03-18.md").write_text("Today's focus: Paper A")
            with patch.object(daily_digest, "BRIEFINGS_DIR", d):
                result = daily_digest.collect_daily_notes(date(2026, 3, 18))
            self.assertEqual(result, "Today's focus: Paper A")

    def test_missing_briefing(self):
        with patch.object(daily_digest, "BRIEFINGS_DIR", Path("/nonexistent")):
            result = daily_digest.collect_daily_notes(date(2026, 3, 18))
        self.assertIsNone(result)


class TestCollectCycleFiles(unittest.TestCase):
    def test_counts_matching(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "c-20260318-1015.md").write_text("cycle 1")
            (d / "c-20260318-1045.md").write_text("cycle 2")
            (d / "c-20260317-1015.md").write_text("yesterday")
            with patch.object(daily_digest, "CYCLES_DIR", d):
                result = daily_digest.collect_cycle_files(date(2026, 3, 18))
            self.assertEqual(result, 2)


class TestExtractHighlights(unittest.TestCase):
    def test_top_3(self):
        data = {"autodidact": {"highlights": ["A", "B", "C", "D"]}}
        result = daily_digest.extract_highlights(data)
        self.assertEqual(len(result), 3)
        self.assertEqual(result, ["A", "B", "C"])

    def test_fallback_git(self):
        data = {"autodidact": {"highlights": []}, "git": {"messages": ["commit msg"]}}
        result = daily_digest.extract_highlights(data)
        self.assertEqual(result, ["commit msg"])

    def test_no_activity(self):
        data = {"autodidact": {"highlights": []}, "git": {"messages": []}}
        result = daily_digest.extract_highlights(data)
        self.assertEqual(result, ["No activity recorded"])

    def test_long_summary_truncated(self):
        data = {"autodidact": {"highlights": ["x" * 200]}}
        result = daily_digest.extract_highlights(data)
        self.assertTrue(result[0].endswith("..."))
        self.assertLessEqual(len(result[0]), 124)


class TestInferPriorities(unittest.TestCase):
    def test_blocked_tasks(self):
        data = {"queue": {"by_status": {"blocked": 3}}, "paper": {}, "active": {}}
        result = daily_digest.infer_priorities(data)
        self.assertTrue(any("3 blocked" in p for p in result))

    def test_paper_todos(self):
        data = {"queue": {"by_status": {}}, "paper": {"total_todos": 5}, "active": {}}
        result = daily_digest.infer_priorities(data)
        self.assertTrue(any("5 paper TODO" in p for p in result))

    def test_build_budget_exhausted(self):
        data = {"queue": {"by_status": {}}, "paper": {},
                "active": {"budgets": {"build_remaining_today": 0}}}
        result = daily_digest.infer_priorities(data)
        self.assertTrue(any("budget" in p.lower() for p in result))

    def test_fallback(self):
        data = {"queue": {"by_status": {}}, "paper": {},
                "active": {"budgets": {"build_remaining_today": 5}}}
        result = daily_digest.infer_priorities(data)
        self.assertEqual(result, ["Review queue and pick highest-priority task"])


class TestFormatTerminal(unittest.TestCase):
    def _make_data(self):
        return {
            "date": "2026-03-18",
            "git": {"commits": 3, "added": 200, "removed": 50, "files_changed": 8, "messages": ["a"]},
            "autodidact": {"cycles": 5, "actions": {"learn": 3, "build": 2},
                           "phase": "converge", "highlights": ["Did X", "Did Y"], "blocked_count": 0},
            "active": {"budgets": {"learn_remaining_today": 2, "build_remaining_today": 8,
                                    "reflect_remaining_today": 1},
                        "stats": {"total_cycles": 200, "papers_read_deep": 50, "code_artifacts": 60},
                        "last_cycle": {"summary": "Read paper Z"}},
            "queue": {"total": 3, "by_status": {"blocked": 2, "ready": 1}, "archived": 100},
            "paper": {"total_words": 5000, "total_todos": 3, "sections": {}, "latex_words": 10000},
            "tests": {"total": 150, "error": None},
            "cycle_files": 5,
        }

    def test_contains_sections(self):
        output = daily_digest.format_terminal(self._make_data())
        self.assertIn("Daily Digest", output)
        self.assertIn("Highlights", output)
        self.assertIn("Research Progress", output)
        self.assertIn("Engineering", output)
        self.assertIn("Autodidact", output)
        self.assertIn("Queue", output)
        self.assertIn("Tomorrow", output)

    def test_contains_stats(self):
        output = daily_digest.format_terminal(self._make_data())
        self.assertIn("Commits: 3", output)
        self.assertIn("+200", output)
        self.assertIn("-50", output)
        self.assertIn("Cycles: 5", output)
        self.assertIn("5000 words", output)
        self.assertIn("150 collected", output)


class TestFormatDiscord(unittest.TestCase):
    def test_no_tables(self):
        data = {
            "date": "2026-03-18",
            "git": {"commits": 1, "added": 10, "removed": 5, "messages": []},
            "autodidact": {"cycles": 2, "actions": {"learn": 1, "build": 1},
                           "highlights": ["Thing"], "blocked_count": 0},
            "paper": {"total_words": 1000, "total_todos": 0},
            "tests": {"total": 50},
            "queue": {"by_status": {}},
            "active": {},
        }
        output = daily_digest.format_discord(data)
        self.assertNotIn("|", output)
        self.assertIn("**Daily Digest", output)
        self.assertIn("Commits: 1", output)


class TestFormatEmail(unittest.TestCase):
    def test_html_structure(self):
        data = {
            "date": "2026-03-18",
            "git": {"commits": 2, "added": 100, "removed": 20, "messages": []},
            "autodidact": {"cycles": 3, "actions": {"learn": 2, "build": 1},
                           "highlights": ["Alpha", "Beta"], "blocked_count": 0},
            "paper": {"total_words": 3000, "total_todos": 1},
            "tests": {"total": 80},
            "queue": {"by_status": {"blocked": 1}},
            "active": {},
        }
        output = daily_digest.format_email(data)
        self.assertIn("<!DOCTYPE html>", output)
        self.assertIn("<h2>Daily Digest", output)
        self.assertIn("Commits: 2", output)


class TestFormatJson(unittest.TestCase):
    def test_roundtrip(self):
        data = {"date": "2026-03-18", "git": {"commits": 1}}
        output = daily_digest.format_json(data)
        parsed = json.loads(output)
        self.assertEqual(parsed["git"]["commits"], 1)


class TestSaveDigest(unittest.TestCase):
    def test_appends_to_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            digests = Path(tmp) / "digests"
            with patch.object(daily_digest, "DIGESTS_DIR", digests):
                p = daily_digest.save_digest({"date": "2026-03-18"}, "# Digest content")
            self.assertTrue(p.exists())
            self.assertIn("Digest content", p.read_text())

    def test_appends_not_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            digests = Path(tmp) / "digests"
            with patch.object(daily_digest, "DIGESTS_DIR", digests):
                daily_digest.save_digest({"date": "2026-03-18"}, "First")
                daily_digest.save_digest({"date": "2026-03-18"}, "Second")
                p = digests / "2026-03-18-digest.md"
            content = p.read_text()
            self.assertIn("First", content)
            self.assertIn("Second", content)


class TestParseArgs(unittest.TestCase):
    def test_defaults(self):
        args = daily_digest.parse_args([])
        self.assertFalse(args.terminal)
        self.assertFalse(args.discord)
        self.assertFalse(args.email)
        self.assertFalse(args.json)
        self.assertFalse(args.save)
        self.assertIsNone(args.date)

    def test_flags(self):
        args = daily_digest.parse_args(["--discord", "--save", "--date", "2026-03-17"])
        self.assertTrue(args.discord)
        self.assertTrue(args.save)
        self.assertEqual(args.date, "2026-03-17")

    def test_skip_tests_flag(self):
        args = daily_digest.parse_args(["--skip-tests"])
        self.assertTrue(args.skip_tests)


class TestMain(unittest.TestCase):
    @patch("daily_digest.collect_tests")
    @patch("daily_digest.subprocess.run")
    def test_terminal_output(self, mock_git_run, mock_tests):
        mock_git_run.return_value = MagicMock(returncode=0, stdout="")
        mock_tests.return_value = {"total": 0, "error": "skipped"}
        output = daily_digest.main(["--terminal", "--skip-tests", "--date", "2026-03-18"])
        self.assertIn("Daily Digest", output)

    @patch("daily_digest.collect_tests")
    @patch("daily_digest.subprocess.run")
    def test_json_output(self, mock_git_run, mock_tests):
        mock_git_run.return_value = MagicMock(returncode=0, stdout="")
        mock_tests.return_value = {"total": 0, "error": "skipped"}
        output = daily_digest.main(["--json", "--skip-tests", "--date", "2026-03-18"])
        parsed = json.loads(output)
        self.assertEqual(parsed["date"], "2026-03-18")


if __name__ == "__main__":
    unittest.main()
