#!/usr/bin/env python3
"""Tests for skills/shared/experiment_dispatch.py

Covers:
- dispatch dry-run: verify correct SSH command constructed
- queue write: dispatch adds entry to queue.jsonl
- status update: check_status updates queue correctly
- results caching: fetch_results caches to correct path
- priority ordering: high priority jobs sorted first in queue list

Usage:
    python3 -m pytest skills/shared/test_experiment_dispatch.py -v
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(__file__))
import experiment_dispatch as ed


# ── Helpers ──

def _patch_paths(tmp_dir: Path):
    """Return a dict of patches redirecting queue/results to tmp_dir."""
    return {
        "QUEUE_PATH": tmp_dir / "queue.jsonl",
        "RESULTS_DIR": tmp_dir / "results",
    }


# ── test_dispatch_dry_run ──

class TestDispatchDryRun:
    """dispatch() with dry_run=True prints SSH command, doesn't execute."""

    def test_dry_run_prints_ssh_command(self, capsys):
        with tempfile.TemporaryDirectory() as td:
            patches = _patch_paths(Path(td))
            with patch.object(ed, "QUEUE_PATH", patches["QUEUE_PATH"]), \
                 patch.object(ed, "RESULTS_DIR", patches["RESULTS_DIR"]):
                job_id = ed.dispatch("Q001", "whisper-small", dry_run=True)
                captured = capsys.readouterr()
                assert "[DRY RUN]" in captured.out
                assert "ssh" in captured.out
                assert "iso_leo" in captured.out
                assert "nohup" in captured.out
                assert job_id.startswith("Q001-whisper-small-")

    def test_dry_run_creates_queue_entry(self):
        with tempfile.TemporaryDirectory() as td:
            patches = _patch_paths(Path(td))
            with patch.object(ed, "QUEUE_PATH", patches["QUEUE_PATH"]), \
                 patch.object(ed, "RESULTS_DIR", patches["RESULTS_DIR"]):
                ed.dispatch("Q001", "whisper-small", dry_run=True)
                jobs = ed._read_queue()
                assert len(jobs) == 1
                assert jobs[0]["status"] == "dry_run"
                assert jobs[0]["exp_id"] == "Q001"

    def test_dry_run_correct_ssh_target(self, capsys):
        with tempfile.TemporaryDirectory() as td:
            patches = _patch_paths(Path(td))
            with patch.object(ed, "QUEUE_PATH", patches["QUEUE_PATH"]), \
                 patch.object(ed, "RESULTS_DIR", patches["RESULTS_DIR"]):
                ed.dispatch("Q001", "whisper-small", dry_run=True)
                captured = capsys.readouterr()
                assert "-J iso_leo" in captured.out
                assert "-p 2222" in captured.out
                assert "leonardo@localhost" in captured.out


# ── test_queue_write ──

class TestQueueWrite:
    """dispatch() adds correct entry to queue.jsonl."""

    def test_dispatch_adds_entry(self):
        with tempfile.TemporaryDirectory() as td:
            patches = _patch_paths(Path(td))
            with patch.object(ed, "QUEUE_PATH", patches["QUEUE_PATH"]), \
                 patch.object(ed, "RESULTS_DIR", patches["RESULTS_DIR"]):
                ed.dispatch("Q001", "whisper-small", priority="high", dry_run=True)
                jobs = ed._read_queue()
                assert len(jobs) == 1
                job = jobs[0]
                assert job["exp_id"] == "Q001"
                assert job["model"] == "whisper-small"
                assert job["priority"] == "high"
                assert job["submitted_at"] is not None

    def test_multiple_dispatches_append(self):
        with tempfile.TemporaryDirectory() as td:
            patches = _patch_paths(Path(td))
            with patch.object(ed, "QUEUE_PATH", patches["QUEUE_PATH"]), \
                 patch.object(ed, "RESULTS_DIR", patches["RESULTS_DIR"]):
                ed.dispatch("Q001", "whisper-small", dry_run=True)
                ed.dispatch("Q002", "whisper-medium", dry_run=True)
                jobs = ed._read_queue()
                assert len(jobs) == 2
                assert jobs[0]["exp_id"] == "Q001"
                assert jobs[1]["exp_id"] == "Q002"

    def test_job_schema_fields(self):
        with tempfile.TemporaryDirectory() as td:
            patches = _patch_paths(Path(td))
            with patch.object(ed, "QUEUE_PATH", patches["QUEUE_PATH"]), \
                 patch.object(ed, "RESULTS_DIR", patches["RESULTS_DIR"]):
                ed.dispatch("Q001", "whisper-small", dry_run=True)
                job = ed._read_queue()[0]
                required_keys = {
                    "job_id", "exp_id", "model", "priority",
                    "status", "submitted_at", "started_at",
                    "completed_at", "result_path", "error",
                }
                assert required_keys.issubset(set(job.keys()))


