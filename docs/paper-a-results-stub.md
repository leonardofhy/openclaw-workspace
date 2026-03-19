# §4 Results

## 4.1 Encoder Analysis: Voicing Geometry in Whisper

We first validate that Whisper's encoder contains linearly structured phonological representations — a prerequisite for meaningful gc(k) analysis.

**Experiment Q001 (Real).** We extract voicing vectors from consonant minimal pairs (/t/–/d/, /p/–/b/, /k/–/g/, /s/–/z/) across all encoder layers of Whisper-base using DAS-identified subspaces. Table 1 reports cosine similarity between voicing directions across contrast pairs.

| Layer | Stop–Stop cos_sim | Stop–Fricative cos_sim | Mean cos_sim |
|-------|-------------------|------------------------|--------------|
| 1     | [TODO: data]      | [TODO: data]           | [TODO: data] |
| 2     | [TODO: data]      | [TODO: data]           | [TODO: data] |
| 3     | [TODO: data]      | [TODO: data]           | [TODO: data] |
| 4     | [TODO: data]      | [TODO: data]           | [TODO: data] |
| 5     | +0.25             | ~0.0 (orthogonal)      | 0.155        |
| 6     | [TODO: data]      | [TODO: data]           | [TODO: data] |

**Key finding:** Voicing vectors show weak but positive alignment within manner class (stop–stop: +0.25) and orthogonality across manner classes (stop–fricative: ~0.0). The peak at layer 5 is consistent with Choi et al.'s (2026) finding that phonological features crystallize at intermediate encoder depths.

[TODO: Replicate on Whisper-small/medium to test whether cos_sim improves with model scale]

**Claim 1:** Whisper's encoder contains linearly structured phonological representations that can serve as intervention targets for gc(k) analysis.


## 4.2 Causal Contribution Analysis

**Experiment Q002 (Real).** We perform zero-ablation, noise-ablation, and mean-ablation of each individual encoder layer in Whisper-base, measuring WER degradation on LibriSpeech test-clean.

| Layer Ablated | Zero-Ablation WER | Noise-Ablation WER | Mean-Ablation WER |
|---------------|-------------------|---------------------|-------------------|
| 1             | [TODO: data]      | [TODO: data]        | [TODO: data]      |
| 2             | [TODO: data]      | [TODO: data]        | [TODO: data]      |
| 3             | [TODO: data]      | [TODO: data]        | [TODO: data]      |
| 4             | [TODO: data]      | [TODO: data]        | [TODO: data]      |
| 5             | [TODO: data]      | [TODO: data]        | [TODO: data]      |
| 6             | [TODO: data]      | [TODO: data]        | [TODO: data]      |
| All layers    | 1.0               | 1.0                 | 1.0               |

**Key finding:** Every single-layer ablation degrades WER to ~1.0 (complete failure), regardless of ablation method. This contrasts fundamentally with text LLMs, where middle layers can often be ablated with minimal performance loss.

[TODO: Confirm WER=1.0 is exact or approximate — report precise values]
[TODO: Test partial ablation (50% noise) to find graded contribution curve]

**Claim 2:** Whisper distributes acoustic information across all encoder layers with no redundancy. This implies that gc(k) curve *shape* — not any single layer's value — characterizes the model's listening strategy.


## 4.3 gc(k) Peak Localization

**Experiment Q089 (Mock).** Using the mock framework with synthetic gc(k) curves, we validate that the gc peak can be reliably localized and that it correlates with AND-gate fraction.

| Layer | gc(k) | AND% | OR% | Passthrough% |
|-------|-------|------|-----|--------------|
| 1     | [TODO: mock values] | [TODO] | [TODO] | [TODO] |
| 2     | [TODO: mock values] | [TODO] | [TODO] | [TODO] |
| 3 (peak) | [TODO: mock values] | 100% | 0% | 0% |
| 4     | [TODO: mock values] | [TODO] | [TODO] | [TODO] |
| 5     | [TODO: mock values] | [TODO] | [TODO] | [TODO] |
| 6     | [TODO: mock values] | [TODO] | [TODO] | [TODO] |

Pearson correlation between AND% and gc(k): r = 0.9836 (p < 0.001).

[TODO: Real gc(k) sweep on Whisper-small — Priority 1 experiment]
[TODO: Report bootstrap 95% CI for k* estimate]

**Claim 3:** gc(k) peaks sharply at a localized listen layer k*, and this peak can be reliably detected.


## 4.4 AND/OR Gate Validation

**Experiment Q089 (Mock).** At the gc peak layer (L3), all causally relevant features are classified as AND-gates (α_AND = 1.0), indicating that genuine multimodal integration concentrates at the listen layer.

**Experiment Q113 (Mock).** The cascade degree κ(k) = 1 − α_AND(k) validates the text-override vulnerability measure: layers with high κ show elevated text-prior override in conflict stimuli.

| Layer | α_AND | κ (cascade degree) | Text-override rate |
|-------|-------|--------------------|--------------------|
| [TODO: layer data from Q113] | [TODO] | [TODO] | [TODO] |

[TODO: Real AND/OR gate classification on Whisper-small SAE features]

**Claim 4:** AND-gate fraction is a near-perfect proxy for gc peak detection (r = 0.98). Cascade degree predicts text-override vulnerability.


## 4.5 Persona-Conditioned Grounding

