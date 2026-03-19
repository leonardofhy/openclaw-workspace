#!/usr/bin/env python3
"""daily_digest.py — End-of-day summary generator from workspace activity.

Usage:
    python3 skills/shared/daily_digest.py                  # terminal (default)
    python3 skills/shared/daily_digest.py --terminal        # same
    python3 skills/shared/daily_digest.py --discord          # Discord-friendly
    python3 skills/shared/daily_digest.py --email            # HTML email
    python3 skills/shared/daily_digest.py --save             # append to daily note
    python3 skills/shared/daily_digest.py --date 2026-03-17  # specific date
    python3 skills/shared/daily_digest.py --json             # machine-readable
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parent.parent.parent

# ── Paths ────────────────────────────────────────────────────────────────

EVENTS_JSONL = WORKSPACE / "memory" / "learning" / "logs" / "events.jsonl"
QUEUE_JSON = WORKSPACE / "memory" / "learning" / "state" / "queue.json"
ACTIVE_JSON = WORKSPACE / "memory" / "learning" / "state" / "active.json"
DIGESTS_DIR = WORKSPACE / "memory" / "learning" / "digests" / "daily"
BRIEFINGS_DIR = WORKSPACE / "memory" / "learning" / "briefings"
DOCS_DIR = WORKSPACE / "docs"
CYCLES_DIR = WORKSPACE / "memory" / "learning" / "cycles"


# ── Collector: Git ───────────────────────────────────────────────────────

def collect_git(target_date: date) -> dict:
    """Collect git commit stats for target_date."""
    iso = target_date.isoformat()
    since = f"{iso}T00:00:00"
    until = f"{iso}T23:59:59"
    result: dict[str, Any] = {"commits": 0, "added": 0, "removed": 0, "files_changed": 0, "messages": []}

    try:
        log = subprocess.run(
            ["git", "log", "--after", since, "--before", until,
             "--pretty=format:%H|%s", "--shortstat"],
            capture_output=True, text=True, cwd=str(WORKSPACE), timeout=10,
        )
        if log.returncode != 0:
            return result
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return result

    lines = log.stdout.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if "|" in line and len(line.split("|")[0]) == 40:
            parts = line.split("|", 1)
            result["commits"] += 1
            result["messages"].append(parts[1].strip() if len(parts) > 1 else "")
        else:
            m_files = re.search(r"(\d+) files? changed", line)
            m_add = re.search(r"(\d+) insertions?", line)
            m_del = re.search(r"(\d+) deletions?", line)
            if m_files:
                result["files_changed"] += int(m_files.group(1))
            if m_add:
                result["added"] += int(m_add.group(1))
            if m_del:
                result["removed"] += int(m_del.group(1))

    return result


# ── Collector: Autodidact Events ─────────────────────────────────────────

def collect_autodidact(target_date: date) -> dict:
    """Parse events.jsonl for cycles on target_date."""
    result: dict[str, Any] = {
        "cycles": 0, "actions": {}, "phase": None,
        "highlights": [], "blocked_count": 0,
    }
    if not EVENTS_JSONL.exists():
        return result

    iso_prefix = target_date.isoformat()
    for line in EVENTS_JSONL.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = ev.get("ts", "")
        if not ts.startswith(iso_prefix):
            continue

        result["cycles"] += 1
        action = ev.get("action", "unknown")
        result["actions"][action] = result["actions"].get(action, 0) + 1
        if ev.get("phase"):
            result["phase"] = ev["phase"]
        if ev.get("blocked"):
            result["blocked_count"] += 1

        summary = ev.get("summary", "")
        if summary and action not in ("skip",):
            result["highlights"].append(summary)

    return result


# ── Collector: Active State / Budgets ────────────────────────────────────

def collect_active_state() -> dict:
    """Read active.json for phase, budgets, stats."""
    if not ACTIVE_JSON.exists():
        return {}
    try:
        return json.loads(ACTIVE_JSON.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


# ── Collector: Queue Changes ─────────────────────────────────────────────

def collect_queue() -> dict:
    """Read queue.json for current task status."""
    result: dict[str, Any] = {"total": 0, "by_status": {}, "archived": 0}
    if not QUEUE_JSON.exists():
        return result
    try:
        q = json.loads(QUEUE_JSON.read_text())
    except (json.JSONDecodeError, OSError):
        return result

    tasks = q.get("tasks", [])
    result["total"] = len(tasks)
    result["archived"] = q.get("archived_count", 0)
    for t in tasks:
        status = t.get("status", "unknown")
        result["by_status"][status] = result["by_status"].get(status, 0) + 1
    return result


# ── Collector: Test Count ────────────────────────────────────────────────

def collect_tests() -> dict:
    """Run pytest --collect-only to count tests."""
    result: dict[str, Any] = {"total": 0, "error": None}
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q"],
            capture_output=True, text=True, cwd=str(WORKSPACE), timeout=30,
        )
        # Last line pattern: "X tests collected" or "X test collected"
        m = re.search(r"(\d+) tests? collected", proc.stdout)
        if m:
            result["total"] = int(m.group(1))
        elif proc.returncode != 0:
            result["error"] = "pytest collection failed"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        result["error"] = "pytest not available"
    return result


# ── Collector: Paper Progress ────────────────────────────────────────────

PAPER_FILES = {
    "Abstract": "paper-a-abstract.md",
    "Intro & RW": "paper-a-intro-rw.md",
    "Methods": "paper-a-method.md",
    "Results": "paper-a-results.md",
    "Discussion": "paper-a-discussion-stub.md",
}


def _word_count(path: Path) -> int:
    if not path.exists():
        return 0
    return len(path.read_text().split())


def collect_paper() -> dict:
    """Compute word counts for paper sections."""
    result: dict[str, Any] = {"sections": {}, "total_words": 0, "total_todos": 0}
    for label, fname in PAPER_FILES.items():
        p = DOCS_DIR / fname
        wc = _word_count(p)
        todos = 0
        if p.exists():
            todos = len(re.findall(r"TODO|FIXME|XXX", p.read_text(), re.IGNORECASE))
        result["sections"][label] = {"words": wc, "todos": todos}
        result["total_words"] += wc
        result["total_todos"] += todos

    # LaTeX main file
    tex = DOCS_DIR / "paper-a.tex"
    result["latex_words"] = _word_count(tex) if tex.exists() else 0
    return result


# ── Collector: Daily Notes ───────────────────────────────────────────────

def collect_daily_notes(target_date: date) -> str | None:
    """Read today's briefing if it exists."""
    fname = f"{target_date.isoformat()}.md"
    p = BRIEFINGS_DIR / fname
    if p.exists():
        return p.read_text().strip()
    return None


