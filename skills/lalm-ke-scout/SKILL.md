# lalm-ke-scout

**LALM-KE Daily Paper Scout** — Automated discovery of papers at the intersection of Knowledge Editing and Audio/Speech Language Models.

## What it does

Each run:
1. Fetches arXiv RSS for cs.CL, cs.SD, cs.AI, cs.LG, cs.IR
2. Runs targeted arXiv API queries for KE × LALM terms
3. Deduplicates by arXiv ID
4. Scores against `preferences_lalm_ke.json` (KE + LALM boost keywords)
5. Outputs top-N papers as JSON + Markdown summary

## Usage

```bash
python3 ~/.openclaw/workspace/skills/lalm-ke-scout/scripts/daily_scout.py
python3 daily_scout.py --limit 20
python3 daily_scout.py --dry-run
python3 daily_scout.py --output-dir /path/to/dir
```

## Output

- `~/.openclaw/workspace/memory/lalm-ke/daily/YYYY-MM-DD.json`
- `~/.openclaw/workspace/memory/lalm-ke/daily/YYYY-MM-DD.md`

## Dependencies

- `~/Workspace/leo-feed-digest/` (for preferences profile)
- Python 3 stdlib only (urllib, xml.etree, json, re)
- No OpenClaw dependencies

## Key files

| File | Purpose |
|------|---------|
| `scripts/daily_scout.py` | Main runner |
| `~/Workspace/leo-feed-digest/data/preferences_lalm_ke.json` | Scoring profile |

## Trigger phrases

「查 LALM-KE 論文」、「今天有什麼 knowledge editing paper」、「run lalm-ke scout」、「knowledge editing 最新進展」
