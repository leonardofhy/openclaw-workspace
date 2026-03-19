"""Tests for workspace_metrics.py."""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import workspace_metrics as wm


class TestCollectors(unittest.TestCase):
    """Unit tests for individual metric collectors."""

    def test_arrow_up(self):
        self.assertEqual(wm._arrow(5), "↑")

    def test_arrow_down(self):
        self.assertEqual(wm._arrow(-3), "↓")

    def test_arrow_flat(self):
        self.assertEqual(wm._arrow(0), "→")

    def test_moving_avg_enough_data(self):
        vals = [10, 20, 30, 40, 50, 60, 70]
        self.assertEqual(wm._moving_avg(vals, 7), 40.0)

    def test_moving_avg_insufficient(self):
        self.assertIsNone(wm._moving_avg([1, 2, 3], 7))

    def test_moving_avg_uses_last_window(self):
        vals = [0, 0, 0, 10, 20, 30, 40, 50, 60, 70]
        self.assertEqual(wm._moving_avg(vals, 7), 40.0)


class TestQueueStats(unittest.TestCase):
    """Queue stats parsing."""

    def test_queue_counts(self, ):
        queue_data = {
            "version": 1,
            "max_tasks": 25,
            "tasks": [
                {"id": "Q1", "status": "active"},
                {"id": "Q2", "status": "waiting"},
                {"id": "Q3", "status": "blocked"},
                {"id": "Q4", "status": "parked"},
                {"id": "Q5", "status": "done"},
            ],
            "archived_count": 50,
        }
        with patch.object(wm, "WORKSPACE", Path("/fake")):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.read_text", return_value=json.dumps(queue_data)):
                    result = wm.queue_stats()
        self.assertEqual(result["ready"], 2)   # active + waiting
        self.assertEqual(result["done"], 51)   # 1 done + 50 archived
        self.assertEqual(result["blocked"], 2) # blocked + parked

    def test_queue_missing_file(self):
        with patch.object(wm, "WORKSPACE", Path("/fake")):
            with patch("pathlib.Path.exists", return_value=False):
                result = wm.queue_stats()
        self.assertEqual(result, {"ready": 0, "done": 0, "blocked": 0})


class TestExperimentPassRate(unittest.TestCase):
    """Experiment pass rate calculation."""

    def test_pass_rate(self):
        lines = "\n".join([
            json.dumps({"id": "E-001", "status": "success"}),
            json.dumps({"id": "E-002", "status": "failure"}),
            json.dumps({"id": "E-003", "status": "success"}),
        ])
        with patch.object(wm, "WORKSPACE", Path("/fake")):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.read_text", return_value=lines):
                    rate = wm.experiment_pass_rate()
        self.assertAlmostEqual(rate, 0.667)

    def test_empty_experiments(self):
        with patch.object(wm, "WORKSPACE", Path("/fake")):
            with patch("pathlib.Path.exists", return_value=False):
                self.assertEqual(wm.experiment_pass_rate(), 0.0)


class TestBootBudget(unittest.TestCase):
    """Boot budget percentage."""

    def test_budget_calc(self):
        # 150 lines out of 300 = 50%
        def fake_read(encoding="utf-8"):
            return "\n".join(["line"] * 30)

        with patch.object(wm, "WORKSPACE", Path("/fake")):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.read_text", side_effect=fake_read):
                    pct = wm.boot_budget_pct()
        # 5 files × 30 lines = 150 / 300 = 50%
        self.assertEqual(pct, 50)


class TestSnapshotIO(unittest.TestCase):
    """Save and load snapshots."""

    def test_save_and_load(self, tmp_path=None):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            test_file = tmp / "metrics" / "daily-metrics.jsonl"
            with patch.object(wm, "METRICS_FILE", test_file):
                snap1 = {"date": "2026-03-17", "source_loc": 100}
                snap2 = {"date": "2026-03-18", "source_loc": 200}
                wm.save_snapshot(snap1)
                wm.save_snapshot(snap2)
                entries = wm.load_all()
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0]["date"], "2026-03-17")
            self.assertEqual(entries[1]["source_loc"], 200)

    def test_same_date_replaces(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            test_file = tmp / "metrics" / "daily-metrics.jsonl"
            with patch.object(wm, "METRICS_FILE", test_file):
                wm.save_snapshot({"date": "2026-03-18", "source_loc": 100})
                wm.save_snapshot({"date": "2026-03-18", "source_loc": 200})
                entries = wm.load_all()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["source_loc"], 200)


class TestTrendReport(unittest.TestCase):
    """Trend analysis."""

    def test_needs_two_entries(self):
        result = wm.trend_report([{"date": "2026-03-18"}])
        self.assertIn("error", result)

    def test_computes_deltas(self):
        e1 = {"date": "2026-03-17", "source_loc": 1000, "test_loc": 300,
               "test_count": 100, "python_files": 50, "commits_today": 10,
               "boot_budget_pct": 45, "queue_ready": 2, "queue_done": 20,
               "queue_blocked": 1, "experiment_pass_rate": 0.9}
        e2 = {**e1, "date": "2026-03-18", "source_loc": 1100, "test_count": 110}
        result = wm.trend_report([e1, e2])
        self.assertEqual(result["deltas"]["source_loc"]["delta"], 100)
        self.assertEqual(result["deltas"]["source_loc"]["arrow"], "↑")
        self.assertEqual(result["deltas"]["test_count"]["delta"], 10)
        self.assertEqual(result["deltas"]["boot_budget_pct"]["delta"], 0)
        self.assertEqual(result["deltas"]["boot_budget_pct"]["arrow"], "→")


class TestCLI(unittest.TestCase):
    """CLI argument parsing."""

    def test_snapshot_flag(self):
        args = wm.parse_args(["--snapshot"])
        self.assertTrue(args.snapshot)
        self.assertFalse(args.json)

    def test_report_json(self):
        args = wm.parse_args(["--report", "--json"])
        self.assertTrue(args.report)
        self.assertTrue(args.json)

    def test_mutually_exclusive(self):
        with self.assertRaises(SystemExit):
            wm.parse_args(["--snapshot", "--report"])


if __name__ == "__main__":
    unittest.main()
