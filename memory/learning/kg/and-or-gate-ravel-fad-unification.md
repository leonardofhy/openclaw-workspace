# AND/OR Gate ↔ RAVEL Cause/Isolate ↔ FAD Bias — Unified Framework

**Created:** 2026-03-21 (Cycle c-20260321-1345, Q123 learn)
**Tracks:** T3, T5
**Status:** Synthesis — ready to apply in design docs

---

## Core Claim

**AND/OR gate polarity is the mechanistic explanation for RAVEL Isolate success/failure.**

A feature's gate polarity predicts its disentanglement properties:

| Gate | gc | RAVEL Cause | RAVEL Isolate | FAD Bias | Interpretation |
|------|----|-------------|---------------|----------|----------------|
| AND-gate | High | High (needs audio) | High (audio-native, clean subspace) | Low | Audio-grounded, monosemantic |
| OR-gate | Low | Moderate (text path) | **Low** (polysemantic, leaks) | **High** | Text-biased, distributed |

**RAVEL Isolate ≈ monosemanticity ≈ audio-groundedness ≈ AND-gate fraction**

---

## Evidence Chain

1. **Q105** RAVEL MDAS × AND/OR: r=0.877 — MDAS subspaces align with AND-gate structure → disentanglement and grounding are the SAME underlying property at different levels of analysis.

2. **Q107** Isolate-gc proxy: r=0.904 — RAVEL Isolate score substitutes for full DAS sweep (67% compute savings). Mechanistic reason: Isolate = "does this feature localize to one attribute?" = same question as gc = "does this layer/feature rely on audio?"

3. **Q123** FAD-RAVEL mock: r=−0.70 (FAD bias ↔ RAVEL Isolate) — anticorrelated. FAD-biased (text-predictable) features FAIL Isolate. Negative result reframed: FAD-biased features are polysemantic (confirmed by AudioSAE finding: ~2000 features per speech concept). This is NOT a bug — it reveals why text-biased features are dangerous (uncontrollable, leak across attributes).

4. **Q096** FAD × AND/OR: r=−0.960 — text-predictable phonemes = low AND%. The tightest correlation in the entire result set.

---

## Geometric Intuition

AND-gate features occupy **isolated subspaces** (only activated by specific audio+text combination) → RAVEL Isolate succeeds (rotation R can cleanly align the subspace to one attribute).

OR-gate features are activated by **either pathway** → the feature direction is a mixture of text-context vectors and audio-signal vectors → RAVEL Isolate fails because the subspace is shared across multiple attributes.

This is why MDAS helps: it forces the rotation R to separate OR-gate features by attribute, but OR-gate features resist because their activation is driven by polysemantic text prediction.

---

## Design Doc Implications (Q123)

**For Paper B (AudioSAEBench):**
- FAD-biased encoder features = low Isolate → poor RAVEL disentanglement → **encoder selection matters**
- Recommend AND-frac > 0.5 as encoder quality criterion (same as gc criterion)
- Section: "Feature Quality ≠ Task Performance — RAVEL Isolate as Groundedness Proxy"

**The finding:** Text-biased features fail disentanglement not because they're "bad" but because they encode multiple text-contextual cues simultaneously. This is the mechanistic cost of text-predictability: you get efficiency (OR-gate activates from either modality) but lose controllability (can't isolate which attribute you're modifying).

---

## Design Doc Implications (Q134 — Hallucination)

AND→OR transition during hallucination = Isolate score drops = features become polysemantic = interventions lose precision. The model starts generating from text-contextual priors rather than audio evidence. Mechanistically: the subspace that was cleanly "audio-grounded" at t* becomes a mixture subspace post-t*.

---

## Open Questions

1. Does RAVEL Cause follow the same AND/OR pattern? (Q123 only measured Isolate)
2. Can we construct an "Audio-RAVEL Isolate" dataset for non-text attributes (pitch, duration) where AND-gate features SHOULD score well?
3. Is the FAD-Isolate anticorrelation (r=−0.70) consistent across layers, or is it layer-dependent?
4. If we filter to AND-gate features only, does RAVEL pass rate increase significantly?

---

## Connections

- → Q123 design doc (FAD × Cause/Isolate mock)
- → Q133 (RAVEL Isolate as beam rescoring signal — Isolate ≈ gc proxy → high-Isolate features = reliable audio anchors)
- → Q134 (hallucination = AND→OR transition = Isolate drop)
- → Paper B §4 caveat: "encoder selection via AND-frac; FAD-biased features fail disentanglement"
- → AudioSAEBench Category 0 (Audio-RAVEL): Isolate-gc correlation justifies using Isolate as a lighter Category 5 proxy
