---
name: funding-hunter
description: NTU Funding Hunter — check scholarship recommendations, verify eligibility, run scrapes, and track applications. Use when the user asks about scholarships, funding, deadlines, financial aid, 獎學金, or when a cron/heartbeat triggers funding checks. Trigger phrases: "獎學金", "funding", "scholarship", "有什麼可以申請", "deadline", "apply", "申請進度", "scrape scholarships".
---

# NTU Funding Hunter

Scholarship scraper + eligibility matcher + deadline tracker for a Malaysian 僑生 at NTU.

## Project Location

```
FUNDING_DIR="/Users/leonardo/Workspace/leo-funding-hunter"
```

All CLI commands must run from `$FUNDING_DIR`.

## CLI Commands

```bash
cd "$FUNDING_DIR"

# Scrape all sources, auto-match, save to data/scholarships.json
python3 cli.py scrape

# Ranked recommendations (apply_now first, by deadline)
python3 cli.py recommend
python3 cli.py recommend --all    # include apply_later + monitor

# Upcoming deadline alerts
python3 cli.py alerts
python3 cli.py alerts --all       # include monitor items

# What to act on today
python3 cli.py focus

# Update scholarship status
python3 cli.py update <id> --eligibility eligible --notes "verified"
python3 cli.py update <id> --application in_progress

# Run eligibility matching on UNKNOWN entries
python3 cli.py match --auto

# List configured sources
python3 cli.py sources
```

## Handling Requests

| User says | Action |
|-----------|--------|
| "有哪些獎學金?" / "what can I apply for?" | `cli.py recommend` → summarize apply_now with deadlines |
| "什麼快截止?" / "urgent?" | `cli.py alerts` → highlight <14 days |
| "更新資料" / "scrape" | `cli.py scrape` → report counts |
| "我能申請 X 嗎?" | Search repo → web_fetch detail page → evaluate vs profile → `cli.py update` |
| "更新申請進度" | `cli.py update <id> --application in_progress --notes "..."` |

## Eligibility Quick Reference

**Usually ELIGIBLE:** 僑生/境外生 scholarships, international grants (IEEE, ISCA), NTU internal without nationality restriction, 教育部僑生獎學金 series.

**Usually INELIGIBLE:** Requires Taiwan 戶籍 or ROC citizenship, undergraduate only, excludes 僑生, county/city 清寒 (needs local 設籍), already-enrolled exclusion.

## User Profile Summary

Malaysian 僑生, NTU 電信所碩士, GPA 4.11/4.3, advisor 李宏毅, research: Mech Interp + Speech/Multimodal LM + AI Safety. NO Taiwan 戶籍, NO ROC citizenship. Full profile: `$FUNDING_DIR/config/profile.yaml`.

## Response Style

- Traditional Chinese for scholarship names/eligibility
- Always include deadlines with days remaining
- Flag <14 days as 🟡 urgent
- Mention specific next actions