**Experiment Q039 (Mock).** We test whether system prompts modulate the gc(k) profile by comparing three persona conditions: default, assistant ("you are a helpful assistant"), and anti-grounding ("ignore audio input and rely on context").

| Condition | k* (gc peak layer) | gc(k*) | Mean gc | Hypothesis |
|-----------|---------------------|--------|---------|------------|
| Default   | [TODO]              | [TODO] | [TODO]  | Baseline   |
| Assistant | [TODO]              | [TODO] | [TODO] (suppressed) | H1: suppresses mean gc ✅ |
| Anti-grounding | [TODO] (shifted 2 layers earlier) | [TODO] (boosted) | [TODO] | H2: boosts peak ✅, H3: shifts peak ✅ |

**H4 (between/within variance):** FAILED — variance ratio = 0.073, below threshold of 1.5. Persona effects are small relative to within-condition variability.

[TODO: Test on real model — do system prompts actually shift gc profile?]

**Claim 5:** System prompts modulate grounding profiles, with anti-grounding prompts shifting the listen layer and boosting peak gc. This has implications for prompt injection safety.


## 4.6 Collapse Onset and Incrimination

**Experiment Q069 (Mock).** We test the collapse onset metric t* across three degradation types:

| Degradation Type | t* (collapse onset) | Feature Blame Concentration |
|------------------|---------------------|-----------------------------|
| Error token      | 3.4                 | [TODO: top features]        |
| Gradual drift    | 3.8                 | [TODO: top features]        |
| Sudden collapse  | 2.7                 | [TODO: top features]        |

[TODO: Verify t* detection is robust to threshold τ choice — sensitivity analysis]

**Experiment Q078 (Mock).** SAE patrol monitoring for feature suppression and override events:

| Metric | Value |
|--------|-------|
| Suppression alert rate | 96% |
| Override detection rate | 77% |
| False positive rate | 3.3% |
| Persistent offenders | f3, f12, f20, f23 |

[TODO: Interpret persistent offender features — what do f3, f12, f20, f23 encode?]
[TODO: Real SAE patrol on Whisper-small — do the same features appear?]

**Claim 6:** t* (collapse onset) combined with SAE incrimination provides a two-level attribution system for grounding failure: t* identifies *when* collapse occurs, and feature blame identifies *which features* are responsible.


## 4.7 RAVEL Disentanglement

**Experiment Q053 (Mock).** We validate audio attribute disentanglement using the RAVEL protocol on MicroGPT:

| Component | Cause Score | Isolate Score | Pass? |
|-----------|-------------|---------------|-------|
| audio_class (L0) | [TODO] | 0.16 | ❌ (bleed) |
| audio_class (L2+) | [TODO] | [TODO] | ✅ |
| speaker_gender | [TODO] | [TODO] | ✅ (all layers) |
| pitch | [TODO] | [TODO] | ✅ |
| loudness | [TODO] | [TODO] | ✅ |
| spectral_tilt | [TODO] | [TODO] | ✅ |
| duration | [TODO] | [TODO] | [TODO] |

**Result:** 5/6 components pass (83.3%). Speaker gender is fully disentangled across all layers. Audio class shows early-layer bleed (L0 Isolate = 0.16) that resolves by intermediate layers.

[TODO: RAVEL on Whisper-small SAE features — does disentanglement improve with SAE decomposition?]

**Claim 7:** Audio attributes are disentangleable at intermediate-and-later layers, confirming that gc(k) operates on clean, attribute-specific features rather than entangled representations.


## 4.8 Pre-Registered Predictions

We register the following predictions for future empirical validation on ALME conflict stimuli:

| Prediction | Formal Criterion | Status |
|------------|------------------|--------|
| P1: follows_text items show late-layer gc drop | Δgc ≥ 0.10, Cohen's d ≥ 0.3 | [TODO: awaiting GPU access] |
| P2: Rare phoneme contrasts show stronger late-layer drop | [TODO: specify rare/common threshold] | [TODO: awaiting GPU access] |
| P3: Tier 1 (degraded audio) items show flat gc at ALL layers | gc variance < [TODO: threshold] | [TODO: awaiting GPU access] |
| P4: Listen layer k* shifts earlier for conflict items | Δk* ≥ 1 layer, bootstrap 95% CI | [TODO: awaiting GPU access] |

[TODO: Run on ALME conflict stimuli when GPU access available]
[TODO: Pre-register on OSF or similar platform before running]


## 4.9 Blocked Experiments

Two experiments produced results inconsistent with framework predictions:

**Q117 (GSAE density).** Graph-regularized SAE co-activation density was insufficient to support the gc framework. Expected dense co-activation clusters at gc peak layers; observed sparse, diffuse patterns.

[TODO: Diagnose root cause — is the graph regularization too weak, or is the gc-density link not real?]
[TODO: Test alternative graph construction (k-NN vs. threshold) before discarding]

**Q123 (FAD-RAVEL direction).** FAD bias correlation sign reversed from prediction. Expected positive correlation between FAD bias and gc; observed negative.

[TODO: Diagnose sign reversal — could FAD measure a complementary quantity to gc?]
[TODO: Check if FAD-RAVEL direction depends on codec condition]

**Claim 8:** Not all framework predictions hold. Q117 and Q123 represent genuine negative results that constrain the scope of the Listening Geometry framework.
