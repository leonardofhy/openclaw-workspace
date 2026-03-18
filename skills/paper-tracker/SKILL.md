---
name: paper-tracker
description: >
  Track, search, and organize research papers from arxiv and other venues. Use when (1) adding a new paper to read,
  (2) checking reading backlog, (3) searching past papers by topic, (4) tagging/organizing papers,
  (5) reviewing reading progress, (6) Leo asks "之前讀過什麼", "那篇 paper", "找一下相關的 paper", "reading list".
  NOT for: running experiments (use experiment-manager), writing papers (use paper-writing), or learning concepts (use autodidact).
---

# Paper Tracker

## Quick Start

```bash
# Add paper from arxiv
python3 skills/paper-tracker/scripts/papers.py add 2301.07041

# Add paper from full URL
python3 skills/paper-tracker/scripts/papers.py add https://arxiv.org/abs/2301.07041

# Add non-arxiv paper manually
python3 skills/paper-tracker/scripts/papers.py add --manual \
  --title "My Paper Title" \
  --authors "Author A, Author B" \
  --venue "ICASSP 2026"

# List papers
python3 skills/paper-tracker/scripts/papers.py list
python3 skills/paper-tracker/scripts/papers.py list --status reading
python3 skills/paper-tracker/scripts/papers.py list --tag speech --limit 10

# Show full details
python3 skills/paper-tracker/scripts/papers.py show P-001

# Tag a paper
python3 skills/paper-tracker/scripts/papers.py tag P-001 speech whisper mech-interp

# Update reading status
python3 skills/paper-tracker/scripts/papers.py status P-001 reading

# Add reading notes
python3 skills/paper-tracker/scripts/papers.py note P-001 "Key insight: layer 3 encodes phonemes"

# Search across all fields
python3 skills/paper-tracker/scripts/papers.py search "attention mechanism"

# View stats
python3 skills/paper-tracker/scripts/papers.py stats

# Export
python3 skills/paper-tracker/scripts/papers.py export --format md
python3 skills/paper-tracker/scripts/papers.py export --format json
```

## Paper Lifecycle

```
queued → reading → read → archived
```

## Data Storage

- **Paper records**: `memory/papers/papers.jsonl` (append-only, one JSON per line)
- **ID format**: `P-001`, `P-002`... (auto-increment)
- **Each record contains**: id, title, authors, abstract, arxiv_id, url, date, categories, venue, status, tags, notes, added_at, updated_at

## Usage Scenarios

### Daily arxiv browsing
1. Skim arxiv, find interesting papers
2. `papers.py add <arxiv_id>` — auto-fetches metadata
3. `papers.py tag P-xxx speech ssl` — categorize

### Before starting research
1. `papers.py search "topic"` — find related papers already tracked
2. `papers.py list --tag topic` — browse by tag
3. `papers.py show P-xxx` — review notes from past reading

### Reading session
1. `papers.py list --status queued` — pick next paper
2. `papers.py status P-xxx reading` — mark as in-progress
3. `papers.py note P-xxx "key finding..."` — record insights
4. `papers.py status P-xxx read` — mark done

### Writing a paper
1. `papers.py search "related work keyword"` — find citations
2. `papers.py export --format md` — generate reference list

## Integration with Other Skills

- **experiment-manager**: Papers inspire experiments; reference P-xxx in experiment notes
- **autodidact**: Learning cycles may reference tracked papers
- **paper-writing**: Export reading notes to inform related work sections
