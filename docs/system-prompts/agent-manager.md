# Task: Build Agent Manager Skill

Build `skills/agent-manager/` — a sub-agent lifecycle management system that wraps
OpenClaw's `sessions_spawn`, `subagents`, and `sessions_list` into a higher-level
management layer with auto-cleanup, naming, status dashboard, and cost tracking.

## Context

Read these files first:
- `AGENTS.md` — workspace rules, CC dispatch conventions
- `CLAUDE.md` — coding conventions (MUST follow)
- `skills/orchestrator/scripts/dag_orchestrator.py` — existing CC orchestration
- `skills/coding-agent/SKILL.md` at `/opt/homebrew/lib/node_modules/openclaw/skills/coding-agent/SKILL.md` — how CCs are currently spawned

## Problem We're Solving

Current pain points (from real usage):
1. Spawning 39 CC agents in one night — no way to track which is which
2. No auto-cleanup: completed agents stay in sessions list forever
3. No cost/token tracking per agent run
4. No dashboard: have to manually `subagents list` and parse output
5. Label naming is ad-hoc (random slugs like "ember-slug", "brisk-ridge")
6. No way to see historical runs (what did agent X produce? when?)

## What to Build

### `skills/agent-manager/scripts/agent_mgr.py`

CLI and importable module:

```bash
# Spawn with meaningful names
python3 agent_mgr.py spawn --name "Paper §3 Polish" --task "..." --model sonnet
python3 agent_mgr.py spawn --name "Feed Scorer" --task "..." --model opus --timeout 300

# Status dashboard
python3 agent_mgr.py status                    # all active agents
python3 agent_mgr.py status --all              # include completed/failed
python3 agent_mgr.py status --name "Paper*"    # filter by name glob

# History
python3 agent_mgr.py history                   # last 20 runs
python3 agent_mgr.py history --today           # today's runs only
python3 agent_mgr.py history --name "Feed*"    # filter

# Cleanup
python3 agent_mgr.py cleanup                   # kill completed sessions older than 1h
python3 agent_mgr.py cleanup --all             # kill all non-active
python3 agent_mgr.py cleanup --older-than 30m  # custom threshold

# Kill
python3 agent_mgr.py kill --name "Paper*"      # kill by name pattern
python3 agent_mgr.py kill --id <session_id>    # kill by ID
```

### Core Design

**Registry file: `memory/agents/registry.jsonl`**

Each spawn appends an entry:
```json
{
  "id": "spawn-20260319-0430-paper-s3",
  "name": "Paper §3 Polish",
  "task_summary": "Polish method section...",
  "model": "claude-sonnet-4-20250514",
  "status": "running",
  "spawned_at": "2026-03-19T04:30:00+08:00",
  "completed_at": null,
  "duration_s": null,
  "exit_code": null,
  "pid": 12345,
  "workdir": "/path/to/workspace",
  "artifacts": [],
  "error": null
}
```

**Key functions:**

1. `spawn(name, task, model, timeout, workdir) -> dict`
   - Generate meaningful ID from name + timestamp
   - Spawn CC via subprocess (claude --print --permission-mode bypassPermissions)
   - Register in registry.jsonl
   - Return spawn info

2. `update_status() -> list[dict]`
   - Read registry.jsonl
   - Check each running agent's process status (via PID)
   - Update completed/failed entries
   - Return current state

3. `get_dashboard(filter_name=None, include_completed=False) -> str`
   - Pretty-print table of agents with: name, model, status, duration, artifacts count
   - Use unicode box-drawing for nice output

4. `cleanup(older_than_minutes=60) -> int`
   - Find completed agents older than threshold
   - Return count of cleaned entries

5. `get_history(days=7, name_filter=None) -> list[dict]`
   - Read registry.jsonl, filter, return sorted by time

### `skills/agent-manager/scripts/test_agent_mgr.py`

Tests (at least 10):
- test_spawn_creates_registry_entry
- test_spawn_generates_meaningful_id
- test_update_status_detects_completed (mock subprocess)
- test_dashboard_formatting
- test_dashboard_name_filter
- test_cleanup_removes_old
- test_cleanup_preserves_recent
- test_history_filter_by_name
- test_history_filter_by_date
- test_kill_by_name_pattern

### `skills/agent-manager/SKILL.md`

Brief skill doc with:
- Description
- Commands reference
- Registry format
- Integration with orchestrator

## Constraints

- stdlib only (subprocess, json, pathlib, fnmatch, datetime)
- Do NOT use sessions_spawn tool (that's OpenClaw internal) — use `claude` CLI directly
- Registry is append-only JSONL (no rewrites, atomic appends)
- Process detection via `os.kill(pid, 0)` for checking if alive
- Must handle concurrent access (file locking via fcntl)
- Dashboard output must work in Discord (no markdown tables — use code blocks)
- Do NOT create COMPLETED.txt
- When done: `git add -A && git commit -m 'feat: agent-manager skill'`
