---
name: self-improve
description: >
  Log learnings, errors, and corrections for continuous self-improvement.
  Use when: (1) a command or operation fails unexpectedly, (2) user corrects you,
  (3) you discover outdated knowledge, (4) you find a better approach than what you did,
  (5) Leo says "記下來", "learn from this", "不要再犯". Complements debugger (which focuses on
  RCA process) and remember (which focuses on facts/decisions). This skill focuses on
  *systematic improvement* — tracking recurrence, detecting patterns, promoting to permanent files.
  NOT for: logging facts (use remember), daily events (use memory/*.md), feature requests (use task-board.md).
---

# Self-Improve

Log mistakes, corrections, and best practices so future sessions don't repeat them.

## Quick Reference

| Situation | Action |
|-----------|--------|
| Command/operation fails | `learn.py error -s "..." -e "..." -f "..."` |
| User corrects you | `learn.py log -c correction -s "..."` |
| Knowledge was outdated | `learn.py log -c knowledge_gap -s "..."` |
| Found better approach | `learn.py log -c best_practice -s "..."` |
| Recurring gotcha | `learn.py log -c gotcha -k "pattern.key" -s "..."` |
| Mark issue fixed | `learn.py resolve ERR-002 -n "fixed by ..."` |
| Check pending items | `learn.py review` |
| Find promotion candidates | `learn.py review --promote-ready` |
| Search past issues | `learn.py search "keyword"` |
| Promote to permanent file | `learn.py promote LRN-003 --to TOOLS.md` |

## CLI

```bash
# All commands
python3 skills/self-improve/scripts/learn.py <command>

# Log a learning (--force skips dedup)
learn.py log -c <category> -p <priority> -s "summary" [-d "details"] [-a "action"] [-k "pattern.key"] [--force]

# Log an error (--force skips dedup, -k for pattern key)
learn.py error -s "summary" -e "error message" [-f "fix"] [--prevention "..."] [-k "pattern.key"] [--force]

# Mark as resolved (works on both LRN and ERR)
learn.py resolve <ID> [-n "resolution notes"]

# Search (--json for machine output)
learn.py search "keyword" [--json]

# Review pending (--json for automation)
learn.py review [--promote-ready] [--json]

# Promote (works on both LRN and ERR)
learn.py promote <ID> --to <AGENTS.md|SOUL.md|TOOLS.md|MEMORY.md|PROACTIVE.md|HEARTBEAT.md|SESSION-STATE.md>

# Stats overview
learn.py stats [--json]
```

### Categories
- `correction` — user corrected you, you were wrong
- `knowledge_gap` — information you didn't know or was outdated
- `best_practice` — discovered a better way to do something
- `gotcha` — tricky/non-obvious behavior that trips you up

### Priorities
- `low` — minor, edge case
- `medium` — moderate impact, workaround exists
- `high` — significant, affects common workflows
- `critical` — blocks core functionality or data loss risk

## Detection Triggers

**Automatically log when you notice:**

Corrections (→ `log -c correction`):
- "No, that's not right..."
- "Actually, it should be..."
- Leo corrects your output or approach

Knowledge gaps (→ `log -c knowledge_gap`):
- You assumed something that turned out wrong
- API/tool behavior differs from expectation
- Documentation was outdated

Errors (→ `error`):
- Command returns non-zero exit code
- Script raises exception
- Unexpected output or behavior

Best practices (→ `log -c best_practice`):
- Found a cleaner way after initial approach
- Discovered a useful pattern worth reusing

## Recurrence & Promotion

**Pattern keys** — stable identifiers for recurring issues:
- Format: `area.specific_issue` (e.g., `config.direct_edit_fails`, `path.parent_levels`, `srun.conda_not_inherited`)
- When logging with `-k`, the system auto-detects matches and bumps recurrence count

**Promotion threshold** — when `recurrence >= 3`:
- System flags the entry as promotion-ready
- `learn.py review --promote-ready` shows candidates
- Use `learn.py promote <ID> --to <target>` to mark as promoted

**Promotion targets:**
- `TOOLS.md` — tool gotchas, API quirks, config notes
- `AGENTS.md` — workflow improvements, operating rules
- `SOUL.md` — behavioral patterns, communication style
- `PROACTIVE.md` — stuck detection, task switching
- `MEMORY.md` — long-term knowledge worth persisting
- `HEARTBEAT.md` — periodic check rules

## Data Files

```
memory/learnings/
├── learnings.jsonl    # LRN-xxx entries (corrections, best practices, gotchas)
└── errors.jsonl       # ERR-xxx entries (command failures, exceptions)
```

Both use `JsonlStore` from `skills/shared/jsonl_store.py` — atomic writes, auto-IDs, filtering.

## Relationship to Other Systems

- **debugger** — Use debugger for RCA process (reproduce → isolate → hypothesize → fix). After fixing, log the lesson here via `learn.py error`.
- **remember** — Use remember for facts, decisions, preferences. Use self-improve for *mistakes and lessons*.
- **knowledge.md** — Quick append-only notes (via `append_memory.py`). Self-improve is for tracked, searchable, promotable entries.
- **task-board.md** — Feature requests go there, not here.

## Migration

Existing `debugger/references/known-issues.md` entries have been migrated to `errors.jsonl`:
```bash
python3 skills/self-improve/scripts/learn.py migrate-known-issues
```
