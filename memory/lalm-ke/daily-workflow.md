# LALM-KE Daily Research Workflow
> Created: 2026-03-24 | Owner: Leo + bot
> Checkpoint: Monday PM meeting with 智凱 and 彥廷

---

## Overview

The bot runs a daily pipeline to surface new papers, summarize them, and deliver a concise briefing to Leo. During the survey phase (first 4 weeks), the focus is wide-net collection. After that, narrow to core LALM-KE papers.

---

## 1. Paper Discovery — Daily arXiv Monitoring

### Primary arXiv Categories
- `cs.CL` — NLP/LLM (knowledge editing methods, benchmarks)
- `cs.SD` — Sound/Speech (new LALMs, audio models)
- `cs.AI` — AI (general multimodal work)
- `eess.AS` — Audio/Speech Signal Processing (encoder work)
- `cs.LG` — Machine Learning (editing algorithms, training methods)

### Keyword Filter (ordered by relevance)
**Tier 1 — always surface:**
```
"knowledge editing"
"model editing"
"LALM"
"audio language model"
"speech language model"
"SALMONN" OR "Qwen-Audio" OR "WavLLM"
"multimodal knowledge editing"
```

**Tier 2 — surface if also in cs.CL/cs.SD:**
```
"mechanistic interpretability" + ("audio" OR "speech")
"factual knowledge" + ("multimodal" OR "audio")
"ROME" OR "MEMIT" OR "MEND" + ("audio" OR "multimodal")
"knowledge localization"
"causal tracing" + ("speech" OR "audio" OR "multimodal")
"continual learning" + ("audio" OR "speech" LLM)
```

**Tier 3 — weekly scan only:**
```
"large audio model"
"audio foundation model"
"speech foundation model"
"instruction tuning" + "audio"
```

### Author Tracking (key researchers to follow)
| Author | Affiliation | Why Track |
|--------|-------------|-----------|
| Kevin Meng | MIT (now industry) | ROME/MEMIT author |
| Christopher Manning | Stanford | KE group |
| Nicola De Cao | UCL | Knowledge Neurons, MEND collaborator |
| Eric Mitchell | Stanford | MEND, SERAC |
| Yunzhi Yao | | KE survey author |
| Changling Tang | Tsinghua | SALMONN author |
| Yunfei Chu | Alibaba | Qwen-Audio author |
| Hung-yi Lee | NTU | Leo's advisor; track output |
| David Hartvigsen | MIT | GRACE author |

---

## 2. Summarization Protocol

### Triage (bot auto-runs)
For each new paper matching Tier 1/2 keywords:

1. **Read abstract** — extract: (a) problem, (b) method type, (c) modality, (d) main claim
2. **Score relevance to LALM-KE** (0-3):
   - 0: tangential
   - 1: relevant background
   - 2: directly relevant (KE + audio/multimodal)
   - 3: core paper (must read)
3. **Tag**: `#ke-method`, `#ke-benchmark`, `#lalm-arch`, `#interp`, `#audio-encoder`, `#multimodal-ke`

### Summary Format (for score ≥ 2 papers)
```
[PAPER] Title
Authors (Year) | arXiv:XXXX | Score: 2/3 | Tags: #ke-method #multimodal
Problem: [1 sentence]
Method: [1 sentence]
Key result: [1 sentence]
LALM-KE relevance: [why Leo should care — 1-2 sentences]
Action: READ / SKIM / QUEUE
```

---

## 3. Daily Briefing to Leo

