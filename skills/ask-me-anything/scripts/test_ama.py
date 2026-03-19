"""Tests for ama.py — Ask Me Anything question tracker.

Run with:
    pytest skills/ask-me-anything/scripts/test_ama.py -v
"""

import argparse
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ── import the module under test ──────────────────────────────────────────────

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import ama  # noqa: E402


# ── fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path: Path, monkeypatch):
    """Redirect all file I/O to a temporary directory for every test."""
    data_dir = str(tmp_path / "ama")
    questions_file = str(tmp_path / "ama" / "questions.jsonl")

    monkeypatch.setattr(ama, "DATA_DIR", data_dir)
    monkeypatch.setattr(ama, "QUESTIONS_FILE", questions_file)

    os.makedirs(data_dir, exist_ok=True)
    yield tmp_path


# ── _next_id() ────────────────────────────────────────────────────────────────


class TestNextId:
    def test_empty_rows_returns_q001(self):
        assert ama._next_id([]) == "Q-001"

    def test_increments_from_existing_max(self):
        rows = [{"id": "Q-003"}, {"id": "Q-001"}, {"id": "Q-007"}]
        assert ama._next_id(rows) == "Q-008"

    def test_ignores_non_q_prefixed_ids(self):
        rows = [{"id": "X-100"}, {"id": "Q-002"}]
        assert ama._next_id(rows) == "Q-003"

    def test_handles_missing_id_key(self):
        rows = [{}, {"id": "Q-005"}]
        assert ama._next_id(rows) == "Q-006"

    def test_zero_padded_three_digits(self):
        result = ama._next_id([])
        assert result == "Q-001"
        assert len(result) == 5  # "Q-001"


# ── _priority_emoji() ─────────────────────────────────────────────────────────


class TestPriorityEmoji:
    def test_p1_is_red(self):
        assert ama._priority_emoji(1) == "🔴"

    def test_p2_is_yellow(self):
        assert ama._priority_emoji(2) == "🟡"

    def test_p3_is_green(self):
        assert ama._priority_emoji(3) == "🟢"

    def test_unknown_priority_returns_white(self):
        assert ama._priority_emoji(99) == "⚪"


# ── _load() / _save() ─────────────────────────────────────────────────────────


