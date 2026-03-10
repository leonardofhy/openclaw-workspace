# Joint Pre-Registration: T3 × T5 Combined Falsification Criteria

> **Status**: Draft v1.0 | Cycle: c-20260309-1015 | Q009
> **Tracks**: T3 (Listen vs. Guess — Paper A) + T5 (Listen-Layer Audit — Paper C / MATS)
> **Purpose**: Unified pre-registration committing to falsification criteria for both papers before any real-data run.
> **Scope**: This doc governs what counts as success/failure and how ambiguous outcomes are resolved.
> **To be frozen**: Before first real-data E1 run on either track.

---

## 0. Why a Joint Pre-Registration?

T3 and T5 share the same core mechanism claim: **the Listen Layer boundary (detected via gc(k)) is causally important for audio understanding and safety**. Their hypotheses are logically coupled:

- If T3's H1 fails (no localized Listen Layer in Whisper), T5's safety claim weakens — gc(k) can't serve as a jailbreak detector if it doesn't localize a meaningful boundary.
- If T5's experiments show gc(k) *does* separate jailbreak/benign audio but T3's localization fails, we reframe: gc(k) detects distributional shift even without strict localization.

Joint pre-registration forces us to commit to this coupling explicitly rather than post-hoc choosing whichever paper survived.

---

## 1. T3 Hypotheses (Paper A: "Localizing the Listen Layer")

*Full version in `paper-a-prereg.md`. Reproduced here for joint reference.*

### H1 — Listen Layer Localization
> gc(L) peaks at L* in Whisper-small satisfying the **peak condition** (bootstrap 95% CI at L* non-overlapping with L*±1 and L*±2; lower CI > gc(floor) + 0.05). L* ∈ [2, 4].

**Certainty prior**: 60%

### H2 — Cross-Model Transfer
> The fractional-depth peak is consistent within ±10% across Whisper-small and Qwen2-Audio-7B.

**Certainty prior**: 45%

### H0 — Distributed Encoding (T3 null)
> gc(L) < 0.55 at all layers, or peak condition not met.

---

## 2. T5 Hypotheses (Paper C: "Audio Jailbreak Detection via Listen-Layer Probing")

### H3 — gc(k) Jailbreak Signal
> The mean gc(k) score at L* (from T3) for jailbreak audio inputs is at least 0.15 higher than for benign audio inputs (Mann-Whitney U, p < 0.01, Bonferroni-corrected for n=3 experiment families).

**Certainty prior**: 55%

Rationale: If jailbreak audio routes through a different mechanistic path (bypassing semantic binding at the listen layer), gc(k) should be elevated — the model is "guessing" rather than "listening" at the critical boundary.

### H4 — Causal Intervention Efficacy
> Causal patching of the top-k listen-layer features (identified via gc(k) at L*) reduces jailbreak compliance rate by ≥40% relative to unpatched baseline (paired binomial test, p < 0.05). Random feature ablation (matched k) must show <10% compliance reduction (control).

**Certainty prior**: 40%

Rationale: Causal necessity test. If gc(k)-identified features are not specifically causal for jailbreak compliance, the framework's intervention value is limited to detection (not mitigation).

### H5 — Zero-Shot Transfer of gc(k) Probe
> A logistic probe trained on gc(k) features for jailbreak Family A achieves ≥70% AUC on Family B (zero-shot), and a text-token baseline is outperformed on transfer AUC by ≥5 percentage points.

**Certainty prior**: 40%

### H0-T5 — No Jailbreak Signal (T5 null)
> Mean gc(k) difference ≤ 0.05 between jailbreak and benign; or Mann-Whitney p > 0.05. Interpretation: audio jailbreaks exploit semantic alignment failure, not acoustic boundary exploitation.

---

## 3. Joint Falsification Criteria (Cross-Paper)

### JFC1 — T3 Failure Propagation Rule
**Condition**: T3 H0 is confirmed (no localized Listen Layer).
**Consequence for T5**: T5 H3/H4 are re-anchored. Instead of using L* from T3, we use argmax(gc) even if peak condition is not met (report as "approximate listen-layer boundary"). T5 results are flagged as "exploratory" rather than "confirmatory."

**Decision point**: If JFC1 triggers, we do NOT cancel T5 — we reframe its claims as detection (not mechanistic) and degrade to an arXiv preprint rather than a conference submission.

### JFC2 — Divergent Results Rule
**Condition**: T3 H1 is confirmed (localized L* exists) AND T5 H0-T5 is confirmed (no jailbreak signal at L*).
**Consequence**: gc(k) localizes a boundary that is not exploited by audio jailbreaks. This is a **publishable null for T5** — it constrains where jailbreak exploitation does NOT occur, redirecting to deeper LLM layers. T3 is unaffected.

**Decision point**: T5 is rewritten as "Audio Jailbreaks Are Not Acoustic: Evidence from Listen-Layer Probing." We do not search for a different layer that gives a significant result.

