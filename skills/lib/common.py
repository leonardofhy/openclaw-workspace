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


def _load_env_file(path: Path) -> None:
    """Load KEY=VALUE lines from a .env file into os.environ (no overwrite)."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

# ── Timezone ──
TZ = timezone(timedelta(hours=8), name='Asia/Taipei')

# ── Paths ──
WORKSPACE = Path(__file__).resolve().parent.parent.parent  # skills/lib/common.py → workspace/
MEMORY    = WORKSPACE / 'memory'
TAGS_DIR  = MEMORY / 'tags'
SECRETS   = WORKSPACE / 'secrets'
SCRIPTS   = WORKSPACE / 'skills' / 'leo-diary' / 'scripts'


# --- External Service Config (loaded from secrets/services.env, no hardcoded IDs) ---
_load_env_file(SECRETS / 'services.env')

CAL_ID = os.environ.get('OPENCLAW_CAL_ID', '')
SHEET_ID = os.environ.get('OPENCLAW_SHEET_ID', '')
DISCORD_BOT_IDS = {
    "lab": os.environ.get('OPENCLAW_DISCORD_BOT_LAB', ''),
    "mac": os.environ.get('OPENCLAW_DISCORD_BOT_MAC', ''),
}
DISCORD_BOT_SYNC_CHANNEL = os.environ.get('OPENCLAW_DISCORD_CHANNEL', '')


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


def load_todoist_token():
    token = os.environ.get('TODOIST_API_TOKEN')
    if token:
        return token
    env_path = SECRETS / 'todoist.env'
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith('TODOIST_API_TOKEN='):
                return line.split('=', 1)[1].strip()
    raise RuntimeError('TODOIST_API_TOKEN not found')
