#!/usr/bin/env python3
"""daily_growth_report.py — Comprehensive daily growth report generator.

Reads memory logs, git history, experiment results, and task board changes
to produce a polished report for Leo's morning review.

Usage:
    python3 skills/shared/daily_growth_report.py                    # today
    python3 skills/shared/daily_growth_report.py --date 2026-03-18  # specific date
    python3 skills/shared/daily_growth_report.py --json             # machine-readable
    python3 skills/shared/daily_growth_report.py --send-discord     # post to #bot-logs
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parent.parent.parent
MEMORY_DIR = WORKSPACE / "memory"
REPORTS_DIR = MEMORY_DIR / "reports"
EVENTS_JSONL = MEMORY_DIR / "learning" / "logs" / "events.jsonl"
QUEUE_JSON = MEMORY_DIR / "learning" / "state" / "queue.json"
ACTIVE_JSON = MEMORY_DIR / "learning" / "state" / "active.json"
DOCS_DIR = WORKSPACE / "docs"

sys.path.insert(0, str(WORKSPACE / "skills" / "shared"))


# ── Git Collector ────────────────────────────────────────────────────────

def collect_git(target_date: date) -> dict[str, Any]:
    """Collect git stats for the target date."""
    iso = target_date.isoformat()
    since = f"{iso}T00:00:00"
    until = f"{iso}T23:59:59"
    result: dict[str, Any] = {
        "commits": 0, "added": 0, "removed": 0,
        "files_changed": 0, "messages": [],
    }

    try:
        log = subprocess.run(
            ["git", "log", "--after", since, "--before", until,
             "--pretty=format:%H|%s", "--shortstat"],
            capture_output=True, text=True, cwd=str(WORKSPACE), timeout=15,
        )
        if log.returncode != 0:
            return result
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return result

    for line in log.stdout.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if "|" in line and len(line.split("|")[0]) == 40:
            parts = line.split("|", 1)
            result["commits"] += 1
            result["messages"].append(parts[1].strip() if len(parts) > 1 else "")
        else:
            m_f = re.search(r"(\d+) files? changed", line)
            m_a = re.search(r"(\d+) insertions?", line)
            m_d = re.search(r"(\d+) deletions?", line)
            if m_f:
                result["files_changed"] += int(m_f.group(1))
            if m_a:
                result["added"] += int(m_a.group(1))
            if m_d:
                result["removed"] += int(m_d.group(1))

    return result


# ── Memory Log Reader ────────────────────────────────────────────────────

def read_daily_log(target_date: date) -> str | None:
    """Read memory/YYYY-MM-DD.md for the target date."""
    p = MEMORY_DIR / f"{target_date.isoformat()}.md"
    if p.exists():
        return p.read_text()
    return None


# ── Experiment Collector ─────────────────────────────────────────────────

def collect_experiments(target_date: date) -> dict[str, Any]:
    """Collect experiment results from research dashboard JSON."""
    result: dict[str, Any] = {
        "total": 0, "pass": 0, "blocked": 0, "real": 0, "mock": 0,
        "pass_rate": 0.0, "strongest": [], "weakest": [],
    }

    try:
        proc = subprocess.run(
            [sys.executable, str(WORKSPACE / "skills" / "shared" / "research_dashboard.py"),
             "--json"],
            capture_output=True, text=True, cwd=str(WORKSPACE), timeout=30,
        )
        if proc.returncode != 0:
            return result
        data = json.loads(proc.stdout)
        exp = data.get("experiments", {})
        result["total"] = exp.get("total", 0)
        result["pass"] = exp.get("pass", 0)
        result["blocked"] = exp.get("blocked", 0)
        result["real"] = exp.get("real", 0)
        result["mock"] = exp.get("mock", 0)
        result["pass_rate"] = exp.get("pass_rate", 0.0)
        result["strongest"] = exp.get("strongest", [])[:3]
        result["weakest"] = exp.get("weakest", [])[:3]
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass

    return result


# ── Paper Progress ───────────────────────────────────────────────────────

PAPER_FILES = {
    "Abstract": "paper-a-abstract.md",
    "Intro & RW": "paper-a-intro-rw.md",
    "Methods": "paper-a-method.md",
    "Results": "paper-a-results.md",
    "Discussion": "paper-a-discussion-stub.md",
}


def collect_paper() -> dict[str, Any]:
    """Word counts and TODO counts for paper sections."""
    result: dict[str, Any] = {"sections": {}, "total_words": 0, "total_todos": 0}
    for label, fname in PAPER_FILES.items():
        p = DOCS_DIR / fname
        wc = len(p.read_text().split()) if p.exists() else 0
        todos = len(re.findall(r"TODO|FIXME|XXX", p.read_text(), re.IGNORECASE)) if p.exists() else 0
        result["sections"][label] = {"words": wc, "todos": todos}
        result["total_words"] += wc
        result["total_todos"] += todos
    return result


# ── Test Collector ───────────────────────────────────────────────────────

def collect_tests() -> dict[str, Any]:
    """Count tests via pytest --collect-only."""
    result: dict[str, Any] = {"total": 0, "error": None}
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q"],
            capture_output=True, text=True, cwd=str(WORKSPACE), timeout=30,
        )
        m = re.search(r"(\d+) tests? collected", proc.stdout)
        if m:
            result["total"] = int(m.group(1))
        elif proc.returncode != 0:
            result["error"] = "pytest collection failed"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        result["error"] = "pytest not available"
    return result


# ── Task Board Collector ─────────────────────────────────────────────────

def collect_task_board() -> dict[str, Any]:
    """Parse task-board.md for status counts."""
    result: dict[str, Any] = {"total": 0, "by_status": {}, "stale": 0}
    tb = WORKSPACE / "task-board.md"
    if not tb.exists():
        return result

    for line in tb.read_text().splitlines():
        line = line.strip()
        if not line.startswith("- ["):
            continue
        result["total"] += 1
        if line.startswith("- [x]"):
            result["by_status"]["done"] = result["by_status"].get("done", 0) + 1
        elif "🔴" in line or "BLOCKED" in line.upper():
            result["by_status"]["blocked"] = result["by_status"].get("blocked", 0) + 1
        elif "⚠️" in line or "STALE" in line.upper():
            result["stale"] += 1
            result["by_status"]["stale"] = result["by_status"].get("stale", 0) + 1
        else:
            result["by_status"]["open"] = result["by_status"].get("open", 0) + 1

    return result


# ── CC Agent Counter ─────────────────────────────────────────────────────

def count_cc_agents(log_text: str | None) -> int:
    """Count CC agent spawns mentioned in daily log."""
    if not log_text:
        return 0
    return len(re.findall(r"CC#\d+", log_text))


# ── Highlight Extractor ──────────────────────────────────────────────────

def extract_highlights(log_text: str | None, git_data: dict, exp_data: dict) -> list[str]:
    """Extract top 3-5 highlights from the day."""
    highlights: list[str] = []

    if log_text:
        # Look for sections with specific markers
        for pattern in [r"### (.+?（完成）)", r"### (.+?breakthrough)", r"### (.+?refactor)"]:
            for m in re.finditer(pattern, log_text, re.IGNORECASE):
                highlights.append(m.group(1))

        # Check for experiment completions
        exp_match = re.findall(r"\*\*(\w+ 完成)\*\*", log_text)
        highlights.extend(exp_match[:2])

        # Check for key features
        feat_match = re.findall(r"\*\*(\w+\.py)\*\*[：:]\s*(.+?)(?:\n|$)", log_text)
        for fname, desc in feat_match[:3]:
            highlights.append(f"{fname}: {desc[:80]}")

    # From git commit messages
    feat_commits = [m for m in git_data.get("messages", []) if m.startswith("feat:")]
    for msg in feat_commits[:2]:
        if len(highlights) < 5:
            highlights.append(msg)

    # Experiment summary
    if exp_data.get("total", 0) > 0:
        highlights.append(
            f"{exp_data['total']} experiments ({exp_data['pass']} pass, "
            f"{exp_data['blocked']} blocked, {exp_data['pass_rate']:.0f}% rate)"
        )

    return highlights[:5] or ["No major highlights recorded"]


# ── Tomorrow Priorities ──────────────────────────────────────────────────

def infer_priorities(log_text: str | None, exp_data: dict, paper: dict, tasks: dict) -> list[str]:
    """Infer tomorrow's priorities."""
    priorities: list[str] = []

    # From daily log "Next steps" section
    if log_text:
        in_next = False
        for line in log_text.splitlines():
            if "next step" in line.lower() or "tomorrow" in line.lower():
                in_next = True
                continue
            if in_next and line.strip().startswith("- "):
                item = line.strip().lstrip("- ").split("—")[0].strip()
                if item and len(priorities) < 5:
                    priorities.append(item)
            elif in_next and line.strip().startswith("#"):
                in_next = False

    # Blocked experiments
    if exp_data.get("blocked", 0) > 0:
        priorities.append(f"Unblock {exp_data['blocked']} blocked experiment(s)")

    # Paper TODOs
    if paper.get("total_todos", 0) > 5:
        priorities.append(f"Paper A: {paper['total_todos']} TODOs remaining")

    return priorities[:5] or ["Review task board and pick highest-priority work"]


