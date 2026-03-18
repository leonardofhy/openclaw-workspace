"""Core feed recommendation engine.

Handles source loading, fetching, scoring, dedup, and ranking.
Zero external dependencies — stdlib only.
"""

import json
import os
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'shared'))
from jsonl_store import find_workspace

from sources import discover_sources, Article, ScoredArticle
from sources.base import BaseSource

TZ = timezone(timedelta(hours=8))
WS = find_workspace()
FEEDS_DIR = os.path.join(WS, 'memory', 'feeds')
DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')


# ── Config ───────────────────────────────────────────────────────

def load_config() -> dict:
    """Load config from memory/feeds/config.json, falling back to default."""
    user_cfg = os.path.join(FEEDS_DIR, 'config.json')
    if os.path.exists(user_cfg):
        with open(user_cfg) as f:
            return json.load(f)
    # Copy default config to user location
    with open(DEFAULT_CONFIG_PATH) as f:
        cfg = json.load(f)
    save_config(cfg)
    return cfg


def save_config(cfg: dict) -> None:
    os.makedirs(FEEDS_DIR, exist_ok=True)
    path = os.path.join(FEEDS_DIR, 'config.json')
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.write('\n')
    os.replace(tmp, path)


# ── Source Loading ───────────────────────────────────────────────

def load_sources(config: dict) -> list[BaseSource]:
    """Discover and instantiate enabled sources based on config."""
    available = discover_sources()
    sources = []
    src_cfg = config.get('sources', {})

    for name, cls in available.items():
        settings = src_cfg.get(name, {})
        if not settings.get('enabled', True):
            continue
        instance = cls()
        instance.configure(settings)
        sources.append(instance)

    return sources


def get_all_sources() -> dict[str, type[BaseSource]]:
    """Return all discovered source classes (enabled or not)."""
    return discover_sources()


# ── Fetching ─────────────────────────────────────────────────────

_FETCH_TIMEOUT = 15  # seconds per source


def _fetch_one(source: BaseSource, limit: int) -> list[Article]:
    """Fetch from a single source (called in a thread)."""
    return source.fetch(limit=limit)


def fetch_all(sources: list[BaseSource], limit_per_source: int = 20,
              config: dict | None = None) -> tuple[list[Article], list[dict]]:
    """Fetch articles from all sources concurrently with per-source timeout.

    Returns (articles, errors) where errors is a list of
    {"source": name, "error": message} dicts.
    """
    articles = []
    errors = []
    src_cfg = (config or {}).get('sources', {})

    with ThreadPoolExecutor(max_workers=len(sources) or 1) as executor:
        futures = {}
        for source in sources:
            limit = src_cfg.get(source.name, {}).get('limit', limit_per_source)
            future = executor.submit(_fetch_one, source, limit)
            futures[future] = source

        for future in futures:
            source = futures[future]
            try:
                fetched = future.result(timeout=_FETCH_TIMEOUT)
                articles.extend(fetched)
                print(f"  {source.name}: {len(fetched)} articles", file=sys.stderr)
            except FuturesTimeoutError:
                msg = f"Timeout after {_FETCH_TIMEOUT}s"
                errors.append({"source": source.name, "error": msg})
                print(f"  {source.name}: ERROR {msg}", file=sys.stderr)
            except Exception as e:
                msg = f"{type(e).__name__}: {e}"
                errors.append({"source": source.name, "error": msg})
                print(f"  {source.name}: ERROR {msg}", file=sys.stderr)

    return articles, errors


# ── Snippet Enrichment ───────────────────────────────────────────

class _MetaDescriptionParser(HTMLParser):
    """Extract meta description or first <p> content from HTML."""

    def __init__(self):
        super().__init__()
        self.description = ""
        self._in_p = False
        self._first_p = ""

    def handle_starttag(self, tag, attrs):
        if tag == 'meta':
            attrs_dict = dict(attrs)
            name = attrs_dict.get('name', '').lower()
            prop = attrs_dict.get('property', '').lower()
            if name in ('description', 'og:description') or prop == 'og:description':
                content = attrs_dict.get('content', '').strip()
                if content and not self.description:
                    self.description = content
        if tag == 'p' and not self._first_p:
            self._in_p = True

    def handle_endtag(self, tag):
        if tag == 'p' and self._in_p:
            self._in_p = False

    def handle_data(self, data):
        if self._in_p and not self._first_p:
            text = data.strip()
            if len(text) > 30:
                self._first_p = text


def _fetch_snippet(url: str, timeout: int = 10) -> str:
    """Fetch a URL and extract a text snippet (~200 chars)."""
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; FeedBot/1.0)'})
    with urlopen(req, timeout=timeout) as resp:
        # Read limited amount to avoid huge pages
        html = resp.read(64 * 1024).decode('utf-8', errors='replace')

    parser = _MetaDescriptionParser()
    parser.feed(html)

    text = parser.description or parser._first_p
    if not text:
        return ""
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) > 200:
        text = text[:197] + "..."
    return text


