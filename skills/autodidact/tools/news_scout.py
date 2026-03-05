#!/usr/bin/env python3
"""Autodidact News Scout — 2-stage pipeline: Python coarse filter → LLM relevance scoring.

Stage 1: Fetch HN front page + Alignment Forum recent, extract titles/URLs/snippets,
         blocklist obvious irrelevant topics.
Stage 2: (Done by the LLM cron session) Score remaining items for research relevance.

This script handles Stage 1 only. Stage 2 is done by the LLM that calls this script —
it reads the output and scores each item.

Usage:
    python3 news_scout.py                    # fetch + coarse filter, output JSON to stdout
    python3 news_scout.py --sources hn       # only Hacker News
    python3 news_scout.py --sources af       # only Alignment Forum
    python3 news_scout.py --sources hn,af    # both (default)
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))

# --- Blocklist: topics definitely irrelevant to Leo's research ---
BLOCKLIST_PATTERNS = [
    r'\bcrypto\b', r'\bbitcoin\b', r'\bethereum\b', r'\bnft\b', r'\bblockchain\b',
    r'\bhiring\b', r'\bwe.re hiring\b', r'\bjob board\b',
    r'\bweb ?dev\b', r'\bcss\b', r'\breact\.?js\b', r'\bvue\.?js\b', r'\bangular\b',
    r'\bgame dev\b', r'\bunity\b', r'\bunreal engine\b',
    r'\brust\b.*\blang\b', r'\bzig\b.*\blang\b',  # programming language news (not ML)
    r'\bipo\b', r'\bfundraising\b.*\bseries [a-d]\b',
    r'\bshow hn\b.*\b(saas|crm|cms|erp)\b',
]
BLOCKLIST_RE = re.compile('|'.join(BLOCKLIST_PATTERNS), re.IGNORECASE)


def fetch_url(url, max_bytes=500_000):
    """Simple URL fetch with timeout."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (autodidact-news-scout)'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read(max_bytes).decode('utf-8', errors='replace')
    except (urllib.error.URLError, OSError, UnicodeDecodeError) as e:
        print(f"WARN: fetch {url}: {e}", file=sys.stderr)
        return None


def fetch_hn_top(limit=30):
    """Fetch top HN stories via API."""
    items = []
    raw = fetch_url('https://hacker-news.firebaseio.com/v0/topstories.json')
    if not raw:
        return items

    try:
        story_ids = json.loads(raw)[:limit]
    except json.JSONDecodeError:
        return items

    for sid in story_ids:
        raw_item = fetch_url(f'https://hacker-news.firebaseio.com/v0/item/{sid}.json')
        if not raw_item:
            continue
        try:
            item = json.loads(raw_item)
            if item.get('type') != 'story':
                continue
            items.append({
                'source': 'hn',
                'title': item.get('title', ''),
                'url': item.get('url', f"https://news.ycombinator.com/item?id={sid}"),
                'hn_url': f"https://news.ycombinator.com/item?id={sid}",
                'score': item.get('score', 0),
                'comments': item.get('descendants', 0),
            })
        except json.JSONDecodeError:
            continue

    return items


def fetch_af_recent(limit=20):
    """Fetch recent Alignment Forum posts via RSS feed."""
    items = []
    raw = fetch_url('https://www.alignmentforum.org/feed.xml')
    if not raw:
        # Fallback: try LessWrong AF tag
        raw = fetch_url('https://www.lesswrong.com/feed.xml?view=community&karmaThreshold=30')
    if not raw:
        return items

    # Regex-based RSS parsing (AF feed has broken CDATA, can't use ET)
    item_pattern = re.compile(r'<item>(.*?)</item>', re.DOTALL)
    title_pattern = re.compile(r'<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>', re.DOTALL)
    link_pattern = re.compile(r'<link>(.*?)</link>')
    date_pattern = re.compile(r'<pubDate>(.*?)</pubDate>')
    creator_pattern = re.compile(r'<dc:creator><!\[CDATA\[(.*?)\]\]></dc:creator>|<dc:creator>(.*?)</dc:creator>', re.DOTALL)

    for match in item_pattern.finditer(raw):
        if len(items) >= limit:
            break
        block = match.group(1)
        t = title_pattern.search(block)
        l = link_pattern.search(block)
        d = date_pattern.search(block)
        c = creator_pattern.search(block)

        title = (t.group(1) or t.group(2)).strip() if t else ''
        link = l.group(1).strip() if l else ''
        pub_date = d.group(1).strip() if d else ''
        author = ((c.group(1) or c.group(2)).strip() if c else '')

        if title and link:
            items.append({
                'source': 'af',
                'title': title,
                'url': link,
                'score': 0,
                'comments': 0,
                'author': author,
                'posted': pub_date,
            })

    return items


def coarse_filter(items):
    """Remove obviously irrelevant items via blocklist."""
    filtered = []
    blocked = 0
    for item in items:
        text = item['title'].lower()
        if BLOCKLIST_RE.search(text):
            blocked += 1
            continue
        filtered.append(item)

    print(f"Coarse filter: {len(items)} → {len(filtered)} (blocked {blocked})", file=sys.stderr)
    return filtered


def main():
    parser = argparse.ArgumentParser(description='News Scout Stage 1')
    parser.add_argument('--sources', default='hn,af', help='Comma-separated: hn,af')
    parser.add_argument('--hn-limit', type=int, default=30)
    parser.add_argument('--af-limit', type=int, default=20)
    args = parser.parse_args()

    sources = [s.strip() for s in args.sources.split(',')]
    all_items = []

    if 'hn' in sources:
        print(f"Fetching HN top {args.hn_limit}...", file=sys.stderr)
        all_items.extend(fetch_hn_top(args.hn_limit))

    if 'af' in sources:
        print(f"Fetching AF recent {args.af_limit}...", file=sys.stderr)
        all_items.extend(fetch_af_recent(args.af_limit))

    filtered = coarse_filter(all_items)

    output = {
        'timestamp': datetime.now(TZ).isoformat(),
        'sources': sources,
        'total_fetched': len(all_items),
        'after_filter': len(filtered),
        'items': filtered,
    }

    # Output JSON to stdout for LLM to process
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
