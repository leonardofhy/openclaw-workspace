# AudioSAEBench: Evaluation Framework for Audio Sparse Autoencoders

> Status: Design Draft v1 | Created: 2026-03-01 | Track: T2 | Task: Q013

## Motivation

SAEBench (Karvonen et al. 2024; EleutherAI) standardizes SAE evaluation for text LLMs. No audio equivalent exists. This document maps all 8 SAEBench core metrics to audio/ASR contexts, enabling rigorous evaluation of SAEs trained on Whisper or audio-LLM activations.

**Use case**: Validate that audio SAEs learn disentangled, monosemantic features aligned with phonological and semantic structure — prerequisite for mechanistic interpretability work (T3 gc(k), T5 Listen-Layer Audit).

---

## Corpus

**Primary**: LibriSpeech test-clean (2620 utterances, ~5.4h)
**Fast eval subset**: 1000 utterances stratified by phoneme distribution (automated via CMU Pronouncing Dictionary alignment)
**Format**: 16kHz WAV + forced-aligned phoneme labels (Montreal Forced Aligner or Whisper timestamps as fallback)

## SAE Targets

Train/evaluate SAEs on Whisper-base encoder:
- Layer 3: early acoustic features (spectral, onset detection)
- Layer 6: mid-level (phoneme consolidation)
- Layer 9: late / pre-output (word-level representations)

Corresponds to gc(k) analysis layers from `gc_eval.py`.

---

## 8 Metrics

### M1 — Reconstruction Fidelity
**SAEBench original**: L2 distance / cosine similarity between original and SAE-reconstructed activations.

**Audio adaptation**: Compute per-time-step (30ms frame) cosine similarity at each target layer. Report:
- Mean cosine similarity (higher = better fidelity)
- Frame-level variance (low variance = stable reconstruction)
- Phoneme-boundary alignment test: fidelity should not degrade at phoneme transitions

**Implementation**: `metrics/m1_reconstruction.py` — hooks on Whisper encoder, compute cosine(h_k, SAE(h_k)) per frame.

---

### M2 — L0 Sparsity
**SAEBench original**: Average number of active features (non-zero activations) per token.

**Audio adaptation**: Average active features per 30ms frame. Additional measure:
- **Phoneme-conditional sparsity**: L0 should be lower for silence/simple phonemes, higher for complex clusters (/str/, /spl/)
- Target: L0 < 50 for typical speech frames (cf. text SAE L0 ≈ 40-80 at 65k features)

**Implementation**: Straightforward count from SAE encoder output.

---

### M3 — Absorption Score
**SAEBench original**: Measures when SAE feature F "absorbs" the meaning of feature G, causing G to under-activate when F is present.

**Audio adaptation**: **gc(k) Absorption Test** — does SAE feature F absorb the acoustic confidence signal gc(k)?
- Procedure: for audio-dominant frames (gc(k) > 0.8), check if any SAE feature activates that shouldn't (i.e., not a known acoustic feature)
- Absorption occurs when a semantic SAE slot reliably co-activates with high gc(k) frames
- Cross-reference with `gc_eval.py` output

**Novelty**: Connects SAE absorption to the audio/text channel distinction — a known interpretability issue in ASR models.

---

### M4 — Monosemanticity / PCDS
**SAEBench original**: RAVEL benchmark — measures if ablating a feature changes target attribute without affecting others.

**Audio adaptation**: **Phoneme-Concept Decoupling Score (PCDS)**

```
PCDS(f) = 1 - MI(act_f; phoneme_labels) / (MI(act_f; phoneme_labels) + MI(act_f; semantic_labels))
```

- PCDS → 1: feature is semantic (good)
- PCDS → 0: feature conflates phoneme identity with semantic content (bad)
- Use MI estimated via KSG estimator (sklearn mutual_info_classif as fast approximation)

**Labels**: phoneme labels from MFA alignment; semantic labels from LibriSpeech transcripts (noun/verb POS as proxy).

