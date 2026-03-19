# Task: Update Abstract + §1 Contributions

You are a senior ML researcher helping write a paper on mechanistic interpretability of audio-language models.

## Context

Read these files first:
- `docs/paper-a-abstract.md` — current abstract draft
- `docs/paper-a-draft.md` — full paper (esp. §1 Introduction Para 4 — Contributions)
- `docs/paper-a-results.md` — what experiments have been done
- `docs/paper-a-discussion.md` — if it exists, read it

## Your task

### 1. Update `docs/paper-a-abstract.md`
Rewrite the abstract to:
- State the problem clearly: ALMs can "listen" or "guess"; no causal metric existed
- State the method: gc(k) = grounding coefficient, based on interchange intervention
- State what we've validated so far: framework validated in 27 mock experiments (median |r| = 0.877); preliminary real evidence from Whisper-base encoder (voicing geometry at layer 5)
- State what's pre-registered: predictions for ALME conflict items and MPAR² RL shift
- Be honest: "We present the framework and preliminary encoder-level validation; full ALM experiments are in progress."
- Target: 150-200 words, structured as: motivation → method → results → implications

### 2. Update §1 Contributions paragraph in `docs/paper-a-draft.md`
Find the "Para 4 — Contributions list" section and update it to:
1. gc(k) metric — first causal, layer-wise grounding coefficient for ALMs
2. Listening Geometry — 5D framework (k*, α_AND, σ, t*, CS)  
3. AND/OR gate decomposition — mechanistic taxonomy of multimodal features
4. Mock framework validation — 29 experiments, 27 mock (median |r| = 0.877), 2 real
5. Pre-registered predictions — 3 testable claims for scale-up and RL-training experiments

Keep the "[TODO: fill in from real data]" notes where real N/performance numbers are needed.

### Output
1. Rewrite `docs/paper-a-abstract.md` in place
2. Edit the contributions paragraph in `docs/paper-a-draft.md` (find and replace the Para 4 section)
3. Create a brief `docs/paper-a-status.md` summarizing: what's done, what's pending GPU, what's pre-registered
