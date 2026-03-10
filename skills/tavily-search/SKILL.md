---
name: tavily-search
description: >
  Use Tavily API to run web search (query → top results, optional answer) when Leo asks to search the web beyond simple web_fetch.
  Trigger phrases: "用 Tavily 查", "tavily search", "幫我網搜", "幫我查最新消息".
  Requires TAVILY_API_KEY.
---

# tavily-search

Use the bundled CLI `scripts/tavily_search.py` to perform web search via Tavily.

## Setup (one-time)

1. Create `secrets/tavily.env`:
   - `TAVILY_API_KEY=...`
2. Alternatively set env var `TAVILY_API_KEY`.

## Commands

- JSON (default):
  - `python3 skills/tavily-search/scripts/tavily_search.py --query "..." --max-results 5`

- Markdown output (easy to paste into chat):
  - `python3 skills/tavily-search/scripts/tavily_search.py --query "..." --format md --include-answer`

## Workflow

1. Ask Leo for the query + constraints (recency, region/language, sources) if missing.
2. Run the CLI.
3. Return: (a) 3-8 links + 1-line why each matters, or (b) a compact answer + citations, depending on Leo request.
