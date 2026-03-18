"""Tests for finance_snapshot.py — financial snapshot manager."""

import sys
import types
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub jsonl_store into sys.modules BEFORE importing finance_snapshot so the
# top-level "from jsonl_store import …" inside the source module resolves to
# our fake objects rather than the real (possibly absent) library.
# ---------------------------------------------------------------------------
_fake_jsonl_store_module = types.ModuleType("jsonl_store")
_fake_jsonl_store_module.JsonlStore = MagicMock()  # type: ignore[attr-defined]
_fake_jsonl_store_module.find_workspace = MagicMock(return_value=MagicMock())  # type: ignore[attr-defined]
sys.modules["jsonl_store"] = _fake_jsonl_store_module

# Insert the scripts directory so the import resolves without relying on the
# real sys.path manipulation inside finance_snapshot.py.
_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import finance_snapshot  # noqa: E402  (must come after sys.modules patch)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_store(items: list) -> MagicMock:
    """Return a MagicMock that behaves like a JsonlStore with the given items."""
    store = MagicMock()
    store.load.return_value = items
    store.append.side_effect = lambda entry: {**entry, "id": "SNAP-0001"}
    return store


def _snapshot(
    snap_date: str = "2026-01-01",
    savings: float = 300_000,
    income: float = 50_000,
    expenses: float = 40_000,
    net: float | None = None,
) -> dict:
    effective_net = net if net is not None else income - expenses
    return {
        "date": snap_date,
        "savings": savings,
        "monthly_income": income,
        "monthly_expenses": expenses,
        "net": effective_net,
    }


# ---------------------------------------------------------------------------
# cmd_latest
# ---------------------------------------------------------------------------


class TestCmdLatest:
    def test_no_snapshots_prints_prompt(self, capsys: pytest.CaptureFixture) -> None:
        store = _make_store([])
        with patch("finance_snapshot.get_snapshots", return_value=store):
            finance_snapshot.cmd_latest()

        out = capsys.readouterr().out
        assert "No snapshots recorded yet." in out
        assert "--record" in out

    def test_single_snapshot_positive_net(self, capsys: pytest.CaptureFixture) -> None:
        snap = _snapshot("2026-03-01", savings=200_000, income=60_000, expenses=40_000)
        store = _make_store([snap])
        with patch("finance_snapshot.get_snapshots", return_value=store):
            finance_snapshot.cmd_latest()

        out = capsys.readouterr().out
        assert "2026-03-01" in out
        assert "200,000" in out
        assert "60,000" in out
        assert "40,000" in out
        # Positive net shows green indicator
        assert "🟢" in out
        # No runway line for positive net
        assert "Runway" not in out
        # No comparison line when there is only one snapshot
        assert "vs " not in out

    def test_single_snapshot_negative_net_shows_runway(self, capsys: pytest.CaptureFixture) -> None:
        # savings=100_000, income=20_000, expenses=30_000 => net=-10_000, runway=10 months
        snap = _snapshot("2026-03-01", savings=100_000, income=20_000, expenses=30_000)
        store = _make_store([snap])
        with patch("finance_snapshot.get_snapshots", return_value=store):
            finance_snapshot.cmd_latest()

        out = capsys.readouterr().out
        assert "🔴" in out
        assert "Runway" in out
        assert "10" in out  # 100_000 / 10_000 = 10

    def test_two_snapshots_shows_delta_positive(self, capsys: pytest.CaptureFixture) -> None:
        prev = _snapshot("2026-02-01", savings=200_000)
        latest = _snapshot("2026-03-01", savings=220_000)
        store = _make_store([prev, latest])
        with patch("finance_snapshot.get_snapshots", return_value=store):
            finance_snapshot.cmd_latest()

        out = capsys.readouterr().out
        assert "vs 2026-02-01" in out
        assert "📈" in out
        assert "+20,000" in out

    def test_two_snapshots_shows_delta_negative(self, capsys: pytest.CaptureFixture) -> None:
        prev = _snapshot("2026-02-01", savings=220_000)
        latest = _snapshot("2026-03-01", savings=200_000)
        store = _make_store([prev, latest])
        with patch("finance_snapshot.get_snapshots", return_value=store):
            finance_snapshot.cmd_latest()

        out = capsys.readouterr().out
        assert "vs 2026-02-01" in out
        assert "📉" in out
        assert "-20,000" in out


# ---------------------------------------------------------------------------
# cmd_record
# ---------------------------------------------------------------------------


