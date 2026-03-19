#!/usr/bin/env python3
"""Feed recommendation quality scorer.

Analyzes historical digests and feedback to compute quality metrics,
identify improvement areas, and recommend scoring weight adjustments.

Usage:
    python3 quality_scorer.py                # full quality report
    python3 quality_scorer.py --json         # JSON output for integration
    python3 quality_scorer.py --help
"""

import argparse
import json
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Bootstrap ────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR.parent.parent.parent / "shared"))

from jsonl_store import find_workspace

WS = find_workspace()
FEEDS_DIR = os.path.join(WS, "memory", "feeds")
CANDIDATES_DIR = os.path.join(FEEDS_DIR, "candidates")
TZ = timezone(timedelta(hours=8))


# ── Data Loading ─────────────────────────────────────────────────

def load_feedback(feeds_dir: str | None = None) -> list[dict]:
    """Load all feedback entries from feedback.jsonl."""
    fd = feeds_dir or FEEDS_DIR
    path = os.path.join(fd, "feedback.jsonl")
    entries = []
    if not os.path.exists(path):
        return entries
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def load_candidates(feeds_dir: str | None = None) -> list[dict]:
    """Load all candidate articles from daily digest files."""
    fd = feeds_dir or FEEDS_DIR
    cand_dir = os.path.join(fd, "candidates")
    items: list[dict] = []

    # Scan .json files in candidates/
    if os.path.isdir(cand_dir):
        for fname in sorted(os.listdir(cand_dir)):
            fpath = os.path.join(cand_dir, fname)
            if fname.endswith(".json"):
                try:
                    with open(fpath) as fh:
                        data = json.load(fh)
                    if isinstance(data, dict):
                        items.extend(data.get("items", data.get("articles", [])))
                    elif isinstance(data, list):
                        items.extend(data)
                except (json.JSONDecodeError, KeyError):
                    continue
            elif fname.endswith(".jsonl"):
                try:
                    with open(fpath) as fh:
                        for line in fh:
                            line = line.strip()
                            if line:
                                entry = json.loads(line)
                                if "title" in entry and "url" in entry:
                                    items.append(entry)
                except (json.JSONDecodeError, KeyError):
                    continue

    # Also scan top-level .json digest files
    if os.path.isdir(fd):
        for fname in sorted(os.listdir(fd)):
            if not fname.endswith(".json"):
                continue
            if fname in ("config.json", "preferences.json"):
                continue
            fpath = os.path.join(fd, fname)
            try:
                with open(fpath) as fh:
                    data = json.load(fh)
                if isinstance(data, dict):
                    items.extend(data.get("items", data.get("articles", [])))
            except (json.JSONDecodeError, KeyError):
                continue

    return items


def load_seen(feeds_dir: str | None = None) -> list[dict]:
    """Load seen entries from seen.jsonl."""
    fd = feeds_dir or FEEDS_DIR
    path = os.path.join(fd, "seen.jsonl")
    entries = []
    if not os.path.exists(path):
        return entries
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


# ── Quality Metrics ──────────────────────────────────────────────

def compute_feedback_metrics(feedback: list[dict]) -> dict:
    """Compute feedback-based quality metrics."""
    if not feedback:
        return {
            "total_feedback": 0,
            "positive_rate": 0.0,
            "negative_rate": 0.0,
            "by_source": {},
        }

    total = len(feedback)
    positive = sum(1 for f in feedback if f.get("positive"))
    negative = total - positive

    by_source: dict[str, dict] = defaultdict(lambda: {"pos": 0, "neg": 0, "total": 0})
    for entry in feedback:
        src = entry.get("source", "unknown") or "unknown"
        by_source[src]["total"] += 1
        if entry.get("positive"):
            by_source[src]["pos"] += 1
        else:
            by_source[src]["neg"] += 1

    source_rates = {}
    for src, counts in by_source.items():
        source_rates[src] = {
            "total": counts["total"],
            "positive": counts["pos"],
            "negative": counts["neg"],
            "positive_rate": round(counts["pos"] / counts["total"], 3) if counts["total"] else 0,
        }

    return {
        "total_feedback": total,
        "positive_rate": round(positive / total, 3) if total else 0,
        "negative_rate": round(negative / total, 3) if total else 0,
        "by_source": source_rates,
    }