# ── Collector: Cycle Files ───────────────────────────────────────────────

def collect_cycle_files(target_date: date) -> int:
    """Count cycle files created on target_date."""
    prefix = f"c-{target_date.strftime('%Y%m%d')}-"
    if not CYCLES_DIR.exists():
        return 0
    return sum(1 for f in CYCLES_DIR.iterdir() if f.name.startswith(prefix))


# ── Aggregate ────────────────────────────────────────────────────────────

def collect_all(target_date: date, skip_tests: bool = False) -> dict:
    """Collect all data sources into a single dict."""
    data: dict[str, Any] = {
        "date": target_date.isoformat(),
        "git": collect_git(target_date),
        "autodidact": collect_autodidact(target_date),
        "active": collect_active_state(),
        "queue": collect_queue(),
        "paper": collect_paper(),
        "daily_notes": collect_daily_notes(target_date),
        "cycle_files": collect_cycle_files(target_date),
    }
    if not skip_tests:
        data["tests"] = collect_tests()
    else:
        data["tests"] = {"total": 0, "error": "skipped"}
    return data


# ── Highlights Extractor ─────────────────────────────────────────────────

def extract_highlights(data: dict) -> list[str]:
    """Pick top 3 highlights from the day's activity."""
    highlights: list[str] = []

    # From autodidact summaries (first 3 non-skip)
    for s in data.get("autodidact", {}).get("highlights", []):
        short = s[:120] + "..." if len(s) > 120 else s
        highlights.append(short)
        if len(highlights) >= 3:
            break

    # From git if we have commits but no autodidact
    if not highlights:
        for msg in data.get("git", {}).get("messages", [])[:3]:
            highlights.append(msg)

    return highlights or ["No activity recorded"]


# ── Tomorrow's Priorities ────────────────────────────────────────────────

