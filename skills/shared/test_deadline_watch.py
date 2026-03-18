"""Unit tests for deadline_watch.py — deadline scanning and alerting."""

import json
import sys
import types
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Bootstrap: stub jsonl_store before import
# ---------------------------------------------------------------------------
_fake_workspace = Path("/fake/workspace")

_jsonl_mod = types.ModuleType("jsonl_store")
_jsonl_mod.find_workspace = MagicMock(return_value=_fake_workspace)

sys.modules.setdefault("jsonl_store", _jsonl_mod)

sys.path.insert(0, str(Path(__file__).parent.parent))

import deadline_watch as dw  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dl(id="DL-001", name="Tax filing", deadline="2026-04-15",
        action="File taxes", status="open", warn_days=0):
    d = {"id": id, "name": name, "deadline": deadline, "action": action}
    if status:
        d["status"] = status
    if warn_days:
        d["warn_days"] = warn_days
    return d


# ===========================================================================
# check_deadlines()
# ===========================================================================

class TestCheckDeadlines:
    def test_empty_list_returns_empty_categories(self):
        result = dw.check_deadlines([], today=date(2026, 3, 18))
        assert result == {"overdue": [], "urgent": [], "upcoming": []}

    def test_overdue_deadline_categorized(self):
        dl = _dl(deadline="2026-03-10")
        result = dw.check_deadlines([dl], today=date(2026, 3, 18))
        assert len(result["overdue"]) == 1
        assert result["overdue"][0]["days_left"] == -8

    def test_urgent_deadline_within_warn_days(self):
        dl = _dl(deadline="2026-03-22")  # 4 days away
        result = dw.check_deadlines([dl], today=date(2026, 3, 18), warn_days=7)
        assert len(result["urgent"]) == 1
        assert result["urgent"][0]["days_left"] == 4

    def test_future_deadline_not_shown_without_show_all(self):
        dl = _dl(deadline="2026-06-01")  # far future
        result = dw.check_deadlines([dl], today=date(2026, 3, 18), warn_days=7)
        assert len(result["upcoming"]) == 0

    def test_future_deadline_shown_with_show_all(self):
        dl = _dl(deadline="2026-06-01")
        result = dw.check_deadlines([dl], today=date(2026, 3, 18),
                                     warn_days=7, show_all=True)
        assert len(result["upcoming"]) == 1

    def test_closed_deadline_skipped(self):
        dl = _dl(deadline="2026-03-10", status="closed")
        result = dw.check_deadlines([dl], today=date(2026, 3, 18))
        assert result == {"overdue": [], "urgent": [], "upcoming": []}

    def test_done_deadline_skipped(self):
        dl = _dl(deadline="2026-03-10", status="done")
        result = dw.check_deadlines([dl], today=date(2026, 3, 18))
        assert result["overdue"] == []

    def test_cancelled_deadline_skipped(self):
        dl = _dl(deadline="2026-03-10", status="cancelled")
        result = dw.check_deadlines([dl], today=date(2026, 3, 18))
        assert result["overdue"] == []

    def test_deadline_with_custom_warn_days(self):
        """Deadline's own warn_days overrides global when larger."""
        dl = _dl(deadline="2026-04-01", warn_days=20)  # 14 days away
        result = dw.check_deadlines([dl], today=date(2026, 3, 18), warn_days=7)
        assert len(result["urgent"]) == 1

    def test_all_overdue_sorted_nearest_first(self):
        dls = [
            _dl(id="DL-1", deadline="2026-03-01"),  # -17 days
            _dl(id="DL-2", deadline="2026-03-15"),  # -3 days
            _dl(id="DL-3", deadline="2026-03-10"),  # -8 days
        ]
        result = dw.check_deadlines(dls, today=date(2026, 3, 18))
        ids = [d["id"] for d in result["overdue"]]
        # Sorted by days_left ascending (most negative first)
        assert ids == ["DL-1", "DL-3", "DL-2"]

    def test_exactly_today_is_urgent_not_overdue(self):
        dl = _dl(deadline="2026-03-18")
        result = dw.check_deadlines([dl], today=date(2026, 3, 18), warn_days=7)
        assert len(result["overdue"]) == 0
        assert len(result["urgent"]) == 1
        assert result["urgent"][0]["days_left"] == 0

    def test_mixed_categories(self):
        dls = [
            _dl(id="DL-1", deadline="2026-03-10"),  # overdue
            _dl(id="DL-2", deadline="2026-03-20"),  # urgent (2 days)
            _dl(id="DL-3", deadline="2026-06-01"),  # future
        ]
        result = dw.check_deadlines(dls, today=date(2026, 3, 18),
                                     warn_days=7, show_all=True)
        assert len(result["overdue"]) == 1
        assert len(result["urgent"]) == 1
        assert len(result["upcoming"]) == 1