class TestCmdRecord:
    def test_positive_net_no_runway_line(self, capsys: pytest.CaptureFixture) -> None:
        store = MagicMock()
        store.append.return_value = {"id": "SNAP-0042"}
        with patch("finance_snapshot.get_snapshots", return_value=store):
            finance_snapshot.cmd_record(savings=300_000, income=50_000, expenses=40_000)

        out = capsys.readouterr().out
        assert "SNAP-0042" in out
        assert "300,000" in out
        assert "+10,000" in out
        assert "Runway" not in out

    def test_negative_net_prints_runway(self, capsys: pytest.CaptureFixture) -> None:
        store = _make_store([])
        store.append.return_value = {"id": "SNAP-0043"}
        # savings=150_000, expenses > income => runway = 150_000 / 10_000 = 15 months
        with patch("finance_snapshot.get_snapshots", return_value=store):
            finance_snapshot.cmd_record(savings=150_000, income=20_000, expenses=30_000)

        out = capsys.readouterr().out
        assert "Runway" in out
        assert "15" in out

    def test_note_is_stored(self, capsys: pytest.CaptureFixture) -> None:
        captured_entry: dict = {}

        def capture_append(entry: dict) -> dict:
            captured_entry.update(entry)
            return {"id": "SNAP-0044"}

        store = MagicMock()
        store.append.side_effect = capture_append
        with patch("finance_snapshot.get_snapshots", return_value=store):
            finance_snapshot.cmd_record(
                savings=100_000, income=50_000, expenses=40_000, note="bonus month"
            )

        assert captured_entry.get("note") == "bonus month"

    def test_record_appends_correct_fields(self, capsys: pytest.CaptureFixture) -> None:
        captured_entry: dict = {}

        def capture_append(entry: dict) -> dict:
            captured_entry.update(entry)
            return {"id": "SNAP-0045"}

        store = MagicMock()
        store.append.side_effect = capture_append
        with patch("finance_snapshot.get_snapshots", return_value=store):
            finance_snapshot.cmd_record(savings=200_000, income=60_000, expenses=45_000)

        assert captured_entry["savings"] == 200_000
        assert captured_entry["monthly_income"] == 60_000
        assert captured_entry["monthly_expenses"] == 45_000
        assert captured_entry["net"] == 15_000
        assert captured_entry["runway_months"] is None  # positive net


# ---------------------------------------------------------------------------
# cmd_check_stale
# ---------------------------------------------------------------------------


class TestCmdCheckStale:
    def test_no_snapshots_exits_2(self) -> None:
        store = _make_store([])
        with patch("finance_snapshot.get_snapshots", return_value=store):
            with pytest.raises(SystemExit) as exc_info:
                finance_snapshot.cmd_check_stale()
        assert exc_info.value.code == 2

    def test_stale_snapshot_exits_1(self, capsys: pytest.CaptureFixture) -> None:
        # age > 45 days from today (2026-03-18)
        snap = _snapshot("2026-01-01")  # 76 days before 2026-03-18
        store = _make_store([snap])
        with patch("finance_snapshot.get_snapshots", return_value=store):
            with patch("finance_snapshot.date") as mock_date:
                mock_date.today.return_value = date(2026, 3, 18)
                mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
                with pytest.raises(SystemExit) as exc_info:
                    finance_snapshot.cmd_check_stale(max_age=45)

        out = capsys.readouterr().out
        assert "🔴" in out
        assert exc_info.value.code == 1

    def test_warning_zone_exits_0(self, capsys: pytest.CaptureFixture) -> None:
        # age > 45 * 0.7 = 31.5 but <= 45 => warning zone
        # today=2026-03-18, snapshot date 35 days prior = 2026-02-11
        snap = _snapshot("2026-02-11")
        store = _make_store([snap])
        with patch("finance_snapshot.get_snapshots", return_value=store):
            with patch("finance_snapshot.date") as mock_date:
                mock_date.today.return_value = date(2026, 3, 18)
                mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
                with pytest.raises(SystemExit) as exc_info:
                    finance_snapshot.cmd_check_stale(max_age=45)

        out = capsys.readouterr().out
        assert "⚠️" in out
        assert exc_info.value.code == 0

    def test_fresh_snapshot_exits_0(self, capsys: pytest.CaptureFixture) -> None:
        # age <= 31 days => fresh
        snap = _snapshot("2026-03-10")
        store = _make_store([snap])
        with patch("finance_snapshot.get_snapshots", return_value=store):
            with patch("finance_snapshot.date") as mock_date:
                mock_date.today.return_value = date(2026, 3, 18)
                mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
                with pytest.raises(SystemExit) as exc_info:
                    finance_snapshot.cmd_check_stale(max_age=45)

        out = capsys.readouterr().out
        assert "✅" in out
        assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# cmd_log_income
# ---------------------------------------------------------------------------


