#!/usr/bin/env python3
"""Tests for agent_mgr.py — agent lifecycle management."""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import agent_mgr


@pytest.fixture(autouse=True)
def tmp_registry(tmp_path, monkeypatch):
    """Redirect registry to a temp directory for every test."""
    reg_dir = tmp_path / "agents"
    reg_dir.mkdir()
    reg_file = reg_dir / "registry.jsonl"
    monkeypatch.setattr(agent_mgr, "REGISTRY_DIR", reg_dir)
    monkeypatch.setattr(agent_mgr, "REGISTRY_FILE", reg_file)
    return reg_file


def _make_entry(name="Test Agent", status="running", pid=99999,
                spawned_minutes_ago=10, completed=False, completed_minutes_ago=None,
                model="claude-sonnet-4-6",
                exit_code=None, error=None):
    """Helper to create a registry entry."""
    now = datetime.now(timezone.utc)
    spawned = now - timedelta(minutes=spawned_minutes_ago)
    if completed:
        c_ago = completed_minutes_ago if completed_minutes_ago is not None else spawned_minutes_ago
        completed_at = (now - timedelta(minutes=c_ago)).isoformat()
    else:
        completed_at = None
    entry = {
        "id": agent_mgr.generate_id(name),
        "name": name,
        "task_summary": "test task",
        "model": model,
        "status": status,
        "spawned_at": spawned.isoformat(),
        "completed_at": completed_at,
        "duration_s": (spawned_minutes_ago * 60 if completed else None),
        "exit_code": exit_code,
        "pid": pid,
        "workdir": str(agent_mgr.REGISTRY_FILE.parent),
        "artifacts": [],
        "error": error,
    }
    agent_mgr._append_entry(entry)
    return entry


# ── Spawn Tests ─────────────────────────────────────────

def test_spawn_creates_registry_entry():
    """Spawning an agent creates a JSONL entry in the registry."""
    mock_proc = MagicMock()
    mock_proc.pid = 12345

    with patch("subprocess.Popen", return_value=mock_proc):
        entry = agent_mgr.spawn(name="Test Build", task="Build something")

    assert entry["name"] == "Test Build"
    assert entry["status"] == "running"
    assert entry["pid"] == 12345

    entries = agent_mgr._read_entries()
    assert len(entries) == 1
    assert entries[0]["name"] == "Test Build"


def test_spawn_generates_meaningful_id():
    """Generated IDs contain date and slugified name."""
    id1 = agent_mgr.generate_id("Paper §3 Polish")
    assert id1.startswith("spawn-")
    assert "paper" in id1
    assert "polish" in id1

    id2 = agent_mgr.generate_id("Feed Scorer v2")
    assert "feed-scorer" in id2


def test_spawn_resolves_model_alias():
    """Model aliases like 'sonnet' resolve to full model IDs."""
    mock_proc = MagicMock()
    mock_proc.pid = 11111

    with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
        entry = agent_mgr.spawn(name="Alias Test", task="test", model="opus")

    assert entry["model"] == "claude-opus-4-6"
    call_args = mock_popen.call_args
    assert "claude-opus-4-6" in call_args[0][0]


# ── Status Tests ────────────────────────────────────────

def test_update_status_detects_completed():
    """update_status marks dead processes as completed."""
    _make_entry("Dead Agent", status="running", pid=99999)

    with patch.object(agent_mgr, "_is_pid_alive", return_value=False):
        with patch("os.waitpid", side_effect=ChildProcessError):
            entries = agent_mgr.update_status()

    assert entries[0]["status"] == "completed"
    assert entries[0]["completed_at"] is not None
    assert entries[0]["duration_s"] is not None


def test_update_status_preserves_running():
    """update_status keeps alive processes as running."""
    _make_entry("Alive Agent", status="running", pid=99999)

    with patch.object(agent_mgr, "_is_pid_alive", return_value=True):
        entries = agent_mgr.update_status()

    assert entries[0]["status"] == "running"


# ── Dashboard Tests ─────────────────────────────────────

def test_dashboard_formatting():
    """Dashboard produces a readable table with headers."""
    _make_entry("Agent Alpha", status="running", pid=99999)
    _make_entry("Agent Beta", status="completed", completed=True, exit_code=0)

    with patch.object(agent_mgr, "_is_pid_alive", return_value=True):
        output = agent_mgr.get_dashboard(include_completed=True)

    assert "Agent Alpha" in output
    assert "Agent Beta" in output
    assert "RUNNING" in output
    assert "COMPLETED" in output
    assert "+" in output  # box drawing separators
    assert "Name" in output  # header


def test_dashboard_name_filter():
    """Dashboard filters by name glob pattern."""
    _make_entry("Paper Draft", status="running", pid=99999)
    _make_entry("Feed Scorer", status="running", pid=99998)

    with patch.object(agent_mgr, "_is_pid_alive", return_value=True):
        output = agent_mgr.get_dashboard(filter_name="Paper*")

    assert "Paper Draft" in output
    assert "Feed Scorer" not in output


