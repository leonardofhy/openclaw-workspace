# Paper B §3 Outline: AudioSAEBench — Benchmark Design

> Created: 2026-03-06 (cycle #154, Q053)
> Status: Tier-0 structural outline — extracted + organized from paper-b-pitch.md §3 prose (v1.3)
> Purpose: Standalone §3 navigation doc for LaTeX writing; more structured than pitch embedding
> Word budget: ~1100 words prose (already drafted) + this outline = template for LaTeX §3
> Connection: Section 3 of AudioSAEBench paper (Paper B); ties to Paper A gc(k) at multiple points

---

## §3 Section Map

```
§3.1  Framework Overview               (~120 words)
§3.2  Category 0: Audio-RAVEL          (~200 words) ← most novel
§3.2b M9: Causal Abstraction Consistency (~150 words) [added c-20260312-0231]
§3.3  Category 1: Acoustic Concept Detection  (~150 words)
§3.3b M10: Schelling SAE Features      (~180 words) [added c-20260312-0401] ← NEW
§3.4  Category 2: Disentanglement & Completeness (~100 words)
§3.5  Category 3: Reconstruction Fidelity  (~80 words)
§3.6  Category 4: Causal Controllability   (~160 words)
§3.7  Category 5: Grounding Sensitivity    (~150 words) ← Paper A tie-in
§3.8  Training & Baseline SAEs (SAELens toolkit) (~100 words)
§3.9  Experimental Setup               (~80 words)
```

Total: ~1470 words (with M9+M10 extensions). May need §§ trimming for 9-page budget — M9+M10 can move to supplementary if space-constrained; keep 1-paragraph framing in main text only.

---

## §3.1 Framework Overview

**Key claims to make:**
- AudioSAEBench evaluates SAEs across 6 categories spanning Pearl's 3 causal levels (Joshi et al. arXiv:2602.16698)
- Theoretical spine: Geiger et al. arXiv:2301.04709 (causal abstraction — all MI methods are special cases)
- Sutter et al. NeurIPS 2025 Spotlight (arXiv:2507.08802): linearity constraint is necessary for non-trivial causal abstraction → ALL interventional categories use linear activation patching only
- Models benchmarked: Whisper-base/small/large-v3, HuBERT-base/large, WavLM-large, Qwen2-Audio-7B
- SAE variants: TopK, BatchTopK, Matryoshka (12+ SAEs total)

**Pearl hierarchy mapping (figure or table candidate):**

| Category | Pearl Level | Epistemic Strength |
|----------|-------------|-------------------|
| 1–3 (Concept, Disentanglement, Fidelity) | Level 1: Observational | Associational evidence |
| 4 (Causal Controllability) | Level 2: Interventional | Behavioral change evidence |
| 0 (Audio-RAVEL), 5 (Grounding Sensitivity) | Level 3: Counterfactual | Causal isolation evidence |

**LaTeX note:** This table is the anchor figure for §3.1. Draft in `figure-3-categories.tex`.

---

## §3.2 Category 0: Audio-RAVEL — Causal Disentanglement ⭐ PRIMARY NOVEL CONTRIBUTION

**Research question:** Does patching SAE feature F *cause* attribute A to change AND *isolate* the change (no collateral damage to other attributes)?

**Metrics:**
- `Cause(F, A)` — patching F produces expected change in attribute A (localization)
- `Isolate(F, A)` — patching F leaves OTHER attributes unchanged (isolation)
- `RAVEL-audio(F, A)` = harmonic mean(Cause, Isolate) — single composite score

**Stimulus design:**
- Minimal phonological contrast pairs from Choi et al. arXiv:2602.18899 (96 languages × voicing/manner/place)
- TTS-augmented pairs for controlled acoustic conditions
- Attribute set: voicing, manner of articulation, place of articulation (extend to accent, emotion as secondary axes)

**Baseline models:**
- MDAS (Multi-task DAS from RAVEL, Huang et al. ACL 2024) — ceiling: simultaneously optimizes all attribute subspaces to be orthogonal
- Linear probes per attribute — floor
- MFA-region patching (Shafran et al. arXiv:2602.02464) — unsupervised comparison baseline

**1-paragraph framing:**
> RAVEL (Huang et al., ACL 2024) introduced the most rigorous existing SAE quality test for text LMs: the Cause/Isolate two-score framework, in which Cause(F, A) tests whether patching feature F produces the expected change in attribute A, and Isolate(F, A) tests whether the same patch leaves *other* attributes unchanged. No audio analogue of RAVEL exists. We extend RAVEL to audio SAEs using phonological minimal-pair stimuli (Choi et al. 2602.18899 — 96 languages × voicing/manner/place contrasts), yielding the first isolation benchmark for any audio representation. We hypothesize that audio SAEs will exhibit more cross-attribute leakage than text SAEs, because acoustic attributes co-occur at the physical signal level in training corpora (e.g., voiced phonemes co-occur with certain speaker gender distributions in standard corpora). The RAVEL-audio score — harmonic mean of Cause and Isolate — is AudioSAEBench's most differentiating metric and the first to formally test whether audio SAE features are *causally disentangled* or merely *consistently correlated* with the attributes they claim to encode (Gap #22).

**Connection to Paper A gc(k):** Audio-RAVEL's patching methodology reuses Paper A's linear DAS infrastructure. A feature with high Cause but low Isolate at the Listen Layer L* (Paper A) would mean: the layer that processes audio does so in an entangled way — phonological attributes are not separated at the representational level, even where the model "listens."

---

## §3.2b: M9 — Causal Abstraction Consistency (CAC) — Audio-RAVEL Extension ⭐

> Added: cycle c-20260312-0231 (Q072). Extends §3.2 Audio-RAVEL with input-direction leakage.

**Motivation**: Audio-RAVEL's RAVEL-audio tests output-direction isolation only. Acoustic co-occurrence
(voiced phonemes ↔ male speaker distributions in training corpora) means a feature can pass
RAVEL and IIA yet still be triggered spuriously by a correlated non-cause.

**M9: Causal Abstraction Consistency**

```
CAC(F, A, B) = IIA(F, A) × RAVEL_audio(F, A) × Isolate_in(F, A, B)

  IIA(F, A)          = interchange intervention accuracy (Geiger et al. 2301.04709)
                       — does F's activation pattern match the causal structure of A?
  RAVEL_audio(F, A)  = harmonic_mean(Cause(F,A), Isolate_out(F,A))   [from §3.2]
  Isolate_in(F,A,B)  = 1 − max(0, R − 1)
                       where R = E[F | B=1, A=0] / E[F | B=0, A=0]
                       — does spurious concept B trigger F when A is absent?
```

**Interpretation:**
- CAC = 1.0 → perfect causal abstraction: fires on A only, matches A's causal hierarchy, patches don't spill
- CAC = 0.0 → at least one component fails (epiphenomenal, leaky, or spuriously triggered)
- CAC > 0.6 → predicted threshold for "genuine causal feature" (extrapolated from RAVEL text baseline)

**Mock example result** (F_42: voiced phoneme feature with male-speaker leakage):
```
Cause=0.82 | Isolate_out=0.78 | IIA=0.84  ← PASS under existing metrics
Isolate_in=0.00 (R ≈ 3.75: male speaker strongly activates F when no voiced phoneme present)
CAC(F_42) = 0.84 × 0.799 × 0.00 = 0.000  ← FAIL — spurious input activation caught
```
→ F_43 (no input leakage): CAC = 0.84 × 0.799 × 1.0 = 0.671 ✅

**Key prediction**: AudioSAE's "50% stable" features will show CAC < 0.4 (acoustic co-occurrence
bias → input leakage), confirming Gap #22 ("consistently correlated ≠ causally disentangled").
CAC is the first metric to test this failure mode formally.

