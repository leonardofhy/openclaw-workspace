---
name: context7
description: >
  Query up-to-date library documentation via Context7 (context7.com).
  Use when Leo asks about API usage, function signatures, or "how do I use X in Y version"
  for any library (PyTorch, Transformers, NumPy, Python stdlib, etc.).
  Trigger phrases: "查文件", "查 API", "context7", "最新文件", "library docs",
  "how to use X", "X 的文件". Provides a doc-query interface for autodidact and
  senior-engineer skills.
---

# context7

Query the latest library documentation via the Context7 HTTP API.
No API key required. Results cached to `memory/context7-cache/`.

## Commands

Search for a library ID:
```bash
python3 skills/context7/scripts/context7_query.py search --query "pytorch"
```

Fetch documentation (by Context7 library ID):
```bash
python3 skills/context7/scripts/context7_query.py docs --library "/pytorch/pytorch" --topic "DataLoader" --tokens 8000
```

Fetch docs + render as Markdown (easier to paste into chat):
```bash
python3 skills/context7/scripts/context7_query.py docs --library "/huggingface/transformers" --topic "Trainer" --format md
```

Version-pinned query (use the versioned library ID from search results):
```bash
python3 skills/context7/scripts/context7_query.py docs --library "/pytorch/pytorch@v2.2.0" --topic "autograd"
```

Force bypass local cache:
```bash
python3 skills/context7/scripts/context7_query.py docs --library "/numpy/numpy" --no-cache
```

## Workflow

1. If library ID is unknown → run `search` to get the correct Context7 ID.
2. Run `docs` with the library ID and a `--topic` matching the user's question.
3. Return: relevant sections + canonical links from `source_urls`.

## Integration with other skills

- **autodidact**: call during `learn` actions to fetch API docs before writing code.
- **senior-engineer**: call to verify correct API signatures before writing implementation.

## Cache

Responses cached at `memory/context7-cache/<library_slug>/<topic_slug>.json` (TTL 24 h).
Cache stores full JSON response + `cached_at` timestamp. Use `--no-cache` to force refresh.

## Setup (MCP — optional)

For native MCP tool integration (instead of HTTP CLI), add to `~/.claude/settings.json`:

```json
"mcpServers": {
  "context7": {
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "@upstash/context7-mcp"]
  }
}
```

After adding, restart Claude Code. The MCP exposes two tools: `resolve-library-id` and
`get-library-docs` — Claude can call these directly without the Python wrapper.
