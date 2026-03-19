#!/usr/bin/env python3
"""Tests for expense_forecast.py functionality."""

import json
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

# Add script directory to path
sys.path.insert(0, str(Path(__file__).parent))

import expense_forecast as ef


class TestExpenseForecast(unittest.TestCase):

    def setUp(self):
        """Create mock data for testing."""
        self.mock_snapshots = [
            {
                "id": "SNAP-001",
                "date": "2026-01-15",
                "savings": 300000,
                "monthly_income": 18000,
                "monthly_expenses": 24000,
                "net": -6000
            },
            {
                "id": "SNAP-002",
                "date": "2026-02-15",
                "savings": 294000,
                "monthly_income": 20000,
                "monthly_expenses": 25600,
                "net": -5600
            }
        ]

        self.mock_income_log = [
            {
                "id": "INC-001",
                "date": "2026-01-10",
                "source": "tutoring",
                "amount": 4800,
                "note": "2 sessions"
            },
            {
                "id": "INC-002",
                "date": "2026-02-05",
                "source": "research_assistant",
                "amount": 15200,
                "note": "monthly stipend"
            },
            {
                "id": "INC-003",
                "date": "2026-02-15",
                "source": "tutoring",
                "amount": 4800,
                "note": "2 sessions"
            }
        ]

        self.mock_expense_log = [
            {
                "id": "EXP-001",
                "date": "2026-02-01",
                "source": "Interspeech registration",
                "amount": 8000,
                "note": "conference fee"
            }
        ]

        self.mock_deadlines = [
            {
                "id": "D-001",
                "name": "NTU Scholarship Application",
                "deadline": "2026-03-25",
                "category": "scholarship",
                "action": "Submit application documents",
                "status": "open"
            },
            {
                "id": "D-002",
                "name": "Research Grant Follow-up",
                "deadline": "2026-03-15",
                "category": "funding",
                "action": "Send follow-up email",
                "status": "open"
            },
            {
                "id": "D-003",
                "name": "Completed Application",
                "deadline": "2026-02-01",
                "category": "scholarship",
                "action": "Already submitted",
                "status": "done"
            }
        ]

    def test_calc_burn_rate(self):
        """Test burn rate calculation from snapshots."""
        # Test with positive burn rate (spending more than earning)
        burn_rate = ef.calc_burn_rate(self.mock_snapshots)
        self.assertEqual(burn_rate, 5600, "Should return positive burn rate from latest snapshot")

        # Test with empty snapshots
        burn_rate_empty = ef.calc_burn_rate([])
        self.assertEqual(burn_rate_empty, 0.0, "Should return 0 for empty snapshots")

        # Test with positive net (earning more than spending)
        positive_snapshot = [{
            "date": "2026-03-01",
            "net": 2000
        }]
        burn_rate_positive = ef.calc_burn_rate(positive_snapshot)
        self.assertEqual(burn_rate_positive, 0.0, "Should return 0 for positive net flow")

    def test_calc_avg_income(self):
        """Test average income calculation from income log."""
        with patch('expense_forecast.date') as mock_date:
            mock_date.today.return_value = date(2026, 3, 19)

            # Test 3-month average (Jan-Mar 2026)
            avg_income = ef.calc_avg_income(self.mock_income_log, months=3)
            # Jan: 4800, Feb: 20000 (15200 + 4800), Mar: no entries
            # Total 24800 over 2 months with income = 12400 average
            self.assertAlmostEqual(avg_income, 12400.0, places=0)

            # Test with empty income log
            avg_income_empty = ef.calc_avg_income([], months=3)
            self.assertEqual(avg_income_empty, 0.0)

    def test_project_runway(self):
        """Test runway projection scenarios."""
        savings = 300000
        burn_rate = 5000

        runway = ef.project_runway(savings, burn_rate)

        # Check all three scenarios are present
        self.assertIn("pessimistic", runway)
        self.assertIn("realistic", runway)
        self.assertIn("optimistic", runway)

        # Realistic should be savings / burn_rate
        self.assertEqual(runway["realistic"], 60.0)

        # Pessimistic should be higher burn rate (shorter runway)
        self.assertLess(runway["pessimistic"], runway["realistic"])

        # Optimistic should be lower burn rate (longer runway)
        self.assertGreater(runway["optimistic"], runway["realistic"])

        # Test zero burn rate (infinite runway)
        infinite_runway = ef.project_runway(savings, 0)
        for scenario in infinite_runway.values():
            self.assertEqual(scenario, float("inf"))

    def test_get_income_sources(self):
        """Test income source grouping."""
        with patch('expense_forecast.date') as mock_date:
            mock_date.today.return_value = date(2026, 3, 19)

            sources = ef.get_income_sources(self.mock_income_log, months=3)

            # Should group tutoring (4800 + 4800) and research_assistant (15200)
            self.assertEqual(sources.get("tutoring"), 9600)
            self.assertEqual(sources.get("research_assistant"), 15200)

            # Test empty income log
            sources_empty = ef.get_income_sources([], months=3)
            self.assertEqual(sources_empty, {})

    def test_get_upcoming_deadlines(self):
        """Test upcoming deadline filtering."""
        with patch('expense_forecast.date') as mock_date:
            mock_date.today.return_value = date(2026, 3, 10)  # 10 days before first deadline

            upcoming = ef.get_upcoming_deadlines(self.mock_deadlines, days=30)

            # Should return 2 deadlines (D-001, D-002), excluding done status
            self.assertEqual(len(upcoming), 2)

            # Check sorting by days_left
            self.assertEqual(upcoming[0]["name"], "Research Grant Follow-up")  # 5 days
            self.assertEqual(upcoming[1]["name"], "NTU Scholarship Application")  # 15 days

            # Check days_left calculation
            self.assertEqual(upcoming[0]["days_left"], 5)
            self.assertEqual(upcoming[1]["days_left"], 15)

            # Test with shorter timeframe
            upcoming_short = ef.get_upcoming_deadlines(self.mock_deadlines, days=10)
            self.assertEqual(len(upcoming_short), 1)
            self.assertEqual(upcoming_short[0]["name"], "Research Grant Follow-up")

    def test_get_scholarship_status(self):
        """Test scholarship status extraction."""
        with patch('expense_forecast.date') as mock_date:
            mock_date.today.return_value = date(2026, 3, 10)

            scholarships = ef.get_scholarship_status(self.mock_deadlines)

            # Should include all scholarship/funding items regardless of status
            self.assertEqual(len(scholarships), 3)

            # Check status assignment
            open_items = [s for s in scholarships if s["status"] == "open"]
            done_items = [s for s in scholarships if s["status"] == "done"]

            self.assertEqual(len(open_items), 2)  # D-001, D-002
            self.assertEqual(len(done_items), 1)   # D-003

            # Check sorting by days_left
            self.assertTrue(scholarships[0]["days_left"] <= scholarships[1]["days_left"])

    @patch('expense_forecast.load_snapshots')
    @patch('expense_forecast.load_income_log')
    @patch('expense_forecast.load_expense_log')
    @patch('expense_forecast.load_deadlines')
    def test_build_summary_integration(self, mock_deadlines, mock_expense_log,
                                     mock_income_log, mock_snapshots):
        """Test full summary generation with mocked data."""
        # Set up mocks
        mock_snapshots.return_value = self.mock_snapshots
        mock_income_log.return_value = self.mock_income_log
        mock_expense_log.return_value = self.mock_expense_log
        mock_deadlines.return_value = self.mock_deadlines

        with patch('expense_forecast.date') as mock_date:
            mock_date.today.return_value = date(2026, 3, 19)

            summary = ef.build_summary()

            # Check key fields are present
            self.assertIn("date", summary)
            self.assertIn("savings", summary)
            self.assertIn("burn_rate", summary)
            self.assertIn("runway", summary)
            self.assertIn("income_sources", summary)
            self.assertIn("upcoming_deadlines", summary)

            # Check data integrity
            self.assertEqual(summary["savings"], 294000)  # Latest snapshot
            self.assertEqual(summary["burn_rate"], 5600)   # From latest net
            self.assertIn("tutoring", summary["income_sources"])
            self.assertGreater(len(summary["upcoming_deadlines"]), 0)

    @patch('expense_forecast.build_summary')
    def test_cmd_json_output(self, mock_summary):
        """Test JSON output formatting for heartbeat."""
        mock_summary.return_value = {
            "date": "2026-03-19",
            "savings": 294000,
            "monthly_income": 20000,
            "monthly_expenses": 25600,
            "burn_rate": 5600,
            "runway": {"pessimistic": 45.8, "realistic": 52.5, "optimistic": 65.6},
            "snapshot_age_days": 32,
            "upcoming_deadlines": [{"name": "Test Deadline"}]
        }

        with patch('sys.stdout.write') as mock_stdout:
            ef.cmd_json()

            # Capture the output and parse as JSON
            output_calls = mock_stdout.call_args_list
            json_output = ''.join(call[0][0] for call in output_calls)

            # Should be valid JSON
            parsed = json.loads(json_output)

            # Check required heartbeat fields
            self.assertIn("status", parsed)
            self.assertIn("upcoming_deadline_count", parsed)
            self.assertIn("next_deadline", parsed)

            # Check status logic (>30 days = warning)
            self.assertEqual(parsed["status"], "warning")


if __name__ == "__main__":
    unittest.main()