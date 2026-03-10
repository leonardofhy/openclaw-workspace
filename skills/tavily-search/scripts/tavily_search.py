#!/usr/bin/env python3
"""Tavily web search CLI.

Requires API key:
- env var: TAVILY_API_KEY
- OR secrets file: secrets/tavily.env with line: TAVILY_API_KEY=...

Examples:
  python3 skills/tavily-search/scripts/tavily_search.py --query "ARENA 8.0 application" \
    --max-results 5 --search-depth advanced --include-answer

  python3 skills/tavily-search/scripts/tavily_search.py --query "Octopus card add value" --format md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[3]


def eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def load_api_key() -> str:
    key = os.environ.get("TAVILY_API_KEY", "").strip()
    if key:
        return key

    env_path = WORKSPACE / "secrets" / "tavily.env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == "TAVILY_API_KEY":
                return v.strip().strip('"').strip("'")
    return ""


def tavily_search(
    api_key: str,
    query: str,
    max_results: int,
    search_depth: str,
    include_answer: bool,
    include_raw_content: bool,
    include_images: bool,
) -> dict:
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": search_depth,
        "include_answer": include_answer,
        "include_raw_content": include_raw_content,
        "include_images": include_images,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return json.loads(body)


def to_markdown(result: dict) -> str:
    lines: list[str] = []
    ans = result.get("answer")
    if ans:
        lines.append(ans.strip())
        lines.append("")

    items = result.get("results") or []
    for i, it in enumerate(items, start=1):
        title = (it.get("title") or "").strip() or "(no title)"
        url = (it.get("url") or "").strip()
        content = (it.get("content") or "").strip()
        score = it.get("score")

        header = f"{i}. {title}"
        if url:
            header += f"\n   {url}"
        if score is not None:
            header += f"\n   score: {score}"
        lines.append(header)
        if content:
            lines.append(f"\n   {content}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Tavily web search")
    p.add_argument("--query", required=True)
    p.add_argument("--max-results", type=int, default=5)
    p.add_argument("--search-depth", choices=["basic", "advanced"], default="basic")
    p.add_argument("--include-answer", action="store_true")
    p.add_argument("--include-raw-content", action="store_true")
    p.add_argument("--include-images", action="store_true")
    p.add_argument("--format", choices=["json", "md"], default="json")
    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.max_results <= 0:
        eprint("ERROR: --max-results must be > 0")
        return 2

    api_key = load_api_key()
    if not api_key:
        eprint("ERROR: Tavily API key missing. Set env TAVILY_API_KEY or create secrets/tavily.env")
        return 2

    try:
        result = tavily_search(
            api_key=api_key,
            query=args.query,
            max_results=args.max_results,
            search_depth=args.search_depth,
            include_answer=args.include_answer,
            include_raw_content=args.include_raw_content,
            include_images=args.include_images,
        )
    except Exception as e:  # noqa: BLE001
        eprint(f"ERROR: {e}")
        return 1

    if args.format == "md":
        print(to_markdown(result), end="")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
