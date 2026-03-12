# AI Personal Assistant Architecture

> Built on [OpenClaw](https://github.com/openclaw/openclaw) — a 24/7 AI personal assistant system.
> This document describes the architecture and design patterns.

---

## 1. System Overview

```
┌─────────────────────────────────────────────────┐
│                    User                          │
│        Discord / Telegram / Signal / ...         │
└──────────────┬──────────────────┬────────────────┘
               │                  │
       ┌───────▼───────┐  ┌──────▼────────┐
       │  Bot A (Mobile)│  │ Bot B (24/7)   │
       │  Laptop        │  │ Server/Desktop │
       │  Personal aide  │  │ Always-on base │
       └───────┬───────┘  └──────┬────────┘
               │    Mailbox Protocol │
               └──────────────────┘
                       │
              ┌────────▼────────┐
              │  Shared Git Repo │
              │  (Private)       │
              └──────────────────┘
```

**Dual-machine architecture**: Two machines run the same "soul" as different instances, synced via Git + Mailbox protocol. One travels with the user, the other stays online 24/7 for cron jobs, heartbeat monitoring, and background tasks.

---

## 2. Core Design Principles

### 2.1 Memory Hierarchy

```
Boot Memory (loaded every session)      ≤300 lines
├── MEMORY.md                           ≤80 lines  — condensed long-term memory
├── SESSION-STATE.md                    ≤30 lines  — working memory / RAM
├── SOUL.md                             ≤50 lines  — personality & values
├── USER.md                             ≤20 lines  — user basic info
└── anti-patterns.md                    ≤50 lines  — absolute DON'T list

Long-term Memory (read on demand)
├── memory/YYYY-MM-DD.md                — daily notes
├── memory/memory-full.md               — complete memory
├── memory/knowledge.md                 — technical knowledge base
└── learnings.jsonl                     — structured lessons
```

**Key designs:**
- **Boot Budget System** — startup path is fixed size (≤300 lines), capabilities grow infinitely. Like kernel vs user-space.
- **WAL Protocol (Write-Ahead Logging)** — when important info appears in conversation, write to file BEFORE responding. Ensures memory survives session interruptions.
- **Eviction Policy** — content exceeding budgets automatically demotes to deeper storage.

### 2.2 Document Priority

```
1. AGENTS.md    — Constitution (highest priority, cannot be overridden)
2. SOUL.md      — Personality
3. PROACTIVE.md — Operating manual
4. HEARTBEAT.md — Periodic checks
5. SKILL.md     — Specific skills
```

Higher-priority documents win on conflicts.

### 2.3 Self-Improvement Loop

```
Make mistake / Get corrected / Discover new knowledge
        │
        ▼
  learn.py log (structured record)
        │
        ▼
  Periodic review (during heartbeat)
        │
        ├─ recurrence ≥ 3 → promote to permanent rule
        ├─ pending > 7 days → must resolve
        └─ stable → archive
```

---

## 3. Skills (Modular Capabilities)

Loaded on demand, don't consume boot resources. Each skill has its own `SKILL.md` + scripts.

| Skill | Function | Description |
|-------|----------|-------------|
| **daily-scheduler** | Schedule management | PLAN/ACTUAL separation, cross-midnight, GCal+Todoist sync |
| **self-improve** | Continuous improvement | Error tracking, lesson recording, anti-pattern detection, auto-promote |
| **coordinator** | Multi-bot coordination | Mailbox protocol, task delegation, Git merge handling |
| **senior-engineer** | Engineering mode | Rigorous engineering practices, RCA, architecture decisions |
| **diary-polisher** | Diary polishing | Voice-to-text restoration, preserving colloquial style & thought rhythm |
| **remember** | Memory writer | Write facts, ideas, decisions to long-term memory |
| **system-scanner** | Health check | Scan workspace for problems & improvement opportunities |

---

## 4. Heartbeat System

```
Every ~30 minutes
    │
    ├─ Self-Awareness (internal, no messages)
    │   └─ review learnings, check stats
    │
    ├─ System Quick-Check (rotate 1-2 items)
    │   └─ git status, task board, SSH tunnel, boot budget
    │
    └─ Decide whether to notify
        ├─ New actionable alert → fix + notify
        ├─ Already-notified alert → silence (Anti-Spam Rule)
        ├─ Did meaningful work → log to bot-logs
        └─ Nothing happened → HEARTBEAT_OK (silence)
```

**Anti-Spam Rule**: Same alert not re-sent within 24 hours unless status changes.

---

## 5. Integrated Services

| Service | Purpose | Access Method |
|---------|---------|---------------|
| Google Calendar | Schedule management | Service Account API |
| Todoist | Task management | REST API |
| Google Sheets | Diary data | Service Account API |
| Discord | Primary communication | OpenClaw message tool |
| Email (SMTP) | Digests, notifications | Python script |
| Git | Memory sync, version control | SSH |
| Whisper | Voice-to-text | Local model |

---

## 6. Safety Design

- **Privacy layering**: MEMORY.md only loaded in direct conversations with the user, not in group chats
- **External actions require confirmation**: Sending emails, posts, etc. need user approval
- **Channel rules**: Main channel only for truly important things; bot-to-bot communication uses dedicated channels
- **Late-night silence**: 23:00-08:00 no proactive notifications (unless urgent)
- **VBR (Verify Before Reporting)**: Must actually verify before saying "done"

---

## 7. Design Philosophy

> **Be genuinely helpful, not performatively helpful.**

- 🏗️ **File > Brain** — all memories written to files, never rely on "mental notes"
- 🔄 **Boot path fixed, capabilities grow infinitely** — kernel vs user-space concept
- 🤫 **Silence is golden** — nothing happened = shut up, something happened = speak up
- 🔧 **Fix first, then report** — fix what you can, then report what you did
- 📝 **PLAN ≠ ACTUAL** — plan and reality tracked separately, honest about divergence
- 🧠 **WAL Protocol** — important info written to file before responding, no risk of loss
- 🔁 **Self-improvement is systematic** — not just "I'll be careful next time", but structured tracking + auto-promote

---

## 8. Tech Stack

- **Platform**: [OpenClaw](https://github.com/openclaw/openclaw) (open-source AI agent framework)
- **Models**: Claude (Anthropic) — Opus / Sonnet / Haiku as needed
- **Runtime**: Node.js + Python scripts
- **OS**: macOS (mobile) + Linux/WSL2 (24/7)
- **Version control**: Git (Private repo)
