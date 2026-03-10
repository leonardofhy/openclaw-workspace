# Paper A — Appendix A: Pre-Registration Protocol

> **Status**: Draft v1.0 | Cycle: c-20260307-1045 | Track: T3
> **Purpose**: Nanda-style pre-registration of hypotheses, falsification criteria, and confound controls for "Localizing the Listen Layer in Speech LLMs"
> **To be submitted**: OSF / arXiv ancillary (before first GPU run)

---

## A.1 Motivation: Why Pre-Register?

Mechanistic interpretability research faces a specific replication problem: the researcher can always post-hoc choose which layer to call "important" after seeing gc(k) curves. Pre-registration closes this loophole by committing, before any real-data run, to:

1. Exactly which hypothesis constitutes success
2. Exactly which observations would falsify it
3. Exactly how confounds will be tested

This document follows Nanda et al. (2023) "Progress measures for grokking via mechanistic interpretability" Appendix conventions: binary outcome framing + explicit null results.

---

## A.2 Core Hypothesis and Uncertainty Framing

### Primary Hypothesis (H1 — Listen Layer Localization)

> **H1**: In Whisper-small, gc(L) peaks at a single encoder layer L* satisfying the **peak condition** (bootstrap 95% CI at L* does not overlap CIs at L*±1 and L*±2; lower CI bound at L* > gc(floor_layer) + 0.05). L* falls in the range [2, 4] (50% encoder depth ± 1 layer).

**Certainty estimate**: ~60% (Nanda-style calibrated prior).

Rationale for uncertainty: We have prior evidence from MFA (Shafran et al. 2025) that phonological separation peaks at mid-encoder depths. DAS adds a *causal* filter — it is possible that the representational peak (MFA) does not coincide with the causal peak (DAS/gc), in which case H1 fails gracefully.

### Secondary Hypothesis (H2 — Cross-Model Transfer)

> **H2**: The gc-peak layer L* (as a fraction of total encoder depth) is consistent (within ±10%) across Whisper-small and Qwen2-Audio-7B encoder.

**Certainty estimate**: ~45%. Qwen2-Audio uses a different encoder depth; absolute layer indices differ. The fractional-depth invariance would constitute strong evidence for a universal Listen Layer principle.

### Null Hypothesis (H0 — Distributed Encoding)

> **H0**: gc(L) < 0.55 at all layers, or the peak condition is not met by any layer. Interpretation: audio grounding is diffuse across encoder layers; no single Listen Layer exists.

H0 is not a failure — it is a publishable result (reframes Paper A as characterizing the *absence* of localized grounding, motivating LALM-level analysis in E2).

---

## A.3 Falsification Criteria

Exactly **three conditions** would falsify H1:

### FC1 — Peak out of predicted range

**Condition**: gc(L) peaks at L ∉ [2, 4] in Whisper-small (e.g., peaks at L = 5 = last encoder layer).

**Consequence**: H1 is falsified. Paper reframes as "Late-layer audio grounding: the Listen Layer is a semantic head, not a mid-encoder transition." The core claim (existence of a localized Listen Layer) survives; only the depth-prediction is wrong.

**Decision point**: If L* = 5, we do NOT cherry-pick a secondary peak at L = 3 to save H1. We report L* = 5 and update the narrative.

### FC2 — Peak condition not satisfied (statistically)

**Condition**: The bootstrap 95% CI at argmax(gc) overlaps the CIs at ±1 or ±2 neighbors, indicating the "peak" is not significantly isolated.

**Consequence**: H1 is falsified statistically. We report the gc curve without claiming localization. If H0 is met (gc < 0.55 everywhere), we declare H0. If gc peaks but is non-isolated, we report "weak grounding peak" with discussion.

**Decision point**: 1000 bootstrap resamples are non-negotiable. We do not switch to permutation tests or lower the CI threshold to 90% to rescue H1.

### FC3 — Baseline B1 (random-init DAS) ≥ trained DAS at L*

**Condition**: gc_trained(L*) − gc_random(L*) < 0.05.

**Consequence**: DAS is not learning a meaningful subspace; gc(k) results are artifacts of the patching geometry, not causal grounding. The experiment is uninformative. We report the failure mode and diagnose (likely: DAS training diverged, or the subspace dimension was wrong).

