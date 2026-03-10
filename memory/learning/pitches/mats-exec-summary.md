# MATS Research Task Proposal: Executive Summary
## "Listen-Layer Audit for Audio Jailbreak Detection & Emergent Misalignment Screening"

> Version: 1.0 | Created: 2026-03-06T19:45+08:00 (cycle c-20260306-1945)
> Track: T5 (Paper C / MATS) | Status: **Ready for Leo submission review**
> Full proposal: `memory/learning/pitches/mats-proposal-draft.md`

---

## 1-Sentence Pitch

We use causal mechanistic interpretability to locate the "Listen Layer" in speech LLMs and show its **gc(L) anomaly score** serves as a zero-shot, attack-agnostic jailbreak detector evaluated on the JALMBench 246-query benchmark — plus a pre-deployment risk screen for audio emergent misalignment.

---

## The Problem (2 sentences)

Audio-language models (ALMs) can be jailbroken via audio-modality attacks that bypass text filters (prosodic manipulation, multimodal conflict injection, adversarial audio). Existing defenses (SALMONN-Guard, SPIRIT, ALMGuard) use surface-level signals; **none exploit the model's own internal audio-processing structure as a safety signal**, and none are evaluated on a shared benchmark, making comparison impossible.

---

## Core Insight

From Paper A: there exists a narrow band of layers — the **Listen Layer** — where audio representations are *causally decisive* for model behavior (measured by grounding coefficient gc(L)). Under audio jailbreaks, this pattern becomes detectably abnormal:

- **Legitimate query**: gc(L) peaks sharply at L\*, then decays (model consulted audio, returned to text processing)
- **Jailbreak query**: gc(L) is suppressed, shifted, or shows anomalous cross-layer coupling

**Key advantage**: An attacker evading gc(L) detection must produce audio that preserves normal causal processing *while* achieving the jailbreak — conflicting objectives → adversarially robust by design.

---

## Dual-Use gc(k) Metric

| Application | When | Signal |
|-------------|------|--------|
| **Jailbreak Detector** | Inference time | gc(L) anomaly vs. benign baseline → ROC on JALMBench 246 queries |
| **EM Risk Screen** | Pre-deployment | Low baseline gc(k) → shallow audio grounding → higher fine-tune misalignment susceptibility |

---

## Why This Fits MATS

| Criterion | ✅ |
|-----------|---|
| Safety relevance | Audio jailbreaks = underexplored attack surface; detection is mechanistic, not heuristic |
| Mechanistic interpretability | gc(L) is a causal quantity; Listen Layer localization = MI core methodology |
| Tractable | CPU-feasible MVP (no GPU needed for prototype); defined deliverables with timelines |
| Novel niche | No prior work uses model-internal mechanisms as safety signal for audio attacks |
| Reproducible | JALMBench provides standardized benchmark → direct F1 comparison to SALMONN-Guard, SPIRIT, ALMGuard |
| Zero-shot | No attack-specific training; calibrated on benign data only |

---

## Research Tasks (All CPU-feasible for MVP)

| Task | Description | Tier | Output |
|------|-------------|------|--------|
| T1 | gc(L) baseline taxonomy on JALMBench benign queries | 0 | gc-curve shape taxonomy |
| T2 | Safety probe direction at Listen Layer L\* (MMProbe) | 0 | Linear safety direction + probe accuracy |
| T3 | gc(L) anomaly score + JALMBench ROC curve | 0 | ROC stratified by 5 attack paradigms |
| T4 | Comparison table vs. SALMONN-Guard / SPIRIT / ALMGuard | 0 | Per-paradigm F1 breakdown |
| T5 | gc(k) risk stratification on model checkpoints | 0 | High-listener vs. low-listener tier assignment |
| T6 | LoRA susceptibility probe (CPU mock / Tier 2 full) | 1/2 | EM delta: high-gc vs. low-gc checkpoint |

---

## Minimum Viable Deliverable

A **6-page technical report** for MATS:
1. Listen Layer localization method (brief recap from Paper A)
2. gc(L) baseline taxonomy (Task T1)
3. Safety probe direction at L\* (Task T2)
4. Anomaly score definition + ROC on JALMBench (Task T3)
5. Per-paradigm comparison table (Task T4)
6. Mechanistic defense argument + Audio EM risk screen (Tasks T5–T6 sketch)

**Does NOT require**: GPU, fine-tuning, harmful training data. Tasks T1–T5 = CPU-only.

---

## Key Differentiator vs. Prior Work

Prior defenses classify *what was said* (output) or *how attention flowed* (attention patterns); they fail on attacks that look normal at the surface but exploit the model's acoustic processing. Listen-Layer Audit asks: **did the model consult the audio normally?** — a *process signal*, not an output signal. This generalizes zero-shot to novel attack paradigms.

---

## Relationship to Ongoing Research

```
Paper A (Listen vs. Guess — grounding coefficient framework)
  └─→ Paper C / MATS (this proposal)
        ├─→ Use-Case 1: gc(L) anomaly = inference-time jailbreak detector
        └─→ Use-Case 2: gc(k) baseline = pre-deployment EM risk screen
  └─→ Paper B (AudioSAEBench — feature-level gc attribution)
```

---

## Open Questions for Leo / MATS Reviewers

1. **MATS track**: MI track + AI safety track are both relevant — which to lead with?
2. **Prototype model**: Prototype on Whisper (CPU) and extrapolate to Qwen2-Audio, or wait for GPU?
3. **Submission format**: Full research task proposal vs. short pitch (≤1 page)?
4. **Standalone vs. extension**: Present as standalone MATS project or as extension of Paper A?
5. **EM Task T6**: Stage as Tier 1 CPU mock first, then full GPU if MATS provides compute?

---

*Full proposal with detailed methodology, anti-confound checklist (10 items), and environment design principles: `mats-proposal-draft.md`*
