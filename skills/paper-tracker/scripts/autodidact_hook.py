#!/usr/bin/env python3
"""Autodidact hook for paper tracker integration.

Provides a function and CLI to log papers read during autodidact cycles
into the paper tracker's JSONL store.

Usage as library:
    from autodidact_hook import log_paper_read
    log_paper_read("2301.07041", title="Attention Is All You Need",
                   tags=["lm", "attention"], note="foundational transformer paper")

Usage as CLI:
    python3 autodidact_hook.py --arxiv 2301.07041 --title 'Attention' \\
        --tags speech,interp --note 'key finding' [--status read]
"""

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from papers import store, now_taipei, VALID_STATUSES


def log_paper_read(
    arxiv_id: str,
    title: str,
    tags: list[str] | None = None,
    note: str | None = None,
    status: str = "read",
    cycle: str | None = None,
) -> dict:
    """Add or update a paper in the tracker from an autodidact cycle.

    Returns the paper record (existing or newly created).
    """
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{status}', must be one of {VALID_STATUSES}")

    # Check if paper already exists by arxiv_id
    existing = store.load()
    for paper in existing:
        if paper.get("arxiv_id") == arxiv_id and arxiv_id:
            # Update existing paper
            updates: dict = {"updated_at": now_taipei()}
            if status:
                updates["status"] = status
            if tags:
                merged_tags = sorted(set(paper.get("tags", [])) | set(tags))
                updates["tags"] = merged_tags
            if note:
                notes = paper.get("notes", [])
                notes.append({"text": note, "time": now_taipei()})
                updates["notes"] = notes
            if cycle:
                notes = updates.get("notes", paper.get("notes", []))
                notes.append({"text": f"Autodidact cycle #{cycle}", "time": now_taipei()})
                updates["notes"] = notes
            result = store.update(paper["id"], updates)
            return result

    # Create new paper
    paper = {
        "title": title,
        "authors": [],
        "abstract": "",
        "arxiv_id": arxiv_id,
        "url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "",
        "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else "",
        "date": "",
        "categories": [],
        "venue": "",
        "status": status,
        "tags": sorted(tags) if tags else [],
        "notes": [],
        "added_at": now_taipei(),
        "updated_at": now_taipei(),
    }
    if note:
        paper["notes"].append({"text": note, "time": now_taipei()})
    if cycle:
        paper["notes"].append({"text": f"Autodidact cycle #{cycle}", "time": now_taipei()})

    return store.append(paper)


def main():
    parser = argparse.ArgumentParser(
        description="Log a paper read from an autodidact cycle"
    )
    parser.add_argument("--arxiv", required=True, help="Arxiv ID (e.g. 2301.07041)")
    parser.add_argument("--title", required=True, help="Paper title")
    parser.add_argument("--tags", default="", help="Comma-separated tags")
    parser.add_argument("--note", default="", help="Reading note")
    parser.add_argument("--status", default="read", choices=sorted(VALID_STATUSES))
    parser.add_argument("--cycle", default="", help="Autodidact cycle ID")
    args = parser.parse_args()

    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []

    result = log_paper_read(
        arxiv_id=args.arxiv,
        title=args.title,
        tags=tags,
        note=args.note or None,
        status=args.status,
        cycle=args.cycle or None,
    )
    print(f"Logged {result.get('id', '?')}: {result['title']} [{result['status']}]")


if __name__ == "__main__":
    main()
