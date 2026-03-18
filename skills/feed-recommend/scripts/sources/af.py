"""Alignment Forum source plugin — RSS feed."""

import re
import urllib.request
import urllib.error

from .base import BaseSource, Article

AF_FEED_URL = 'https://www.alignmentforum.org/feed.xml'

# Regex-based RSS parsing (AF feed has broken CDATA sometimes)
_ITEM_RE = re.compile(r'<item>(.*?)</item>', re.DOTALL)
_TITLE_RE = re.compile(r'<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>', re.DOTALL)
_LINK_RE = re.compile(r'<link>(.*?)</link>')
_DATE_RE = re.compile(r'<pubDate>(.*?)</pubDate>')
_CREATOR_RE = re.compile(
    r'<dc:creator><!\[CDATA\[(.*?)\]\]></dc:creator>|<dc:creator>(.*?)</dc:creator>',
    re.DOTALL,
)
_DESC_RE = re.compile(
    r'<description><!\[CDATA\[(.*?)\]\]></description>|<description>(.*?)</description>',
    re.DOTALL,
)


def _fetch_url(url: str, max_bytes: int = 500_000) -> str | None:
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (feed-recommend/1.0)'
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read(max_bytes).decode('utf-8', errors='replace')
    except (urllib.error.URLError, OSError):
        return None


def _parse_rss(raw: str, limit: int, source_name: str) -> list[Article]:
    """Parse RSS XML into Article list using regex (handles broken CDATA)."""
    articles = []
    for match in _ITEM_RE.finditer(raw):
        if len(articles) >= limit:
            break
        block = match.group(1)

        t = _TITLE_RE.search(block)
        l = _LINK_RE.search(block)
        d = _DATE_RE.search(block)
        c = _CREATOR_RE.search(block)
        desc = _DESC_RE.search(block)

        title = ((t.group(1) or t.group(2)).strip() if t else '')
        link = l.group(1).strip() if l else ''
        pub_date = d.group(1).strip() if d else ''
        author = ((c.group(1) or c.group(2)).strip() if c else '')
        snippet = ''
        if desc:
            raw_desc = (desc.group(1) or desc.group(2) or '').strip()
            # Strip HTML tags for snippet
            snippet = re.sub(r'<[^>]+>', '', raw_desc)[:200]

        if title and link:
            articles.append(Article(
                source=source_name,
                title=title,
                url=link,
                author=author,
                posted=pub_date,
                snippet=snippet,
                source_id=link,  # use URL as ID for RSS sources
            ))
    return articles


class AlignmentForumSource(BaseSource):

    @property
    def name(self) -> str:
        return "af"

    def fetch(self, limit: int = 20) -> list[Article]:
        raw = _fetch_url(AF_FEED_URL)
        if not raw:
            return []
        return _parse_rss(raw, limit, "af")

    def is_available(self) -> bool:
        raw = _fetch_url(AF_FEED_URL)
        return raw is not None
