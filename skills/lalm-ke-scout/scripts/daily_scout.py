#!/usr/bin/env python3
"""LALM-KE Daily Paper Scout — find new papers on Knowledge Editing × Audio LMs.

Usage:
    python3 daily_scout.py                  # run normally, save to default output dir
    python3 daily_scout.py --dry-run        # fetch and score but don't write files
    python3 daily_scout.py --limit 20       # top 20 papers (default: 10)
    python3 daily_scout.py --output-dir /path/to/dir
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# ─── Path setup: import from leo-feed-digest ───────────────────────────────

FEED_DIGEST_PATH = Path.home() / "Workspace" / "leo-feed-digest"
if FEED_DIGEST_PATH.exists():
    sys.path.insert(0, str(FEED_DIGEST_PATH))

WORKSPACE = Path.home() / ".openclaw" / "workspace"
DEFAULT_OUTPUT_DIR = WORKSPACE / "memory" / "lalm-ke" / "daily"
PREFS_PATH = FEED_DIGEST_PATH / "data" / "preferences_lalm_ke.json"

TZ = timezone(timedelta(hours=8))

# ─── arXiv API targeted search terms ─────────────────────────────────────────

ARXIV_SEARCH_QUERIES = [
    'all:"knowledge editing" AND (all:"language model" OR all:"large language model")',
    'all:"model editing" AND all:factual',
    'all:"knowledge neurons"',
    'all:"audio language model" OR all:LALM OR all:SALMONN OR all:WavLLM',
    'all:"speech language model" AND (all:knowledge OR all:editing OR all:factual)',
]

ARXIV_API_BASE = "http://export.arxiv.org/api/query"
ARXIV_RSS_BASE = "https://rss.arxiv.org/rss/"
ARXIV_CATEGORIES = ["cs.CL", "cs.SD", "cs.AI", "cs.LG", "cs.IR"]

# ─── Lightweight Article dataclass (fallback if imports fail) ─────────────────

class Article:
    __slots__ = ("source", "title", "url", "author", "snippet", "tags", "source_id", "extra")

    def __init__(self, source="", title="", url="", author="",
                 snippet="", tags=None, source_id="", extra=None):
        self.source = source
        self.title = title
        self.url = url
        self.author = author
        self.snippet = snippet
        self.tags = tags or []
        self.source_id = source_id
        self.extra = extra or {}


# ─── Scoring ──────────────────────────────────────────────────────────────────

def load_profile(prefs_path: Path) -> dict:
    if prefs_path.exists():
        with open(prefs_path) as f:
            return json.load(f)
    print(f"[WARN] Preferences not found at {prefs_path}, using empty profile")
    return {"boost_keywords": {}, "penalty_keywords": {}}


def keyword_score(text: str, profile: dict) -> float:
    """Score text against boost/penalty keywords (case-insensitive)."""
    text_lower = text.lower()
    score = 0.0
    boost_kw = sorted(profile.get("boost_keywords", {}).items(), key=lambda x: -len(x[0]))
    for kw, pts in boost_kw:
        if kw.lower() in text_lower:
            score += pts
    for kw, pts in profile.get("penalty_keywords", {}).items():
        if kw.lower() in text_lower:
            score += pts  # pts is negative
    return score


def score_article_with_profile(article: Article, profile: dict) -> float:
    """Score an article against the LALM-KE profile."""
    full_text = f"{article.title} {article.snippet} {' '.join(article.tags)}"
    return keyword_score(full_text, profile)


# ─── arXiv RSS fetch ──────────────────────────────────────────────────────────

def fetch_arxiv_rss(category: str, limit: int = 30) -> list[Article]:
    """Fetch arXiv RSS feed for a category."""
    url = f"{ARXIV_RSS_BASE}{category}"
    try:
        req = Request(url, headers={"User-Agent": "lalm-ke-scout/1.0"})
        with urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except (URLError, HTTPError) as e:
        print(f"[WARN] RSS fetch failed for {category}: {e}")
        return []

    articles = []
    try:
        root = ET.fromstring(raw)
        channel = root.find("channel")
        if channel is None:
            return []
        for item in channel.findall("item"):
            if len(articles) >= limit:
                break
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            description = (item.findtext("description") or "").strip()
            snippet = re.sub(r"<[^>]+>", "", description)[:400]
            author = (item.findtext("{http://purl.org/dc/elements/1.1/}creator") or "").strip()
            if title and link:
                arxiv_id = link.rsplit("/", 1)[-1] if "/abs/" in link else link
                articles.append(Article(
                    source="arxiv_rss",
                    title=title,
                    url=link,
                    author=author,
                    snippet=snippet,
                    tags=[category],
                    source_id=arxiv_id,
                ))
    except ET.ParseError as e:
        print(f"[WARN] XML parse error for {category}: {e}")

    return articles


def fetch_all_rss(categories: list[str], limit_per_cat: int = 30) -> list[Article]:
    """Fetch RSS from all categories."""
    articles = []
    for cat in categories:
        arts = fetch_arxiv_rss(cat, limit_per_cat)
        articles.extend(arts)
        print(f"  [RSS] {cat}: {len(arts)} articles")
    return articles


# ─── arXiv API targeted search ───────────────────────────────────────────────

def fetch_arxiv_api(query: str, max_results: int = 20) -> list[Article]:
    """Query arXiv API for a specific search term."""
    params = urllib.parse.urlencode({
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    })
    url = f"{ARXIV_API_BASE}?{params}"

    try:
        req = Request(url, headers={"User-Agent": "lalm-ke-scout/1.0"})
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except (URLError, HTTPError) as e:
        print(f"[WARN] arXiv API query failed: {e}")
        return []

    articles = []
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    try:
        root = ET.fromstring(raw)
        for entry in root.findall("atom:entry", ns):
            title = (entry.findtext("atom:title", namespaces=ns) or "").strip()
            title = re.sub(r"\s+", " ", title)
            link_el = entry.find("atom:link[@rel='alternate']", ns)
            url_val = link_el.attrib.get("href", "") if link_el is not None else ""
            if not url_val:
                for l in entry.findall("atom:link", ns):
                    if l.attrib.get("type") == "text/html":
                        url_val = l.attrib.get("href", "")
                        break
            abstract = (entry.findtext("atom:summary", namespaces=ns) or "").strip()
            abstract = re.sub(r"\s+", " ", abstract)[:400]
            # Authors
            authors = []
            for auth_el in entry.findall("atom:author", ns):
                name = auth_el.findtext("atom:name", namespaces=ns)
                if name:
                    authors.append(name.strip())
            # Categories
            cats = [c.attrib.get("term", "") for c in entry.findall("atom:category", ns)]

            # arXiv ID
            id_el = entry.findtext("atom:id", namespaces=ns) or ""
            arxiv_id = id_el.rsplit("/", 1)[-1] if "/" in id_el else id_el
            # Strip version suffix
            arxiv_id = re.sub(r"v\d+$", "", arxiv_id)

            if title and url_val:
                articles.append(Article(
                    source="arxiv_api",
                    title=title,
                    url=url_val,
                    author=", ".join(authors[:3]),
                    snippet=abstract,
                    tags=cats,
                    source_id=arxiv_id,
                ))
    except ET.ParseError as e:
        print(f"[WARN] arXiv API XML parse error: {e}")

    return articles


def fetch_all_api_queries(queries: list[str], max_per_query: int = 15, delay: float = 3.0) -> list[Article]:
    """Run all targeted queries with rate-limit delay."""
    all_articles = []
    for i, q in enumerate(queries):
        if i > 0:
            time.sleep(delay)
        arts = fetch_arxiv_api(q, max_per_query)
        print(f"  [API] Query {i+1}/{len(queries)}: {len(arts)} results — {q[:60]}...")
        all_articles.extend(arts)
    return all_articles


# ─── Dedup ────────────────────────────────────────────────────────────────────

def dedup_articles(articles: list[Article]) -> list[Article]:
    """Dedup by arXiv ID (normalised), preserving first occurrence."""
    seen_ids = set()
    seen_urls = set()
    out = []
    for a in articles:
        norm_id = re.sub(r"v\d+$", "", a.source_id.strip())
        if norm_id and norm_id in seen_ids:
            continue
        if a.url and a.url in seen_urls:
            continue
        if norm_id:
            seen_ids.add(norm_id)
        if a.url:
            seen_urls.add(a.url)
        out.append(a)
    return out


# ─── Try to use feed_engine's scorer if available ─────────────────────────────

def try_import_feed_engine():
    """Try to import feed_engine's score_articles. Return None if unavailable."""
    try:
        from core.scoring import score_articles  # noqa
        return score_articles
    except ImportError:
        return None


