#!/usr/bin/env python3
"""
Smart test runner for the openclaw workspace.

Discovers all test_*.py under skills/, handles sys.modules isolation,
and provides clear pass/fail output.

Usage:
    python3 scripts/run_tests.py              # full suite
    python3 scripts/run_tests.py --quick      # only changed files (git diff)
    python3 scripts/run_tests.py --verbose    # verbose pytest output
    python3 scripts/run_tests.py --file PATH  # single file
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"

# Files that must run in isolation due to sys.modules side-effects
ISOLATED_FILES = {
    "skills/lib/test_common.py",
    "skills/shared/test_jsonl_store.py",
    "skills/system-scanner/scripts/test_scan.py",
    "skills/remember/scripts/test_append_memory.py",
}

EXCLUDE_DIRS = {"venv", ".venv", ".git", "__pycache__", "node_modules"}


def discover_tests() -> list[Path]:
    """Find all test_*.py files under skills/, excluding noise dirs."""
    results = []
    for p in SKILLS_DIR.rglob("test_*.py"):
        if not any(part in EXCLUDE_DIRS for part in p.parts):
            results.append(p)
    return sorted(results)


def get_changed_test_files() -> list[Path]:
    """Return test files changed vs the main branch (staged + unstaged + committed on branch)."""
    changed: set[str] = set()

    # Uncommitted changes (staged + unstaged)
    for cmd in (
        ["git", "diff", "--name-only"],
        ["git", "diff", "--cached", "--name-only"],
    ):
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
        if result.returncode == 0:
            changed.update(result.stdout.strip().splitlines())

    # Committed on branch but not on main
    result = subprocess.run(
        ["git", "diff", "--name-only", "main...HEAD"],
        capture_output=True, text=True, cwd=ROOT,
    )
    if result.returncode == 0:
        changed.update(result.stdout.strip().splitlines())

    test_files = []
    for f in changed:
        p = ROOT / f
        if p.name.startswith("test_") and p.suffix == ".py" and p.exists():
            test_files.append(p)
        # If a non-test source file changed, include its corresponding test
        elif p.suffix == ".py" and not p.name.startswith("test_"):
            candidate = p.parent / f"test_{p.name}"
            if candidate.exists():
                test_files.append(candidate)
    return sorted(set(test_files))


def run_pytest(files: list[Path], verbose: bool = False) -> subprocess.CompletedProcess:
    """Run pytest on a list of files, return the CompletedProcess."""
    cmd = [sys.executable, "-m", "pytest"]
    if verbose:
        cmd.append("-v")
    else:
        cmd.extend(["-q", "--tb=short"])
    cmd.extend(str(f) for f in files)
    return subprocess.run(cmd, cwd=ROOT)


def run_suite(test_files: list[Path], verbose: bool = False) -> int:
    """Run tests with isolation handling. Returns 0 on success, 1 on failure."""
    if not test_files:
        print("No test files to run.")
        return 0

    isolated = []
    batch = []
    for f in test_files:
        rel = str(f.relative_to(ROOT))
        if rel in ISOLATED_FILES:
            isolated.append(f)
        else:
            batch.append(f)

    total_failures = 0
    t0 = time.time()

    # Run isolated files first, each in their own pytest invocation
    for f in isolated:
        print(f"\n{'='*60}")
        print(f"  ISOLATED: {f.relative_to(ROOT)}")
        print(f"{'='*60}")
        result = run_pytest([f], verbose)
        if result.returncode != 0:
            total_failures += 1

    # Run the rest as a single batch
    if batch:
        print(f"\n{'='*60}")
        print(f"  BATCH: {len(batch)} test files")
        print(f"{'='*60}")
        result = run_pytest(batch, verbose)
        if result.returncode != 0:
            total_failures += 1

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    if total_failures:
        print(f"  RESULT: FAILURES in {total_failures} run(s)  ({elapsed:.1f}s)")
    else:
        count = len(isolated) + len(batch)
        print(f"  RESULT: ALL PASSED — {count} file(s)  ({elapsed:.1f}s)")
    print(f"{'='*60}")

    return 1 if total_failures else 0


def main():
    parser = argparse.ArgumentParser(description="Run openclaw workspace tests")
    parser.add_argument("--quick", action="store_true", help="Only test files changed vs main")
    parser.add_argument("--verbose", action="store_true", help="Verbose pytest output")
    parser.add_argument("--file", type=str, help="Run a single test file")
    args = parser.parse_args()

    if args.file:
        p = Path(args.file).resolve()
        if not p.exists():
            print(f"File not found: {args.file}")
            sys.exit(1)
        test_files = [p]
    elif args.quick:
        test_files = get_changed_test_files()
        if not test_files:
            print("No changed test files detected — skipping.")
            sys.exit(0)
        print(f"Quick mode: {len(test_files)} changed file(s)")
    else:
        test_files = discover_tests()
        print(f"Full suite: {len(test_files)} test file(s)")

    sys.exit(run_suite(test_files, verbose=args.verbose))


if __name__ == "__main__":
    main()
