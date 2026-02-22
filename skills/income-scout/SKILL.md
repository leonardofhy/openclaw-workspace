---
name: income-scout
description: "Analyze Leo’s personal data (resume, finance/spending reports, schedules, constraints) and propose concrete ways to earn money beyond scholarships (internships, TA/RA, freelance, tutoring, grants, bounties, writing, part-time roles). Use when Leo asks for 找錢/增加收入/接案/兼職/變現/我可以做什麼工作, or when updating a plan after new spending or runway changes."
---

# Income Scout

Produce a practical “get money” plan based on Leo’s actual profile + constraints.

## Workflow

### 0) Confirm constraints (ask only if missing)
- Time budget per week (e.g., 5h / 10h / 20h)
- On-site vs remote preference
- Taiwan work eligibility constraints (visa/permit). If unknown, flag as a risk + propose safe remote options.
- Minimum monthly target (e.g., +10k TWD/mo) and urgency (e.g., “need cash in 30 days”).

### 1) Load Leo’s data (be evidence-based)
Read only what’s needed.

**Resume (primary)**
- Repo: `/Users/leonardo/Workspace/my_resume/`
  - Start with `resume.tex` then read `cv/experience.tex`, `cv/projects.tex`, `cv/skills.tex`.

**Finance (runway + spending behavior)**
- Latest generated report(s) in: `/Users/leonardo/Workspace/little-leo-tools/reports/`
  - Prefer the newest `reports/YYYY-MM/report.md` (currency-corrected).
- If needed, re-run the report generator:
  - `python3 /Users/leonardo/Workspace/little-leo-tools/scripts/generate_report.py`

**Schedule (time reality-check)**
- If gog is configured, optionally check upcoming calendar blocks.

### 2) Extract “sellable skills inventory”
From resume + projects, summarize:
- Hard skills (languages, ML/infra/tooling)
- Proof of work (projects, deployments, open source)
- Domain fit (AI safety organizer, telecom/ML, etc.)
- Strength signals (elite schools, research context)

Output: a short table:
- Skill / Evidence (link/line/file) / Market use-case

### 3) Build an opportunity pipeline (ranked)
Create a ranked list of opportunities with:
- Expected monthly value (TWD)
- Time-to-cash (days)
- Time cost (h/week)
- Probability (low/med/high)
- Career synergy (low/med/high)
- Risk/constraints (work permit, NDA, etc.)

Minimum categories to consider:
1. **Immediate cash (0–14 days):** tutoring (CS/Math/ML), code review gigs, small freelance.
2. **Short-term (2–8 weeks):** part-time dev/ML engineer, research assistant, paid organizer role.
3. **Medium-term (2–4 months):** internship, contract role, grant/funding applications.
4. **One-off wins:** hackathon prizes, bug bounty (only if relevant), writing/technical blog paid pieces.

### 4) Convert to an action plan (next 7 days)
Deliver:
- 3 highest-ROI actions
- Draft outreach template(s)
- A weekly cadence plan (how to keep applying while doing research)

## Output format (default)
1) **Diagnosis (3 bullets)**
2) **Evidence tables**
   - Skills inventory table
   - Spending/runway constraints table (cite report numbers)
3) **Ranked opportunities table** (10–15 rows)
4) **Next 7 days checklist**

## Safety / privacy
- Do not paste secrets (tokens, passwords).
- Before sending any email/messages to third parties, ask Leo to confirm.
