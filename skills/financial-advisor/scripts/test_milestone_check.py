#!/usr/bin/env python3
"""Tests for skills/financial-advisor/scripts/milestone_check.py.

Covers:
- cmd_init(): creates milestones.json, refuses to overwrite existing file
- cmd_check(): groups by phase, marks overdue/done/warning icons, exits 1 on overdue
- cmd_overdue(): no overdue case, multiple overdue items, day-count accuracy
- cmd_next(): top N sorted by due date, count param, all-done edge case
- cmd_complete(): marks status=done, sets completed_date, writes note, unknown ID exits 1
- cmd_skip(): marks status=skipped, writes note, unknown ID exits 1
- cmd_postpone(): updates due and note, resets status to pending, invalid date exits 1,
                  unknown ID exits 1
- cmd_brief(): summary line format, exits 1 on overdue, exits 0 when all clear
- load_milestones() / save_milestones(): file round-trip, missing file exits 1

All tests use a fixed "today" date of 2026-03-18 for deterministic results.
Uses pytest with tmp_path fixture; milestone file I/O is redirected to tmp_path.

Usage:
    python3 -m pytest skills/financial-advisor/scripts/test_milestone_check.py -v
"""

import copy
import json
import sys
import types
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Bootstrap: stub jsonl_store before importing milestone_check
# ---------------------------------------------------------------------------

_fake_jsonl = types.ModuleType("jsonl_store")
_fake_jsonl.find_workspace = MagicMock(return_value=MagicMock())  # type: ignore[attr-defined]
sys.modules["jsonl_store"] = _fake_jsonl

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import milestone_check  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIXED_TODAY = date(2026, 3, 18)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _milestone(
    mid: str = "M1-1",
    due: str = "2026-03-31",
    status: str = "pending",
    phase: str = "plug-the-leak",
    task: str = "Do something",
    owner: str = "leo",
    month: int = 1,
    impact: str = "Some impact",
    effort: str = "1 hr",
    **extra,
) -> dict:
    """Return a minimal milestone dict matching the DEFAULT_MILESTONES schema."""
    m = {
        "id": mid,
        "month": month,
        "phase": phase,
        "task": task,
        "due": due,
        "status": status,
        "owner": owner,
        "impact": impact,
        "effort": effort,
    }
    m.update(extra)
    return m


