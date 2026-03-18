#!/usr/bin/env python3
"""research_dashboard.py — Single-command research status overview.

Usage:
    python3 skills/shared/research_dashboard.py              # full dashboard
    python3 skills/shared/research_dashboard.py --section paper
    python3 skills/shared/research_dashboard.py --section experiments
    python3 skills/shared/research_dashboard.py --section autodidact
    python3 skills/shared/research_dashboard.py --section health
    python3 skills/shared/research_dashboard.py --section upcoming
    python3 skills/shared/research_dashboard.py --json       # machine-readable
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent

# Ensure imports work for sibling modules
sys.path.insert(0, str(WORKSPACE / "skills" / "shared"))
sys.path.insert(0, str(WORKSPACE / "skills" / "autodidact" / "scripts"))
sys.path.insert(0, str(WORKSPACE / "skills" / "leo-diary" / "scripts"))
sys.path.insert(0, str(WORKSPACE / "skills"))

SECTIONS = ("paper", "experiments", "autodidact", "health", "upcoming")

# ── Formatting helpers ───────────────────────────────────────────────────

def bar(pct: float, width: int = 20) -> str:
    filled = int(width * pct / 100)
    return f"{pct:5.1f}% {'█' * filled}{'░' * (width - filled)}"


def hdr(title: str) -> str:
    return f"\n{'─' * 60}\n  {title}\n{'─' * 60}"


# ── Section 1: Paper A Status ───────────────────────────────────────────

PAPER_SECTIONS = {
    "Abstract":    "paper-a-abstract.md",
    "Intro & RW":  "paper-a-intro-rw.md",
    "Methods":     "paper-a-method.md",
    "Results":     "paper-a-results.md",
    "Discussion":  "paper-a-discussion-stub.md",
    "Outline":     "paper-a-outline.md",
}

# Target word counts per section (approximate for a workshop/short paper)
WORD_TARGETS = {
    "Abstract":   300,
    "Intro & RW": 1500,
    "Methods":    2000,
    "Results":    2000,
    "Discussion": 1000,
    "Outline":    0,  # not a prose section
}


def _count(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, re.IGNORECASE))


def section_paper() -> dict:
    docs = WORKSPACE / "docs"
    rows = []
    total_words = 0
    total_todos = 0
    total_cites = 0

    for label, fname in PAPER_SECTIONS.items():
        p = docs / fname
        if not p.exists():
            rows.append({"section": label, "file": fname, "words": 0,
                         "todos": 0, "cites": 0, "pct": 0})
            continue
        text = p.read_text(encoding="utf-8")
        words = len(text.split())
        todos = _count(text, r"\bTODO\b")
        cites = _count(text, r"\bCITE\b")
        target = WORD_TARGETS.get(label, 0)
        pct = min(words / target * 100, 100) if target > 0 else 100
        rows.append({"section": label, "file": fname, "words": words,
                     "todos": todos, "cites": cites, "pct": round(pct, 1)})
        total_words += words
        total_todos += todos
        total_cites += cites

    # Draft total
    draft = docs / "paper-a-draft.md"
    draft_words = len(draft.read_text().split()) if draft.exists() else 0

    return {"sections": rows, "total_words": total_words,
            "draft_words": draft_words, "total_todos": total_todos,
            "total_cites": total_cites}


def print_paper(data: dict) -> None:
    print(hdr("📝  Paper A — The Listening Geometry"))
    print(f"  {'Section':<14} {'Words':>6} {'Target':>7}  {'Progress':<28} {'TODO':>4} {'CITE':>4}")
    for r in data["sections"]:
        target = WORD_TARGETS.get(r["section"], 0)
        tgt_str = str(target) if target else "  —"
        print(f"  {r['section']:<14} {r['words']:>6} {tgt_str:>7}  {bar(r['pct']):<28} {r['todos']:>4} {r['cites']:>4}")
    print(f"\n  Total words: {data['total_words']}  |  Draft: {data['draft_words']}  |  "
          f"TODOs: {data['total_todos']}  |  CITEs: {data['total_cites']}")


# ── Section 2: Experiment Status ────────────────────────────────────────

def section_experiments() -> dict:
    try:
        from unified_results_dashboard import RESULTS
    except ImportError:
        return {"error": "unified_results_dashboard not importable"}

    total = len(RESULTS)
    n_pass = sum(1 for r in RESULTS.values() if r["status"] == "pass")
    n_blocked = sum(1 for r in RESULTS.values() if r["status"] == "blocked")
    n_real = sum(1 for r in RESULTS.values() if r["mode"] == "real")
    correlations = [r["correlation"] for r in RESULTS.values()
                    if r["correlation"] is not None]
    abs_corr = [abs(c) for c in correlations]

    strongest = []
    weakest = []
    if correlations:
        sorted_items = sorted(
            [(qid, r) for qid, r in RESULTS.items()
             if r["correlation"] is not None],
            key=lambda x: abs(x[1]["correlation"]), reverse=True)
        strongest = [{"id": qid, "name": r["name"],
                      "r": r["correlation"]} for qid, r in sorted_items[:3]]
        weakest = [{"id": qid, "name": r["name"],
                    "r": r["correlation"]} for qid, r in sorted_items[-2:]]

    return {
        "total": total, "pass": n_pass, "blocked": n_blocked,
        "real": n_real, "mock": total - n_real,
        "pass_rate": round(n_pass / total * 100, 1) if total else 0,
        "mean_abs_r": round(sum(abs_corr) / len(abs_corr), 3) if abs_corr else None,
        "median_abs_r": round(sorted(abs_corr)[len(abs_corr) // 2], 3) if abs_corr else None,
        "strongest": strongest, "weakest": weakest,
    }


def print_experiments(data: dict) -> None:
    print(hdr("🧪  Experiment Status"))
    if "error" in data:
        print(f"  ⚠️  {data['error']}")
        return
    pr = data["pass_rate"]
    print(f"  Total: {data['total']}  |  Pass: {data['pass']}  |  "
          f"Blocked: {data['blocked']}  |  Real: {data['real']}  Mock: {data['mock']}")
    print(f"  Pass rate: {bar(pr)}")
    if data["mean_abs_r"] is not None:
        print(f"  Mean |r|: {data['mean_abs_r']:.3f}  |  Median |r|: {data['median_abs_r']:.3f}")
    if data["strongest"]:
        top = data["strongest"][0]
        print(f"  Strongest: {top['id']} {top['name']} (r={top['r']:+.3f})")
    if data["weakest"]:
        bot = data["weakest"][-1]
        print(f"  Weakest:   {bot['id']} {bot['name']} (r={bot['r']:+.3f})")


# ── Section 3: Autodidact State ─────────────────────────────────────────

def section_autodidact() -> dict:
    state_dir = WORKSPACE / "memory" / "learning" / "state"
    result: dict = {}

    # active.json
    active_path = state_dir / "active.json"
    if active_path.exists():
        active = json.loads(active_path.read_text(encoding="utf-8"))
        result["phase"] = active.get("phase", "?")
        result["phase_since"] = active.get("phase_since", "?")
        result["tracks"] = [
            {"id": t["id"], "name": t["name"], "status": t.get("status", "?")}
            for t in active.get("active_tracks", [])
        ]
        budgets = active.get("budgets", {})
        result["budgets"] = {
            "learn": budgets.get("learn_remaining_today", "?"),
            "build": budgets.get("build_remaining_today", "?"),
            "reflect": budgets.get("reflect_remaining_today", "?"),
            "ideate": budgets.get("ideate_remaining_today", "?"),
            "reset_date": budgets.get("budget_reset_date", "?"),
        }
        stats = active.get("stats", {})
        result["stats"] = {
            "total_cycles": stats.get("total_cycles", 0),
            "papers_read": stats.get("papers_read_deep", 0),
            "experiments_done": stats.get("experiments_done", 0),
            "real_experiments": stats.get("real_experiments_completed", 0),
            "code_artifacts": stats.get("code_artifacts", 0),
        }
    else:
        result["error"] = "active.json not found"

    # queue.json
    queue_path = state_dir / "queue.json"
    if queue_path.exists():
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        tasks = queue.get("tasks", [])
        by_status: dict[str, int] = {}
        for t in tasks:
            s = t.get("status", "unknown")
            by_status[s] = by_status.get(s, 0) + 1
        result["queue"] = {
            "total": len(tasks),
            "by_status": by_status,
            "archived": queue.get("archived_count", 0),
        }
    else:
        result["queue"] = {"total": 0, "by_status": {}, "archived": 0}

    return result


def print_autodidact(data: dict) -> None:
    print(hdr("🤖  Autodidact State"))
    if "error" in data:
        print(f"  ⚠️  {data['error']}")
        return
    print(f"  Phase: {data['phase']} (since {data['phase_since']})")
    if data.get("tracks"):
        print("  Tracks:")
        for t in data["tracks"]:
            print(f"    • {t['id']}: {t['name']} [{t['status']}]")
    b = data.get("budgets", {})
    print(f"  Budgets remaining: learn={b.get('learn','?')}  build={b.get('build','?')}  "
          f"reflect={b.get('reflect','?')}  ideate={b.get('ideate','?')}")
    if b.get("reset_date") and b["reset_date"] != str(date.today()):
        print(f"  ⚠️  Budget reset date: {b['reset_date']} (stale)")
    s = data.get("stats", {})
    print(f"  Stats: {s.get('total_cycles',0)} cycles | {s.get('papers_read',0)} papers | "
          f"{s.get('experiments_done',0)} experiments ({s.get('real_experiments',0)} real) | "
          f"{s.get('code_artifacts',0)} artifacts")
    q = data.get("queue", {})
    if q.get("total", 0) > 0:
        parts = [f"{k}={v}" for k, v in q["by_status"].items()]
        print(f"  Queue: {q['total']} tasks ({', '.join(parts)}) | {q.get('archived',0)} archived")
    else:
        print(f"  Queue: empty | {q.get('archived',0)} archived")


# ── Section 4: System Health ────────────────────────────────────────────

def section_health() -> dict:
    result: dict = {}

    # Boot budget
    try:
        from boot_budget_check import check
        result["boot_budget"] = check()
    except Exception as e:
        result["boot_budget"] = {"error": str(e)}

    # Test count (fast: --co -q just collects, doesn't run)
    try:
        out = subprocess.run(
            [sys.executable, "-m", "pytest", "--co", "-q", "--no-header"],
            capture_output=True, text=True, cwd=str(WORKSPACE), timeout=30)
        # Last line is like "42 tests collected"
        for line in reversed(out.stdout.strip().splitlines()):
            m = re.search(r"(\d+)\s+tests?\s", line)
            if m:
                result["test_count"] = int(m.group(1))
                break
        if "test_count" not in result:
            result["test_count"] = None
    except Exception:
        result["test_count"] = None

    # Git status
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            text=True, cwd=str(WORKSPACE)).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            text=True, cwd=str(WORKSPACE)).strip()
        log = subprocess.check_output(
            ["git", "log", "-1", "--format=%h %s"],
            text=True, cwd=str(WORKSPACE)).strip()
        result["git"] = {
            "branch": branch,
            "clean": len(status) == 0,
            "dirty_files": len(status.splitlines()) if status else 0,
            "last_commit": log,
        }
    except Exception:
        result["git"] = {"error": "git not available"}

    # Codebase stats (fast: just count .py files and LOC)
    try:
        py_files = list(WORKSPACE.rglob("*.py"))
        # Exclude archive/, __pycache__, venv, node_modules
        skip = {"archive", "__pycache__", "venv", "node_modules", ".git"}
        py_files = [f for f in py_files
                    if not any(s in f.parts for s in skip)]
        total_loc = 0
        for f in py_files:
            try:
                total_loc += len(f.read_text(encoding="utf-8").splitlines())
            except Exception:
                pass
        result["codebase"] = {"py_files": len(py_files), "loc": total_loc}
    except Exception:
        result["codebase"] = {"py_files": 0, "loc": 0}

    return result


def print_health(data: dict) -> None:
    print(hdr("🏥  System Health"))

    # Boot budget
    bb = data.get("boot_budget", {})
    if "error" in bb:
        print(f"  Boot budget: ⚠️  {bb['error']}")
    else:
        icon = {"ok": "✅", "warn": "⚠️", "over": "🔴"}
        i = icon.get(bb.get("total_status", "ok"), "❓")
        print(f"  Boot budget: {i} {bb['total_lines']}/{bb['total_budget']} lines "
              f"({bb['total_ratio']:.0%})")

    # Tests
    tc = data.get("test_count")
    print(f"  Tests: {tc if tc is not None else '?'} collected")

    # Git
    g = data.get("git", {})
    if "error" in g:
        print(f"  Git: ⚠️  {g['error']}")
    else:
        status = "✅ clean" if g["clean"] else f"⚠️  {g['dirty_files']} dirty"
        print(f"  Git: {g['branch']} | {status} | {g['last_commit']}")

    # Codebase
    cb = data.get("codebase", {})
    print(f"  Codebase: {cb.get('py_files', 0)} .py files | {cb.get('loc', 0):,} LOC")


# ── Section 5: Upcoming ────────────────────────────────────────────────

def section_upcoming() -> dict:
    result: dict = {}

    # Calendar (next 24h)
    try:
        from gcal_today import get_events
        events = get_events(days_ahead=0, days_range=1)
        result["calendar"] = [
            {"summary": e["summary"], "start": e["start"],
             "all_day": e["all_day"]}
            for e in events
        ]
    except Exception as e:
        result["calendar"] = {"error": str(e)}

    # Deadlines
    try:
        deadlines_file = WORKSPACE / "memory" / "finance" / "deadlines.json"
        if deadlines_file.exists():
            from deadline_watch import check_deadlines
            deadlines = json.loads(deadlines_file.read_text(encoding="utf-8"))
            dl_result = check_deadlines(deadlines, date.today(),
                                        warn_days=14, show_all=True)
            result["deadlines"] = {
                "overdue": [{"id": d["id"], "name": d["name"],
                             "days": d["days_left"]} for d in dl_result["overdue"]],
                "urgent": [{"id": d["id"], "name": d["name"],
                            "days": d["days_left"]} for d in dl_result["urgent"]],
                "upcoming": [{"id": d["id"], "name": d["name"],
                              "days": d["days_left"]}
                             for d in dl_result["upcoming"][:5]],
            }
        else:
            result["deadlines"] = {"error": "deadlines.json not found"}
    except Exception as e:
        result["deadlines"] = {"error": str(e)}

    return result


def print_upcoming(data: dict) -> None:
    print(hdr("📅  Upcoming"))

    # Calendar
    cal = data.get("calendar", {})
    if isinstance(cal, dict) and "error" in cal:
        print(f"  Calendar: ⚠️  {cal['error']}")
    elif isinstance(cal, list):
        if not cal:
            print("  Calendar: no events today")
        else:
            print(f"  Calendar: {len(cal)} event(s) today")
            for e in cal[:8]:
                time_str = ""
                if not e.get("all_day"):
                    try:
                        t = datetime.fromisoformat(e["start"])
                        time_str = t.strftime("%H:%M")
                    except Exception:
                        time_str = e["start"]
                else:
                    time_str = "all-day"
                print(f"    {time_str:>7}  {e['summary']}")

    # Deadlines
    dl = data.get("deadlines", {})
    if isinstance(dl, dict) and "error" in dl:
        print(f"  Deadlines: ⚠️  {dl['error']}")
    elif isinstance(dl, dict):
        for d in dl.get("overdue", []):
            print(f"  🔴 OVERDUE: {d['id']} {d['name']} ({-d['days']}d ago)")
        for d in dl.get("urgent", []):
            print(f"  ⚠️  URGENT: {d['id']} {d['name']} ({d['days']}d left)")
        for d in dl.get("upcoming", []):
            print(f"  📋 {d['id']} {d['name']} ({d['days']}d left)")
        total = sum(len(dl.get(k, [])) for k in ("overdue", "urgent", "upcoming"))
        if total == 0:
            print("  Deadlines: none active")


# ── Main ────────────────────────────────────────────────────────────────

SECTION_MAP = {
    "paper":       (section_paper,       print_paper),
    "experiments": (section_experiments, print_experiments),
    "autodidact":  (section_autodidact,  print_autodidact),
    "health":      (section_health,      print_health),
    "upcoming":    (section_upcoming,    print_upcoming),
}


def run_dashboard(sections: list[str] | None = None,
                  as_json: bool = False) -> dict:
    """Run dashboard and return all data. Prints human output unless as_json."""
    targets = sections or list(SECTIONS)
    all_data: dict = {}

    if not as_json:
        print("╔══════════════════════════════════════════════════════════════╗")
        print(f"║        OpenClaw Research Dashboard — {date.today()}         ║")
        print("╚══════════════════════════════════════════════════════════════╝")

    for name in targets:
        if name not in SECTION_MAP:
            if not as_json:
                print(f"\n  ⚠️  Unknown section: {name}")
            continue
        gather, display = SECTION_MAP[name]
        try:
            data = gather()
        except Exception as e:
            data = {"error": str(e)}
        all_data[name] = data
        if not as_json:
            display(data)

    if as_json:
        print(json.dumps(all_data, indent=2, ensure_ascii=False, default=str))

    return all_data


def main() -> None:
    parser = argparse.ArgumentParser(
        description="OpenClaw Research Dashboard — single-command status overview")
    parser.add_argument("--json", action="store_true",
                        help="Machine-readable JSON output")
    parser.add_argument("--section", choices=SECTIONS,
                        help="Show only one section")
    args = parser.parse_args()

    sections = [args.section] if args.section else None
    run_dashboard(sections=sections, as_json=args.json)


if __name__ == "__main__":
    main()