class TestCmdLogIncome:
    def test_basic_income_log(self, capsys: pytest.CaptureFixture) -> None:
        store = MagicMock()
        store.append.return_value = {"id": "INC-0001"}
        with patch("finance_snapshot.get_income_log", return_value=store):
            finance_snapshot.cmd_log_income(source="tutoring", amount=4800.0)

        out = capsys.readouterr().out
        assert "INC-0001" in out
        assert "tutoring" in out
        assert "4,800" in out

    def test_income_log_with_note_stored(self) -> None:
        captured: dict = {}

        def capture_append(entry: dict) -> dict:
            captured.update(entry)
            return {"id": "INC-0002"}

        store = MagicMock()
        store.append.side_effect = capture_append
        with patch("finance_snapshot.get_income_log", return_value=store):
            finance_snapshot.cmd_log_income(source="freelance", amount=10_000.0, note="two projects")

        assert captured.get("note") == "two projects"

    def test_income_log_custom_date(self, capsys: pytest.CaptureFixture) -> None:
        captured: dict = {}

        def capture_append(entry: dict) -> dict:
            captured.update(entry)
            return {"id": "INC-0003"}

        store = MagicMock()
        store.append.side_effect = capture_append
        with patch("finance_snapshot.get_income_log", return_value=store):
            finance_snapshot.cmd_log_income(
                source="consulting", amount=15_000.0, log_date="2026-03-10"
            )

        assert captured["date"] == "2026-03-10"
        assert "2026-03-10" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# cmd_log_expense
# ---------------------------------------------------------------------------


class TestCmdLogExpense:
    def test_basic_expense_log(self, capsys: pytest.CaptureFixture) -> None:
        store = MagicMock()
        store.append.return_value = {"id": "EXP-0001"}
        with patch("finance_snapshot.get_expense_log", return_value=store):
            finance_snapshot.cmd_log_expense(source="rent", amount=18_000.0)

        out = capsys.readouterr().out
        assert "EXP-0001" in out
        assert "rent" in out
        assert "18,000" in out

    def test_expense_log_with_note_stored(self) -> None:
        captured: dict = {}

        def capture_append(entry: dict) -> dict:
            captured.update(entry)
            return {"id": "EXP-0002"}

        store = MagicMock()
        store.append.side_effect = capture_append
        with patch("finance_snapshot.get_expense_log", return_value=store):
            finance_snapshot.cmd_log_expense(
                source="conference", amount=8_000.0, note="Interspeech registration"
            )

        assert captured.get("note") == "Interspeech registration"


# ---------------------------------------------------------------------------
# cmd_income_summary
# ---------------------------------------------------------------------------


class TestCmdIncomeSummary:
    def test_empty_store_prints_prompt(self, capsys: pytest.CaptureFixture) -> None:
        store = _make_store([])
        with patch("finance_snapshot.get_income_log", return_value=store):
            finance_snapshot.cmd_income_summary(months=1)

        out = capsys.readouterr().out
        assert "No income events logged yet." in out

    def test_no_events_in_range_prints_notice(self, capsys: pytest.CaptureFixture) -> None:
        # Item date is far in the past, outside any reasonable 1-month window
        items = [{"date": "2020-01-15", "source": "old job", "amount": 50_000.0}]
        store = _make_store(items)
        with patch("finance_snapshot.get_income_log", return_value=store):
            with patch("finance_snapshot.date") as mock_date:
                mock_date.today.return_value = date(2026, 3, 18)
                mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
                finance_snapshot.cmd_income_summary(months=1)

        out = capsys.readouterr().out
        assert "No income events in the last 1 month(s)." in out

    def test_grouped_by_source_with_total(self, capsys: pytest.CaptureFixture) -> None:
        items = [
            {"date": "2026-03-05", "source": "tutoring", "amount": 4_800.0},
            {"date": "2026-03-10", "source": "tutoring", "amount": 2_400.0},
            {"date": "2026-03-12", "source": "freelance", "amount": 10_000.0},
        ]
        store = _make_store(items)
        with patch("finance_snapshot.get_income_log", return_value=store):
            with patch("finance_snapshot.date") as mock_date:
                mock_date.today.return_value = date(2026, 3, 18)
                mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
                finance_snapshot.cmd_income_summary(months=1)

        out = capsys.readouterr().out
        # freelance (10_000) should appear before tutoring (7_200) due to descending sort
        assert "freelance" in out
        assert "tutoring" in out
        assert "10,000" in out
        assert "7,200" in out
        assert "17,200" in out
        assert "Total" in out


# ---------------------------------------------------------------------------
# cmd_trend
# ---------------------------------------------------------------------------


