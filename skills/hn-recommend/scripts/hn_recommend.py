#!/usr/bin/env python3
"""HN Recommender — Personalized Hacker News recommendations for Leo.

Two-stage pipeline:
  Stage 1 (this script): Fetch HN stories, dedup against seen history,
           apply interest profile scoring, output top-N candidates as JSON.
  Stage 2 (LLM cron session): Read candidates, write personalized "why it matters",
           send to Discord, log feedback.

Usage:
    python3 hn_recommend.py                        # fetch + score, output JSON
    python3 hn_recommend.py --limit 5              # top 5 candidates
    python3 hn_recommend.py --session morning       # tag for AM vs PM dedup
    python3 hn_recommend.py --mark-seen < ids.json  # mark article IDs as seen
    python3 hn_recommend.py --feedback <id> <+|->   # record positive/negative feedback
    python3 hn_recommend.py --profile               # show current interest profile
    python3 hn_recommend.py --stats                 # show recommendation stats
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from collections import Counter

TZ = timezone(timedelta(hours=8))


def find_workspace():
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        if os.path.isdir(os.path.join(d, '.git')):
            return d
        d = os.path.dirname(d)
    return os.path.expanduser('~/.openclaw/workspace')


WS = find_workspace()
DATA_DIR = os.path.join(WS, 'memory', 'hn')
PROFILE_PATH = os.path.join(DATA_DIR, 'preferences.json')
SEEN_PATH = os.path.join(DATA_DIR, 'seen.jsonl')
FEEDBACK_PATH = os.path.join(DATA_DIR, 'feedback.jsonl')
STATS_PATH = os.path.join(DATA_DIR, 'stats.json')


# ── Interest Profile ──────────────────────────────────────────────

DEFAULT_PROFILE = {
    "version": 1,
    "updated": None,
    "boost_keywords": {
        # Core research (high weight)
        "mechanistic interpretability": 5,
        "interpretability": 4,
        "sparse autoencoder": 5, "SAE": 4,
        "activation patching": 5,
        "probing": 3,
        "circuit": 3,
        "superposition": 4,
        # AI Safety
        "alignment": 4, "ai safety": 4, "jailbreak": 5,
        "adversarial": 3, "red team": 3,
        "RLHF": 3, "constitutional ai": 3,
        # Speech/Audio ML
        "speech": 4, "audio": 4, "whisper": 5,
        "ASR": 3, "TTS": 2, "voice": 2,
        "multimodal": 3,
        # General ML interest
        "transformer": 3, "LLM": 3, "language model": 3,
        "fine-tuning": 2, "LoRA": 3,
        "scaling": 2, "emergent": 3,
        "benchmark": 2, "evaluation": 2,
        # Research meta
        "Anthropic": 3, "DeepMind": 3, "OpenAI": 2,
        "Neel Nanda": 5, "Chris Olah": 4,
        "MATS": 4,
        # Tooling Leo uses
        "TransformerLens": 5, "NNsight": 4, "SAELens": 4,
        "pyvene": 3,
    },
    "penalty_keywords": {
        # Topics Leo doesn't care about
        "crypto": -5, "bitcoin": -5, "blockchain": -5, "NFT": -5,
        "web dev": -3, "CSS": -3, "React": -2,
        "game dev": -3, "Unity": -3,
        "hiring": -4, "job board": -4,
        "IPO": -3, "fundraising": -2,
        "Rust": -1, "Go lang": -1,  # mild penalty, sometimes ML-adjacent
    },
    "preferred_categories": [
        "ml_research", "ai_safety", "speech_audio",
        "interpretability", "tooling", "science"
    ],
    "min_hn_score": 20,  # ignore stories with <20 points
}


def load_profile():
    """Load interest profile, create default if missing."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(PROFILE_PATH):
        try:
            with open(PROFILE_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError):
            pass
    # Write default
    save_profile(DEFAULT_PROFILE)
    return DEFAULT_PROFILE.copy()


def save_profile(profile):
    os.makedirs(DATA_DIR, exist_ok=True)
    profile['updated'] = datetime.now(TZ).isoformat()
    tmp = PROFILE_PATH + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
        f.write('\n')
    os.replace(tmp, PROFILE_PATH)


