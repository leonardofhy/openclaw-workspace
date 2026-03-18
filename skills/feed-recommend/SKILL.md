---
name: feed-recommend
description: >
  Plugin-based multi-source feed recommendation system. Aggregates HN, Alignment Forum,
  LessWrong, arXiv (and any custom source) into a unified scored feed using Leo's
  interest profile. Drop-in source plugins, cross-source dedup, feedback loop.
---

# Feed Recommender — Multi-Source

Plugin 架構：每個來源一個 .py，統一 scoring + dedup + feedback。

## Architecture

```
sources/
  base.py        — BaseSource ABC
  hn.py          — Hacker News (Firebase API)
  af.py          — Alignment Forum (RSS)
  lw.py          — LessWrong (RSS)
  arxiv_feed.py  — arXiv (RSS, configurable categories)
  __init__.py    — auto-discover plugins

feed_engine.py   — load sources, fetch, score, dedup, rank
feed.py          — CLI interface
```

## Adding a New Source

1. Create `sources/my_source.py` with a class extending `BaseSource`
2. Add entry to `memory/feeds/config.json` under `sources`
3. Done — auto-discovery picks it up

## Commands

| Command | Description |
|---------|-------------|
| `sources` | List all available sources (enabled/disabled) |
| `enable <name>` | Enable a source |
| `disable <name>` | Disable a source |
| `fetch [--source X] [--limit N]` | Fetch from enabled sources |
| `recommend [--limit 10] [--source X]` | Score + rank + output top-N |
| `mark-seen <ids...>` | Mark articles as seen |
| `feedback <id> <+\|->` | Record feedback |
| `profile` | Show interest profile |
| `stats` | Show stats by source |
| `config` | Show current config |

## Data Files

| File | Purpose |
|------|---------|
| `memory/feeds/config.json` | Enabled sources + per-source settings |
| `memory/feeds/preferences.json` | Interest profile (shared across sources) |
| `memory/feeds/seen.jsonl` | Cross-source seen history (7-day window) |
| `memory/feeds/feedback.jsonl` | Feedback log with source tags |
| `memory/feeds/candidates/YYYY-MM-DD.jsonl` | Daily candidate files |
