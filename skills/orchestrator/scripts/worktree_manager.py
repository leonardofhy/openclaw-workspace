#!/usr/bin/env python3
"""Git worktree isolation for orchestrator tasks.

Each CC agent gets its own worktree so there are no concurrent writes to main.
After all CCs in a wave complete, the orchestrator merges them sequentially.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
WORKTREES_DIR = REPO_ROOT / ".worktrees"


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


def create_worktree(task_id: str) -> Path:
    """Create an isolated worktree for a task. Returns worktree path."""
    wt_path = WORKTREES_DIR / task_id
    branch = f"orchestrator/{task_id}"

    if wt_path.exists():
        raise FileExistsError(f"Worktree already exists: {wt_path}")

    WORKTREES_DIR.mkdir(parents=True, exist_ok=True)
    _git("worktree", "add", str(wt_path), "-b", branch)
    return wt_path


def cleanup_worktree(task_id: str) -> None:
    """Remove a worktree and its branch."""
    wt_path = WORKTREES_DIR / task_id
    branch = f"orchestrator/{task_id}"

    if wt_path.exists():
        _git("worktree", "remove", str(wt_path), "--force")

    # Delete branch if it still exists
    try:
        _git("branch", "-D", branch)
    except RuntimeError:
        pass  # Branch already gone


def commit_worktree(task_id: str) -> bool:
    """Stage and commit all changes in a worktree. Returns True if there were changes."""
    wt_path = WORKTREES_DIR / task_id
    if not wt_path.exists():
        return False

    # Check if there are any changes to commit
    status = _git("status", "--porcelain", cwd=wt_path)
    if not status.strip():
        return False

    _git("add", "-A", cwd=wt_path)
    _git("commit", "-m", f"orchestrator: {task_id} artifacts", cwd=wt_path)
    return True


def merge_worktree(task_id: str) -> str:
    """Commit worktree changes, then merge into current branch. Returns merge output."""
    branch = f"orchestrator/{task_id}"

    # Commit any uncommitted dirty state in the worktree first (may be a no-op if
    # the CC agent already committed its own work — that's fine).
    commit_worktree(task_id)

    # Check if the branch has any commits ahead of the current HEAD.
    # This handles the case where commit_worktree returned False but the CC agent
    # already committed on its own branch.
    try:
        ahead = _git("rev-list", "--count", f"HEAD..{branch}")
        if int(ahead) == 0:
            return f"No changes to merge for {task_id}"
    except RuntimeError:
        return f"No changes to merge for {task_id}"

    return _git("merge", branch, "--no-edit", "-m", f"merge: orchestrator/{task_id}")


def cleanup_all() -> None:
    """Remove all orchestrator worktrees."""
    if not WORKTREES_DIR.exists():
        return

    # List worktrees
    output = _git("worktree", "list", "--porcelain")
    worktree_paths = []
    for line in output.split("\n"):
        if line.startswith("worktree ") and str(WORKTREES_DIR) in line:
            worktree_paths.append(line.split("worktree ", 1)[1])

    # Remove each
    for wt in worktree_paths:
        try:
            _git("worktree", "remove", wt, "--force")
        except RuntimeError:
            pass

    # Clean up branches
    try:
        branches = _git("branch", "--list", "orchestrator/*")
        for branch in branches.strip().split("\n"):
            branch = branch.strip()
            if branch:
                try:
                    _git("branch", "-D", branch)
                except RuntimeError:
                    pass
    except RuntimeError:
        pass

    # Remove directory if empty
    if WORKTREES_DIR.exists():
        try:
            WORKTREES_DIR.rmdir()
        except OSError:
            pass
