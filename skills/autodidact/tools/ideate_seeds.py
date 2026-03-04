#!/usr/bin/env python3
"""ideate_seeds.py — Collect seed elements for combinatorial ideation.

Scans multiple sources to extract "interesting elements" — concepts, methods,
findings, gaps — that can be cross-pollinated to generate novel research ideas.

Sources:
  1. events.jsonl    — recent cycle summaries (learnings + builds)
  2. queue.json      — completed task insights + active directions
  3. news/*.md       — recent news digests
  4. paper-reading-list.md — completed deep reads
  5. knowledge-graph entries (kg/ directory, if exists)
  6. active.json     — current research tracks

Usage:
  python3 ideate_seeds.py [--limit N] [--json]

Output: Structured list of seed elements, one per line.
        With --json: JSON array for programmatic use.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

def find_workspace():
    """Find the openclaw workspace root."""
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "AGENTS.md").exists():
            return parent
    home = Path.home()
    ws = home / ".openclaw" / "workspace"
    if ws.exists():
        return ws
    return Path.cwd()

WS = find_workspace()
LEARNING = WS / "memory" / "learning"

def load_events(limit=30):
    """Load recent events from events.jsonl."""
    path = LEARNING / "logs" / "events.jsonl"
    if not path.exists():
        return []
    lines = path.read_text().strip().split("\n")
    events = []
    for line in lines[-limit:]:
        try:
            e = json.loads(line)
            if e.get("action") in ("learn", "build", "reflect") and e.get("summary"):
                events.append({
                    "source": "event",
                    "id": e.get("task_id", "?"),
                    "action": e["action"],
                    "track": e.get("track", "?"),
                    "element": e["summary"],
                    "artifacts": e.get("artifacts", []),
                })
        except json.JSONDecodeError:
            continue
    return events

def load_queue_completed():
    """Load completed tasks from queue.json for their insights."""
    path = LEARNING / "state" / "queue.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    seeds = []
    for t in data.get("tasks", []):
        if t.get("status") == "done" and t.get("title"):
            seeds.append({
                "source": "queue_done",
                "id": t["id"],
                "track": t.get("track", "?"),
                "element": t["title"],
                "type": t.get("type", "unknown"),
            })
    return seeds

def load_active_tracks():
    """Load current research tracks from active.json."""
    path = LEARNING / "state" / "active.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    seeds = []
    for t in data.get("active_tracks", []):
        seeds.append({
            "source": "track",
            "id": t["id"],
            "element": f"{t['name']}: {t.get('objective', '')}",
            "status": t.get("status", "?"),
        })
    return seeds

def load_news_digests(days=7):
    """Load recent news digest highlights."""
    news_dir = LEARNING / "news"
    if not news_dir.exists():
        return []
    seeds = []
    cutoff = datetime.now() - timedelta(days=days)
    for f in sorted(news_dir.glob("*.md")):
        # Parse date from filename YYYY-MM-DD.md
        try:
            date_str = f.stem
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            if file_date < cutoff:
                continue
        except ValueError:
            continue
        content = f.read_text()
        # Extract items — look for headlines or bullet points
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("- **") or line.startswith("## "):
                # Clean up markdown
                clean = re.sub(r'[*#\[\]]', '', line).strip("- ").strip()
                if len(clean) > 15:
                    seeds.append({
                        "source": "news",
                        "date": date_str,
                        "element": clean[:200],
                    })
    return seeds

def load_paper_readings():
    """Load completed paper readings from paper-reading-list.md."""
    path = LEARNING / "paper-reading-list.md"
    if not path.exists():
        return []
    content = path.read_text()
    seeds = []
    # Extract papers from C/C2 sections (completed reads)
    in_completed = False
    for line in content.split("\n"):
        if "Completed" in line or "## C" in line:
            in_completed = True
            continue
        if line.startswith("## ") and in_completed:
            # new section
            if "Completed" not in line and "## C" not in line:
                in_completed = False
                continue
        if in_completed and line.strip().startswith(("- ", "| ")):
            clean = re.sub(r'[*|]', '', line).strip("- ").strip()
            if len(clean) > 15 and not clean.startswith("Paper") and not clean.startswith("---"):
                seeds.append({
                    "source": "paper",
                    "element": clean[:200],
                })
    return seeds

def load_kg_entries():
    """Load knowledge graph entries if available."""
    kg_dir = LEARNING / "kg"
    if not kg_dir.exists():
        return []
    seeds = []
    for f in sorted(kg_dir.glob("*.md"))[:10]:
        content = f.read_text()
        # First non-empty line as element
        for line in content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                seeds.append({
                    "source": "kg",
                    "element": line[:200],
                })
                break
    return seeds

def collect_all(limit=None):
    """Collect seeds from all sources."""
    all_seeds = []
    all_seeds.extend(load_active_tracks())
    all_seeds.extend(load_events(limit=30))
    all_seeds.extend(load_paper_readings())
    all_seeds.extend(load_news_digests(days=7))
    all_seeds.extend(load_queue_completed())
    all_seeds.extend(load_kg_entries())
    
    # Deduplicate by element text (fuzzy: first 50 chars)
    seen = set()
    unique = []
    for s in all_seeds:
        key = s["element"][:50].lower()
        if key not in seen:
            seen.add(key)
            unique.append(s)
    
    if limit:
        unique = unique[:limit]
    
    return unique

def main():
    parser = argparse.ArgumentParser(description="Collect ideation seed elements")
    parser.add_argument("--limit", type=int, default=None, help="Max seeds to return")
    parser.add_argument("--json", action="store_true", help="Output as JSON array")
    parser.add_argument("--summary", action="store_true", help="Print summary stats only")
    args = parser.parse_args()
    
    seeds = collect_all(limit=args.limit)
    
    if args.summary:
        by_source = {}
        for s in seeds:
            src = s["source"]
            by_source[src] = by_source.get(src, 0) + 1
        print(f"Total seeds: {len(seeds)}")
        for src, count in sorted(by_source.items()):
            print(f"  {src}: {count}")
        return
    
    if args.json:
        print(json.dumps(seeds, indent=2, ensure_ascii=False))
    else:
        for i, s in enumerate(seeds, 1):
            src = s["source"]
            elem = s["element"]
            extra = ""
            if "track" in s:
                extra = f" [{s['track']}]"
            elif "date" in s:
                extra = f" [{s['date']}]"
            print(f"{i:3d}. [{src}]{extra} {elem}")

if __name__ == "__main__":
    main()
