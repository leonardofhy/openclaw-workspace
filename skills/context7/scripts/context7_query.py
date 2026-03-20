#!/usr/bin/env python3
"""Context7 documentation query CLI.

Queries context7.com for up-to-date library documentation.
No API key required.

Examples:
  python3 skills/context7/scripts/context7_query.py search --query "pytorch"
  python3 skills/context7/scripts/context7_query.py docs --library "/pytorch/pytorch" --topic "DataLoader"
  python3 skills/context7/scripts/context7_query.py docs --library "/huggingface/transformers" --format md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[3]
CACHE_DIR = WORKSPACE / "memory" / "context7-cache"
CACHE_TTL_SECONDS = 24 * 3600

API_BASE = "https://context7.com/api/v1"


def eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _get(url: str, timeout: int = 30) -> dict:
    """GET url, return parsed JSON. Raises urllib.error.URLError on network failure."""
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "openclaw-context7/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    return json.loads(body)


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


def _cache_key(library: str, topic: str, tokens: int) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]", "_", library.strip("/"))
    topic_slug = re.sub(r"[^a-zA-Z0-9_-]", "_", topic) if topic else "all"
    raw = f"{library}|{topic}|{tokens}"
    short_hash = hashlib.sha1(raw.encode()).hexdigest()[:8]
    return f"{slug}/{topic_slug}_{short_hash}"


def cache_load(key: str) -> dict | None:
    """Return cached payload if fresh, else None."""
    path = CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - data.get("cached_at", 0) < CACHE_TTL_SECONDS:
            return data["payload"]
    except (json.JSONDecodeError, KeyError, OSError):
        pass
    return None


def cache_save(key: str, payload: dict) -> None:
    """Write payload to cache."""
    path = CACHE_DIR / f"{key}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"cached_at": time.time(), "payload": payload}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------


def search_library(query: str) -> dict:
    """Search context7 for a library; returns raw API response."""
    params = urllib.parse.urlencode({"q": query})
    return _get(f"{API_BASE}/search?{params}")


def get_docs(library: str, topic: str = "", tokens: int = 10000, use_cache: bool = True) -> dict:
    """Fetch documentation for a library. Returns raw API response."""
    cache_key = _cache_key(library, topic, tokens)
    if use_cache:
        cached = cache_load(cache_key)
        if cached is not None:
            return cached

    params: dict[str, str | int] = {"tokens": tokens}
    if topic:
        params["topic"] = topic
    qs = urllib.parse.urlencode(params)
    url = f"{API_BASE}/{library.strip('/')}/llms.txt?{qs}"
    result = _get(url)

    if use_cache:
        cache_save(cache_key, result)
    return result


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def search_to_markdown(data: dict) -> str:
    results = data.get("results") or []
    if not results:
        return "No libraries found.\n"
    lines = []
    for item in results:
        lib_id = item.get("id") or item.get("library_id") or ""
        name = item.get("name") or item.get("title") or lib_id
        desc = (item.get("description") or "").strip()
        version = item.get("version") or ""
        line = f"- `{lib_id}` — **{name}**"
        if version:
            line += f" (v{version})"
        if desc:
            line += f"\n  {desc}"
        lines.append(line)
    return "\n".join(lines) + "\n"


def docs_to_markdown(data: dict) -> str:
    # Context7 llms.txt endpoint returns either a string body or a JSON object
    # with a `content` or `text` field.
    if isinstance(data, str):
        return data if data.endswith("\n") else data + "\n"
    content = data.get("content") or data.get("text") or ""
    if not content:
        return json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    return content if content.endswith("\n") else content + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Query Context7 for up-to-date library documentation"
    )
    sub = p.add_subparsers(dest="command", required=True)

    # search
    s = sub.add_parser("search", help="Search for a library and get its Context7 ID")
    s.add_argument("--query", required=True, help="Library name to search for")
    s.add_argument("--format", choices=["json", "md"], default="md")

    # docs
    d = sub.add_parser("docs", help="Fetch documentation for a library")
    d.add_argument("--library", required=True, help="Context7 library ID (e.g. /pytorch/pytorch)")
    d.add_argument("--topic", default="", help="Focus topic / function name")
    d.add_argument("--tokens", type=int, default=10000, help="Max tokens to return (default 10000)")
    d.add_argument("--format", choices=["json", "md"], default="md")
    d.add_argument("--no-cache", action="store_true", help="Bypass local cache")

    return p


def cmd_search(args: argparse.Namespace) -> int:
    try:
        data = search_library(args.query)
    except Exception as e:  # noqa: BLE001
        eprint(f"ERROR: {e}")
        return 1
    if args.format == "md":
        print(search_to_markdown(data), end="")
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def cmd_docs(args: argparse.Namespace) -> int:
    if args.tokens <= 0:
        eprint("ERROR: --tokens must be > 0")
        return 2
    try:
        data = get_docs(
            library=args.library,
            topic=args.topic,
            tokens=args.tokens,
            use_cache=not args.no_cache,
        )
    except Exception as e:  # noqa: BLE001
        eprint(f"ERROR: {e}")
        return 1
    if args.format == "md":
        print(docs_to_markdown(data), end="")
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "search":
        return cmd_search(args)
    if args.command == "docs":
        return cmd_docs(args)
    eprint(f"ERROR: unknown command {args.command!r}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