**Decision point**: If FC3 triggers, we re-run DAS with corrected hyperparameters (one re-run allowed before filing as "method failure"). This re-run must be pre-declared — we are declaring it here.

---

## A.4 Confound Controls

Exactly **two confound classes** must be ruled out before the main result is claimed:

### CC1 — Polysemanticity / Dimensionality Confound

**Risk**: gc(L) peaks at L* simply because that layer has the lowest-rank activation structure (easy to patch), not because it encodes audio features causally. DAS would then be exploiting activation geometry, not semantics.

**Control procedure**:
1. Compute **decomposability score** decomp(L*): train two DAS rotations simultaneously — one for voicing (voiced/unvoiced), one for phoneme identity (vowel/consonant). Measure the angular separation between the two learned subspaces. decomp(L*) = sin(θ) where θ = angle between subspace principal axes.
2. **Threshold**: decomp(L*) > 0.7 required to claim that voicing and phoneme-identity are decomposable at L* (not polysemantically entangled).
3. If decomp(L*) < 0.7: we report "Listen Layer is polysemantic at L* — multiple phonological features are entangled in the same causal subspace." This is scientifically interesting but limits the decomposition claim.

**Reporting**: Always report decomp(L*) in the paper regardless of outcome.

### CC2 — Stimulus Distribution Confound

**Risk**: gc(k) results depend on the specific stimulus pairs chosen (e.g., voiced-unvoiced pairs from LibriSpeech may be confounded with speaker identity, noise level, or utterance length).

**Control procedure**:
1. **Matched pairs**: stimulus pairs are matched on utterance duration (±200ms), speaker ID (same speaker for both stimuli in a pair), and SNR (±3dB). Matching criteria are applied before any gc computation.
2. **Out-of-distribution probe**: After main results, re-run gc on a held-out stimulus set from a different corpus (TEDLIUM-3 or CommonVoice). Report Δgc = |gc_main(L*) − gc_ood(L*)| as a generalization measure.
3. **Threshold for claiming generalization**: Δgc < 0.08 (empirically motivated; larger deltas indicate corpus-specific encoding).

**Reporting**: If Δgc > 0.08, we scope the claim to LibriSpeech-style stimuli and flag it as a limitation.

---

## A.5 Decision Tree (Summary)

```
Run experiments
    │
    ├─ FC3 triggered? → DAS failure → fix and re-run (1x) or report method failure
    │
    ├─ H0 met (gc < 0.55 everywhere)? → Distributed encoding result → pivot narrative
    │
    ├─ Peak condition met?
    │   ├─ YES → Check L* range
    │   │         ├─ L* ∈ [2,4]: H1 confirmed → claim localized Listen Layer
    │   │         └─ L* ∉ [2,4]: H1 partially falsified → reframe (late-layer)
    │   └─ NO  → FC2 triggered → weak grounding, no localization claim
    │
    └─ Apply confound controls CC1, CC2 (always, regardless of above)
```

---

## A.6 What We Will NOT Do

- ❌ Report only the "best" stimulus pair post-hoc
- ❌ Switch from bootstrap to permutation tests if bootstrap CIs are inconvenient
- ❌ Declare L* = argmax(gc) without checking the peak condition
- ❌ Omit decomp(L*) or Δgc even if they hurt the story
- ❌ Run Experiment 2 (Qwen2-Audio, GPU) before E1 (Whisper, CPU) results are analyzed

---

## A.7 Artifact Roadmap

| Artifact | Status | Blocks |
|----------|--------|--------|
| `gc_eval.py` — DAS gc(k) harness | ✅ scaffold built | E1 run |
| `synthetic_stimuli.py` — stimulus generator | ✅ built | E1 run |
| `decomp_score.py` — decomposability metric | ⬜ not started | CC1 |
| `ood_probe.py` — out-of-distribution gc | ⬜ not started | CC2 |
| `bootstrap_ci.py` — bootstrap wrapper | ⬜ not started | Peak condition |
| LibriSpeech matched pairs CSV | ⬜ not built | E1 real data |
| TEDLIUM-3 held-out pairs CSV | ⬜ not built | CC2 |

---

*This document is to be frozen (no edits) before the first real-data run on E1.*
*Amendments require a new version number and justification log.*
