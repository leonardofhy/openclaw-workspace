---
name: claude-usage
description: Check Claude Code plan usage (session/weekly/sonnet quotas). Use when the user asks about Claude usage, quota, limits, remaining credits, or burn rate. Trigger phrases: "查額度", "claude usage", "用量多少", "還剩多少額度", "quota", "how much usage", "plan limits".
---

# Claude Usage Checker

Query Claude Code plan usage via `skills/shared/claude_usage.py`.

## Commands

```bash
# Human-readable output (bar chart)
python3 skills/shared/claude_usage.py

# JSON (for scripts/heartbeat)
python3 skills/shared/claude_usage.py --json

# One-line summary
python3 skills/shared/claude_usage.py --oneline
```

## Output

Three metrics: Session % | Week (all models) % | Week (sonnet) % + reset times.

## Notes

- Takes ~20 seconds (spawns interactive claude CLI)
- Has built-in retry
- No API key needed — reads from `claude` CLI `/usage` command