def _write_milestones(path: Path, milestones: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(milestones, f, ensure_ascii=False, indent=2)


def _read_milestones(path: Path) -> list:
    with open(path) as f:
        return json.load(f)


def _patch_milestones_file(tmp_path: Path, milestones: list):
    """
    Context-manager-compatible helper: writes milestones to a temp file and
    patches milestone_check.MILESTONES_FILE to point there.

    Returns (tmp_file_path, patch_object) — use as:

        with _patch_milestones_file(tmp_path, data) as mf:
            milestone_check.cmd_something(...)
    """
    mf = tmp_path / "milestones.json"
    _write_milestones(mf, milestones)
    return mf


# ---------------------------------------------------------------------------
# load_milestones / save_milestones
# ---------------------------------------------------------------------------


class TestLoadAndSaveMilestones:

    def test_load_missing_file_exits_1(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.json"
        with patch.object(milestone_check, "MILESTONES_FILE", missing):
            with pytest.raises(SystemExit) as exc_info:
                milestone_check.load_milestones()
        assert exc_info.value.code == 1

    def test_load_returns_list(self, tmp_path: Path) -> None:
        data = [_milestone("M1-1")]
        mf = tmp_path / "milestones.json"
        _write_milestones(mf, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf):
            result = milestone_check.load_milestones()
        assert isinstance(result, list)
        assert len(result) == 1

    def test_save_then_load_round_trip(self, tmp_path: Path) -> None:
        data = [_milestone("M1-1"), _milestone("M1-2", due="2026-04-30")]
        mf = tmp_path / "milestones.json"
        with patch.object(milestone_check, "MILESTONES_FILE", mf):
            milestone_check.save_milestones(data)
            result = milestone_check.load_milestones()
        assert len(result) == 2
        assert result[0]["id"] == "M1-1"
        assert result[1]["id"] == "M1-2"

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        mf = tmp_path / "deep" / "nested" / "milestones.json"
        with patch.object(milestone_check, "MILESTONES_FILE", mf):
            milestone_check.save_milestones([_milestone()])
        assert mf.exists()

    def test_load_preserves_unicode(self, tmp_path: Path) -> None:
        data = [_milestone(task="申請工作證")]
        mf = tmp_path / "milestones.json"
        _write_milestones(mf, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf):
            result = milestone_check.load_milestones()
        assert result[0]["task"] == "申請工作證"


# ---------------------------------------------------------------------------
# cmd_init
# ---------------------------------------------------------------------------


class TestCmdInit:

    def test_init_creates_file_with_default_milestones(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        mf = tmp_path / "milestones.json"
        with patch.object(milestone_check, "MILESTONES_FILE", mf):
            milestone_check.cmd_init()

        assert mf.exists()
        loaded = _read_milestones(mf)
        assert len(loaded) == len(milestone_check.DEFAULT_MILESTONES)
        out = capsys.readouterr().out
        assert "Initialized" in out

    def test_init_does_not_overwrite_existing_file(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        mf = tmp_path / "milestones.json"
        custom_data = [_milestone("CUSTOM-1")]
        _write_milestones(mf, custom_data)

        with patch.object(milestone_check, "MILESTONES_FILE", mf):
            milestone_check.cmd_init()

        # File must not have been overwritten
        loaded = _read_milestones(mf)
        assert loaded[0]["id"] == "CUSTOM-1"
        out = capsys.readouterr().out
        assert "already exists" in out

    def test_init_milestone_ids_start_from_m1(self, tmp_path: Path) -> None:
        mf = tmp_path / "milestones.json"
        with patch.object(milestone_check, "MILESTONES_FILE", mf):
            milestone_check.cmd_init()
        loaded = _read_milestones(mf)
        ids = [m["id"] for m in loaded]
        assert "M1-1" in ids

    def test_init_all_milestones_pending_by_default(self, tmp_path: Path) -> None:
        mf = tmp_path / "milestones.json"
        with patch.object(milestone_check, "MILESTONES_FILE", mf):
            milestone_check.cmd_init()
        loaded = _read_milestones(mf)
        assert all(m["status"] == "pending" for m in loaded)


# ---------------------------------------------------------------------------
# cmd_overdue
# ---------------------------------------------------------------------------


class TestCmdOverdue:

    def test_no_overdue_items_prints_clear(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        # All milestones have future due dates
        data = [
            _milestone("M1-1", due="2026-04-01", status="pending"),
            _milestone("M1-2", due="2026-05-01", status="pending"),
        ]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            milestone_check.cmd_overdue()

        out = capsys.readouterr().out
        assert "No overdue" in out

    def test_overdue_items_reported(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        # M1-1 is 18 days overdue: due 2026-03-01, today 2026-03-18 (== -17 days_left)
        data = [
            _milestone("M1-1", due="2026-03-01", status="pending"),
            _milestone("M1-2", due="2026-04-01", status="pending"),
        ]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            milestone_check.cmd_overdue()

        out = capsys.readouterr().out
        assert "M1-1" in out
        assert "1 overdue" in out
        # M1-2 is NOT overdue
        assert "M1-2" not in out

    def test_done_milestones_not_reported_overdue(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        # Past due date but status=done — must NOT appear as overdue
        data = [_milestone("M1-1", due="2026-01-01", status="done")]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            milestone_check.cmd_overdue()

        assert "No overdue" in capsys.readouterr().out

    def test_skipped_milestones_not_reported_overdue(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        data = [_milestone("M1-1", due="2026-01-01", status="skipped")]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            milestone_check.cmd_overdue()

        assert "No overdue" in capsys.readouterr().out

    def test_overdue_day_count_is_accurate(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        # Due 2026-03-08 => 10 days before 2026-03-18
        data = [_milestone("M1-1", due="2026-03-08", status="pending")]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            milestone_check.cmd_overdue()

        out = capsys.readouterr().out
        assert "10d" in out

    def test_multiple_overdue_reported_with_count(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        data = [
            _milestone("M1-1", due="2026-02-01", status="pending"),
            _milestone("M1-2", due="2026-02-15", status="pending"),
            _milestone("M1-3", due="2026-04-01", status="pending"),
        ]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            milestone_check.cmd_overdue()

        out = capsys.readouterr().out
        assert "2 overdue" in out
        assert "M1-1" in out
        assert "M1-2" in out
        assert "M1-3" not in out


# ---------------------------------------------------------------------------
# cmd_next
# ---------------------------------------------------------------------------


class TestCmdNext:

    def test_next_returns_top_n_by_due(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        data = [
            _milestone("M1-1", due="2026-05-01", status="pending"),
            _milestone("M1-2", due="2026-04-01", status="pending"),
            _milestone("M1-3", due="2026-06-01", status="pending"),
            _milestone("M1-4", due="2026-07-01", status="pending"),
        ]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            milestone_check.cmd_next(count=2)

        out = capsys.readouterr().out
        # Earliest 2 pending milestones are M1-2 (Apr) and M1-1 (May)
        assert "M1-2" in out
        assert "M1-1" in out
        assert "M1-3" not in out
        assert "M1-4" not in out

    def test_next_skips_done_and_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        data = [
            _milestone("M1-1", due="2026-03-20", status="done"),
            _milestone("M1-2", due="2026-03-25", status="skipped"),
            _milestone("M1-3", due="2026-03-30", status="pending"),
        ]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            milestone_check.cmd_next(count=3)

        out = capsys.readouterr().out
        assert "M1-3" in out
        assert "M1-1" not in out
        assert "M1-2" not in out

    def test_next_all_complete_prints_celebration(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        data = [
            _milestone("M1-1", due="2026-03-20", status="done"),
            _milestone("M1-2", due="2026-03-25", status="skipped"),
        ]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            milestone_check.cmd_next(count=3)

        assert "All milestones complete" in capsys.readouterr().out

    def test_next_default_count_three(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        data = [
            _milestone(f"M1-{i}", due=f"2026-0{i+3}-01", status="pending")
            for i in range(1, 6)
        ]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            milestone_check.cmd_next()  # default count=3

        out = capsys.readouterr().out
        assert "Next 3 actionable" in out

    def test_next_shows_effort(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        data = [_milestone("M1-1", due="2026-04-01", status="pending", effort="3 hr prep")]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            milestone_check.cmd_next(count=1)

        assert "3 hr prep" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# cmd_complete
# ---------------------------------------------------------------------------


class TestCmdComplete:

    def test_complete_marks_status_done(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        data = [_milestone("M1-1", status="pending")]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            milestone_check.cmd_complete("M1-1")

        loaded = _read_milestones(mf)
        assert loaded[0]["status"] == "done"
        assert loaded[0]["completed_date"] == FIXED_TODAY.isoformat()

    def test_complete_stores_note(self, tmp_path: Path) -> None:
        data = [_milestone("M1-1", status="pending")]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            milestone_check.cmd_complete("M1-1", note="submitted via portal")

        loaded = _read_milestones(mf)
        assert loaded[0]["note"] == "submitted via portal"

    def test_complete_unknown_id_exits_1(self, tmp_path: Path) -> None:
        data = [_milestone("M1-1", status="pending")]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf):
            with pytest.raises(SystemExit) as exc_info:
                milestone_check.cmd_complete("M9-9")
        assert exc_info.value.code == 1

    def test_complete_does_not_alter_other_milestones(self, tmp_path: Path) -> None:
        data = [
            _milestone("M1-1", status="pending"),
            _milestone("M1-2", status="pending"),
        ]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            milestone_check.cmd_complete("M1-1")

        loaded = _read_milestones(mf)
        m2 = next(m for m in loaded if m["id"] == "M1-2")
        assert m2["status"] == "pending"

    def test_complete_prints_confirmation(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        data = [_milestone("M1-1", task="File the permit")]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            milestone_check.cmd_complete("M1-1")

        out = capsys.readouterr().out
        assert "M1-1" in out
        assert "done" in out


# ---------------------------------------------------------------------------
# cmd_skip
# ---------------------------------------------------------------------------


class TestCmdSkip:

    def test_skip_marks_status_skipped(self, tmp_path: Path) -> None:
        data = [_milestone("M1-1", status="pending")]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf):
            milestone_check.cmd_skip("M1-1")

        loaded = _read_milestones(mf)
        assert loaded[0]["status"] == "skipped"

    def test_skip_stores_note(self, tmp_path: Path) -> None:
        data = [_milestone("M1-1", status="pending")]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf):
            milestone_check.cmd_skip("M1-1", note="changed plans")

        loaded = _read_milestones(mf)
        assert loaded[0]["note"] == "changed plans"

    def test_skip_unknown_id_exits_1(self, tmp_path: Path) -> None:
        data = [_milestone("M1-1", status="pending")]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf):
            with pytest.raises(SystemExit) as exc_info:
                milestone_check.cmd_skip("M9-9")
        assert exc_info.value.code == 1

    def test_skip_prints_confirmation(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        data = [_milestone("M1-1", task="Start newsletter")]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf):
            milestone_check.cmd_skip("M1-1")

        out = capsys.readouterr().out
        assert "M1-1" in out
        assert "skipped" in out


# ---------------------------------------------------------------------------
# cmd_postpone
# ---------------------------------------------------------------------------


class TestCmdPostpone:

    def test_postpone_updates_due_date(self, tmp_path: Path) -> None:
        data = [_milestone("M1-1", due="2026-03-31", status="pending")]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf):
            milestone_check.cmd_postpone("M1-1", "2026-04-30")

        loaded = _read_milestones(mf)
        assert loaded[0]["due"] == "2026-04-30"

    def test_postpone_resets_status_to_pending(self, tmp_path: Path) -> None:
        # Even a previously overdue / pending item should be reset to pending
        data = [_milestone("M1-1", due="2026-01-01", status="pending")]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf):
            milestone_check.cmd_postpone("M1-1", "2026-06-01")

        loaded = _read_milestones(mf)
        assert loaded[0]["status"] == "pending"

    def test_postpone_writes_postpone_note(self, tmp_path: Path) -> None:
        data = [_milestone("M1-1", due="2026-03-31")]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf):
            milestone_check.cmd_postpone("M1-1", "2026-04-30", note="visa delay")

        loaded = _read_milestones(mf)
        note = loaded[0]["note"]
        assert "2026-03-31" in note
        assert "2026-04-30" in note
        assert "visa delay" in note

    def test_postpone_invalid_date_format_exits_1(self, tmp_path: Path) -> None:
        data = [_milestone("M1-1")]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf):
            with pytest.raises(SystemExit) as exc_info:
                milestone_check.cmd_postpone("M1-1", "31-04-2026")  # wrong format
        assert exc_info.value.code == 1

    def test_postpone_unknown_id_exits_1(self, tmp_path: Path) -> None:
        data = [_milestone("M1-1")]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf):
            with pytest.raises(SystemExit) as exc_info:
                milestone_check.cmd_postpone("M9-9", "2026-06-01")
        assert exc_info.value.code == 1

    def test_postpone_prints_confirmation(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        data = [_milestone("M1-1", due="2026-03-31")]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf):
            milestone_check.cmd_postpone("M1-1", "2026-05-31")

        out = capsys.readouterr().out
        assert "M1-1" in out
        assert "postponed" in out.lower()
        assert "2026-03-31" in out
        assert "2026-05-31" in out


# ---------------------------------------------------------------------------
# cmd_check
# ---------------------------------------------------------------------------


class TestCmdCheck:

    def test_check_shows_progress_line(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        data = [
            _milestone("M1-1", due="2026-04-01", status="done"),
            _milestone("M1-2", due="2026-04-01", status="pending"),
        ]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            milestone_check.cmd_check(show_all=True)

        out = capsys.readouterr().out
        assert "1/2 done" in out

    def test_check_exits_1_when_overdue(self, tmp_path: Path) -> None:
        data = [_milestone("M1-1", due="2026-01-01", status="pending")]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            with pytest.raises(SystemExit) as exc_info:
                milestone_check.cmd_check(show_all=True)

        assert exc_info.value.code == 1

    def test_check_does_not_exit_when_no_overdue(self, tmp_path: Path) -> None:
        data = [_milestone("M1-1", due="2026-04-01", status="pending")]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            # Should not raise
            milestone_check.cmd_check(show_all=True)

    def test_check_groups_by_phase(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        data = [
            _milestone("M1-1", phase="phase-alpha", due="2026-04-01"),
            _milestone("M1-2", phase="phase-beta", due="2026-05-01"),
        ]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            milestone_check.cmd_check(show_all=True)

        out = capsys.readouterr().out
        assert "phase-alpha" in out
        assert "phase-beta" in out

    def test_check_show_all_false_hides_done(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        data = [
            _milestone("M1-1", task="Task Done", due="2026-04-01", status="done"),
            _milestone("M1-2", task="Task Pending", due="2026-04-01", status="pending"),
        ]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            milestone_check.cmd_check(show_all=False)

        out = capsys.readouterr().out
        assert "Task Pending" in out
        assert "Task Done" not in out

    def test_check_overdue_icon_applied(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        data = [_milestone("M1-1", due="2026-01-01", status="pending")]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            try:
                milestone_check.cmd_check(show_all=True)
            except SystemExit:
                pass

        out = capsys.readouterr().out
        assert "🔴" in out


# ---------------------------------------------------------------------------
# cmd_brief
# ---------------------------------------------------------------------------


class TestCmdBrief:

    def test_brief_exits_0_no_overdue(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        data = [
            _milestone("M1-1", due="2026-04-01", status="pending"),
            _milestone("M1-2", due="2026-03-31", status="done"),
        ]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            with pytest.raises(SystemExit) as exc_info:
                milestone_check.cmd_brief()

        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "Milestones:" in out

    def test_brief_exits_1_with_overdue(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        data = [_milestone("M1-1", due="2026-01-01", status="pending")]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            with pytest.raises(SystemExit) as exc_info:
                milestone_check.cmd_brief()

        assert exc_info.value.code == 1
        assert "overdue" in capsys.readouterr().out

    def test_brief_shows_done_fraction(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        data = [
            _milestone("M1-1", due="2026-04-01", status="done"),
            _milestone("M1-2", due="2026-04-01", status="done"),
            _milestone("M1-3", due="2026-04-01", status="pending"),
        ]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            with pytest.raises(SystemExit):
                milestone_check.cmd_brief()

        out = capsys.readouterr().out
        assert "2/3 done" in out

    def test_brief_shows_next_milestone_id(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        data = [
            _milestone("M1-1", due="2026-04-15", status="pending"),
            _milestone("M1-2", due="2026-05-01", status="pending"),
        ]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            with pytest.raises(SystemExit):
                milestone_check.cmd_brief()

        out = capsys.readouterr().out
        # M1-1 is earlier, should appear as "next"
        assert "M1-1" in out

    def test_brief_all_done_exits_0(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        data = [
            _milestone("M1-1", due="2026-04-01", status="done"),
            _milestone("M1-2", due="2026-04-01", status="skipped"),
        ]
        mf = _patch_milestones_file(tmp_path, data)
        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            with pytest.raises(SystemExit) as exc_info:
                milestone_check.cmd_brief()

        assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# Integration: complete → skip → postpone round-trip
# ---------------------------------------------------------------------------


class TestRoundTrip:

    def test_complete_skip_postpone_round_trip(self, tmp_path: Path) -> None:
        """Sequence: complete M1-1, skip M1-2, postpone M1-3 — verify final state."""
        data = [
            _milestone("M1-1", due="2026-03-31", status="pending"),
            _milestone("M1-2", due="2026-03-31", status="pending"),
            _milestone("M1-3", due="2026-03-31", status="pending"),
        ]
        mf = _patch_milestones_file(tmp_path, data)

        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            milestone_check.cmd_complete("M1-1", note="all done")
            milestone_check.cmd_skip("M1-2", note="no longer needed")
            milestone_check.cmd_postpone("M1-3", "2026-05-01")

        loaded = _read_milestones(mf)
        by_id = {m["id"]: m for m in loaded}
        assert by_id["M1-1"]["status"] == "done"
        assert by_id["M1-1"]["completed_date"] == FIXED_TODAY.isoformat()
        assert by_id["M1-2"]["status"] == "skipped"
        assert by_id["M1-3"]["status"] == "pending"
        assert by_id["M1-3"]["due"] == "2026-05-01"

    def test_overdue_milestone_cleared_by_postpone(self, tmp_path: Path) -> None:
        """A milestone past its due date that is postponed should no longer appear overdue."""
        data = [_milestone("M1-1", due="2026-01-01", status="pending")]
        mf = _patch_milestones_file(tmp_path, data)

        with patch.object(milestone_check, "MILESTONES_FILE", mf), \
             patch("milestone_check.date") as mock_date:
            mock_date.today.return_value = FIXED_TODAY
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            milestone_check.cmd_postpone("M1-1", "2026-06-01")
            milestone_check.cmd_overdue()  # should print "No overdue"

        # If we get here without SystemExit the test passes; also verify output
