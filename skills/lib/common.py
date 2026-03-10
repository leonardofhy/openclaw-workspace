"""common.py — shared constants and utilities for all workspace scripts.

Usage:
    from common import TZ, now, today_str, WORKSPACE, MEMORY, TAGS_DIR, SCRIPTS

    # Current time (always Asia/Taipei)
    current = now()            # → datetime with TZ
    t = now().strftime('%H:%M')  # → "13:47"
    d = today_str()            # → "2026-02-24"
"""
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Timezone ──
TZ = timezone(timedelta(hours=8), name='Asia/Taipei')

# ── Paths ──
WORKSPACE = Path(__file__).resolve().parent.parent.parent  # skills/lib/common.py → workspace/
MEMORY    = WORKSPACE / 'memory'
TAGS_DIR  = MEMORY / 'tags'
SECRETS   = WORKSPACE / 'secrets'
SCRIPTS   = WORKSPACE / 'skills' / 'leo-diary' / 'scripts'


# --- External Service Config (centralized, not hardcoded in scripts) ---
CAL_ID = os.environ.get('OPENCLAW_CAL_ID', 'leonardofoohy@gmail.com')
SHEET_ID = os.environ.get('OPENCLAW_SHEET_ID', '1CRY53JyLUXdRNDtHRCJwbPMZBo7Azhpowl15-3UigWg')
DISCORD_BOT_IDS = {
    "lab": os.environ.get('OPENCLAW_DISCORD_BOT_LAB', '1476497627490025644'),
    "mac": os.environ.get('OPENCLAW_DISCORD_BOT_MAC', '1473210706567495730'),
}
DISCORD_BOT_SYNC_CHANNEL = os.environ.get('OPENCLAW_DISCORD_CHANNEL', '1476624495702966506')


# ── Time helpers ──
def now() -> datetime:
    """Current time in Asia/Taipei."""
    return datetime.now(TZ)


def today_str() -> str:
    """Today's date as YYYY-MM-DD string."""
    return now().strftime('%Y-%m-%d')


def yesterday_str() -> str:
    """Yesterday's date as YYYY-MM-DD string."""
    return (now() - timedelta(days=1)).strftime('%Y-%m-%d')


def remaining_hours(target_hour: float = 23.0) -> float:
    """Hours remaining until target (default 23:00)."""
    n = now()
    current = n.hour + n.minute / 60
    return round(max(0, target_hour - current), 1)


def is_quiet_hours() -> bool:
    """True if current time is between 23:00–08:00 (no proactive messages)."""
    h = now().hour
    return h >= 23 or h < 8