def compute_diversity_index(candidates: list[dict]) -> dict:
    """Compute source diversity using Shannon entropy."""
    source_counts = Counter(item.get("source", "unknown") for item in candidates)
    total = sum(source_counts.values())
    if total == 0:
        return {"shannon_entropy": 0.0, "normalized_entropy": 0.0,
                "source_distribution": {}, "num_sources": 0}

    probs = [count / total for count in source_counts.values()]
    entropy = -sum(p * math.log2(p) for p in probs if p > 0)
    max_entropy = math.log2(len(source_counts)) if len(source_counts) > 1 else 1.0
    normalized = round(entropy / max_entropy, 3) if max_entropy > 0 else 0.0

    distribution = {
        src: {"count": count, "pct": round(count / total * 100, 1)}
        for src, count in source_counts.most_common()
    }

    return {
        "shannon_entropy": round(entropy, 3),
        "normalized_entropy": normalized,
        "source_distribution": distribution,
        "num_sources": len(source_counts),
    }


def compute_precision_at_k(candidates: list[dict], feedback: list[dict],
                           k: int = 10) -> float:
    """Estimate precision@K from feedback on top-K recommendations.

    Uses feedback as ground truth: items with positive feedback are "relevant".
    Returns the fraction of top-K recommended items that received positive feedback.
    """
    if not candidates or not feedback:
        return 0.0

    # Build set of positively-rated URLs/UIDs
    positive_ids: set[str] = set()
    for entry in feedback:
        if entry.get("positive"):
            positive_ids.add(entry.get("id", ""))
            # Also match by title substring for fuzzy matching
            title = entry.get("title", "")
            if title:
                positive_ids.add(title)

    # Sort candidates by interest_score descending (top-K)
    scored = [c for c in candidates if "interest_score" in c]
    scored.sort(key=lambda x: float(x.get("interest_score", 0)), reverse=True)
    top_k = scored[:k]

    if not top_k:
        return 0.0

    relevant = 0
    for item in top_k:
        uid = item.get("uid", "")
        url = item.get("url", "")
        title = item.get("title", "")
        if uid in positive_ids or url in positive_ids or title in positive_ids:
            relevant += 1

    return round(relevant / len(top_k), 3)


def compute_novelty_score(candidates: list[dict], seen: list[dict]) -> float:
    """Fraction of recommended items that were NOT previously seen."""
    if not candidates:
        return 0.0

    seen_ids = {entry.get("id", "") for entry in seen}
    seen_ids |= {entry.get("url", "") for entry in seen if "url" in entry}

    novel = 0
    for item in candidates:
        uid = item.get("uid", "")
        url = item.get("url", "")
        if uid not in seen_ids and url not in seen_ids:
            novel += 1

    return round(novel / len(candidates), 3)


# ── Improvement Analysis ─────────────────────────────────────────

def identify_low_rated_sources(feedback: list[dict],
                               min_feedback: int = 3) -> list[dict]:
    """Find sources with consistently low positive rates."""
    by_source: dict[str, dict] = defaultdict(lambda: {"pos": 0, "neg": 0})
    for entry in feedback:
        src = entry.get("source", "unknown") or "unknown"
        if entry.get("positive"):
            by_source[src]["pos"] += 1
        else:
            by_source[src]["neg"] += 1

    low_rated = []
    for src, counts in by_source.items():
        total = counts["pos"] + counts["neg"]
        if total < min_feedback:
            continue
        rate = counts["pos"] / total
        if rate < 0.5:
            low_rated.append({
                "source": src,
                "positive_rate": round(rate, 3),
                "total_feedback": total,
                "suggestion": f"Consider reducing weight for '{src}' or reviewing its relevance filter",
            })

    low_rated.sort(key=lambda x: x["positive_rate"])
    return low_rated


