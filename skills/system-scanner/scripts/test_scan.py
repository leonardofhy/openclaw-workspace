"""Tests for scan.py — system scanner helpers.

Run with:
    pytest skills/system-scanner/scripts/test_scan.py -v
"""

import importlib
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── import the module under test ──────────────────────────────────────────────

SCRIPTS_DIR = Path(__file__).resolve().parent
LIB_DIR = SCRIPTS_DIR.parent.parent / "lib"

if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import scan  # noqa: E402


# ── ScanContext / check() ─────────────────────────────────────────────────────


class TestScanContext:
    def test_initial_state_is_empty(self):
        ctx = scan.ScanContext()
        assert ctx.results == []
        assert ctx.fix_queue == []

    def test_check_ok_appends_result(self):
        ctx = scan.ScanContext()
        scan.check(ctx, "Disk", "ok", "50% used")

        assert len(ctx.results) == 1
        r = ctx.results[0]
        assert r["label"] == "Disk"
        assert r["status"] == "ok"
        assert r["detail"] == "50% used"
        assert r["fixable"] is False
        assert ctx.fix_queue == []

    def test_check_warn_without_fix_fn_skips_queue(self):
        ctx = scan.ScanContext()
        scan.check(ctx, "Git", "warn", "3 uncommitted files", fix_hint="git commit")

        assert ctx.results[0]["fixable"] is False
        assert ctx.fix_queue == []

    def test_check_warn_with_fix_fn_enqueues_fix(self):
        ctx = scan.ScanContext()
        fix = lambda: "fixed"  # noqa: E731
        scan.check(ctx, "Git", "warn", "3 uncommitted files", fix_fn=fix)

        assert ctx.results[0]["fixable"] is True
        assert len(ctx.fix_queue) == 1
        assert ctx.fix_queue[0]["label"] == "Git"
        assert ctx.fix_queue[0]["fn"] is fix

    def test_check_crit_with_fix_fn_enqueues_fix(self):
        ctx = scan.ScanContext()
        fix = lambda: "done"  # noqa: E731
        scan.check(ctx, "Secret", "crit", "Token missing", fix_fn=fix)

        assert ctx.results[0]["fixable"] is True
        assert len(ctx.fix_queue) == 1

    def test_check_ok_with_fix_fn_does_not_enqueue(self):
        """ok status should never land in fix_queue even when fix_fn is provided."""
        ctx = scan.ScanContext()
        scan.check(ctx, "Disk", "ok", fix_fn=lambda: "already fine")

        assert ctx.results[0]["fixable"] is True
        assert ctx.fix_queue == []  # ok → not queued

    def test_multiple_checks_accumulate(self):
        ctx = scan.ScanContext()
        for label, status in [("A", "ok"), ("B", "warn"), ("C", "crit")]:
            scan.check(ctx, label, status)

        assert len(ctx.results) == 3
        assert [r["label"] for r in ctx.results] == ["A", "B", "C"]


# ── sh() ──────────────────────────────────────────────────────────────────────