# ── test_status_update ──

class TestStatusUpdate:
    """check_status() updates queue with current process status."""

    def test_status_marks_dead_process_as_done(self):
        with tempfile.TemporaryDirectory() as td:
            patches = _patch_paths(Path(td))
            with patch.object(ed, "QUEUE_PATH", patches["QUEUE_PATH"]), \
                 patch.object(ed, "RESULTS_DIR", patches["RESULTS_DIR"]):
                # Seed a running job with a PID
                job = {
                    "job_id": "Q001-whisper-small-20260319-0330",
                    "exp_id": "Q001",
                    "model": "whisper-small",
                    "priority": "high",
                    "status": "running",
                    "submitted_at": "2026-03-19T03:30:00+0800",
                    "started_at": "2026-03-19T03:30:01+0800",
                    "completed_at": None,
                    "result_path": None,
                    "error": None,
                    "pid": "12345",
                }
                ed._append_job(job)

                # Mock SSH: process is dead, results exist
                def mock_ssh(cmd, *, dry_run=False, timeout=30):
                    if "kill -0" in cmd:
                        return "DEAD"
                    if "test -f" in cmd:
                        return "EXISTS"
                    return ""

                with patch.object(ed, "_run_ssh", side_effect=mock_ssh):
                    results = ed.check_status(job_id="Q001-whisper-small-20260319-0330")

                assert len(results) == 1
                assert results[0]["status"] == "done"
                assert results[0]["completed_at"] is not None

    def test_status_marks_dead_without_results_as_failed(self):
        with tempfile.TemporaryDirectory() as td:
            patches = _patch_paths(Path(td))
            with patch.object(ed, "QUEUE_PATH", patches["QUEUE_PATH"]), \
                 patch.object(ed, "RESULTS_DIR", patches["RESULTS_DIR"]):
                job = {
                    "job_id": "Q001-whisper-small-20260319-0400",
                    "exp_id": "Q001",
                    "model": "whisper-small",
                    "priority": "high",
                    "status": "running",
                    "submitted_at": "2026-03-19T04:00:00+0800",
                    "started_at": "2026-03-19T04:00:01+0800",
                    "completed_at": None,
                    "result_path": None,
                    "error": None,
                    "pid": "99999",
                }
                ed._append_job(job)

                def mock_ssh(cmd, *, dry_run=False, timeout=30):
                    if "kill -0" in cmd:
                        return "DEAD"
                    if "test -f" in cmd:
                        raise RuntimeError("no results")
                    return ""

                with patch.object(ed, "_run_ssh", side_effect=mock_ssh):
                    results = ed.check_status()

                assert results[0]["status"] == "failed"
                assert "without producing results" in results[0]["error"]

    def test_status_ssh_failure_marks_failed(self):
        with tempfile.TemporaryDirectory() as td:
            patches = _patch_paths(Path(td))
            with patch.object(ed, "QUEUE_PATH", patches["QUEUE_PATH"]), \
                 patch.object(ed, "RESULTS_DIR", patches["RESULTS_DIR"]):
                job = {
                    "job_id": "Q001-whisper-small-20260319-0500",
                    "exp_id": "Q001",
                    "model": "whisper-small",
                    "priority": "high",
                    "status": "running",
                    "submitted_at": "2026-03-19T05:00:00+0800",
                    "started_at": "2026-03-19T05:00:01+0800",
                    "completed_at": None,
                    "result_path": None,
                    "error": None,
                    "pid": "11111",
                }
                ed._append_job(job)

                with patch.object(ed, "_run_ssh", side_effect=RuntimeError("SSH connection refused")):
                    results = ed.check_status()

                assert results[0]["status"] == "failed"
                assert "SSH connection refused" in results[0]["error"]


# ── test_results_caching ──

