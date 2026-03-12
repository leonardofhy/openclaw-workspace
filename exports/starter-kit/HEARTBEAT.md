# HEARTBEAT.md - Periodic Checks

> Core principle: **Silence is golden. Only speak when it matters.**
> #general (or your main channel) is for humans, not machine logs.

## Decision Flow (every heartbeat)

### Step 1: Self-Awareness (internal, no messages)
1. `python3 skills/self-improve/scripts/learn.py review` — check pending items
2. `python3 skills/self-improve/scripts/learn.py stats` — look at trends
3. If any pending > 7 days → **immediately promote or resolve** (see Learnings TTL)
4. If recurrence ≥ 3 for any error → **trigger Fix-First Protocol** (see PROACTIVE.md §10)

### Step 2: System Quick-Check (pick 1-2 each heartbeat)
- `python3 skills/shared/ensure_state.py` → ensure state files exist (auto-creates on first boot)
- `git status --short` → uncommitted changes? commit + push
- `python3 skills/task-check.py` → alerts? handle them
- SSH tunnel alive check (if applicable)
- Rotate through checks below

### Step 3: Decide Whether to Notify

**🚨 Anti-Spam Rule (highest priority):**
1. Read `memory/heartbeat-state.json` `recent_alerts`
2. If what you're about to send is **essentially the same as something sent in the past 24h** (same stale task, same system failure, same deadline) → **don't send**
3. Only re-notify when **status changes** (e.g. stale task was fixed and broke again, new failure, deadline enters more urgent stage)
4. After sending an alert, write to `heartbeat-state.json`: `recent_alerts[<key>] = {ts, summary}`
5. At start of each heartbeat: clean up entries >24h old

```
IF there is a NEW actionable alert (not sent in past 24h)
  → fix the issue (fix what you can first)
  → post to #general: brief description + what you did + what {{NICKNAME}} needs to do (if anything)
  → update heartbeat-state.json
  → no fixed template needed, speak like a human

ELSE IF there is an actionable alert but already notified
  → don't post to #general (already notified, wait for {{NICKNAME}} or status change)
  → can log to memory/YYYY-MM-DD.md that you checked

ELSE IF you did meaningful work (fixed bug, pushed tasks forward, cleaned up learnings)
  → log to memory/YYYY-MM-DD.md
  → post to #bot-logs: brief record (for audit trail)
  → don't post to #general

ELSE (nothing happened, everything normal)
  → HEARTBEAT_OK (silent)
```

## Rotation Checks (pick 1-2 each heartbeat)

### 📅 Calendar & Tasks & Deadlines
- Run `python3 skills/task-check.py`, handle any alerts
- Check calendar events within 2 hours, set reminders if needed

### 🔀 Git Sync
- `git status --short`, auto-commit + push if there are uncommitted changes

### 🔧 System Health (once per week)
- Run `python3 skills/system-scanner/scripts/scan.py`
- 🔴 Notify immediately (main channel), ⚠️ log to memory

### 📝 Memory Maintenance (every 2-3 days)
- Does today's `memory/YYYY-MM-DD.md` exist?
- Does `MEMORY.md` need updating? (watch ≤80 line budget)

### 📏 Boot Budget Check (once per week)
- Run `python3 skills/shared/boot_budget_check.py`
- exit 1 (⚠️ approaching limit) → proactively slim down (evict old content to memory-full.md or archive)
- exit 2 (🔴 over limit) → handle immediately, don't wait for next heartbeat
- SESSION-STATE.md: archive Recent Context >48h to daily memory

### 🔄 Learnings Cleanup (once per week, or when pending > 5)
- Run `learn.py review`
- recurrence ≥ 3 → promote (add to appropriate .md)
- pending > 7 days → must resolve or escalate
- Goal: pending ≤ 3

## Channel Rules
> Customize these for your messaging platform.

- **#general** (main channel): **only truly important things** (system failures, {{NICKNAME}} needs to decide immediately, major milestone). Bot-to-bot communication **not allowed here**
- **#bot-logs**: machine logs, routine work records, self-awareness, daily growth reports
- **#bot-sync**: cross-bot communication, @mentions, mailbox notifications (if you have a second bot)
- Late night (23:00-08:00) don't post to main channel unless urgent
- #bot-logs and #bot-sync have no time restrictions