# ── Seen History ──────────────────────────────────────────────────

def load_seen(max_age_days=7):
    """Load seen article IDs (dedup window)."""
    seen = set()
    if not os.path.exists(SEEN_PATH):
        return seen
    cutoff = datetime.now(TZ) - timedelta(days=max_age_days)
    kept_lines = []
    with open(SEEN_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                ts = datetime.fromisoformat(entry['ts'])
                if ts >= cutoff:
                    seen.add(entry['id'])
                    kept_lines.append(line)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
    # GC old entries
    if len(kept_lines) < sum(1 for _ in open(SEEN_PATH)):
        with open(SEEN_PATH, 'w') as f:
            for line in kept_lines:
                f.write(line + '\n')
    return seen


def mark_seen(ids):
    """Mark article IDs as seen."""
    os.makedirs(DATA_DIR, exist_ok=True)
    now = datetime.now(TZ).isoformat()
    with open(SEEN_PATH, 'a') as f:
        for aid in ids:
            f.write(json.dumps({"id": str(aid), "ts": now}) + '\n')


# ── Feedback ──────────────────────────────────────────────────────

def record_feedback(article_id, positive, title=""):
    """Record positive/negative feedback, update profile weights."""
    os.makedirs(DATA_DIR, exist_ok=True)
    entry = {
        "id": str(article_id),
        "positive": positive,
        "title": title,
        "ts": datetime.now(TZ).isoformat(),
    }
    with open(FEEDBACK_PATH, 'a') as f:
        f.write(json.dumps(entry) + '\n')
    print(f"Feedback recorded: {'👍' if positive else '👎'} {article_id} {title}", file=sys.stderr)


def get_feedback_stats():
    """Summarize feedback history."""
    if not os.path.exists(FEEDBACK_PATH):
        return {"total": 0, "positive": 0, "negative": 0, "keywords": {}}
    pos = neg = 0
    keyword_hits = Counter()
    with open(FEEDBACK_PATH) as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                if entry.get('positive'):
                    pos += 1
                    # Extract keywords from liked titles for profile learning
                    for word in entry.get('title', '').lower().split():
                        if len(word) > 3:
                            keyword_hits[word] += 1
                else:
                    neg += 1
            except (json.JSONDecodeError, KeyError):
                continue
    return {"total": pos + neg, "positive": pos, "negative": neg,
            "top_keywords": keyword_hits.most_common(10)}


# ── Fetch ─────────────────────────────────────────────────────────

def fetch_url(url, max_bytes=500_000):
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (HN-Recommend/1.0)'
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read(max_bytes).decode('utf-8', errors='replace')
    except (urllib.error.URLError, OSError) as e:
        print(f"WARN: fetch {url}: {e}", file=sys.stderr)
        return None


def fetch_hn_top(limit=50):
    """Fetch top HN stories."""
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
                'id': str(sid),
                'title': item.get('title', ''),
                'url': item.get('url', f"https://news.ycombinator.com/item?id={sid}"),
                'hn_url': f"https://news.ycombinator.com/item?id={sid}",
                'score': item.get('score', 0),
                'comments': item.get('descendants', 0),
                'by': item.get('by', ''),
                'time': item.get('time', 0),
            })
        except json.JSONDecodeError:
            continue
    return items


# ── Scoring ───────────────────────────────────────────────────────

def score_article(item, profile):
    """Score an article based on interest profile. Higher = more relevant."""
    title = item['title'].lower()
    url = item.get('url', '').lower()
    text = f"{title} {url}"
    score = 0.0

    # Keyword boost/penalty
    for kw, weight in profile.get('boost_keywords', {}).items():
        if kw.lower() in text:
            score += weight

    for kw, weight in profile.get('penalty_keywords', {}).items():
        if kw.lower() in text:
            score += weight  # weight is already negative

    # HN score bonus (popular = likely interesting)
    hn_score = item.get('score', 0)
    if hn_score >= 500:
        score += 3
    elif hn_score >= 200:
        score += 2
    elif hn_score >= 100:
        score += 1

    # Comment engagement bonus
    comments = item.get('comments', 0)
    if comments >= 200:
        score += 1.5
    elif comments >= 100:
        score += 1

    # URL domain hints
    domain_boosts = {
        'arxiv.org': 2, 'openreview.net': 2,
        'anthropic.com': 2, 'deepmind.com': 2,
        'alignmentforum.org': 2, 'lesswrong.com': 1,
        'transformer-circuits.pub': 3,
        'github.com': 0.5,
    }
    for domain, boost in domain_boosts.items():
        if domain in url:
            score += boost
            break

    return round(score, 1)


