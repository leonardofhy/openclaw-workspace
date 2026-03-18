#!/usr/bin/env python3
"""Reading list management for paper tracker.

Manages a prioritized reading queue stored in memory/papers/reading-queue.json.
Integrates with the autodidact queue and paper tracker.

Usage:
    reading_list.py add <arxiv_id_or_url> [--priority high|medium|low] [--note 'text']
    reading_list.py add --from-tracker <paper_id>  # add from papers.jsonl
    reading_list.py list [--status queued|reading|done|skipped] [--limit N]
    reading_list.py show <id>
    reading_list.py done <id> [--note 'reading note']
    reading_list.py skip <id> [--reason 'why skipped']
    reading_list.py priority <id> <high|medium|low>
    reading_list.py note <id> 'note text'
    reading_list.py stats
    reading_list.py export [--format md|json]

Storage:
    memory/papers/reading-queue.json    # reading queue
    memory/papers/papers.jsonl          # paper tracker integration
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
# Workspace setup
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
READING_QUEUE_PATH = WORKSPACE / "memory" / "papers" / "reading-queue.json"
PAPERS_JSONL_PATH = WORKSPACE / "memory" / "papers" / "papers.jsonl"

TZ = timezone(timedelta(hours=8))
VALID_PRIORITIES = {"high", "medium", "low"}
VALID_STATUSES = {"queued", "reading", "done", "skipped"}

# arXiv ID regex
ARXIV_ID_RE = re.compile(r"(?:https?://)?(?:arxiv\.org/(?:abs|pdf)/)?(\d{4}\.\d{4,5}(?:v\d+)?)")

def now_taipei() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")

# ---------------------------------------------------------------------------
# Reading queue management
# ---------------------------------------------------------------------------

def load_reading_queue() -> list[dict]:
    """Load the reading queue from JSON file."""
    if not READING_QUEUE_PATH.exists():
        return []
    try:
        return json.loads(READING_QUEUE_PATH.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_reading_queue(queue: list[dict]) -> None:
    """Save the reading queue to JSON file."""
    READING_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(READING_QUEUE_PATH, "w") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)

def next_queue_id(queue: list[dict]) -> str:
    """Generate next reading queue ID (R-001, R-002, ...)."""
    if not queue:
        return "R-001"

    max_num = 0
    for item in queue:
        try:
            num = int(item["id"].split("-")[1])
            max_num = max(max_num, num)
        except (KeyError, IndexError, ValueError):
            pass
    return f"R-{max_num + 1:03d}"

def find_queue_item(queue: list[dict], item_id: str) -> dict | None:
    """Find an item in the queue by ID."""
    for item in queue:
        if item.get("id") == item_id:
            return item
    return None

def update_queue_item(queue: list[dict], item_id: str, updates: dict) -> dict | None:
    """Update an item in the queue."""
    for item in queue:
        if item.get("id") == item_id:
            item.update(updates)
            item["updated_at"] = now_taipei()
            return item
    return None

# ---------------------------------------------------------------------------
# Paper tracker integration
# ---------------------------------------------------------------------------

def load_tracked_papers() -> list[dict]:
    """Load papers from papers.jsonl."""
    if not PAPERS_JSONL_PATH.exists():
        return []
    papers = []
    for line in PAPERS_JSONL_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            papers.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return papers

def find_tracked_paper(paper_id: str) -> dict | None:
    """Find a paper in the tracker by ID."""
    papers = load_tracked_papers()
    for paper in papers:
        if paper.get("id") == paper_id:
            return paper
    return None

# ---------------------------------------------------------------------------
# arXiv API helpers
# ---------------------------------------------------------------------------

def parse_arxiv_id(raw: str) -> str | None:
    """Extract arXiv ID from URL or bare ID."""
    m = ARXIV_ID_RE.search(raw)
    return m.group(1) if m else None

def fetch_arxiv_metadata(arxiv_id: str) -> dict:
    """Fetch paper metadata from the arXiv Atom API."""
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "openclaw-reading-list/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()

    root = ET.fromstring(data)
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

    entry = root.find("atom:entry", ns)
    if entry is None:
        raise ValueError(f"No entry found for arXiv ID: {arxiv_id}")

    # Check for error
    entry_id = entry.findtext("atom:id", "", ns)
    if "Error" in entry_id or not entry.findtext("atom:title", "", ns).strip():
        raise ValueError(f"Invalid arXiv ID: {arxiv_id}")

    title = " ".join(entry.findtext("atom:title", "", ns).split())
    abstract = " ".join(entry.findtext("atom:summary", "", ns).split())
    authors = [a.findtext("atom:name", "", ns) for a in entry.findall("atom:author", ns)]
    published = entry.findtext("atom:published", "", ns)[:10]  # YYYY-MM-DD
    categories = [c.get("term", "") for c in entry.findall("atom:category", ns) if c.get("term")]

    return {
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "arxiv_id": arxiv_id,
        "url": f"https://arxiv.org/abs/{arxiv_id}",
        "date": published,
        "categories": categories,
    }

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_add(args):
    """Add a paper to the reading queue."""
    queue = load_reading_queue()

    if args.from_tracker:
        # Add from paper tracker
        paper = find_tracked_paper(args.from_tracker)
        if not paper:
            print(f"Error: Paper {args.from_tracker} not found in tracker", file=sys.stderr)
            return 1

        # Check if already in queue
        for item in queue:
            if item.get("paper_id") == args.from_tracker:
                print(f"Paper {args.from_tracker} already in reading queue as {item['id']}")
                return 0

        queue_item = {
            "id": next_queue_id(queue),
            "paper_id": args.from_tracker,
            "title": paper.get("title", ""),
            "authors": paper.get("authors", []),
            "arxiv_id": paper.get("arxiv_id", ""),
            "url": paper.get("url", ""),
            "priority": args.priority or "medium",
            "status": "queued",
            "notes": [],
            "added_at": now_taipei(),
            "updated_at": now_taipei(),
        }

        if args.note:
            queue_item["notes"].append({
                "text": args.note,
                "time": now_taipei(),
                "type": "add"
            })

    else:
        # Add by arXiv URL/ID
        if not args.source:
            print("Error: provide an arXiv URL/ID or use --from-tracker", file=sys.stderr)
            return 1

        arxiv_id = parse_arxiv_id(args.source)
        if not arxiv_id:
            print(f"Error: cannot parse arXiv ID from '{args.source}'", file=sys.stderr)
            return 1

        # Check if already in queue
        for item in queue:
            if item.get("arxiv_id") == arxiv_id:
                print(f"Paper {arxiv_id} already in reading queue as {item['id']}")
                return 0

        try:
            meta = fetch_arxiv_metadata(arxiv_id)
        except (urllib.error.URLError, ValueError) as e:
            print(f"Error fetching arXiv metadata: {e}", file=sys.stderr)
            return 1

        queue_item = {
            "id": next_queue_id(queue),
            "paper_id": "",  # no tracker integration
            "title": meta["title"],
            "authors": meta["authors"],
            "arxiv_id": arxiv_id,
            "url": meta["url"],
            "priority": args.priority or "medium",
            "status": "queued",
            "notes": [],
            "added_at": now_taipei(),
            "updated_at": now_taipei(),
        }

        if args.note:
            queue_item["notes"].append({
                "text": args.note,
                "time": now_taipei(),
                "type": "add"
            })

    queue.append(queue_item)
    save_reading_queue(queue)

    priority_icon = {"high": "🔥", "medium": "📚", "low": "📝"}.get(queue_item["priority"], "📚")
    print(f"Added {queue_item['id']} {priority_icon} {queue_item['title']}")
    return 0

def cmd_list(args):
    """List papers in the reading queue."""
    queue = load_reading_queue()

    if args.status:
        queue = [item for item in queue if item.get("status") == args.status]

    # Sort by priority (high -> medium -> low) then by added_at
    priority_order = {"high": 0, "medium": 1, "low": 2}
    queue.sort(key=lambda x: (priority_order.get(x.get("priority", "medium"), 1), x.get("added_at", "")))

    if args.limit:
        queue = queue[:args.limit]

    if not queue:
        print("No papers found in reading queue.")
        return 0

    print(f"Reading queue ({len(queue)} papers):")
    print()

    for item in queue:
        priority_icon = {"high": "🔥", "medium": "📚", "low": "📝"}.get(item.get("priority", "medium"), "📚")
        status_icon = {"queued": "⏳", "reading": "📖", "done": "✅", "skipped": "⏭️"}.get(item.get("status", "queued"), "⏳")

        authors = ", ".join(item.get("authors", [])[:2])
        if len(item.get("authors", [])) > 2:
            authors += " et al."

        print(f"  {item['id']}  {status_icon} {priority_icon}  {item.get('title', '')[:60]}")
        if authors:
            print(f"         {authors}")
        if item.get("notes"):
            latest_note = item["notes"][-1]
            print(f"         💭 {latest_note['text'][:50]}")
        print()

    return 0

def cmd_show(args):
    """Show detailed information about a queue item."""
    queue = load_reading_queue()
    item = find_queue_item(queue, args.id)

    if not item:
        print(f"Item {args.id} not found in reading queue.", file=sys.stderr)
        return 1

    priority_icon = {"high": "🔥", "medium": "📚", "low": "📝"}.get(item.get("priority", "medium"), "📚")
    status_icon = {"queued": "⏳", "reading": "📖", "done": "✅", "skipped": "⏭️"}.get(item.get("status", "queued"), "⏳")

    print(f"ID:       {item['id']}")
    print(f"Title:    {item.get('title', '')}")
    print(f"Authors:  {', '.join(item.get('authors', []))}")
    print(f"Status:   {status_icon} {item.get('status', 'queued')}")
    print(f"Priority: {priority_icon} {item.get('priority', 'medium')}")

    if item.get("arxiv_id"):
        print(f"arXiv:    {item['arxiv_id']}")
    if item.get("url"):
        print(f"URL:      {item['url']}")
    if item.get("paper_id"):
        print(f"Tracker:  {item['paper_id']}")

    print(f"Added:    {item.get('added_at', '')}")
    print(f"Updated:  {item.get('updated_at', '')}")

    if item.get("notes"):
        print(f"\nNotes ({len(item['notes'])}):")
        for note in item["notes"]:
            note_type = f" ({note['type']})" if note.get('type') else ""
            print(f"  [{note.get('time', '')}]{note_type} {note['text']}")

    return 0

def cmd_done(args):
    """Mark a paper as done reading."""
    queue = load_reading_queue()
    item = update_queue_item(queue, args.id, {"status": "done"})

    if not item:
        print(f"Item {args.id} not found in reading queue.", file=sys.stderr)
        return 1

    if args.note:
        item.setdefault("notes", []).append({
            "text": args.note,
            "time": now_taipei(),
            "type": "done"
        })

    save_reading_queue(queue)
    print(f"✅ Marked {args.id} as done: {item.get('title', '')[:60]}")
    return 0

def cmd_skip(args):
    """Mark a paper as skipped."""
    queue = load_reading_queue()
    item = update_queue_item(queue, args.id, {"status": "skipped"})

    if not item:
        print(f"Item {args.id} not found in reading queue.", file=sys.stderr)
        return 1

    if args.reason:
        item.setdefault("notes", []).append({
            "text": f"Skipped: {args.reason}",
            "time": now_taipei(),
            "type": "skip"
        })

    save_reading_queue(queue)
    print(f"⏭️ Marked {args.id} as skipped: {item.get('title', '')[:60]}")
    return 0

def cmd_priority(args):
    """Update paper priority."""
    queue = load_reading_queue()
    item = update_queue_item(queue, args.id, {"priority": args.new_priority})

    if not item:
        print(f"Item {args.id} not found in reading queue.", file=sys.stderr)
        return 1

    save_reading_queue(queue)
    priority_icon = {"high": "🔥", "medium": "📚", "low": "📝"}.get(args.new_priority, "📚")
    print(f"{priority_icon} Set {args.id} priority to {args.new_priority}")
    return 0

def cmd_note(args):
    """Add a note to a queue item."""
    queue = load_reading_queue()
    item = find_queue_item(queue, args.id)

    if not item:
        print(f"Item {args.id} not found in reading queue.", file=sys.stderr)
        return 1

    item.setdefault("notes", []).append({
        "text": args.text,
        "time": now_taipei(),
        "type": "note"
    })
    item["updated_at"] = now_taipei()

    save_reading_queue(queue)
    print(f"💭 Added note to {args.id}")
    return 0

def cmd_stats(args):
    """Show reading queue statistics."""
    queue = load_reading_queue()

    if not queue:
        print("Reading queue is empty.")
        return 0

    # Count by status
    status_counts = {}
    for item in queue:
        status = item.get("status", "queued")
        status_counts[status] = status_counts.get(status, 0) + 1

    # Count by priority
    priority_counts = {}
    for item in queue:
        priority = item.get("priority", "medium")
        priority_counts[priority] = priority_counts.get(priority, 0) + 1

    # Recent activity
    week_ago = (datetime.now(TZ) - timedelta(days=7)).isoformat()
    recent = [item for item in queue if item.get("added_at", "") >= week_ago]

    print(f"Reading queue statistics:")
    print(f"  Total items: {len(queue)}")
    print()

    print("By status:")
    for status in ["queued", "reading", "done", "skipped"]:
        count = status_counts.get(status, 0)
        icon = {"queued": "⏳", "reading": "📖", "done": "✅", "skipped": "⏭️"}.get(status, "")
        if count > 0:
            print(f"  {icon} {status}: {count}")
    print()

    print("By priority:")
    for priority in ["high", "medium", "low"]:
        count = priority_counts.get(priority, 0)
        icon = {"high": "🔥", "medium": "📚", "low": "📝"}.get(priority, "")
        if count > 0:
            print(f"  {icon} {priority}: {count}")
    print()

    print(f"Added this week: {len(recent)}")

    # Progress
    done_count = status_counts.get("done", 0)
    total_actionable = len(queue) - status_counts.get("skipped", 0)
    if total_actionable > 0:
        progress = (done_count / total_actionable) * 100
        print(f"Progress: {done_count}/{total_actionable} ({progress:.1f}%)")

    return 0

def cmd_export(args):
    """Export the reading queue."""
    queue = load_reading_queue()
    fmt = args.format or "md"

    if fmt == "json":
        print(json.dumps(queue, indent=2, ensure_ascii=False))
    elif fmt == "md":
        if not queue:
            print("# Reading Queue\n\n*Empty*")
            return 0

        print("# Reading Queue\n")

        # Group by status
        by_status = {}
        for item in queue:
            status = item.get("status", "queued")
            by_status.setdefault(status, []).append(item)

        # Sort by priority within each status
        priority_order = {"high": 0, "medium": 1, "low": 2}
        for status in ["reading", "queued", "done", "skipped"]:
            items = by_status.get(status, [])
            if not items:
                continue

            items.sort(key=lambda x: priority_order.get(x.get("priority", "medium"), 1))

            status_icon = {"queued": "⏳", "reading": "📖", "done": "✅", "skipped": "⏭️"}.get(status, "")
            print(f"## {status_icon} {status.title()} ({len(items)})\n")

            for item in items:
                priority_icon = {"high": "🔥", "medium": "📚", "low": "📝"}.get(item.get("priority", "medium"), "📚")
                authors = ", ".join(item.get("authors", [])[:3])
                if len(item.get("authors", [])) > 3:
                    authors += " et al."

                url_part = ""
                if item.get("arxiv_id"):
                    url_part = f" — [arXiv:{item['arxiv_id']}]({item.get('url', '')})"
                elif item.get("url"):
                    url_part = f" — [Link]({item['url']})"

                print(f"- {priority_icon} **{item.get('title', '')}** ({authors}){url_part}")

                if item.get("notes"):
                    for note in item["notes"][-2:]:  # Show last 2 notes
                        print(f"  - 💭 {note['text']}")
                print()

    return 0

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reading_list.py",
        description="Manage prioritized reading queue for papers",
    )
    sub = parser.add_subparsers(dest="command")

    # add
    p_add = sub.add_parser("add", help="Add a paper to the reading queue")
    p_add.add_argument("source", nargs="?", help="arXiv URL or ID")
    p_add.add_argument("--from-tracker", help="Add paper from tracker by ID")
    p_add.add_argument("--priority", choices=list(VALID_PRIORITIES), default="medium")
    p_add.add_argument("--note", help="Initial note")

    # list
    p_list = sub.add_parser("list", help="List papers in reading queue")
    p_list.add_argument("--status", choices=list(VALID_STATUSES))
    p_list.add_argument("--limit", type=int)

    # show
    p_show = sub.add_parser("show", help="Show queue item details")
    p_show.add_argument("id", help="Queue item ID (e.g., R-001)")

    # done
    p_done = sub.add_parser("done", help="Mark paper as done reading")
    p_done.add_argument("id", help="Queue item ID")
    p_done.add_argument("--note", help="Reading completion note")

    # skip
    p_skip = sub.add_parser("skip", help="Mark paper as skipped")
    p_skip.add_argument("id", help="Queue item ID")
    p_skip.add_argument("--reason", help="Reason for skipping")

    # priority
    p_priority = sub.add_parser("priority", help="Update paper priority")
    p_priority.add_argument("id", help="Queue item ID")
    p_priority.add_argument("new_priority", choices=list(VALID_PRIORITIES))

    # note
    p_note = sub.add_parser("note", help="Add a note to queue item")
    p_note.add_argument("id", help="Queue item ID")
    p_note.add_argument("text", help="Note text")

    # stats
    sub.add_parser("stats", help="Show reading queue statistics")

    # export
    p_export = sub.add_parser("export", help="Export reading queue")
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
        "done": cmd_done,
        "skip": cmd_skip,
        "priority": cmd_priority,
        "note": cmd_note,
        "stats": cmd_stats,
        "export": cmd_export,
    }
    return dispatch[args.command](args) or 0

if __name__ == "__main__":
    sys.exit(main())