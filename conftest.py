"""Root conftest.py – workspace-wide pytest fixtures and path setup."""
import sys
import tempfile
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Auto-add each test file's parent directory to sys.path so sibling imports
# work without per-file sys.path hacks.
# ---------------------------------------------------------------------------
def pytest_collect_file(parent, file_path):
    """Called for every collected file; ensures its directory is importable."""
    d = str(file_path.parent)
    if d not in sys.path:
        sys.path.insert(0, d)
    # Also ensure skills/lib is always available (common utilities)
    lib_dir = str(WORKSPACE / "skills" / "lib")
    if lib_dir not in sys.path:
        sys.path.insert(0, lib_dir)
    # Return None – we don't want to override collection, just inject paths.
    return None


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def tmp_workspace(tmp_path):
    """Provide a temporary workspace directory pre-populated with skeleton."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "skills").mkdir()
    (ws / "skills" / "shared").mkdir()
    return ws


@pytest.fixture
def mock_state(tmp_path):
    """Provide a clean temporary directory for state files."""
    state = tmp_path / "state"
    state.mkdir()
    return state