**Stimuli**: 4-condition design (A × B): C1(A=1,B=1), C2(A=1,B=0), C3(A=0,B=1), C4(A=0,B=0).
A = target concept (voicing, jailbreak), B = spurious correlate (speaker gender, angry prosody).
**Connection to Paper A**: IIA reuses NNsight interchange infrastructure from gc(k) harness.
**Code target**: `directed_isolate_mock.py` (Q068/Q073 build task, Tier 0, ~120 LOC).

---

## §3.3 Category 1: Acoustic Concept Detection

**Research question:** Does SAE feature F activate for a specific acoustic concept (phoneme, emotion, pitch, accent, noise)?

**Metrics:**
- Feature-concept F1 (max-activation features per concept class) — time-resolved per timestep (not pooled)
- `TCS(F)` = Temporal Coherence Score = within-phoneme feature variance / across-phoneme-boundary variance
  - Requires MFA alignment (Shafran et al. arXiv:2602.02464 or Montreal Forced Aligner)
  - Evaluates whether features have learned phoneme-level temporal structure (Audio T-SAE hypothesis, Idea #7)

**Stimulus sources:**
- LibriSpeech (ASR / phoneme labels via MFA)
- IEMOCAP (emotion)
- ESC-50 (sound events)
- VocalSet (singing technique, pitch range)

**Baseline models:**
- AR&D concept naming (Chowdhury et al. arXiv:2602.22253)
- AudioSAE phoneme accuracy (Aparin et al. EACL 2026: 0.92 at Whisper layer 12)

**1-paragraph framing:**
> Category 1 tests observational concept alignment — Pearl Level 1 evidence. For each SAE feature, we compute time-resolved feature-concept F1 across 4 stimulus types (phoneme, emotion, sound event, vocal technique). Unlike prior work that pools activations over the full utterance, we compute F1 per 30ms frame, enabling detection of temporally localized features that prior pooled evaluations would miss. Category 1b adds the Temporal Coherence Score TCS(F): the ratio of within-phoneme activation variance to across-phoneme-boundary variance. A standard TopK SAE is expected to score TCS ≈ 1.0 (no temporal structure exploitation); an Audio T-SAE (Bhalla et al. arXiv:2511.05541) trained with multi-scale contrastive loss is predicted to score TCS ≥ 3.0 for phoneme-level features. TCS is the first audio-native SAE metric with no text equivalent.

---

## §3.3b: M10 — Schelling SAE Features (Cross-Seed Stability) — Category 1 Extension ⭐

> Added: cycle c-20260312-0401 (Q076). Extends §3.3 Acoustic Concept Detection with cross-seed convergence measure.

**Motivation**: AudioSAE (Aparin et al., EACL 2026) trains SAEs across multiple random seeds and finds that
only ~50% of features are "consistent" — they appear across seeds with similar concept alignment. But this
consistency score is defined heuristically (cosine similarity > θ between activation patterns) without a
principled theoretical grounding. The question left unanswered: *why* do only 50% of features converge?
Are the stable features genuinely capturing the model's representational structure, or are they merely
capturing the most salient correlations in training data?

**Schelling focal-point framing**: Schelling (1960) observed that rational agents can coordinate on a
"focal point" — a solution that stands out as natural even without communication. We apply this to SAE
features: a **Schelling feature** is a feature that independently emerges across SAE training runs (seeds,
hyperparameter variations, training data orderings) because it corresponds to a natural partition of the
representation space — a "focal" decomposition that any decomposition algorithm would rediscover. Schelling
features are not artifacts of initialization; they reflect genuine structure in the underlying computation.

**M10: Schelling Stability Score**

```
SchwellScore(F, S) = (1 / |S|-1) × Σ_{s' ≠ s} max_{F' ∈ SAE_s'} cos_sim(act_F, act_{F'})

where:
  F          = candidate feature from SAE trained with seed s
  S          = set of training seeds {s₁, s₂, ..., sₖ}
  SAE_s'     = the SAE trained with seed s' (same architecture, different initialization)
  act_F      = activation vector of F across the evaluation corpus (frame-level, N frames)
  cos_sim    = cosine similarity of activation vectors across the same corpus

SchellScore(F, S) ∈ [0, 1]:
  ≥ 0.85 → Schelling feature (converges across seeds)
  0.50–0.84 → semi-stable feature (partial convergence)
  < 0.50 → unstable feature (seed-specific, possibly noise or superposition artifact)

Population metrics:
  SchellFraction(SAE) = |{F : SchellScore(F,S) ≥ 0.85}| / |F_total|
  SchellMeanScore(SAE) = mean SchellScore over all features
```

**M10b: Causal Validation of Schelling Stability**

The critical claim is: *Schelling features are not merely consistently observed — they are causally
significant*. To validate, we cross-reference M10 with Audio-RAVEL (M_Cat0):

```
SchellCAC_correlation = Pearson r(SchellScore(F), CAC(F, A))

where CAC is the Causal Abstraction Consistency score (M9) for the same feature F and its
primary concept A (assigned by Category 1 concept F1 maximizer).

Prediction: r ≥ +0.5  →  Schelling features are causally grounded (converge because they're real)
             r ≈ 0     →  Stability is independent of causal quality (possible in noisy corpora)
             r < 0     →  Stable features are epiphenomenal (convergence via spurious correlation)
```

**Mock example result** (Whisper-small, k=3 seeds, N=1000 evaluation frames):

| Feature | Primary Concept | SchellScore | RAVEL-audio | CAC   | Schelling? |
|---------|----------------|-------------|-------------|-------|------------|
| F_88    | voicing        | 0.91        | 0.73        | 0.61  | ✅ Schelling |
| F_42    | voiced + male  | 0.87        | 0.44        | 0.000 | ✅ Schelling but causally broken (I/O leakage) |
| F_201   | pitch contour  | 0.79        | 0.51        | 0.39  | semi-stable |
| F_337   | noise burst    | 0.31        | 0.22        | 0.08  | ❌ unstable |

→ Overall SchellFraction = 0.50 (consistent with AudioSAE's empirical finding)
→ SchellCAC_correlation = 0.48 (approaching +0.5 threshold — partial validation)
→ F_42: high Schelling + low CAC = "spurious Schelling feature" — stable because acoustic
  co-occurrence is stable in the training corpus, NOT because the feature captures a
  causally independent phonological attribute. This is the critical finding M10 adds.

**Key prediction**: AudioSAE's 50% stable features will split into two subgroups:
  ~35% genuine Schelling features (high SchellScore + high CAC) — encode real phonological units
  ~15% spurious Schelling features (high SchellScore + low CAC) — encode correlated acoustic surface forms

This prediction is falsifiable with existing AudioSAE cross-seed checkpoints (Aparin et al. released code).

**Why this matters for AudioSAEBench**: M10 closes the loop between AudioSAE's empirical finding and
Audio-RAVEL's causal test. An SAE can score well on M10 (stable features) while failing Category 0
(leaky features). The combination M10 + Cat0 distinguishes:
  - **Genuine** Schelling features: stable + causally isolated (the gold standard)
  - **Spurious** Schelling features: stable + leaky (consistent because correlates are consistent)
  - **Genuine unstable** features: unstable + causally isolated (real but not robust)
  - **Noise** features: unstable + leaky (seed-specific superposition artifacts)

**Implementation**: `compute_schelling_score.py` (Tier 0, ~60 LOC):
  1. Load activation vectors for each feature across the evaluation corpus
  2. For each feature, compute max cosine similarity to all features in alternate-seed SAEs
  3. Average across seeds → SchellScore
  4. Compute SchellFraction, SchellMeanScore, SchellCAC_correlation
  - No GPU required; Whisper-small activations on 1000 frames ≈ 2 min on MacBook Air M2

**1-paragraph framing for Paper B §3.3b:**
> AudioSAE (Aparin et al., EACL 2026) reports that approximately 50% of SAE features trained on Whisper representations are "consistent" across training seeds — they re-emerge independently when the same architecture is trained from a different initialization. We formalize this observation as the Schelling Stability Score (M10): for each feature F, the average maximum cosine similarity between F's activation vector and any feature in an alternate-seed SAE, evaluated over a shared corpus of N frames. A feature with M10 ≥ 0.85 is a *Schelling feature* — a natural focal point in representation space that SAE training independently rediscovers, analogous to Schelling's (1960) focal-point solutions in coordination games. The critical question M10 raises — which AudioSAE does not answer — is whether stable features are causally significant or merely stably spurious. We cross-reference M10 with Category 0 (Audio-RAVEL CAC score) via Pearson correlation. Our prediction: stable Schelling features will split into a genuine group (high M10 + high CAC, ~35% of total features) and a spurious group (high M10 + low CAC, ~15%) — the latter stable precisely because acoustic co-occurrence patterns in training data are themselves stable, not because the features encode causally independent attributes. M10 is the first formalization of SAE feature convergence as a testable causal claim rather than an empirical observation.

**Connection to §3.2b M9 (CAC)**: M9 tests per-feature causal isolation (within a single training run).
M10 tests cross-seed convergence (across training runs). Together M9 + M10 answer:
  - M9: "Does this feature causally isolate its claimed attribute?" (within-run quality)
  - M10: "Does this feature consistently emerge, and is its stability causally grounded?" (cross-run quality)

---

## §3.4 Category 2: Disentanglement & Completeness

**Research question:** Are SAE features more independently encoding acoustic concepts than raw hidden states?

**Metric:** Mariotte completeness metric (Mariotte et al. ICASSP 2026, arXiv:2509.24793) — linear probe independence across concept dimensions. Evaluated at matched layer depth (L/L_max ∈ {0.25, 0.5, 0.75, 1.0}) for cross-model comparability.

**Attributes tested:** Pitch, shimmer, HNR, spectral rolloff, gender, accent, voicing (7 attributes)

**Stimulus sources:** VocalSet + IEMOCAP + LibriSpeech

**Baseline models:** Mariotte et al. (4 models: AST, HuBERT, WavLM, MERT). AudioSAEBench extends to 5+ models with matched depth normalization.

**1-paragraph framing:**
> Category 2 evaluates disentanglement completeness — whether SAE decomposition into features improves the independence of encoded acoustic attributes compared to raw hidden states. We adopt Mariotte et al.'s completeness metric and extend their 4-model analysis to 5+ models with layer-depth normalization (L/L_max), enabling fair cross-architecture comparison across models of different depths. Cross-attribute leakage revealed in Category 0 (Audio-RAVEL) at the feature level manifests at the population level in Category 2: a model with high leakage in Cat 0 should score lower on completeness in Cat 2, providing internal validation across the two categories.

---

## §3.5 Category 3: Reconstruction Fidelity

**Research question:** Does routing activations through the SAE bottleneck preserve downstream task performance?

**Metric:** `task_preservation_ratio` = task_score_with_SAE / task_score_without_SAE
- ASR: WER_with_SAE / WER_base (lower delta = better)
- Emotion: emotion-F1_with_SAE / emotion-F1_base
- Sound events: SED-F1_with_SAE / SED-F1_base

**Stimulus sources:** LibriSpeech-test-clean + IEMOCAP-test

**Baseline models:** AudioSAE (WER penalty +0.4% for Whisper large-v3 top-100 feature steering)

**1-paragraph framing:**
> Category 3 provides a sanity check and practical utility score: an SAE that captures interesting features but collapses task performance is not useful for controlled experiments. We extend AudioSAE's single-task WER metric to a multi-task preservation ratio across ASR, emotion recognition, and sound event detection. The expected finding is near-1.0 preservation ratios for high-quality SAEs (task_preservation_ratio ≥ 0.98), with quality degrading for SAEs trained with insufficient expansion factor or aggressive sparsity.

---

## §3.6 Category 4: Causal Controllability

**Research question:** Can SAE features be used to causally steer model behavior? Do they exhibit AND/OR gate structure?

**Metrics** (three-metric protocol from Heimersheim & Nanda 2024):
- `ablation_d` = Cohen's d between ablated vs control accuracy (necessity — AND-gate)
- `steering_precision` = fraction of behavior change attributable to target feature (specificity — OR-gate)
- `hydra_compensation` = behavior change ratio with top-K ablation vs top-1 ablation (Hydra backup pathway detection; expected ~0.7× for text LMs per Heimersheim & Nanda; predicted lower for audio due to higher redundancy)

**Stimuli:**
- AudioSAE hallucination stimuli (Aparin et al. EACL 2026)
- SPIRIT adversarial examples (Djanibekov et al. EMNLP 2025, arXiv:2505.13541)
- ESC-50 deactivation stimuli (sound concept ablation)
- Audio denoising preferred over noising for patching stimuli (OR-gate dominance in audio; noising creates OOD activations per Heimersheim & Nanda 2024)

**Baseline models:**
- AudioSAE (70% FPR reduction via top-100 feature suppression)
- SPIRIT (MLP-layer activation patching, 99% defense robustness)
- MFA-region patching (Shafran et al.) — unsupervised baseline

**1-paragraph framing:**
> Category 4 tests interventional evidence (Pearl Level 2): whether patching SAE features produces measurable behavioral change. Following Heimersheim & Nanda's (2024) patching best practices, we decompose controllability into three components. First, the AND-gate test (ablation_d): is feature F *necessary* for the behavior — does ablating it degrade performance? Second, the OR-gate test (steering_precision): is feature F *sufficient* — does activating it produce the target behavior? Third, the Hydra effect quantification: how much do backup pathways compensate when feature F is ablated? Audio models are predicted to exhibit stronger Hydra compensation than text models (ratio < 0.7×) because AudioSAE requires ~2000 features to erase accent versus tens of features in text LMs — a ~100× redundancy ratio that predicts stronger backup pathway compensation. AudioSAEBench is the first benchmark to report Hydra compensation as a standardized metric for audio SAEs.

---

## §3.7 Category 5: Grounding Sensitivity ⭐ PAPER A TIE-IN

**Research question:** Does SAE feature F respond to audio content or text linguistic context?

**Metric:**
```
gc(F) = IIA at feature granularity (Geiger et al. arXiv:2301.04709)
       ≈ fraction of feature activation variance attributable to audio content
         vs linguistic context, estimated via activation patching on conflict stimuli

gc(F) = 1.0  → pure audio grounding (feature fires to audio signal, not text)
gc(F) = 0.0  → pure text prediction (feature fires to transcription context)
gc(F) = 0.5  → ambiguous / mixed modality
```

**Stimuli:** ALME 57K audio-text conflict pairs (Li et al. arXiv:2602.11488 — off-the-shelf)

**Baseline models:** None — first audio-native grounding metric. No text SAE benchmark equivalent.

**Encoder-only proxy (Whisper):** Use decoder text generation as the "text pathway" proxy for gc(F) computation. Noisier than LALM measurement but still informative.

**M7: ΔGS — Grounding Sensitivity Contrast Score (secondary, patching-free)**

While gc(F) (M5) requires activation patching on conflict stimuli, ΔGS(F) provides a
patching-free proxy for grounding robustness using the same ALME stimulus pairs:

```
ΔGS(F) = (µ_c − µ_x) / σ_pool    [Cohen's d of activation contrast]

where:
  µ_c = mean activation of F on CONSISTENT stimuli (audio matches transcript context)
  µ_x = mean activation of F on CONFLICT stimuli (audio contradicts transcript context)
  σ_pool = sqrt((σ_c² + σ_x²) / 2)    [pooled std, Cohen's d denominator]

Interpretation:
  ΔGS(F) ≈ 0   → feature insensitive to audio-text conflict → AUDIO-GROUNDED
  ΔGS(F) > 0.5 → feature more active on consistent stimuli → TEXT-GROUNDED
  ΔGS(F) < -0.3 → feature more active on conflict stimuli → ANOMALOUS (error-detection?)
```

**Population-level summary metrics:**
- `GS_audio` = fraction of features with |ΔGS| < 0.1 (audio-grounded cluster)
- `GS_text`  = fraction of features with ΔGS > 0.5 (text-grounded cluster)
- `GS_anom`  = fraction of features with ΔGS < -0.3 (conflict-preferring)

**Predictions:**
- Whisper encoder (all layers): GS_audio ≥ 0.70
- Qwen2-Audio LLM backbone: GS_audio ≤ 0.30 (text pathway dominates)
- GS_audio drops sharply at Listen Layer L* (Paper A cross-validation)

**CPU-feasibility:** ΔGS requires only 2 forward passes per stimulus pair (no patching).
200 ALME pairs, Whisper-small: ~2 min on MacBook Air M2. Tier 1 (auto-allowed).

**Cross-metric validation:** Pearson r(gc(F), |ΔGS(F)|) < −0.4 predicted at encoder layers.
If r > 0, both metrics are confounded (investigate feature sparsity / activation magnitude).

**Implementation path:** Extend `skills/autodidact/scripts/gc_eval.py` with
`compute_delta_gs_feature()` and `compute_gs_profile()` — Tier 0 code addition.

**1-paragraph framing:**
> Category 5 tests counterfactual isolation (Pearl Level 3): not just whether a feature responds to an acoustic attribute, but whether it responds to the *audio signal itself* versus the model's *linguistic predictions about audio*. We operationalize this as Grounding Sensitivity gc(F) — the IIT accuracy at feature granularity (Geiger et al. 2301.04709) estimated via activation patching on 57K audio-text conflict stimuli (ALME, Li et al. 2025). A feature with gc(F) = 1.0 fires on audio content regardless of text context; gc(F) = 0.0 fires on text-predictable patterns regardless of audio content. We predict a bimodal distribution for Qwen2-Audio-7B: a cluster at gc(F) > 0.8 (encoder/connector features) and a cluster at gc(F) < 0.2 (LLM backbone features), with the modality boundary aligning with the Listen Layer L* identified in Paper A — providing cross-paper validation. For Whisper-small (encoder-only), features are expected to cluster near gc(F) ≈ 1.0. gc(F) is directly analogous to Paper A's gc(L) at coarser resolution: gc(L) identifies *which layer* grounds to audio; gc(F) identifies *which features* ground to audio within each layer.

**Paper A connection (explicit):**
```
Paper A:  gc(L) = layer-level grounding coefficient
          → Answers: WHERE does the model listen? (Listen Layer L*)
          → Method: patching whole layer activations on ALME stimuli

Paper B:  gc(F) = feature-level grounding sensitivity
          → Answers: WHICH features listen vs guess?
          → Method: patching individual SAE feature activations on same stimuli

Relationship:
  gc(L) = average gc(F) over all features at layer L (if gc(F) were defined)
  Paper A validates the metric at coarse resolution → Paper B scales to feature resolution
  L* from Paper A = predicted peak of gc(F) bimodal split
  Same infrastructure: NNsight patching + ALME stimuli
```

---

## §3.8 Training & Baseline SAEs (SAELens-Audio Toolkit)

**Gap addressed:** Gap #19 — SAELens v6 has ZERO audio/speech pre-trained SAEs (all 25 HuggingFace models are text LMs only). All 5 audio SAE papers use custom one-off training code.

**Contribution:** SAELens-compatible audio SAE training toolkit
- NNsight frame-level activation hooks for Whisper/HuBERT/WavLM
- Phoneme-boundary-aware batching (MFA alignment integration)
- SAELens model card schema (for HuggingFace upload with `saelens-audio` tag)
- Supports: TopK, BatchTopK, Matryoshka SAE variants

**Release:** Alongside paper — `pip install saelens-audio` target

**1-paragraph framing:**
> No standardized audio SAE training pipeline exists. SAELens v6 (de-facto SAE training library; Anthropic, `decoderesearch/SAELens`) includes 25 HuggingFace pre-trained SAEs — all for text LMs (Gemma-scope, GPT-2, LLaMA). We release a SAELens-compatible audio training toolkit with NNsight frame-level hooks, phoneme-boundary-aware batching, and HuggingFace model card integration. This makes AudioSAEBench not just an evaluation framework but also a community training resource: future audio SAE papers can use the same toolkit to produce results that are directly comparable. All 12+ SAEs evaluated in this paper are trained with this toolkit and released with the `saelens-audio` tag.

---

## §3.9 Experimental Setup

**Compute:**
- Categories 0–4: MacBook (Whisper-small/base) — all experiments runnable in <12h total
- Category 5: NDIF or GPU workstation (Qwen2-Audio-7B requires ~24h for full 57K ALME suite)
- Full 12+ SAE suite: GPU workstation (~3 days)

**Implementation:**
- `pyvene` + `NNsight` for activation patching (consistent with Paper A)
- MFA alignment: Montreal Forced Aligner or Shafran et al. unsupervised variant
- Code released alongside paper

**SAEs evaluated:**

| Model | SAE Variants | Layer Range |
|-------|-------------|-------------|
| Whisper-base | TopK, BatchTopK | Layers 3, 6, 9, 12 |
| Whisper-small | TopK, BatchTopK, Matryoshka | Layers 3, 6, 9, 12 |
| Whisper-large-v3 | TopK | Layer 12 only (resource) |
| HuBERT-base | TopK, BatchTopK | Layers 3, 6, 9, 12 |
| WavLM-large | TopK | Layer 12 only (resource) |
| Qwen2-Audio-7B | TopK (encoder) | Layers 4, 16, 28 (LLM backbone) |

---

## Category Summary Table (for §3 or §1.2)

| Cat | Name | Pearl Level | Novel? | Key Metric | Stimulus Source | Baseline |
|-----|------|-------------|--------|------------|-----------------|---------|
| 0 | Audio-RAVEL | L3 Counterfactual | ✅ Novel | Cause(F,A), Isolate_out(F,A), RAVEL-audio | Choi et al. 2602.18899 | MDAS (Huang et al. ACL 2024) |
| 0b | M9: CAC | L3 Counterfactual | ✅ Novel | CAC = IIA × RAVEL_audio × Isolate_in | 4-condition (A×B controlled) | None (first input-direction metric) |
| 1 | Acoustic Concept | L1 Observational | Partial (TCS novel) | Feature-concept F1, TCS(F) | LibriSpeech, IEMOCAP, ESC-50 | AR&D, AudioSAE |
| 2 | Disentanglement | L1 Observational | Partial (cross-model) | Mariotte completeness | VocalSet, IEMOCAP | Mariotte et al. |
| 3 | Reconstruction | L1 Observational | No | task_preservation_ratio | LibriSpeech, IEMOCAP | AudioSAE |
| 4 | Controllability | L2 Interventional | Partial (Hydra novel) | ablation_d, steering_precision, hydra_compensation | AudioSAE stimuli, SPIRIT | AudioSAE, SPIRIT |
| 5 | Grounding Sensitivity | L3 Counterfactual | ✅ Novel | gc(F) [M5], ΔGS(F) [M7] | ALME 57K (Li et al. 2602.11488) | None (first) |

---

## Connection to Paper A gc(k): Explicit Cross-Paper Validation Chain

```
Paper A establishes:
  gc(L) at layer granularity → finds Listen Layer L*
  Prediction: gc(F) distribution splits at L* (bimodal: audio cluster vs text cluster)
  Infrastructure: NNsight patching on ALME stimuli (reusable)

Paper B uses:
  gc(F) at feature granularity → which features listen vs guess within each layer
  Validation: gc(F) bimodal split should occur at L* (cross-paper convergent evidence)
  Infrastructure: same NNsight code, same ALME stimuli, different intervention unit

AudioSAEBench §3.7 explicitly cites Paper A:
  "Layer-level analysis in [Paper A] identifies L* as the transition point where
  audio information enters the LLM backbone. AudioSAEBench Category 5 (Grounding
  Sensitivity) tests the feature-level correlate of this finding: within each layer,
  which SAE features carry audio-grounded information (gc(F) ≈ 1.0) versus
  text-prediction information (gc(F) ≈ 0.0)? The distribution split at L* provides
  the first feature-resolution account of the Listen Layer phenomenon."

This cross-paper citation is the strongest evidence that both papers are part of a
coherent research program rather than two isolated contributions.
```

---

## Writing Order Recommendation

Priority for LaTeX draft (based on content readiness):
1. **§3.2 (Audio-RAVEL)** — most novel, clearest methodology, ready to write
2. **§3.7 (Grounding Sensitivity)** — Paper A tie-in, well-specified
3. **§3.1 (Framework Overview)** — needs Pearl table as anchor figure
4. **§3.6 (Causal Controllability)** — Hydra metric is concrete
5. **§3.8 (SAELens toolkit)** — straightforward gap fill
6. **§3.3–§3.5** — lower novelty, can borrow from Mariotte/AudioSAE prose style
7. **§3.9 (Setup)** — write last, numbers may change

---

*End of §3 outline. Full §3 prose draft (~1100 words) embedded in paper-b-pitch.md §3 section (v1.3, cycle #225). This outline is the structured navigation doc for LaTeX transfer.*