def enrich_snippets(articles: list['ScoredArticle'], max_workers: int = 5,
                    timeout: int = 10) -> None:
    """Fetch snippets for articles with empty snippet fields (in-place)."""
    to_enrich = [(i, sa) for i, sa in enumerate(articles) if not sa.article.snippet]
    if not to_enrich:
        return

    print(f"Enriching {len(to_enrich)} snippets...", file=sys.stderr)

    def _do_fetch(item):
        idx, sa = item
        try:
            snippet = _fetch_snippet(sa.article.url, timeout=timeout)
            return idx, snippet
        except Exception:
            return idx, ""

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for idx, snippet in executor.map(_do_fetch, to_enrich):
            if snippet:
                articles[idx].article.snippet = snippet


# ── Scoring ──────────────────────────────────────────────────────

def load_profile(config: dict | None = None) -> dict:
    """Load interest profile."""
    # Check feeds-specific profile first
    feeds_profile = os.path.join(FEEDS_DIR, 'preferences.json')
    if os.path.exists(feeds_profile):
        with open(feeds_profile) as f:
            return json.load(f)
    # Fall back to path in config
    if config:
        profile_path = config.get('scoring', {}).get('profile_path', '')
        if profile_path:
            full_path = os.path.join(WS, profile_path)
            if os.path.exists(full_path):
                with open(full_path) as f:
                    return json.load(f)
    # Last resort: HN profile
    hn_profile = os.path.join(WS, 'memory', 'hn', 'preferences.json')
    if os.path.exists(hn_profile):
        with open(hn_profile) as f:
            return json.load(f)
    return {}


def _parse_posted_age_hours(posted: str) -> float | None:
    """Try to parse article posted time and return age in hours. None if unparseable."""
    if not posted:
        return None
    now = datetime.now(timezone.utc)
    # Try unix timestamp (HN style)
    try:
        ts = int(posted)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return (now - dt).total_seconds() / 3600
    except (ValueError, OSError):
        pass
    # Try ISO format
    try:
        dt = datetime.fromisoformat(posted)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (now - dt).total_seconds() / 3600
    except ValueError:
        pass
    # Try RFC 2822 (RSS style)
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(posted)
        return (now - dt).total_seconds() / 3600
    except (ValueError, TypeError):
        pass
    return None


def score_article(article: Article, profile: dict) -> float:
    """Score an article based on interest profile. Higher = more relevant."""
    text = f"{article.title} {article.url} {article.snippet}".lower()
    score = 0.0

    # Keyword boost/penalty
    for kw, weight in profile.get('boost_keywords', {}).items():
        if kw.lower() in text:
            score += weight

    for kw, weight in profile.get('penalty_keywords', {}).items():
        if kw.lower() in text:
            score += weight  # already negative

    # Tag-based scoring: match article tags against profile boost_keywords
    boost_kw = profile.get('boost_keywords', {})
    if boost_kw and article.tags:
        boost_kw_lower = {k.lower() for k in boost_kw}
        matched = sum(1 for tag in article.tags if tag.lower() in boost_kw_lower)
        score += matched  # +1 per matching tag

    # Tag-based scoring: match article tags against profile interest_topics
    interest_topics = {t.lower() for t in profile.get('interest_topics', [])}
    if interest_topics and article.tags:
        matched = sum(1 for tag in article.tags if tag.lower() in interest_topics)
        score += matched * 2

    # Score-based bonus (HN points, etc.)
    pts = article.score
    if pts >= 500:
        score += 3
    elif pts >= 200:
        score += 2
    elif pts >= 100:
        score += 1

    # Comment engagement bonus
    if article.comments >= 200:
        score += 1.5
    elif article.comments >= 100:
        score += 1

    # Domain hints
    domain_boosts = {
        'arxiv.org': 2, 'openreview.net': 2,
        'anthropic.com': 2, 'deepmind.com': 2,
        'alignmentforum.org': 2, 'lesswrong.com': 1,
        'transformer-circuits.pub': 3,
        'github.com': 0.5,
    }
    url_lower = article.url.lower()
    for domain, boost in domain_boosts.items():
        if domain in url_lower:
            score += boost
            break

    # Recency bonus
    age_hours = _parse_posted_age_hours(article.posted)
    if age_hours is not None:
        if age_hours <= 24:
            score += 2
        elif age_hours <= 48:
            score += 1

    # Source reputation bonus
    source_reputation = {
        'arxiv': 1,
        'af': 1.5,
        'lw': 0.5,
    }
    score += source_reputation.get(article.source, 0)

    return round(score, 1)


