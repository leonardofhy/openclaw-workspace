# ENV Taxonomy ↔ RVQ Hierarchy ↔ AND/OR Gate — Triple Alignment

**Created:** 2026-03-21 (Cycle c-20260321-1745, Q126 learn)
**Tracks:** T5, T3
**Status:** Design doc — ready for CPU mock

---

## Core Claim

**Feature graph connectivity class (ENV) predicts codec residual layer (RVQ) and gate polarity (AND/OR).**

| ENV Class | RVQ Layer | Gate | Semantic Level | Intervention Effect |
|-----------|-----------|------|---------------|---------------------|
| ENV-1 (hub) | RVQ-1 (coarse) | OR-gate | Semantic / speaker / broad phoneme | Global semantic shift |
| ENV-2 (intermediate) | RVQ-2..4 | Mixed | Mid-level prosody | Moderate, attribute-specific |
| ENV-3 (isolated) | RVQ-N (fine residual) | AND-gate | Fine acoustic / timbre / detail | Local, surgical acoustic change |

All three taxonomies (topology, codec, gate) are measuring the **same underlying property**: 
*how broadly vs. narrowly a feature is grounded in the audio signal.*

---

## Mechanistic Chain

```
Coarse grounding (ENV-1/RVQ-1/OR):
  - Activated by many audio patterns (hub = high in-degree)
  - OR-gate: text context alone can activate (text-predictable)
  - RVQ-1: captures semantics that survive heavy compression
  - Result: hard to isolate (RAVEL Isolate low), polysemantic, global intervention

Fine grounding (ENV-3/RVQ-N/AND-gate):
  - Activated by specific audio+context combination
  - AND-gate: needs BOTH audio signal AND context (audio-grounded)
  - RVQ-N: captures residual after semantic info removed
  - Result: cleanly isolatable (RAVEL Isolate high), monosemantic, surgical intervention
```

---

## Testable Predictions

1. r(ENV-1 activations, RVQ-1 token probe) > r(ENV-1 activations, RVQ-N token probe)
2. r(ENV-3 activations, RVQ-N token probe) > r(ENV-3 activations, RVQ-1 token probe)
3. ENV-3 features have AND-frac > ENV-1 features (links to Q096)
4. FGSM adversarial attacks on RVQ-N tokens collapse ENV-3 feature activations (Q129 prediction)
5. Hallucination onset (t*) = ENV-3 feature dropout = model falls back to RVQ-1-level generation

---

## Intervention Protocol (per ENV type)

- **Target ENV-1:** Swap RVQ-1 codebook tokens → semantic identity transfer (speaker clone, accent shift)
- **Target ENV-3:** Swap RVQ-N tokens → fine acoustic modification (denoise, timbre edit, adversarial perturbation)
- **Safety implication:** Jailbreak detection should monitor ENV-3 feature activations (AND-gate, RVQ-N level) — adversarial audio manipulates fine acoustic features to bypass safety classifiers

---

## Connections

- `kg/and-or-gate-ravel-fad-unification.md` — AND/OR gate framework (Q105, Q107, Q123)
- Q129 (Adversarial audio × t* detector) — attacks target ENV-3/RVQ-N features
- Q134 (Hallucination = AND→OR transition) — hallucination = ENV-3 feature dropout
- Q144 (T-SAE × Schelling × AND-gate triple alignment) — same triple alignment pattern
- Q145 (ENV-1 hub features as cross-language phoneme universals) — ENV-1 semantic universals via RVQ-1

---

## Open Questions

1. ENV-RVQ layer correspondence: constant across Whisper encoder layers, or layer-dependent?
2. Codec choice (EnCodec vs DAC) preserves ENV-RVQ alignment?
3. ENV-2 intermediate: maps to specific RVQ range or is task-dependent?
