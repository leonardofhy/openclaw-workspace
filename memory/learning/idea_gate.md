# Idea Gate (Default Protocol)

Purpose: prevent duplicate work and low-ROI ideas by forcing novelty + feasibility checks **before** deep implementation.
Owner: Little Leo
Status: active default (2026-02-28)

---

## 0) Trigger

Run this gate whenever:
- a new paper idea appears,
- scope shifts significantly,
- or an old idea is revived after >14 days.

No exceptions: **pass gate first, then build.**

---

## 1) Idea Snapshot (2 minutes)

- **One-sentence claim:**
  - `We [do what] for [who/what] using [core method], showing [main result].`
- **Target venue + deadline:**
- **Expected artifact:** (method paper / benchmark / empirical finding / toolkit)

---

## 2) Novelty Scan (10–20 minutes)

## 2.1 Search queries
Use combinations of:
- task/domain terms
- method terms
- causal/probing/intervention terms
- output granularity terms (layer / head / feature)

Example skeleton:
- `("speech llm" OR "audio-language model") AND ("causal" OR "activation patching") AND ("layer" OR "feature")`

## 2.2 Candidate set
Collect top **5–10 closest papers** (recent first, then citation backbone).
For each paper, store:
- title
- year/venue
- URL
- 1-line summary

## 2.3 Overlap table (required)
For each paper compare against your idea:
- **Question:** same or different?
- **Method:** same family or meaningfully different?
- **Output:** same granularity/setting or different?

Use this rubric:
- `Same` / `Partial` / `Different`

---

## 3) Duplicate Risk Decision (R/Y/G)

- **RED (stop or pivot):**
  - Question=Same + Method=Same + Output=Same for at least one strong paper.
- **YELLOW (reframe first):**
  - Partial overlap on 1–2 dimensions.
  - Must rewrite claim before experiments.
- **GREEN (proceed):**
  - Clear differentiation in at least one core dimension and practical contribution remains.

Record one-line verdict + reason.

---

## 4) Feasibility Gate (MVE first)

Define one **minimum viable experiment** that can finish in <= 1 day compute.

Required fields:
- hypothesis
- required data/tools
- runtime estimate
- success threshold (numeric)
- failure threshold (numeric)

Decision:
- pass -> continue
- fail -> pivot or stop

---

## 5) Value Gate (Impact × Tractability × Timing)

Score each 1–5:
- **Impact:** if successful, will people care/use it?
- **Tractability:** can we get convincing evidence in 1–2 weeks?
- **Timing:** is this a live window (new gap, recent wave, deadline fit)?

Total out of 15:
- `>=10` -> continue
- `7–9` -> narrow scope then re-gate
- `<=6` -> stop

---

## 6) Output Template (copy/paste)

## Idea Gate Report — [Idea Name]
- Date:
- One-sentence claim:
- Venue/deadline:

### A. Novelty Scan
- Closest papers reviewed: [N]
- Overlap summary:
  - Paper 1: Q/M/O = _ / _ / _
  - Paper 2: Q/M/O = _ / _ / _
- R/Y/G verdict:
- Why:

### B. Feasibility (MVE)
- Experiment:
- Success threshold:
- Failure threshold:
- Result: pass/fail

### C. Value Score
- Impact:
- Tractability:
- Timing:
- Total:
- Final decision: continue / reframe / stop

---

## 7) Operating Rule (default behavior)

For every new idea:
1. Fill this gate first.
2. Share concise gate report with Leo.
3. Only then start deep implementation.

If skipped, treat as process violation and backfill immediately.
