# Q057: Paper A §4 — 3-Tier Grounding Failure Taxonomy with Predicted gc(k) Signatures

> Cycle: c-20260306-0931 | Phase: converge | Track: T3 | Action: build (Tier 0 doc)
> Status: COMPLETE ✅

---

## Overview

**Gap #31** (introduced cycle #293) proposes a unified taxonomy of audio grounding failures across 3 architectural tiers: codec, connector, and LLM. Each tier corresponds to a distinct failure mode with a *falsifiable* gc(k) signature — a predicted curve shape from the Listen Layer framework.

This document provides:
1. The 3-tier taxonomy table with citations
2. Predicted gc(k) curve shapes (falsifiable)
3. Three specific falsifiable predictions (Paper A §4)
4. Connections to experimental design (P0–P3 in experiment-queue.md)

---

## 1. The 3-Tier Grounding Failure Taxonomy

| Tier | Location | Failure Mode | Behavioral Evidence | gc(k) Prediction |
|------|----------|-------------|---------------------|-----------------|
| **T1: Codec** | RVQ tokenizer | Information destroyed at discrete quantization; acoustic signal never enters model | Sadok et al. (Interspeech 2025, arXiv:2506.04492): semantic content only in layer 1 of SpeechTokenizer; acoustic attributes lost in RVQ | **Flat near-0**: gc(k) ≈ 0 for ALL layers — signal not present anywhere in model; auditory patching has no effect |
| **T2: Connector** | Multimodal projector | Phonological geometry present in encoder but collapses after projection; connector = modality bottleneck | Gap #18 (phonological vector arithmetic): Choi et al. (arXiv:2602.18899) confirm linearity in S3M; unknown if geometry survives connector | **Hump-then-drop**: gc(k) peaks in encoder layers (L_enc_peak ≈ middle of speech encoder), then collapses to near-0 after connector (connector layer L_c) |
| **T3: LLM** | Upper LM layers | Audio representations enter LLM but upper layers default to text priors; ALME phenomenon | Zhao et al. (arXiv:2602.23136) Modality Collapse; ALME 57K conflict pairs (arXiv:2602.11488): text dominance in LLM reasoning layers | **Rise-then-fall**: gc(k) rises from L_0 → peaks at L_mid (≈ 40–60% depth), then falls toward L_top as LM prior takes over |

---

## 2. Predicted gc(k) Curve Shapes

### Tier 1 — Flat Zero (Codec Failure)
```
gc(k)
1.0 |
    |
0.5 |
    |
0.0 |_________________________________________________
    L0  L4  L8  L12  [connector]  L0  L8  L16  L24
                      (encoder)               (LM layers)
```
**Prediction**: Audio patching at ANY layer produces ΔP(correct) ≈ 0. The speech encoder receives inputs that are semantically impoverished from the start. **Cite**: Sadok et al. (arXiv:2506.04492), layer 1 = all semantic content.

---

### Tier 2 — Hump-then-Drop (Connector Bottleneck)
```
gc(k)
1.0 |       ___
    |      /   \
0.5 |     /     \___________
    |    /
0.0 |___/                   (drops to ~0 after connector)
    L0  L4  L8  L12  [connector]  L0  L8  L16  L24
         (encoder layers)                  (LM layers)
```
**Prediction**: gc(k) peaks in the speech encoder (around encoder layer 6-8, consistent with Triple Convergence Hypothesis from whisper_hook_demo.py CKA), then collapses to near-0 immediately after the multimodal connector. The LM layers show near-zero audio sensitivity. **Cite**: Gap #18 (phonological geometry test), Choi et al. (arXiv:2602.18899), connector bottleneck hypothesis (Gap #14 Modality Collapse).

---

