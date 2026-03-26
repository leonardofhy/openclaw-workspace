# LALM-KE Literature Review Pipeline — Pre-Approved Spec

> This spec is PRE-APPROVED by the user. Skip brainstorming, go directly to writing-plans → subagent-driven-development.

## Goal

Build an automated daily literature review pipeline that:
1. Discovers new papers on LALM Knowledge Editing (already done: `daily_scout.py`)
2. Fetches and reads full paper content
3. Produces structured summaries and reading notes
4. Generates a daily report for Leo (Discord DM + file)

## Architecture

```
daily_scout.py (existing) → finds top papers with scores
        ↓
paper_reader.py (NEW) → fetches full text, LLM summarizes
        ↓
report_generator.py (NEW) → aggregates into daily report
        ↓
Cron orchestration → daily_pipeline.sh
        ↓
Output: Discord DM + memory/lalm-ke/reports/YYYY-MM-DD.md
```

## Components

### 1. `paper_reader.py` — Core Paper Reading Engine

**Location:** `skills/lalm-ke-scout/scripts/paper_reader.py`

**Input:** arXiv ID or URL (from daily_scout.py output JSON)

**Process:**
1. Fetch full paper as markdown via HuggingFace Papers API:
   `curl -s "https://huggingface.co/papers/{ARXIV_ID}.md"` 
   Fallback: `curl -s -H "Accept: text/markdown" "https://huggingface.co/papers/{ARXIV_ID}"`
   Fallback 2: fetch abstract from arXiv API
2. If full text > 100KB, truncate to intro + method + conclusion sections
3. Send to Claude CLI for structured summarization (claude --print -p):
   - One-paragraph summary (3-5 sentences)
   - Problem statement
   - Method (key technique)
   - Key results (quantitative if available)
   - Relevance to LALM-KE (score 0-3 with explanation)
   - Open questions / limitations
   - Connections to other papers in our reading list
4. Save structured notes to `memory/lalm-ke/paper-notes/{ARXIV_ID}.md`

**Output format (paper note):**
```markdown
# {Title}

- **arXiv:** {id}
- **Authors:** {authors}
- **Date:** {date}
- **Scout Score:** {score}
- **Relevance:** {0-3}/3 — {explanation}
- **Read Date:** {today}

## Summary
{3-5 sentence summary}

## Problem
{what problem does this solve}

## Method
{key technique, 2-3 sentences}

## Key Results
{quantitative results, benchmarks}

## LALM-KE Relevance
{how this connects to our research direction}

## Open Questions
{limitations, future work, things to investigate}

## Connections
{links to other papers we've read}
```

**CLI interface:**
```bash
python3 paper_reader.py --arxiv-id 2310.08475          # single paper
python3 paper_reader.py --from-scout daily/2026-03-24.json --top 5   # top 5 from scout
python3 paper_reader.py --from-scout daily/2026-03-24.json --min-score 25  # score threshold
python3 paper_reader.py --dry-run                       # show what would be read
python3 paper_reader.py --skip-existing                 # don't re-read papers with notes
```

**Important constraints:**
- Use `claude -p --print --model sonnet` for summarization (not opus, save quota)
- Add `--permission-mode bypassPermissions --bare` flags
- Rate limit: 3 second delay between papers
- Handle network errors gracefully (retry once, then skip)
- Track which papers have been read in `memory/lalm-ke/paper-notes/index.json`

### 2. `report_generator.py` — Daily Report Builder

**Location:** `skills/lalm-ke-scout/scripts/report_generator.py`

**Input:** Today's scout results + newly read paper notes

**Process:**
1. Load today's scout JSON (`memory/lalm-ke/daily/YYYY-MM-DD.json`)
2. Load all paper notes read today (check read date)
3. Generate daily report with:
   - 📊 Stats: N papers scanned, M new, K read in detail
   - 🔴 High relevance (score 3): full summary
   - 🟡 Medium relevance (score 2): title + 1-line takeaway
   - 🟢 Low relevance (score 0-1): just titles
   - 💡 Cross-paper insights (if 2+ papers read)
   - 📚 Updated reading queue status
4. Save to `memory/lalm-ke/reports/YYYY-MM-DD.md`
5. Output a concise Discord-friendly version (no markdown tables, <2000 chars)

**CLI interface:**
```bash
python3 report_generator.py                    # today's report
python3 report_generator.py --date 2026-03-24  # specific date
python3 report_generator.py --discord          # output Discord-friendly format
python3 report_generator.py --weekly           # weekly synthesis
```

### 3. `daily_pipeline.sh` — Orchestration Script

**Location:** `skills/lalm-ke-scout/scripts/daily_pipeline.sh`

**Flow:**
```bash
#!/bin/bash
set -e
WORKSPACE="$HOME/.openclaw/workspace"
SCRIPTS="$WORKSPACE/skills/lalm-ke-scout/scripts"

# Step 1: Scout for new papers
python3 "$SCRIPTS/daily_scout.py" --limit 20

# Step 2: Read top papers (skip already-read)
python3 "$SCRIPTS/paper_reader.py" \
  --from-scout "$WORKSPACE/memory/lalm-ke/daily/$(date +%Y-%m-%d).json" \
  --top 5 --skip-existing

# Step 3: Generate report
python3 "$SCRIPTS/report_generator.py" --discord > /tmp/lalm-ke-report.txt

# Step 4: Output for cron to pick up
cat /tmp/lalm-ke-report.txt
```

### 4. Directory Structure

```
memory/lalm-ke/
├── daily/              # Scout results (existing)
│   └── YYYY-MM-DD.json
├── paper-notes/        # Individual paper summaries
│   ├── index.json      # Track read papers
│   └── 2310.08475.md   # One file per paper
├── reports/            # Daily aggregated reports
│   └── YYYY-MM-DD.md
├── weekly/             # Weekly synthesis
│   └── YYYY-WNN.md
└── (existing files: landscape.md, reading-roadmap.md, etc.)
```

## Testing

- `paper_reader.py --dry-run` should work without API calls
- `report_generator.py` should handle empty days gracefully
- Test with known arxiv IDs: 2202.05262 (ROME), 2310.08475 (Multimodal KE)

## Constraints

- All scripts must work standalone (no OpenClaw-specific imports)
- Use subprocess to call `claude` CLI (not import anthropic SDK)
- Graceful degradation: if claude CLI fails, still save the raw paper content
- All output in UTF-8, handle CJK characters
- No API keys needed beyond what claude CLI already has

## NOT in scope

- Interactive paper reading (that's a different workflow)
- Citation graph analysis (future enhancement)
- Paper writing assistance (separate skill)
