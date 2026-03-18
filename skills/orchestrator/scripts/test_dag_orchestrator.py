#!/usr/bin/env python3
"""Tests for the DAG orchestrator — manifest, waves, worktrees, CLI."""

import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import pytest

# Bootstrap
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import manifest as mf


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def tmp_manifest(tmp_path):
    """Create a temp manifest file path."""
    return tmp_path / "manifest.json"


@pytest.fixture
def sample_manifest():
    """A manifest with a small DAG: A -> B -> C, plus D (independent)."""
    m = mf.new_manifest("test-pipeline")
    mf.add_task(m, "A", prompt="Task A")
    mf.add_task(m, "B", prompt="Task B", depends_on=["A"])
    mf.add_task(m, "C", prompt="Task C", depends_on=["B"])
    mf.add_task(m, "D", prompt="Task D")
    return m


# ── test_manifest_crud ────────────────────────────────────

def test_manifest_crud(tmp_manifest):
    """Add, update, get tasks — round-trip through save/load."""
    m = mf.new_manifest("crud-test")
    mf.add_task(m, "t1", prompt="hello")
    mf.add_task(m, "t2", prompt="world", depends_on=["t1"], timeout=600)

    mf.save(tmp_manifest, m)
    loaded = mf.load(tmp_manifest)

    assert loaded["pipeline_name"] == "crud-test"
    assert "t1" in loaded["tasks"]
    assert "t2" in loaded["tasks"]
    assert loaded["tasks"]["t2"]["depends_on"] == ["t1"]
    assert loaded["tasks"]["t2"]["timeout"] == 600
    assert loaded["tasks"]["t1"]["status"] == "pending"


def test_add_duplicate_raises(sample_manifest):
    """Adding a task with an existing ID should raise."""
    with pytest.raises(ValueError, match="already exists"):
        mf.add_task(sample_manifest, "A", prompt="duplicate")


def test_add_no_prompt_raises():
    m = mf.new_manifest("x")
    with pytest.raises(ValueError, match="Must provide prompt"):
        mf.add_task(m, "t", depends_on=[])


# ── test_dependency_resolution ────────────────────────────

def test_dependency_resolution(sample_manifest):
    """Topological sort produces correct ordering."""
    waves = mf.compute_waves(sample_manifest)
    # Flatten to check ordering
    flat = [tid for wave in waves for tid in wave]
    assert flat.index("A") < flat.index("B")
    assert flat.index("B") < flat.index("C")


# ── test_cycle_detection ──────────────────────────────────

def test_cycle_detection():
    """Circular dependencies should raise ValueError."""
    m = mf.new_manifest("cycle")
    mf.add_task(m, "X", prompt="x", depends_on=["Z"])
    mf.add_task(m, "Y", prompt="y", depends_on=["X"])
    mf.add_task(m, "Z", prompt="z", depends_on=["Y"])

    with pytest.raises(ValueError, match="Cycle"):
        mf.compute_waves(m)


# ── test_wave_computation ─────────────────────────────────

def test_wave_computation(sample_manifest):
    """Correct grouping into waves."""
    waves = mf.compute_waves(sample_manifest)
    # Wave 1: A, D (no deps) — Wave 2: B — Wave 3: C
    assert len(waves) == 3
    assert set(waves[0]) == {"A", "D"}
    assert waves[1] == ["B"]
    assert waves[2] == ["C"]


def test_wave_computation_flat():
    """All independent tasks should be in one wave."""
    m = mf.new_manifest("flat")
    for i in range(5):
        mf.add_task(m, f"t{i}", prompt=f"task {i}")
    waves = mf.compute_waves(m)
    assert len(waves) == 1
    assert len(waves[0]) == 5


# ── test_ready_tasks ──────────────────────────────────────

def test_ready_tasks(sample_manifest):
    """Only tasks with all deps completed are ready."""
    m = sample_manifest
    # Initially: A and D are ready (no deps)
    ready = mf.get_ready_tasks(m)
    assert set(ready) == {"A", "D"}

    # Complete A -> B becomes ready
    mf.update_status(m, "A", "completed")
    ready = mf.get_ready_tasks(m)
    assert "B" in ready
    assert "C" not in ready

    # Complete B -> C becomes ready
    mf.update_status(m, "B", "completed")
    ready = mf.get_ready_tasks(m)
    assert "C" in ready


# ── test_file_locking ─────────────────────────────────────

def test_file_locking(tmp_manifest):
    """Concurrent save/load shouldn't corrupt the file."""
    m = mf.new_manifest("lock-test")
    for i in range(10):
        mf.add_task(m, f"t{i}", prompt=f"task {i}")
    mf.save(tmp_manifest, m)

    errors = []

    def writer(task_id):
        try:
            data = mf.load(tmp_manifest)
            mf.update_status(data, task_id, "completed")
            mf.save(tmp_manifest, data)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=writer, args=(f"t{i}",)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # File should still be valid JSON
    final = mf.load(tmp_manifest)
    assert final["pipeline_name"] == "lock-test"
    assert len(errors) == 0


