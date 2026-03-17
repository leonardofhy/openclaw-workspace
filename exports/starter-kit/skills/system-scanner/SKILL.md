---
name: system-scanner
description: Scan OpenClaw workspace and tools for critical issues and improvement opportunities. Use when the user asks to check system health, scan for problems, or do a system audit. Also use when something seems broken and a full diagnostic is needed.
---

# System Scanner

Runs a comprehensive scan of the OpenClaw workspace and reports critical issues, warnings, and improvement suggestions.

## Usage

```bash
python3 skills/system-scanner/scripts/scan.py
python3 skills/system-scanner/scripts/scan.py --quiet       # problems only
python3 skills/system-scanner/scripts/scan.py --json        # machine-readable
python3 skills/system-scanner/scripts/scan.py --category git memory   # specific categories
```

Exit code 0 = no critical issues. Exit code 1 = at least one critical issue found.

## What It Checks

| Area | Checks |
|------|--------|
| **Secrets** | Existence + non-empty: email_ops.env, todoist.env, google-service-account.json |
| **APIs** | Todoist, Google Calendar connectivity |
| **Git** | Uncommitted changes, unpushed commits |
| **Memory** | 7-day coverage of daily .md files, MEMORY.md freshness |
| **Gateway** | OpenClaw gateway service status |
| **Disk** | Usage ≥75% warn, ≥90% critical |
| **Key scripts** | Presence of core scripts |

## After Running

- 🔴 **Critical**: address immediately before doing other work
- ⚠️  **Warn**: fix soon; each has a suggested fix
- ℹ️  **Info**: optional improvements
- ✅ **OK**: healthy

## Extending

To add a new check, add a `check_*()` function to `scan.py` and call it in `run_all()`.
Use `check(label, status, detail, fix)` to record results.