class TestLoadSave:
    def test_load_empty_when_no_file(self):
        rows = ama._load()
        assert rows == []

    def test_save_and_reload_roundtrip(self):
        original = [
            {"id": "Q-001", "question": "What is Python?", "status": "open"},
            {"id": "Q-002", "question": "Why async?", "status": "answered"},
        ]
        ama._save(original)
        loaded = ama._load()

        assert loaded == original

    def test_save_atomic_write_via_replace(self, tmp_path: Path):
        """Verify the file exists and is valid after save (atomic replace succeeded)."""
        rows = [{"id": "Q-001", "question": "Test", "status": "open"}]
        ama._save(rows)

        assert os.path.exists(ama.QUESTIONS_FILE)
        with open(ama.QUESTIONS_FILE, encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        assert len(lines) == 1
        assert json.loads(lines[0])["id"] == "Q-001"

    def test_load_skips_blank_lines(self, tmp_path: Path):
        path = Path(ama.QUESTIONS_FILE)
        path.write_text(
            '{"id": "Q-001", "question": "a", "status": "open"}\n\n'
            '{"id": "Q-002", "question": "b", "status": "open"}\n',
            encoding="utf-8",
        )

        rows = ama._load()

        assert len(rows) == 2
        assert rows[0]["id"] == "Q-001"
        assert rows[1]["id"] == "Q-002"


# ── cmd_ask() ─────────────────────────────────────────────────────────────────


class TestCmdAsk:
    def _make_args(self, question, context=None, task=None, priority=2):
        args = argparse.Namespace(
            question=question,
            context=context,
            task=task,
            priority=priority,
        )
        return args

    def test_creates_question_entry(self, capsys):
        ama.cmd_ask(self._make_args("What is a generator?"))

        rows = ama._load()
        assert len(rows) == 1
        entry = rows[0]
        assert entry["id"] == "Q-001"
        assert entry["question"] == "What is a generator?"
        assert entry["status"] == "open"
        assert entry["priority"] == 2
        assert entry["answer"] == ""
        assert entry["answered_at"] == ""

    def test_sequential_ids_increment(self, capsys):
        ama.cmd_ask(self._make_args("First question"))
        ama.cmd_ask(self._make_args("Second question"))

        rows = ama._load()
        assert rows[0]["id"] == "Q-001"
        assert rows[1]["id"] == "Q-002"

    def test_context_and_task_stored(self, capsys):
        ama.cmd_ask(self._make_args("Q?", context="some context", task="L-07", priority=1))

        rows = ama._load()
        assert rows[0]["context"] == "some context"
        assert rows[0]["task"] == "L-07"
        assert rows[0]["priority"] == 1

    def test_empty_context_stored_as_empty_string(self, capsys):
        ama.cmd_ask(self._make_args("Q?", context=None))

        rows = ama._load()
        assert rows[0]["context"] == ""

    def test_output_contains_id(self, capsys):
        ama.cmd_ask(self._make_args("Test question?"))

        captured = capsys.readouterr()
        assert "Q-001" in captured.out


# ── cmd_answer() ──────────────────────────────────────────────────────────────


class TestCmdAnswer:
    def _seed_question(self, question="How does GIL work?", priority=2):
        args = argparse.Namespace(question=question, context=None, task=None, priority=priority)
        ama.cmd_ask(args)

    def test_marks_question_as_answered(self, capsys):
        self._seed_question()

        ans_args = argparse.Namespace(question_id="Q-001", answer="GIL serialises threads")
        ama.cmd_answer(ans_args)

        rows = ama._load()
        assert rows[0]["status"] == "answered"
        assert rows[0]["answer"] == "GIL serialises threads"
        assert rows[0]["answered_at"] != ""

    def test_unknown_id_exits_with_error(self, capsys):
        self._seed_question()

        ans_args = argparse.Namespace(question_id="Q-999", answer="irrelevant")
        with pytest.raises(SystemExit) as exc_info:
            ama.cmd_answer(ans_args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Q-999" in captured.err

    def test_other_questions_unaffected(self, capsys):
        self._seed_question("First Q")
        self._seed_question("Second Q")

        ans_args = argparse.Namespace(question_id="Q-001", answer="Answer to first")
        ama.cmd_answer(ans_args)

        rows = ama._load()
        assert rows[0]["status"] == "answered"
        assert rows[1]["status"] == "open"


# ── cmd_list() ────────────────────────────────────────────────────────────────


class TestCmdList:
    def _seed(self, n=3):
        for i in range(n):
            args = argparse.Namespace(
                question=f"Question {i}",
                context=None,
                task=None,
                priority=(i % 3) + 1,
            )
            ama.cmd_ask(args)

    def test_lists_open_questions_by_default(self, capsys):
        self._seed(2)
        list_args = argparse.Namespace(status="open", priority=None)
        ama.cmd_list(list_args)

        out = capsys.readouterr().out
        assert "Q-001" in out
        assert "Q-002" in out

    def test_filter_by_status_answered_shows_only_answered(self, capsys):
        self._seed(2)
        ama.cmd_answer(argparse.Namespace(question_id="Q-001", answer="ans"))
        capsys.readouterr()  # flush ask/answer output

        list_args = argparse.Namespace(status="answered", priority=None)
        ama.cmd_list(list_args)

        out = capsys.readouterr().out
        assert "Q-001" in out
        assert "Q-002" not in out

    def test_filter_by_priority(self, capsys):
        self._seed(3)  # priorities: 1, 2, 3
        capsys.readouterr()

        list_args = argparse.Namespace(status="all", priority=1)
        ama.cmd_list(list_args)

        out = capsys.readouterr().out
        # Only Q-001 has priority 1 (index 0 → (0%3)+1 = 1)
        assert "Q-001" in out
        assert "Q-002" not in out

    def test_no_matching_questions_prints_message(self, capsys):
        list_args = argparse.Namespace(status="open", priority=None)
        ama.cmd_list(list_args)

        out = capsys.readouterr().out
        assert "沒有" in out  # "(沒有符合條件的問題)"

    def test_answered_entry_shows_answer_preview(self, capsys):
        self._seed(1)
        ama.cmd_answer(argparse.Namespace(question_id="Q-001", answer="Deep answer text"))
        capsys.readouterr()

        list_args = argparse.Namespace(status="answered", priority=None)
        ama.cmd_list(list_args)

        out = capsys.readouterr().out
        assert "Deep answer text" in out


# ── cmd_search() ──────────────────────────────────────────────────────────────


class TestCmdSearch:
    def _seed_varied(self):
        for q, ctx in [
            ("How does asyncio work?", "event loop"),
            ("What is a decorator?", "metaprogramming"),
            ("Explain GIL", "threading"),
        ]:
            ama.cmd_ask(argparse.Namespace(question=q, context=ctx, task=None, priority=2))

    def test_finds_match_in_question(self, capsys):
        self._seed_varied()
        capsys.readouterr()

        ama.cmd_search(argparse.Namespace(keyword="asyncio"))

        out = capsys.readouterr().out
        assert "Q-001" in out
        assert "Q-002" not in out

    def test_finds_match_in_context(self, capsys):
        self._seed_varied()
        capsys.readouterr()

        ama.cmd_search(argparse.Namespace(keyword="metaprogramming"))

        out = capsys.readouterr().out
        assert "Q-002" in out

    def test_case_insensitive_search(self, capsys):
        self._seed_varied()
        capsys.readouterr()

        ama.cmd_search(argparse.Namespace(keyword="GIL"))

        out1 = capsys.readouterr().out

        ama.cmd_search(argparse.Namespace(keyword="gil"))
        out2 = capsys.readouterr().out

        assert out1 == out2

    def test_no_results_prints_message(self, capsys):
        self._seed_varied()
        capsys.readouterr()

        ama.cmd_search(argparse.Namespace(keyword="xyzzy_not_there"))

        out = capsys.readouterr().out
        assert "找不到" in out

    def test_finds_match_in_answer(self, capsys):
        self._seed_varied()
        ama.cmd_answer(argparse.Namespace(question_id="Q-003", answer="GIL prevents true parallelism"))
        capsys.readouterr()

        ama.cmd_search(argparse.Namespace(keyword="parallelism"))

        out = capsys.readouterr().out
        assert "Q-003" in out


# ── cmd_stats() ───────────────────────────────────────────────────────────────


class TestCmdStats:
    def test_empty_stats(self, capsys):
        ama.cmd_stats(argparse.Namespace())

        out = capsys.readouterr().out
        assert "Total: 0" in out
        assert "Answered: 0" in out

    def test_counts_open_and_answered(self, capsys):
        for i in range(3):
            ama.cmd_ask(argparse.Namespace(question=f"Q{i}", context=None, task=None, priority=2))
        ama.cmd_answer(argparse.Namespace(question_id="Q-001", answer="ans"))
        capsys.readouterr()

        ama.cmd_stats(argparse.Namespace())

        out = capsys.readouterr().out
        assert "Total: 3" in out
        assert "Answered: 1" in out
        assert "Open: 2" in out

    def test_breakdown_by_priority(self, capsys):
        ama.cmd_ask(argparse.Namespace(question="P1 question", context=None, task=None, priority=1))
        ama.cmd_ask(argparse.Namespace(question="P2 question", context=None, task=None, priority=2))
        ama.cmd_ask(argparse.Namespace(question="P2 question 2", context=None, task=None, priority=2))
        capsys.readouterr()

        ama.cmd_stats(argparse.Namespace())

        out = capsys.readouterr().out
        assert "P1" in out
        assert "P2" in out
