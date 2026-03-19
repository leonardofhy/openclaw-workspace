#!/usr/bin/env python3
"""Learn from feedback to adjust future scoring.

Analyzes feedback.jsonl to extract patterns:
- Which keywords appear in liked vs disliked articles
- Which sources Leo prefers
- Which authors Leo engages with

Outputs adjustments that feed_engine applies as score modifiers.

Usage:
    python3 feedback_learner.py learn          # analyze + write adjustments
    python3 feedback_learner.py show           # show current adjustments
    python3 feedback_learner.py stats          # feedback statistics
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'shared'))
from jsonl_store import find_workspace

TZ = timezone(timedelta(hours=8))
WS = find_workspace()
FEEDS_DIR = os.path.join(WS, 'memory', 'feeds')
ADJUSTMENTS_PATH = os.path.join(FEEDS_DIR, 'feedback_adjustments.json')

# Stopwords for keyword extraction
STOPWORDS = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'need', 'dare', 'to', 'of',
    'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through',
    'during', 'before', 'after', 'above', 'below', 'between', 'out', 'off',
    'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there',
    'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both', 'few',
    'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only',
    'own', 'same', 'so', 'than', 'too', 'very', 'and', 'but', 'or', 'yet',
    'it', 'its', 'this', 'that', 'these', 'those', 'i', 'we', 'you', 'he',
    'she', 'they', 'what', 'which', 'who', 'whom', 'new', 'via', 'using',
}


def _extract_keywords(title: str) -> list[str]:
    """Extract meaningful words from a title."""
    words = re.findall(r'[a-zA-Z]{3,}', title.lower())
    return [w for w in words if w not in STOPWORDS]


def _extract_bigrams(title: str) -> list[str]:
    """Extract word bigrams from a title."""
    words = _extract_keywords(title)
    return [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]


def load_feedback() -> list[dict]:
    """Load all feedback entries."""
    fb_path = os.path.join(FEEDS_DIR, 'feedback.jsonl')
    entries = []
    if not os.path.exists(fb_path):
        return entries
    with open(fb_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def analyze_feedback(entries: list[dict]) -> dict:
    """Analyze feedback patterns.

    Returns:
        {
            "keyword_scores": {"word": score},  # positive = liked, negative = disliked
            "source_bias": {"source": score},
            "author_bias": {"author": score},
            "total_positive": int,
            "total_negative": int,
            "last_analyzed": str,
        }
    """
    keyword_pos = Counter()
    keyword_neg = Counter()
    bigram_pos = Counter()
    bigram_neg = Counter()
    source_pos = Counter()
    source_neg = Counter()
    total_pos = 0
    total_neg = 0

    for entry in entries:
        title = entry.get('title', '')
        source = entry.get('source', '')
        positive = entry.get('positive', True)

        keywords = _extract_keywords(title)
        bigrams = _extract_bigrams(title)

        if positive:
            total_pos += 1
            keyword_pos.update(keywords)
            bigram_pos.update(bigrams)
            source_pos[source] += 1
        else:
            total_neg += 1
            keyword_neg.update(keywords)
            bigram_neg.update(bigrams)
            source_neg[source] += 1

    # Compute keyword scores: log-odds style
    # Score = (pos_count - neg_count) / total * scale
    total = max(total_pos + total_neg, 1)
    keyword_scores = {}

    all_keywords = set(keyword_pos.keys()) | set(keyword_neg.keys())
    for kw in all_keywords:
        p = keyword_pos.get(kw, 0)
        n = keyword_neg.get(kw, 0)
        # Only include keywords with enough signal (≥2 appearances)
        if p + n < 2:
            continue
        # Scale: each feedback unit = 0.5 points, capped at ±3
        raw_score = (p - n) * 0.5
        keyword_scores[kw] = max(-3.0, min(3.0, raw_score))

    # Bigram scores (stronger signal)
    all_bigrams = set(bigram_pos.keys()) | set(bigram_neg.keys())
    for bg in all_bigrams:
        p = bigram_pos.get(bg, 0)
        n = bigram_neg.get(bg, 0)
        if p + n < 2:
            continue
        raw_score = (p - n) * 0.75
        keyword_scores[bg] = max(-3.0, min(3.0, raw_score))

    # Source bias
    source_bias = {}
    all_sources = set(source_pos.keys()) | set(source_neg.keys())
    for src in all_sources:
        p = source_pos.get(src, 0)
        n = source_neg.get(src, 0)
        if p + n < 2:
            continue
        raw_score = (p - n) * 0.3
        source_bias[src] = max(-2.0, min(2.0, raw_score))

    return {
        "keyword_scores": keyword_scores,
        "source_bias": source_bias,
        "total_positive": total_pos,
        "total_negative": total_neg,
        "feedback_count": total,
        "last_analyzed": datetime.now(TZ).isoformat(),
    }


def save_adjustments(adjustments: dict) -> None:
    """Save feedback adjustments."""
    os.makedirs(FEEDS_DIR, exist_ok=True)
    with open(ADJUSTMENTS_PATH, 'w') as f:
        json.dump(adjustments, f, indent=2, ensure_ascii=False)


def load_adjustments() -> dict | None:
    """Load saved feedback adjustments."""
    if not os.path.exists(ADJUSTMENTS_PATH):
        return None
    with open(ADJUSTMENTS_PATH) as f:
        return json.load(f)


def apply_feedback_score(article_title: str, article_source: str,
                         adjustments: dict | None = None) -> float:
    """Calculate feedback-based score adjustment for an article.

    This is called from feed_engine.score_article() to add feedback learning.
    """
    if adjustments is None:
        adjustments = load_adjustments()
    if not adjustments:
        return 0.0

    score = 0.0
    title_lower = article_title.lower()

    # Keyword adjustments
    for kw, weight in adjustments.get('keyword_scores', {}).items():
        if kw in title_lower:
            score += weight

    # Source bias
    source_bias = adjustments.get('source_bias', {})
    score += source_bias.get(article_source, 0.0)

    return round(score, 1)


# ── CLI ──────────────────────────────────────────────────────────

def cmd_learn(args):
    entries = load_feedback()
    if not entries:
        print("No feedback data yet. Use `feed.py feedback <uid> +/-` to add some.")
        return

    adjustments = analyze_feedback(entries)
    save_adjustments(adjustments)

    kw = adjustments['keyword_scores']
    src = adjustments['source_bias']
    print(f"Analyzed {adjustments['feedback_count']} feedback entries "
          f"(+{adjustments['total_positive']}, -{adjustments['total_negative']})")
    print(f"\nKeyword adjustments ({len(kw)}):")
    for k, v in sorted(kw.items(), key=lambda x: -abs(x[1])):
        sign = "+" if v > 0 else ""
        print(f"  {k}: {sign}{v}")
    if src:
        print(f"\nSource bias ({len(src)}):")
        for s, v in sorted(src.items(), key=lambda x: -x[1]):
            sign = "+" if v > 0 else ""
            print(f"  {s}: {sign}{v}")
    print(f"\nSaved to: {ADJUSTMENTS_PATH}")


def cmd_show(args):
    adj = load_adjustments()
    if not adj:
        print("No adjustments yet. Run `feedback_learner.py learn` first.")
        return
    print(json.dumps(adj, indent=2, ensure_ascii=False))


def cmd_stats(args):
    entries = load_feedback()
    if not entries:
        print("No feedback data.")
        return

    pos = sum(1 for e in entries if e.get('positive'))
    neg = len(entries) - pos
    sources = Counter(e.get('source', '?') for e in entries)

    print(f"Total: {len(entries)} feedback entries")
    print(f"  👍 Positive: {pos}")
    print(f"  👎 Negative: {neg}")
    print(f"\nBy source:")
    for src, count in sources.most_common():
        print(f"  {src}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Feed feedback learner")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("learn", help="Analyze feedback and generate adjustments")
    sub.add_parser("show", help="Show current adjustments")
    sub.add_parser("stats", help="Feedback statistics")

    args = parser.parse_args()
    {"learn": cmd_learn, "show": cmd_show, "stats": cmd_stats}[args.command](args)


if __name__ == "__main__":
    main()