### Tier 3 — Rise-then-Fall (LLM Modality Collapse)
```
gc(k)
1.0 |              *
    |           *     *
0.5 |        *           *
    |     *                  *
0.0 |__*_                       *___
    L0  L4  L8  L12  [connector]  L0  L8  L16  L24
         (encoder layers)                  (LM layers)
         (encoder largely flat)   (peak here, then falls)
```
**Prediction**: Audio information enters the LM successfully (connector NOT a bottleneck), gc(k) rises through the early-to-mid LM layers (L_0 → L_mid ≈ 40-60% depth), then falls in upper layers as text priors dominate. This is the "Listen Layer" hypothesis in its standard form. **Cite**: ALME (arXiv:2602.11488), Modality Collapse (arXiv:2602.23136), Lin et al. 2502.17516 (§4.1: intermediate layers capture cross-modal interactions in VLMs — audio analog predicts same).

---

## 3. Three Falsifiable Predictions (Paper A §4)

These are concrete experimental predictions derivable from the taxonomy, stated before experiments are run:

### Prediction 1: SpeechTokenizer Layer-1-Only Corruption → Tier 1 Signature
**Test**: Replace all RVQ tokens with SpeechTokenizer Layer 1 content tokens (preserving Layer 2+ acoustic tokens) — this degrades phonological specificity while keeping LM-level semantics.  
**Predicted result**: gc(k) ≈ 0 across all layers (acoustic information gone; no layer can recover it via patching).  
**Falsification**: If gc(k) remains elevated at L_mid LM layers → semantic content alone is sufficient for listen-layer localization (revises Tier 1 failure criterion).  
**Citation anchor**: Sadok et al. SpeechTokenizer codec probe + Gap #21 RVQ-selective corruption design.

