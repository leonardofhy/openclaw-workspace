#!/usr/bin/env python3
"""Sync feedback from Google Sheet column K back into the feed engine.

Reads rows where the 'Feedback' column (K, index 10) contains a thumbs-up/down
signal, calls record_feedback() from feed_engine, and updates preferences.json
to boost/penalize keywords extracted from liked/disliked articles.

Usage:
    python3 feedback_sync.py              # apply feedback
    python3 feedback_sync.py --dry-run    # preview without writing
    python3 feedback_sync.py --help
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent.parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
CREDS_PATH = ROOT_DIR / "secrets" / "google-service-account.json"
PREFS_PATH = ROOT_DIR / "memory" / "feeds" / "preferences.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

TZ = timezone(timedelta(hours=8))

POSITIVE_SIGNALS = {"👍", "like", "yes", "good", "1", "+1"}
NEGATIVE_SIGNALS = {"👎", "dislike", "no", "bad", "-1"}

# Words to skip when extracting keywords from titles
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "have", "has", "do", "does", "can", "could", "will", "would", "should",
    "that", "this", "it", "its", "not", "no", "as", "into", "about", "than",
    "via", "how", "what", "when", "where", "why", "which",
}

FEEDBACK_COL_IDX = 10   # 0-based index of column K in each row list
FEEDBACK_HEADER = "Feedback"


# ---------------------------------------------------------------------------
# Imports with graceful degradation
# ---------------------------------------------------------------------------

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    gspread = None  # type: ignore


# Feed engine lives in the same directory
sys.path.insert(0, str(SCRIPT_DIR))
try:
    from feed_engine import record_feedback
except ImportError as e:
    print(f"ERROR: cannot import feed_engine: {e}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Sheet helpers
# ---------------------------------------------------------------------------

def get_sheet_id() -> str:
    if CONFIG_PATH.exists():
        cfg = json.loads(CONFIG_PATH.read_text())
        sid = cfg.get("google_sheets", {}).get("sheet_id", "")
        if sid:
            return sid
    return ""


def open_worksheet():
    if gspread is None:
        print("ERROR: gspread not installed (pip install gspread)", file=sys.stderr)
        sys.exit(1)
    sid = get_sheet_id()
    if not sid:
        print("ERROR: no sheet_id in config.json", file=sys.stderr)
        sys.exit(1)
    if not CREDS_PATH.exists():
        print(f"ERROR: credentials not found at {CREDS_PATH}", file=sys.stderr)
        sys.exit(1)
    creds = Credentials.from_service_account_file(str(CREDS_PATH), scopes=SCOPES)
    gc = gspread.authorize(creds)
    return gc.open_by_key(sid).sheet1


def ensure_feedback_column(ws, dry_run: bool) -> None:
    """Add 'Feedback' header to column K if missing."""
    header_row = ws.row_values(1)
    if len(header_row) <= FEEDBACK_COL_IDX or header_row[FEEDBACK_COL_IDX].strip() == "":
        print(f"  → Adding '{FEEDBACK_HEADER}' header to column K", flush=True)
        if not dry_run:
            # gspread uses 1-based col numbering
            ws.update_cell(1, FEEDBACK_COL_IDX + 1, FEEDBACK_HEADER)
    else:
        existing = header_row[FEEDBACK_COL_IDX]
        if existing.strip() != FEEDBACK_HEADER:
            print(f"  ⚠ Column K header is '{existing}', expected '{FEEDBACK_HEADER}' — proceeding anyway")


# ---------------------------------------------------------------------------
# Feedback parsing
# ---------------------------------------------------------------------------

def parse_feedback_signal(raw: str) -> bool | None:
    """Return True=positive, False=negative, None=not a signal."""
    val = raw.strip().lower()
    if val in {s.lower() for s in POSITIVE_SIGNALS}:
        return True
    if val in {s.lower() for s in NEGATIVE_SIGNALS}:
        return False
    return None


def extract_keywords(title: str, tags: str) -> list[str]:
    """Extract meaningful single-word and bigram keywords from title + tags."""
    # Combine and tokenize
    text = f"{title} {tags}".lower()
    words = re.findall(r"[a-z][a-z0-9\-]+", text)
    words = [w for w in words if w not in STOPWORDS and len(w) > 2]

    keywords = list(words)
    # Also add bigrams from title
    title_words = re.findall(r"[a-z][a-z0-9\-]+", title.lower())
    title_words = [w for w in title_words if w not in STOPWORDS]
    for i in range(len(title_words) - 1):
        keywords.append(f"{title_words[i]} {title_words[i+1]}")

    return list(dict.fromkeys(keywords))  # dedup, preserve order


# ---------------------------------------------------------------------------
# Preferences update
# ---------------------------------------------------------------------------

def load_prefs() -> dict:
    if PREFS_PATH.exists():
        return json.loads(PREFS_PATH.read_text())
    return {
        "version": 1,
        "boost_keywords": {},
        "penalty_keywords": {},
        "preferred_categories": [],
        "min_hn_score": 20,
    }


def save_prefs(prefs: dict, dry_run: bool) -> None:
    prefs["updated"] = datetime.now(TZ).isoformat()
    if dry_run:
        print(f"  [dry-run] would write preferences.json")
        return
    PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PREFS_PATH.write_text(json.dumps(prefs, indent=2, ensure_ascii=False) + "\n")
    print(f"  ✓ preferences.json updated")


def update_prefs(prefs: dict, keywords: list[str], positive: bool, weight: int = 1) -> int:
    """
    Add keywords to boost or penalty dict. Returns count of new keywords added.
    Existing keywords keep their current weight; new ones get weight ±1.
    """
    if positive:
        target = prefs.setdefault("boost_keywords", {})
        delta = weight
    else:
        target = prefs.setdefault("penalty_keywords", {})
        delta = -weight

    added = 0
    for kw in keywords:
        if kw not in target:
            target[kw] = delta
            added += 1
    return added


# ---------------------------------------------------------------------------
# Main sync logic
# ---------------------------------------------------------------------------

def sync_feedback(dry_run: bool) -> int:
    """Returns number of feedback rows processed."""
    print("Connecting to Google Sheets…", flush=True)
    ws = open_worksheet()

    ensure_feedback_column(ws, dry_run)

    # Fetch all rows
    all_rows = ws.get_all_values()
    if not all_rows:
        print("Sheet is empty.")
        return 0

    header = all_rows[0]
    data_rows = all_rows[1:]

    # Column indices (0-based) — map header names
    def col(name: str, default: int) -> int:
        try:
            return header.index(name)
        except ValueError:
            return default

    idx_title  = col("Title", 2)
    idx_source = col("Source", 1)
    idx_url    = col("URL", 5)
    idx_tags   = col("Tags", 6)
    idx_fb     = FEEDBACK_COL_IDX

    prefs = load_prefs()
    processed = 0
    new_kw_total = 0

    for row_num, row in enumerate(data_rows, start=2):
        # Pad short rows
        while len(row) <= idx_fb:
            row.append("")

        raw_fb = row[idx_fb]
        signal = parse_feedback_signal(raw_fb)
        if signal is None:
            continue

        title  = row[idx_title]  if idx_title  < len(row) else ""
        source = row[idx_source] if idx_source < len(row) else ""
        url    = row[idx_url]    if idx_url    < len(row) else ""
        tags   = row[idx_tags]   if idx_tags   < len(row) else ""

        label = "👍" if signal else "👎"
        print(f"  Row {row_num}: {label} — {title[:60]}")

        uid = url or title  # use URL as ID, fall back to title

        if not dry_run:
            record_feedback(uid=uid, positive=signal, title=title, source=source)

        keywords = extract_keywords(title, tags)
        new_kw = update_prefs(prefs, keywords, positive=signal)
        new_kw_total += new_kw
        if new_kw:
            print(f"    + {new_kw} keyword(s) → {'boost' if signal else 'penalty'}")

        processed += 1

    print(f"\nProcessed {processed} feedback row(s), {new_kw_total} new keyword(s).")
    save_prefs(prefs, dry_run)
    return processed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Sync feed feedback from Google Sheet → feed_engine + preferences.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Feedback values recognised in column K:
  Positive: 👍  like  yes  good  1  +1
  Negative: 👎  dislike  no  bad  -1

Examples:
  python3 feedback_sync.py              # apply all pending feedback
  python3 feedback_sync.py --dry-run    # preview without writing
""",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview changes without writing to disk or calling record_feedback()",
    )
    args = parser.parse_args()

    if args.dry_run:
        print("[DRY RUN] No changes will be written.\n")

    try:
        n = sync_feedback(dry_run=args.dry_run)
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0 if n >= 0 else 1)


if __name__ == "__main__":
    main()
