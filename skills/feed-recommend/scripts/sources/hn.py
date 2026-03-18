"""Hacker News source plugin — Firebase API."""

import json
import urllib.request
import urllib.error

from .base import BaseSource, Article


def _fetch_url(url: str, max_bytes: int = 500_000) -> str | None:
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (feed-recommend/1.0)'
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read(max_bytes).decode('utf-8', errors='replace')
    except (urllib.error.URLError, OSError):
        return None


class HackerNewsSource(BaseSource):

    @property
    def name(self) -> str:
        return "hn"

    def fetch(self, limit: int = 50) -> list[Article]:
        raw = _fetch_url('https://hacker-news.firebaseio.com/v0/topstories.json')
        if not raw:
            return []
        try:
            story_ids = json.loads(raw)[:limit]
        except json.JSONDecodeError:
            return []

        articles = []
        for sid in story_ids:
            raw_item = _fetch_url(f'https://hacker-news.firebaseio.com/v0/item/{sid}.json')
            if not raw_item:
                continue
            try:
                item = json.loads(raw_item)
                if item.get('type') != 'story':
                    continue
                articles.append(Article(
                    source="hn",
                    title=item.get('title', ''),
                    url=item.get('url', f"https://news.ycombinator.com/item?id={sid}"),
                    author=item.get('by', ''),
                    score=item.get('score', 0),
                    comments=item.get('descendants', 0),
                    posted=str(item.get('time', '')),
                    source_id=str(sid),
                ))
            except json.JSONDecodeError:
                continue
        return articles

    def is_available(self) -> bool:
        raw = _fetch_url('https://hacker-news.firebaseio.com/v0/topstories.json?limitToFirst=1')
        return raw is not None
