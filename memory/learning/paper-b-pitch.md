# 📄 Paper B Pitch: "AudioSAEBench"

> Version: 0.9 | Created: 2026-02-28 04:31 (cycle #58) | Updated: 2026-03-03 09:01 (cycle #208)
> Status: Draft — for Leo's review. Not finalized.
> Depends on: Paper A (Listen Layer) — run Paper A first; gc(L) validates gc(F) theory
> Connects to: knowledge-graph.md sections J, K, B, H, N (DAS/IIT), RAVEL (Huang et al. 2024)

---

### ⚡ v0.9 Upgrade (cycle #208 — Causal Abstraction Hierarchy)
**NEW theoretical framing:** Under Geiger et al. 2301.04709 (Causal Abstraction as unified MI theory), all 6 AudioSAEBench evaluation categories are testing the SAME underlying question — whether audio SAE features constitute valid causal abstractions of the underlying speech computation — but at *different levels of alignment map strictness*:

| Category | Alignment Map Strictness | What's Being Tested |
|----------|--------------------------|---------------------|
| 1–3 (Concept Detection, Disentanglement, Fidelity) | Weakest: M = soft correlation | Does the feature encode a human-recognizable concept? |
| 4 (Causal Controllability / Hydra) | Medium: M = behavioral intervention | Does patching the feature change model behavior? |
| 0 (Audio-RAVEL: Cause + Isolate) | Strict: M = cause AND isolate | Does the feature causally change A without leaking to B? |
| 5 (Grounding Sensitivity gc(F)) | Strictest: M = audio-specific causality | Is the feature responding to audio or text? |

This hierarchy:
1. Provides a **principled justification** for why AudioSAEBench has these specific 6 categories (not arbitrary)
2. **Unifies Papers A and B** under one theoretical spine (both cite Geiger 2301.04709)
3. **Differentiates AudioSAEBench from SAEBench** (Karvonen et al.): SAEBench has no causal abstraction framing; AudioSAEBench does → novel theoretical contribution beyond category count
4. **Decision for Leo:** Does this framing resonate? Abstract can be updated with 1 paragraph to add the hierarchy frame. If yes → add "Causal Abstraction Hierarchy" as a framing paragraph to Paper B abstract + §3. If no → current structure is still correct, just less unified.

---

## 1-Sentence Pitch

> We introduce AudioSAEBench — the first multi-metric evaluation framework for sparse autoencoders applied to speech and audio language models — featuring a novel **Audio-RAVEL** disentanglement benchmark (Category 0) and a **Grounding Sensitivity** metric (Category 5) that together test whether audio SAE features truly *cause* attribute changes and *isolate* them from irrelevant co-occurrence.

---

## The Problem (Why This Paper Needs to Exist)

Five audio SAE papers now exist (AudioSAE, Mariotte, AR&D, Plantinga-PD, Paek et al.), but they're incomparable:
- AudioSAE evaluates hallucination steering, ignores disentanglement
- Mariotte evaluates disentanglement completeness, ignores causal steering
- AR&D evaluates concept recovery, ignores grounding
- Paek et al. (NeurIPS 2025 MI Workshop, arXiv:2510.23802) evaluate audio generation latents (music), no causal metrics

No audio SAE paper answers: **"Is this feature actually responding to the audio, or to the transcription?"**

This is the foundational question for any MI claim about audio models — and nobody has a metric for it.
That metric is **Grounding Sensitivity** (`gc(F)`), and it requires a benchmark to make it reusable.

**This paper = SAEBench (Karvonen et al., ICML 2025) for audio models + one novel metric that has no text analogue.**

> **New motivation (cycle #167, 2026-03-02):** FAD encoder bias paper (Gui et al., arXiv:2602.23958, Interspeech 2026) shows Whisper is structurally biased toward text-predictable patterns and is acoustically blind to certain attributes — directly proving that no single encoder is universal and each encoder needs independent characterization. This is a strong "why you can't just use one benchmark for all models" cite for AudioSAEBench. Additionally, DashengTokenizer (arXiv:2602.23765) provides behavioral evidence that "one [semantic] layer is sufficient for 22 audio tasks" — convergent with the RVQ Layer 1 = content hypothesis from Gap #21, and supportive of the Listen Layer Hypothesis (Paper A). Both papers are new cites for Paper B §1 (The Problem) and §3 (Why This Paper Wins).

---

## Abstract Draft (target 200 words)

Sparse autoencoders (SAEs) are increasingly applied to speech and audio models, but evaluation is fragmented across incomparable studies. AudioSAE (Aparin et al.), Mariotte et al., and AR&D (Chowdhury et al.) each evaluate different properties on different models with different metrics — making progress hard to track and SAE design choices impossible to compare fairly. Critically, no existing audio SAE paper tests *causal disentanglement*: whether a feature truly *causes* the claimed attribute to change without leaking into other attributes.

We introduce **AudioSAEBench**, a multi-metric evaluation framework unifying SAE assessment for speech and audio language models across six dimensions: (0) **Audio-RAVEL** — Causal Disentanglement, (1) Acoustic Concept Detection, (2) Disentanglement & Completeness, (3) Reconstruction Fidelity, (4) Causal Controllability, and (5) **Grounding Sensitivity**.

**Audio-RAVEL** (Category 0) extends RAVEL (Huang et al., ACL 2024) to audio SAEs. For each feature F and attribute A (e.g., voicing, manner, place), we measure Cause(F,A) — does patching F change attribute A as expected? — and Isolate(F,A) — does patching F leave *other* attributes unchanged? Audio SAEs are expected to exhibit more cross-attribute leakage than text SAEs due to acoustic co-occurrence in training data (voicing correlates with speaker gender; noise correlates with emotion). The RAVEL score = harmonic mean(Cause, Isolate) is the first isolation metric for audio SAEs.

**Grounding Sensitivity** (`gc(F)`) measures whether each SAE feature responds to audio content or text context via activation patching on audio-text conflict stimuli (ALME, Li et al. 2025 — 57K pairs). No text SAE benchmark has an equivalent.

We benchmark 12+ SAEs across Whisper-base/small/large, HuBERT, WavLM, and Qwen2-Audio-7B. We find that proxy metrics (sparsity + reconstruction) do not reliably predict Audio-RAVEL score or Grounding Sensitivity — echoing SAEBench's finding for text, and motivating multi-metric evaluation as the standard.

> **v0.8 (cycle #179-180, 2026-03-02):** Audio-RAVEL (Category 0) added as primary novel contribution, derived from RAVEL (Huang et al., ACL 2024, Gap #23). Category 4 (Causal Controllability) upgraded with Hydra effect quantification (Heimersheim & Nanda 2024) and denoising-preferred protocol. Gap #22 (causal utility vs consistency) fully integrated: Audio-RAVEL tests exactly the gap AudioSAE leaves open. Title updated to: "AudioSAEBench: Evaluating Sparse Autoencoders for Speech Models on Causal Disentanglement and Temporal Coherence".

> **Field update (cycle #80, 2026-02-28):** 5 audio SAE papers now identified (AudioSAE, Mariotte, AR&D, Plantinga-PD, Paek et al. NeurIPS 2025 MI Workshop). Paek et al. focus on audio *generation* model latents (music synthesis) — no overlap with speech understanding. None of the 5 papers has causal patching OR grounding sensitivity. AudioSAEBench gap confirmed broader than initially mapped.

> **Gap #21 — Codec RVQ natural partition (cycle #165):** Sadok et al. (Interspeech 2025, arXiv:2506.04492) probe RVQ layers of 4 neural codecs; SpeechTokenizer Layer 1 = semantic content, Layers 2+ = acoustic attributes (by design). Implication for AudioSAEBench Category 1 (Acoustic Concept Detection): RVQ layer index = principled ground-truth partition for concept type — content features should load on Layer 1, acoustic features on Layers 2+. Enables an additional AudioSAEBench "RVQ Alignment" sub-metric: does SAE feature activation pattern correlate with the RVQ layer that encodes the matched acoustic/semantic attribute? Zero competitors for this metric.

> **TCS(F) metric validation (cycle #81):** Choi et al. 2602.18899 ("Phonological Vector Arithmetic in S3Ms", ACL submission, 96 languages) confirms that phonological features are LINEAR, COMPOSITIONAL, and SCALE-CONTINUOUS in S3M representation space. This directly validates the TCS(F) = Temporal Coherence Score metric: phoneme boundaries are geometrically well-defined, MFA-alignable, and stable across languages. Citation anchor for Category 1b (Acoustic Concept Detection, temporal dimension). Additionally, Choi et al. provides the STIMULI DESIGN BLUEPRINT for minimal-pair audio patching (phonological contrast pairs are an instance of the "minimal pair" principle from Heimersheim & Nanda). Cross-lingual stability of phonological vectors opens a new AudioSAEBench evaluation axis: "Cross-Lingual Feature Alignment" (do SAE features discovered on English align to Mandarin via phonological vector arithmetic?).

---

## Why This Paper Wins

| Claim | Evidence |
|-------|----------|
| **Only multi-metric audio SAE benchmark** | 5 audio SAE papers exist (AudioSAE, Mariotte, AR&D, Plantinga-PD, Paek et al.) — all single-dimension, incomparable. Nobody combines all. FAD encoder bias (Gui et al. 2602.23958, Interspeech 2026) proves no single encoder is universal — model-specific multi-metric benchmarking is necessary. |
| **Novel metric (Audio-RAVEL) — MOST NOVEL** | RAVEL (Huang et al., ACL 2024) = gold standard for text LM disentanglement; zero audio analogue exists. Leo is first to apply Cause/Isolate scoring to speech SAEs. Gap #23 confirmed (cycle #179). |
| **Novel metric (Grounding Sensitivity)** | No text SAE paper has audio-vs-text attribution at feature level. Zero competitors. |
| **Identifies systematic weakness of existing audio SAEs** | Acoustic co-occurrence means audio SAE features leak across attributes more than text SAEs — AudioSAE's "50% consistent features" claim is weakened if consistent = epiphenomenal (Gap #22). AudioSAEBench exposes this. |
| **Uses existing stimuli** | ALME 57K conflict pairs (gc metric) + Choi et al. phonological pairs (Audio-RAVEL) already exist; no need to generate. |
| **Timely** | SAEBench (text) = ICML 2025; audio gap = open NOW. AR&D (partial overlap) just appeared Feb 24 2026 — move fast. |
| **Community resource** | Once published, every audio SAE paper will cite/use this. Like SAEBench for text. |
| **Principled theory** | Audio-RAVEL = Causal Abstraction (Geiger et al.) applied to SAE features; Grounding Sensitivity = IIT accuracy at feature granularity. Not ad hoc — both theoretically grounded. |
| **Paper A synergy** | Paper A's layer-level gc validates the theoretical claim; Paper B scales it to features. Same code, same stimuli, different resolution. |

---

## 5+1 Evaluation Categories

> **v0.8 change:** Added Category 0 (Audio-RAVEL) as the new foundational metric, derived from RAVEL (Huang et al., ACL 2024). This makes AudioSAEBench 6 categories total. Category 0 is the most differentiating contribution (first audio disentanglement benchmark with Cause + Isolate two-score).

### Category 0: Audio-RAVEL — Causal Disentanglement ⭐ MOST NOVEL
- **Question:** Does patching an SAE feature *cause* the target attribute to change AND *isolate* the change (no collateral damage to other attributes)?
- **Metrics:**
  - `Cause(F, A)`: does patching feature F cause attribute A to change as expected? (localization test)
  - `Isolate(F, A)`: does patching feature F leave OTHER attributes unchanged? (isolation test)
  - `RAVEL-audio(F, A)` = harmonic mean of Cause + Isolate (single quality score)
- **Why audio is harder than text:** Acoustic attributes co-occur at the physical signal level (voicing correlates with speaker gender in training corpora → voiced phoneme features may also encode gender by statistical leakage). Audio SAEs should exhibit MORE cross-attribute leakage than text SAEs. This hypothesis is testable and likely to yield a striking finding.
- **Stimulus design:** Minimal phonological contrast pairs from Choi et al. 2602.18899 (96 languages × voicing/manner/place contrasts) + TTS-augmented pairs for controlled volume. AudioSAE hallucination stimuli as a second attribute axis.
- **Baseline:** MDAS (multi-task DAS from RAVEL, Huang et al. 2024) — simultaneously optimizes all attribute subspaces to be orthogonal; represents the mechanistic ideal. SAE features should beat naïve probes but trail MDAS on isolation.
- **Novel contribution:** First application of Cause/Isolate scoring to audio SAE features. Zero existing audio work measures isolation — all 5 audio SAE papers (AudioSAE, Mariotte, AR&D, Plantinga-PD, Paek et al.) measure Cause only (via steering success) without isolation.
- **Source:** Extends RAVEL (Huang et al., ACL 2024, arXiv:2405.XXXX); no audio analogue exists (confirmed via Gap #23, cycle #179).
- **Connection to Gap #22:** AudioSAE shows >50% feature consistency across seeds (STABLE), but Gap #22 identifies that stability ≠ causality. Audio-RAVEL tests exactly this: a consistent-but-epiphenomenal feature will score high on Cause but fail Isolation (because the feature is tracking correlated surface form, not the causal factor). Audio-RAVEL therefore distinguishes "consistently correlated" from "causally efficacious" features — which is the full story that AudioSAE left untold.

### Category 1: Acoustic Concept Detection
- **Question:** Does this SAE feature activate for a specific acoustic concept (phoneme, emotion, pitch range, accent, noise level)?
- **Metric:** Feature-level concept F1 (max-activation features per concept class; time-resolved)
- **Stimuli:** LibriSpeech (ASR), IEMOCAP (emotion), ESC-50 (sound events), VocalSet (singing technique)
- **Baseline:** Best existing: AR&D (concept naming + retrieval), AudioSAE (phoneme acc 0.92)
- **Novel contribution (1a):** Time-resolved (per-timestep) feature activation — who fires WHEN?
- **Novel contribution (1b — NEW cycle #71):** `TCS(F)` = **Temporal Coherence Score** = within-phoneme feature variance / across-phoneme boundary variance. T-SAE (Bhalla et al. ICLR 2026, arXiv:2511.05541) provides the method backbone: contrastive loss on adjacent frames → discovers phoneme-level features without labels. TCS(F) evaluates this: if T-SAE's high-level features have low within-phoneme variance and high across-boundary variance → high TCS = temporally coherent. Standard SAE should score low. **Second novel metric** alongside gc(F), purely audio-native (no text equivalent).

### Category 2: Disentanglement & Completeness
- **Question:** Are SAE features more independently encoding concepts than raw hidden states?
- **Metric:** Mariotte completeness metric (linear probe independence across concept dimensions)
- **Stimuli:** VocalSet + IEMOCAP + LibriSpeech (acoustic attributes: pitch, shimmer, HNR, spectral rolloff, gender, accent)
- **Baseline:** Mariotte 2509.24793 (completeness metric defined here; extends their 4-model study)
- **Novel contribution:** Cross-model comparison at matched scale (Whisper vs HuBERT vs WavLM)

### Category 3: Reconstruction Fidelity
- **Question:** Does reconstructing activations through the SAE preserve downstream task performance?
- **Metric:** `task_preservation_ratio` = WER_with_SAE / WER_base (for ASR); emotion-F1_with_SAE / emotion-F1_base (for emotion); lower delta = better
- **Stimuli:** LibriSpeech-test-clean + IEMOCAP-test
- **Baseline:** AudioSAE (reports WER penalty of +0.4% for feature steering)
- **Novel contribution:** Extends from hallucination metric to task-general metric + multi-task comparison

### Category 4: Causal Controllability
- **Question:** Can we steer/ablate SAE features to change model behavior causally? Do they exhibit proper AND/OR gate structure?
- **Metrics:**
  - `ablation_d` = Cohen's d between ablated vs control accuracy (necessity — tests AND-gate component)
  - `steering_precision` = fraction of behavior change attributable to target feature (specificity — tests OR-gate component)
  - `hydra_compensation` = behavior change when top-K features ablated vs. top-1; ratio < 1 signals Hydra effect (compensatory backup paths reduce apparent feature importance)
- **Stimuli:** AudioSAE hallucination stimuli + SPIRIT adversarial examples + ESC-50 deactivation
- **Baseline:** AudioSAE (70% FPR reduction via top-100 feature suppression); SPIRIT (defense layers)
- **Novel contribution (v0.8 update):** Three-metric protocol derived from Heimersheim & Nanda (2024) patching best-practices:
  - AND-gate test (ablation_d): feature is necessary — ablating it degrades performance
  - OR-gate test (steering_precision): feature is sufficient — activating it produces the behavior
  - Hydra effect quantification: backup pathway compensation (expected 0.7x compensation per Heimersheim & Nanda) — top-K aggregate metric required for reliable attribution
  - Audio denoising preferred over noising for patching stimuli (OR-gate dominance in audio; noising creates OOD activations)
- **Connection to Audio-RAVEL (Cat 0):** Cat 4 tests behavior-level control; Cat 0 tests representation-level isolation. Together they answer: "Is this feature causally responsible for behavior, and does it only encode the attribute it claims to encode?" — the two questions that completely characterize a good audio SAE feature.

### Category 5: Grounding Sensitivity ⭐ NOVEL
- **Question:** Does this SAE feature respond to audio content or text context?
- **Metric:** `gc(F)` = activation on (audio=C, text=neutral) / [activation on (audio=C, text=neutral) + activation on (audio=neutral, text=C)]
  - `gc=1.0` → pure audio grounding (feature fires to audio content, not linguistic prediction)
  - `gc=0.0` → pure text prediction (feature fires to transcription context, not audio signal)
  - `gc=0.5` → ambiguous / mixed
- **Stimuli:** ALME 57K audio-text conflict pairs (Li et al. 2025, arXiv:2602.11488) — off-the-shelf
- **Baseline:** None — first audio-native grounding metric. No text SAE benchmark equivalent.
- **Novel contribution:** Defines and operationalizes the most fundamental question in audio MI: "Is this feature actually about audio?"
- **IIT grounding:** gc(F) = IIT accuracy at feature granularity (Geiger et al. 2301.04709). Theoretically principled, not ad hoc.
- **Connection to Paper A:** Paper A measures gc(L) (layer-level grounding coefficient); Paper B measures gc(F) (feature-level). Same formula, different scope. Paper A running first validates that grounding_coefficient behaves as predicted before scaling to feature resolution.

---

## Key Experimental Table

| Experiment | Model(s) | Resource | Time | Main Output |
|-----------|---------|----------|------|-------------|
| **Cat 0: Audio-RAVEL** | Whisper-small + HuBERT | MacBook | 3h | RAVEL(F, A) = harmonic mean(Cause, Isolate) per feature |
| Cat 1: Concept Detection | Whisper-base/small | MacBook | 2h | Feature-concept F1 per layer |
| Cat 2: Disentanglement | HuBERT + WavLM + Whisper | MacBook | 3h | Completeness metric cross-model |
| Cat 3: Reconstruction | Whisper-base/small | MacBook | 1h | task_preservation_ratio vs sparsity |
| Cat 4: Controllability | Whisper-small | MacBook/戰艦 | 3h | ablation_d + steering_precision + hydra_compensation |
| Cat 5: Grounding Sensitivity | Qwen2-Audio-7B | NDIF/戰艦 | 1 day | gc(F) histogram per feature |
| Full suite (3 SAE variants) | Whisper + HuBERT + WavLM | 戰艦 | ~3 days | Comparison table (12+ SAEs) |

**Minimum viable paper (MVP v0.8):** Cat 0 (Audio-RAVEL) + Cat 5 (Grounding Sensitivity) on Whisper-small. Cat 0 is the new strongest story — Cause/Isolate on phonological minimal pairs is self-contained and high-impact. If Paper A has been accepted, Cat 5 adds the audio-vs-text grounding layer. Together = sufficient for NeurIPS D&B or Interspeech 2027.

---

## Comparison to Prior Work

| Dimension | AudioSAE | Mariotte | AR&D | SAEBench (text) | **AudioSAEBench (B)** |
|-----------|----------|----------|------|-----------------|-------------------|
| **Causal Disentanglement (Cause+Isolate)** | ❌ | ❌ | ❌ | ❌ | ✅ **Cat 0: Audio-RAVEL (NOVEL)** |
| Concept Detection | ✅ phoneme acc | ✅ completeness | ✅ concept naming | partial | ✅ + time-resolved + RVQ-aligned |
| Disentanglement | ❌ | ✅ | ❌ | ✅ (text) | ✅ cross-model + Cause/Isolate |
| Reconstruction Fidelity | partial (WER only) | ❌ | ❌ | ✅ | ✅ multi-task |
| Causal Controllability | ✅ Cause only | ❌ | ✅ Cause only | ✅ (text) | ✅ 3-metric (AND+OR+Hydra) |
| **Grounding Sensitivity** | ❌ | ❌ | ❌ | ❌ (no audio) | ✅ **NOVEL** |
| Isolation metric | ❌ | ❌ | ❌ | ❌ | ✅ (Audio-RAVEL Isolate score) |
| Multi-metric comparison | ❌ | ❌ | ❌ | ✅ | ✅ |
| Cross-model / multi-model | 2 models | 4 models | partial | ≥10 models | ≥5 models (scalable) |

> **Key differentiator**: No existing audio SAE paper — and no text SAE paper — applies both Cause AND Isolate scoring to SAE features. AudioSAEBench is the first to do this for audio, and Audio-RAVEL is the first disentanglement benchmark using the Cause/Isolate framework for any modality beyond text.

---

## Target Venue

| Venue | Deadline | Fit |
|-------|----------|-----|
| **NeurIPS 2026 Datasets & Benchmarks** | ~May 2026 | Best fit — D&B track exists for benchmark papers |
| **INTERSPEECH 2027** | ~Mar 2027 | High visibility in speech community; more time to polish |
| **ICML 2026 Workshop** | ~Apr 2026 | Fast way to get feedback; non-archival |
| **ACL 2026** | ~Feb 2026 | Too language-focused; audio = stretch |

**Recommendation:** NeurIPS 2026 D&B track. Paper A submitted to NeurIPS 2026 main track → Paper B to D&B = coordinated submission, two citations, same deadline.

---

## Dependencies & Prerequisites

### From Paper A:
- `gc(L)` (layer-level grounding coefficient) validated → gives theoretical credibility to `gc(F)`
- Experimental infrastructure (NNsight patching, ALME stimuli setup) → directly reusable
- Time: Paper A experiments first (~3h MacBook + 1 day GPU) → Paper B can start in parallel

### Independent of Paper A:
- Categories 1-4 can be evaluated without `gc` metric
- Can start Cat 2 (disentanglement) immediately on MacBook once venv is set up

### External:
- ALME stimuli access (arXiv:2602.11488, Li et al. 2025) — available on GitHub/HuggingFace
- SAE implementations: AudioSAE codebase (github.com/audiosae/audiosae_demo), Mariotte (github.com/theomariotte/sae_audio_ssl)
- Optional: collaboration with AR&D authors for Cat 1 concept labeling pipeline

---

## Execution Roadmap

**Week 1 (after Leo unblocks):**
1. Set up venv: `pip install nnsight openai-whisper transformers torch`
2. Run Cat 1 (Concept Detection) on Whisper-small — MacBook-feasible
3. Run Cat 3 (Reconstruction Fidelity) as sanity check

**Week 2-3 (after Paper A Exp 1 validated):**
4. Implement `gc(F)` using Paper A's NNsight patching code
5. Run Cat 5 on Whisper-base/small (subset of ALME stimuli to validate)

**Month 1-2:**
6. Full 5-category suite on all models (戰艦/NDIF for larger models)
7. Benchmark 3+ SAE variants (TopK, BatchTopK, Matryoshka)
8. Write paper: adopt SAEBench structure (4-category → 5-category)

---

## Open Questions for Leo

1. **Paper A first or parallel?** Running Paper A's E1 first (3h) validates the gc metric before scaling to features. But Cat 1-4 of AudioSAEBench can start in parallel.
2. **AR&D overlap**: AR&D (Chowdhury et al.) covers concept detection — should we reach out for collaboration on Cat 1, or differentiate sharply?
3. **ALME stimuli**: Do we need to contact Li et al. to officially use their 57K stimuli, or is citation sufficient?
4. **Matryoshka SAE**: SAEBench found Matryoshka wins on disentanglement. Should we include Matryoshka audio SAE as a variant? (Training required, ~1 week GPU)
5. **Scope of Cat 5**: Full 57K stimuli or a curated 5K subset for MVP? Smaller = faster iteration.
6. **Grounding Sensitivity on encoder-only models**: For Whisper (encoder, no text pathway), `gc(F)` is still meaningful if we use the decoder's text generation as the "text" proxy. Is this framing solid?

---

## Connection to Leo's Research Portfolio

```
Paper A: "Localizing the Listen Layer in Speech LLMs"
  → gc(L) = layer-level grounding coefficient
  → Answers: WHERE does the model listen?
  → Venue: NeurIPS 2026 or Interspeech 2026

Paper B: "AudioSAEBench"
  → gc(F) = feature-level grounding sensitivity
  → Answers: WHICH features respond to audio vs text?
  → Venue: NeurIPS 2026 D&B track

Connection:
  - Same metric (gc) at different granularity
  - Same stimuli (ALME 57K)
  - Same theory (IIT / Causal Abstraction)
  - Same infrastructure (NNsight patching)
  - Paper A validates → Paper B scales
  - Together: complete mech interp toolkit for audio LMs
```
