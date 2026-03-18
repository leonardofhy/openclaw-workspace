"""Base class for feed source plugins."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class Article:
    """Unified article representation across all sources."""
    source: str
    title: str
    url: str
    author: str = ""
    score: int = 0
    comments: int = 0
    posted: str = ""
    snippet: str = ""
    tags: list[str] = field(default_factory=list)
    # Internal fields
    source_id: str = ""  # source-specific ID (e.g. HN story ID)

    def uid(self) -> str:
        """Unique identifier: source:source_id or source:url."""
        if self.source_id:
            return f"{self.source}:{self.source_id}"
        return f"{self.source}:{self.url}"

    def to_dict(self) -> dict:
        d = asdict(self)
        d['uid'] = self.uid()
        return d


@dataclass
class ScoredArticle:
    """Article with interest score attached."""
    article: Article
    interest_score: float = 0.0
    suggested_action: str = ""

    def to_dict(self) -> dict:
        d = self.article.to_dict()
        d['interest_score'] = self.interest_score
        d['suggested_action'] = self.suggested_action
        return d


class BaseSource(ABC):
    """Abstract base class for feed sources.

    To add a new source:
      1. Create a .py file in sources/
      2. Define a class extending BaseSource
      3. Implement name, fetch(), is_available()
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier (e.g. 'hn', 'af', 'lw')."""
        ...

    @abstractmethod
    def fetch(self, limit: int = 20) -> list[Article]:
        """Fetch articles from this source. Returns list of Article."""
        ...

    def is_available(self) -> bool:
        """Check if this source is reachable. Default: True."""
        return True

    def configure(self, settings: dict) -> None:
        """Apply per-source settings from config. Override if needed."""
        pass
