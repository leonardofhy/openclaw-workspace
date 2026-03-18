#!/usr/bin/env python3
"""Import arxiv papers from feed recommendations into the paper tracker.

Sources:
  --from-json PATH   Read from a feed JSON file (default: /tmp/feed_articles.json)
  --from-sheet       Read from the Google Sheet used by feed-recommend

Deduplicates by arxiv ID against existing papers.jsonl entries.

Usage:
    python3 import_from_feed.py                              # from /tmp/feed_articles.json
    python3 import_from_feed.py --from-json /path/to/file   # custom JSON path
    python3 import_from_feed.py --from-sheet                 # from Google Sheet
    python3 import_from_feed.py --dry-run                    # preview without writing
    python3 import_from_feed.py --help
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent.parent

STORE_PATH = ROOT_DIR / "memory" / "papers" / "papers.jsonl"
FEED_CONFIG_PATH = ROOT_DIR / "skills" / "feed-recommend" / "scripts" / "config.json"
CREDS_PATH = ROOT_DIR / "secrets" / "google-service-account.json"
DEFAULT_JSON = Path("/tmp/feed_articles.json")

TZ = timezone(timedelta(hours=8))

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

ARXIV_ID_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5}(?:v\d+)?)", re.I)

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    gspread = None  # type: ignore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now_taipei() -> str:
    return datetime.now(TZ).isoformat()


def parse_arxiv_id(url: str) -> str | None:
    m = ARXIV_ID_RE.search(url)
    return m.group(1).split("v")[0] if m else None  # strip version suffix


def load_existing_ids() -> set[str]:
    """Return set of arxiv IDs already in papers.jsonl."""
    if not STORE_PATH.exists():
        return set()
    ids = set()
    for line in STORE_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            p = json.loads(line)
            aid = p.get("arxiv_id", "")
            if aid:
                ids.add(aid.split("v")[0])
        except json.JSONDecodeError:
            continue
    return ids


def _base_count() -> int:
    if not STORE_PATH.exists():
        return 0
    return sum(1 for line in STORE_PATH.read_text().splitlines() if line.strip())


_id_counter = [None]  # lazy singleton: [base_count]


def next_paper_id() -> str:
    """Generate next P-series ID (P001, P002, …), incrementing in memory."""
    if _id_counter[0] is None:
        _id_counter[0] = _base_count()
    _id_counter[0] += 1
    return f"P{_id_counter[0]:03d}"


def append_paper(paper: dict, dry_run: bool) -> str:
    """Append a paper dict to papers.jsonl. Returns the assigned ID."""
    pid = next_paper_id()
    paper["id"] = pid
    if dry_run:
        print(f"  [dry-run] would append {pid}: {paper['title'][:60]}")
        return pid
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "a") as f:
        f.write(json.dumps(paper, ensure_ascii=False) + "\n")
    return pid


# ---------------------------------------------------------------------------
# arxiv metadata fetch
# ---------------------------------------------------------------------------

def fetch_arxiv_metadata(arxiv_id: str) -> dict:
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "openclaw-paper-tracker/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()
    root = ET.fromstring(data)
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    entry = root.find("atom:entry", ns)
    if entry is None:
        raise ValueError(f"No entry for arxiv ID: {arxiv_id}")
    entry_id_text = entry.findtext("atom:id", "", ns)
    if "Error" in entry_id_text:
        raise ValueError(f"Invalid arxiv ID: {arxiv_id}")

    title = " ".join(entry.findtext("atom:title", "", ns).split())
    abstract = " ".join(entry.findtext("atom:summary", "", ns).split())
    authors = [a.findtext("atom:name", "", ns) for a in entry.findall("atom:author", ns)]
    published = entry.findtext("atom:published", "", ns)[:10]
    categories = [c.get("term", "") for c in entry.findall("atom:category", ns) if c.get("term")]
    pdf_link = ""
    for link in entry.findall("atom:link", ns):
        if link.get("title") == "pdf":
            pdf_link = link.get("href", "")
            break

    return {
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "arxiv_id": arxiv_id,
        "url": f"https://arxiv.org/abs/{arxiv_id}",
        "pdf_url": pdf_link,
        "date": published,
        "categories": categories,
    }


def build_paper_stub(article: dict) -> dict | None:
    """
    Build a paper record from a feed article dict without hitting the arxiv API.
    Returns None if the article has no arxiv URL.
    """
    url = article.get("url", "") or article.get("URL", "")
    arxiv_id = parse_arxiv_id(url)
    if not arxiv_id:
        return None

    title = article.get("title", "") or article.get("Title", "")
    tags_raw = article.get("tags", article.get("Tags", ""))
    if isinstance(tags_raw, str):
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
    else:
        tags = list(tags_raw) if tags_raw else []

    return {
        "title": title,
        "authors": [],
        "abstract": article.get("snippet", article.get("summary", "")),
        "arxiv_id": arxiv_id,
        "url": f"https://arxiv.org/abs/{arxiv_id}",
        "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}",
        "date": (article.get("date", "") or "")[:10] or now_taipei()[:10],
        "categories": [],
        "venue": "",
        "status": "queued",
        "tags": tags,
        "notes": [],
        "added_at": now_taipei(),
        "updated_at": now_taipei(),
    }


# ---------------------------------------------------------------------------
# Source: JSON file
# ---------------------------------------------------------------------------

def articles_from_json(path: Path) -> list[dict]:
    if not path.exists():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    data = json.loads(path.read_text())
    # Support both {"recommended": [...]} and flat list formats
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("recommended", "articles", "items"):
            if key in data and isinstance(data[key], list):
                return data[key]
        # Flat dict of URL → article
        return list(data.values()) if data else []
    return []


# ---------------------------------------------------------------------------
# Source: Google Sheet
# ---------------------------------------------------------------------------

def articles_from_sheet() -> list[dict]:
    if gspread is None:
        print("ERROR: gspread not installed", file=sys.stderr)
        sys.exit(1)
    if not FEED_CONFIG_PATH.exists():
        print(f"ERROR: feed config not found at {FEED_CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    cfg = json.loads(FEED_CONFIG_PATH.read_text())
    sid = cfg.get("google_sheets", {}).get("sheet_id", "")
    if not sid:
        print("ERROR: no sheet_id in feed config", file=sys.stderr)
        sys.exit(1)
    if not CREDS_PATH.exists():
        print(f"ERROR: credentials not found at {CREDS_PATH}", file=sys.stderr)
        sys.exit(1)

    creds = Credentials.from_service_account_file(str(CREDS_PATH), scopes=SCOPES)
    gc = gspread.authorize(creds)
    ws = gc.open_by_key(sid).sheet1
    all_rows = ws.get_all_values()
    if not all_rows:
        return []

    header = all_rows[0]

    def col(name: str, default: int) -> int:
        try:
            return header.index(name)
        except ValueError:
            return default

    idx_title  = col("Title", 2)
    idx_source = col("Source", 1)
    idx_url    = col("URL", 5)
    idx_tags   = col("Tags", 6)
    idx_score  = col("Score", 4)

    articles = []
    for row in all_rows[1:]:
        def get(idx):
            return row[idx] if idx < len(row) else ""
        url = get(idx_url)
        if not url:
            continue
        articles.append({
            "url": url,
            "title": get(idx_title),
            "source": get(idx_source),
            "tags": get(idx_tags),
            "score": get(idx_score),
        })
    return articles


# ---------------------------------------------------------------------------
# Main import logic
# ---------------------------------------------------------------------------

def import_articles(articles: list[dict], dry_run: bool, fetch_meta: bool) -> tuple[int, int]:
    """
    Returns (added, skipped).
    """
    existing_ids = load_existing_ids()
    added = skipped = 0

    for article in articles:
        paper = build_paper_stub(article)
        if paper is None:
            continue  # not an arxiv article

        aid = paper["arxiv_id"]
        if aid in existing_ids:
            print(f"  skip (dup) {aid}: {paper['title'][:50]}")
            skipped += 1
            continue

        # Optionally enrich with full arxiv metadata
        if fetch_meta:
            try:
                meta = fetch_arxiv_metadata(aid)
                paper.update({
                    "title":      meta["title"] or paper["title"],
                    "authors":    meta["authors"],
                    "abstract":   meta["abstract"],
                    "date":       meta["date"],
                    "categories": meta["categories"],
                    "pdf_url":    meta["pdf_url"],
                })
            except (urllib.error.URLError, ValueError, Exception) as e:
                print(f"  ⚠ metadata fetch failed for {aid}: {e} — using feed data")

        pid = append_paper(paper, dry_run)
        print(f"  {'[dry-run] ' if dry_run else ''}added {pid}: {paper['title'][:60]}")
        existing_ids.add(aid)
        added += 1

    return added, skipped


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Import arxiv papers from feed recommendations into paper tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 import_from_feed.py                                  # default JSON source
  python3 import_from_feed.py --from-json /tmp/feed.json
  python3 import_from_feed.py --from-sheet
  python3 import_from_feed.py --from-sheet --dry-run
  python3 import_from_feed.py --fetch-meta                     # enrich via arxiv API
""",
    )

    src = parser.add_mutually_exclusive_group()
    src.add_argument(
        "--from-json", metavar="PATH",
        nargs="?", const=str(DEFAULT_JSON),
        help=f"Read articles from a JSON file (default: {DEFAULT_JSON})",
    )
    src.add_argument(
        "--from-sheet", action="store_true",
        help="Read articles from the Google Sheet",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview without writing to papers.jsonl",
    )
    parser.add_argument(
        "--fetch-meta", action="store_true",
        help="Fetch full metadata from arxiv API for each paper",
    )

    args = parser.parse_args()

    if args.dry_run:
        print("[DRY RUN] No changes will be written.\n")

    # Determine source
    if args.from_sheet:
        print("Fetching articles from Google Sheet…", flush=True)
        articles = articles_from_sheet()
    else:
        path = Path(args.from_json) if args.from_json else DEFAULT_JSON
        print(f"Reading articles from {path}…", flush=True)
        articles = articles_from_json(path)

    print(f"Found {len(articles)} article(s). Filtering for arxiv…\n")

    try:
        added, skipped = import_articles(articles, dry_run=args.dry_run, fetch_meta=args.fetch_meta)
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\nDone. Added: {added}, Skipped (dup): {skipped}.")
    if args.dry_run:
        print("[DRY RUN] No files were modified.")


if __name__ == "__main__":
    main()