### Delivery
- **Channel**: Discord DM (user:756053339913060392)
- **Timing**: 09:00 TPE (after daily digest, before Leo's morning)
- **Frequency**: Daily during survey phase (first 4 weeks), then 3x/week

### Report Format
```
📚 LALM-KE Daily Brief — [Date]

🔴 MUST READ today:
→ [Title] [arXiv link] — [1-line why]

🟡 Worth skimming (score 2):
→ [Title] — [1-line relevance]
→ [Title] — [1-line relevance]

🟢 Background (score 1):
→ [N papers in queue — skim this week]

📊 Weekly progress: [X/10 Phase 1 papers read]
📅 Next Monday meeting: [N days away]
💡 Suggested focus today: [1 specific task — e.g., "finish ROME paper, start SALMONN"]
```

### Escalation rule
- If a **score-3 paper** (core LALM-KE paper, highly relevant) drops → push immediately as a separate DM, don't wait for morning brief
- If something looks like a **direct competitor paper** (someone is doing LALM-KE) → flag urgently in Discord + note in `memory/lalm-ke/competitor-watch.md`

---

## 4. Integration with Autodidact System

### Phase-Aware Integration
- **Survey phase (weeks 1-4)**: autodidact pulls LALM-KE papers into its reading queue; Leo's notes trigger autodidact synthesis sessions
- **After survey**: autodidact shifts to "research development" phase — synthesizing gaps, drafting hypotheses

### Handoff Protocol
When autodidact runs (every 30 min on lab bot):
1. Check `memory/lalm-ke/reading-queue.md` for new papers Leo flagged
2. If a paper has `status: summarized`, extract key findings to `memory/lalm-ke/synthesis-notes.md`
3. Weekly (Sunday): summarize week's reading → update `memory/lalm-ke/weekly-synthesis.md`
4. Before Monday meeting: generate a "pre-meeting briefing" → Leo's Discord DM

### Files to Maintain
```
memory/lalm-ke/
├── landscape.md              # This field map (living)
├── reading-roadmap.md        # Paper list with status
├── reading-queue.md          # Active queue (what Leo is reading now)
├── survey-notes/             # Individual paper notes (use template)
│   └── YYYY-MM-DD-[slug].md
├── synthesis-notes.md        # Cross-paper synthesis (bot updates after reading)
├── weekly-synthesis.md       # Weekly summaries (bot generates Sundays)
├── competitor-watch.md       # Papers that are close to LALM-KE (urgency tracker)
├── experiment-ideas.md       # Concrete experiment proposals from readings
└── daily-workflow.md         # This file
```

### Reading Queue Management
In `memory/lalm-ke/reading-queue.md`, maintain entries:
```markdown
## Active
- [ ] [Paper slug] | Priority: P0 | Added: 2026-03-24 | Due: 2026-03-27

## Completed
- [x] [Paper slug] | Completed: YYYY-MM-DD | Notes: survey-notes/slug.md
```

---

## 5. Cron Job Recommendations

### For Lab Bot (24/7, WSL2)

```bash
# Daily arXiv scan for LALM-KE papers
# Run at 07:30 TPE (after arXiv daily update ~06:00 UTC = 14:00 TPE, so catch next-day batch)
# OR run at 14:30 TPE to catch same-day arXiv submissions
30 14 * * * openclaw session run isolated --model g53s --timeout 120 "Check arXiv cs.CL, cs.SD, cs.AI for new LALM-KE papers today. Keywords: knowledge editing, model editing, audio language model, multimodal knowledge editing. Score relevance 0-3. Send brief to Leo Discord DM if any score >= 2. Format per memory/lalm-ke/daily-workflow.md."

# Sunday pre-meeting synthesis (before Monday meeting)
0 20 * * 0 openclaw session run isolated --model sonnet --timeout 300 "Generate LALM-KE weekly synthesis for Leo's Monday meeting. Read memory/lalm-ke/survey-notes/ from this week. Summarize: (1) papers read, (2) key insights, (3) open questions, (4) suggested agenda items. Write to memory/lalm-ke/weekly-synthesis.md and send to Leo Discord DM."

# Monday morning meeting prep reminder
0 9 * * 1 openclaw session run isolated --model g53s --timeout 60 "Remind Leo: LALM-KE group meeting today (Monday PM). Check memory/lalm-ke/weekly-synthesis.md and send a 3-bullet prep summary to Leo Discord DM."
```

### For Mac Bot (opportunistic, when laptop is on)

No additional cron needed — lab bot handles continuous monitoring. Mac bot can run:
- arXiv checks during heartbeat if user asks
- Paper reading sessions when Leo is actively working

---

## 6. Weekly Monday Meeting Prep Checklist

The bot should auto-generate this on Sunday evening:

```markdown
## LALM-KE Monday Meeting Prep — [Date]

### Papers read this week
- [list with 1-line takeaway each]

### Key insights / surprising findings
- 

### Open questions to discuss with 智凱 and 彥廷
- 

### Proposed experiments to propose
- 

### Papers for next week
- 

### Blockers / things that confused me
- 
```

---

## 7. Survey Phase Milestones

| Week | Milestone | Done? |
|------|-----------|-------|
| Week 1 | Read Phase 1 P0 papers (7 papers) | ☐ |
| Week 1 | First Monday meeting: alignment on direction | ☐ |
| Week 2 | Choose target LALM for experiments (SALMONN or Qwen-Audio) | ☐ |
| Week 2 | Choose target KE method to adapt (ROME or GRACE) | ☐ |
| Week 3 | Read all Phase 2 methods papers | ☐ |
| Week 3 | Identify the gap: confirm LALM-KE hasn't been done | ☐ |
| Week 4 | Draft experiment proposal (what to run, what to measure) | ☐ |
| Week 4 | Present plan to Prof. Lee | ☐ |
