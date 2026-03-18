"""Tests for append_memory.py.

Strategy: patch append_memory.WORKSPACE, append_memory.MEMORY_DIR, and
append_memory._now so the script writes into a tmp_path and uses a fixed
timestamp. sys.argv is patched for every test so argparse does not read
pytest's own arguments.
"""

import sys
import importlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Bootstrap: make append_memory importable
# ---------------------------------------------------------------------------
_SCRIPTS = "/Users/leonardo/.openclaw/workspace/skills/remember/scripts"
_LIB     = "/Users/leonardo/.openclaw/workspace/skills/lib"

if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

import append_memory


# ---------------------------------------------------------------------------
# Fixed timestamp used across all tests
# ---------------------------------------------------------------------------
_FIXED_DATETIME = datetime(2026, 3, 18, 14, 30, tzinfo=timezone(timedelta(hours=8)))
_FIXED_TS = "2026-03-18 14:30"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_main(argv: list[str], tmp_workspace: Path, tmp_memory: Path) -> None:
    """Invoke append_memory.main() with patched paths and timestamp."""
    with (
        patch.object(sys, "argv", ["append_memory.py"] + argv),
        patch("append_memory.WORKSPACE", tmp_workspace),
        patch("append_memory.MEMORY_DIR", tmp_memory),
        patch("append_memory._now", return_value=_FIXED_DATETIME),
    ):
        append_memory.main()


# ===========================================================================
# Routing tests
# ===========================================================================

class TestRouting:
    def test_memory_md_routes_to_workspace_root(self, tmp_path: Path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        memory_dir = workspace / "memory"
        memory_dir.mkdir()

        run_main(
            ["--target", "MEMORY.md", "--text", "hello world"],
            workspace,
            memory_dir,
        )

        target_file = workspace / "MEMORY.md"
        assert target_file.exists(), "MEMORY.md should be created at workspace root"

    def test_other_target_routes_to_memory_dir(self, tmp_path: Path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        memory_dir = workspace / "memory"
        memory_dir.mkdir()

        run_main(
            ["--target", "research", "--text", "a new finding"],
            workspace,
            memory_dir,
        )

        target_file = memory_dir / "research.md"
        assert target_file.exists(), "research.md should be created in memory dir"

    def test_core_md_routes_to_memory_dir(self, tmp_path: Path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        memory_dir = workspace / "memory"
        memory_dir.mkdir()

        run_main(
            ["--target", "core", "--text", "core content"],
            workspace,
            memory_dir,
        )

        target_file = memory_dir / "core.md"
        assert target_file.exists(), "core.md should be in memory dir (not workspace root)"


# ===========================================================================
# Extension tests
# ===========================================================================

class TestExtensionHandling:
    def test_md_extension_added_when_missing(self, tmp_path: Path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        memory_dir = workspace / "memory"
        memory_dir.mkdir()

        run_main(
            ["--target", "notes", "--text", "some note"],
            workspace,
            memory_dir,
        )

        assert (memory_dir / "notes.md").exists()

    def test_md_extension_not_doubled_when_present(self, tmp_path: Path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        memory_dir = workspace / "memory"
        memory_dir.mkdir()

        run_main(
            ["--target", "notes.md", "--text", "some note"],
            workspace,
            memory_dir,
        )

        # notes.md should exist, notes.md.md should NOT
        assert (memory_dir / "notes.md").exists()
        assert not (memory_dir / "notes.md.md").exists()


# ===========================================================================
# Entry format tests
# ===========================================================================

class TestEntryFormat:
    def test_entry_contains_fixed_timestamp(self, tmp_path: Path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        memory_dir = workspace / "memory"
        memory_dir.mkdir()

        run_main(
            ["--target", "log", "--text", "entry with timestamp"],
            workspace,
            memory_dir,
        )

        content = (memory_dir / "log.md").read_text(encoding="utf-8")
        assert _FIXED_TS in content

    def test_entry_format_without_tag(self, tmp_path: Path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        memory_dir = workspace / "memory"
        memory_dir.mkdir()

        run_main(
            ["--target", "log", "--text", "plain entry"],
            workspace,
            memory_dir,
        )

        content = (memory_dir / "log.md").read_text(encoding="utf-8")
        expected = f"- `{_FIXED_TS}` plain entry\n"
        assert expected in content

    def test_entry_format_with_tag(self, tmp_path: Path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        memory_dir = workspace / "memory"
        memory_dir.mkdir()

        run_main(
            ["--target", "log", "--text", "tagged entry", "--tag", "decision"],
            workspace,
            memory_dir,
        )

        content = (memory_dir / "log.md").read_text(encoding="utf-8")
        expected = f"- `{_FIXED_TS}` `[DECISION]` tagged entry\n"
        assert expected in content

    def test_tag_is_uppercased(self, tmp_path: Path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        memory_dir = workspace / "memory"
        memory_dir.mkdir()

        run_main(
            ["--target", "log", "--text", "some text", "--tag", "idea"],
            workspace,
            memory_dir,
        )

        content = (memory_dir / "log.md").read_text(encoding="utf-8")
        assert "`[IDEA]`" in content
        assert "`[idea]`" not in content

    def test_entries_are_appended_not_overwritten(self, tmp_path: Path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        memory_dir = workspace / "memory"
        memory_dir.mkdir()

        run_main(["--target", "log", "--text", "first entry"], workspace, memory_dir)
        run_main(["--target", "log", "--text", "second entry"], workspace, memory_dir)

        content = (memory_dir / "log.md").read_text(encoding="utf-8")
        assert "first entry" in content
        assert "second entry" in content
        assert content.count("- `") == 2


# ===========================================================================
# Parent directory creation
# ===========================================================================

class TestDirectoryCreation:
    def test_creates_missing_parent_directory(self, tmp_path: Path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        # memory_dir does NOT exist yet
        memory_dir = workspace / "memory"

        run_main(
            ["--target", "newfile", "--text", "content"],
            workspace,
            memory_dir,
        )

        assert (memory_dir / "newfile.md").exists()


# ===========================================================================
# MEMORY.md target — content correctness
# ===========================================================================

class TestMemoryMdContent:
    def test_memory_md_entry_content(self, tmp_path: Path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        memory_dir = workspace / "memory"
        memory_dir.mkdir()

        run_main(
            ["--target", "MEMORY.md", "--text", "workspace memory entry"],
            workspace,
            memory_dir,
        )

        content = (workspace / "MEMORY.md").read_text(encoding="utf-8")
        assert "workspace memory entry" in content
        assert _FIXED_TS in content
