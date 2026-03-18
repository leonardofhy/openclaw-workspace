#!/usr/bin/env python3
"""Migrate papers from paper-reading-list.md into papers.jsonl.

Parses sections A/B/C/C2 from the markdown reading list, extracts metadata,
and adds each paper to the JSONL store via the paper tracker's store logic.
Idempotent: skips papers whose arxiv ID already exists in the store.

Also imports notes from memory/learning/paper-notes/ when a matching arxiv ID
is found in the filename.

Usage:
    python3 migrate_papers.py [--dry-run]
"""

import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Workspace / store setup (reuse paper tracker's store)
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

# Import the store setup from papers.py
from papers import WORKSPACE, STORE_PATH, store, now_taipei

READING_LIST = WORKSPACE / "memory" / "learning" / "paper-reading-list.md"
PAPER_NOTES_DIR = WORKSPACE / "memory" / "learning" / "paper-notes"

# ---------------------------------------------------------------------------
# Tag inference
# ---------------------------------------------------------------------------

TAG_KEYWORDS: dict[str, list[str]] = {
    "mech-interp": [
        "mechanistic", "interpretab", "causal abstraction", "causal patching",
        "logit lens", "activation", "steering", "probing", "patching",
        "circuit", "neuron", "attention head", "residual stream",
    ],
    "sae": ["sae", "sparse autoencoder", "sparse auto-encoder", "matryoshka"],
    "speech": [
        "speech", "audio", "whisper", "codec", "phonolog", "asr",
        "brain-to-speech", "vocalized", "imagined",
    ],
    "lm": ["lm", "language model", "lalm", "llm", "transformer"],
    "safety": [
        "safety", "adversarial", "robustness", "hallucination", "defense",
        "attack", "pgd",
    ],
    "emotion": ["emotion", "sentiment", "affective"],
    "multimodal": ["multimodal", "cross-modal", "modality", "audio-text"],
    "evaluation": ["benchmark", "evaluation", "eval", "metric"],
}


def infer_tags(text: str) -> list[str]:
    """Infer tags from paper description text."""
    lower = text.lower()
    tags = []
    for tag, keywords in TAG_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            tags.append(tag)
    return sorted(tags)


# ---------------------------------------------------------------------------
# Markdown parsing
# ---------------------------------------------------------------------------

ARXIV_RE = re.compile(r'(\d{4}\.\d{4,5}(?:v\d+)?)')
CYCLE_RE = re.compile(r'[Cc]ycle\s*((?:#|c-)\S+)')


def parse_section_c_bullet(line: str) -> dict | None:
    """Parse a bullet from section C (completed deep reads).

    Format: - **Author info arxiv_id** (year) — description
    """
    line = line.strip()
    if not line.startswith("- "):
        return None

    text = line[2:].strip()
    arxiv_match = ARXIV_RE.search(text)
    arxiv_id = arxiv_match.group(1) if arxiv_match else ""

    # Extract title: text between ** ** or before —
    title_match = re.match(r'\*\*(.+?)\*\*', text)
    if title_match:
        title = title_match.group(1).strip()
        # Clean arxiv ID from title
        title = ARXIV_RE.sub('', title).strip().rstrip(' —-')
    else:
        # No bold — use text up to first —
        parts = text.split('—', 1)
        title = parts[0].strip().rstrip(' —-')

    if not title or len(title) < 3:
        return None

    # Extract description after —
    desc = ""
    if '—' in text:
        desc = text.split('—', 1)[1].strip()
    elif '–' in text:
        desc = text.split('–', 1)[1].strip()

    cycle_match = CYCLE_RE.search(text)
    cycle = cycle_match.group(1) if cycle_match else ""

    return {
        "title": title,
        "arxiv_id": arxiv_id,
        "description": desc,
        "cycle": cycle,
    }


def parse_section_c2_row(line: str) -> dict | None:
    """Parse a table row from section C2.

    Format: | Paper | arXiv | Cycle | Key output |
    """
    line = line.strip()
    if not line.startswith("|") or line.startswith("|---") or line.startswith("| Paper"):
        return None

    # Split by | and drop empty first/last from leading/trailing |
    cells = line.split("|")
    # Remove empty strings from leading/trailing pipes
    if cells and cells[0].strip() == "":
        cells = cells[1:]
    if cells and cells[-1].strip() == "":
        cells = cells[:-1]
    cells = [c.strip() for c in cells]
    if len(cells) < 4:
        return None

    title = cells[0]
    arxiv_raw = cells[1]
    cycle_raw = cells[2]
    key_output = cells[3] if len(cells) > 3 else ""

    # Clean title
    title = re.sub(r'[*]', '', title).strip()
    if not title or title == "Paper":
        return None

    # Extract arxiv ID
    arxiv_match = ARXIV_RE.search(arxiv_raw)
    arxiv_id = arxiv_match.group(1) if arxiv_match else ""

    # Extract cycle number
    cycle = cycle_raw.lstrip('#').strip()

    return {
        "title": title,
        "arxiv_id": arxiv_id,
        "description": key_output,
        "cycle": cycle,
    }


def parse_reading_list(content: str) -> list[dict]:
    """Parse all papers from the reading list markdown."""
    papers = []
    current_section = None

    for line in content.split("\n"):
        # Detect section headers
        if line.startswith("## A)"):
            current_section = "A"
            continue
        elif line.startswith("## B)"):
            current_section = "B"
            continue
        elif line.startswith("## C2)"):
            current_section = "C2"
            continue
        elif line.startswith("## C)"):
            current_section = "C"
            continue
        elif line.startswith("## ") and current_section:
            current_section = None
            continue

        stripped = line.strip()
        if not stripped or stripped == "(empty)" or stripped == "- (empty)":
            continue

        entry = None
        if current_section == "C" and line.strip().startswith("- "):
            entry = parse_section_c_bullet(line)
            if entry:
                entry["status"] = "read"
        elif current_section == "C2" and line.strip().startswith("|"):
            entry = parse_section_c2_row(line)
            if entry:
                entry["status"] = "read"
        elif current_section == "A" and line.strip().startswith("- "):
            entry = parse_section_c_bullet(line)
            if entry:
                entry["status"] = "queued"
        elif current_section == "B" and line.strip().startswith("- "):
            entry = parse_section_c_bullet(line)
            if entry:
                entry["status"] = "reading"

        if entry:
            papers.append(entry)

    return papers


# ---------------------------------------------------------------------------
# Note import
# ---------------------------------------------------------------------------

def find_paper_note(arxiv_id: str) -> str | None:
    """Find a paper note file matching the arxiv ID."""
    if not arxiv_id or not PAPER_NOTES_DIR.exists():
        return None
    for f in PAPER_NOTES_DIR.glob("*.md"):
        if arxiv_id in f.name:
            return f.read_text()
    return None


def extract_note_summary(note_content: str) -> str:
    """Extract a summary from paper note markdown."""
    lines = []
    for line in note_content.split("\n"):
        line = line.strip()
        # Stop at Tags section
        if line.startswith("## Tags") or line.startswith("## Action"):
            break
        # Skip headers, empty lines, action items
        if not line or line.startswith("#") or line.startswith(">") or line.startswith("- ["):
            continue
        lines.append(line)
    return " ".join(lines[:5])[:500] if lines else ""


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------

def migrate(dry_run: bool = False) -> dict:
    """Run the migration. Returns stats dict."""
    if not READING_LIST.exists():
        print(f"Reading list not found: {READING_LIST}", file=sys.stderr)
        return {"error": "reading list not found"}

    content = READING_LIST.read_text()
    parsed = parse_reading_list(content)

    # Load existing papers to check for duplicates
    existing = store.load()
    existing_arxiv_ids = {p.get("arxiv_id") for p in existing if p.get("arxiv_id")}

    stats = {"parsed": len(parsed), "added": 0, "skipped": 0, "notes_imported": 0}

    for entry in parsed:
        arxiv_id = entry.get("arxiv_id", "")

        # Skip if already exists (idempotent)
        if arxiv_id and arxiv_id in existing_arxiv_ids:
            stats["skipped"] += 1
            if not dry_run:
                print(f"  SKIP (exists): {entry['title'][:60]}")
            continue

        # Build paper record
        tags = infer_tags(
            f"{entry['title']} {entry.get('description', '')}"
        )

        paper = {
            "title": entry["title"],
            "authors": [],
            "abstract": "",
            "arxiv_id": arxiv_id,
            "url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "",
            "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else "",
            "date": "",
            "categories": [],
            "venue": "",
            "status": entry.get("status", "read"),
            "tags": tags,
            "notes": [],
            "added_at": now_taipei(),
            "updated_at": now_taipei(),
        }

        # Add cycle info as note if present
        if entry.get("cycle"):
            paper["notes"].append({
                "text": f"Autodidact cycle #{entry['cycle']}",
                "time": now_taipei(),
            })

        # Add description as note
        if entry.get("description"):
            paper["notes"].append({
                "text": entry["description"],
                "time": now_taipei(),
            })

        # Import paper notes file if available
        note_content = find_paper_note(arxiv_id)
        if note_content:
            summary = extract_note_summary(note_content)
            if summary:
                paper["notes"].append({
                    "text": f"[imported note] {summary}",
                    "time": now_taipei(),
                })
                stats["notes_imported"] += 1

        if dry_run:
            print(f"  DRY-RUN add: {paper['title'][:60]} [{paper['status']}] tags={paper['tags']}")
        else:
            result = store.append(paper)
            print(f"  ADD {result['id']}: {paper['title'][:60]} [{paper['status']}] tags={paper['tags']}")
            # Track arxiv_id to avoid duplicates within same run
            if arxiv_id:
                existing_arxiv_ids.add(arxiv_id)

        stats["added"] += 1

    return stats


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Migrate papers from reading list to JSONL store")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated without writing")
    args = parser.parse_args()

    print(f"Source: {READING_LIST}")
    print(f"Target: {STORE_PATH}")
    print()

    stats = migrate(dry_run=args.dry_run)

    print(f"\nMigration {'(dry-run) ' if args.dry_run else ''}complete:")
    print(f"  Parsed:         {stats.get('parsed', 0)}")
    print(f"  Added:          {stats.get('added', 0)}")
    print(f"  Skipped (dupes):{stats.get('skipped', 0)}")
    print(f"  Notes imported: {stats.get('notes_imported', 0)}")


if __name__ == "__main__":
    main()
