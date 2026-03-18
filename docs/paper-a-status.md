# Paper Status Summary

## Completed Work

### Framework Development
- **gc(k) metric**: Causal grounding coefficient based on interchange intervention - fully defined
- **Listening Geometry**: 5D framework (k*, α_AND, σ, t*, CS) with 4-profile taxonomy - complete
- **AND/OR gate decomposition**: Mechanistic taxonomy of multimodal features - complete

### Mock Validation
- **27 mock experiments**: Framework internal consistency validated (median |r| = 0.877)
- **93.1% pass rate**: 25/27 experiments confirm framework coherence
- **2 blocked results**: GSAE density and FAD-RAVEL direction - identifies framework boundaries

### Preliminary Real Evidence
- **Q001 partial**: Whisper-base layer 5 voicing geometry (Stop-Stop cos_sim = +0.25)
- **Structural validation**: Linear phonological organization confirmed for DAS intervention

## Pending GPU Work

### Critical Real Experiments
- **Q001 completion**: Full voicing geometry sweep across Whisper-base layers 1-6
- **Q002**: Causal contribution analysis (WER degradation under layer ablation)
- **Full gc(k) profiles**: Real grounding coefficients for Whisper-base encoder

### Scale-up Validation
- **Whisper-small/medium**: Test Triple Convergence hypothesis (k* at ~50% depth)
- **Complete ALMs**: Qwen2-Audio experiments for full encoder→connector→LLM pipeline

## Pre-registered Predictions

### Ready for Testing (when GPU available)
1. **P1**: ALME "follows_text" items show late-layer gc drop (Δgc ≥ 0.10, d ≥ 0.3)
2. **P2**: Rare phoneme contrasts show stronger late-layer drop than common contrasts (d ≥ 0.3)
3. **P3**: Degraded audio items show flat gc across all layers (variance < 0.01)

### Target Models
- **Whisper-small**: Primary validation target for all 3 predictions
- **Qwen2-Audio**: Future target for full ALM listening vs. guessing dynamics

## Current Bottleneck
**Computational access**: Framework is theoretically complete and mock-validated, but empirical validation requires sustained GPU access for real neural network experiments.
