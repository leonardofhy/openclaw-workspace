#!/usr/bin/env python3
"""Sync feed recommendations to Google Sheets.

Usage:
    python3 sync_to_sheets.py --json-file digest.json   # from file
    cat digest.json | python3 sync_to_sheets.py --stdin  # from pipe
    python3 sync_to_sheets.py --backfill                 # import past digests
    python3 sync_to_sheets.py --test                     # push 3 sample rows
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    gspread = None  # type: ignore

# ── Paths ────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent.parent  # workspace root
CONFIG_PATH = SCRIPT_DIR / "config.json"
CREDS_PATH = ROOT_DIR / "secrets" / "google-service-account.json"
FEEDS_DIR = ROOT_DIR / "memory" / "feeds"
CANDIDATES_DIR = FEEDS_DIR / "candidates"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = [
    "Date", "Source", "Title", "Author", "Score", "URL",
    "Summary", "Tags", "Relevance Score", "Reasoning",
]

TZ = timezone(timedelta(hours=8))


# ── Google Sheets helpers ────────────────────────────────────────

def get_sheet_id() -> str:
    """Load sheet ID from config."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
        sid = cfg.get("google_sheets", {}).get("sheet_id", "")
        if sid:
            return sid
    return ""


def open_worksheet(sheet_id: str | None = None) -> "gspread.Worksheet":
    """Authenticate and return the first worksheet."""
    if gspread is None:
        print("ERROR: gspread not installed (pip install gspread)", file=sys.stderr)
        sys.exit(1)

    sid = sheet_id or get_sheet_id()
    if not sid:
        print("ERROR: no sheet_id in config.json", file=sys.stderr)
        sys.exit(1)

    creds = Credentials.from_service_account_file(str(CREDS_PATH), scopes=SCOPES)
    gc = gspread.authorize(creds)
    spreadsheet = gc.open_by_key(sid)
    return spreadsheet.sheet1


def ensure_headers(ws: "gspread.Worksheet") -> None:
    """Set up headers if the sheet is empty."""
    existing = ws.row_values(1)
    if existing == HEADERS:
        return
    if not existing or all(c == "" for c in existing):
        ws.update([HEADERS], range_name="A1")
        _format_sheet(ws)
        print("Headers written + sheet formatted", file=sys.stderr)


def _format_sheet(ws: "gspread.Worksheet") -> None:
    """Freeze header row, add filters, bold headers."""
    try:
        ws.freeze(rows=1)
        ws.set_basic_filter()
        ws.format("A1:J1", {
            "textFormat": {"bold": True},
            "backgroundColor": {"red": 0.9, "green": 0.93, "blue": 1.0},
        })
    except Exception as e:
        print(f"Warning: formatting failed ({e}), continuing", file=sys.stderr)


# ── Row conversion ───────────────────────────────────────────────

def item_to_row(item: dict) -> list[str]:
    """Convert a digest item dict to a sheet row."""
    date = item.get("posted", "") or datetime.now(TZ).strftime("%Y-%m-%d")
    # Normalize date to YYYY-MM-DD if possible
    if "," in date:
        # Try parsing RFC 2822 style: "Mon, 18 Mar 2026 10:00:00 GMT"
        try:
            # Strip timezone suffix since %Z is unreliable across platforms
            clean = date.strip()
            for tz_suffix in ("GMT", "UTC", "EST", "PST", "CST", "PDT", "EDT", "CDT"):
                clean = clean.replace(tz_suffix, "").strip()
            dt = datetime.strptime(clean, "%a, %d %b %Y %H:%M:%S")
            date = dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    elif "T" in date:
        # ISO 8601: "2026-03-18T10:00:00+08:00"
        date = date.split("T")[0]

    tags = item.get("tags", [])
    if isinstance(tags, list):
        tags = ", ".join(tags)

    return [
        date,
        item.get("source", ""),
        item.get("title", ""),
        item.get("author", ""),
        str(item.get("score", 0)),
        item.get("url", ""),
        item.get("snippet", ""),
        tags,
        str(item.get("interest_score", "")),
        item.get("suggested_action", ""),
    ]


# ── Dedup ────────────────────────────────────────────────────────

def get_existing_urls(ws: "gspread.Worksheet") -> set[str]:
    """Get all URLs already in the sheet (column F)."""
    try:
        url_col = ws.col_values(6)  # column F = URL
        return set(url_col[1:])  # skip header
    except Exception:
        return set()


# ── Core sync ────────────────────────────────────────────────────