---

### M5 — Interventional Selectivity
**SAEBench original**: Ablate a single SAE feature → measure downstream effect size. Good SAE: small effect (selective); bad SAE: large cascading effect.

**Audio adaptation**: Ablate feature F → measure **WER delta** on downstream Whisper transcription.
- Local effect: WER change on frames where F was active
- Global effect: WER change across full utterance
- Selectivity score: WER_local_delta / WER_global_delta (high = selective = good)

**Connection to T3**: Same causal patching infrastructure as gc(k) eval harness (`gc_eval.py`). Reuse forward hook setup.

---

### M6 — Downstream Task Performance
**SAEBench original**: Probe downstream task accuracy using SAE latent features vs original activations.

**Audio adaptation**: Compare Whisper WER:
- Baseline: original Whisper (no SAE)
- SAE reconstruction: replace h_k with SAE(h_k) at layer k, continue forward pass
- Feature probe: train linear probe on SAE latents → predict phoneme label

**Target**: SAE reconstruction WER within 5% relative of baseline (fidelity threshold for deployment).

---

### M7 — Spurious Correlation
**SAEBench original**: Check if features activate for semantically unrelated concepts.

**Audio adaptation**: **Cross-phoneme activation overlap** — does feature F activate for phonemes that are acoustically and articulatorily unrelated?

```python
# For each feature f:
# 1. Get frames where f activates (threshold: top 10%)
# 2. Get phoneme labels for those frames
# 3. Compute χ² test: uniform over phoneme classes vs observed
# 4. Compute acoustic similarity (formant distance) between top-activated phonemes
# spurious_score = χ² statistic / expected (if perfect monosemanticity)
```

**Expected**: Good SAE features should activate for acoustically similar phonemes (/p/, /b/, /m/ = bilabials) not random phoneme subsets.

---

### M8 — Feature Geometry
**SAEBench original**: Analyze cosine similarity structure between features; check for superposition.

**Audio adaptation**: **Phonological Cluster Geometry**
- Group SAE features by their peak-activating phoneme class (stop/fricative/nasal/vowel)
- Compute intra-class mean cosine similarity vs inter-class mean cosine similarity
- **Geometry score** = intra_cosim / inter_cosim (should be > 2.0 for well-structured SAE)

Additionally: check for anti-podal features (cosine ≈ -1.0 = likely encoding a binary acoustic distinction like voiced/unvoiced).

---

## Implementation Plan

### Tier 0 (CPU, synthetic — can run now)
- [ ] `metrics/m1_reconstruction.py` — mock activations, cosine similarity
- [ ] `metrics/m2_sparsity.py` — L0 per frame
- [ ] `metrics/m4_pcds.py` — PCDS with synthetic phoneme/semantic labels
- [ ] `metrics/m7_spurious.py` — χ² test
- [ ] `metrics/m8_geometry.py` — cluster cosine similarity

### Tier 1 (CPU, real Whisper — <5min)
- [ ] `metrics/m3_absorption.py` — gc(k) cross-reference
- [ ] `metrics/m5_selectivity.py` — WER delta via interventional patching
- [ ] `metrics/m6_downstream.py` — probe + reconstruction WER

### Tier 2 (GPU — needs Leo approval)
- [ ] Full LibriSpeech test-clean eval
- [ ] Whisper-large targets

---

## Deliverables

1. This design document ✅
2. `scripts/audio_saebench_runner.py` — orchestrates all metrics (Tier 0 scaffold, next task)
3. Results table: baseline Whisper-base vs SAE at layers 3/6/9

---

## Open Questions for Leo

1. Should we train our own audio SAE, or evaluate an existing one? (No public Whisper SAEs found as of 2026-03-01)
2. Is T2 (AudioSAEBench) a standalone paper or a methods section in Paper A?
3. JALMBench (Q011) may have an audio eval suite — read before building to avoid duplication.