### Prediction 2: Connector Orthogonality Test → Tier 2 Detection
**Test**: Compute cosine similarity between voicing direction `h([d]) - h([t])` in Whisper encoder vs. after multimodal projection (Gap #18 experiment P0).  
**Predicted result**: Cosine similarity ≥ 0.7 (phonological geometry preserved through connector) → ruling out Tier 2 failure for Qwen2-Audio; if < 0.3 → Tier 2 failure confirmed for that model.  
**Falsification**: If cosine similarity is uncorrelated with downstream gc(k) peak location → phonological vector arithmetic is not the right proxy for grounding.  
**Citation anchor**: Choi et al. 2602.18899 (phonological vectors are linear in S3M), Gap #18 experiment spec (P0 in experiment-queue.md).

### Prediction 3: ALME Conflict Patching → Tier 3 gc(k) Peak at L_mid (35–60%)
**Test**: On ALME conflict stimuli (57K audio-text conflicts), sweep DAS-IIA (gc(k)) across all LM layers of Qwen2-Audio-7B via NNsight.  
**Predicted result**: gc(k) peaks at L_mid ≈ 35–60% of LM depth (≈ layers 10–17 out of 28 for Qwen2-Audio-7B).  
**Alternative hypotheses**: If peak is at L_early (< 25%) → connector directly injects audio into early LM processing (connector is more powerful than predicted); if peak is at L_late (> 75%) → text priors dominate and audio grounding is marginal throughout (Tier 3 failure is near-total).  
**Falsification criterion**: If gc(k) is flat (all values < 0.1) → Tier 2 failure is actually present (connector bottleneck, not LLM modality collapse).  
**Citation anchor**: ALME (arXiv:2602.11488), Modality Collapse (arXiv:2602.23136), Lin et al. 2502.17516 §4.1 VLM intermediate-layer finding.

---

## 4. Cross-Tier Disambiguation Protocol

Two tiers can superficially look similar until you check the right diagnostic:

| Confusion Pair | Differentiator | Method |
|---|---|---|
| Tier 1 vs Tier 2 | Tier 1: gc(k)=0 even in encoder. Tier 2: gc(k) > 0 in encoder, drops after connector. | Compute gc(k) separately for encoder layers only |
| Tier 2 vs Tier 3 | Tier 2: LM layers show gc(k) ≈ 0. Tier 3: LM layers show gc(k) > 0 (at least early LM). | Compute gc(k) for LM layers only (post-connector) |
| Mixed failures | Some layers show T2 signature, others T3 | Per-layer gc(k) curve plot resolves this |

**Protocol**: Always plot the FULL layer-sweep (encoder + connector + all LM layers). The transition point reveals which tier is responsible.

---

## 5. Connection to Prior Work

| Finding | Paper | Connection to Taxonomy |
|---|---|---|
| RVQ Layer 1 = semantic, L2+ = acoustic | Sadok et al. 2026 (arXiv:2506.04492) | Tier 1 failure mechanism: L2+ corruption = pure acoustic manipulation, L1 corruption = semantic corruption |
| Phonological features linear in S3M | Choi et al. 2026 (arXiv:2602.18899) | Tier 2 test: phonological geometry = proxy for connector preservation |
| Audio-text conflict → text dominates in LLM reasoning | Zhao et al. / ALME 2026 (arXiv:2602.23136, 2602.11488) | Tier 3 mechanism: LM prior overtakes audio signal in upper layers |
| Behavioral grounding degrades under scene complexity | Lee et al. 2026 (arXiv:2603.03855) | Tier 3 phenomenon: under high-complexity scenes, text priors amplified → gc(k) peak shifts later |
| Behavioral modality collapse quantified | Zhao et al. ALME | Tier 3 severity measure: higher collapse rate → gc(k) peak lower + earlier fall |
| Store ≠ Contribute (SCD) | AG-REPA (arXiv:2603.01006) | Meta-principle unifying all 3 tiers: "where audio is stored" ≠ "where audio causally controls output" |

---

## 6. Paper A §4 Section Structure (Draft Outline)

```
§4 Predicted Signatures of Grounding Failures
  §4.1 A Unified Taxonomy of Audio Grounding Failures
    - 3-tier classification (Codec / Connector / LLM)
    - Each tier: mechanism + prior behavioral evidence + predicted gc(k) shape
  §4.2 Three Falsifiable Predictions
    - P1: Codec corruption → flat-zero gc(k)
    - P2: Connector orthogonality → Tier 2 detection
    - P3: ALME conflict → Tier 3 gc(k) peak at L_mid (35–60%)
  §4.3 Cross-Tier Disambiguation Protocol
    - Encoder-only vs LM-only gc(k) diagnostic
    - Full layer-sweep as ground truth
  §4.4 Experimental Predictions Table (summary of §4.1–4.3)
```

This section positions Paper A's framework as *predictive*, not just descriptive — a hallmark of mature scientific contribution (Pearl Level 3 per Joshi et al. 2602.16698).

---

## 7. Connections to Other Work Items

- **experiment-queue.md P0** (Gap #18): Tests Prediction 2 (connector orthogonality)
- **experiment-queue.md P2** (ALME patching on Qwen2-Audio): Tests Prediction 3
- **gc_eval.py** (counterfactual mode, Q055): IncrimScore(k) = per-error version of same taxonomy
- **Paper B (AudioSAEBench)**: Category 0 Audio-RAVEL uses Tier 2/3 taxonomy to design stimuli (minimal pairs vs. conflict pairs)
- **Track 5 (MATS safety)**: Tier 3 failures where text prior = safety-problematic text → mechanistic safety probe target
- **Gap #30** (Modality Collapse as SAE Isolate failure): Tier 3 = predicted to show low SAE Isolate score for audio features
- **Gap #31 source**: 3-tier taxonomy unifies codec (Sadok) + connector (Gap #18) + LLM (Zhao/ALME) literatures

---

## Status

- [x] Taxonomy table written (3 tiers × 4 dimensions)
- [x] Predicted gc(k) curves drawn (ASCII)
- [x] 3 falsifiable predictions formalized with falsification criteria
- [x] Cross-tier disambiguation protocol written
- [x] Prior work connection table
- [x] Paper A §4 outline drafted
- [x] Connection map to experiment-queue / other tasks

**Artifact**: `memory/learning/cycles/gap31-tier-taxonomy-predictions.md` (this file)
**Task Q057**: COMPLETE ✅
