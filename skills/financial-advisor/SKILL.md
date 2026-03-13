---
name: financial-advisor
description: >
  Leo's personal financial advisor — track burn rate, scholarship/grant deadlines,
  income strategies, and 6-month survival plan milestones. Use when: (1) Leo asks about
  finances, money, budget, or scholarships, (2) heartbeat finance health check,
  (3) recording income or expense events, (4) monthly financial review, (5) checking
  milestone progress on the 6-month plan. Trigger phrases: 理財、財務、獎學金、burn rate、
  runway、收入、支出、financial、money、scholarship、grant. NOT for: investment advice,
  crypto, stock trading — Leo's priority is cash flow management during grad school.
---

# Financial Advisor

Leo's financial situation: not broke, but deteriorating. ~50 months runway at current burn rate.
Goal: **minimum time investment (≤5 hr/week) to reach cash-flow neutral while keeping research #1.**

## Core Principle

Leo avoids financial tasks (鴕鳥傾向). Your job is to **reduce cognitive load to zero** —
track everything, nudge at the right time, never make him think about money more than necessary.

## Data Files

All data lives in `memory/finance/`:

| File | Purpose |
|------|---------|
| `deadlines.json` | Scholarship/grant/admin deadlines (shared with `deadline_watch.py`) |
| `milestones.json` | 6-month plan milestones with status |
| `snapshots.jsonl` | Monthly financial position snapshots |
| `income-log.jsonl` | Income events (tutoring, freelance, grants, scholarships) |
| `FINANCE_TRACKER.md` | Human-readable summary (update monthly) |
| `FUNDING_MASTER_PLAN.md` | All known funding sources |

## Scripts

```bash
# Check current financial health (for heartbeat)
python3 skills/financial-advisor/scripts/finance_snapshot.py --latest

# Record a new snapshot
python3 skills/financial-advisor/scripts/finance_snapshot.py --record \
  --savings 280000 --income 20000 --expenses 25600

# Check 6-month plan milestones
python3 skills/financial-advisor/scripts/milestone_check.py

# Mark a milestone done
python3 skills/financial-advisor/scripts/milestone_check.py --complete M1-1

# Log income event
python3 skills/financial-advisor/scripts/finance_snapshot.py --log-income \
  --source tutoring --amount 4800 --note "2 sessions this week"

# Monthly report
python3 skills/financial-advisor/scripts/finance_report.py
```

## Heartbeat Integration

During heartbeat, run `milestone_check.py` (fast, <1s). If any milestone is:
- **Overdue** → nudge Leo via Discord DM (not #general)
- **Due this week** → mention in heartbeat summary
- **Blocked on Leo** → add to next direct conversation

Do NOT spam #general with financial updates. Finance = private → DM only.

## Monthly Review Protocol (1st of each month)

1. Ask Leo for latest 記帳 export (if not auto-synced)
2. Run `finance_snapshot.py --record` with new numbers
3. Run `finance_report.py` for trend analysis
4. Update `FINANCE_TRACKER.md` with new snapshot
5. Review upcoming deadlines (next 30 days)
6. Check milestone progress and adjust plan if needed

## Key Context

- **僑生 work rules**: 學期中 ≤20 hr/week, 需工作證 (NT$100, 7 days)
- **RA stipend conflict**: Most gov scholarships conflict with 研究獎助生 status
- **Safe bets**: 中技社 (private foundation), LTFF (international), 家教 (quick cash)
- **Leo's moat**: Speech AI + AI Safety + bilingual + Interspeech pub = rare combination

For detailed situation analysis, see `references/leo-situation.md`.
For full funding database, see `memory/finance/FUNDING_MASTER_PLAN.md`.
