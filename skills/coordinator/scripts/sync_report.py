#!/usr/bin/env python3
"""Generate a sync report for inter-bot coordination.

Usage:
    sync_report.py          # human-readable
    sync_report.py --json   # structured JSON
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
TASK_BOARD = WORKSPACE / "memory" / "task-board.md"
EXPERIMENTS = WORKSPACE / "memory" / "experiments" / "experiments.jsonl"


def git_status() -> dict:
    """Get git sync status."""
    result = {}
    try:
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=WORKSPACE, text=True
        ).strip()
        result["branch"] = branch

        # Check for uncommitted changes
        status = subprocess.check_output(
            ["git", "status", "--short"], cwd=WORKSPACE, text=True
        ).strip()
        result["uncommitted"] = len(status.splitlines()) if status else 0

        # Check unpushed commits
        try:
            unpushed = subprocess.check_output(
                ["git", "log", f"origin/{branch}..HEAD", "--oneline"],
                cwd=WORKSPACE, text=True, stderr=subprocess.DEVNULL
            ).strip()
            result["unpushed"] = len(unpushed.splitlines()) if unpushed else 0
        except subprocess.CalledProcessError:
            result["unpushed"] = "unknown"

        # Check how far behind other branches
        for other in ["macbook-m3", "lab-desktop"]:
            if other == branch:
                continue
            try:
                behind = subprocess.check_output(
                    ["git", "log", f"HEAD..origin/{other}", "--oneline"],
                    cwd=WORKSPACE, text=True, stderr=subprocess.DEVNULL
                ).strip()
                result[f"behind_{other}"] = len(behind.splitlines()) if behind else 0
            except subprocess.CalledProcessError:
                result[f"behind_{other}"] = "unknown"

    except (subprocess.CalledProcessError, FileNotFoundError):
        result["error"] = "git not available"
    return result


def task_summary() -> dict:
    """Summarize task board by owner."""
    if not TASK_BOARD.exists():
        return {"error": "task-board.md not found"}

    import re
    text = TASK_BOARD.read_text()
    tasks = {"lab": {}, "mac": {}}

    section = None
    current_owner = None
    for line in text.splitlines():
        if line.startswith("## ACTIVE"):
            section = "active"
        elif line.startswith("## WAITING"):
            section = "waiting"
        elif line.startswith("## BLOCKED"):
            section = "blocked"
        elif line.startswith("## PARKED"):
            section = "parked"
        elif line.startswith("## DONE"):
            section = "done"
        elif line.startswith("## ") or line.startswith("---"):
            section = None

        m = re.match(r"^### ([A-Z])-(\d+\w?)\s*\|\s*(.+)", line)
        if m and section:
            prefix = m.group(1)
            owner = "lab" if prefix == "L" else "mac" if prefix == "M" else "unknown"
            current_owner = owner
            tasks[owner].setdefault(section, [])
            tasks[owner][section].append(f"{prefix}-{m.group(2)} {m.group(3).strip()}")

    summary = {}
    for owner in ["lab", "mac"]:
        summary[owner] = {
            status: len(items)
            for status, items in tasks[owner].items()
        }
        summary[owner]["details"] = tasks[owner]
    return summary


def experiment_summary() -> dict:
    """Summarize experiments."""
    if not EXPERIMENTS.exists():
        return {"total": 0}

    experiments = []
    for line in EXPERIMENTS.read_text().strip().splitlines():
        if line.strip():
            try:
                experiments.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    by_status = {}
    by_machine = {}
    for e in experiments:
        s = e.get("status", "unknown")
        m = e.get("machine", "unknown")
        by_status[s] = by_status.get(s, 0) + 1
        by_machine[m] = by_machine.get(m, 0) + 1

    return {
        "total": len(experiments),
        "by_status": by_status,
        "by_machine": by_machine,
    }


def main():
    use_json = "--json" in sys.argv
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    git = git_status()
    tasks = task_summary()
    exps = experiment_summary()

    if use_json:
        print(json.dumps({
            "timestamp": now,
            "git": git,
            "tasks": tasks,
            "experiments": exps,
        }, ensure_ascii=False, indent=2))
        return

    print(f"📊 Sync Report — {now}")
    print("=" * 50)

    # Git
    print(f"\n🔀 Git")
    print(f"   Branch: {git.get('branch', '?')}")
    print(f"   Uncommitted: {git.get('uncommitted', '?')}")
    print(f"   Unpushed: {git.get('unpushed', '?')}")
    for key, val in git.items():
        if key.startswith("behind_"):
            other = key.replace("behind_", "")
            print(f"   Behind {other}: {val} commits")

    # Tasks
    print(f"\n📋 Tasks")
    for owner in ["lab", "mac"]:
        info = tasks.get(owner, {})
        details = info.pop("details", {})
        counts = " / ".join(f"{k}: {v}" for k, v in info.items() if k != "details")
        print(f"   {owner.upper()}: {counts or 'no tasks'}")
        for status, items in details.items():
            if status != "done":
                for item in items:
                    print(f"     {'🔵' if status == 'active' else '⏳' if status == 'waiting' else '🔴'} {item}")

    # Experiments
    print(f"\n🧪 Experiments: {exps['total']} total")
    if exps.get("by_status"):
        print(f"   Status: {exps['by_status']}")
    if exps.get("by_machine"):
        print(f"   Machine: {exps['by_machine']}")

    print(f"\n{'=' * 50}")


if __name__ == "__main__":
    main()