# ─── Output generation ────────────────────────────────────────────────────────

def make_relevance_note(article: Article, profile: dict) -> str:
    """Generate a 1-line relevance note based on matched keywords."""
    text_lower = (article.title + " " + article.snippet).lower()
    ke_hits = [k for k in [
        "knowledge editing", "model editing", "ROME", "MEMIT", "MEND", "SERAC", "GRACE",
        "knowledge neurons", "locate-and-edit", "factual"
    ] if k.lower() in text_lower]
    lalm_hits = [k for k in [
        "audio language model", "speech language model", "SALMONN", "Qwen-Audio",
        "WavLLM", "SLAM-LLM", "AudioPaLM", "LALM", "audio LLM", "spoken language"
    ] if k.lower() in text_lower]
    parts = []
    if ke_hits:
        parts.append(f"KE: {', '.join(ke_hits[:3])}")
    if lalm_hits:
        parts.append(f"LALM: {', '.join(lalm_hits[:2])}")
    if parts:
        return " | ".join(parts)
    return "Matched boost keywords in abstract"


def build_json_output(articles: list[Article], scores: list[float], today: str, total_found: int) -> dict:
    """Build structured JSON output."""
    papers = []
    for art, score in zip(articles, scores):
        papers.append({
            "rank": len(papers) + 1,
            "title": art.title,
            "url": art.url,
            "authors": art.author,
            "categories": art.tags,
            "abstract_snippet": art.snippet[:300],
            "score": round(score, 2),
            "arxiv_id": art.source_id,
            "source": art.source,
        })
    return {
        "date": today,
        "generated_at": datetime.now(TZ).isoformat(),
        "total_found": total_found,
        "shown": len(papers),
        "papers": papers,
    }