# ===========================================================================
# format_alerts()
# ===========================================================================

class TestFormatAlerts:
    def test_overdue_alert_format(self):
        results = {
            "overdue": [{"id": "DL-1", "name": "Tax", "days_left": -5, "action": "File"}],
            "urgent": [],
            "upcoming": [],
        }
        alerts = dw.format_alerts(results)
        assert len(alerts) == 1
        assert "OVERDUE" in alerts[0]
        assert "DL-1" in alerts[0]
        assert "5" in alerts[0]

    def test_urgent_alert_format(self):
        results = {
            "overdue": [],
            "urgent": [{"id": "DL-2", "name": "Rent", "days_left": 2,
                        "deadline": "2026-03-20", "action": "Pay"}],
            "upcoming": [],
        }
        alerts = dw.format_alerts(results)
        assert len(alerts) == 1
        assert "UPCOMING" in alerts[0]
        assert "DL-2" in alerts[0]

    def test_no_alerts_when_empty(self):
        results = {"overdue": [], "urgent": [], "upcoming": []}
        alerts = dw.format_alerts(results)
        assert alerts == []


# ===========================================================================
# load_deadlines()
# ===========================================================================

class TestLoadDeadlines:
    def test_missing_file_exits(self):
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        with patch.object(dw, "DEADLINES_FILE", mock_path):
            with pytest.raises(SystemExit) as exc_info:
                dw.load_deadlines()
            assert exc_info.value.code == 1


# ===========================================================================
# main()
# ===========================================================================

class TestMain:
    @patch.object(dw, "check_deadlines")
    @patch.object(dw, "load_deadlines")
    def test_main_exits_1_when_alerts(self, mock_load, mock_check):
        mock_load.return_value = [_dl(deadline="2026-03-10")]
        mock_check.return_value = {
            "overdue": [{"id": "DL-1", "name": "Tax", "days_left": -8,
                         "action": "File", "deadline": "2026-03-10"}],
            "urgent": [],
            "upcoming": [],
        }
        with patch.object(sys, "argv", ["deadline_watch.py"]):
            with pytest.raises(SystemExit) as exc_info:
                dw.main()
            assert exc_info.value.code == 1

    @patch.object(dw, "check_deadlines")
    @patch.object(dw, "load_deadlines")
    def test_main_exits_0_when_no_alerts(self, mock_load, mock_check):
        mock_load.return_value = [_dl(deadline="2026-06-01")]
        mock_check.return_value = {"overdue": [], "urgent": [], "upcoming": []}
        with patch.object(sys, "argv", ["deadline_watch.py"]):
            with pytest.raises(SystemExit) as exc_info:
                dw.main()
            assert exc_info.value.code == 0

    @patch.object(dw, "check_deadlines")
    @patch.object(dw, "load_deadlines")
    def test_main_json_output(self, mock_load, mock_check, capsys):
        mock_load.return_value = [_dl(deadline="2026-03-10")]
        mock_check.return_value = {
            "overdue": [{"id": "DL-1", "name": "Tax", "days_left": -8,
                         "action": "File", "deadline": "2026-03-10",
                         "deadline_date": date(2026, 3, 10)}],
            "urgent": [],
            "upcoming": [],
        }
        with patch.object(sys, "argv", ["deadline_watch.py", "--json"]):
            with pytest.raises(SystemExit):
                dw.main()
            out = capsys.readouterr().out
            data = json.loads(out)
            assert "overdue" in data
            assert len(data["overdue"]) == 1
