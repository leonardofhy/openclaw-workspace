---
name: memory
description: >
  Memory rumination tools. Fetch latest diary entries for the cron-based
  memory reflection pipeline (記憶反芻). Used by the daily 12:00 cron job.
---

# Memory Skill

## Scripts

- `scripts/fetch_latest_diary.py` — Outputs the latest diary entry in structured text for the cron agent to reflect on and optionally save insights to `memory/insights.md`.