def classify_action(score):
    """Suggest action level based on score."""
    if score >= 8:
        return "深讀"
    elif score >= 5:
        return "略讀"
    else:
        return "掃標題"


# ── Main ──────────────────────────────────────────────────────────

def cmd_fetch_and_score(args):
    """Main flow: fetch, dedup, score, output top candidates."""
    profile = load_profile()
    seen = load_seen()

    fetch_count = max(args.limit * 5, 40)  # fetch many to find ML/AI gems
    print(f"Fetching HN top {fetch_count}...", file=sys.stderr)
    items = fetch_hn_top(limit=fetch_count)

    if not items:
        print("ERROR: No stories fetched", file=sys.stderr)
        json.dump({"items": [], "error": "fetch_failed"}, sys.stdout)
        return

    # Filter by min score
    min_score = profile.get('min_hn_score', 20)
    items = [i for i in items if i.get('score', 0) >= min_score]

    # Dedup against seen
    before_dedup = len(items)
    items = [i for i in items if i['id'] not in seen]
    print(f"Dedup: {before_dedup} → {len(items)} (removed {before_dedup - len(items)} seen)", file=sys.stderr)

    # Score
    for item in items:
        item['interest_score'] = score_article(item, profile)
        item['suggested_action'] = classify_action(item['interest_score'])

    # Sort by interest score desc
    items.sort(key=lambda x: x['interest_score'], reverse=True)

    # Take top N
    candidates = items[:args.limit]

    output = {
        'timestamp': datetime.now(TZ).isoformat(),
        'session': args.session,
        'total_fetched': before_dedup,
        'after_dedup': len(items),
        'candidates': len(candidates),
        'items': candidates,
    }

    json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
    print(file=sys.stdout)  # trailing newline


def cmd_collect(args):
    """Collect: fetch, score, append new candidates to daily JSONL. Silent accumulation."""
    profile = load_profile()
    seen = load_seen()

    fetch_count = max(args.limit * 5, 50)
    print(f"Collecting HN top {fetch_count}...", file=sys.stderr)
    items = fetch_hn_top(limit=fetch_count)

    if not items:
        print("No stories fetched", file=sys.stderr)
        return

    min_score = profile.get('min_hn_score', 20)
    items = [i for i in items if i.get('score', 0) >= min_score]
    items = [i for i in items if i['id'] not in seen]

    for item in items:
        item['interest_score'] = score_article(item, profile)
        item['suggested_action'] = classify_action(item['interest_score'])

    # Load existing daily candidates to dedup
    today = args.date or datetime.now(TZ).strftime('%Y-%m-%d')
    candidates_dir = os.path.join(DATA_DIR, 'candidates')
    os.makedirs(candidates_dir, exist_ok=True)
    daily_path = os.path.join(candidates_dir, f'{today}.jsonl')

    existing_ids = set()
    if os.path.exists(daily_path):
        with open(daily_path) as f:
            for line in f:
                try:
                    existing_ids.add(json.loads(line.strip())['id'])
                except (json.JSONDecodeError, KeyError):
                    continue

    new_items = [i for i in items if i['id'] not in existing_ids]
    if not new_items:
        print(f"No new candidates (all {len(items)} already collected)", file=sys.stderr)
        return

    with open(daily_path, 'a') as f:
        for item in new_items:
            item['collected_at'] = datetime.now(TZ).isoformat()
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print(f"Collected {len(new_items)} new candidates → {daily_path} (total today: {len(existing_ids) + len(new_items)})", file=sys.stderr)


