# OpenClaw Personal Assistant Starter Kit

A complete bootstrap template for building a personal AI assistant on [OpenClaw](https://github.com/openclaw/openclaw).

This kit gives you a production-ready structure with:
- 📦 **Boot Budget System** — fixed-size startup context (≤300 lines total)
- 🧠 **WAL Protocol** — write-ahead logging to survive session restarts
- 🔄 **Self-Improvement Loop** — structured error/learning tracking
- 💓 **Heartbeat System** — periodic checks with anti-spam rules
- 🤝 **Dual-Bot Coordinator** — two-machine setup via Git + Mailbox
- 🛠️ **Core Skills** — scheduler, remember, system-scanner, diary-polisher

---

## Quickstart

### 1. Prerequisites

- [OpenClaw](https://github.com/openclaw/openclaw) installed and configured
- Python 3.10+
- Git
- A Discord server (for notifications) — or swap for any messaging channel

### 2. Copy files to your workspace

```bash
cp -r starter-kit/* ~/.openclaw/workspace/
```

### 3. Fill in your details

Edit these files first:
- **`USER.md`** — your name, timezone, language preferences
- **`IDENTITY.md`** — give your bot a name and personality
- **`TOOLS.md`** — add your API keys and service connections
- **`MEMORY.md`** — leave mostly empty, bot will populate it

### 4. Set environment variables (optional, for scripts)

```bash
export OPENCLAW_CAL_ID="your-calendar-id@gmail.com"
export OPENCLAW_SHEET_ID="your-google-sheet-id"
export OPENCLAW_DISCORD_CHANNEL="your-channel-id"
```

Or hardcode them in `secrets/` files (see `TOOLS.md`).

### 5. Initialize state files

```bash
python3 skills/shared/ensure_state.py
```

### 6. Check boot budget

```bash
python3 skills/shared/boot_budget_check.py
```

Should output: `✅ TOTAL: X/300 (XX%)`

### 7. Start chatting

Open OpenClaw and start a conversation. The bot will:
1. Read `SESSION-STATE.md` on every session start
2. Load `SOUL.md`, `USER.md`, `MEMORY.md` in main sessions
3. Follow the boot flow in `AGENTS.md`

---

## Directory Structure

```
workspace/
├── AGENTS.md             — Constitution (highest priority)
├── SOUL.md               — Bot personality & values
├── USER.md               — About your human
├── IDENTITY.md           — Bot's own identity
├── HEARTBEAT.md          — Periodic check rules
├── TOOLS.md              — Service registry & credentials map
├── MEMORY.md             — Long-term memory (≤80 lines, auto-managed)
├── SESSION-STATE.md      — Working RAM (≤30 lines, survives compaction)
│
├── memory/
│   ├── YYYY-MM-DD.md     — Daily notes (auto-created)
│   ├── anti-patterns.md  — Absolute DON'T list (boot-loaded)
│   ├── knowledge.md      — Quick facts & lessons
│   ├── working-buffer.md — Danger-zone log for long sessions
│   └── heartbeat-state.json  — Anti-spam tracker (auto-created)
│
└── skills/
    ├── shared/           — Shared utilities
    ├── self-improve/     — Error/learning tracker
    ├── remember/         — Long-term memory writer
    ├── daily-scheduler/  — Daily schedule management
    ├── coordinator/      — Multi-bot coordination
    ├── senior-engineer/  — Engineering best practices
    ├── system-scanner/   — System health checker
    └── diary-polisher/   — Voice diary transcription polisher
```

---

## Key Concepts

### Boot Budget (≤300 lines total)
Files loaded on every session. Keep them lean. Overflow → evict to `memory/memory-full.md`.

| File | Budget |
|------|--------|
| `MEMORY.md` | 80 lines |
| `SESSION-STATE.md` | 30 lines |
| `memory/anti-patterns.md` | 50 lines |
| `SOUL.md` | 50 lines |
| `USER.md` | 20 lines |

### WAL Protocol
When a conversation contains: corrections, names, decisions, preferences, or specific values → **write to SESSION-STATE.md first, then reply**.

### Self-Improvement
```bash
python3 skills/self-improve/scripts/learn.py log -c correction -s "summary"
python3 skills/self-improve/scripts/learn.py review
```

### Heartbeat
Triggered every ~30 min. Checks system health, runs tasks, notifies only when something new happens. See `HEARTBEAT.md` for the full decision flow.

---

## Customization Guide

1. **Add a new skill**: Create `skills/your-skill/SKILL.md` and add a description to `AGENTS.md`'s available_skills section.
2. **Add a service**: Add it to `TOOLS.md` with credentials in `secrets/`.
3. **Adjust bot personality**: Edit `SOUL.md`.
4. **Change check frequency**: Edit `HEARTBEAT.md` rotation section.
5. **Add anti-patterns**: Add to `memory/anti-patterns.md` (keep ≤10 entries, ≤50 lines).

---

## Full Setup Guide

See `docs/setup-guide.md` for step-by-step instructions from zero to running.

## Architecture Overview

See `docs/architecture-overview.md` for system design details.