# ── Aggregate All Data ───────────────────────────────────────────────────

def collect_all(target_date: date, skip_tests: bool = False) -> dict[str, Any]:
    """Collect all data sources into a single dict."""
    log_text = read_daily_log(target_date)
    git = collect_git(target_date)
    experiments = collect_experiments(target_date)
    paper = collect_paper()
    tasks = collect_task_board()
    tests = collect_tests() if not skip_tests else {"total": 0, "error": "skipped"}

    return {
        "date": target_date.isoformat(),
        "log_text": log_text,
        "git": git,
        "experiments": experiments,
        "paper": paper,
        "tasks": tasks,
        "tests": tests,
        "cc_agents": count_cc_agents(log_text),
        "highlights": extract_highlights(log_text, git, experiments),
        "priorities": infer_priorities(log_text, experiments, paper, tasks),
    }


# ── Markdown Report Formatter ────────────────────────────────────────────

def format_report(data: dict) -> str:
    """Generate the structured markdown growth report."""
    d = data["date"]
    git = data["git"]
    exp = data["experiments"]
    paper = data["paper"]
    tasks = data["tasks"]
    tests = data["tests"]
    highlights = data["highlights"]
    priorities = data["priorities"]

    lines: list[str] = []
    lines.append(f"## 📊 Daily Growth Report — {d}")
    lines.append("")

    # ── Highlights ──
    lines.append("### Highlights")
    for i, h in enumerate(highlights, 1):
        lines.append(f"{i}. {h}")
    lines.append("")

    # ── Research Progress ──
    lines.append("### Research Progress")
    if exp["total"] > 0:
        lines.append(f"- **Experiments**: {exp['total']} total — "
                      f"{exp['pass']} pass, {exp['blocked']} blocked "
                      f"({exp['pass_rate']:.1f}% rate)")
        lines.append(f"  - Real: {exp['real']} | Mock: {exp['mock']}")
        if exp["strongest"]:
            top = exp["strongest"][0]
            lines.append(f"  - Strongest: {top.get('id', '?')} {top.get('name', '')} "
                          f"(r={top.get('r', '?')})")
    else:
        lines.append("- No experiment data available")

    lines.append(f"- **Paper A**: {paper['total_words']:,} words across "
                  f"{len(paper['sections'])} sections, {paper['total_todos']} TODOs")
    for label, info in paper["sections"].items():
        if info["words"] > 0:
            lines.append(f"  - {label}: {info['words']:,} words"
                          + (f" ({info['todos']} TODOs)" if info["todos"] else ""))
    lines.append("")

    # ── Engineering ──
    lines.append("### Engineering")
    lines.append(f"- Commits: {git['commits']}")
    lines.append(f"- Files changed: {git['files_changed']}")
    lines.append(f"- LOC: +{git['added']:,} / -{git['removed']:,} "
                  f"(net +{git['added'] - git['removed']:,})")
    test_total = tests.get("total", 0)
    if test_total > 0:
        lines.append(f"- Tests collected: {test_total:,}")
    if tests.get("error"):
        lines.append(f"- Tests: {tests['error']}")

    # Notable commits
    feat_msgs = [m for m in git.get("messages", [])
                 if m.startswith(("feat:", "refactor:", "experiment:"))]
    if feat_msgs:
        lines.append("- Notable commits:")
        for msg in feat_msgs[:8]:
            lines.append(f"  - {msg}")
    lines.append("")

    # ── System Health ──
    lines.append("### System Health")
    lines.append(f"- Task board: {tasks['total']} items "
                  + ", ".join(f"{s}: {c}" for s, c in sorted(tasks.get("by_status", {}).items())))
    if tasks.get("stale", 0) > 0:
        lines.append(f"  - ⚠️ {tasks['stale']} stale task(s)")
    lines.append(f"- CC agents spawned: {data['cc_agents']}")
    lines.append("")

    # ── Tomorrow's Priorities ──
    lines.append("### Tomorrow's Priorities")
    for p in priorities:
        lines.append(f"- {p}")
    lines.append("")

    # ── Metrics ──
    lines.append("### Metrics")
    lines.append(f"- Commits: {git['commits']}")
    lines.append(f"- Files changed: {git['files_changed']}")
    lines.append(f"- LOC: +{git['added']:,} / -{git['removed']:,}")
    lines.append(f"- Tests: {test_total:,} collected")
    lines.append(f"- CC agents spawned: {data['cc_agents']}")
    lines.append(f"- Experiments: {exp['pass']} pass / {exp['blocked']} blocked")
    lines.append(f"- Paper A: {paper['total_words']:,} words")
    lines.append("")

    return "\n".join(lines)


