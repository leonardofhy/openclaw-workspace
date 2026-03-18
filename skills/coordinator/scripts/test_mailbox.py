#!/usr/bin/env python3
"""Comprehensive pytest tests for mailbox.py.

Stubs shared packages into sys.modules BEFORE importing the module under test
so that module-level side effects (store = JsonlStore(...), WORKSPACE = find_workspace())
use controlled mocks instead of touching the real filesystem or git.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import types
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

# ---------------------------------------------------------------------------
# Stub shared packages into sys.modules before any import of mailbox
# ---------------------------------------------------------------------------

_fake_workspace = Path("/fake/workspace")

# --- jsonl_store stub ---
_mock_jsonl_store_instance = MagicMock()

_mock_JsonlStore_cls = MagicMock(return_value=_mock_jsonl_store_instance)

_jsonl_store_mod = types.ModuleType("jsonl_store")
_jsonl_store_mod.find_workspace = MagicMock(return_value=_fake_workspace)  # type: ignore[attr-defined]
_jsonl_store_mod.JsonlStore = _mock_JsonlStore_cls  # type: ignore[attr-defined]
sys.modules["jsonl_store"] = _jsonl_store_mod

# --- common stub ---
_common_mod = types.ModuleType("common")
_common_mod.DISCORD_BOT_IDS = {"lab": "111111111111111111", "mac": "222222222222222222"}  # type: ignore[attr-defined]
_common_mod.DISCORD_BOT_SYNC_CHANNEL = "bot-sync"  # type: ignore[attr-defined]
sys.modules["common"] = _common_mod

# Now it is safe to import the module under test.
# We must add its parent dirs to sys.path exactly as the real script does,
# but since the stubs are already registered the import will succeed without
# the real files being present.
_scripts_dir = Path(__file__).resolve().parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

import mailbox as mb  # noqa: E402  (intentionally after sys.modules patching)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STORE: MagicMock = mb.store  # the module-level singleton (already a MagicMock)


def _make_args(**kwargs: Any) -> argparse.Namespace:
    """Build a minimal Namespace for command functions."""
    defaults: dict[str, Any] = {
        "sync": False,
        "sender": "lab",
        "receiver": "mac",
        "title": "Test title",
        "body": "Test body",
        "task_id": "",
        "priority": 2,
        "urgent": False,
        "to": "",
        "status": "",
        "id": "MB-001",
        "force": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# ---------------------------------------------------------------------------
# 1. now_iso
# ---------------------------------------------------------------------------


class TestNowIso:
    def test_returns_correct_format(self) -> None:
        result = mb.now_iso()
        # Must match YYYY-MM-DDTHH:MM:SS exactly
        assert len(result) == 19
        assert result[4] == "-"
        assert result[7] == "-"
        assert result[10] == "T"
        assert result[13] == ":"
        assert result[16] == ":"

    def test_values_are_numeric(self) -> None:
        result = mb.now_iso()
        parts = result.replace("T", "-").replace(":", "-").split("-")
        assert all(p.isdigit() for p in parts), f"Non-numeric part in {result}"


# ---------------------------------------------------------------------------
# 2. _current_branch
# ---------------------------------------------------------------------------


class TestCurrentBranch:
    @patch("mailbox.subprocess.check_output")
    def test_returns_branch_name_on_success(self, mock_check: MagicMock) -> None:
        mock_check.return_value = "macbook-m3\n"
        assert mb._current_branch() == "macbook-m3"

    @patch("mailbox.subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "git"))
    def test_returns_empty_string_on_called_process_error(self, _: MagicMock) -> None:
        assert mb._current_branch() == ""

    @patch("mailbox.subprocess.check_output", side_effect=FileNotFoundError)
    def test_returns_empty_string_when_git_not_found(self, _: MagicMock) -> None:
        assert mb._current_branch() == ""


# ---------------------------------------------------------------------------
# 3. _other_branch
# ---------------------------------------------------------------------------


class TestOtherBranch:
    @patch("mailbox._current_branch", return_value="lab-desktop")
    def test_lab_desktop_maps_to_macbook_m3(self, _: MagicMock) -> None:
        assert mb._other_branch() == "macbook-m3"

    @patch("mailbox._current_branch", return_value="macbook-m3")
    def test_macbook_m3_maps_to_lab_desktop(self, _: MagicMock) -> None:
        assert mb._other_branch() == "lab-desktop"

    @patch("mailbox._current_branch", return_value="unknown-branch")
    def test_unknown_branch_returns_empty_string(self, _: MagicMock) -> None:
        assert mb._other_branch() == ""

    @patch("mailbox._current_branch", return_value="")
    def test_empty_current_branch_returns_empty_string(self, _: MagicMock) -> None:
        assert mb._other_branch() == ""


# ---------------------------------------------------------------------------
# 4. _git_pull
# ---------------------------------------------------------------------------


class TestGitPull:
    @patch("mailbox._other_branch", return_value="macbook-m3")
    @patch("mailbox.subprocess.run")
    def test_returns_true_on_successful_merge(
        self, mock_run: MagicMock, _: MagicMock
    ) -> None:
        fetch_result = MagicMock(returncode=0, stdout="", stderr="")
        merge_result = MagicMock(returncode=0, stdout="Fast-forward", stderr="")
        mock_run.side_effect = [fetch_result, merge_result]
        assert mb._git_pull(quiet=True) is True

    @patch("mailbox._other_branch", return_value="")
    def test_returns_false_when_no_other_branch(self, _: MagicMock) -> None:
        assert mb._git_pull(quiet=True) is False

    @patch("mailbox._other_branch", return_value="macbook-m3")
    @patch("mailbox.subprocess.run")
    def test_returns_false_and_aborts_on_conflict(
        self, mock_run: MagicMock, _: MagicMock
    ) -> None:
        fetch_result = MagicMock(returncode=0, stdout="", stderr="")
        merge_result = MagicMock(returncode=1, stdout="CONFLICT (content)", stderr="")
        abort_result = MagicMock(returncode=0)
        mock_run.side_effect = [fetch_result, merge_result, abort_result]
        assert mb._git_pull(quiet=True) is False
        # Verify abort was called
        abort_call = mock_run.call_args_list[2]
        assert abort_call[0][0] == ["git", "merge", "--abort"]

    @patch("mailbox._other_branch", return_value="macbook-m3")
    @patch("mailbox.subprocess.run", side_effect=subprocess.TimeoutExpired("git", 15))
    def test_returns_false_on_timeout(self, _mock_run: MagicMock, _other: MagicMock) -> None:
        assert mb._git_pull(quiet=True) is False


# ---------------------------------------------------------------------------
# 5. _git_push
# ---------------------------------------------------------------------------


class TestGitPush:
    @patch("mailbox.subprocess.run")
    def test_returns_true_on_successful_push(self, mock_run: MagicMock) -> None:
        add_r = MagicMock(returncode=0)
        commit_r = MagicMock(returncode=0, stdout="", stderr="")
        hash_r = MagicMock(returncode=0, stdout="abc1234\n")
        push_r = MagicMock(returncode=0, stdout="", stderr="")
        mock_run.side_effect = [add_r, commit_r, hash_r, push_r]
        assert mb._git_push("MB-001", "send") is True

    @patch("mailbox.subprocess.run")
    def test_returns_false_when_push_fails(self, mock_run: MagicMock) -> None:
        add_r = MagicMock(returncode=0)
        commit_r = MagicMock(returncode=0, stdout="", stderr="")
        hash_r = MagicMock(returncode=0, stdout="abc1234\n")
        push_r = MagicMock(returncode=1, stdout="", stderr="remote rejected")
        mock_run.side_effect = [add_r, commit_r, hash_r, push_r]
        assert mb._git_push("MB-001", "send") is False

    @patch("mailbox.subprocess.run", side_effect=subprocess.TimeoutExpired("git", 10))
    def test_returns_false_on_timeout(self, _: MagicMock) -> None:
        assert mb._git_push("MB-001", "send") is False

    @patch("mailbox.subprocess.run")
    def test_commit_message_includes_id_and_action(self, mock_run: MagicMock) -> None:
        add_r = MagicMock(returncode=0)
        commit_r = MagicMock(returncode=0, stdout="", stderr="")
        hash_r = MagicMock(returncode=0, stdout="deadbee\n")
        push_r = MagicMock(returncode=0, stdout="", stderr="")
        mock_run.side_effect = [add_r, commit_r, hash_r, push_r]
        mb._git_push("MB-007", "ack")
        commit_call = mock_run.call_args_list[1]
        commit_cmd = commit_call[0][0]
        assert "mailbox: MB-007 ack" in commit_cmd


# ---------------------------------------------------------------------------
# 6. _discord_mention
# ---------------------------------------------------------------------------


class TestDiscordMention:
    def test_normal_body_included_in_full(self) -> None:
        result = mb._discord_mention("mac", "MB-001", "Hello", "Short body")
        assert "<@222222222222222222>" in result
        assert "MB-001" in result
        assert "Hello" in result
        assert "Short body" in result

    def test_long_body_is_truncated_to_100_chars_plus_ellipsis(self) -> None:
        long_body = "x" * 150
        result = mb._discord_mention("lab", "MB-002", "Title", long_body)
        assert "<@111111111111111111>" in result
        assert "..." in result
        # The body portion should be exactly 100 chars + "..."
        body_section = long_body[:100] + "..."
        assert body_section in result

    def test_body_exactly_100_chars_has_no_ellipsis(self) -> None:
        exact_body = "y" * 100
        result = mb._discord_mention("mac", "MB-003", "T", exact_body)
        assert "..." not in result
        assert exact_body in result

    def test_unknown_recipient_uses_question_marks(self) -> None:
        result = mb._discord_mention("unknown", "MB-004", "T", "B")
        assert "<@???>" in result


# ---------------------------------------------------------------------------
# 7. cmd_send
# ---------------------------------------------------------------------------


class TestCmdSend:
    def setup_method(self) -> None:
        _STORE.reset_mock()

    def test_send_returns_0_and_prints_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        sent_item = {
            "id": "MB-001", "from": "lab", "to": "mac",
            "title": "Test title", "body": "Test body",
            "task_id": "", "priority": 2, "urgent": False,
            "status": "open", "created_at": "2026-03-18T10:00:00",
            "acked_at": "", "done_at": "",
        }
        _STORE.append.return_value = sent_item
        args = _make_args(sender="lab", receiver="mac", sync=False)
        result = mb.cmd_send(args)
        assert result == 0
        out = capsys.readouterr().out
        assert '"id": "MB-001"' in out

    def test_send_to_self_returns_1(self, capsys: pytest.CaptureFixture[str]) -> None:
        args = _make_args(sender="lab", receiver="lab", sync=False)
        result = mb.cmd_send(args)
        assert result == 1
        assert "cannot send to self" in capsys.readouterr().err

    @patch("mailbox._git_pull", return_value=True)
    @patch("mailbox._git_push", return_value=True)
    def test_send_with_sync_calls_pull_and_push(
        self, mock_push: MagicMock, mock_pull: MagicMock
    ) -> None:
        _STORE.append.return_value = {"id": "MB-001", "title": "T", "body": "B"}
        args = _make_args(sender="lab", receiver="mac", sync=True)
        mb.cmd_send(args)
        mock_pull.assert_called_once_with(quiet=True)
        mock_push.assert_called_once_with("MB-001", "send")

    def test_send_payload_contains_expected_fields(self) -> None:
        _STORE.append.return_value = {
            "id": "MB-002", "from": "lab", "to": "mac",
            "title": "Deploy", "body": "Please deploy", "task_id": "TASK-5",
            "priority": 1, "urgent": True, "status": "open",
            "created_at": "2026-03-18T10:00:00", "acked_at": "", "done_at": "",
        }
        args = _make_args(
            sender="lab", receiver="mac", title="Deploy",
            body="Please deploy", task_id="TASK-5", priority=1, urgent=True,
        )
        mb.cmd_send(args)
        appended_item: dict = _STORE.append.call_args[0][0]
        assert appended_item["from"] == "lab"
        assert appended_item["to"] == "mac"
        assert appended_item["priority"] == 1
        assert appended_item["urgent"] is True
        assert appended_item["status"] == "open"


# ---------------------------------------------------------------------------
# 8. cmd_list
# ---------------------------------------------------------------------------


class TestCmdList:
    def setup_method(self) -> None:
        _STORE.reset_mock()

    def test_empty_store_prints_empty_marker(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _STORE.load.return_value = []
        args = _make_args(sync=False, to="", status="")
        result = mb.cmd_list(args)
        assert result == 0
        assert "(empty)" in capsys.readouterr().out

    def test_filters_by_to(self, capsys: pytest.CaptureFixture[str]) -> None:
        _STORE.load.return_value = [
            {"id": "MB-001", "to": "mac", "status": "open"},
            {"id": "MB-002", "to": "lab", "status": "open"},
        ]
        args = _make_args(sync=False, to="mac", status="")
        mb.cmd_list(args)
        out = capsys.readouterr().out
        assert "MB-001" in out
        assert "MB-002" not in out

    def test_filters_by_status(self, capsys: pytest.CaptureFixture[str]) -> None:
        _STORE.load.return_value = [
            {"id": "MB-001", "to": "mac", "status": "open"},
            {"id": "MB-002", "to": "mac", "status": "done"},
        ]
        args = _make_args(sync=False, to="", status="done")
        mb.cmd_list(args)
        out = capsys.readouterr().out
        assert "MB-002" in out
        assert "MB-001" not in out

    @patch("mailbox._git_pull", return_value=True)
    def test_list_with_sync_calls_pull(self, mock_pull: MagicMock) -> None:
        _STORE.load.return_value = []
        args = _make_args(sync=True, to="", status="")
        mb.cmd_list(args)
        mock_pull.assert_called_once_with(quiet=True)


# ---------------------------------------------------------------------------
# 9. cmd_ack
# ---------------------------------------------------------------------------


class TestCmdAck:
    def setup_method(self) -> None:
        _STORE.reset_mock()

    def test_ack_open_message_returns_0(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _STORE.find.return_value = {"id": "MB-001", "status": "open"}
        acked = {"id": "MB-001", "status": "acked", "acked_at": "2026-03-18T10:00:00"}
        _STORE.update.return_value = acked
        args = _make_args(id="MB-001", sync=False, force=False)
        result = mb.cmd_ack(args)
        assert result == 0
        assert '"status": "acked"' in capsys.readouterr().out

    def test_ack_nonexistent_message_returns_1(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _STORE.find.return_value = {"id": "MB-999", "status": "open"}
        _STORE.update.return_value = None
        args = _make_args(id="MB-999", sync=False, force=False)
        result = mb.cmd_ack(args)
        assert result == 1
        assert "not found" in capsys.readouterr().err

    def test_ack_already_acked_message_fails_without_force(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _STORE.find.return_value = {"id": "MB-001", "status": "acked"}
        args = _make_args(id="MB-001", sync=False, force=False)
        result = mb.cmd_ack(args)
        assert result == 1
        err = capsys.readouterr().err
        assert "expected 'open'" in err

    def test_ack_wrong_status_with_force_proceeds(self) -> None:
        # With --force, required_status is None so status check is skipped
        acked = {"id": "MB-001", "status": "acked", "acked_at": "2026-03-18T10:00:00"}
        _STORE.update.return_value = acked
        args = _make_args(id="MB-001", sync=False, force=True)
        result = mb.cmd_ack(args)
        assert result == 0
        # find should NOT have been called when force=True (required_status=None)
        _STORE.find.assert_not_called()


# ---------------------------------------------------------------------------
# 10. cmd_done
# ---------------------------------------------------------------------------


class TestCmdDone:
    def setup_method(self) -> None:
        _STORE.reset_mock()

    def test_done_acked_message_returns_0(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _STORE.find.return_value = {"id": "MB-001", "status": "acked"}
        done_item = {"id": "MB-001", "status": "done", "done_at": "2026-03-18T11:00:00"}
        _STORE.update.return_value = done_item
        args = _make_args(id="MB-001", sync=False, force=False)
        result = mb.cmd_done(args)
        assert result == 0
        assert '"status": "done"' in capsys.readouterr().out

    def test_done_on_open_message_fails_without_force(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _STORE.find.return_value = {"id": "MB-001", "status": "open"}
        args = _make_args(id="MB-001", sync=False, force=False)
        result = mb.cmd_done(args)
        assert result == 1
        err = capsys.readouterr().err
        assert "expected 'acked'" in err

    @patch("mailbox._git_pull", return_value=True)
    @patch("mailbox._git_push", return_value=True)
    def test_done_with_sync_calls_pull_and_push(
        self, mock_push: MagicMock, mock_pull: MagicMock
    ) -> None:
        _STORE.find.return_value = {"id": "MB-001", "status": "acked"}
        done_item = {"id": "MB-001", "status": "done", "done_at": "2026-03-18T11:00:00"}
        _STORE.update.return_value = done_item
        args = _make_args(id="MB-001", sync=True, force=False)
        mb.cmd_done(args)
        mock_pull.assert_called_once_with(quiet=True)
        mock_push.assert_called_once_with("MB-001", "done")


# ---------------------------------------------------------------------------
# 11. build_parser
# ---------------------------------------------------------------------------


class TestBuildParser:
    def test_send_subcommand_parses_required_args(self) -> None:
        parser = mb.build_parser()
        args = parser.parse_args([
            "--no-sync", "send",
            "--from", "lab", "--to", "mac",
            "--title", "Hello", "--body", "World",
        ])
        assert args.sender == "lab"
        assert args.receiver == "mac"
        assert args.title == "Hello"
        assert args.body == "World"
        assert args.sync is False
        assert args.func is mb.cmd_send

    def test_list_subcommand_sets_correct_defaults(self) -> None:
        parser = mb.build_parser()
        args = parser.parse_args(["list"])
        assert args.to == ""
        assert args.status == ""
        assert args.sync is True
        assert args.func is mb.cmd_list

    def test_ack_subcommand_parses_id(self) -> None:
        parser = mb.build_parser()
        args = parser.parse_args(["--no-sync", "ack", "MB-005"])
        assert args.id == "MB-005"
        assert args.force is False
        assert args.func is mb.cmd_ack

    def test_done_subcommand_with_force_flag(self) -> None:
        parser = mb.build_parser()
        args = parser.parse_args(["done", "MB-010", "--force"])
        assert args.id == "MB-010"
        assert args.force is True
        assert args.func is mb.cmd_done

    def test_send_priority_choices_are_enforced(self) -> None:
        parser = mb.build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([
                "send", "--from", "lab", "--to", "mac",
                "--title", "T", "--body", "B", "--priority", "5",
            ])

    def test_send_from_choices_are_enforced(self) -> None:
        parser = mb.build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([
                "send", "--from", "desktop", "--to", "mac",
                "--title", "T", "--body", "B",
            ])

    def test_send_urgent_flag_defaults_to_false(self) -> None:
        parser = mb.build_parser()
        args = parser.parse_args([
            "send", "--from", "mac", "--to", "lab",
            "--title", "T", "--body", "B",
        ])
        assert args.urgent is False

    def test_send_urgent_flag_sets_true_when_present(self) -> None:
        parser = mb.build_parser()
        args = parser.parse_args([
            "send", "--from", "mac", "--to", "lab",
            "--title", "T", "--body", "B", "--urgent",
        ])
        assert args.urgent is True
