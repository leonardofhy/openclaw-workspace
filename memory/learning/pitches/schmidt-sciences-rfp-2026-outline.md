# Schmidt Sciences 2026 Interpretability RFP — Proposal Outline

> Created: 2026-03-26T17:15+08:00 (cycle c-20260326-1715)
> Track: T5 (Listen-Layer Audit) | Deadline: May 26, 2026
> Based on: Peter Hase's RFP posting (LessWrong/AF, 2026-03-13)

---

## 1-Sentence Pitch

We propose **AND-frac + Power Steering** as a mechanistically grounded framework to (1) detect when speech LLMs "stop listening" to safety-relevant audio features (deception detection) and (2) reinstate correct routing via Jacobian singular vector steering (mitigation).

---

## RFP Alignment

Schmidt Sciences asks: **Can interpretability methods detect deceptive behaviors and steer reasoning to eliminate them?**

| RFP Requirement | Our Approach |
|-----------------|-------------|
| Detect deceptive behaviors | AND-frac anomaly at Listen Layer L* flags when model routes around safety constraints |
| Steer reasoning to eliminate them | Power Steering SVs of J_{L*→safety_layer} reinstate AND-gate behavior at L* |
| Generalize beyond benchmarks | Audio domain is novel; mechanisms are model-agnostic (Whisper, Qwen2-Audio, SALMONN) |
| Address concrete risks | Audio jailbreaks bypass text-only defenses — underexplored vector with real deployment risk |

---

## Core Narrative

### The Problem
Audio-language models (ALMs) can be manipulated via audio-modality attacks that bypass text-level safety filters. Existing defenses are surface-level; none exploit the model's internal audio-processing structure as a safety signal.

### Key Insight 1: AND-gate structure = safety signal
From Paper A (Listen vs. Guess): there exists a narrow "Listen Layer" L* where the model gates its decision on audio. We measure this via **AND-frac** — the fraction of neurons that fire only when *both* audio and text features are present (AND-gate, not OR-gate).

- **Normal query**: High AND-frac at L* → model is "listening" to audio
- **Jailbreak / deceptive input**: AND-frac suppressed → model has been manipulated into ignoring safety-relevant audio features

**This is the detection mechanism**: AND-frac < threshold at L* = deceptive audio input alert.

### Key Insight 2: Jacobian SVs = targeted intervention
From Power Steering (Ayyub 2026): the right singular vectors of J_{L*→target} identify directions that maximally propagate L* signals downstream. These are cheap to compute (~15 forward passes, power iteration, no explicit Jacobian formation).

**Proposed intervention**: When AND-frac flags a deceptive input, add the top SV of J_{L*→decoder} to the L* activation. This "reinstates" AND-gate routing — the model is steered back to consulting safety-relevant audio features.

**Why it's adversarially robust**: An attacker evading AND-frac must maintain normal AND-gate structure *while* achieving the manipulation — conflicting objectives.

---

## Research Plan (12 weeks, fits May 26 deadline)

### Phase 1: Detection (Weeks 1–4) — CPU, Tier 1
- Compute AND-frac on JALMBench 246-query benchmark (Whisper-base, SALMONN)
- Establish ROC curve: AND-frac anomaly vs. benign baseline
- Validate: do jailbreak queries show suppressed AND-frac at L*?
- **Deliverable**: Detection paper section + ROC results table

### Phase 2: Mechanism (Weeks 3–6) — CPU/GPU
- Compute J_{L*→decoder} top SVs for benign vs. jailbreak samples (Whisper-base)
- Test correlation: high AND-frac ↔ large top SV magnitude (model is "committed" to audio)
- Replicate on Qwen2-Audio-7B (GPU needed)
- **Deliverable**: Mechanism section + correlation plots

### Phase 3: Mitigation (Weeks 5–10) — CPU/GPU
- Implement Power Steering intervention at L*: add top J SV when AND-frac below threshold
- Measure: does intervention recover normal AND-frac? Does jailbreak success rate drop?
- Ablation: SV direction vs. random direction vs. contrastive steering (CAA baseline)
- **Deliverable**: Mitigation section + ablation table

### Phase 4: Writeup + Submission (Weeks 10–12)
- Full paper draft (Interspeech 2026 or NeurIPS safety track if accepted to submit)
- Schmidt Sciences deliverables: report + code release

---

## Novelty Claims

1. **First mechanistic interpretability work on audio safety** — prior work (SPIRIT, SALMONN-Guard) uses surface signals
2. **AND-frac as deception detector** — novel application of circuit-level gates to safety
3. **Cross-modal power steering** — extending Ayyub's text-model SVs to speech-text models
4. **Adversarial robustness by design** — mechanism-based defense vs. empirical defense

---

## Resources Required

| Resource | Status |
|---------|--------|
| Whisper-base (Tier 1 experiments) | ✅ Available, eval harness done |
| JALMBench benchmark | ✅ 246 queries available |
| Qwen2-Audio-7B | ⚠️ Need GPU (Leo approval) |
| SALMONN (safety experiments) | ⚠️ Need GPU access |
| Compute budget | ~$200-500 GPU hours for full study |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| AND-frac doesn't separate jailbreaks cleanly | Fall back to gc(L) anomaly score (existing Paper A work) |
| Qwen2-Audio access blocked | Focus on Whisper + open models first |
| Power steering vector unstable across inputs | Report per-input SV distribution; use ensemble SV |
| Timeline too tight | Phases 1+2 sufficient for initial Schmidt submission |

---

## Fit with Track T5 (MATS / Paper C)

This proposal *is* Paper C. The MATS proposal (exec-summary.md) establishes the detection angle; Schmidt adds the mitigation angle (Power Steering). The combined narrative is stronger for Schmidt than MATS since Schmidt explicitly asks for both detect + mitigate.

**Recommendation for Leo**: Submit Schmidt Sciences RFP as Paper C's funding vehicle. Redirect MATS application energy here if MATS doesn't pan out.

---

## Next Steps

1. **Leo reviews this outline** — confirm narrative + novelty framing ✅/✗
2. **Q182 build**: Compute J_{L*→decoder} SVs + AND-frac correlation on Whisper-base (CPU, Tier 1)
3. **Q184 (to add)**: Write Schmidt Sciences full proposal draft based on this outline (after Leo confirms)
4. **Discuss**: GPU access plan for Qwen2-Audio (needed for Phase 2+)

---

*Outline written by autodidact cycle c-20260326-1715. Leo should review before full proposal draft.*
