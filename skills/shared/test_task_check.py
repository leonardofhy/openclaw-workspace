"""Unit tests for task-check.py — task board staleness checker."""

import importlib
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

# task-check.py has a hyphen, so use importlib
_task_check_path = Path(__file__).resolve().parent.parent / "task-check.py"
spec = importlib.util.spec_from_file_location("task_check", _task_check_path)
tc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tc)


# ---------------------------------------------------------------------------
# Sample task board markdown
# ---------------------------------------------------------------------------

SAMPLE_BOARD = """\
# Task Board

## ACTIVE
### M-001 | Fix login bug
- **priority**: high
- **last_touched**: 2026-03-10
- **deadline**: 2026-03-20

### L-001 | Setup CI pipeline
- **priority**: medium
- **last_touched**: 2026-03-17

## WAITING
### M-002 | Waiting for API key
- **priority**: low
- **last_touched**: 2026-03-01

## BLOCKED
### M-003 | Blocked by upstream
- **priority**: high
- **last_touched**: 2026-03-15

## DONE
### M-004 | Completed task
- **priority**: low
- **last_touched**: 2026-03-10
"""

EMPTY_BOARD = """\
# Task Board

## ACTIVE

## WAITING

## DONE
"""


# ===========================================================================
# parse_tasks()
# ===========================================================================

class TestParseTasks:
    def test_parses_all_sections(self):
        tasks = tc.parse_tasks(SAMPLE_BOARD)
        statuses = {t["status"] for t in tasks}
        assert "ACTIVE" in statuses
        assert "WAITING" in statuses
        assert "BLOCKED" in statuses
        assert "DONE" in statuses

    def test_correct_task_count(self):
        tasks = tc.parse_tasks(SAMPLE_BOARD)
        assert len(tasks) == 5

    def test_task_id_and_title_parsed(self):
        tasks = tc.parse_tasks(SAMPLE_BOARD)
        m001 = next(t for t in tasks if t["id"] == "M-001")
        assert m001["title"] == "Fix login bug"

    def test_owner_mac_from_m_prefix(self):
        tasks = tc.parse_tasks(SAMPLE_BOARD)
        m001 = next(t for t in tasks if t["id"] == "M-001")
        assert m001["owner"] == "mac"

    def test_owner_lab_from_l_prefix(self):
        tasks = tc.parse_tasks(SAMPLE_BOARD)
        l001 = next(t for t in tasks if t["id"] == "L-001")
        assert l001["owner"] == "lab"

    def test_last_touched_parsed_as_date(self):
        tasks = tc.parse_tasks(SAMPLE_BOARD)
        m001 = next(t for t in tasks if t["id"] == "M-001")
        assert m001["last_touched"] == date(2026, 3, 10)

    def test_deadline_parsed_as_date(self):
        tasks = tc.parse_tasks(SAMPLE_BOARD)
        m001 = next(t for t in tasks if t["id"] == "M-001")
        assert m001["deadline"] == date(2026, 3, 20)

    def test_priority_parsed(self):
        tasks = tc.parse_tasks(SAMPLE_BOARD)
        m001 = next(t for t in tasks if t["id"] == "M-001")
        assert m001["priority"] == "high"

    def test_empty_board_returns_no_tasks(self):
        tasks = tc.parse_tasks(EMPTY_BOARD)
        assert tasks == []

    def test_task_without_deadline_has_none(self):
        tasks = tc.parse_tasks(SAMPLE_BOARD)
        l001 = next(t for t in tasks if t["id"] == "L-001")
        assert l001["deadline"] is None


# ===========================================================================
# detect_owner()
# ===========================================================================

class TestDetectOwner:
    @patch.dict("os.environ", {"TASK_CHECK_OWNER": "lab"}, clear=False)
    def test_env_task_check_owner(self):
        assert tc.detect_owner() == "lab"

    @patch.dict("os.environ", {"TASK_CHECK_OWNER": "", "TASK_OWNER": "all"}, clear=False)
    def test_env_task_owner_fallback(self):
        assert tc.detect_owner() == "all"

    @patch.dict("os.environ", {"TASK_CHECK_OWNER": "", "TASK_OWNER": ""}, clear=False)
    @patch("platform.system", return_value="Darwin")
    def test_darwin_returns_mac(self, mock_plat):
        assert tc.detect_owner() == "mac"

    @patch.dict("os.environ", {"TASK_CHECK_OWNER": "", "TASK_OWNER": ""}, clear=False)
    @patch("platform.system", return_value="Linux")
    @patch("socket.gethostname", return_value="lab-desktop-001")
    def test_linux_hostname_returns_lab(self, mock_host, mock_plat):
        assert tc.detect_owner() == "lab"


# ===========================================================================
# in_scope()
# ===========================================================================

class TestInScope:
    def test_all_scope_matches_everything(self):
        assert tc.in_scope({"owner": "mac"}, "all") is True
        assert tc.in_scope({"owner": "lab"}, "all") is True

    def test_mac_scope_matches_mac(self):
        assert tc.in_scope({"owner": "mac"}, "mac") is True

    def test_mac_scope_rejects_lab(self):
        assert tc.in_scope({"owner": "lab"}, "mac") is False


# ===========================================================================
# check()
# ===========================================================================

