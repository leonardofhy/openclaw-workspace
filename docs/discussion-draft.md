# [Feature Proposal] Agent Manager Skill — Sub-agent Lifecycle Management

**Related issue:** #49895 (Sub-agent lifecycle management: better naming and dynamic creation/destruction)

## Problem

When using OpenClaw to orchestrate multiple Claude Code (or other coding agent) sessions, lifecycle management becomes painful at scale:

1. **No meaningful naming** — sub-agents get random slugs (`ember-slug`, `brisk-ridge`), hard to tell apart when running 10+ simultaneously
2. **No auto-cleanup** — completed sessions stay in `subagents list` forever
3. **No history** — after a session ends, there's no record of what it produced, how long it took, or whether it succeeded
4. **No cost awareness** — no tracking of token usage or duration per agent run
5. **No dashboard** — need to manually parse `subagents list` output

## Proposed Solution

A self-contained **AgentSkill** (`agent-manager`) that wraps `claude --print` spawning with a persistent JSONL registry for tracking, naming, cleanup, and history.

### CLI Interface

```bash
# Spawn with meaningful names
agent_mgr.py spawn --name "Paper §3 Polish" --task "..." --model sonnet

# Status dashboard (code-block formatted for Discord/terminal)
agent_mgr.py status
agent_mgr.py status --all              # include completed/failed
agent_mgr.py status --name "Paper*"    # glob filter

# History of past runs
agent_mgr.py history --today
agent_mgr.py history --name "Feed*"

# Lifecycle management  
agent_mgr.py cleanup                   # remove completed sessions >1h old
agent_mgr.py cleanup --older-than 30m
agent_mgr.py kill --name "Paper*"      # kill by name pattern
```

### Design Decisions

- **JSONL registry** (`memory/agents/registry.jsonl`) — append-only, crash-safe, human-readable
- **Atomic writes** — uses `os.replace()` for safe concurrent access  
- **Process detection** — `os.kill(pid, 0)` to check if agent is still alive
- **Model aliases** — `sonnet` → `claude-sonnet-4-6`, `opus` → `claude-opus-4-6`
- **ID generation** — `{slug}-{HHMMSS}-{random}` for uniqueness without UUID noise
- **Pure stdlib** — no external dependencies beyond Python 3.10+

### What's Built

- `agent_mgr.py` — 465 lines, full CLI with spawn/status/history/cleanup/kill
- `test_agent_mgr.py` — 21 tests, all passing
- `SKILL.md` — skill description and usage docs
- Code reviewed and hardened (race conditions, atomic writes, edge cases)

## Questions for Maintainers

1. Is this better contributed as a **built-in skill** (PR to `skills/`) or as a **ClawHub skill**?
2. Should this integrate with OpenClaw's native `sessions_spawn` / `subagents` APIs instead of wrapping `claude --print` directly?
3. Any naming conventions or API patterns I should follow for skill CLI tools?

## Implementation

Full source available for review. Happy to adapt to maintainer preferences on architecture, naming, or integration approach.

Built with AI assistance (Claude Opus 4.6) — reviewed, tested, and hardened.
