"""common.py — shared constants and utilities for all workspace scripts.

Usage:
    from common import TZ, now, today_str, WORKSPACE, MEMORY, SECRETS

    current = now()              # → datetime with TZ
    t = now().strftime('%H:%M')  # → "13:47"
    d = today_str()              # → "2026-02-24"

Configuration:
    Set environment variables to override defaults:
        OPENCLAW_CAL_ID      — Google Calendar ID
        OPENCLAW_SHEET_ID    — Google Sheet ID
        OPENCLAW_DISCORD_CHANNEL — Discord bot-sync channel
"""
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Timezone ──
# Change TZ_OFFSET_HOURS to match your location
TZ_OFFSET_HOURS = 8  # e.g. -5 for EST, 0 for UTC, 8 for CST/SGT
TZ = timezone(timedelta(hours=TZ_OFFSET_HOURS), name='Local')

# ── Paths ──
WORKSPACE = Path(__file__).resolve().parent.parent.parent  # skills/lib/common.py → workspace/
MEMORY    = WORKSPACE / 'memory'
TAGS_DIR  = MEMORY / 'tags'
SECRETS   = WORKSPACE / 'secrets'
SCRIPTS   = WORKSPACE / 'skills' / 'personal-tools' / 'scripts'  # Adjust if you rename this skill


# ── External Service Config (centralized, not hardcoded in scripts) ──
CAL_ID = os.environ.get('OPENCLAW_CAL_ID', '{{GCAL_ID}}')
SHEET_ID = os.environ.get('OPENCLAW_SHEET_ID', '{{SHEET_ID}}')
DISCORD_BOT_IDS = {
    "bot-b": os.environ.get('OPENCLAW_DISCORD_BOT_B', '{{DISCORD_BOT_B_ID}}'),
    "bot-a": os.environ.get('OPENCLAW_DISCORD_BOT_A', '{{DISCORD_BOT_A_ID}}'),
}
DISCORD_BOT_SYNC_CHANNEL = os.environ.get('OPENCLAW_DISCORD_CHANNEL', '{{CHANNEL_BOT_SYNC}}')


# ── Time helpers ──
def now() -> datetime:
    """Current time in your timezone."""
    return datetime.now(TZ)


def today_str() -> str:
    """Today's date as YYYY-MM-DD string."""
    return now().strftime('%Y-%m-%d')


def yesterday_str() -> str:
    """Yesterday's date as YYYY-MM-DD string."""
    return (now() - timedelta(days=1)).strftime('%Y-%m-%d')
