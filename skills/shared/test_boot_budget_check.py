"""Unit tests for boot_budget_check.py — boot path line budget guardian."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))
import boot_budget_check as bbc  # noqa: E402


# ===========================================================================
# count_lines()
# ===========================================================================

class TestCountLines:
    def test_existing_file_returns_line_count(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("line1\nline2\nline3\n")
        assert bbc.count_lines(f) == 3

    def test_missing_file_returns_zero(self, tmp_path):
        f = tmp_path / "nonexistent.md"
        assert bbc.count_lines(f) == 0

    def test_empty_file_returns_zero(self, tmp_path):
        f = tmp_path / "empty.md"
        f.write_text("")
        assert bbc.count_lines(f) == 0

    def test_single_line_no_trailing_newline(self, tmp_path):
        f = tmp_path / "one.md"
        f.write_text("single line")
        assert bbc.count_lines(f) == 1


# ===========================================================================
# check()
# ===========================================================================

class TestCheck:
    def _mock_count(self, line_counts: dict):
        """Return a side_effect function for count_lines based on filename."""
        def _count(path: Path):
            name = str(path)
            for key, val in line_counts.items():
                if name.endswith(key):
                    return val
            return 0
        return _count

    @patch.object(bbc, "count_lines")
    def test_all_files_under_budget_status_ok(self, mock_cl):
        mock_cl.return_value = 10
        report = bbc.check()
        assert report["total_status"] == "ok"
        assert all(f["status"] == "ok" for f in report["files"])

    @patch.object(bbc, "count_lines")
    def test_file_at_exactly_budget_is_over(self, mock_cl):
        """ratio == 1.0 → status 'over'."""
        counts = {
            "MEMORY.md": 80,  # exactly at budget
            "SESSION-STATE.md": 0,
            "memory/anti-patterns.md": 0,
            "SOUL.md": 0,
            "USER.md": 0,
        }
        mock_cl.side_effect = self._mock_count(counts)
        report = bbc.check()
        memory_file = next(f for f in report["files"] if f["file"] == "MEMORY.md")
        assert memory_file["status"] == "over"
        assert memory_file["ratio"] == 1.0

    @patch.object(bbc, "count_lines")
    def test_file_at_warn_threshold(self, mock_cl):
        """80% of budget → status 'warn'."""
        counts = {
            "MEMORY.md": 64,  # 64/80 = 0.80 exactly
            "SESSION-STATE.md": 0,
            "memory/anti-patterns.md": 0,
            "SOUL.md": 0,
            "USER.md": 0,
        }
        mock_cl.side_effect = self._mock_count(counts)
        report = bbc.check()
        memory_file = next(f for f in report["files"] if f["file"] == "MEMORY.md")
        assert memory_file["status"] == "warn"

    @patch.object(bbc, "count_lines")
    def test_file_just_below_warn_threshold(self, mock_cl):
        """79% of budget → still 'ok'."""
        counts = {
            "MEMORY.md": 63,  # 63/80 = 0.7875 < 0.80
            "SESSION-STATE.md": 0,
            "memory/anti-patterns.md": 0,
            "SOUL.md": 0,
            "USER.md": 0,
        }
        mock_cl.side_effect = self._mock_count(counts)
        report = bbc.check()
        memory_file = next(f for f in report["files"] if f["file"] == "MEMORY.md")
        assert memory_file["status"] == "ok"

    @patch.object(bbc, "count_lines")
    def test_total_budget_over(self, mock_cl):
        """Total >= 300 → total_status 'over'."""
        mock_cl.return_value = 60  # 60 * 5 = 300, ratio = 1.0
        report = bbc.check()
        assert report["total_lines"] == 300
        assert report["total_status"] == "over"

    @patch.object(bbc, "count_lines")
    def test_total_budget_warn(self, mock_cl):
        """Total >= 240 (80%) but < 300 → total_status 'warn'."""
        mock_cl.return_value = 48  # 48 * 5 = 240, ratio = 0.80
        report = bbc.check()
        assert report["total_lines"] == 240
        assert report["total_status"] == "warn"

    @patch.object(bbc, "count_lines")
    def test_report_structure(self, mock_cl):
        mock_cl.return_value = 5
        report = bbc.check()
        assert "files" in report
        assert "total_lines" in report
        assert "total_budget" in report
        assert "total_ratio" in report
        assert "total_status" in report
        assert len(report["files"]) == len(bbc.BUDGETS)
        for f in report["files"]:
            assert set(f.keys()) == {"file", "lines", "budget", "ratio", "status"}

    @patch.object(bbc, "count_lines")
    def test_all_files_missing_returns_zero_total(self, mock_cl):
        mock_cl.return_value = 0
        report = bbc.check()
        assert report["total_lines"] == 0
        assert report["total_status"] == "ok"


# ===========================================================================
# print_human()
# ===========================================================================

class TestPrintHuman:
    @patch.object(bbc, "count_lines")
    def test_print_human_shows_over_action_needed(self, mock_cl, capsys):
        mock_cl.return_value = 100  # over budget for all files
        report = bbc.check()
        bbc.print_human(report)
        out = capsys.readouterr().out
        assert "Action needed" in out
        assert "over budget" in out

    @patch.object(bbc, "count_lines")
    def test_print_human_ok_no_action_needed(self, mock_cl, capsys):
        mock_cl.return_value = 1
        report = bbc.check()
        bbc.print_human(report)
        out = capsys.readouterr().out
        assert "Action needed" not in out


# ===========================================================================
# main()
# ===========================================================================

class TestMain:
    @patch.object(bbc, "count_lines")
    def test_main_exits_0_when_ok(self, mock_cl):
        mock_cl.return_value = 1
        with patch.object(sys, "argv", ["boot_budget_check.py"]):
            with pytest.raises(SystemExit) as exc_info:
                bbc.main()
            assert exc_info.value.code == 0

    @patch.object(bbc, "count_lines")
    def test_main_exits_2_when_over(self, mock_cl):
        mock_cl.return_value = 100
        with patch.object(sys, "argv", ["boot_budget_check.py"]):
            with pytest.raises(SystemExit) as exc_info:
                bbc.main()
            assert exc_info.value.code == 2

    @patch.object(bbc, "count_lines")
    def test_main_exits_1_when_warn(self, mock_cl):
        # Set each file to 80% of its own budget → warn but not over
        pcts = {
            "MEMORY.md": 64,             # 80% of 80
            "SESSION-STATE.md": 24,      # 80% of 30
            "memory/anti-patterns.md": 40,  # 80% of 50
            "SOUL.md": 40,              # 80% of 50
            "USER.md": 16,              # 80% of 20
        }
        def _count(path):
            for key, val in pcts.items():
                if str(path).endswith(key):
                    return val
            return 0
        mock_cl.side_effect = _count
        with patch.object(sys, "argv", ["boot_budget_check.py"]):
            with pytest.raises(SystemExit) as exc_info:
                bbc.main()
            assert exc_info.value.code == 1

    @patch.object(bbc, "count_lines")
    def test_main_json_flag_outputs_valid_json(self, mock_cl, capsys):
        mock_cl.return_value = 1
        with patch.object(sys, "argv", ["boot_budget_check.py", "--json"]):
            with pytest.raises(SystemExit):
                bbc.main()
            out = capsys.readouterr().out
            data = json.loads(out)
            assert "files" in data
            assert "total_status" in data
