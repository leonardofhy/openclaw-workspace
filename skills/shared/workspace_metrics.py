#!/usr/bin/env python3
"""workspace_metrics.py — Workspace health metrics tracker.

Collects daily snapshots of workspace health (files, LOC, tests, queue,
boot budget, experiments) and prints trend analysis over time.

Usage:
    python3 skills/shared/workspace_metrics.py --snapshot       # collect + save today
    python3 skills/shared/workspace_metrics.py --report         # show trends (>=2 days)
    python3 skills/shared/workspace_metrics.py --snapshot --json # machine-readable
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent
METRICS_FILE = WORKSPACE / "memory" / "metrics" / "daily-metrics.jsonl"
TZ = timezone(timedelta(hours=8))  # Asia/Taipei


# ── Collectors ──────────────────────────────────────────────────────────


def _count_python_files() -> int:
    return len(list(WORKSPACE.rglob("*.py")))


def _count_loc(pattern: str) -> int:
    total = 0
    for p in WORKSPACE.rglob(pattern):
        try:
            total += len(p.read_text(encoding="utf-8").splitlines())
        except (OSError, UnicodeDecodeError):
            pass
    return total


def _skip(p: Path) -> bool:
    """Skip __pycache__ and hidden dirs relative to workspace."""
    rel = p.relative_to(WORKSPACE)
    return any(part.startswith(".") or part == "__pycache__" for part in rel.parts)


def count_source_loc() -> int:
    total = 0
    for p in WORKSPACE.rglob("*.py"):
        if p.name.startswith("test_") or p.name.endswith("_test.py"):
            continue
        if _skip(p):
            continue
        try:
            total += len(p.read_text(encoding="utf-8").splitlines())
        except (OSError, UnicodeDecodeError):
            pass
    return total


def count_test_loc() -> int:
    total = 0
    for p in WORKSPACE.rglob("*.py"):
        if not (p.name.startswith("test_") or p.name.endswith("_test.py")):
            continue
        if _skip(p):
            continue
        try:
            total += len(p.read_text(encoding="utf-8").splitlines())
        except (OSError, UnicodeDecodeError):
            pass
    return total


def count_tests() -> int:
    """Run pytest --co -q and count collected tests."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--co", "-q", "--no-header"],
            capture_output=True, text=True, timeout=60,
            cwd=str(WORKSPACE),
        )
        # Last non-empty line is like "1286 tests collected"
        for line in reversed(result.stdout.strip().splitlines()):
            line = line.strip()
            if "selected" in line or "collected" in line:
                return int(line.split()[0])
        # Fallback: count non-empty lines that look like test items
        return sum(1 for ln in result.stdout.splitlines() if "::" in ln)
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        return 0


def commits_today() -> int:
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"--since={today}T00:00:00+08:00"],
            capture_output=True, text=True, timeout=10,
            cwd=str(WORKSPACE),
        )
        return len([ln for ln in result.stdout.strip().splitlines() if ln.strip()])
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 0


def boot_budget_pct() -> int:
    """Return total boot budget usage as integer percentage."""
    budgets = {
        "MEMORY.md": 80,
        "SESSION-STATE.md": 30,
        "memory/anti-patterns.md": 50,
        "SOUL.md": 50,
        "USER.md": 20,
    }
    total_budget = 300
    total_lines = 0
    for rel, _budget in budgets.items():
        p = WORKSPACE / rel
        if p.exists():
            try:
                total_lines += len(p.read_text(encoding="utf-8").splitlines())
            except OSError:
                pass
    return round(total_lines / total_budget * 100) if total_budget else 0


def queue_stats() -> dict[str, int]:
    """Read queue.json and count by status."""
    qpath = WORKSPACE / "memory" / "learning" / "state" / "queue.json"
    counts = {"ready": 0, "done": 0, "blocked": 0}
    if not qpath.exists():
        return counts
    try:
        data = json.loads(qpath.read_text(encoding="utf-8"))
        for task in data.get("tasks", []):
            status = task.get("status", "").lower()
            if status in ("active", "waiting"):
                counts["ready"] += 1
            elif status == "done":
                counts["done"] += 1
            elif status in ("blocked", "parked"):
                counts["blocked"] += 1
        counts["done"] += data.get("archived_count", 0)
    except (json.JSONDecodeError, OSError):
        pass
    return counts


def experiment_pass_rate() -> float:
    """Compute pass rate from experiments.jsonl."""
    epath = WORKSPACE / "memory" / "experiments" / "experiments.jsonl"
    if not epath.exists():
        return 0.0
    total = 0
    passed = 0
    try:
        for line in epath.read_text(encoding="utf-8").strip().splitlines():
            if not line.strip():
                continue
            try:
                exp = json.loads(line)
                total += 1
                if exp.get("status") == "success":
                    passed += 1
            except json.JSONDecodeError:
                pass
    except OSError:
        return 0.0
    return round(passed / total, 3) if total else 0.0


def memory_file_sizes() -> int:
    """Total bytes of all memory files."""
    mem_dir = WORKSPACE / "memory"
    if not mem_dir.exists():
        return 0
    total = 0
    for p in mem_dir.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total


# ── Snapshot ────────────────────────────────────────────────────────────


