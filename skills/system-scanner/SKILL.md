---
name: system-scanner
description: Scan OpenClaw workspace and tools for critical issues and improvement opportunities. Use when Leo asks to check the system health, scan for problems, identify critical issues, find things to fix, or do a system audit. Also use when something seems broken and a full diagnostic is needed.
---

# System Scanner

Runs a comprehensive scan of the OpenClaw workspace and reports critical issues, warnings, and improvement suggestions.

## Usage

```bash
python3 skills/system-scanner/scripts/scan.py
```

Exit code 0 = no critical issues. Exit code 1 = at least one critical issue found.

## What It Checks

| Area | Checks |
|------|--------|
| **Secrets** | Existence + non-empty: email_ops.env, todoist.env, google-service-account.json |
| **APIs** | Todoist, Google Calendar, Diary (Google Sheets) connectivity |
| **Git** | Uncommitted changes, unpushed commits (vs current branch upstream) |
| **Memory** | 7-day coverage of daily `.md` files, MEMORY.md freshness |
| **Delivery queue** | Stuck items in `~/.openclaw/delivery-queue` |
| **Gateway** | Platform-aware: systemd (Linux/WSL) or LaunchAgent (macOS) |
| **Gateway logs** | Recent errors, Discord WebSocket disconnects |
| **OpenClaw config** | Compaction mode, contextPruning, cron model cost |
| **Disk** | Usage ≥ 75% warn, ≥ 90% critical |
| **Tasks** | task-board staleness, overdue comms follow-ups, stuck experiments |
| **SSH tunnels** | Reverse tunnel health (Linux/WSL only) |
| **Key scripts** | Presence of core leo-diary scripts |

## After Running

- 🔴 **Critical**: address immediately before doing other work
- ⚠️  **Warn**: fix soon; each has a suggested fix
- ℹ️  **Info**: optional improvements
- ✅ **OK**: healthy

## Extending

To add a new check, add a `check_*()` function to `scan.py` and call it in `run_all()`.
Use `check(label, status, detail, fix)` to record results.

Categories: secrets, todoist, gcal, diary, smtp, git, memory,
            delivery, gateway, config, cron, disk, deps, scripts, tasks, tunnels
