# Setup Guide — From Zero to Running

## Prerequisites

1. **OpenClaw** installed and configured ([docs](https://docs.openclaw.ai))
2. A messaging channel connected (Discord, Telegram, Signal, etc.)
3. An LLM provider configured (Anthropic Claude recommended)

## Quick Start (5 minutes)

### Step 1: Copy starter kit into your workspace

```bash
# Find your OpenClaw workspace
openclaw status  # shows workspace path

# Copy starter kit files
cp -r /path/to/starter-kit/* ~/.openclaw/workspace/
```

### Step 2: Personalize core files

Edit these files with your info:

**USER.md** — Your basic info:
```markdown
# USER.md
- **Name:** Your Name
- **Timezone:** Your/Timezone
- **Language:** Your preferred language
```

**IDENTITY.md** — Your bot's identity:
```markdown
# IDENTITY.md
- **Name:** Your bot's name
- **Creature:** What personality/character
- **Emoji:** 🤖 (pick one)
```

**SOUL.md** — Already has good defaults. Customize the vibe/personality.

**TOOLS.md** — Add your actual integrations:
- Replace `{{PLACEHOLDER}}` values with real service details
- Remove sections for services you don't use
- Add any additional tools you have

### Step 3: Set up memory directory

```bash
cd ~/.openclaw/workspace
mkdir -p memory/schedules memory/learning secrets
```

### Step 4: Configure secrets (optional)

If using integrations, add credentials:
```bash
# Todoist
echo "TODOIST_API_TOKEN=your_token" > secrets/todoist.env

# Google Calendar (Service Account)
cp /path/to/service-account.json secrets/google-service-account.json

# Email
cat > secrets/email_ops.env << 'EOF'
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_ops_email@gmail.com
SMTP_PASS=your_app_password
EMAIL_TO=your_personal_email@gmail.com
EOF
```

### Step 5: Set up cron jobs (optional)

```bash
# Heartbeat every 30 minutes
openclaw cron add --prompt "Read HEARTBEAT.md..." --schedule "*/30 8-23 * * *"

# Daily summary
openclaw cron add --prompt "Generate daily summary" --schedule "0 23 * * *"
```

### Step 6: Verify

```bash
openclaw gateway status
openclaw status
```

Send your bot a message — it should follow AGENTS.md boot flow.

## Integration Setup

### Google Calendar
1. Create a Google Cloud project
2. Enable Calendar API
3. Create a Service Account
4. Share your calendar with the service account email
5. Download the JSON key → `secrets/google-service-account.json`

### Todoist
1. Go to Todoist Settings → Integrations → Developer
2. Copy your API token → `secrets/todoist.env`

### Discord
1. Note your User ID (Developer Mode → right click → Copy ID)
2. Note channel IDs for your key channels
3. Update TOOLS.md with the IDs

## Customization

### Adding new skills
1. Create `skills/your-skill/SKILL.md`
2. Add scripts in `skills/your-skill/scripts/`
3. The bot will auto-discover skills from SKILL.md descriptions

### Dual-machine setup
1. Set up both machines with OpenClaw
2. Use the coordinator skill for cross-machine sync
3. Share the workspace via Git (private repo)
4. Configure mailbox protocol for async communication

### Adjusting boot budget
Edit limits in AGENTS.md under "Line Budgets" section.
Default: MEMORY.md ≤80 lines, SESSION-STATE.md ≤30 lines.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Bot doesn't follow boot flow | Check AGENTS.md is in workspace root |
| Memory not persisting | Verify bot has write access to workspace |
| Cron not firing | `openclaw cron list` to verify schedules |
| Skills not loading | Check SKILL.md has correct `description` field |
| Boot too slow | Run `python3 skills/shared/boot_budget_check.py` |

## Architecture Reference

See `docs/architecture-overview.md` for the full system design.
