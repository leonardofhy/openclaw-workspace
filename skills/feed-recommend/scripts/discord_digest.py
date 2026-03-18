#!/usr/bin/env python3
"""Format feed recommendations as a Discord message.

Usage:
    python3 feed.py recommend --limit 10 | python3 discord_digest.py
    python3 discord_digest.py --json-file /tmp/feed_articles.json
    python3 discord_digest.py --dry-run  # print instead of send
"""

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))

# Source emoji mapping
SOURCE_EMOJI = {
    "hn": "🟠",
    "af": "🔬",
    "arxiv": "📄",
    "lw": "🧠",
}

ACTION_EMOJI = {
    "深讀": "⭐",
    "略讀": "📌",
    "skip": "⏭️",
}


def format_digest(data: dict) -> str:
    """Format recommendation data into a Discord-friendly message."""
    items = data.get("items", data.get("articles", []))
    total = data.get("total_fetched", 0)
    now = datetime.now(TZ)

    if not items:
        return f"📡 **Feed Digest** — {now.strftime('%m/%d %H:%M')}\n\n沒有新推薦。今天掃了 {total} 篇，都不夠相關。"

    lines = [
        f"📡 **Daily Feed Digest** — {now.strftime('%m/%d')}",
        f"從 {total} 篇中挑了 {len(items)} 篇：",
        "",
    ]

    for i, item in enumerate(items, 1):
        src = SOURCE_EMOJI.get(item.get("source", ""), "📰")
        score = item.get("interest_score", 0)
        action = item.get("suggested_action", "")
        action_icon = ACTION_EMOJI.get(action, "")
        title = item.get("title", "Untitled")
        url = item.get("url", "")
        author = item.get("author", "")

        # Score bar (visual)
        filled = min(int(score / 2), 10)
        bar = "█" * filled + "░" * (10 - filled)

        # Format: number + source emoji + title (linked) + score
        line = f"**{i}.** {src} [{title}](<{url}>)"
        if author:
            line += f" — {author}"
        lines.append(line)
        lines.append(f"   {bar} {score:.1f} {action_icon}")
        lines.append("")

    # Source breakdown
    source_counts = {}
    for item in items:
        s = item.get("source", "?")
        source_counts[s] = source_counts.get(s, 0) + 1

    breakdown = " · ".join(
        f"{SOURCE_EMOJI.get(s, '📰')}{s}:{c}" for s, c in sorted(source_counts.items())
    )
    lines.append(f"─── {breakdown} ───")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Format feed digest for Discord")
    parser.add_argument("--json-file", help="Read from file instead of stdin")
    parser.add_argument("--dry-run", action="store_true", help="Print instead of outputting")
    args = parser.parse_args()

    if args.json_file:
        with open(args.json_file) as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    msg = format_digest(data)
    print(msg)


if __name__ == "__main__":
    main()