def collect_snapshot() -> dict:
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    q = queue_stats()
    src = count_source_loc()
    tst = count_test_loc()
    return {
        "date": today,
        "python_files": _count_python_files(),
        "source_loc": src,
        "test_loc": tst,
        "test_count": count_tests(),
        "test_source_ratio": round(tst / src, 3) if src else 0.0,
        "commits_today": commits_today(),
        "boot_budget_pct": boot_budget_pct(),
        "queue_ready": q["ready"],
        "queue_done": q["done"],
        "queue_blocked": q["blocked"],
        "experiment_pass_rate": experiment_pass_rate(),
        "memory_bytes": memory_file_sizes(),
    }


def save_snapshot(snapshot: dict) -> Path:
    METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Replace existing entry for the same date
    existing = load_all()
    replaced = False
    updated = []
    for entry in existing:
        if entry.get("date") == snapshot["date"]:
            updated.append(snapshot)
            replaced = True
        else:
            updated.append(entry)
    if not replaced:
        updated.append(snapshot)
    # Atomic rewrite
    with open(METRICS_FILE, "w") as f:
        for entry in updated:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return METRICS_FILE


def load_all() -> list[dict]:
    if not METRICS_FILE.exists():
        return []
    entries = []
    for line in METRICS_FILE.read_text(encoding="utf-8").strip().splitlines():
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return entries


# ── Trend report ────────────────────────────────────────────────────────


def _arrow(delta: float) -> str:
    if delta > 0:
        return "↑"
    elif delta < 0:
        return "↓"
    return "→"


def _moving_avg(values: list[float], window: int = 7) -> float | None:
    if len(values) < window:
        return None
    return round(sum(values[-window:]) / window, 1)


def trend_report(entries: list[dict]) -> dict:
    """Build trend analysis from >=2 entries."""
    if len(entries) < 2:
        return {"error": "Need at least 2 snapshots for trends"}

    latest = entries[-1]
    prev = entries[-2]

    numeric_keys = [
        "python_files", "source_loc", "test_loc", "test_count",
        "commits_today", "boot_budget_pct", "queue_ready",
        "queue_done", "queue_blocked", "experiment_pass_rate",
    ]

    trends = {"date": latest["date"], "prev_date": prev["date"], "deltas": {}}
    for key in numeric_keys:
        cur = latest.get(key, 0)
        prv = prev.get(key, 0)
        delta = cur - prv if isinstance(cur, int) else round(cur - prv, 3)
        ma = _moving_avg([e.get(key, 0) for e in entries], 7)
        trends["deltas"][key] = {
            "current": cur,
            "previous": prv,
            "delta": delta,
            "arrow": _arrow(delta),
            "moving_avg_7d": ma,
        }
    return trends


def print_trends_human(trends: dict) -> None:
    if "error" in trends:
        print(trends["error"])
        return

    print(f"Workspace Trends: {trends['prev_date']} → {trends['date']}")
    print("=" * 58)

    labels = {
        "python_files": "Python files",
        "source_loc": "Source LOC",
        "test_loc": "Test LOC",
        "test_count": "Tests",
        "commits_today": "Commits today",
        "boot_budget_pct": "Boot budget %",
        "queue_ready": "Queue ready",
        "queue_done": "Queue done",
        "queue_blocked": "Queue blocked",
        "experiment_pass_rate": "Exp pass rate",
    }

    for key, label in labels.items():
        d = trends["deltas"][key]
        delta_str = f"+{d['delta']}" if d["delta"] > 0 else str(d["delta"])
        ma_str = f"  (7d avg: {d['moving_avg_7d']})" if d["moving_avg_7d"] is not None else ""
        print(f"  {d['arrow']} {label:18s} {d['current']:>8}  ({delta_str}){ma_str}")

    print("=" * 58)


def print_snapshot_human(snap: dict) -> None:
    print(f"Workspace Snapshot: {snap['date']}")
    print("=" * 42)
    print(f"  Python files:      {snap['python_files']:>8}")
    print(f"  Source LOC:        {snap['source_loc']:>8}")
    print(f"  Test LOC:          {snap['test_loc']:>8}")
    print(f"  Tests:             {snap['test_count']:>8}")
    print(f"  Test/source ratio: {snap['test_source_ratio']:>8.3f}")
    print(f"  Commits today:     {snap['commits_today']:>8}")
    print(f"  Boot budget %:     {snap['boot_budget_pct']:>7}%")
    print(f"  Queue ready:       {snap['queue_ready']:>8}")
    print(f"  Queue done:        {snap['queue_done']:>8}")
    print(f"  Queue blocked:     {snap['queue_blocked']:>8}")
    print(f"  Exp pass rate:     {snap['experiment_pass_rate']:>8.3f}")
    print(f"  Memory size:       {snap['memory_bytes']:>8} B")
    print("=" * 42)


# ── CLI ─────────────────────────────────────────────────────────────────


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Workspace health metrics tracker"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--snapshot", action="store_true", help="Collect and save today's metrics")
    mode.add_argument("--report", action="store_true", help="Show trends (needs >=2 snapshots)")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> str:
    args = parse_args(argv)

    if args.snapshot:
        snap = collect_snapshot()
        save_snapshot(snap)
        if args.json:
            out = json.dumps(snap, indent=2)
            print(out)
            return out
        print_snapshot_human(snap)
        entries = load_all()
        if len(entries) >= 2:
            print()
            trends = trend_report(entries)
            print_trends_human(trends)
        return ""

    if args.report:
        entries = load_all()
        trends = trend_report(entries)
        if args.json:
            out = json.dumps(trends, indent=2)
            print(out)
            return out
        print_trends_human(trends)
        return ""

    return ""


if __name__ == "__main__":
    main()
