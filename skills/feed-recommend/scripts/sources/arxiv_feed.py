"""arXiv source plugin — RSS/Atom feed for configurable categories."""

import re
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

from .base import BaseSource, Article

ARXIV_RSS_BASE = 'https://rss.arxiv.org/rss/'

# Atom namespace
_NS = {'atom': 'http://www.w3.org/2005/Atom'}


def _fetch_url(url: str, max_bytes: int = 1_000_000) -> str | None:
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (feed-recommend/1.0)'
        })
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read(max_bytes).decode('utf-8', errors='replace')
    except (urllib.error.URLError, OSError):
        return None


class ArxivSource(BaseSource):

    def __init__(self):
        self._categories: list[str] = ["cs.CL", "cs.SD", "cs.AI", "cs.LG"]

    @property
    def name(self) -> str:
        return "arxiv"

    def configure(self, settings: dict) -> None:
        if 'categories' in settings:
            self._categories = settings['categories']

    def fetch(self, limit: int = 30) -> list[Article]:
        articles = []
        per_cat = max(limit // len(self._categories), 5) if self._categories else limit

        for cat in self._categories:
            url = f"{ARXIV_RSS_BASE}{cat}"
            raw = _fetch_url(url)
            if not raw:
                continue
            articles.extend(self._parse_feed(raw, per_cat, cat))

        return articles[:limit]

    def _parse_feed(self, raw: str, limit: int, category: str) -> list[Article]:
        """Parse arXiv RSS (which is RSS 2.0 format)."""
        articles = []
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            return self._parse_feed_regex(raw, limit, category)

        # arXiv RSS 2.0: /rss/channel/item
        channel = root.find('channel')
        if channel is None:
            return self._parse_feed_regex(raw, limit, category)

        for item in channel.findall('item'):
            if len(articles) >= limit:
                break
            title = (item.findtext('title') or '').strip()
            link = (item.findtext('link') or '').strip()
            description = (item.findtext('description') or '').strip()
            # Clean HTML from description
            snippet = re.sub(r'<[^>]+>', '', description)[:200]
            # Extract author from dc:creator or description
            author = (item.findtext('{http://purl.org/dc/elements/1.1/}creator') or '').strip()

            if title and link:
                # Extract arXiv ID from URL
                arxiv_id = link.rsplit('/', 1)[-1] if '/abs/' in link else link
                articles.append(Article(
                    source="arxiv",
                    title=title,
                    url=link,
                    author=author,
                    snippet=snippet,
                    tags=[category],
                    source_id=arxiv_id,
                ))
        return articles

    def _parse_feed_regex(self, raw: str, limit: int, category: str) -> list[Article]:
        """Fallback regex parsing for malformed XML."""
        articles = []
        item_re = re.compile(r'<item>(.*?)</item>', re.DOTALL)
        title_re = re.compile(r'<title>(.*?)</title>', re.DOTALL)
        link_re = re.compile(r'<link>(.*?)</link>')

        for match in item_re.finditer(raw):
            if len(articles) >= limit:
                break
            block = match.group(1)
            t = title_re.search(block)
            l = link_re.search(block)
            title = t.group(1).strip() if t else ''
            link = l.group(1).strip() if l else ''
            if title and link:
                arxiv_id = link.rsplit('/', 1)[-1] if '/abs/' in link else link
                articles.append(Article(
                    source="arxiv",
                    title=title,
                    url=link,
                    tags=[category],
                    source_id=arxiv_id,
                ))
        return articles