### JFC3 — gc(k) Validity Check (shared)
**Condition**: In both T3 and T5, gc_trained(L*) − gc_random(L*) < 0.05 at the claimed L*.
**Consequence**: DAS is not functioning; neither paper's causal claims hold. Both papers are suspended pending DAS repair (one re-run allowed per track).

**Decision point**: This is a method-level failure. We report it and diagnose the cause (training instability, subspace dimension mismatch, patching implementation bug). Fix must be documented in a new version of this pre-registration before re-running.

---

## 4. Confound Controls (Joint)

### CC-J1 — Shared Stimulus Confound
**Risk**: gc(k) differences between conditions (voiced/unvoiced for T3; jailbreak/benign for T5) are driven by acoustic properties (duration, SNR, speaker) rather than semantic/safety content.

**Control (both tracks)**:
- Stimuli matched on: duration (±200ms), speaker ID, SNR (±3dB)
- CC-J1 test: fit a linear model predicting gc(k) from acoustic confounds only (duration, SNR, f0). Partial R² of acoustic predictors must be < 0.2 before the semantic effect is claimed.
- If partial R² ≥ 0.2: we add acoustic features as covariates in main analysis and flag confound risk in the paper.

### CC-J2 — Cross-Corpus Generalization (both tracks)
- T3: Δgc < 0.08 between LibriSpeech and TEDLIUM-3 held-out set (see paper-a-prereg A.4/CC2).
- T5: AUC drop < 10 percentage points between GCG-audio jailbreaks and PAIR-audio jailbreaks (same probe, different attack family).
- If either threshold is violated: scope is limited to the in-distribution corpus; limitation section required.

### CC-J3 — Multiple Comparison Control (T5 only)
- T5 runs 3 experiment families (H3, H4, H5). Bonferroni correction applied (α = 0.05/3 ≈ 0.017 per test).
- We do NOT drop to α = 0.05 per test after seeing results. No post-hoc family selection.

---

## 5. Decision Tree (Joint)

```
Run T3 first (CPU, Whisper-small)
        │
        ├─ JFC3 triggered (both)? → DAS broken → fix → re-run (1x each)
        │
        ├─ T3 H0 (distributed)? → JFC1 → T5 becomes exploratory
        │
        └─ T3 H1 confirmed?
                │
                ├─ Use L* for T5 experiments
                │
                ├─ T5 H3 significant?
                │   ├─ YES → test H4 (causal patching) → test H5 (transfer)
                │   └─ NO  → JFC2 → T5 null result (reframe)
                │
                └─ Apply CC-J1, CC-J2 regardless of outcome
```

---

## 6. Shared "What We Will NOT Do" List

- ❌ Run T5 experiments before T3 E1 results are analyzed (T3 gates L*)
- ❌ Use L* from T5 results to backfill T3's peak-condition check
- ❌ Report only the attack family that gave significant results in T5
- ❌ Run additional jailbreak families after seeing H3/H4 results without a new pre-registration amendment
- ❌ Claim H5 transfer if the text-token baseline outperforms gc(k) probe
- ❌ Apply a different statistical test after observing the data distribution

---

## 7. Amendment Protocol

If any experiment reveals a condition not covered above, we:
1. Write an amendment (new section "A-vX" in this file with date and justification)
2. Freeze the amendment before running the affected experiment
3. Report both the original and amended criterion in the paper

Amendments require Leo sign-off (async Discord DM is sufficient).

---

## 8. Artifact Dependency Map

| Artifact | Track | Status | Required by |
|----------|-------|--------|-------------|
| `gc_eval.py` — DAS gc(k) harness | T3 | ✅ scaffold | H1, H3, JFC3 |
| `synthetic_stimuli.py` — stimulus generator | T3 | ✅ built | H1 |
| `bootstrap_ci.py` — peak condition check | T3 | ⬜ | H1 peak condition |
| `decomp_score.py` — decomposability | T3 | ⬜ | CC1 (in paper-a-prereg) |
| `jailbreak_gc_detect.py` — jailbreak thermometer | T5 | ✅ scaffold (Q006) | H3 |
| `causal_patch.py` — activation patching | T5 | ⬜ | H4 |
| `gc_probe_transfer.py` — probe transfer eval | T5 | ⬜ | H5 |
| LibriSpeech matched pairs CSV | T3 | ⬜ | H1 real data |
| GCG-audio / PAIR-audio jailbreak set (~100) | T5 | ⬜ | H3-H5 |
| TEDLIUM-3 held-out pairs | T3/T5 | ⬜ | CC-J2 |

**Critical path**: gc_eval.py → (bootstrap_ci.py + matched pairs) → T3 E1 → T5 H3 → H4 → H5

---

*This document is to be frozen before the first real-data run on T3 E1.*
*Version: v1.0 | Author: Little Leo (Lab) | Date: 2026-03-09*
