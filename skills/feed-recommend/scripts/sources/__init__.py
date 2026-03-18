"""Auto-discover source plugins in this package.

Any module in this directory that defines a class extending BaseSource
will be automatically discovered by discover_sources().
"""

import importlib
import pkgutil
from pathlib import Path

from .base import BaseSource, Article, ScoredArticle


def discover_sources() -> dict[str, type[BaseSource]]:
    """Scan this package for BaseSource subclasses. Returns {name: class}."""
    sources: dict[str, type[BaseSource]] = {}
    package_dir = Path(__file__).parent

    for info in pkgutil.iter_modules([str(package_dir)]):
        if info.name == 'base':
            continue
        try:
            module = importlib.import_module(f'.{info.name}', package=__package__)
        except ImportError:
            continue
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type)
                    and issubclass(attr, BaseSource)
                    and attr is not BaseSource):
                instance = attr()
                sources[instance.name] = attr
    return sources


__all__ = ['BaseSource', 'Article', 'ScoredArticle', 'discover_sources']
