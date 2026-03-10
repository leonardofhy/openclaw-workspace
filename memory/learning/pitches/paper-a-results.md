# Paper A — Results Section Scaffold
**Track:** T3 (Listen vs Guess)
**Version:** v0.1 | **Date:** 2026-03-07
**Task:** Q068

---

## 4. Results (~800-word scaffold)

> **Note to Leo:** This is a scaffold with expected table formats, hypothesis headers, and placeholders (XXX).
> Fill in actual numbers after E1/E2 experiments run. All structural decisions are already made.

---

### 4.1 Overview

We report results across two experiments:

- **E1 (Whisper-small, CPU):** Does a localized Listen Layer exist? Measured via gc(k) curve + bootstrap CIs.
- **E2 (Token-level conditionality, CPU):** Does gc(k) covary with model confidence / prior strength? Measured via binned gc vs. unigram frequency.

All E1 and E2 results are CPU-feasible. GPU experiments (E3: Qwen2-Audio; E4: cross-model ablations) are deferred pending Leo approval.

---

### 4.2 Experiment E1: Localizing the Listen Layer in Whisper-small

**Hypothesis H1:** There exists a single layer $k^*$ in the Whisper-small encoder where gc(k) is significantly higher than adjacent layers and above chance.

**Table 1.** Grounding coefficient gc(k) across Whisper-small encoder layers.

| Layer k | gc(k) | 95% CI Lower | 95% CI Upper | Baseline (B1-Random) |
|---------|-------|-------------|-------------|----------------------|
| 0       | XXX   | XXX         | XXX         | XXX                  |
| 1       | XXX   | XXX         | XXX         | XXX                  |
| 2       | XXX   | XXX         | XXX         | XXX                  |
| 3       | XXX   | XXX         | XXX         | XXX                  |
| 4       | XXX   | XXX         | XXX         | XXX                  |
| 5       | XXX   | XXX         | XXX         | XXX                  |

*gc(k) = DAS-IIA at layer k (1000-resample bootstrap). B1-Random = DAS with random rotation.*

**Expected outcome (H1 supported):** gc(k) peaks at k ≈ 3 (mid-encoder) with non-overlapping CIs at k±2. Peak layer k* satisfies: lower CI > gc(B1-Random) + 0.05 at all layers.

**Decision rule:**
- H1 confirmed → claim "Listen Layer is localized at mid-encoder transition zone"
- H1 weakly confirmed (peak but CI overlaps k±1) → claim "grounding gradient with soft peak at k≈3"
- H1 rejected (flat gc curve) → claim "distributed encoding — no single Listen Layer" (still publishable; reframe §1)

---

**Table 2.** Comparison with baselines.

| Method | Peak Layer | Peak gc | Pass Peak Condition? |
|--------|-----------|---------|---------------------|
| DAS (ours) | XXX | XXX | XXX |
| B1: Random-init DAS | — | XXX ≈ 0.5 | N/A |
| B2: Vanilla activation patching | XXX | XXX | XXX |
| B3: MFA pre-screen (unsupervised) | XXX | — | — |

*B3 convergence: if DAS k* = MFA peak layer → convergent validity.*

---

### 4.3 Experiment E2: Listen vs Guess Conditionality on Prior Strength

**Hypothesis H2:** gc(k*) is lower for high-frequency, predictable tokens (model "guesses") and higher for rare, acoustically-driven tokens (model "listens").

**Table 3.** gc(k*) stratified by token unigram frequency.

| Frequency Bin | # Tokens | Mean gc(k*) | 95% CI |
|--------------|---------|------------|--------|
| Top 10% (common) | XXX | XXX | XXX |
| 10–50% | XXX | XXX | XXX |
| 50–90% | XXX | XXX | XXX |
| Bottom 10% (rare) | XXX | XXX | XXX |

**Expected outcome:** gc(k*) increases monotonically from common → rare bins (Δgc ≥ 0.1 across range).

**Secondary analysis:** gc(k*) vs. WER on matched utterance set.

| Group | WER | Mean gc(k*) |
|-------|-----|------------|
| Low-WER utterances | XXX | XXX |
| High-WER utterances | XXX | XXX |

*Expected: high-WER utterances have lower gc(k*) — model is guessing, not listening, on hard audio.*

---

### 4.4 Decomposability at k* (Supplementary)

**Hypothesis H3 (supplementary):** At k*, phonological sub-features (voicing, place, manner) are linearly separable into orthogonal subspaces (decomposability score decomp(k*) > 0.7).

| Sub-feature Pair | Subspace Angle (°) | Decomp Score |
|-----------------|-------------------|-------------|
| Voicing ⊥ Phoneme identity | XXX | XXX |
| Voicing ⊥ Pitch | XXX | XXX |
| Place ⊥ Manner | XXX | XXX |

*Target: all angles > 60° (near-orthogonal); decomp > 0.7 on all pairs.*

---

### 4.5 Summary

**Table 4.** Summary of main claims and supporting evidence.

| Claim | Evidence | Status |
|-------|---------|--------|
| Listen Layer is localized (H1) | Table 1: gc peak + peak condition | TBD |
| Listening correlates with acoustic need (H2) | Table 3: gc vs. frequency | TBD |
| Listen Layer is decomposable (H3) | Table 4: subspace angles | TBD |
| DAS > vanilla patching | Table 2: B2 comparison | TBD |
| MFA convergence | Table 2: B3 comparison | TBD |

---

### 4.6 Failure Mode Documentation (Pre-registered)

Per pre-registration (Q061), we report:

| Failure Mode | Observed? | Reframe / Mitigation |
|-------------|----------|---------------------|
| gc(k) flat at all layers | TBD | Pivot to "diffuse grounding" framing |
| k* at final encoder layer | TBD | "Semantic head as Listen Layer" — reframe §1 |
| DAS = vanilla (B2 parity) | TBD | Report; weaken DAS novelty claim |
| MFA ≠ DAS (no convergence) | TBD | Report divergence as finding; investigate |

---

## Writing Notes

- **§4.1**: 1 paragraph, funnel from E1→E2→deferred.
- **§4.2**: Results first, then baseline comparison. Do NOT over-explain tables — each table needs 2–3 sentence lead-in.
- **§4.3**: Short (150 words). Mainly the table + 1 conclusion sentence.
- **§4.4**: Move to Appendix if page-limited (Interspeech: 4+1 page).
- **§4.5**: Required — reviewers want a summary of what was shown.
- **§4.6**: Required per pre-reg commitment. Shows scientific integrity.

## Open Questions (to resolve before camera-ready)
- [ ] Which corpus for E1? Synthetic TTS only, or LibriSpeech dev-clean? (Ask Leo)
- [ ] N_samples for bootstrap? (Currently: 100 utterances × 1000 resamples — OK?)
- [ ] Table 2 B3 (MFA): is `sklearn.mixture.GaussianMixture` sufficient, or need the Shafran et al. implementation?
