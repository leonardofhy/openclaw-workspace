#!/usr/bin/env python3
"""Save news scout results to daily digest file + optionally add to autodidact queue.

Usage (called by the LLM after scoring):
    python3 news_digest.py --date 2026-03-01 < scored_items.json
    python3 news_digest.py --date 2026-03-01 --add-to-queue < scored_items.json

Input: JSON array of scored items on stdin:
[
  {"title": "...", "url": "...", "source": "hn", "relevance": 8, "why": "Direct connection to Track 5"},
  ...
]
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))

def find_workspace():
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        if os.path.isdir(os.path.join(d, '.git')):
            return d
        d = os.path.dirname(d)
    return os.path.expanduser('~/.openclaw/workspace')

def main():
    parser = argparse.ArgumentParser(description='Save news digest')
    parser.add_argument('--date', default=datetime.now(TZ).strftime('%Y-%m-%d'))
    parser.add_argument('--add-to-queue', action='store_true',
                        help='Add high-relevance items to autodidact queue')
    parser.add_argument('--min-relevance', type=int, default=7,
                        help='Minimum relevance score to include (default: 7)')
    parser.add_argument('--file', help='Read scored items from file instead of stdin')
    args = parser.parse_args()

    ws = find_workspace()
    news_dir = os.path.join(ws, 'memory', 'learning', 'news')
    os.makedirs(news_dir, exist_ok=True)

    # Read scored items from file or stdin
    try:
        if args.file:
            with open(args.file) as f:
                items = json.load(f)
        else:
            items = json.load(sys.stdin)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"ERROR: Invalid input: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(items, list):
        items = items.get('items', [])

    # Filter by relevance
    relevant = [i for i in items if i.get('relevance', 0) >= args.min_relevance]
    relevant.sort(key=lambda x: x.get('relevance', 0), reverse=True)

    if not relevant:
        print(f"No items with relevance >= {args.min_relevance}. Skipping digest.")
        return

    # Write digest markdown
    digest_path = os.path.join(news_dir, f'{args.date}.md')
    with open(digest_path, 'w') as f:
        f.write(f"# 📰 News Digest — {args.date}\n\n")
        f.write(f"> {len(relevant)} relevant items (threshold: relevance ≥ {args.min_relevance})\n\n")

        for i, item in enumerate(relevant, 1):
            source_tag = {'hn': '🟠 HN', 'af': '🔵 AF'}.get(item.get('source', ''), item.get('source', ''))
            f.write(f"## {i}. [{item['title']}]({item['url']})\n")
            f.write(f"**{source_tag}** | Relevance: {item.get('relevance', '?')}/10\n")
            if item.get('why'):
                f.write(f"**Why**: {item['why']}\n")
            if item.get('author'):
                f.write(f"Author: {item['author']}\n")
            f.write("\n")

    print(f"Wrote {len(relevant)} items to {digest_path}")

    # Optionally add to queue
    if args.add_to_queue and relevant:
        queue_path = os.path.join(ws, 'memory', 'learning', 'state', 'queue.json')
        try:
            with open(queue_path) as f:
                queue = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print("WARN: Could not load queue.json", file=sys.stderr)
            return

        tasks = queue.get('tasks', [])
        max_num = max((int(t['id'][1:]) for t in tasks if t['id'].startswith('Q') and t['id'][1:].isdigit()), default=0)

        added = 0
        for item in relevant[:3]:  # Max 3 items per day
            if len(tasks) >= 25:
                print("Queue full (25), skipping remaining items", file=sys.stderr)
                break
            max_num += 1
            new_task = {
                "id": f"Q{max_num:03d}",
                "type": "read",
                "track": "T5" if 'safety' in item.get('why', '').lower() else "T3",
                "title": f"News: {item['title'][:60]}",
                "status": "ready",
                "priority": 3,
                "blocked_by": None,
                "definition_of_done": f"Read and note key insights. Source: {item['url'][:80]}",
                "created": args.date,
                "due": None
            }
            tasks.append(new_task)
            added += 1
            print(f"Added to queue: {new_task['id']} — {new_task['title']}")

        if added:
            queue['tasks'] = tasks
            tmp = queue_path + '.tmp'
            with open(tmp, 'w') as f:
                json.dump(queue, f, indent=2, ensure_ascii=False)
                f.write('\n')
            os.replace(tmp, queue_path)
            print(f"Queue updated: {added} tasks added")


if __name__ == '__main__':
    main()
