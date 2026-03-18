---
name: agent-manager
description: 'Sub-agent lifecycle management — spawn, track, dashboard, cleanup for Claude Code agents. Use when spawning multiple agents and need to track them, view status dashboards, clean up old sessions, or review agent history.'
metadata:
  { "openclaw": { "emoji": "🤖", "requires": { "anyBins": ["claude"] } } }
---

# Agent Manager

Higher-level management layer for Claude Code sub-agents with naming, status
dashboard, history, and auto-cleanup.

## Commands

```bash
# Spawn with meaningful names
python3 agent_mgr.py spawn --name "Paper §3 Polish" --task "..." --model sonnet
python3 agent_mgr.py spawn --name "Feed Scorer" --task "..." --model opus --timeout 300

# Status dashboard
python3 agent_mgr.py status                    # active agents only
python3 agent_mgr.py status --all              # include completed/failed
python3 agent_mgr.py status --name "Paper*"    # filter by name glob

# History
python3 agent_mgr.py history                   # last 20 runs (7 days)
python3 agent_mgr.py history --today           # today only
python3 agent_mgr.py history --name "Feed*"    # filter by name

# Cleanup
python3 agent_mgr.py cleanup                   # remove completed older than 1h
python3 agent_mgr.py cleanup --all             # remove all non-running
python3 agent_mgr.py cleanup --older-than 30m  # custom threshold

# Kill
python3 agent_mgr.py kill --name "Paper*"      # by name pattern
python3 agent_mgr.py kill --id <spawn-id>      # by ID
```

## Registry

Append-only JSONL at `memory/agents/registry.jsonl`. Each entry:

| Field          | Type       | Description                        |
|----------------|------------|------------------------------------|
| `id`           | string     | `spawn-YYYYMMDD-HHMM-slug`        |
| `name`         | string     | Human-readable name                |
| `task_summary` | string     | First 200 chars of task prompt     |
| `model`        | string     | Full model ID                      |
| `status`       | string     | running/completed/failed/killed    |
| `spawned_at`   | ISO 8601   | UTC timestamp                      |
| `pid`          | int        | OS process ID                      |
| `duration_s`   | float|null | Total runtime in seconds           |

## Model Aliases

- `sonnet` → `claude-sonnet-4-20250514`
- `opus` → `claude-opus-4-20250514`
- `haiku` → `claude-haiku-4-5-20251001`

## Integration

Import as module from orchestrator or other skills:

```python
from skills.agent_manager.scripts.agent_mgr import spawn, update_status, get_dashboard
```

File locking via `fcntl.flock` ensures safe concurrent access to the registry.
