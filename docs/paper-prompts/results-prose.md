# Task: Improve §4 Results Prose

You are a senior ML researcher helping write a paper on mechanistic interpretability of audio-language models.

## Context

Read these files first:
- `docs/paper-a-results.md` — current §4 Results (mix of real + mock data)
- `docs/paper-a-results-stub.md` — alternative stub with partial real data
- `docs/paper-a-outline.md` — section outline
- `docs/paper-a-draft.md` — full paper draft

## Your task

Produce an improved `docs/paper-a-results.md` with the following goals:

### 1. For real experiment sections (Q001, Q002)
- **Q001 (Voicing Geometry)**: Layer 5 has real data (Stop–Stop cos_sim = +0.25, Stop–Fricative ≈ 0.0). Write narrative for this finding. For other layers, leave `[PENDING: Whisper-base GPU run]` placeholders. Add interpretation: "The peak at layer 5 (~83% encoder depth) is consistent with Choi et al.'s (2026) finding that phonological features crystallize at intermediate depths."
- **Q002 (Causal Contribution)**: Write the narrative framing for zero/noise/mean ablation results. Leave tables as `[PENDING]` but add prediction text: "We expect layers 4-6 to show highest WER degradation under ablation, consistent with Q001's phonological crystallization at layer 5."

### 2. For mock experiment sections (§4.2–§4.5)
- Each mock experiment section should have:
  a. **Setup** (1 sentence): what the mock circuit tests
  b. **Result** (1-2 sentences): what was found (median |r| = 0.877 across experiments)
  c. **Interpretation** (1-2 sentences): what this means for the framework
  d. **Limitation** (1 sentence): "This is a framework validation experiment; the result holds for numpy circuits, not real models."
- Make the mock/real distinction prominent and honest throughout

### 3. Add a clear §4.6 "Summary and Pre-registered Predictions"
Write a summary table (markdown) mapping:
- Experiments completed (real): Q001 partial, Q002 pending
- Experiments validated (mock): 27 experiments, median |r| = 0.877
- Pre-registered predictions: 3 specific testable claims for Whisper-small/medium scale-up

### 4. Tone
- Be precise about what IS vs IS NOT established
- Real data claims need qualifiers ("preliminary evidence suggests...")
- Mock data claims need explicit labeling ("In our numpy mock circuit, ...")

### Output
Write the complete updated `docs/paper-a-results.md`. Target: ≤250 lines. Preserve all existing tables.