def sync_items(ws: "gspread.Worksheet", items: list[dict], *, verbose: bool = True) -> int:
    """Append items to the sheet, deduplicating by URL. Returns count added."""
    ensure_headers(ws)
    existing_urls = get_existing_urls(ws)

    rows_to_add = []
    for item in items:
        url = item.get("url", "")
        if not url or url in existing_urls:
            continue
        existing_urls.add(url)
        rows_to_add.append(item_to_row(item))

    if not rows_to_add:
        if verbose:
            print("No new rows to add (all duplicates)", file=sys.stderr)
        return 0

    # Sort by date descending (newest first)
    rows_to_add.sort(key=lambda r: r[0], reverse=True)

    # Insert after header (row 2) to keep newest on top
    ws.insert_rows(rows_to_add, row=2)

    if verbose:
        print(f"Added {len(rows_to_add)} rows", file=sys.stderr)
    return len(rows_to_add)


# ── Input modes ──────────────────────────────────────────────────

def load_digest_json(data: dict) -> list[dict]:
    """Extract items from digest JSON (supports both fetch and recommend output)."""
    if "items" in data:
        return data["items"]
    if "articles" in data:
        return data["articles"]
    # Maybe it's a raw list
    if isinstance(data, list):
        return data
    return []


def cmd_json_file(path: str) -> list[dict]:
    """Load items from a JSON file."""
    with open(path) as f:
        data = json.load(f)
    return load_digest_json(data)


def cmd_stdin() -> list[dict]:
    """Load items from stdin."""
    data = json.load(sys.stdin)
    return load_digest_json(data)


def cmd_backfill() -> list[dict]:
    """Scan memory/feeds/candidates/ for past digest files."""
    items: list[dict] = []
    search_dirs = [CANDIDATES_DIR, FEEDS_DIR]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for f in sorted(search_dir.glob("*.json")):
            if f.name in ("config.json", "preferences.json"):
                continue
            try:
                with open(f) as fh:
                    data = json.load(fh)
                batch = load_digest_json(data)
                items.extend(batch)
            except (json.JSONDecodeError, KeyError):
                pass

        # Also scan .jsonl files
        for f in sorted(search_dir.glob("*.jsonl")):
            if f.name in ("seen.jsonl", "feedback.jsonl"):
                continue
            try:
                with open(f) as fh:
                    for line in fh:
                        line = line.strip()
                        if line:
                            entry = json.loads(line)
                            # Only include entries that look like articles
                            if "title" in entry and "url" in entry:
                                items.append(entry)
            except (json.JSONDecodeError, KeyError):
                pass

    print(f"Backfill: found {len(items)} items from {len(search_dirs)} dirs", file=sys.stderr)
    return items


def cmd_test() -> list[dict]:
    """Generate 3 sample rows for testing."""
    now = datetime.now(TZ).strftime("%Y-%m-%d")
    return [
        {
            "source": "hn", "title": "[TEST] LLM Interpretability Breakthrough",
            "url": f"https://test.example.com/test-1-{now}",
            "author": "test_user", "score": 250, "posted": now,
            "snippet": "Test article about interpretability research",
            "tags": ["ml", "interpretability"], "interest_score": 9.2,
            "suggested_action": "深讀",
        },
        {
            "source": "arxiv", "title": "[TEST] Speech Recognition via Transformers",
            "url": f"https://test.example.com/test-2-{now}",
            "author": "researcher", "score": 0, "posted": now,
            "snippet": "Novel ASR approach using self-supervised learning",
            "tags": ["speech", "cs.CL"], "interest_score": 7.5,
            "suggested_action": "略讀",
        },
        {
            "source": "af", "title": "[TEST] Alignment Forum: SAE Features",
            "url": f"https://test.example.com/test-3-{now}",
            "author": "neel_nanda", "score": 42, "posted": now,
            "snippet": "Sparse autoencoder feature analysis on GPT-4",
            "tags": ["alignment", "SAE"], "interest_score": 8.8,
            "suggested_action": "深讀",
        },
    ]


# ── Main ─────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Sync feed recommendations to Google Sheets")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--json-file", metavar="PATH", help="Path to digest JSON file")
    group.add_argument("--stdin", action="store_true", help="Read digest JSON from stdin")
    group.add_argument("--backfill", action="store_true", help="Import past digests from memory/feeds/")
    group.add_argument("--test", action="store_true", help="Push 3 sample rows to verify connection")
    parser.add_argument("--sheet-id", default=None, help="Override sheet ID from config")
    parser.add_argument("--dry-run", action="store_true", help="Show rows without pushing")

    args = parser.parse_args()

    # Collect items
    if args.json_file:
        items = cmd_json_file(args.json_file)
    elif args.stdin:
        items = cmd_stdin()
    elif args.backfill:
        items = cmd_backfill()
    elif args.test:
        items = cmd_test()

    if not items:
        print("No items to sync", file=sys.stderr)
        return

    print(f"Collected {len(items)} items", file=sys.stderr)

    if args.dry_run:
        for item in items:
            row = item_to_row(item)
            print("\t".join(row))
        return

    # Push to Google Sheets
    ws = open_worksheet(args.sheet_id)
    added = sync_items(ws, items)
    print(f"Done. {added} new rows synced to Google Sheets.", file=sys.stderr)


if __name__ == "__main__":
    main()