def infer_priorities(data: dict) -> list[str]:
    """Infer tomorrow's priorities from stale tasks and autodidact next."""
    priorities: list[str] = []

    # Blocked tasks
    queue = data.get("queue", {})
    blocked = queue.get("by_status", {}).get("blocked", 0)
    if blocked:
        priorities.append(f"Unblock {blocked} blocked task(s)")

    # Paper TODOs
    paper = data.get("paper", {})
    if paper.get("total_todos", 0) > 0:
        priorities.append(f"Resolve {paper['total_todos']} paper TODO(s)")

    # Budget-based
    active = data.get("active", {})
    budgets = active.get("budgets", {})
    build_rem = budgets.get("build_remaining_today", 0)
    if build_rem == 0:
        priorities.append("Build budget exhausted — resets tomorrow")

    # Last cycle next
    last = active.get("last_cycle", {})
    if last.get("summary"):
        nxt = last.get("summary", "")[:100]
        priorities.append(f"Continue: {nxt}")

    return priorities or ["Review queue and pick highest-priority task"]


# ── Formatters ───────────────────────────────────────────────────────────

def format_terminal(data: dict) -> str:
    """Format digest for terminal output."""
    d = data["date"]
    lines = [f"{'─' * 60}", f"  📊 Daily Digest — {d}", f"{'─' * 60}"]

    # Highlights
    highlights = extract_highlights(data)
    lines.append("\n### Highlights")
    for i, h in enumerate(highlights, 1):
        lines.append(f"  {i}. {h}")

    # Research Progress
    auto = data.get("autodidact", {})
    paper = data.get("paper", {})
    lines.append("\n### Research Progress")
    actions = auto.get("actions", {})
    lines.append(f"  Cycles: {auto.get('cycles', 0)}  |  "
                 f"learn:{actions.get('learn', 0)}  build:{actions.get('build', 0)}  "
                 f"reflect:{actions.get('reflect', 0)}  ideate:{actions.get('ideate', 0)}")
    if auto.get("phase"):
        lines.append(f"  Phase: {auto['phase']}")
    lines.append(f"  Paper A: {paper.get('total_words', 0)} words, "
                 f"{paper.get('total_todos', 0)} TODOs remaining")

    # Engineering
    git = data.get("git", {})
    tests = data.get("tests", {})
    lines.append("\n### Engineering")
    lines.append(f"  Commits: {git.get('commits', 0)}")
    lines.append(f"  LOC: +{git.get('added', 0)} / -{git.get('removed', 0)}")
    lines.append(f"  Files changed: {git.get('files_changed', 0)}")
    test_total = tests.get("total", 0)
    lines.append(f"  Tests: {test_total} collected")

    # Autodidact State
    active = data.get("active", {})
    budgets = active.get("budgets", {})
    lines.append("\n### Autodidact")
    lines.append(f"  Cycle files: {data.get('cycle_files', 0)}")
    if budgets:
        lines.append(f"  Budgets remaining — learn:{budgets.get('learn_remaining_today', '?')} "
                     f"build:{budgets.get('build_remaining_today', '?')} "
                     f"reflect:{budgets.get('reflect_remaining_today', '?')}")
    stats = active.get("stats", {})
    if stats:
        lines.append(f"  Lifetime — cycles:{stats.get('total_cycles', 0)} "
                     f"papers:{stats.get('papers_read_deep', 0)} "
                     f"artifacts:{stats.get('code_artifacts', 0)}")

    # Queue
    queue = data.get("queue", {})
    lines.append("\n### Queue")
    lines.append(f"  Active tasks: {queue.get('total', 0)}  |  "
                 f"Archived: {queue.get('archived', 0)}")
    for status, count in sorted(queue.get("by_status", {}).items()):
        lines.append(f"    {status}: {count}")

    # Tomorrow
    priorities = infer_priorities(data)
    lines.append("\n### Tomorrow's Priorities")
    for p in priorities:
        lines.append(f"  - {p}")

    lines.append(f"\n{'─' * 60}")
    return "\n".join(lines)


