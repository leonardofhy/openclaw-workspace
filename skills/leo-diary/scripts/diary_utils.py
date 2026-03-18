#!/usr/bin/env python3
"""
Shared utilities for leo-diary scripts.

Provides a single source of truth for:
  - PEOPLE_ALIASES  — person → alias list (used by search_diary + generate_tags)
  - parse_date()    — Google Forms timestamp → YYYY-MM-DD
  - format_date()   — date/datetime → YYYY-MM-DD string
  - get_diary_sheet() — open the diary Google Sheet worksheet
"""
import sys
from datetime import datetime
from pathlib import Path

_WS = Path(__file__).resolve().parent.parent.parent.parent
SHEET_ID = '1CRY53JyLUXdRNDtHRCJwbPMZBo7Azhpowl15-3UigWg'
CREDS_PATH = str(_WS / 'secrets' / 'google-service-account.json')
_SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# ─── People aliases ───────────────────────────────────────────────────────────
# Canonical source of truth for person → aliases mapping.
# Used by search_diary.py (search expansion) and generate_tags.py (tag extraction).
# Union of both files' alias lists; update here to keep them in sync.
PEOPLE_ALIASES: dict[str, list[str]] = {
    "智凱": ["智凱", "智凱哥", "凱哥", "zhikai"],
    "晨安": ["晨安", "晨安哥", "chenan"],
    "康哥": ["康哥", "康", "kang"],
    "李宏毅": ["李宏毅", "宏毅", "宏毅老師", "老師", "李老師", "hungyi", "hung-yi"],
    "明淵": ["明淵", "mingyuan"],
    "朗軒": ["朗軒", "langxuan"],
    "Rocky": ["Rocky", "rocky"],
    "Wilson": ["Wilson", "wilson"],
    "Howard": ["Howard", "howard"],
    "David": ["David", "david"],
    "Ziya": ["Ziya", "ziya"],
    "Christine": ["Christine", "christine"],
    "Teddy": ["Teddy", "teddy"],
    "Zen": ["Zen", "zen"],
    "陳縕儂": ["陳縕儂", "縕儂", "yunnnung", "vivian"],
    "專題生": ["專題生"],
    "媽": ["媽", "我媽", "媽媽", "老媽"],
    "爸": ["爸", "我爸", "爸爸", "老爸"],
}


# ─── Date utilities ───────────────────────────────────────────────────────────

def parse_date(ts_str: str) -> str | None:
    """Parse a Google Forms timestamp string to YYYY-MM-DD.

    Tries both DD/MM/YYYY and MM/DD/YYYY formats.
    Returns None when the string is empty or unparseable.
    """
    if not ts_str:
        return None
    for fmt in ('%d/%m/%Y %H:%M:%S', '%m/%d/%Y %H:%M:%S'):
        try:
            return datetime.strptime(ts_str.strip(), fmt).strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            continue
    return None


def format_date(date_obj) -> str:
    """Return YYYY-MM-DD string from a date, datetime, or existing string."""
    if isinstance(date_obj, str):
        return date_obj
    return date_obj.strftime('%Y-%m-%d')


# ─── Google Sheets access ─────────────────────────────────────────────────────

def get_diary_sheet():
    """Open and return the diary Google Sheet worksheet (index 0).

    Raises an exception on any connection or auth failure — callers
    should catch and fall back to CSV as needed.
    """
    import gspread
    from google.oauth2.service_account import Credentials
    creds = Credentials.from_service_account_file(CREDS_PATH, scopes=_SCOPES)
    gc = gspread.authorize(creds)
    return gc.open_by_key(SHEET_ID).get_worksheet(0)
