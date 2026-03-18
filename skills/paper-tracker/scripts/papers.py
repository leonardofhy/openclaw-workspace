#!/usr/bin/env python3
"""Research paper tracker CLI.

Usage:
    papers.py add <arxiv_url_or_id>
    papers.py add --manual --title 'X' --authors 'Y' [--venue 'Z'] [--abstract 'A']
    papers.py list [--status S] [--tag T] [--limit N]
    papers.py show <id>
    papers.py tag <id> <tags...>
    papers.py status <id> <status>
    papers.py note <id> 'text'
    papers.py search <query>
    papers.py stats
    papers.py export [--format md|json]

Storage: memory/papers/papers.jsonl
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
# Workspace & store setup
# ---------------------------------------------------------------------------

def _find_workspace() -> Path:
    import subprocess
    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
        return Path(root)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.home() / ".openclaw" / "workspace"

WORKSPACE = _find_workspace()
STORE_REL = "memory/papers/papers.jsonl"
STORE_PATH = WORKSPACE / STORE_REL
PREFIX = "P"
TZ_TAIPEI = timezone(timedelta(hours=8))
VALID_STATUSES = {"queued", "reading", "read", "archived"}

# Try importing shared JsonlStore; fall back to inline implementation
try:
    sys.path.insert(0, str(WORKSPACE / "skills"))
    from shared.jsonl_store import JsonlStore
    store = JsonlStore(STORE_REL, prefix=PREFIX)
except ImportError:
    # Minimal inline implementation matching shared/jsonl_store.py
    import os
    import tempfile

    class JsonlStore:
        def __init__(self, rel_path: str, prefix: str = "ID"):
            self.path = WORKSPACE / rel_path
            self.prefix = prefix

        def load(self) -> list[dict]:
            if not self.path.exists():
                return []
            items = []
            for i, line in enumerate(self.path.read_text().strip().splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    print(f"⚠️ {self.path.name}:{i}: skipping malformed line", file=sys.stderr)
            return items

        def next_id(self, items: list[dict] | None = None) -> str:
            if items is None:
                items = self.load()
            if not items:
                return f"{self.prefix}-001"
            max_num = 0
            for item in items:
                try:
                    num = int(item["id"].split("-")[1])
                    max_num = max(max_num, num)
                except (KeyError, IndexError, ValueError):
                    pass
            return f"{self.prefix}-{max_num + 1:03d}"

        def append(self, item: dict) -> dict:
            items = self.load()
            if "id" not in item:
                item["id"] = self.next_id(items)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a") as f:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
            return item

        def update(self, item_id: str, updates: dict) -> dict | None:
            items = self.load()
            target = None
            for item in items:
                if item.get("id") == item_id:
                    item.update(updates)
                    target = item
                    break
            if target is None:
                return None
            self._atomic_rewrite(items)
            return target

        def find(self, item_id: str) -> dict | None:
            for item in self.load():
                if item.get("id") == item_id:
                    return item
            return None

        def _atomic_rewrite(self, items: list[dict]):
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(
                dir=self.path.parent, suffix=".tmp", prefix=self.path.stem,
            )
            try:
                with os.fdopen(fd, "w") as f:
                    for item in items:
                        f.write(json.dumps(item, ensure_ascii=False) + "\n")
                os.replace(tmp_path, self.path)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise

    store = JsonlStore(STORE_REL, prefix=PREFIX)


def now_taipei() -> str:
    return datetime.now(TZ_TAIPEI).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Arxiv API helpers
# ---------------------------------------------------------------------------

ARXIV_ID_RE = re.compile(r"(?:https?://)?(?:arxiv\.org/(?:abs|pdf)/)?(\d{4}\.\d{4,5}(?:v\d+)?)")

def parse_arxiv_id(raw: str) -> str | None:
    """Extract arxiv ID from URL or bare ID."""
    m = ARXIV_ID_RE.search(raw)
    return m.group(1) if m else None


def fetch_arxiv_metadata(arxiv_id: str) -> dict:
    """Fetch paper metadata from the arxiv Atom API."""
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "openclaw-paper-tracker/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()
    root = ET.fromstring(data)
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

    entry = root.find("atom:entry", ns)
    if entry is None:
        raise ValueError(f"No entry found for arxiv ID: {arxiv_id}")

    # Check for error (arxiv returns an entry with id containing "Error" for bad IDs)
    entry_id = entry.findtext("atom:id", "", ns)
    if "Error" in entry_id or not entry.findtext("atom:title", "", ns).strip():
        raise ValueError(f"Invalid arxiv ID: {arxiv_id}")

    title = " ".join(entry.findtext("atom:title", "", ns).split())
    abstract = " ".join(entry.findtext("atom:summary", "", ns).split())
    authors = [a.findtext("atom:name", "", ns) for a in entry.findall("atom:author", ns)]
    published = entry.findtext("atom:published", "", ns)[:10]  # YYYY-MM-DD
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


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_add(args):
    """Add a paper (from arxiv or manually)."""
    if args.manual:
        if not args.title:
            print("Error: --title is required for manual add", file=sys.stderr)
            return 1
        paper = {
            "title": args.title,
            "authors": [a.strip() for a in (args.authors or "").split(",") if a.strip()],
            "abstract": args.abstract or "",
            "arxiv_id": "",
            "url": args.url or "",
            "pdf_url": "",
            "date": args.date or now_taipei()[:10],
            "categories": [],
            "venue": args.venue or "",
            "status": "queued",
            "tags": [],
            "notes": [],
            "added_at": now_taipei(),
            "updated_at": now_taipei(),
        }
    else:
        if not args.source:
            print("Error: provide an arxiv URL or ID", file=sys.stderr)
            return 1
        arxiv_id = parse_arxiv_id(args.source)
        if not arxiv_id:
            print(f"Error: cannot parse arxiv ID from '{args.source}'", file=sys.stderr)
            return 1

        # Check for duplicate
        for existing in store.load():
            if existing.get("arxiv_id") == arxiv_id:
                print(f"Paper already tracked as {existing['id']}: {existing['title']}")
                return 0

        try:
            meta = fetch_arxiv_metadata(arxiv_id)
        except (urllib.error.URLError, ValueError) as e:
            print(f"Error fetching arxiv metadata: {e}", file=sys.stderr)
            return 1

        paper = {
            **meta,
            "venue": "",
            "status": "queued",
            "tags": [],
            "notes": [],
            "added_at": now_taipei(),
            "updated_at": now_taipei(),
        }

    result = store.append(paper)
    print(f"Added {result['id']}: {result['title']}")
    return 0


def cmd_list(args):
    """List papers with optional filters."""
    items = store.load()

    if args.status:
        items = [p for p in items if p.get("status") == args.status]
    if args.tag:
        items = [p for p in items if args.tag in p.get("tags", [])]

    # Sort by added_at descending (newest first)
    items.sort(key=lambda p: p.get("added_at", ""), reverse=True)

    if args.limit:
        items = items[: args.limit]

    if not items:
        print("No papers found.")
        return 0

    for p in items:
        tags_str = f" [{', '.join(p.get('tags', []))}]" if p.get("tags") else ""
        status = p.get("status", "queued")
        print(f"  {p['id']}  [{status}]  {p['title'][:70]}{tags_str}")
    print(f"\n{len(items)} paper(s)")
    return 0


def cmd_show(args):
    """Show full details of a paper."""
    paper = store.find(args.id)
    if not paper:
        print(f"Paper {args.id} not found.", file=sys.stderr)
        return 1

    print(f"ID:         {paper['id']}")
    print(f"Title:      {paper['title']}")
    print(f"Authors:    {', '.join(paper.get('authors', []))}")
    print(f"Date:       {paper.get('date', 'N/A')}")
    print(f"Status:     {paper.get('status', 'queued')}")
    if paper.get("arxiv_id"):
        print(f"Arxiv:      {paper['arxiv_id']}")
    if paper.get("url"):
        print(f"URL:        {paper['url']}")
    if paper.get("venue"):
        print(f"Venue:      {paper['venue']}")
    if paper.get("categories"):
        print(f"Categories: {', '.join(paper['categories'])}")
    if paper.get("tags"):
        print(f"Tags:       {', '.join(paper['tags'])}")
    if paper.get("abstract"):
        print(f"\nAbstract:\n  {paper['abstract'][:500]}")
    if paper.get("notes"):
        print(f"\nNotes ({len(paper['notes'])}):")
        for n in paper["notes"]:
            ts = n.get("time", "")
            print(f"  [{ts}] {n['text']}")
    print(f"\nAdded:   {paper.get('added_at', 'N/A')}")
    print(f"Updated: {paper.get('updated_at', 'N/A')}")
    return 0


def cmd_tag(args):
    """Add tags to a paper."""
    paper = store.find(args.id)
    if not paper:
        print(f"Paper {args.id} not found.", file=sys.stderr)
        return 1
    existing_tags = set(paper.get("tags", []))
    new_tags = existing_tags | set(args.tags)
    store.update(args.id, {"tags": sorted(new_tags), "updated_at": now_taipei()})
    print(f"Tags for {args.id}: {', '.join(sorted(new_tags))}")
    return 0


def cmd_status(args):
    """Update paper reading status."""
    if args.new_status not in VALID_STATUSES:
        print(f"Error: status must be one of {VALID_STATUSES}", file=sys.stderr)
        return 1
    paper = store.find(args.id)
    if not paper:
        print(f"Paper {args.id} not found.", file=sys.stderr)
        return 1
    store.update(args.id, {"status": args.new_status, "updated_at": now_taipei()})
    print(f"{args.id} status → {args.new_status}")
    return 0


def cmd_note(args):
    """Add a reading note to a paper."""
    paper = store.find(args.id)
    if not paper:
        print(f"Paper {args.id} not found.", file=sys.stderr)
        return 1
    notes = paper.get("notes", [])
    notes.append({"text": args.text, "time": now_taipei()})
    store.update(args.id, {"notes": notes, "updated_at": now_taipei()})
    print(f"Note added to {args.id} ({len(notes)} total)")
    return 0


def cmd_search(args):
    """Fuzzy search across title, abstract, tags, and notes."""
    query = args.query.lower()
    items = store.load()
    results = []
    for p in items:
        searchable = " ".join([
            p.get("title", ""),
            p.get("abstract", ""),
            " ".join(p.get("tags", [])),
            " ".join(p.get("categories", [])),
            " ".join(n.get("text", "") for n in p.get("notes", [])),
            " ".join(p.get("authors", [])),
            p.get("venue", ""),
        ]).lower()
        # Simple substring + token matching (CJK-friendly)
        if query in searchable:
            results.append(p)
        else:
            # Token-level: all query tokens must appear
            tokens = query.split()
            if tokens and all(t in searchable for t in tokens):
                results.append(p)

    if not results:
        print("No papers match your query.")
        return 0

    for p in results:
        tags_str = f" [{', '.join(p.get('tags', []))}]" if p.get("tags") else ""
        print(f"  {p['id']}  [{p.get('status', 'queued')}]  {p['title'][:70]}{tags_str}")
    print(f"\n{len(results)} result(s)")
    return 0


def cmd_stats(args):
    """Summary statistics."""
    items = store.load()
    if not items:
        print("No papers tracked yet.")
        return 0

    # By status
    status_counts: dict[str, int] = {}
    for p in items:
        s = p.get("status", "queued")
        status_counts[s] = status_counts.get(s, 0) + 1

    # By tag
    tag_counts: dict[str, int] = {}
    for p in items:
        for t in p.get("tags", []):
            tag_counts[t] = tag_counts.get(t, 0) + 1

    # Recent activity (last 7 days)
    week_ago = (datetime.now(TZ_TAIPEI) - timedelta(days=7)).isoformat()
    recent = [p for p in items if p.get("added_at", "") >= week_ago]

    print(f"Total papers: {len(items)}")
    print(f"\nBy status:")
    for s in ["queued", "reading", "read", "archived"]:
        if s in status_counts:
            print(f"  {s}: {status_counts[s]}")

    if tag_counts:
        print(f"\nTop tags:")
        for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"  {tag}: {count}")

    print(f"\nAdded this week: {len(recent)}")
    total_notes = sum(len(p.get("notes", [])) for p in items)
    print(f"Total notes: {total_notes}")
    return 0


def cmd_export(args):
    """Export papers."""
    items = store.load()
    fmt = args.format or "md"

    if fmt == "json":
        print(json.dumps(items, indent=2, ensure_ascii=False))
    elif fmt == "md":
        if not items:
            print("No papers to export.")
            return 0
        print("# Paper Reading List\n")
        by_status: dict[str, list] = {}
        for p in items:
            s = p.get("status", "queued")
            by_status.setdefault(s, []).append(p)
        for status in ["reading", "queued", "read", "archived"]:
            papers = by_status.get(status, [])
            if not papers:
                continue
            print(f"## {status.title()} ({len(papers)})\n")
            for p in papers:
                authors = ", ".join(p.get("authors", [])[:3])
                if len(p.get("authors", [])) > 3:
                    authors += " et al."
                url_part = f" — [{p['arxiv_id']}]({p['url']})" if p.get("arxiv_id") else ""
                tags_part = f"  Tags: {', '.join(p['tags'])}" if p.get("tags") else ""
                print(f"- **{p['title']}** ({authors}){url_part}")
                if tags_part:
                    print(f"  {tags_part}")
                if p.get("notes"):
                    for n in p["notes"]:
                        print(f"  - {n['text']}")
            print()
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="papers.py",
        description="Research paper tracker",
    )
    sub = parser.add_subparsers(dest="command")

    # add
    p_add = sub.add_parser("add", help="Add a paper")
    p_add.add_argument("source", nargs="?", help="Arxiv URL or ID")
    p_add.add_argument("--manual", action="store_true", help="Manual entry (non-arxiv)")
    p_add.add_argument("--title", help="Paper title")
    p_add.add_argument("--authors", help="Comma-separated authors")
    p_add.add_argument("--venue", help="Publication venue")
    p_add.add_argument("--abstract", help="Paper abstract")
    p_add.add_argument("--url", help="Paper URL")
    p_add.add_argument("--date", help="Publication date (YYYY-MM-DD)")

    # list
    p_list = sub.add_parser("list", help="List papers")
    p_list.add_argument("--status", choices=list(VALID_STATUSES))
    p_list.add_argument("--tag")
    p_list.add_argument("--limit", type=int)

    # show
    p_show = sub.add_parser("show", help="Show paper details")
    p_show.add_argument("id", help="Paper ID (e.g., P-001)")

    # tag
    p_tag = sub.add_parser("tag", help="Add tags to a paper")
    p_tag.add_argument("id", help="Paper ID")
    p_tag.add_argument("tags", nargs="+", help="Tags to add")

    # status
    p_status = sub.add_parser("status", help="Update paper status")
    p_status.add_argument("id", help="Paper ID")
    p_status.add_argument("new_status", help="New status")

    # note
    p_note = sub.add_parser("note", help="Add a reading note")
    p_note.add_argument("id", help="Paper ID")
    p_note.add_argument("text", help="Note text")

    # search
    p_search = sub.add_parser("search", help="Search papers")
    p_search.add_argument("query", help="Search query")

    # stats
    sub.add_parser("stats", help="Show statistics")

    # export
    p_export = sub.add_parser("export", help="Export papers")
    p_export.add_argument("--format", choices=["md", "json"], default="md")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    dispatch = {
        "add": cmd_add,
        "list": cmd_list,
        "show": cmd_show,
        "tag": cmd_tag,
        "status": cmd_status,
        "note": cmd_note,
        "search": cmd_search,
        "stats": cmd_stats,
        "export": cmd_export,
    }
    return dispatch[args.command](args) or 0


if __name__ == "__main__":
    sys.exit(main())
