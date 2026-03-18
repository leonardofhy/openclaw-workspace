"""Hacker News source plugin — Algolia search API (single request)."""

import json
import urllib.request
import urllib.error
from urllib.parse import urlparse

from .base import BaseSource, Article

_ALGOLIA_URL = 'https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage={limit}'


def _fetch_url(url: str, max_bytes: int = 500_000) -> str | None:
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (feed-recommend/1.0)'
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read(max_bytes).decode('utf-8', errors='replace')
    except (urllib.error.URLError, OSError):
        return None


def _tags_from_url(url: str) -> list[str]:
    """Infer tags from article URL domain."""
    try:
        domain = urlparse(url).netloc.lower()
    except Exception:
        return []
    # Strip www. prefix
    if domain.startswith('www.'):
        domain = domain[4:]
    domain_tags = {
        'github.com': ['github', 'opensource'],
        'arxiv.org': ['arxiv', 'research'],
        'blog.google': ['google'],
        'openai.com': ['openai'],
        'anthropic.com': ['anthropic'],
        'deepmind.com': ['deepmind'],
        'huggingface.co': ['huggingface', 'ml'],
    }
    return domain_tags.get(domain, [domain.split('.')[0]])


class HackerNewsSource(BaseSource):

    @property
    def name(self) -> str:
        return "hn"

    def fetch(self, limit: int = 50) -> list[Article]:
        raw = _fetch_url(_ALGOLIA_URL.format(limit=limit))
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []

        articles = []
        for hit in data.get('hits', []):
            url = hit.get('url') or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
            articles.append(Article(
                source="hn",
                title=hit.get('title', ''),
                url=url,
                author=hit.get('author', ''),
                score=hit.get('points', 0) or 0,
                comments=hit.get('num_comments', 0) or 0,
                posted=str(hit.get('created_at_i', '')),
                source_id=str(hit.get('objectID', '')),
                tags=_tags_from_url(url),
            ))
        return articles

    def is_available(self) -> bool:
        raw = _fetch_url(_ALGOLIA_URL.format(limit=1))
        return raw is not None
