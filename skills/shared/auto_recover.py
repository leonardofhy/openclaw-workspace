#!/usr/bin/env python3
"""Intelligent error recovery — diagnose, suggest fixes, and optionally auto-fix.

Usage:
    python3 auto_recover.py --diagnose "ModuleNotFoundError: No module named 'shared'"
    python3 auto_recover.py --diagnose "TimeoutError: process exceeded 120s" --fix
    python3 auto_recover.py --diagnose "merge conflict in file.py" --fix --dry-run
    python3 auto_recover.py --classify "AssertionError: expected 5, got 3"

Error classes:
    import_error   — missing module or path issue
    timeout        — process exceeded time limit
    state_conflict — merge conflict, stale state, dirty worktree
    permission     — file/SSH access issue
    resource       — disk/memory/GPU unavailable
    logic          — assertion failure, wrong output
    unknown        — unclassifiable
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# --- Bootstrap ---
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shared.jsonl_store import JsonlStore, find_workspace

WORKSPACE = find_workspace()
RECOVERY_LOG = "memory/learning/auto-recovery.jsonl"

_TZ_TAIPEI = timezone(timedelta(hours=8))


def now_ts() -> str:
    return datetime.now(_TZ_TAIPEI).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def today() -> str:
    return datetime.now(_TZ_TAIPEI).strftime("%Y-%m-%d")


# ── Error Classification ─────────────────────────────────

# Pattern → (error_class, confidence_boost)
CLASSIFICATION_RULES: list[tuple[re.Pattern, str, float]] = [
    # import_error
    (re.compile(r"ModuleNotFoundError", re.I), "import_error", 0.95),
    (re.compile(r"ImportError", re.I), "import_error", 0.90),
    (re.compile(r"No module named", re.I), "import_error", 0.95),
    (re.compile(r"cannot import name", re.I), "import_error", 0.85),
    (re.compile(r"ModuleNotFoundError.*conftest", re.I), "import_error", 0.98),
    (re.compile(r"sys\.path", re.I), "import_error", 0.70),
    # timeout
    (re.compile(r"TimeoutError", re.I), "timeout", 0.95),
    (re.compile(r"timed?\s*out", re.I), "timeout", 0.85),
    (re.compile(r"exceeded.*(?:time|limit|seconds|timeout)", re.I), "timeout", 0.90),
    (re.compile(r"SIGALRM|alarm", re.I), "timeout", 0.80),
    (re.compile(r"deadline exceeded", re.I), "timeout", 0.90),
    # state_conflict
    (re.compile(r"merge conflict", re.I), "state_conflict", 0.95),
    (re.compile(r"CONFLICT \(", re.I), "state_conflict", 0.95),
    (re.compile(r"stale.*(?:state|ref|index)", re.I), "state_conflict", 0.80),
    (re.compile(r"Your local changes.*would be overwritten", re.I), "state_conflict", 0.90),
    (re.compile(r"needs merge", re.I), "state_conflict", 0.85),
    (re.compile(r"not a git repository", re.I), "state_conflict", 0.70),
    (re.compile(r"lock.*file.*exists", re.I), "state_conflict", 0.80),
    # permission
    (re.compile(r"PermissionError", re.I), "permission", 0.95),
    (re.compile(r"Permission denied", re.I), "permission", 0.95),
    (re.compile(r"EACCES", re.I), "permission", 0.90),
    (re.compile(r"ssh.*(?:refused|denied|timeout|banner)", re.I), "permission", 0.80),
    (re.compile(r"Host key verification failed", re.I), "permission", 0.85),
    (re.compile(r"publickey.*denied", re.I), "permission", 0.90),
    # resource
    (re.compile(r"MemoryError", re.I), "resource", 0.95),
    (re.compile(r"No space left on device", re.I), "resource", 0.95),
    (re.compile(r"ENOMEM|cannot allocate", re.I), "resource", 0.90),
    (re.compile(r"CUDA out of memory", re.I), "resource", 0.95),
    (re.compile(r"OOM|out.of.memory", re.I), "resource", 0.85),
    (re.compile(r"disk.*full|quota exceeded", re.I), "resource", 0.90),
    (re.compile(r"ResourceExhausted", re.I), "resource", 0.90),
    # logic
    (re.compile(r"AssertionError", re.I), "logic", 0.90),
    (re.compile(r"assert\s+.*failed", re.I), "logic", 0.85),
    (re.compile(r"expected.*got", re.I), "logic", 0.75),
    (re.compile(r"ValueError", re.I), "logic", 0.70),
    (re.compile(r"TypeError", re.I), "logic", 0.70),
    (re.compile(r"KeyError", re.I), "logic", 0.65),
    (re.compile(r"wrong.*(?:output|result|value)", re.I), "logic", 0.75),
]

ERROR_CLASSES = ("import_error", "timeout", "state_conflict", "permission", "resource", "logic", "unknown")


def classify_error(error_text: str) -> dict:
    """Classify error text into an error class with confidence."""
    scores: dict[str, float] = {c: 0.0 for c in ERROR_CLASSES}

    for pattern, error_class, confidence in CLASSIFICATION_RULES:
        if pattern.search(error_text):
            scores[error_class] = max(scores[error_class], confidence)

    best_class = max(scores, key=scores.get)  # type: ignore[arg-type]
    best_score = scores[best_class]

    if best_score == 0.0:
        best_class = "unknown"
        best_score = 0.0

    return {
        "error_class": best_class,
        "confidence": round(best_score, 2),
        "scores": {k: round(v, 2) for k, v in scores.items() if v > 0},
    }


# ── Recovery Suggestions ─────────────────────────────────

def suggest_recovery(error_class: str, error_text: str) -> list[dict]:
    """Return ordered list of recovery suggestions for the error class."""
    suggestions: list[dict] = []

    if error_class == "import_error":
        # Extract module name if possible
        m = re.search(r"No module named ['\"]?(\S+?)['\"]?(?:\s|$)", error_text)
        module = m.group(1).strip("'\"") if m else None

        suggestions.append({
            "action": "check_sys_path",
            "description": "Verify sys.path includes the module's parent directory",
            "command": "python3 -c \"import sys; print('\\n'.join(sys.path))\"",
            "auto_fixable": True,
        })
        if module:
            suggestions.append({
                "action": "find_module",
                "description": f"Locate module '{module}' in workspace",
                "command": f"find {WORKSPACE} -name '{module.split('.')[-1]}.py' -o -name '{module.split('.')[0]}' -type d 2>/dev/null | head -10",
                "auto_fixable": False,
            })
        suggestions.append({
            "action": "fix_conftest",
            "description": "Add workspace root to sys.path via conftest.py",
            "command": None,
            "auto_fixable": True,
        })
        suggestions.append({
            "action": "install_package",
            "description": "Install missing package if it's a third-party module",
            "command": f"pip install {module}" if module else None,
            "auto_fixable": False,
        })

    elif error_class == "timeout":
        # Extract timeout value if possible
        m = re.search(r"(\d+)\s*(?:s(?:ec)?|seconds?)", error_text)
        current_timeout = int(m.group(1)) if m else 120

        suggestions.append({
            "action": "retry_increased_timeout",
            "description": f"Retry with 2x timeout ({current_timeout * 2}s)",
            "command": None,
            "auto_fixable": True,
            "new_timeout": current_timeout * 2,
        })
        suggestions.append({
            "action": "skip_slow_test",
            "description": "Mark slow test with @pytest.mark.slow and skip",
            "command": None,
            "auto_fixable": False,
        })
        suggestions.append({
            "action": "use_help_mode",
            "description": "Run with --help or lightweight mode to verify setup",
            "command": None,
            "auto_fixable": False,
        })

    elif error_class == "state_conflict":
        suggestions.append({
            "action": "git_stash_pull",
            "description": "Stash local changes, pull latest, then re-apply",
            "command": "git stash && git pull --rebase && git stash pop",
            "auto_fixable": True,
        })
        suggestions.append({
            "action": "remove_lock",
            "description": "Remove stale lock file if git is stuck",
            "command": f"rm -f {WORKSPACE}/.git/index.lock",
            "auto_fixable": True,
        })
        suggestions.append({
            "action": "check_status",
            "description": "Check git status for conflict markers",
            "command": "git status --short",
            "auto_fixable": False,
        })

    elif error_class == "permission":
        suggestions.append({
            "action": "check_file_perms",
            "description": "Check file permissions on the target",
            "command": None,
            "auto_fixable": False,
        })
        suggestions.append({
            "action": "check_ssh_agent",
            "description": "Verify SSH agent has loaded keys",
            "command": "ssh-add -l 2>/dev/null || echo 'No SSH agent or no keys loaded'",
            "auto_fixable": False,
        })
        suggestions.append({
            "action": "fix_permissions",
            "description": "Fix file permissions (chmod)",
            "command": None,
            "auto_fixable": False,
        })

    elif error_class == "resource":
        suggestions.append({
            "action": "check_disk",
            "description": "Check available disk space",
            "command": "df -h .",
            "auto_fixable": False,
        })
        suggestions.append({
            "action": "check_memory",
            "description": "Check memory usage",
            "command": "vm_stat | head -5",
            "auto_fixable": False,
        })
        suggestions.append({
            "action": "clear_cache",
            "description": "Clear Python/pip caches to free space",
            "command": "pip cache purge 2>/dev/null; find /tmp -name '*.pyc' -delete 2>/dev/null",
            "auto_fixable": True,
        })

    elif error_class == "logic":
        suggestions.append({
            "action": "inspect_traceback",
            "description": "Review the full traceback for root cause",
            "command": None,
            "auto_fixable": False,
        })
        suggestions.append({
            "action": "check_test_data",
            "description": "Verify test inputs/fixtures are up to date",
            "command": None,
            "auto_fixable": False,
        })

    else:  # unknown
        suggestions.append({
            "action": "search_errors_log",
            "description": "Search existing error log for similar issues",
            "command": None,
            "auto_fixable": False,
        })

    return suggestions


# ── Auto-Fix ─────────────────────────────────────────────

def attempt_fix(error_class: str, error_text: str, dry_run: bool = True) -> dict:
    """Attempt automatic recovery. Returns result dict."""
    result = {
        "error_class": error_class,
        "dry_run": dry_run,
        "actions_taken": [],
        "success": False,
    }

    if error_class == "import_error":
        # Strategy: find conftest.py and ensure sys.path insertion
        conftest_path = WORKSPACE / "conftest.py"

        m = re.search(r"No module named ['\"]?(\S+?)['\"]?(?:\s|$)", error_text)
        module = m.group(1).strip("'\"") if m else None

        if conftest_path.exists():
            content = conftest_path.read_text()
            ws_insert = f'sys.path.insert(0, "{WORKSPACE}")'
            if str(WORKSPACE) not in content:
                if dry_run:
                    result["actions_taken"].append({
                        "action": "would_add_sys_path_to_conftest",
                        "path": str(conftest_path),
                        "line": ws_insert,
                    })
                else:
                    # Prepend sys.path fix
                    new_content = f"import sys\n{ws_insert}\n\n{content}"
                    conftest_path.write_text(new_content)
                    result["actions_taken"].append({
                        "action": "added_sys_path_to_conftest",
                        "path": str(conftest_path),
                    })
                result["success"] = True
            else:
                result["actions_taken"].append({
                    "action": "sys_path_already_present",
                    "note": f"conftest.py already includes {WORKSPACE}",
                })
                # Try to find module location
                if module:
                    found = _find_module(module)
                    result["actions_taken"].append({
                        "action": "module_search",
                        "module": module,
                        "found": found,
                    })
                    result["success"] = bool(found)
        else:
            if dry_run:
                result["actions_taken"].append({
                    "action": "would_create_conftest",
                    "path": str(conftest_path),
                })
            else:
                conftest_path.write_text(
                    f"import sys\nsys.path.insert(0, \"{WORKSPACE}\")\n"
                )
                result["actions_taken"].append({
                    "action": "created_conftest",
                    "path": str(conftest_path),
                })
            result["success"] = True

    elif error_class == "timeout":
        m = re.search(r"(\d+)\s*(?:s(?:ec)?|seconds?)", error_text)
        current_timeout = int(m.group(1)) if m else 120
        new_timeout = current_timeout * 2

        result["actions_taken"].append({
            "action": "recommend_retry" if dry_run else "retry_with_timeout",
            "original_timeout": current_timeout,
            "new_timeout": new_timeout,
            "note": f"{'Would retry' if dry_run else 'Retry'} with {new_timeout}s timeout",
        })
        result["success"] = True

    elif error_class == "state_conflict":
        if dry_run:
            result["actions_taken"].append({
                "action": "would_stash_pull_pop",
                "commands": ["git stash", "git pull --rebase", "git stash pop"],
            })
            # Check if lock file exists
            lock = WORKSPACE / ".git" / "index.lock"
            if lock.exists():
                result["actions_taken"].append({
                    "action": "would_remove_lock",
                    "path": str(lock),
                })
            result["success"] = True
        else:
            try:
                subprocess.run(["git", "stash"], cwd=WORKSPACE, check=True,
                               capture_output=True, text=True, timeout=30)
                result["actions_taken"].append({"action": "git_stash", "status": "ok"})

                subprocess.run(["git", "pull", "--rebase"], cwd=WORKSPACE, check=True,
                               capture_output=True, text=True, timeout=60)
                result["actions_taken"].append({"action": "git_pull_rebase", "status": "ok"})

                subprocess.run(["git", "stash", "pop"], cwd=WORKSPACE, check=True,
                               capture_output=True, text=True, timeout=30)
                result["actions_taken"].append({"action": "git_stash_pop", "status": "ok"})
                result["success"] = True
            except subprocess.CalledProcessError as e:
                result["actions_taken"].append({
                    "action": "git_recovery_failed",
                    "error": str(e),
                    "stderr": e.stderr[:500] if e.stderr else "",
                })

    else:
        result["actions_taken"].append({
            "action": "no_auto_fix",
            "note": f"No automatic fix available for error class '{error_class}'",
        })

    return result


def _find_module(module_name: str) -> list[str]:
    """Search workspace for a Python module by name."""
    parts = module_name.split(".")
    base = parts[0]
    found = []
    for p in WORKSPACE.rglob(f"{base}.py"):
        found.append(str(p.relative_to(WORKSPACE)))
    for p in WORKSPACE.rglob(f"{base}/__init__.py"):
        found.append(str(p.parent.relative_to(WORKSPACE)))
    return found[:10]


# ── Logging ──────────────────────────────────────────────

def log_recovery(error_text: str, classification: dict, suggestions: list[dict],
                 fix_result: dict | None = None) -> str:
    """Log diagnosis + fix attempt to auto-recovery.jsonl."""
    store = JsonlStore(RECOVERY_LOG, prefix="REC")
    entry = {
        "timestamp": now_ts(),
        "date": today(),
        "error_text": error_text[:500],  # truncate long errors
        "error_class": classification["error_class"],
        "confidence": classification["confidence"],
        "suggestions_count": len(suggestions),
        "fix_attempted": fix_result is not None,
        "fix_dry_run": fix_result.get("dry_run") if fix_result else None,
        "fix_success": fix_result.get("success") if fix_result else None,
        "fix_actions": fix_result.get("actions_taken") if fix_result else None,
    }
    result = store.append(entry)
    return result["id"]


# ── CLI ──────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Intelligent error recovery — diagnose, suggest, auto-fix.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--diagnose", metavar="ERROR_TEXT",
                        help="Diagnose an error and suggest recovery steps")
    parser.add_argument("--classify", metavar="ERROR_TEXT",
                        help="Classify error only (no suggestions)")
    parser.add_argument("--fix", action="store_true",
                        help="Attempt automatic recovery")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        dest="dry_run", help="Dry-run mode (default)")
    parser.add_argument("--no-dry-run", action="store_false", dest="dry_run",
                        help="Actually execute fixes")
    parser.add_argument("--json", action="store_true",
                        help="JSON output")

    args = parser.parse_args()

    if not args.diagnose and not args.classify:
        parser.print_help()
        sys.exit(1)

    error_text = args.diagnose or args.classify

    # Step 1: Classify
    classification = classify_error(error_text)

    if args.classify:
        if args.json:
            print(json.dumps(classification, indent=2))
        else:
            print(f"Class: {classification['error_class']}  (confidence: {classification['confidence']})")
            if classification["scores"]:
                print(f"Scores: {classification['scores']}")
        return

    # Step 2: Suggest recovery
    suggestions = suggest_recovery(classification["error_class"], error_text)

    # Step 3: Optionally fix
    fix_result = None
    if args.fix:
        fix_result = attempt_fix(classification["error_class"], error_text, dry_run=args.dry_run)

    # Step 4: Log
    rec_id = log_recovery(error_text, classification, suggestions, fix_result)

    # Output
    if args.json:
        output = {
            "id": rec_id,
            "classification": classification,
            "suggestions": suggestions,
        }
        if fix_result:
            output["fix_result"] = fix_result
        print(json.dumps(output, indent=2))
    else:
        print(f"[{rec_id}] Diagnosis: {classification['error_class']} (confidence: {classification['confidence']})")
        print()
        print("Suggested recovery steps:")
        for i, s in enumerate(suggestions, 1):
            auto = " [auto-fixable]" if s.get("auto_fixable") else ""
            print(f"  {i}. {s['description']}{auto}")
            if s.get("command"):
                print(f"     $ {s['command']}")
        if fix_result:
            print()
            mode = "DRY-RUN" if fix_result["dry_run"] else "LIVE"
            status = "SUCCESS" if fix_result["success"] else "FAILED"
            print(f"Fix attempt ({mode}): {status}")
            for action in fix_result.get("actions_taken", []):
                print(f"  - {action.get('action', '?')}: {action.get('note', action.get('status', ''))}")


if __name__ == "__main__":
    main()