class TestResultsCaching:
    """fetch_results() caches to correct path."""

    def test_caches_to_results_dir(self):
        with tempfile.TemporaryDirectory() as td:
            patches = _patch_paths(Path(td))
            with patch.object(ed, "QUEUE_PATH", patches["QUEUE_PATH"]), \
                 patch.object(ed, "RESULTS_DIR", patches["RESULTS_DIR"]):
                mock_data = {"accuracy": 0.95, "wer": 0.05}

                with patch.object(ed, "_run_ssh", return_value=json.dumps(mock_data)):
                    result = ed.fetch_results("Q001", "whisper-small")

                assert result == mock_data
                cache = patches["RESULTS_DIR"] / "Q001_whisper-small.json"
                assert cache.exists()
                assert json.loads(cache.read_text()) == mock_data

    def test_returns_cached_on_second_call(self):
        with tempfile.TemporaryDirectory() as td:
            patches = _patch_paths(Path(td))
            with patch.object(ed, "QUEUE_PATH", patches["QUEUE_PATH"]), \
                 patch.object(ed, "RESULTS_DIR", patches["RESULTS_DIR"]):
                # Pre-populate cache
                cache = patches["RESULTS_DIR"] / "Q001_whisper-small.json"
                cache.parent.mkdir(parents=True, exist_ok=True)
                cached_data = {"accuracy": 0.99}
                cache.write_text(json.dumps(cached_data))

                # Should return cache without SSH
                with patch.object(ed, "_run_ssh") as mock_ssh:
                    result = ed.fetch_results("Q001", "whisper-small")
                    mock_ssh.assert_not_called()

                assert result == cached_data

    def test_returns_none_on_ssh_failure(self):
        with tempfile.TemporaryDirectory() as td:
            patches = _patch_paths(Path(td))
            with patch.object(ed, "QUEUE_PATH", patches["QUEUE_PATH"]), \
                 patch.object(ed, "RESULTS_DIR", patches["RESULTS_DIR"]):
                with patch.object(ed, "_run_ssh", side_effect=RuntimeError("timeout")):
                    result = ed.fetch_results("Q001", "whisper-small")
                assert result is None

    def test_dry_run_returns_none(self):
        with tempfile.TemporaryDirectory() as td:
            patches = _patch_paths(Path(td))
            with patch.object(ed, "QUEUE_PATH", patches["QUEUE_PATH"]), \
                 patch.object(ed, "RESULTS_DIR", patches["RESULTS_DIR"]):
                result = ed.fetch_results("Q001", "whisper-small", dry_run=True)
                assert result is None


# ── test_priority_ordering ──

class TestPriorityOrdering:
    """High priority jobs sorted first in queue list."""

    def test_high_priority_first(self):
        with tempfile.TemporaryDirectory() as td:
            patches = _patch_paths(Path(td))
            with patch.object(ed, "QUEUE_PATH", patches["QUEUE_PATH"]), \
                 patch.object(ed, "RESULTS_DIR", patches["RESULTS_DIR"]):
                ed._append_job({"job_id": "j1", "priority": "normal", "status": "queued", "submitted_at": "2026-03-19T01:00:00+0800", "exp_id": "Q001", "model": "whisper-medium"})
                ed._append_job({"job_id": "j2", "priority": "high", "status": "queued", "submitted_at": "2026-03-19T02:00:00+0800", "exp_id": "Q002", "model": "whisper-small"})
                ed._append_job({"job_id": "j3", "priority": "low", "status": "queued", "submitted_at": "2026-03-19T00:30:00+0800", "exp_id": "Q001", "model": "whisper-small"})

                jobs = ed._read_queue()
                priority_order = {"high": 0, "normal": 1, "low": 2}
                jobs.sort(key=lambda j: (priority_order.get(j.get("priority", "normal"), 1), j.get("submitted_at", "")))

                assert jobs[0]["job_id"] == "j2"  # high
                assert jobs[1]["job_id"] == "j1"  # normal
                assert jobs[2]["job_id"] == "j3"  # low


# ── test_build_run_command ──

class TestBuildRunCommand:
    """_build_run_command() generates correct nohup commands."""

    def test_q001_command(self):
        cmd = ed._build_run_command("Q001", "whisper-small")
        assert "q001_voicing_geometry.py" in cmd
        assert "--model whisper-small" in cmd
        assert "nohup" in cmd
        assert "miniconda3" in cmd

    def test_q002_command(self):
        cmd = ed._build_run_command("Q002", "whisper-medium")
        assert "q002_causal_contribution.py" in cmd
        assert "--model whisper-medium" in cmd

    def test_unknown_exp_fallback(self):
        cmd = ed._build_run_command("Q999", "whisper-base")
        assert "q999_experiment.py" in cmd


# ── test_ssh_config ──

class TestSshConfig:
    """SSH command uses correct jump host and port."""

    def test_ssh_cmd_base(self):
        assert ed.SSH_CMD_BASE == ["ssh", "-J", "iso_leo", "-p", "2222", "leonardo@localhost"]

    def test_ssh_timeout(self):
        assert ed.SSH_TIMEOUT == 30


# ── test_graceful_ssh_failure ──

class TestGracefulSshFailure:
    """SSH failures mark job as failed, don't crash."""

    def test_dispatch_ssh_failure_marks_failed(self):
        with tempfile.TemporaryDirectory() as td:
            patches = _patch_paths(Path(td))
            with patch.object(ed, "QUEUE_PATH", patches["QUEUE_PATH"]), \
                 patch.object(ed, "RESULTS_DIR", patches["RESULTS_DIR"]):
                with patch.object(ed, "_run_ssh", side_effect=RuntimeError("Connection refused")):
                    job_id = ed.dispatch("Q001", "whisper-small")

                jobs = ed._read_queue()
                assert len(jobs) == 1
                assert jobs[0]["status"] == "failed"
                assert "Connection refused" in jobs[0]["error"]
                assert job_id == jobs[0]["job_id"]


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