# ── Discord Formatter ────────────────────────────────────────────────────

def format_discord(data: dict) -> str:
    """Shorter Discord-friendly format."""
    d = data["date"]
    git = data["git"]
    exp = data["experiments"]
    paper = data["paper"]
    tests = data["tests"]

    lines = [f"**📊 Daily Growth Report — {d}**", ""]
    lines.append("**Highlights**")
    for i, h in enumerate(data["highlights"], 1):
        lines.append(f"{i}. {h}")

    lines.append("")
    lines.append("**Metrics**")
    lines.append(f"```")
    lines.append(f"Commits:     {git['commits']}")
    lines.append(f"LOC:         +{git['added']:,} / -{git['removed']:,}")
    lines.append(f"Tests:       {tests.get('total', 0):,}")
    lines.append(f"Experiments: {exp['pass']} pass / {exp['blocked']} blocked ({exp['pass_rate']:.0f}%)")
    lines.append(f"Paper A:     {paper['total_words']:,} words")
    lines.append(f"CC agents:   {data['cc_agents']}")
    lines.append(f"```")

    lines.append("")
    lines.append("**Tomorrow**")
    for p in data["priorities"]:
        lines.append(f"- {p}")

    return "\n".join(lines)


# ── Save Report ──────────────────────────────────────────────────────────

