"""Unit tests for todoist_hygiene.py — dedup + flag overdue todoist tasks."""

import json
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

# ---------------------------------------------------------------------------
# Bootstrap: stub the common module before import
# ---------------------------------------------------------------------------
TZ = timezone(timedelta(hours=8), name="Asia/Taipei")

_common_mod = types.ModuleType("common")
_common_mod.TZ = TZ
_common_mod.load_todoist_token = MagicMock(return_value="fake-token")
_common_mod.WORKSPACE = Path("/fake/workspace")

sys.modules["common"] = _common_mod

sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))
sys.path.insert(0, str(Path(__file__).parent.parent))

import todoist_hygiene as th  # noqa: E402


# ===========================================================================
# similarity()
# ===========================================================================

class TestSimilarity:
    def test_identical_strings(self):
        assert th.similarity("buy milk", "buy milk") == 1.0

    def test_case_insensitive(self):
        assert th.similarity("Buy Milk", "buy milk") == 1.0

    def test_completely_different(self):
        assert th.similarity("aaaa", "zzzz") < 0.1

    def test_partial_overlap(self):
        ratio = th.similarity("buy milk today", "buy milk tomorrow")
        assert 0.5 < ratio < 1.0


# ===========================================================================
# is_overdue()
# ===========================================================================

class TestIsOverdue:
    def _task(self, due_date_str=None, due_as_dict=True):
        if due_date_str is None:
            return {"content": "test", "id": "1"}
        if due_as_dict:
            return {"content": "test", "id": "1", "due": {"date": due_date_str}}
        return {"content": "test", "id": "1", "due": due_date_str}

    def test_no_due_date_not_overdue(self):
        assert th.is_overdue(self._task()) is False

    def test_future_date_not_overdue(self):
        future = (datetime.now(TZ) + timedelta(days=10)).strftime("%Y-%m-%d")
        assert th.is_overdue(self._task(future)) is False

    def test_yesterday_not_overdue(self):
        """1 day past is ≤3 days, so not overdue."""
        yesterday = (datetime.now(TZ) - timedelta(days=1)).strftime("%Y-%m-%d")
        assert th.is_overdue(self._task(yesterday)) is False

    def test_exactly_3_days_not_overdue(self):
        """Exactly 3 days past is NOT >3, so not overdue."""
        three_days = (datetime.now(TZ) - timedelta(days=3)).strftime("%Y-%m-%d")
        assert th.is_overdue(self._task(three_days)) is False

    def test_4_days_past_is_overdue(self):
        four_days = (datetime.now(TZ) - timedelta(days=4)).strftime("%Y-%m-%d")
        assert th.is_overdue(self._task(four_days)) is True

    def test_due_as_string_not_dict(self):
        old = (datetime.now(TZ) - timedelta(days=10)).strftime("%Y-%m-%d")
        assert th.is_overdue(self._task(old, due_as_dict=False)) is True

    def test_invalid_due_date_returns_false(self):
        task = {"content": "test", "id": "1", "due": {"date": "not-a-date"}}
        assert th.is_overdue(task) is False

    def test_empty_due_dict_returns_false(self):
        task = {"content": "test", "id": "1", "due": {}}
        assert th.is_overdue(task) is False


# ===========================================================================
# get_tasks()
# ===========================================================================

class TestGetTasks:
    @patch("todoist_hygiene.requests.get")
    def test_returns_list_directly(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": "1", "content": "task"}]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        result = th.get_tasks("token")
        assert result == [{"id": "1", "content": "task"}]

    @patch("todoist_hygiene.requests.get")
    def test_returns_results_key_from_dict(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": [{"id": "1"}]}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        result = th.get_tasks("token")
        assert result == [{"id": "1"}]

    @patch("todoist_hygiene.requests.get")
    def test_dict_without_results_returns_empty(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"other": "data"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        result = th.get_tasks("token")
        assert result == []


# ===========================================================================
# main() — integration-level tests with mocked I/O
# ===========================================================================

class TestMain:
    STATE_JSON = json.dumps({"lastChecks": {}, "recent_alerts": {}})

    def _tasks(self):
        """Sample tasks with duplicates and overdue items."""
        old_date = (datetime.now(TZ) - timedelta(days=10)).strftime("%Y-%m-%d")
        return [
            {"id": "1", "content": "Buy groceries", "due": None},
            {"id": "2", "content": "Buy groceries", "due": None},  # exact dup
            {"id": "3", "content": "Pay rent", "due": {"date": old_date}},  # overdue
        ]

    @patch("todoist_hygiene.delete_task")
    @patch("todoist_hygiene.get_tasks")
    @patch("todoist_hygiene.load_todoist_token", return_value="fake")
    def test_dry_run_no_deletions(self, mock_token, mock_get, mock_del):
        mock_get.return_value = self._tasks()

        with patch.object(sys, "argv", ["todoist_hygiene.py", "--dry-run"]):
            with patch("builtins.open", mock_open(read_data=self.STATE_JSON)):
                with patch.object(Path, "exists", return_value=True):
                    th.main()

        mock_del.assert_not_called()

    @patch("todoist_hygiene.delete_task")
    @patch("todoist_hygiene.get_tasks")
    @patch("todoist_hygiene.load_todoist_token", return_value="fake")
    def test_exact_duplicates_deleted(self, mock_token, mock_get, mock_del):
        mock_get.return_value = self._tasks()

        with patch.object(sys, "argv", ["todoist_hygiene.py"]):
            with patch("builtins.open", mock_open(read_data=self.STATE_JSON)):
                with patch.object(Path, "exists", return_value=True):
                    th.main()

        # Task "2" is the duplicate of "1"
        mock_del.assert_called_once_with("2", "fake")

    @patch("todoist_hygiene.delete_task")
    @patch("todoist_hygiene.get_tasks")
    @patch("todoist_hygiene.load_todoist_token", return_value="fake")
    def test_no_tasks_no_errors(self, mock_token, mock_get, mock_del):
        mock_get.return_value = []

        with patch.object(sys, "argv", ["todoist_hygiene.py", "--dry-run"]):
            with patch("builtins.open", mock_open(read_data=self.STATE_JSON)):
                with patch.object(Path, "exists", return_value=True):
                    th.main()

        mock_del.assert_not_called()

    @patch("todoist_hygiene.delete_task")
    @patch("todoist_hygiene.get_tasks")
    @patch("todoist_hygiene.load_todoist_token", return_value="fake")
    def test_overdue_flagged_in_output(self, mock_token, mock_get, mock_del, capsys):
        mock_get.return_value = self._tasks()

        with patch.object(sys, "argv", ["todoist_hygiene.py", "--dry-run"]):
            with patch("builtins.open", mock_open(read_data=self.STATE_JSON)):
                with patch.object(Path, "exists", return_value=True):
                    th.main()

        out = capsys.readouterr().out
        assert "Overdue (>3 days): 1" in out
