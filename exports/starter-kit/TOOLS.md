# TOOLS.md - Service Registry & Tool Notes

> ⚡ This file is auto-loaded every session. Keep it concise but complete.
> Last updated: YYYY-MM-DD

## Enabled Services

### 🔀 Git (Version Control)
- **Repo:** `{{YOUR_GIT_REPO}}`  (Private)
- **Branch:** `main`
- **Rules:** After major changes: `git add -A && git commit && git push`
- **Tracking scope:** scripts, config .md, skills, memory persistent notes
- **Ignore:** `secrets/`, `memory/tags/`, `memory/????-??-??.md`, `*.json`, `.openclaw/`
- **Note:** No sensitive data (configured in .gitignore); MEMORY.md contains personal info, repo must stay Private

### 📧 Email (SMTP)
- **Ops account:** `{{OPS_EMAIL}}`
- **Recipient:** `{{YOUR_EMAIL}}`
- **Credentials location:** `secrets/email_ops.env`
- **Shared module:** `skills/personal-tools/scripts/email_utils.py`
- **Usage:** `from email_utils import send_email`

### ✅ Todoist
- **API Base:** `https://api.todoist.com/api/v1`
- **Credentials location:** `secrets/todoist.env`  (`TODOIST_API_TOKEN={{TODOIST_API_TOKEN}}`)
- **Script:** `skills/personal-tools/scripts/todoist_sync.py`
- **Features:** `--limit N` (incomplete tasks), `--completed-today` (today's completions)

### 📅 Google Calendar
- **Service Account:** `{{SERVICE_ACCOUNT_EMAIL}}`
- **Permission:** Make changes to events (main calendar)
- **Cal ID:** `{{GCAL_ID}}`
- **Credentials location:** `secrets/google-service-account.json`
- **Script:** `skills/personal-tools/scripts/gcal_today.py`
- **Usage:** `python3 gcal_today.py --days-ahead 0 --days-range 7`

### 📝 Google Sheets (diary/data)
- **Service Account:** same as above
- **Permission:** Readonly
- **Sheet ID:** `{{SHEET_ID}}`
- **Script:** `skills/personal-tools/scripts/read_diary.py`

### 💬 Discord
- **User ID:** `{{DISCORD_USER_ID}}`
- **Guild ID:** `{{DISCORD_GUILD_ID}}`
- **How to send:** `message` tool (channel=discord)
- **Target format:** `user:{{DISCORD_USER_ID}}` (DM), `channel:ID` (channel)
- **Channels:**
  - `#general` (`{{CHANNEL_GENERAL}}`) — **only truly important things** (system failures, decisions needed, major milestones). No bot-to-bot noise.
  - `#bot-logs` (`{{CHANNEL_BOT_LOGS}}`) — machine logs, routine records, growth reports
  - `#bot-sync` (`{{CHANNEL_BOT_SYNC}}`) — real-time bot-to-bot communication, @mentions, mailbox notifications
- **Uses:** Todoist reminders, daily summaries, weekly reports, calendar alerts

### 🎤 Whisper (Voice-to-Text)
- **Tool:** `whisper-cli` or `openai-whisper`
- **Model:** `ggml-base.bin` (base, ~147MB) — change as needed
- **Usage:** `ffmpeg -y -i input.ogg -ar 16000 -ac 1 /tmp/voice.wav && whisper-cli -m <model_path> -l <language> /tmp/voice.wav`
- **Note:** Accepts WAV format only; use ffmpeg to convert first

### 🛰️ SSH Tunnel (if dual-bot setup)
- **Remote Host:** `{{SSH_HOST}}`
- **User:** `{{SSH_USER}}`
- **Jump Host:** `{{JUMP_HOST}}`
- **Route:** `Local → {{JUMP_HOST}} → Remote`
- **Connect:** `ssh -J {{JUMP_HOST}} {{SSH_USER}}@{{SSH_HOST}}`

## Not Yet Configured / Pending Setup

- **Gmail API:** Requires separate OAuth authorization
- **memory_search:** Requires embedding API key (OpenAI/Voyage), semantic search not available

## Scripts Overview

| Script | Location | Function |
|--------|----------|----------|
| `append_memory.py` | remember/scripts/ | Write to long-term memory |
| `learn.py` | self-improve/scripts/ | Log/review/promote learnings |
| `scan.py` | system-scanner/scripts/ | System health check |
| `schedule_data.py` | daily-scheduler/scripts/ | Fetch scheduling data |
| `mailbox.py` | coordinator/scripts/ | Cross-bot mailbox |
| `boot_budget_check.py` | shared/ | Check boot file sizes |
| `ensure_state.py` | shared/ | Create missing state files |
| `task-check.py` | skills/ | Task board staleness check |

## Secrets Inventory
- `secrets/email_ops.env` — Email SMTP credentials
- `secrets/todoist.env` — Todoist API Token
- `secrets/google-service-account.json` — Google Service Account

## Cron Schedule

> Add your own cron jobs here as you set them up.

### Example schedule:
- 08:30 Morning overview (Todoist + Calendar)
- 12:00 Daily digest (email)
- 20:30 Evening task review (Discord)
- 23:50 End-of-day summary (Discord)
- Weekly: sync report, memory maintenance

### Environment Variables (centralized in `skills/lib/common.py`)
```bash
export OPENCLAW_CAL_ID="{{GCAL_ID}}"
export OPENCLAW_SHEET_ID="{{SHEET_ID}}"
export OPENCLAW_DISCORD_CHANNEL="{{CHANNEL_BOT_SYNC}}"
```