def save_report(data: dict, content: str) -> Path:
    """Save report to memory/reports/YYYY-MM-DD-growth.md."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"{data['date']}-growth.md"
    p = REPORTS_DIR / fname
    p.write_text(content + "\n")
    return p


# ── Discord Webhook ──────────────────────────────────────────────────────

def send_discord(content: str) -> bool:
    """Post report to Discord #bot-logs via webhook."""
    webhook_url = os.environ.get("DISCORD_WEBHOOK_BOT_LOGS")
    if not webhook_url:
        print("DISCORD_WEBHOOK_BOT_LOGS not set, skipping Discord", file=sys.stderr)
        return False

    payload = json.dumps({"content": content[:2000]}).encode()
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        print(f"Discord send failed: {e}", file=sys.stderr)
        return False


# ── CLI ──────────────────────────────────────────────────────────────────

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate daily growth report")
    parser.add_argument("--date", type=str, default=None,
                        help="Target date (YYYY-MM-DD), defaults to today")
    parser.add_argument("--json", action="store_true", default=False,
                        help="Machine-readable JSON output")
    parser.add_argument("--send-discord", action="store_true", default=False,
                        help="Post to #bot-logs via webhook")
    parser.add_argument("--skip-tests", action="store_true", default=False,
                        help="Skip pytest collection (faster)")
    parser.add_argument("--no-save", action="store_true", default=False,
                        help="Don't save report to disk")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> str:
    args = parse_args(argv)

    target = date.fromisoformat(args.date) if args.date else date.today()

    data = collect_all(target, skip_tests=args.skip_tests)

    if args.json:
        # Remove raw log from JSON (too large)
        json_data = {k: v for k, v in data.items() if k != "log_text"}
        output = json.dumps(json_data, indent=2, default=str)
    else:
        output = format_report(data)

    # Always save unless --no-save
    if not args.no_save and not args.json:
        p = save_report(data, output)
        print(f"Saved: {p}", file=sys.stderr)

    # Discord
    if args.send_discord:
        discord_msg = format_discord(data)
        if send_discord(discord_msg):
            print("Posted to Discord #bot-logs", file=sys.stderr)

    print(output)
    return output


if __name__ == "__main__":
    main()