def identify_engaged_topics(feedback: list[dict]) -> dict:
    """Extract topics Leo engages with (positive) vs ignores (negative)."""
    engaged: Counter = Counter()
    ignored: Counter = Counter()

    for entry in feedback:
        title = entry.get("title", "").lower()
        words = [w for w in title.split() if len(w) > 3]
        target = engaged if entry.get("positive") else ignored
        target.update(words)

    return {
        "engaged_keywords": dict(engaged.most_common(15)),
        "ignored_keywords": dict(ignored.most_common(15)),
    }


def analyze_time_patterns(feedback: list[dict]) -> dict:
    """Analyze when feedback is given (proxy for reading time)."""
    hour_counts: Counter = Counter()
    day_counts: Counter = Counter()

    for entry in feedback:
        ts = entry.get("ts", "")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts)
            hour_counts[dt.hour] += 1
            day_counts[dt.strftime("%A")] += 1
        except (ValueError, TypeError):
            continue

    peak_hours = [h for h, _ in hour_counts.most_common(3)] if hour_counts else []
    peak_days = [d for d, _ in day_counts.most_common(3)] if day_counts else []

    return {
        "hourly_distribution": dict(sorted(hour_counts.items())),
        "daily_distribution": dict(day_counts.most_common()),
        "peak_hours": peak_hours,
        "peak_days": peak_days,
    }


# ── Weight Adjustment Recommendations ────────────────────────────

def recommend_weight_adjustments(feedback: list[dict],
                                 candidates: list[dict]) -> list[dict]:
    """Generate actionable weight adjustment recommendations."""
    recommendations = []

    # Check source balance
    fb_metrics = compute_feedback_metrics(feedback)
    for src, stats in fb_metrics.get("by_source", {}).items():
        rate = stats.get("positive_rate", 0)
        total = stats.get("total", 0)
        if total >= 3 and rate < 0.3:
            recommendations.append({
                "type": "reduce_source_weight",
                "source": src,
                "reason": f"Low positive rate ({rate:.0%}) across {total} items",
                "suggestion": f"Reduce source_reputation for '{src}' by 0.5",
            })
        elif total >= 5 and rate > 0.8:
            recommendations.append({
                "type": "increase_source_weight",
                "source": src,
                "reason": f"High positive rate ({rate:.0%}) across {total} items",
                "suggestion": f"Increase source_reputation for '{src}' by 0.5",
            })

    # Check topic engagement
    topics = identify_engaged_topics(feedback)
    top_engaged = list(topics["engaged_keywords"].keys())[:5]
    top_ignored = list(topics["ignored_keywords"].keys())[:5]

    if top_engaged:
        recommendations.append({
            "type": "boost_keywords",
            "keywords": top_engaged,
            "reason": "Frequently engaged topics",
            "suggestion": "Consider adding/increasing boost_keywords weights",
        })
    if top_ignored:
        recommendations.append({
            "type": "penalty_keywords",
            "keywords": top_ignored,
            "reason": "Frequently ignored topics",
            "suggestion": "Consider adding/increasing penalty_keywords weights",
        })

    # Check diversity
    diversity = compute_diversity_index(candidates)
    if diversity["normalized_entropy"] < 0.5 and diversity["num_sources"] > 1:
        recommendations.append({
            "type": "increase_diversity",
            "current_entropy": diversity["normalized_entropy"],
            "reason": "Source diversity is low — recommendations are dominated by few sources",
            "suggestion": "Increase min_per_source in diversity config",
        })

    return recommendations


# ── Full Report ──────────────────────────────────────────────────

