# AudioSAEBench: Evaluation Framework for Audio Sparse Autoencoders

> Status: Design Draft v3 | Created: 2026-03-01 | Updated: 2026-03-05 (Q045 Gap #30 modality collapse hypothesis) | Track: T2 | Task: Q013

---

## §0: SAEBench Metric Portability Matrix (Q044, cycle #295)

**Source**: Karvonen, Nanda et al. (ICML 2025). 8 categories across single-prompt, multi-prompt, and absorption evaluations.

| # | SAEBench Metric | Text Assumption Being Ported | Audio Analogue (AudioSAEBench) | Port Complexity |
|---|----------------|-------------------------------|-------------------------------|-----------------|
| M1 | **Reconstruction Fidelity** | Token-level activations; reconstruction at embedding dim | Frame-level (30ms) cosine similarity; identical math, different temporal granularity | 🟢 LOW |
| M2 | **L0 Sparsity** | Active features per token | Active features per 30ms frame; add phoneme-conditional sparsity (silence vs. complex clusters) | 🟢 LOW |
| M3 | **Absorption Score** | Semantic features absorb another feature's meaning (text polysemy) | gc(k) Absorption Test: SAE feature co-activates in high-gc(k) frames (audio-dominant) | 🟡 MEDIUM |
| M4 | **Monosemanticity / RAVEL Isolate** | Entity-attribute disentanglement; RAVEL minimal pairs from text corpora | PCDS + Audio-RAVEL: phonological attribute isolation via MFA-aligned minimal pairs (Choi et al. 2602.18899) | 🔴 HIGH |
| M5 | **Interventional Selectivity** | Ablate feature → logprob delta on next-token prediction | Ablate feature → WER delta on Whisper CTC; local vs. global WER selectivity ratio | 🟡 MEDIUM |
| M6 | **Downstream Task Performance** | Probe SAE latents → NLP downstream tasks | (a) Probe → predict phoneme class; (b) SAE reconstruction WER vs. baseline Whisper | 🟢 LOW |
| M7 | **Spurious Correlation** | Feature activates on semantically unrelated tokens | Cross-phoneme activation overlap: χ² test; acoustic/articulatory distance check | 🟡 MEDIUM |
| M8 | **Feature Geometry** | Cosine similarity structure; anti-podal = binary semantic distinctions | Phonological Cluster Geometry: intra-class vs. inter-class cosine; voiced/unvoiced anti-podal features | 🟢 LOW |

**Port complexity breakdown**: 🟢 LOW (M1, M2, M6, M8) — direct port ≤1 day; 🟡 MEDIUM (M3, M5, M7) — concept port 2-3 days; 🔴 HIGH (M4) — novel contribution 1-2 weeks.

### Audio Friction Sources
1. **Temporal structure**: 1 utterance = N frames; must choose frame-wise vs. utterance-level aggregation. Resolution: M1-M3, M6-M8 = frame-wise; M4 = utterance minimal pairs; M5 = both.
2. **Ground truth**: MFA phoneme alignment = millisecond-precision (CLEANER than text entity labels). Audio advantage, not liability.
3. **Behavioral signal**: WER = sequence-level (slower than logprob). Resolution: use Whisper encoder CTC output per frame for M5/M6; full WER only for final evaluation.

### Paper B Framing Implications
- **§1 claim**: "We port 7 of 8 SAEBench metrics to audio with LOW-to-MEDIUM complexity, and introduce M4 (PCDS / Audio-RAVEL) as the first audio-native disentanglement metric."
- **M4 = cornerstone**: only metric requiring novel conceptual work; AudioSAEBench is not "SAEBench but audio" — it introduces the audio disentanglement measurement problem.
- **Flip narrative**: "Audio provides STRONGER theoretical priors for SAE geometry (M8) and CLEANER ground truth (M6) — audio SAE evaluation may be MORE rigorous than text."
- **Implementation order**: M1+M2+M6+M8 first (lowest friction) → M5+M7 (medium) → M4 last (needs MFA + minimal pair corpus).

---

## §1: Modality Collapse as Measurable SAE Isolation Failure (Gap #30, Q045, cycle #296)

**Hypothesis**: Models that exhibit behavioral *modality collapse* (Zhao et al. 2602.23136) will score LOW on AudioSAEBench M4 (Isolate) — because their "audio SAE features" are not truly isolated from the text-prediction pathway.

### Background
- **Modality collapse** (Zhao et al., ALME, 57K audio-text conflict pairs): audio LLMs default to text-prediction pathway even when audio content *contradicts* the text context. Behavioral phenomenon (black-box).
- **Isolate(F, A)** (RAVEL, AudioSAEBench M4): measures whether patching feature F changes attribute A *without* affecting OTHER attributes. Low Isolate = the "audio feature" also encodes text information → not isolated from text pathway.

### The Link
If a model has high modality collapse rate → its encoder produces SAE features that respond to audio *and* carry text-prior information (the feature co-activates with text-prediction frames). This is exactly what Isolate(F, A) detects.

**Predicted relationship**:
```
Isolate(audio SAE feature, audio_attribute) ↓  ←→  Modality Collapse Rate ↑
```

### Experiment Design
1. **Models**: compare audio LLMs with known modality collapse rates (from ALME benchmark, Zhao et al.)
   - High collapse: likely weaker audio-LLM connectors (e.g., smaller adapter models)
   - Low collapse: stronger audio-grounded models (e.g., Qwen2-Audio)
2. **Stimuli**: ALME conflict pairs (audio says A, text context says B) — reuse existing benchmark
3. **SAE**: AudioSAE (Aparin 2026) or custom Whisper-base SAE trained via SAELens-compatible pipeline (Gap #19)
4. **Metric**: M4 Isolate score for audio-specific attributes (voicing, phoneme identity) vs text-predictive attributes (word frequency, collocations)
5. **Expected result**: Isolate(audio feature, audio attribute) negatively correlates with model's modality collapse rate (r < -0.5 predicted)

### Paper B Contribution
- **First mechanistic/quantitative correlate of behavioral modality collapse**
- Connects AudioSAEBench M4 (Isolate metric) to established behavioral finding
- **Position in Paper B §4**: "Our M4 (Isolate) metric validates against the behavioral modality collapse phenomenon, providing a mechanistic account of a previously black-box result."
- **Falsifiable**: if high-collapse models do NOT show lower Isolate scores → modality collapse mechanism is NOT at the feature level (interesting negative result)

### Prior Work Gap
| Method | What it measures | Missing |
|--------|-----------------|---------|
| ALME (Zhao et al.) | Behavioral collapse rate (input-output level) | No feature-level attribution |
| SPIRIT patching | MLP-layer collapse-adjacent interventions | No SAE feature granularity |
| AudioSAE consistency | Cross-seed feature stability | No causal/isolation test |
| **AudioSAEBench M4** | Per-feature Isolate score ← **bridges the gap** | — |

### Venue
Same as AudioSAEBench (Paper B): ACL 2026 or NeurIPS 2026 workshop.

### Status: 🟢 GREEN
- High novelty (no prior work measures collapse at SAE feature level)
- Infrastructure overlap with M4 already designed (RAVEL-style Isolate, ALME stimuli)
- Priority: Paper B §4 after M4 prototype validated

---

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

### M4 — Monosemanticity / PCDS / Isolate
**SAEBench original**: RAVEL benchmark — measures if ablating a feature changes target attribute without affecting others.

**Audio adaptation**: **Phoneme-Concept Decoupling Score (PCDS)**

```
PCDS(f) = 1 - MI(act_f; phoneme_labels) / (MI(act_f; phoneme_labels) + MI(act_f; semantic_labels))
```

- PCDS → 1: feature is semantic (good)
- PCDS → 0: feature conflates phoneme identity with semantic content (bad)
- Use MI estimated via KSG estimator (sklearn mutual_info_classif as fast approximation)

**Labels**: phoneme labels from MFA alignment; semantic labels from LibriSpeech transcripts (noun/verb POS as proxy).

**[NEW] Empirical motivation from ACES (Parekh et al. 2603.03359, 2026):**
ACES extracts accent-discriminative subspaces from Wav2Vec2-base and finds:
- Accent info concentrates in low-dimensional early-layer subspace (layer 3, k=8)
- Linear attenuation of accent subspace **DOES NOT reduce disparity** — slightly worsens it
- Conclusion: accent features are "deeply entangled with recognition-critical cues"
→ **This is exactly the Isolate(F,A) failure mode we want AudioSAEBench M4 to detect!**
→ If AudioSAE accent features fail PCDS/Isolate test → expected & documented by ACES
→ Cite in Paper B §2.2: "Prior work shows accent features entangled with WER-critical cues [Parekh et al. 2026]; AudioSAEBench M4 (Isolate metric) quantifies this per-feature entanglement."
→ ACES = PCA-based (subspace); AudioSAEBench M4 = SAE-feature-based (monosemantic) — ACES motivates but doesn't solve the measurement problem
→ **Gap #29 candidate**: Are ACES accent PCA directions captured by AudioSAE monosemantic features? If not → SAE and linear subspace methods diverge on accent representation.

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