def cmd_digest(args):
    """Digest: read today's collected candidates, rank, output top N as JSON for LLM."""
    today = args.date or datetime.now(TZ).strftime('%Y-%m-%d')
    candidates_dir = os.path.join(DATA_DIR, 'candidates')
    daily_path = os.path.join(candidates_dir, f'{today}.jsonl')

    if not os.path.exists(daily_path):
        print(f"No candidates for {today}", file=sys.stderr)
        json.dump({"items": [], "date": today}, sys.stdout)
        return

    items = []
    with open(daily_path) as f:
        for line in f:
            try:
                items.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue

    # Re-score with latest profile (scores may have been stale)
    profile = load_profile()
    for item in items:
        item['interest_score'] = score_article(item, profile)
        item['suggested_action'] = classify_action(item['interest_score'])

    # Sort by interest score desc, then HN score as tiebreaker
    items.sort(key=lambda x: (x.get('interest_score', 0), x.get('score', 0)), reverse=True)

    top = items[:args.limit]

    output = {
        'date': today,
        'total_collected': len(items),
        'selected': len(top),
        'items': top,
    }
    json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
    print()
    print(f"Digest: {len(items)} candidates → top {len(top)}", file=sys.stderr)


def cmd_mark_seen(args):
    """Mark IDs as seen from stdin JSON array."""
    try:
        ids = json.load(sys.stdin)
        if not isinstance(ids, list):
            ids = [ids]
        mark_seen(ids)
        print(f"Marked {len(ids)} as seen", file=sys.stderr)
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_feedback(args):
    positive = args.sentiment == '+'
    record_feedback(args.article_id, positive, title=args.title or "")


def cmd_profile(args):
    profile = load_profile()
    json.dump(profile, sys.stdout, indent=2, ensure_ascii=False)
    print()


def cmd_stats(args):
    fb = get_feedback_stats()
    seen_count = len(load_seen())
    stats = {
        "seen_articles_7d": seen_count,
        "feedback": fb,
        "profile_version": load_profile().get('version', 0),
    }
    json.dump(stats, sys.stdout, indent=2, ensure_ascii=False)
    print()


def main():
    parser = argparse.ArgumentParser(description='HN Recommender for Leo')
    sub = parser.add_subparsers(dest='command')

    # fetch: one-shot fetch + score (legacy, still works)
    p_fetch = sub.add_parser('fetch', help='Fetch and score HN stories (one-shot)')
    p_fetch.add_argument('--limit', type=int, default=8, help='Number of candidates')
    p_fetch.add_argument('--session', default='default', help='Session tag')

    # collect: silent hourly accumulation
    p_collect = sub.add_parser('collect', help='Fetch and append new candidates to daily file')
    p_collect.add_argument('--limit', type=int, default=15, help='Max candidates per collect')
    p_collect.add_argument('--date', default=None, help='Override date (YYYY-MM-DD)')

    # digest: daily summary for LLM
    p_digest = sub.add_parser('digest', help='Output top-N from today\'s collected candidates')
    p_digest.add_argument('--limit', type=int, default=10, help='Number of items in digest')
    p_digest.add_argument('--date', default=None, help='Override date (YYYY-MM-DD)')

    p_seen = sub.add_parser('mark-seen', help='Mark article IDs as seen')

    p_fb = sub.add_parser('feedback', help='Record feedback')
    p_fb.add_argument('article_id', help='HN story ID')
    p_fb.add_argument('sentiment', choices=['+', '-'], help='+ for positive, - for negative')
    p_fb.add_argument('--title', default='', help='Article title')

    p_prof = sub.add_parser('profile', help='Show interest profile')

    p_stats = sub.add_parser('stats', help='Show recommendation stats')

    args = parser.parse_args()

    if args.command == 'collect':
        cmd_collect(args)
    elif args.command == 'digest':
        cmd_digest(args)
    elif args.command == 'mark-seen':
        cmd_mark_seen(args)
    elif args.command == 'feedback':
        cmd_feedback(args)
    elif args.command == 'profile':
        cmd_profile(args)
    elif args.command == 'stats':
        cmd_stats(args)
    elif args.command == 'fetch':
        cmd_fetch_and_score(args)
    else:
        # Default to fetch
        if not hasattr(args, 'limit'):
            args.limit = 8
        if not hasattr(args, 'session'):
            args.session = 'default'
        cmd_fetch_and_score(args)


if __name__ == '__main__':
    main()