def classify_action(score: float) -> str:
    if score >= 8:
        return "深讀"
    elif score >= 5:
        return "略讀"
    else:
        return "掃標題"


def score_articles(articles: list[Article], profile: dict) -> list[ScoredArticle]:
    """Score all articles and return ScoredArticle list."""
    scored = []
    for article in articles:
        s = score_article(article, profile)
        scored.append(ScoredArticle(
            article=article,
            interest_score=s,
            suggested_action=classify_action(s),
        ))
    return scored


# ── Dedup ────────────────────────────────────────────────────────

def _title_similarity(a: str, b: str) -> float:
    """Simple word-overlap Jaccard similarity."""
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def load_seen(seen_path: str | None = None, max_age_days: int = 7) -> set[str]:
    """Load seen UIDs from JSONL."""
    if seen_path is None:
        seen_path = os.path.join(FEEDS_DIR, 'seen.jsonl')
    seen = set()
    if not os.path.exists(seen_path):
        return seen
    cutoff = datetime.now(TZ) - timedelta(days=max_age_days)
    with open(seen_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                ts = datetime.fromisoformat(entry['ts'])
                if ts >= cutoff:
                    seen.add(entry['id'])
                    # Also add URL if present for cross-source matching
                    if 'url' in entry:
                        seen.add(entry['url'])
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
    return seen


def dedup(articles: list[Article], seen_path: str | None = None,
          title_threshold: float = 0.85) -> list[Article]:
    """Cross-source dedup by URL, UID, and title similarity."""
    seen = load_seen(seen_path)
    result = []
    seen_urls: set[str] = set()
    seen_titles: list[str] = []

    for article in articles:
        # Skip if UID or URL already seen
        if article.uid() in seen or article.url in seen:
            continue
        if article.url in seen_urls:
            continue

        # Title similarity check against already-accepted articles
        is_dup = False
        for prev_title in seen_titles:
            if _title_similarity(article.title, prev_title) >= title_threshold:
                is_dup = True
                break
        if is_dup:
            continue

        result.append(article)
        seen_urls.add(article.url)
        seen_titles.append(article.title)

    return result


# ── Recommend ────────────────────────────────────────────────────

def recommend(articles: list[Article], profile: dict,
              limit: int = 10, seen_path: str | None = None,
              title_threshold: float = 0.85) -> list[ScoredArticle]:
    """Full pipeline: dedup → score → rank → top-N."""
    deduped = dedup(articles, seen_path=seen_path, title_threshold=title_threshold)
    scored = score_articles(deduped, profile)
    scored.sort(key=lambda x: x.interest_score, reverse=True)
    return scored[:limit]


# ── Seen / Feedback ──────────────────────────────────────────────

def mark_seen(uids: list[str], urls: list[str] | None = None) -> None:
    """Mark article UIDs as seen."""
    os.makedirs(FEEDS_DIR, exist_ok=True)
    seen_path = os.path.join(FEEDS_DIR, 'seen.jsonl')
    now = datetime.now(TZ).isoformat()
    with open(seen_path, 'a') as f:
        for uid in uids:
            entry = {"id": uid, "ts": now}
            f.write(json.dumps(entry) + '\n')
        if urls:
            for url in urls:
                entry = {"id": url, "url": url, "ts": now}
                f.write(json.dumps(entry) + '\n')


def record_feedback(uid: str, positive: bool, title: str = "",
                    source: str = "") -> None:
    """Record feedback for an article."""
    os.makedirs(FEEDS_DIR, exist_ok=True)
    fb_path = os.path.join(FEEDS_DIR, 'feedback.jsonl')
    entry = {
        "id": uid,
        "source": source,
        "positive": positive,
        "title": title,
        "ts": datetime.now(TZ).isoformat(),
    }
    with open(fb_path, 'a') as f:
        f.write(json.dumps(entry) + '\n')


def get_stats() -> dict:
    """Aggregate stats across all sources."""
    seen_path = os.path.join(FEEDS_DIR, 'seen.jsonl')
    fb_path = os.path.join(FEEDS_DIR, 'feedback.jsonl')

    seen_count = len(load_seen(seen_path))

    by_source: Counter = Counter()
    fb_pos = fb_neg = 0
    if os.path.exists(fb_path):
        with open(fb_path) as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    src = entry.get('source', 'unknown')
                    by_source[src] += 1
                    if entry.get('positive'):
                        fb_pos += 1
                    else:
                        fb_neg += 1
                except (json.JSONDecodeError, KeyError):
                    continue

    return {
        "seen_7d": seen_count,
        "feedback_total": fb_pos + fb_neg,
        "feedback_positive": fb_pos,
        "feedback_negative": fb_neg,
        "feedback_by_source": dict(by_source),
    }
