---
name: daily-scheduler
description: Plan, update, or view Leo's daily schedule. Always run schedule_data.py first. v2 separates PLAN (intent) from ACTUAL (truth), supports cross-midnight, and syncs ACTUAL to GCal safely.
---

# daily-scheduler (v2)

## Mission
Maintain a reliable daily schedule that survives real life:
- **PLAN = intent** (can be replanned/overwritten)
- **ACTUAL = truth** (single canonical timeline)
- Calendar correction follows **ACTUAL**, never PLAN.

## Mandatory first step
Before planning/replanning/view:
```bash
python3 skills/daily-scheduler/scripts/schedule_data.py
```

## File-first persistence (non-negotiable)
Write to file before any outward sync/notification.

- `memory/schedules/YYYY-MM-DD.md` — human-readable source of truth
- `memory/schedules/.meta/YYYY-MM-DD.json` — sync IDs / locks / hashes (v2 rollout)
- `memory/schedules/.archive/YYYY-MM-DD/<timestamp>.md` — backup before writes (v2 rollout)

## Required section model (v2)
```md
---
schema: daily-scheduler/v2
date: 2026-03-01
tz: Asia/Taipei
day_state: open   # open | closing | closed
plan_rev: 1
actual_rev: 1
updated_at: 2026-03-01T12:00+08:00
---

## Snapshot

## PLAN
### Current
### Deferred / Backlog
### History (compact)

## ACTUAL
### Timeline
### Skipped / Deferred (actual)

## Divergence
## Inbox
## Changelog
```

### Block grammar
- PLAN:
  - `- [P] HH:MM-HH:MM Title {uid:P-..., status:planned, fixed:false}`
- ACTUAL:
  - `- [A] HH:MM-HH:MM Title {uid:A-..., ps:exact, pe:exact, status:done, plan:P-...}`
- Cross-midnight:
  - `- [A] 23:45-01:30(+1d) Debugging {uid:A-..., ps:exact, pe:exact, status:done}`
- Approx:
  - `- [A] ~17:30-18:10 Biking {uid:A-..., ps:approx, pe:exact, status:done}`

## Operating modes

1) **Heartbeat / Status**
- Read today file, output compact snapshot only.

2) **Plan / Replan**
- Edit PLAN only.
- Increment `plan_rev` and append one compact history line.

3) **Log Actual**
- Edit ACTUAL timeline only.
- Set precision tags (`exact|approx|inferred`).
- Increment `actual_rev`.
- Run deterministic reconcile (mark done/skip/defer in PLAN).

4) **Bulk Correction Mode**
- Parse corrections into atomic ops.
- Apply parseable ones in one pass.
- Ambiguous items go to `## Inbox` (never silently guessed).
- MVP script available:
  ```bash
  # insert
  python3 skills/daily-scheduler/scripts/bulk_correct_v2.py --date YYYY-MM-DD --text "13:00-14:00 xxx; 14:10-15:00 yyy"
  # adjust by uid
  python3 skills/daily-scheduler/scripts/bulk_correct_v2.py --date YYYY-MM-DD --text "adjust A-xxxx to 14:00-15:10"
  # split by uid
  python3 skills/daily-scheduler/scripts/bulk_correct_v2.py --date YYYY-MM-DD --text "split A-xxxx at 15:30"
  # merge two uids
  python3 skills/daily-scheduler/scripts/bulk_correct_v2.py --date YYYY-MM-DD --text "merge A-1,A-2 as Focus Block"
  ```

5) **Close Day**
- Finalize ACTUAL and set `day_state: closed`.
- Exact ACTUAL blocks become locked-by-default in `.meta`.

6) **Sync**
- Sync **ACTUAL timeline only**.

## Cross-midnight ownership rule (critical)
Event belongs to the file of its **start date**.
If end is after midnight, use `(+1d)` or explicit end date.

## Sync contract (Google Calendar)
Hard rules:
1. Only ACTUAL blocks are synced.
2. Managed events must include:
   - `daily-scheduler/v2`
   - `daily-scheduler uid=A-...`
3. Never update/delete without uid match.
4. No mass delete.

Current phase safety:
- create/update only
- no automatic delete

## Validation checklist before write
- Front matter parseable
- Required sections present
- UIDs unique
- Time ranges normalize to start < end
- Cross-midnight normalized (no `timeRangeEmpty`)
- ACTUAL timeline sorted by start
- If uncertain, preserve raw text in `## Inbox`

## Leo-specific routing
See `memory/scheduling-rules.md`.
Default order: schedule file → Google Calendar → Todoist.
Never delete past events unless Leo explicitly asks.
