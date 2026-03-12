---
name: coordinator
description: >
  Inter-bot coordination between Bot A and Bot B (e.g. laptop + server). Use when (1) delegating
  tasks to the other bot, (2) checking cross-machine task dependencies, (3) generating sync reports,
  (4) resolving git merge conflicts between branches, (5) allocating resources (GPU, experiments),
  (6) user asks "what's the status on both machines", "sync up", "who's doing what".
  Also triggered by weekly sync cron.
  NOT for: single-machine task management (use task-board), or bot communication rules (see BOT_RULES.md).
---

# Coordinator

Manage collaboration between Bot A and Bot B.

## Quick Reference

```bash
# Generate sync report
python3 skills/coordinator/scripts/sync_report.py

# Generate sync report (JSON)
python3 skills/coordinator/scripts/sync_report.py --json

# Mailbox (guaranteed delivery)
python3 skills/coordinator/scripts/mailbox.py send --from bot-a --to bot-b --title "Task title" --body "Details"
python3 skills/coordinator/scripts/mailbox.py list --to bot-b --status open
python3 skills/coordinator/scripts/mailbox.py ack MB-001
python3 skills/coordinator/scripts/mailbox.py done MB-001
```

## Collaboration Model

### Machine Roles

| Machine | Role | Strengths | Good for |
|---------|------|-----------|----------|
| **Bot B (Server/24-7)** | Always-on base | Never disconnects, cron, monitoring | heartbeat, schedules, system maintenance, background jobs |
| **Bot A (Laptop)** | Personal assistant | Travels with user, real-time interaction | interactive research, writing, quick prototypes |

### Resource Sharing
- **GPU (if available)**: accessible via SSH from either bot
- **experiments.jsonl**: shared experiment records, visible cross-machine
- **task-board.md**: global task board, use prefixes to distinguish owner (e.g. A-/B-)

## Git Sync Protocol

### Branch Strategy
- `main` — stable version, neither bot pushes directly
- `bot-a` — Bot A's working branch
- `bot-b` — Bot B's working branch

### Merge Rules
1. Each bot works on its own branch
2. To sync: `git fetch origin && git merge origin/<other-branch>`
3. Conflict resolution: the side that made the change wins; the other merges
4. task-board.md conflicts: keep the version with newer `last_touched`
5. experiments.jsonl conflicts: append-only so usually no conflict; if conflict keep both

### Auto-sync Timing
- During heartbeat: `git push`
- After important changes: `git push` immediately
- At least once daily: merge other bot's branch

## Task Delegation

### Delegation format (post to #bot-sync)
```
📤 Delegating [bot-prefix]-xx | [Title]
Reason: [why delegating]
Need: [specific deliverable]
Deadline: [time]
Context: [background the other bot needs]
```

### Delegation Rules
- Before delegating: create the task in task-board.md with the other bot's prefix
- After other bot confirms: change status to ACTIVE
- On completion: report in #bot-sync + update task-board.md

## Weekly Sync

Generated automatically on Sunday, sent to #bot-sync. See `scripts/sync_report.py`.

## Upgrade Path

Current: loose collaboration via Discord #bot-sync + git.
Future options:
- GitHub Issues for formal task tracking
- Shared experiment dashboard
- Automated merge bot
