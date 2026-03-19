#!/usr/bin/env python3
"""Manifest CRUD — task DAG management with file locking.

Schema: see SKILL.md for full manifest.json spec.
"""

import fcntl
import json
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_manifest(name: str) -> dict:
    """Create a blank manifest dict."""
    return {
        "version": 1,
        "created": _now(),
        "pipeline_name": name,
        "tasks": {},
        "waves": [],
    }


def _lock_path(p: Path) -> Path:
    return p.with_suffix(".lock")


def load(path: str | Path) -> dict:
    """Load manifest with file lock."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Manifest not found: {p}")
    lp = _lock_path(p)
    lp.touch(exist_ok=True)
    with open(lp) as lf:
        fcntl.flock(lf, fcntl.LOCK_SH)
        try:
            return json.loads(p.read_text())
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def save(path: str | Path, manifest: dict) -> None:
    """Save manifest with exclusive file lock (atomic via lock file)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lp = _lock_path(p)
    lp.touch(exist_ok=True)
    with open(lp) as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            p.write_text(json.dumps(manifest, indent=2) + "\n")
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


_TASK_DEFAULTS = {
    "status": "pending",
    "model": "claude-sonnet-4-20250514",
    "timeout": 300,
    "retries": 3,
    "retry_count": 0,
    "artifacts": [],
    "workdir": None,
    "started_at": None,
    "completed_at": None,
    "error": None,
    "session_id": None,
}


def add_task(
    manifest: dict,
    task_id: str,
    *,
    prompt: str | None = None,
    prompt_file: str | None = None,
    depends_on: list[str] | None = None,
    model: str | None = None,
    timeout: int | None = None,
    retries: int | None = None,
) -> dict:
    """Add a task to the manifest. Returns the task dict."""
    if task_id in manifest["tasks"]:
        raise ValueError(f"Task '{task_id}' already exists")
    if not prompt and not prompt_file:
        raise ValueError("Must provide prompt or prompt_file")

    task = dict(_TASK_DEFAULTS)
    if prompt:
        task["prompt"] = prompt
    if prompt_file:
        task["prompt_file"] = prompt_file
    task["depends_on"] = depends_on or []
    if model:
        task["model"] = model
    if timeout is not None:
        task["timeout"] = timeout
    if retries is not None:
        task["retries"] = retries

    manifest["tasks"][task_id] = task
    return task


def update_status(
    manifest: dict,
    task_id: str,
    status: str,
    *,
    error: str | None = None,
    artifacts: list[str] | None = None,
) -> None:
    """Update task status and optional fields."""
    if task_id not in manifest["tasks"]:
        raise KeyError(f"Task '{task_id}' not found")
    valid = ("pending", "running", "completed", "failed", "skipped")
    if status not in valid:
        raise ValueError(f"Invalid status '{status}', must be one of {valid}")

    task = manifest["tasks"][task_id]
    task["status"] = status
    if status == "running":
        task["started_at"] = _now()
    if status in ("completed", "failed"):
        task["completed_at"] = _now()
    if error is not None:
        task["error"] = error
    if artifacts is not None:
        task["artifacts"] = artifacts


def get_ready_tasks(manifest: dict) -> list[str]:
    """Return task IDs whose dependencies are all 'completed' and status is 'pending'."""
    ready = []
    for tid, task in manifest["tasks"].items():
        if task["status"] != "pending":
            continue
        deps = task.get("depends_on", [])
        if all(
            manifest["tasks"].get(d, {}).get("status") == "completed"
            for d in deps
        ):
            ready.append(tid)
    return sorted(ready)


def compute_waves(manifest: dict) -> list[list[str]]:
    """Topological sort into execution waves (Kahn's algorithm)."""
    tasks = manifest["tasks"]
    task_ids = set(tasks.keys())

    # Validate dependencies exist
    for tid, task in tasks.items():
        for dep in task.get("depends_on", []):
            if dep not in task_ids:
                raise ValueError(f"Task '{tid}' depends on unknown task '{dep}'")

    # Build in-degree map
    in_degree = {tid: 0 for tid in task_ids}
    dependents: dict[str, list[str]] = {tid: [] for tid in task_ids}
    for tid, task in tasks.items():
        for dep in task.get("depends_on", []):
            in_degree[tid] += 1
            dependents[dep].append(tid)

    # Kahn's algorithm
    waves: list[list[str]] = []
    queue = sorted([tid for tid, deg in in_degree.items() if deg == 0])

    processed = 0
    while queue:
        waves.append(queue)
        next_queue = []
        for tid in queue:
            processed += 1
            for dep_tid in dependents[tid]:
                in_degree[dep_tid] -= 1
                if in_degree[dep_tid] == 0:
                    next_queue.append(dep_tid)
        queue = sorted(next_queue)

    if processed != len(task_ids):
        raise ValueError("Cycle detected in task dependencies")

    return waves


def validate(manifest: dict) -> list[str]:
    """Validate manifest. Returns list of errors (empty = valid)."""
    errors = []
    tasks = manifest.get("tasks", {})

    if not tasks:
        errors.append("No tasks defined")
        return errors

    task_ids = set(tasks.keys())
    for tid, task in tasks.items():
        # Check required fields
        if not task.get("prompt") and not task.get("prompt_file"):
            errors.append(f"Task '{tid}' has no prompt or prompt_file")
        # Check deps exist
        for dep in task.get("depends_on", []):
            if dep not in task_ids:
                errors.append(f"Task '{tid}' depends on unknown task '{dep}'")

    # Check for cycles
    try:
        compute_waves(manifest)
    except ValueError as e:
        if "Cycle" in str(e):
            errors.append(str(e))

    return errors


def get_stats(manifest: dict) -> dict[str, int]:
    """Count tasks by status."""
    stats: dict[str, int] = {}
    for task in manifest["tasks"].values():
        s = task.get("status", "unknown")
        stats[s] = stats.get(s, 0) + 1
    stats["total"] = len(manifest["tasks"])
    return stats
