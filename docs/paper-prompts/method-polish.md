# Task: Polish §3 Method

You are a senior ML researcher helping write a paper on mechanistic interpretability of audio-language models.

## Context

Read these files first:
- `docs/paper-a-method.md` — current §3 Method draft (has TODOs)
- `docs/paper-a-outline.md` — §3 outline and theoretical framing
- `docs/paper-a-draft.md` — full paper draft context

## Your task

Produce an improved `docs/paper-a-method.md` with the following goals:

### 1. Fill conceptual TODOs (do NOT invent empirical values)
- `[TODO: threshold, calibrated via bootstrap]` → write a concrete calibration procedure: "We set δ via a bootstrap null distribution: for each feature, we compute IIA(f; A+T) under 1000 random label permutations and set δ as the 95th percentile of this null distribution."
- `[TODO: ε threshold]` → "We set ε = 0.05, matching the noise floor of random IIA estimates in pilot experiments."
- `[TODO: cite]` for statistical criteria → cite "Efron & Hastie (2016)" for bootstrap CI recommendations
- For GPU/data TODOs: mark as `[PENDING: requires experimental data]` rather than inventing numbers

### 2. Improve prose quality
- All paragraphs should have clear topic sentences
- Remove redundancy between subsections
- Ensure notation is consistent throughout (gc(k), IIA, α_AND, α_OR)
- Make the AND/OR gate decomposition section cleaner and more precise
- Add transition sentences between major subsections (§3.1→§3.2→§3.3)

### 3. Add a subsection §3.5 "Scope and Limitations"
Write 3-4 paragraphs covering:
- Current experiments focus on Whisper-base (encoder-only); full ALM analysis (Qwen2-Audio) is pending GPU access
- Mock experiments validate algebraic framework but not neural behavior
- gc(k) measures linear causal influence; nonlinear contributions not captured
- Pre-registration of predictions for ALME conflict items and MPAR² RL shift

### Output
Write the complete updated `docs/paper-a-method.md`. Maintain all LaTeX notation. Keep it rigorous and concise (target: ≤250 lines).
