#!/usr/bin/env python3
"""Pre-commit quality gate — catches common issues before they're pushed.

Usage:
    python3 skills/shared/pre_commit_check.py --staged   # only staged files (used by hook)
    python3 skills/shared/pre_commit_check.py --all      # check everything tracked
    python3 skills/shared/pre_commit_check.py --fix      # auto-fix trailing whitespace etc.
"""

import argparse
import os
import re
import subprocess
import sys

# ── Patterns ────────────────────────────────────────────────────────────────

SECRET_PATTERNS = [
    # Match actual secret values (8+ chars), not env-var lookups like os.environ.get()
    (r'TODOIST_API_TOKEN\s*=\s*["\'][^"\']{8,}["\']', "TODOIST_API_TOKEN assignment"),
    (r'(?<!\w)password\s*=\s*["\'][^"\']{4,}["\']', "password assignment"),
    (r'(?<!\w)api_key\s*=\s*["\'][^"\']{4,}["\']', "api_key assignment"),
    (r'(?<!\w)secret\s*=\s*["\'][^"\']{4,}["\']', "secret assignment"),
    (r'Bearer\s+[A-Za-z0-9\-._~+/]{20,}=*', "Bearer token"),
]

MERGE_CONFLICT_RE = re.compile(r'^(<{7}|>{7}|={7})\s', re.MULTILINE)

PRINT_RE = re.compile(r'^\s*print\s*\(', re.MULTILINE)

LINE_LENGTH_LIMIT = 120

# Directories whose .py files are "shared libs" (print() is disallowed)
SHARED_LIB_DIRS = {"skills/shared", "skills/coordinator/scripts", "skills/autodidact/tools"}

# ── Helpers ─────────────────────────────────────────────────────────────────

def get_repo_root() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], text=True
    ).strip()


def staged_files() -> list[str]:
    out = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"], text=True
    )
    return [f for f in out.strip().splitlines() if f]


def tracked_files() -> list[str]:
    out = subprocess.check_output(["git", "ls-files"], text=True)
    return [f for f in out.strip().splitlines() if f]


def is_env_file(path: str) -> bool:
    base = os.path.basename(path)
    return base.startswith(".env") or path.startswith("secrets/")


def is_shared_lib(path: str) -> bool:
    """True if path is a non-test, non-script shared library."""
    if not path.endswith(".py"):
        return False
    base = os.path.basename(path)
    if base.startswith("test_") or base == "run_tests.py":
        return False
    # Files inside known shared-lib directories
    for d in SHARED_LIB_DIRS:
        if path.startswith(d):
            return True
    return False


# ── Checks ──────────────────────────────────────────────────────────────────

class CheckResult:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def error(self, msg: str):
        self.errors.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)


SECRET_IGNORE_LINE_RE = re.compile(
    r'(os\.environ|getenv|startswith|endswith|\.get\(|raise\s|RuntimeError|#.*noqa)',
    re.IGNORECASE,
)


def check_secrets(files: list[str], root: str, result: CheckResult):
    for rel in files:
        if is_env_file(rel):
            continue
        if not (rel.endswith(".py") or rel.endswith(".md")):
            continue
        # Skip test files — they use mock/fake values
        if os.path.basename(rel).startswith("test_"):
            continue
        full = os.path.join(root, rel)
        if not os.path.isfile(full):
            continue
        try:
            lines = open(full).readlines()
        except Exception:
            continue
        for i, line in enumerate(lines, 1):
            if SECRET_IGNORE_LINE_RE.search(line):
                continue
            for pattern, label in SECRET_PATTERNS:
                if re.search(pattern, line):
                    result.error(f"[SECRET] {rel}:{i} — {label}")


def check_print_statements(files: list[str], root: str, result: CheckResult):
    for rel in files:
        if not is_shared_lib(rel):
            continue
        full = os.path.join(root, rel)
        if not os.path.isfile(full):
            continue
        try:
            content = open(full).read()
        except Exception:
            continue
        for m in PRINT_RE.finditer(content):
            lineno = content[:m.start()].count("\n") + 1
            result.error(f"[PRINT] {rel}:{lineno} — use logging instead of print()")


def check_syntax(files: list[str], root: str, result: CheckResult):
    py_files = [f for f in files if f.endswith(".py")]
    for rel in py_files:
        full = os.path.join(root, rel)
        if not os.path.isfile(full):
            continue
        proc = subprocess.run(
            [sys.executable, "-m", "py_compile", full],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            msg = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "syntax error"
            result.error(f"[SYNTAX] {rel} — {msg}")


def check_line_length(files: list[str], root: str, result: CheckResult):
    for rel in files:
        if not (rel.endswith(".py") or rel.endswith(".md")):
            continue
        full = os.path.join(root, rel)
        if not os.path.isfile(full):
            continue
        try:
            lines = open(full).readlines()
        except Exception:
            continue
        long_lines = [
            (i + 1, len(line.rstrip()))
            for i, line in enumerate(lines)
            if len(line.rstrip()) > LINE_LENGTH_LIMIT
        ]
        if long_lines:
            examples = long_lines[:3]
            desc = ", ".join(f"L{ln}({length})" for ln, length in examples)
            extra = f" +{len(long_lines) - 3} more" if len(long_lines) > 3 else ""
            result.warn(f"[LENGTH] {rel} — {desc}{extra}")


def check_merge_conflicts(files: list[str], root: str, result: CheckResult):
    for rel in files:
        full = os.path.join(root, rel)
        if not os.path.isfile(full):
            continue
        try:
            content = open(full).read()
        except Exception:
            continue
        if MERGE_CONFLICT_RE.search(content):
            result.error(f"[CONFLICT] {rel} — merge conflict markers found")


def fix_trailing_whitespace(files: list[str], root: str) -> int:
    fixed = 0
    for rel in files:
        full = os.path.join(root, rel)
        if not os.path.isfile(full):
            continue
        try:
            original = open(full).read()
        except Exception:
            continue
        cleaned = "\n".join(line.rstrip() for line in original.splitlines())
        if original.endswith("\n"):
            cleaned += "\n"
        if cleaned != original:
            open(full, "w").write(cleaned)
            fixed += 1
            print(f"  [FIXED] trailing whitespace: {rel}")
    return fixed


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Pre-commit quality gate")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--staged", action="store_true", help="Check staged files only")
    group.add_argument("--all", action="store_true", help="Check all tracked files")
    parser.add_argument("--fix", action="store_true", help="Auto-fix what's possible")
    args = parser.parse_args()

    root = get_repo_root()
    os.chdir(root)

    files = staged_files() if args.staged else tracked_files()
    if not files:
        print("No files to check.")
        sys.exit(0)

    if args.fix:
        n = fix_trailing_whitespace(files, root)
        if n:
            print(f"  Fixed trailing whitespace in {n} file(s)")

    result = CheckResult()
    check_secrets(files, root, result)
    check_print_statements(files, root, result)
    check_syntax(files, root, result)
    check_line_length(files, root, result)
    check_merge_conflicts(files, root, result)

    # ── Report ──────────────────────────────────────────────────────────
    if result.errors:
        print(f"\n✗ {len(result.errors)} error(s):")
        for e in result.errors:
            print(f"  {e}")

    if result.warnings:
        print(f"\n⚠ {len(result.warnings)} warning(s):")
        for w in result.warnings:
            print(f"  {w}")

    if not result.errors and not result.warnings:
        print("✓ All checks passed.")

    sys.exit(0 if result.ok else 1)


if __name__ == "__main__":
    main()