def generate_report(feeds_dir: str | None = None) -> dict:
    """Generate a complete quality report."""
    feedback = load_feedback(feeds_dir)
    candidates = load_candidates(feeds_dir)
    seen = load_seen(feeds_dir)

    fb_metrics = compute_feedback_metrics(feedback)
    diversity = compute_diversity_index(candidates)
    precision = compute_precision_at_k(candidates, feedback, k=10)
    novelty = compute_novelty_score(candidates, seen)
    low_sources = identify_low_rated_sources(feedback)
    topics = identify_engaged_topics(feedback)
    time_patterns = analyze_time_patterns(feedback)
    adjustments = recommend_weight_adjustments(feedback, candidates)

    return {
        "generated_at": datetime.now(TZ).isoformat(),
        "data_summary": {
            "total_candidates": len(candidates),
            "total_feedback": len(feedback),
            "total_seen": len(seen),
        },
        "quality_metrics": {
            "precision_at_10": precision,
            "novelty_score": novelty,
            "diversity": diversity,
            "feedback": fb_metrics,
        },
        "improvement_areas": {
            "low_rated_sources": low_sources,
            "topic_engagement": topics,
            "time_patterns": time_patterns,
        },
        "weight_adjustments": adjustments,
    }


# ── CLI ──────────────────────────────────────────────────────────

def format_text_report(report: dict) -> str:
    """Format report as human-readable text."""
    lines = []
    lines.append("=" * 60)
    lines.append("Feed Recommendation Quality Report")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append("=" * 60)

    ds = report["data_summary"]
    lines.append(f"\nData: {ds['total_candidates']} candidates, "
                 f"{ds['total_feedback']} feedback, {ds['total_seen']} seen")

    qm = report["quality_metrics"]
    lines.append(f"\n--- Quality Metrics ---")
    lines.append(f"  Precision@10:      {qm['precision_at_10']:.1%}")
    lines.append(f"  Novelty Score:     {qm['novelty_score']:.1%}")
    lines.append(f"  Diversity (norm):  {qm['diversity']['normalized_entropy']:.1%}")
    lines.append(f"  Feedback +rate:    {qm['feedback']['positive_rate']:.1%}")

    fb_src = qm["feedback"].get("by_source", {})
    if fb_src:
        lines.append(f"\n  Feedback by source:")
        for src, stats in fb_src.items():
            lines.append(f"    {src}: {stats['positive']}/{stats['total']} "
                         f"({stats['positive_rate']:.0%} positive)")

    div = qm["diversity"]
    if div["source_distribution"]:
        lines.append(f"\n  Source distribution:")
        for src, info in div["source_distribution"].items():
            lines.append(f"    {src}: {info['count']} ({info['pct']}%)")

    ia = report["improvement_areas"]
    low = ia["low_rated_sources"]
    if low:
        lines.append(f"\n--- Low-Rated Sources ---")
        for entry in low:
            lines.append(f"  {entry['source']}: {entry['positive_rate']:.0%} positive "
                         f"({entry['total_feedback']} items)")
            lines.append(f"    → {entry['suggestion']}")

    topics = ia["topic_engagement"]
    if topics["engaged_keywords"]:
        lines.append(f"\n--- Engaged Topics ---")
        top5 = list(topics["engaged_keywords"].items())[:5]
        lines.append(f"  {', '.join(f'{k}({v})' for k, v in top5)}")
    if topics["ignored_keywords"]:
        lines.append(f"\n--- Ignored Topics ---")
        top5 = list(topics["ignored_keywords"].items())[:5]
        lines.append(f"  {', '.join(f'{k}({v})' for k, v in top5)}")

    tp = ia["time_patterns"]
    if tp["peak_hours"]:
        lines.append(f"\n--- Reading Patterns ---")
        lines.append(f"  Peak hours: {', '.join(f'{h}:00' for h in tp['peak_hours'])}")
    if tp["peak_days"]:
        lines.append(f"  Peak days:  {', '.join(tp['peak_days'])}")

    adj = report["weight_adjustments"]
    if adj:
        lines.append(f"\n--- Recommended Adjustments ---")
        for rec in adj:
            lines.append(f"  [{rec['type']}] {rec['reason']}")
            lines.append(f"    → {rec['suggestion']}")

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze feed recommendation quality and suggest improvements",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--feeds-dir", default=None,
                        help="Override feeds directory (for testing)")
    args = parser.parse_args()

    report = generate_report(feeds_dir=args.feeds_dir)

    if args.json:
        json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        print(format_text_report(report))


if __name__ == "__main__":
    main()
