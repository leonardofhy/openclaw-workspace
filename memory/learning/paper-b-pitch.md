# 📄 Paper B Pitch: "AudioSAEBench"

> Version: 0.1 | Created: 2026-02-28 04:31 (cycle #58)
> Status: Draft — for Leo's review. Not finalized.
> Depends on: Paper A (Listen Layer) — run Paper A first; gc(L) validates gc(F) theory
> Connects to: knowledge-graph.md sections J, K, B, H

---

## 1-Sentence Pitch

> We introduce AudioSAEBench — the first multi-metric evaluation framework for sparse autoencoders applied to speech and audio language models — featuring a novel **Grounding Sensitivity** metric that measures how much each SAE feature responds to audio content vs. text context.

---

## The Problem (Why This Paper Needs to Exist)

Three audio SAE papers exist (AudioSAE, Mariotte, AR&D), but they're incomparable:
- AudioSAE evaluates hallucination steering, ignores disentanglement
- Mariotte evaluates disentanglement completeness, ignores causal steering
- AR&D evaluates concept recovery, ignores grounding

No audio SAE paper answers: **"Is this feature actually responding to the audio, or to the transcription?"**

This is the foundational question for any MI claim about audio models — and nobody has a metric for it.
That metric is **Grounding Sensitivity** (`gc(F)`), and it requires a benchmark to make it reusable.

**This paper = SAEBench (Karvonen et al., ICML 2025) for audio models + one novel metric that has no text analogue.**

---

## Abstract Draft (target 200 words)

Sparse autoencoders (SAEs) are increasingly applied to speech and audio models, but evaluation is fragmented across incompatible studies. AudioSAE (Aparin et al.), Mariotte et al., and AR&D (Chowdhury et al.) each evaluate different properties on different models with different metrics — making progress hard to track and SAE design choices impossible to compare fairly.

We introduce **AudioSAEBench**, a multi-metric evaluation framework that unifies SAE assessment for speech and audio language models across five dimensions: (1) Acoustic Concept Detection, (2) Disentanglement & Completeness, (3) Reconstruction Fidelity, (4) Causal Controllability, and (5) **Grounding Sensitivity** — a novel metric unique to audio SAEs.

**Grounding Sensitivity** (`gc(F)`) measures whether each SAE feature responds to audio content or text context by applying activation patching on audio-text conflict stimuli (ALME, Li et al. 2025 — 57K pairs). A feature with `gc=1.0` is purely audio-grounded; `gc=0.0` is purely text-predicted. This is the audio-native counterpart to Paper A's layer-level grounding coefficient, scaled to the feature level. No text SAE benchmark has an equivalent.

We benchmark 12+ SAEs across Whisper-base/small/large, HuBERT, WavLM, and Qwen2-Audio-7B. We find that proxy metrics (sparsity + reconstruction) do not reliably predict Grounding Sensitivity — echoing SAEBench's finding for text, and motivating multi-metric evaluation as the standard.

---

## Why This Paper Wins

| Claim | Evidence |
|-------|----------|
| **Only multi-metric audio SAE benchmark** | AudioSAE = 2 metrics; Mariotte = 1; AR&D = 1. Nobody combines all. |
| **Novel metric (Grounding Sensitivity)** | No text SAE paper has audio-vs-text attribution at feature level. Zero competitors. |
| **Uses existing stimuli** | ALME 57K conflict pairs already exist; no need to generate. |
| **Timely** | SAEBench (text) = ICML 2025; audio gap = open NOW. AR&D (partial overlap) just appeared Feb 24 2026 — move fast. |
| **Community resource** | Once published, every audio SAE paper will cite/use this. Like SAEBench for text. |
| **Principled theory** | Grounding Sensitivity = IIT accuracy (Geiger et al.) at feature granularity. Not ad hoc. |
| **Paper A synergy** | Paper A's layer-level gc validates the theoretical claim; Paper B scales it to features. Same code, same stimuli, different resolution. |

---

## 5 Evaluation Categories

### Category 1: Acoustic Concept Detection
- **Question:** Does this SAE feature activate for a specific acoustic concept (phoneme, emotion, pitch range, accent, noise level)?
- **Metric:** Feature-level concept F1 (max-activation features per concept class; time-resolved)
- **Stimuli:** LibriSpeech (ASR), IEMOCAP (emotion), ESC-50 (sound events), VocalSet (singing technique)
- **Baseline:** Best existing: AR&D (concept naming + retrieval), AudioSAE (phoneme acc 0.92)
- **Novel contribution:** Time-resolved (per-timestep) feature activation — who fires WHEN?

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
- **Question:** Can we steer/ablate SAE features to change model behavior causally?
- **Metrics:**
  - `ablation_d` = Cohen's d between ablated vs control accuracy (necessity)
  - `steering_precision` = fraction of behavior change attributable to target feature (specificity)
- **Stimuli:** AudioSAE hallucination stimuli + SPIRIT adversarial examples + ESC-50 deactivation
- **Baseline:** AudioSAE (70% FPR reduction via top-100 feature suppression); SPIRIT (defense layers)
- **Novel contribution:** Two-test protocol (necessity + controllability, matching Heimersheim & Nanda distinction)

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
| Cat 1: Concept Detection | Whisper-base/small | MacBook | 2h | Feature-concept F1 per layer |
| Cat 2: Disentanglement | HuBERT + WavLM + Whisper | MacBook | 3h | Completeness metric cross-model |
| Cat 3: Reconstruction | Whisper-base/small | MacBook | 1h | task_preservation_ratio vs sparsity |
| Cat 4: Controllability | Whisper-small | MacBook/戰艦 | 3h | ablation_d + steering_precision |
| Cat 5: Grounding Sensitivity | Qwen2-Audio-7B | NDIF/戰艦 | 1 day | gc(F) histogram per feature |
| Full suite (3 SAE variants) | Whisper + HuBERT + WavLM | 戰艦 | ~3 days | Comparison table (12+ SAEs) |

**Minimum viable paper (MVP):** Cat 1 + Cat 5 only, Whisper-small + Qwen2-Audio-7B. That's enough for a NeurIPS D&B or Interspeech paper if Paper A has been accepted and gc is validated.

---

## Comparison to Prior Work

| Dimension | AudioSAE | Mariotte | AR&D | **AudioSAEBench (B)** |
|-----------|----------|----------|------|-------------------|
| Concept Detection | ✅ phoneme acc | ✅ completeness | ✅ concept naming | ✅ + time-resolved |
| Disentanglement | ❌ | ✅ | ❌ | ✅ cross-model |
| Reconstruction Fidelity | partial (WER only) | ❌ | ❌ | ✅ multi-task |
| Causal Controllability | ✅ | ❌ | ✅ | ✅ 2-test protocol |
| **Grounding Sensitivity** | ❌ | ❌ | ❌ | ✅ **NOVEL** |
| Multi-metric comparison | ❌ | ❌ | ❌ | ✅ |
| Cross-model / multi-model | 2 models | 4 models | partial | ≥5 models |

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