# ── test_retry_logic ──────────────────────────────────────

def test_retry_logic():
    """Failed tasks respect retry counts."""
    m = mf.new_manifest("retry")
    mf.add_task(m, "flaky", prompt="might fail", retries=2)

    # Simulate failure + retry
    mf.update_status(m, "flaky", "running")
    mf.update_status(m, "flaky", "failed", error="connection reset")

    task = m["tasks"]["flaky"]
    assert task["status"] == "failed"
    assert task["error"] == "connection reset"

    # Reset for retry
    task["retry_count"] += 1
    mf.update_status(m, "flaky", "pending", error=None)
    assert task["status"] == "pending"
    assert task["retry_count"] == 1


# ── test_worktree_create_cleanup ──────────────────────────

def test_worktree_create_cleanup(tmp_path, monkeypatch):
    """Worktree create/cleanup via mocked git commands."""
    import worktree_manager as wm

    calls = []

    def mock_git(*args, cwd=None):
        calls.append(args)
        if args[0] == "worktree" and args[1] == "add":
            # Create the directory to simulate git worktree add
            Path(args[2]).mkdir(parents=True, exist_ok=True)
            return ""
        if args[0] == "worktree" and args[1] == "remove":
            p = Path(args[2])
            if p.exists():
                import shutil
                shutil.rmtree(p)
            return ""
        if args[0] == "branch" and args[1] == "-D":
            return ""
        return ""

    monkeypatch.setattr(wm, "_git", mock_git)
    monkeypatch.setattr(wm, "WORKTREES_DIR", tmp_path / ".worktrees")

    # Create
    wt = wm.create_worktree("test-task")
    assert wt.exists()

    # Cleanup
    wm.cleanup_worktree("test-task")
    assert not wt.exists()


# ── test_cli_init_add_plan ────────────────────────────────

def test_cli_init_add_plan(tmp_path):
    """CLI subcommands: init, add, plan."""
    manifest_path = tmp_path / "manifest.json"
    orch = str(SCRIPT_DIR / "orchestrator.py")

    # init
    result = subprocess.run(
        [sys.executable, orch, "--manifest", str(manifest_path), "init", "--name", "cli-test"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert manifest_path.exists()

    # add task A
    result = subprocess.run(
        [sys.executable, orch, "--manifest", str(manifest_path), "add",
         "--id", "A", "--prompt", "Do thing A"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0

    # add task B depending on A
    result = subprocess.run(
        [sys.executable, orch, "--manifest", str(manifest_path), "add",
         "--id", "B", "--prompt", "Do thing B", "--depends-on", "A"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0

    # plan
    result = subprocess.run(
        [sys.executable, orch, "--manifest", str(manifest_path), "plan"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert "Wave 1" in result.stdout
    assert "Wave 2" in result.stdout


# ── test_status_display ───────────────────────────────────

def test_status_display(tmp_path):
    """Status command shows formatted output."""
    manifest_path = tmp_path / "manifest.json"
    m = mf.new_manifest("status-test")
    mf.add_task(m, "done", prompt="finished")
    mf.update_status(m, "done", "completed")
    mf.add_task(m, "stuck", prompt="broken")
    mf.update_status(m, "stuck", "failed", error="something went wrong")
    mf.add_task(m, "waiting", prompt="pending")
    mf.save(manifest_path, m)

    orch = str(SCRIPT_DIR / "orchestrator.py")
    result = subprocess.run(
        [sys.executable, orch, "--manifest", str(manifest_path), "status"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert "done: completed" in result.stdout
    assert "stuck: failed" in result.stdout
    assert "waiting: pending" in result.stdout


# ── test_validate ─────────────────────────────────────────

def test_validate_missing_dep():
    """Validation catches missing dependencies."""
    m = mf.new_manifest("bad")
    mf.add_task(m, "X", prompt="x", depends_on=["NONEXISTENT"])
    errors = mf.validate(m)
    assert any("unknown task" in e for e in errors)


def test_validate_cycle():
    """Validation catches cycles."""
    m = mf.new_manifest("cycle")
    mf.add_task(m, "A", prompt="a", depends_on=["B"])
    mf.add_task(m, "B", prompt="b", depends_on=["A"])
    errors = mf.validate(m)
    assert any("Cycle" in e for e in errors)


def test_get_stats(sample_manifest):
    """Stats counts by status."""
    mf.update_status(sample_manifest, "A", "completed")
    mf.update_status(sample_manifest, "D", "failed", error="oops")
    stats = mf.get_stats(sample_manifest)
    assert stats["completed"] == 1
    assert stats["failed"] == 1
    assert stats["pending"] == 2
    assert stats["total"] == 4
