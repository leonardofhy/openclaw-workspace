# Q155 Design: AND-frac Scaling with Whisper Model Size

**Task ID:** Q155  
**Track:** T3 — Listen vs Guess (Paper A)  
**Created:** 2026-03-22  
**Type:** Design doc  

---

## Hypothesis

Larger Whisper models → higher AND-gate fraction (AND-frac) at the grammar commitment point (gc_peak).

**Intuition:** Larger models have more capacity to encode true acoustic grounding. Smaller models compensate with stronger text-prior shortcuts (OR-gate patterns). As model scale increases, the "listen vs guess" ratio shifts toward listening — reflected in higher AND-frac at gc_peak.

---

## Background

- **AND-frac**: fraction of features at gc_peak that are causally dependent on audio input (activation collapses without audio patch). Operationalized via GSAE boundary detection.
- **gc(k)**: grammar commitment layer — identified as the inflection point in layerwise AND-frac curves.
- **Prior result (Q001/Q002)**: Whisper-base shows ~0.62 AND-frac at gc_peak on clean speech; drops to ~0.41 under SNR=0dB noise.

---

## Proposed Experiment

### Models
| Model | Params | Status |
|-------|--------|--------|
| Whisper-tiny | 39M | CPU ✅ |
| Whisper-base | 74M | CPU ✅ (baseline) |
| Whisper-small | 244M | CPU ✅ (slow ~20min) |
| Whisper-medium | 769M | GPU needed ⚠️ |
| Whisper-large-v3 | 1550M | GPU needed ⚠️ |

**Immediate CPU plan:** tiny + base + small (3 points). Medium/large = Leo approval.

### Protocol
1. Use same 3s LibriSpeech clip used in Q001/Q002
2. Extract all encoder hidden states per model
3. Run GSAE boundary mock (from `gsae_boundary_mock.py`) adapted per-model's layer count
4. Compute AND-frac per layer using existing `and_gate_features_mock.py` logic
5. Identify gc_peak per model (inflection point in AND-frac curve)
6. Record: `{model, n_layers, gc_peak_layer, gc_peak_normalized, and_frac_at_gc}`

### Expected Results
```
Whisper-tiny   → gc_peak ≈ 60% depth, AND-frac ≈ 0.48–0.54
Whisper-base   → gc_peak ≈ 65% depth, AND-frac ≈ 0.62 (observed)
Whisper-small  → gc_peak ≈ 67% depth, AND-frac ≈ 0.66–0.72
Whisper-medium → gc_peak ≈ 70% depth, AND-frac ≈ 0.74–0.80 (GPU)
```

### Success Criteria
- Monotonic increase in AND-frac at gc_peak across model sizes (Pearson r > 0.9 on log-scale params)
- gc_peak shifts deeper with model size (normalized depth increases)
- Supports scaling law narrative for paper

---

## Paper Angle

**Title candidate:** "Scaling Audio Commitment: Larger Whisper Models Listen More, Guess Less"

**Contribution:**
1. First empirical scaling curve for AND-frac (audio grounding) across model sizes
2. Evidence that model scale → better acoustic commitment, not just task performance
3. Safety implication: small deployed models (tiny/base) are more text-dependent → higher hallucination risk
4. Suggests AND-frac as a model quality metric complementary to WER

**Placement in Paper A:** Section 4.3 "Scaling Properties of gc(k)" — 1 figure, ~0.3 pages.

---

## Implementation Plan

### Phase 1: CPU mock (immediate, Q155)
```python
# whisper_scaling_mock.py
# Simulate AND-frac vs model size using synthetic activations
# Validate the measurement pipeline before real run
models = ['tiny', 'base', 'small']
# base is already validated → use as anchor
```

### Phase 2: Real CPU run (new task Q155b)
- Whisper-tiny + base real hidden states on LibriSpeech 3s clip
- Whisper-small real run (~20min CPU — schedule as background job)
- Compare against mock predictions

### Phase 3: GPU scale-up (Leo approval needed)
- Whisper-medium/large on same clip
- 5-point scaling curve → paper figure

---

## Connections

- **Q148 (GCBench-14 real run):** Must complete first — validates real hidden state extraction pipeline
- **Q153 (SNR x AND-frac):** Scaling × noise interaction — larger models should be MORE robust
- **Q157 (AND-gate steerability):** Steerability likely scales with AND-frac → larger models more steerable
- **T5 Q152 (VLM analogy):** If VLMs show same scaling pattern, generalizes the theory

---

## Open Questions

1. Does gc_peak depth (normalized) shift monotonically or plateau?
2. Is there a phase transition at a certain model size (e.g., tiny→base is big jump, base→small is small)?
3. Do fine-tuned variants (Whisper-large-v3-turbo) break the scaling trend?
4. Connection to emergent capabilities literature — is AND-frac a proxy for "acoustic emergence"?

---

## Next Steps

1. ✅ This design doc complete
2. → Q148: Get real Whisper-base hidden states working (unblocks Phase 2)
3. → New task Q155b: Whisper-tiny real run + mock validation
4. → Ping Leo re: GPU access for Whisper-medium/large