class TestCheck:
    def test_stale_active_task_flagged(self):
        tasks = tc.parse_tasks(SAMPLE_BOARD)
        # M-001 last_touched 2026-03-10, if today is 2026-03-18 → 8 days stale
        alerts = tc.check(tasks, today=date(2026, 3, 18), owner_scope="all")
        stale_alerts = [a for a in alerts if "STALE" in a and "M-001" in a]
        assert len(stale_alerts) == 1

    def test_stale_waiting_task_flagged(self):
        tasks = tc.parse_tasks(SAMPLE_BOARD)
        # M-002 last_touched 2026-03-01, today 2026-03-18 → 17 days
        alerts = tc.check(tasks, today=date(2026, 3, 18), owner_scope="all")
        stale_waiting = [a for a in alerts if "STALE" in a and "M-002" in a]
        assert len(stale_waiting) == 1

    def test_done_tasks_not_flagged(self):
        tasks = tc.parse_tasks(SAMPLE_BOARD)
        alerts = tc.check(tasks, today=date(2026, 3, 18), owner_scope="all")
        done_alerts = [a for a in alerts if "M-004" in a]
        assert len(done_alerts) == 0

    def test_overdue_deadline_flagged(self):
        tasks = tc.parse_tasks(SAMPLE_BOARD)
        # M-001 deadline 2026-03-20, today 2026-03-25 → overdue
        alerts = tc.check(tasks, today=date(2026, 3, 25), owner_scope="all")
        overdue = [a for a in alerts if "OVERDUE" in a and "M-001" in a]
        assert len(overdue) == 1

    def test_deadline_tomorrow_flagged(self):
        tasks = tc.parse_tasks(SAMPLE_BOARD)
        # M-001 deadline 2026-03-20, today 2026-03-19 → 1 day left
        alerts = tc.check(tasks, today=date(2026, 3, 19), owner_scope="all")
        deadline_alerts = [a for a in alerts if "DEADLINE" in a and "M-001" in a]
        assert len(deadline_alerts) == 1

    def test_owner_scope_filters_tasks(self):
        tasks = tc.parse_tasks(SAMPLE_BOARD)
        # Only lab scope — should not see mac tasks
        alerts = tc.check(tasks, today=date(2026, 3, 18), owner_scope="lab")
        mac_alerts = [a for a in alerts if "M-00" in a]
        assert len(mac_alerts) == 0

    def test_active_over_limit_alert(self):
        """More than MAX_ACTIVE active tasks for an owner triggers alert."""
        board = "## ACTIVE\n"
        for i in range(6):
            board += f"### M-{i:03d} | Task {i}\n- **last_touched**: 2026-03-18\n"
        tasks = tc.parse_tasks(board)
        alerts = tc.check(tasks, today=date(2026, 3, 18), owner_scope="mac")
        limit_alerts = [a for a in alerts if "上限" in a]
        assert len(limit_alerts) == 1

    def test_no_alerts_for_healthy_board(self):
        board = """\
## ACTIVE
### M-001 | Fresh task
- **last_touched**: 2026-03-18
"""
        tasks = tc.parse_tasks(board)
        alerts = tc.check(tasks, today=date(2026, 3, 18), owner_scope="all")
        assert alerts == []

    def test_empty_task_list_no_alerts(self):
        alerts = tc.check([], today=date(2026, 3, 18), owner_scope="all")
        assert alerts == []

    def test_all_scope_checks_each_owner_active_limit(self):
        board = "## ACTIVE\n"
        for i in range(6):
            board += f"### M-{i:03d} | Mac task {i}\n- **last_touched**: 2026-03-18\n"
        for i in range(3):
            board += f"### L-{i:03d} | Lab task {i}\n- **last_touched**: 2026-03-18\n"
        tasks = tc.parse_tasks(board)
        alerts = tc.check(tasks, today=date(2026, 3, 18), owner_scope="all")
        # Only mac should trigger (6 > 5), lab is fine (3 < 5)
        limit_alerts = [a for a in alerts if "上限" in a]
        assert len(limit_alerts) == 1
        assert "mac" in limit_alerts[0]


# ===========================================================================
# main()
# ===========================================================================

class TestMain:
    @patch.object(tc, "BOARD")
    def test_missing_board_exits_1(self, mock_board):
        mock_board.exists.return_value = False
        with patch.object(sys, "argv", ["task-check.py"]):
            with pytest.raises(SystemExit) as exc_info:
                tc.main()
            assert exc_info.value.code == 1

    @patch.object(tc, "BOARD")
    def test_missing_board_json_output(self, mock_board, capsys):
        mock_board.exists.return_value = False
        with patch.object(sys, "argv", ["task-check.py", "--json"]):
            with pytest.raises(SystemExit):
                tc.main()
            out = capsys.readouterr().out
            data = json.loads(out)
            assert "error" in data

    @patch.object(tc, "BOARD")
    def test_healthy_board_exits_0(self, mock_board):
        today = date.today()
        mock_board.exists.return_value = True
        mock_board.read_text.return_value = f"""\
## ACTIVE
### M-001 | Fresh task
- **last_touched**: {today.isoformat()}
"""
        with patch.object(sys, "argv", ["task-check.py", "--owner", "all"]):
            with pytest.raises(SystemExit) as exc_info:
                tc.main()
            assert exc_info.value.code == 0
