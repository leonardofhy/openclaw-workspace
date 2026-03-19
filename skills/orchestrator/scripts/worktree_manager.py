#!/usr/bin/env python3
"""Task isolation for orchestrator — rsync-based (v2).

v1 used git worktrees but had fundamental merge conflict issues when
parallel CCs modified overlapping files. v2 uses a simpler approach:

1. CC runs directly in the main workspace (no worktree)
2. Before each wave, we snapshot changed files
3. After each CC, we collect only NEW/MODIFIED files via git diff
4. Conflicts are detected and reported, not silently lost

For truly isolated tasks (different directories), CCs run in-place.
For overlapping tasks, they run sequentially within the wave.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SANDBOX_DIR = REPO_ROOT / ".sandboxes"


def _git(*args: str, cwd: Path | None = None) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _run(*args: str, cwd: Path | None = None) -> str:
    """Run a command and return stdout."""
    result = subprocess.run(
        args,
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def snapshot_state() -> str:
    """Take a snapshot of current git state. Returns the HEAD commit hash."""
    # Commit any pending changes first
    status = _git("status", "--porcelain")
    if status.strip():
        _git("add", "-A")
        _git("commit", "-m", "orchestrator: pre-wave snapshot", "--allow-empty")
    return _git("rev-parse", "HEAD")


def create_sandbox(task_id: str) -> Path:
    """Create an isolated sandbox copy for a task. Returns sandbox path."""
    sandbox = SANDBOX_DIR / task_id
    if sandbox.exists():
        shutil.rmtree(sandbox)

    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

    # rsync workspace to sandbox (exclude heavy dirs)
    _run(
        "rsync", "-a", "--delete",
        "--exclude", ".git",
        "--exclude", ".sandboxes",
        "--exclude", ".worktrees",
        "--exclude", "venv",
        "--exclude", "node_modules",
        "--exclude", "__pycache__",
        str(REPO_ROOT) + "/",
        str(sandbox) + "/",
    )
    return sandbox


def collect_artifacts(task_id: str) -> list[str]:
    """Find new/modified files in a sandbox vs the main workspace.

    Returns list of relative paths that were created or modified.
    """
    sandbox = SANDBOX_DIR / task_id
    if not sandbox.exists():
        return []

    artifacts = []
    for root, dirs, files in os.walk(sandbox):
        # Skip hidden dirs and heavy dirs
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in
                   ('venv', 'node_modules', '__pycache__', '.sandboxes', '.worktrees')]
        for fname in files:
            if fname.startswith('.'):
                continue
            sandbox_file = Path(root) / fname
            rel_path = sandbox_file.relative_to(sandbox)
            main_file = REPO_ROOT / rel_path

            # New file or modified file
            if not main_file.exists():
                artifacts.append(str(rel_path))
            elif sandbox_file.read_bytes() != main_file.read_bytes():
                artifacts.append(str(rel_path))

    return artifacts


def merge_sandbox(task_id: str) -> str:
    """Copy new/modified files from sandbox back to main workspace.

    Returns summary of what was merged.
    """
    sandbox = SANDBOX_DIR / task_id
    if not sandbox.exists():
        return f"No sandbox found for {task_id}"

    artifacts = collect_artifacts(task_id)
    if not artifacts:
        return f"No changes to merge for {task_id}"

    merged = []
    for rel_path in artifacts:
        src = sandbox / rel_path
        dst = REPO_ROOT / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        merged.append(rel_path)

    # Commit merged changes
    _git("add", "-A")
    _git("commit", "-m", f"orchestrator: {task_id} artifacts", "--allow-empty")

    return f"Merged {len(merged)} files: {', '.join(merged[:5])}{'...' if len(merged) > 5 else ''}"


def cleanup_sandbox(task_id: str) -> None:
    """Remove a task's sandbox."""
    sandbox = SANDBOX_DIR / task_id
    if sandbox.exists():
        shutil.rmtree(sandbox)


def cleanup_all() -> None:
    """Remove all sandboxes."""
    if SANDBOX_DIR.exists():
        shutil.rmtree(SANDBOX_DIR)


# ── Backward compatibility aliases ──
# These map old worktree API to new sandbox API so orchestrator.py doesn't break

def create_worktree(task_id: str) -> Path:
    """Compat: create sandbox instead of worktree."""
    return create_sandbox(task_id)


def merge_worktree(task_id: str) -> str:
    """Compat: merge sandbox instead of worktree."""
    return merge_sandbox(task_id)


def cleanup_worktree(task_id: str) -> None:
    """Compat: cleanup sandbox instead of worktree."""
    cleanup_sandbox(task_id)


def commit_worktree(task_id: str) -> bool:
    """Compat: no-op (sandbox doesn't need git commit)."""
    return True