def format_discord(data: dict) -> str:
    """Format digest for Discord (no markdown tables, bullet lists only)."""
    d = data["date"]
    lines = [f"**Daily Digest — {d}**"]

    highlights = extract_highlights(data)
    lines.append("\n**Highlights**")
    for i, h in enumerate(highlights, 1):
        lines.append(f"  {i}. {h}")

    auto = data.get("autodidact", {})
    actions = auto.get("actions", {})
    lines.append("\n**Research**")
    lines.append(f"- Cycles: {auto.get('cycles', 0)}")
    lines.append(f"- Actions: learn={actions.get('learn', 0)}, "
                 f"build={actions.get('build', 0)}, reflect={actions.get('reflect', 0)}")
    paper = data.get("paper", {})
    lines.append(f"- Paper A: {paper.get('total_words', 0)} words")

    git = data.get("git", {})
    tests = data.get("tests", {})
    lines.append("\n**Engineering**")
    lines.append(f"- Commits: {git.get('commits', 0)}")
    lines.append(f"- LOC: +{git.get('added', 0)} / -{git.get('removed', 0)}")
    lines.append(f"- Tests: {tests.get('total', 0)} collected")

    priorities = infer_priorities(data)
    lines.append("\n**Tomorrow**")
    for p in priorities:
        lines.append(f"- {p}")

    return "\n".join(lines)


def format_email(data: dict) -> str:
    """Format digest as HTML email."""
    d = data["date"]
    highlights = extract_highlights(data)
    auto = data.get("autodidact", {})
    actions = auto.get("actions", {})
    git = data.get("git", {})
    tests = data.get("tests", {})
    paper = data.get("paper", {})
    priorities = infer_priorities(data)

    hl_items = "".join(f"<li>{h}</li>" for h in highlights)
    pri_items = "".join(f"<li>{p}</li>" for p in priorities)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Daily Digest {d}</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 600px; margin: auto; padding: 20px; }}
  h2 {{ border-bottom: 2px solid #333; padding-bottom: 4px; }}
  h3 {{ color: #555; }}
  .stat {{ display: inline-block; margin-right: 16px; }}
</style></head><body>
<h2>Daily Digest &mdash; {d}</h2>
<h3>Highlights</h3><ol>{hl_items}</ol>
<h3>Research</h3>
<p><span class="stat">Cycles: {auto.get('cycles', 0)}</span>
<span class="stat">learn: {actions.get('learn', 0)}</span>
<span class="stat">build: {actions.get('build', 0)}</span>
<span class="stat">reflect: {actions.get('reflect', 0)}</span></p>
<p>Paper A: {paper.get('total_words', 0)} words, {paper.get('total_todos', 0)} TODOs</p>
<h3>Engineering</h3>
<p><span class="stat">Commits: {git.get('commits', 0)}</span>
<span class="stat">LOC: +{git.get('added', 0)} / -{git.get('removed', 0)}</span>
<span class="stat">Tests: {tests.get('total', 0)}</span></p>
<h3>Tomorrow</h3><ul>{pri_items}</ul>
</body></html>"""


def format_json(data: dict) -> str:
    """Raw JSON output."""
    return json.dumps(data, indent=2, default=str)


# ── Save ─────────────────────────────────────────────────────────────────

def save_digest(data: dict, content: str) -> Path:
    """Append digest to daily digest file."""
    DIGESTS_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"{data['date']}-digest.md"
    p = DIGESTS_DIR / fname
    with open(p, "a") as f:
        f.write("\n\n" + content + "\n")
    return p


# ── CLI ──────────────────────────────────────────────────────────────────

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate daily workspace digest")
    parser.add_argument("--date", type=str, default=None,
                        help="Target date (YYYY-MM-DD), defaults to today")
    parser.add_argument("--terminal", action="store_true", default=False,
                        help="Terminal output (default)")
    parser.add_argument("--discord", action="store_true", default=False,
                        help="Discord-friendly output")
    parser.add_argument("--email", action="store_true", default=False,
                        help="HTML email output")
    parser.add_argument("--json", action="store_true", default=False,
                        help="Machine-readable JSON")
    parser.add_argument("--save", action="store_true", default=False,
                        help="Append to daily digest file")
    parser.add_argument("--skip-tests", action="store_true", default=False,
                        help="Skip pytest collection (faster)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> str:
    args = parse_args(argv)

    if args.date:
        target = date.fromisoformat(args.date)
    else:
        target = date.today()

    data = collect_all(target, skip_tests=args.skip_tests)

    if args.json:
        output = format_json(data)
    elif args.discord:
        output = format_discord(data)
    elif args.email:
        output = format_email(data)
    else:
        output = format_terminal(data)

    if args.save:
        p = save_digest(data, output)
        print(f"Saved to {p}", file=sys.stderr)

    print(output)
    return output


if __name__ == "__main__":
    main()
