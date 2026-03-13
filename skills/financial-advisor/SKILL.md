---
name: financial-advisor
description: >
  Leo's personal financial advisor — track burn rate, scholarship/grant deadlines,
  income strategies, and 6-month survival plan milestones. Use when: (1) Leo asks about
  finances, money, budget, or scholarships, (2) heartbeat finance health check,
  (3) recording income or expense events, (4) monthly financial review, (5) checking
  milestone progress on the 6-month plan, (6) grant/scholarship application drafting.
  Trigger phrases: 理財、財務、獎學金、burn rate、runway、收入、支出、financial、money、
  scholarship、grant、工作證、打工、freelance. NOT for: investment advice, crypto, stock
  trading — Leo's priority is cash flow management during grad school.
---

# Financial Advisor

Leo's financial situation: not broke, but deteriorating. ~50 months runway at current burn rate.
Goal: **minimum time investment (≤5 hr/week) to reach cash-flow neutral, research stays #1.**

## Core Principles

1. **Leo avoids financial tasks** (鴕鳥傾向). Reduce his cognitive load to zero.
2. **Legal compliance first** — 僑生 20hr/week cap is non-negotiable. See `references/leo-situation.md` §Legal Guardrails.
3. **Finance is private** — never post to #general or group channels. DM only.
4. **Nudge, don't nag** — one reminder per milestone. If postponed, respect it.

## Data Architecture

All data in `memory/finance/`. **Single source of truth per concern:**

| File | Purpose | Authority |
|------|---------|-----------|
| `deadlines.json` | All deadline dates (shared with `deadline_watch.py`) | Dates |
| `milestones.json` | 6-month plan milestones with status | Plan progress |
| `snapshots.jsonl` | Monthly financial position snapshots | Financial position |
| `income-log.jsonl` | Income events | Income tracking |
| `expense-log.jsonl` | One-off expense events | Expense tracking |
| `FINANCE_TRACKER.md` | Human-readable summary (update monthly) | Dashboard |
| `FUNDING_MASTER_PLAN.md` | All known funding sources + MATS plan | Scholarship DB |

Legacy files (`SCHOLARSHIP_ANALYSIS.md`, `INCOME_IDEAS.md`, `GPT52*.md`, `ARENA8*.md`) are
archived reference — **do not update them**, use canonical files above instead.

## Scripts

```bash
# === Snapshots ===
python3 skills/financial-advisor/scripts/finance_snapshot.py --latest
python3 skills/financial-advisor/scripts/finance_snapshot.py --check-stale [--max-age 45]
python3 skills/financial-advisor/scripts/finance_snapshot.py --record \
  --savings 280000 --income 20000 --expenses 25600
python3 skills/financial-advisor/scripts/finance_snapshot.py --trend --months 6

# === Income/Expense Logging ===
python3 skills/financial-advisor/scripts/finance_snapshot.py --log-income \
  --source tutoring --amount 4800 [--note "2 sessions"] [--date 2026-03-10]
python3 skills/financial-advisor/scripts/finance_snapshot.py --log-expense \
  --source "Interspeech reg" --amount 8000
python3 skills/financial-advisor/scripts/finance_snapshot.py --income-summary --months 3

# === Milestones ===
python3 skills/financial-advisor/scripts/milestone_check.py              # Full view
python3 skills/financial-advisor/scripts/milestone_check.py --brief      # Heartbeat one-liner
python3 skills/financial-advisor/scripts/milestone_check.py --next       # Next 3 actionable
python3 skills/financial-advisor/scripts/milestone_check.py --overdue
python3 skills/financial-advisor/scripts/milestone_check.py --complete M1-1 [--note "done"]
python3 skills/financial-advisor/scripts/milestone_check.py --skip M2-3 --note "not pursuing"
python3 skills/financial-advisor/scripts/milestone_check.py --postpone M1-2 --to 2026-04-15

# === Reports ===
python3 skills/financial-advisor/scripts/finance_report.py               # Full monthly
python3 skills/financial-advisor/scripts/finance_report.py --brief       # Heartbeat one-liner
```

## Heartbeat Integration

Run these two commands (fast, <1s each):
```bash
python3 skills/financial-advisor/scripts/finance_report.py --brief
python3 skills/financial-advisor/scripts/finance_snapshot.py --check-stale
```

Decision tree:
- **Snapshot stale (>45d)** → DM Leo: "需要你最新的記帳匯出"
- **Overdue milestones** → DM Leo with top 1-2 items (don't dump the whole list)
- **Deadline <7d** → Mention in heartbeat summary (already handled by `deadline_watch.py`)
- **All clear** → No finance message needed

## Monthly Review Protocol (1st of each month)

1. `--check-stale` → if stale, ask Leo for 記帳 export
2. `--record` with new numbers
3. `finance_report.py` for trend analysis
4. Update `FINANCE_TRACKER.md` with new snapshot
5. Review upcoming deadlines (next 30-60 days)
6. Check milestone progress; postpone or adjust as needed
7. Cross-reference `FUNDING_MASTER_PLAN.md` for upcoming application windows

## Grant Application Support

When a grant/scholarship deadline approaches:
1. Read `FUNDING_MASTER_PLAN.md` for requirements
2. Read `references/leo-situation.md` for positioning angles
3. Draft application/email for Leo to review
4. Key selling points: Interspeech 2026 first-author, NTUAIS organizer, bilingual,
   Speech AI × AI Safety intersection, Taiwan = underserved region

## Key Context

For detailed situation analysis, legal rules, income strategies, and funding sources:
→ `references/leo-situation.md`

For full funding database with timelines and MATS plan:
→ `memory/finance/FUNDING_MASTER_PLAN.md`

For AI Safety organization landscape (useful for grant positioning):
→ `memory/research/ai-safety-org-survey.md`
