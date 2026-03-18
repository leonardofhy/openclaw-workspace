#!/usr/bin/env python3
"""boot_budget_check.py — Guardian script for boot path line budgets.

Checks all boot-loaded files against their line budgets.
Run during heartbeat to detect bloat before it becomes a problem.

Usage:
    python3 skills/shared/boot_budget_check.py           # human-readable
    python3 skills/shared/boot_budget_check.py --json     # machine-readable
"""
import json
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent

# ── Line budgets for boot-loaded files ──
# These files are read every session. Total budget: ≤300 lines.
BUDGETS = {
    "MEMORY.md":              80,
    "SESSION-STATE.md":       30,
    "memory/anti-patterns.md": 50,
    "SOUL.md":                50,
    "USER.md":                20,
}

WARN_THRESHOLD = 0.8   # warn at 80% of budget
TOTAL_BUDGET = 300


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return len(path.read_text(encoding="utf-8").splitlines())


def check() -> dict:
    results = []
    total = 0

    for rel_path, budget in BUDGETS.items():
        full_path = WORKSPACE / rel_path
        lines = count_lines(full_path)
        total += lines
        ratio = lines / budget if budget > 0 else 0

        status = "ok"
        if ratio >= 1.0:
            status = "over"
        elif ratio >= WARN_THRESHOLD:
            status = "warn"

        results.append({
            "file": rel_path,
            "lines": lines,
            "budget": budget,
            "ratio": round(ratio, 2),
            "status": status,
        })

    total_ratio = total / TOTAL_BUDGET if TOTAL_BUDGET > 0 else 0
    total_status = "ok"
    if total_ratio >= 1.0:
        total_status = "over"
    elif total_ratio >= WARN_THRESHOLD:
        total_status = "warn"

    return {
        "files": results,
        "total_lines": total,
        "total_budget": TOTAL_BUDGET,
        "total_ratio": round(total_ratio, 2),
        "total_status": total_status,
    }


def print_human(report: dict) -> None:
    icon = {"ok": "✅", "warn": "⚠️", "over": "🔴"}

    print("Boot Budget Check")
    print("=" * 50)
    for f in report["files"]:
        i = icon[f["status"]]
        print(f"  {i} {f['file']}: {f['lines']}/{f['budget']} ({f['ratio']:.0%})")
    print("-" * 50)
    i = icon[report["total_status"]]
    print(f"  {i} TOTAL: {report['total_lines']}/{report['total_budget']} ({report['total_ratio']:.0%})")

    over = [f for f in report["files"] if f["status"] == "over"]
    if over:
        print()
        print("Action needed:")
        for f in over:
            excess = f["lines"] - f["budget"]
            print(f"  - {f['file']}: {excess} lines over budget. Evict old content.")


def main() -> None:
    report = check()

    if "--json" in sys.argv:
        print(json.dumps(report, indent=2))
    else:
        print_human(report)

    # Exit code: 0=ok, 1=warn, 2=over
    if report["total_status"] == "over" or any(f["status"] == "over" for f in report["files"]):
        sys.exit(2)
    elif report["total_status"] == "warn" or any(f["status"] == "warn" for f in report["files"]):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