def test_dashboard_empty():
    """Dashboard shows message when no agents match."""
    output = agent_mgr.get_dashboard()
    assert "No agents found" in output


# ── Cleanup Tests ───────────────────────────────────────

def test_cleanup_removes_old():
    """Cleanup removes completed entries older than threshold."""
    _make_entry("Old Done", status="completed", completed=True,
                spawned_minutes_ago=120)
    _make_entry("Still Running", status="running", pid=99999)

    removed = agent_mgr.cleanup(older_than_minutes=60)
    assert removed == 1

    entries = agent_mgr._read_entries()
    assert len(entries) == 1
    assert entries[0]["name"] == "Still Running"


def test_cleanup_preserves_recent():
    """Cleanup preserves recently completed entries."""
    _make_entry("Just Done", status="completed", completed=True,
                spawned_minutes_ago=5)

    removed = agent_mgr.cleanup(older_than_minutes=60)
    assert removed == 0

    entries = agent_mgr._read_entries()
    assert len(entries) == 1


# ── History Tests ───────────────────────────────────────

def test_history_filter_by_name():
    """History filters entries by name glob."""
    _make_entry("Paper A", spawned_minutes_ago=5)
    _make_entry("Feed X", spawned_minutes_ago=10)
    _make_entry("Paper B", spawned_minutes_ago=15)

    history = agent_mgr.get_history(name_filter="Paper*")
    assert len(history) == 2
    assert all("Paper" in e["name"] for e in history)


def test_history_filter_by_date():
    """History --today filters to today's entries only."""
    _make_entry("Today Agent", spawned_minutes_ago=5)

    history = agent_mgr.get_history(today_only=True)
    assert len(history) == 1
    assert history[0]["name"] == "Today Agent"


def test_history_limit():
    """History respects limit parameter."""
    for i in range(5):
        _make_entry(f"Agent {i}", spawned_minutes_ago=i + 1)

    history = agent_mgr.get_history(limit=3)
    assert len(history) == 3


# ── Kill Tests ──────────────────────────────────────────

def test_kill_by_name_pattern():
    """Kill terminates matching running agents."""
    _make_entry("Paper Draft", status="running", pid=99999)
    _make_entry("Feed Scorer", status="running", pid=99998)

    with patch.object(agent_mgr, "_is_pid_alive", return_value=True):
        with patch("os.kill") as mock_kill:
            killed = agent_mgr.kill_agents(name_pattern="Paper*")

    assert len(killed) == 1
    assert "paper" in killed[0]
    # SIGTERM sent to PID
    mock_kill.assert_called_once_with(99999, agent_mgr.signal.SIGTERM)


def test_kill_by_id():
    """Kill by exact ID works."""
    entry = _make_entry("Target Agent", status="running", pid=88888)

    with patch.object(agent_mgr, "_is_pid_alive", return_value=True):
        with patch("os.kill"):
            killed = agent_mgr.kill_agents(agent_id=entry["id"])

    assert len(killed) == 1


# ── Edge Cases ──────────────────────────────────────────

def test_slugify_special_chars():
    """Slugify handles unicode and special characters."""
    assert agent_mgr._slugify("Paper §3 Polish") == "paper-3-polish"
    assert agent_mgr._slugify("Hello World!!!") == "hello-world"
    assert agent_mgr._slugify("") == "agent"


def test_parse_duration():
    """Duration parsing handles m, h, s suffixes."""
    assert agent_mgr._parse_duration("30m") == 30
    assert agent_mgr._parse_duration("2h") == 120
    assert agent_mgr._parse_duration("120s") == 2


def test_concurrent_appends(tmp_registry):
    """Multiple appends don't corrupt the registry."""
    for i in range(10):
        _make_entry(f"Concurrent {i}", spawned_minutes_ago=i)

    entries = agent_mgr._read_entries()
    assert len(entries) == 10


def test_generate_id_uniqueness():
    """IDs generated for the same name are unique (random suffix)."""
    ids = {agent_mgr.generate_id("Same Name") for _ in range(20)}
    assert len(ids) == 20


def test_kill_already_dead_updates_registry():
    """Kill updates registry even when process is already dead."""
    entry = _make_entry("Dead Agent", status="running", pid=99999)

    with patch.object(agent_mgr, "_is_pid_alive", return_value=True):
        with patch("os.kill", side_effect=ProcessLookupError):
            killed = agent_mgr.kill_agents(agent_id=entry["id"])

    assert len(killed) == 1
    entries = agent_mgr._read_entries()
    assert entries[0]["status"] == "completed"
    assert entries[0]["completed_at"] is not None


def test_spawn_with_timeout():
    """Spawn with timeout wraps command with timeout prefix."""
    mock_proc = MagicMock()
    mock_proc.pid = 12345

    with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
        agent_mgr.spawn(name="Timeout Test", task="test", timeout=300)

    cmd = mock_popen.call_args[0][0]
    assert cmd[0] == "timeout"
    assert cmd[1] == "300"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