def build_markdown(articles: list[Article], scores: list[float], today: str,
                   total_found: int, profile: dict) -> str:
    """Build markdown summary."""
    lines = [
        f"# LALM-KE Daily Scout — {today}",
        "",
        f"## Top Papers ({total_found} found, {len(articles)} shown)",
        "",
    ]
    for i, (art, score) in enumerate(zip(articles, scores), 1):
        cats = ", ".join(art.tags[:5]) if art.tags else "—"
        snippet = art.snippet[:200].replace("\n", " ")
        relevance = make_relevance_note(art, profile)
        lines += [
            f"### {i}. [{art.title}]({art.url}) — Score: {score:.2f}",
            f"**Authors:** {art.author or '—'}",
            f"**Categories:** {cats}",
            f"**Abstract snippet:** {snippet}...",
            f"**Relevance:** {relevance}",
            "",
        ]
    lines += [
        "---",
        f"*Generated by lalm-ke-scout on {datetime.now(TZ).strftime('%Y-%m-%d %H:%M %Z')}*",
    ]
    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="LALM-KE Daily Paper Scout")
    parser.add_argument("--limit", type=int, default=10, help="Number of top papers to show (default: 10)")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and score but don't write files")
    parser.add_argument("--output-dir", type=str, default=str(DEFAULT_OUTPUT_DIR),
                        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--no-rss", action="store_true", help="Skip RSS feed fetch")
    parser.add_argument("--no-api", action="store_true", help="Skip arXiv API queries")
    args = parser.parse_args()

    today = date.today().isoformat()
    output_dir = Path(args.output_dir)

    print(f"=== LALM-KE Daily Paper Scout — {today} ===")
    print(f"Preferences: {PREFS_PATH}")
    profile = load_profile(PREFS_PATH)
    print(f"Loaded profile: {len(profile.get('boost_keywords', {}))} boost keywords, "
          f"{len(profile.get('penalty_keywords', {}))} penalty keywords")

    # 1. Fetch from arXiv RSS
    all_articles: list[Article] = []

    if not args.no_rss:
        print("\n[1/2] Fetching arXiv RSS feeds...")
        rss_articles = fetch_all_rss(ARXIV_CATEGORIES, limit_per_cat=40)
        all_articles.extend(rss_articles)
        print(f"  RSS total: {len(rss_articles)} articles")

    # 2. Targeted arXiv API search
    if not args.no_api:
        print("\n[2/2] Running targeted arXiv API queries (3s delay between queries)...")
        api_articles = fetch_all_api_queries(ARXIV_SEARCH_QUERIES, max_per_query=20, delay=3.0)
        all_articles.extend(api_articles)
        print(f"  API total: {len(api_articles)} articles")

    # 3. Dedup
    all_articles = dedup_articles(all_articles)
    total_found = len(all_articles)
    print(f"\nAfter dedup: {total_found} unique articles")

    if total_found == 0:
        print("[WARN] No articles found. Check network or try --no-rss / --no-api.")
        sys.exit(0)

    # 4. Score
    scores = [score_article_with_profile(a, profile) for a in all_articles]

    # 5. Filter: only articles with score > 0
    scored_pairs = [(a, s) for a, s in zip(all_articles, scores) if s > 0]
    scored_pairs.sort(key=lambda x: -x[1])
    print(f"Articles with score > 0: {len(scored_pairs)}")

    top_articles = [p[0] for p in scored_pairs[:args.limit]]
    top_scores = [p[1] for p in scored_pairs[:args.limit]]

    # 6. Build output
    json_out = build_json_output(top_articles, top_scores, today, total_found)
    md_out = build_markdown(top_articles, top_scores, today, total_found, profile)

    # 7. Print preview
    print(f"\n{'='*60}")
    print(f"TOP {len(top_articles)} PAPERS:")
    for i, (art, score) in enumerate(zip(top_articles, top_scores), 1):
        print(f"  {i:2d}. [{score:6.2f}] {art.title[:70]}")
    print(f"{'='*60}")

    if args.dry_run:
        print("\n[dry-run] Skipping file writes.")
        print("\n--- Markdown preview ---")
        print(md_out[:1500])
        print("--- end ---")
        return

    # 8. Save files
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{today}.json"
    md_path = output_dir / f"{today}.md"

    with open(json_path, "w") as f:
        json.dump(json_out, f, indent=2, ensure_ascii=False)
    with open(md_path, "w") as f:
        f.write(md_out)

    print(f"\n[OK] Saved JSON: {json_path}")
    print(f"[OK] Saved MD:   {md_path}")


if __name__ == "__main__":
    main()