class TestSh:
    def test_success_returns_stdout_stripped(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "  hello world  \n"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            rc, out, err = scan.sh(["echo", "hello world"])

        assert rc == 0
        assert out == "hello world"
        assert err == ""
        mock_run.assert_called_once()

    def test_nonzero_returncode_propagated(self):
        mock_result = MagicMock()
        mock_result.returncode = 127
        mock_result.stdout = ""
        mock_result.stderr = "command not found"

        with patch("subprocess.run", return_value=mock_result):
            rc, out, err = scan.sh(["bogus-command"])

        assert rc == 127
        assert err == "command not found"

    def test_exception_returns_minus_one(self):
        with patch("subprocess.run", side_effect=FileNotFoundError("no such file")):
            rc, out, err = scan.sh(["nonexistent"])

        assert rc == -1
        assert out == ""
        assert "no such file" in err

    def test_timeout_exception_returns_minus_one(self):
        import subprocess

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 10)):
            rc, out, err = scan.sh(["sleep", "999"], timeout=10)

        assert rc == -1

    def test_cwd_forwarded_to_subprocess(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "main"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            scan.sh(["git", "branch"], cwd="/tmp")

        _, kwargs = mock_run.call_args
        assert kwargs.get("cwd") == "/tmp" or mock_run.call_args[0][1] == "/tmp" or True
        # Verify cwd was passed regardless of positional/keyword style
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["cwd"] == "/tmp"


# ── load_env() ────────────────────────────────────────────────────────────────


class TestLoadEnv:
    def test_parses_simple_key_value(self, tmp_path: Path):
        env_file = tmp_path / ".env"
        env_file.write_text("FOO=bar\nBAZ=qux\n")

        result = scan.load_env(env_file)

        assert result == {"FOO": "bar", "BAZ": "qux"}

    def test_strips_double_quotes(self, tmp_path: Path):
        env_file = tmp_path / ".env"
        env_file.write_text('KEY="quoted value"\n')

        result = scan.load_env(env_file)

        assert result["KEY"] == "quoted value"

    def test_strips_single_quotes(self, tmp_path: Path):
        env_file = tmp_path / ".env"
        env_file.write_text("KEY='single quoted'\n")

        result = scan.load_env(env_file)

        assert result["KEY"] == "single quoted"

    def test_ignores_comment_lines(self, tmp_path: Path):
        env_file = tmp_path / ".env"
        env_file.write_text("# This is a comment\nREAL=value\n")

        result = scan.load_env(env_file)

        assert "# This is a comment" not in result
        assert result == {"REAL": "value"}

    def test_ignores_blank_lines(self, tmp_path: Path):
        env_file = tmp_path / ".env"
        env_file.write_text("\n\nKEY=val\n\n")

        result = scan.load_env(env_file)

        assert result == {"KEY": "val"}

    def test_missing_file_returns_empty_dict(self, tmp_path: Path):
        result = scan.load_env(tmp_path / "nonexistent.env")

        assert result == {}

    def test_value_with_equals_sign_preserved(self, tmp_path: Path):
        env_file = tmp_path / ".env"
        env_file.write_text("TOKEN=abc=def=ghi\n")

        result = scan.load_env(env_file)

        assert result["TOKEN"] == "abc=def=ghi"


# ── load_json() ───────────────────────────────────────────────────────────────


class TestLoadJson:
    def test_loads_valid_json_dict(self, tmp_path: Path):
        f = tmp_path / "data.json"
        f.write_text(json.dumps({"key": "value", "num": 42}))

        result = scan.load_json(f)

        assert result == {"key": "value", "num": 42}

    def test_loads_valid_json_list(self, tmp_path: Path):
        f = tmp_path / "data.json"
        f.write_text(json.dumps([1, 2, 3]))

        result = scan.load_json(f)

        assert result == [1, 2, 3]

    def test_missing_file_returns_none(self, tmp_path: Path):
        result = scan.load_json(tmp_path / "missing.json")

        assert result is None

    def test_malformed_json_returns_none(self, tmp_path: Path):
        f = tmp_path / "bad.json"
        f.write_text("{not valid json}")

        result = scan.load_json(f)

        assert result is None

    def test_empty_file_returns_none(self, tmp_path: Path):
        f = tmp_path / "empty.json"
        f.write_text("")

        result = scan.load_json(f)

        assert result is None


# ── save_json() ───────────────────────────────────────────────────────────────


class TestSaveJson:
    def test_writes_dict_as_pretty_json(self, tmp_path: Path):
        f = tmp_path / "out.json"
        data = {"hello": "world", "n": 7}

        result = scan.save_json(f, data)

        assert result is True
        loaded = json.loads(f.read_text())
        assert loaded == data

    def test_writes_list(self, tmp_path: Path):
        f = tmp_path / "list.json"

        result = scan.save_json(f, [1, 2, 3])

        assert result is True
        assert json.loads(f.read_text()) == [1, 2, 3]

    def test_returns_false_on_oserror(self, tmp_path: Path):
        # Write to a directory path (always fails)
        result = scan.save_json(tmp_path, {"x": 1})

        assert result is False

    def test_overwrites_existing_file(self, tmp_path: Path):
        f = tmp_path / "data.json"
        f.write_text(json.dumps({"old": True}))

        scan.save_json(f, {"new": True})

        assert json.loads(f.read_text()) == {"new": True}

    def test_non_ascii_preserved(self, tmp_path: Path):
        f = tmp_path / "unicode.json"
        data = {"name": "台北"}

        scan.save_json(f, data)

        # ensure_ascii=False means characters are stored as-is, not escaped
        raw = f.read_text(encoding="utf-8")
        assert "台北" in raw


# ── run_fixes() ───────────────────────────────────────────────────────────────


class TestRunFixes:
    def test_empty_fix_queue_returns_empty_list(self):
        ctx = scan.ScanContext()
        result = scan.run_fixes(ctx)

        assert result == []

    def test_successful_fix_reported(self, capsys):
        ctx = scan.ScanContext()
        ctx.fix_queue.append({"label": "MyCheck", "fn": lambda: "all good"})

        results = scan.run_fixes(ctx)

        assert len(results) == 1
        assert results[0]["label"] == "MyCheck"
        assert results[0]["success"] is True
        assert results[0]["msg"] == "all good"

    def test_failing_fix_reported_as_failure(self):
        ctx = scan.ScanContext()

        def bad_fix():
            raise RuntimeError("boom")

        ctx.fix_queue.append({"label": "BadCheck", "fn": bad_fix})

        results = scan.run_fixes(ctx)

        assert results[0]["success"] is False
        assert "boom" in results[0]["msg"]


# ── _next_id helpers ──────────────────────────────────────────────────────────
# (These test internal logic accessible via the module; no CLI invocation needed)


class TestLoadCronJobs:
    def test_returns_empty_list_when_file_missing(self, tmp_path: Path):
        with patch.object(scan, "CRON_JOBS", tmp_path / "missing.json"):
            result = scan.load_cron_jobs()

        assert result == []

    def test_parses_jobs_key_from_dict(self, tmp_path: Path):
        f = tmp_path / "jobs.json"
        f.write_text(json.dumps({"version": 1, "jobs": [{"name": "daily"}]}))

        with patch.object(scan, "CRON_JOBS", f):
            result = scan.load_cron_jobs()

        assert result == [{"name": "daily"}]

    def test_parses_bare_list(self, tmp_path: Path):
        f = tmp_path / "jobs.json"
        f.write_text(json.dumps([{"name": "task1"}, {"name": "task2"}]))

        with patch.object(scan, "CRON_JOBS", f):
            result = scan.load_cron_jobs()

        assert len(result) == 2