class TestCmdTrend:
    def test_less_than_two_snapshots_prints_notice(self, capsys: pytest.CaptureFixture) -> None:
        store = _make_store([_snapshot("2026-03-01")])
        with patch("finance_snapshot.get_snapshots", return_value=store):
            finance_snapshot.cmd_trend()

        out = capsys.readouterr().out
        assert "Need at least 2 snapshots" in out

    def test_empty_store_prints_notice(self, capsys: pytest.CaptureFixture) -> None:
        store = _make_store([])
        with patch("finance_snapshot.get_snapshots", return_value=store):
            finance_snapshot.cmd_trend()

        out = capsys.readouterr().out
        assert "Need at least 2 snapshots" in out

    def test_improving_trend(self, capsys: pytest.CaptureFixture) -> None:
        snaps = [
            _snapshot("2026-01-01", savings=200_000),
            _snapshot("2026-02-01", savings=210_000),
            _snapshot("2026-03-01", savings=230_000),
        ]
        store = _make_store(snaps)
        with patch("finance_snapshot.get_snapshots", return_value=store):
            finance_snapshot.cmd_trend(months=6)

        out = capsys.readouterr().out
        assert "improving" in out
        assert "+30,000" in out

    def test_declining_trend(self, capsys: pytest.CaptureFixture) -> None:
        snaps = [
            _snapshot("2026-01-01", savings=230_000),
            _snapshot("2026-02-01", savings=215_000),
            _snapshot("2026-03-01", savings=200_000),
        ]
        store = _make_store(snaps)
        with patch("finance_snapshot.get_snapshots", return_value=store):
            finance_snapshot.cmd_trend(months=6)

        out = capsys.readouterr().out
        assert "declining" in out
        assert "-30,000" in out

    def test_trend_respects_months_limit(self, capsys: pytest.CaptureFixture) -> None:
        # 6 snapshots: 2025-01-01 through 2025-06-01
        # items[-3:] keeps indices 3,4,5 => 2025-04-01, 2025-05-01, 2025-06-01
        # indices 0,1,2 (2025-01-01, 2025-02-01, 2025-03-01) must be absent
        snaps = [_snapshot(f"2025-0{i+1}-01", savings=100_000 + i * 10_000) for i in range(6)]
        store = _make_store(snaps)
        with patch("finance_snapshot.get_snapshots", return_value=store):
            finance_snapshot.cmd_trend(months=3)

        out = capsys.readouterr().out
        # Header says "last 3 snapshots"
        assert "last 3 snapshots" in out
        # First snapshot of the trimmed window is 2025-04-01 (present)
        assert "2025-04-01" in out
        assert "2025-06-01" in out
        # Snapshots before the window must not appear
        assert "2025-03-01" not in out
        assert "2025-01-01" not in out


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_zero_savings_positive_net(self, capsys: pytest.CaptureFixture) -> None:
        snap = _snapshot("2026-03-01", savings=0, income=50_000, expenses=40_000)
        store = _make_store([snap])
        with patch("finance_snapshot.get_snapshots", return_value=store):
            finance_snapshot.cmd_latest()

        out = capsys.readouterr().out
        assert "0" in out
        assert "🟢" in out
        assert "Runway" not in out

    def test_zero_income_zero_expenses_zero_net(self, capsys: pytest.CaptureFixture) -> None:
        # net = 0, runway = inf (treated as positive / infinite)
        snap = _snapshot("2026-03-01", savings=100_000, income=0, expenses=0)
        store = _make_store([snap])
        with patch("finance_snapshot.get_snapshots", return_value=store):
            finance_snapshot.cmd_latest()

        out = capsys.readouterr().out
        assert "🟢" in out
        assert "Runway" not in out

    def test_record_zero_savings_negative_net_runway_stored(self, capsys: pytest.CaptureFixture) -> None:
        """When savings=0 and net<0 the runway is 0 months (0/X), stored as None since not > 0."""
        captured: dict = {}

        def capture_append(entry: dict) -> dict:
            captured.update(entry)
            return {"id": "SNAP-0099"}

        store = MagicMock()
        store.append.side_effect = capture_append
        with patch("finance_snapshot.get_snapshots", return_value=store):
            finance_snapshot.cmd_record(savings=0, income=10_000, expenses=20_000)

        # runway = 0 / 10_000 = 0.0, which is not > 0, so runway_months should be None
        assert captured["runway_months"] is None

    def test_cmd_log_income_no_note_key_absent(self) -> None:
        """When no note is given, the entry dict must not contain a 'note' key."""
        captured: dict = {}

        def capture_append(entry: dict) -> dict:
            captured.update(entry)
            return {"id": "INC-0010"}

        store = MagicMock()
        store.append.side_effect = capture_append
        with patch("finance_snapshot.get_income_log", return_value=store):
            finance_snapshot.cmd_log_income(source="salary", amount=60_000.0)

        assert "note" not in captured
