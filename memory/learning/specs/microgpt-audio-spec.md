# MicroGPT-Audio: Toy Substrate Spec for DAS Validation

> Cycle: c-20260306-0731 | Track: T3 | Task: Q056
> Created: 2026-03-06

## Problem Statement

Why not just run DAS experiments directly on Whisper-small?

Three reasons:
1. **Interpretability opacity**: Whisper was trained on 680K hours with complex multi-task objectives. Its internal representations conflate phoneme identity, acoustic robustness, domain adaptation, and language modeling. A DAS result on Whisper could be real signal OR artifact of pre-training shortcuts.
2. **No ground truth causal graph**: We don't know Whisper's "intended algorithm." DAS validates that a *proposed* causal graph matches the model — but if we can't specify the ground truth, we can't tell a good result from a lucky one.
3. **MacBook constraints**: Full DAS on Whisper-small requires repeated activations on minimal pairs + interchange interventions. At 50MB activations per layer × 32 layers × N pairs, experiment iteration time is slow. A 200-line model with the same structural properties but 1000× fewer parameters would iterate in seconds.

**Solution:** Build a tiny VQ-discrete transformer (MicroGPT-Audio) trained on a synthetic dataset where we *know* the causal graph. Validate DAS methodology on this toy. Then transfer to Whisper with confidence.

---

## VQ Scheme

### Discrete tokenization (why VQ matters for DAS)

DAS with discrete tokens is cleaner than with continuous activations:
- Each token position carries a discrete identity → interchange interventions are exact (swap token A with token B)
- No distributional mismatch: swapped tokens are in-distribution by construction
- gc(k) can be measured in token-space (exact attribution) before moving to residual stream

### Proposed VQ scheme

1. **Synthetic dataset**: 5 phoneme categories × 3 speakers × 10 variations = 150 distinct "speech clips" as 32-dimensional spectral vectors (no real audio needed).
2. **Codebook**: k=64 codes, dim=32. Trained with straight-through estimator (STE) or product quantization.
3. **Token sequence**: Each "utterance" = 8 VQ tokens in sequence. Task: predict final token given 7 context tokens.
4. **Ground truth causal graph**: Define explicitly — e.g., token 3 causally determines token 7 via phoneme harmony rule. This is the IIA target.

### Why VQ over raw continuous activations?
- Swap operations (interchange interventions) are meaningful: swapping code 12 with code 47 has defined semantics.
- Codebook = explicit monosemanticity test: does each code encode *one* thing?
- Natural bridge to EnCodec/DAC analysis (Gap #9): VQ tokens in real codec models.

---

## Architecture

```
MicroGPT-Audio (target: ~200 lines Python)

Input: sequence of VQ tokens (int, vocab=64)
Embedding: 64-dim
Transformer: 4 layers × 4 heads × 64-dim (no MLP, just attention)
Output: logits over 64 tokens (next-token prediction)

Parameter count: ~200K
Forward pass: <1ms on CPU (MacBook)
Training: 150 synthetic sequences × 1000 epochs = ~30s
```

**Why no MLP layers?**
For DAS validation, pure attention is mechanistically cleaner — the causal graph is easier to specify (attention heads = edges in graph). Adding MLPs introduces superposition and nonlinearity that complicates ground-truth construction.

**Why 4 layers?**
Enough to have a "middle layer" where grounding can peak (Lin §4.1 prediction: intermediate layers capture cross-modal interaction). 4 layers → layer 2 = predicted Listen Layer. With 2 layers, there's no "middle" to find.

---

## gc(k) Integration Rationale

### Ground truth construction
1. Define a minimal pair: utterance A = [1, 2, 3, 12, 5, 6, 7] and utterance B = [1, 2, 3, 47, 5, 6, 7] (differ at position 4).
2. The causal rule says: token 4 determines token 8. So A → prediction X, B → prediction Y.
3. **gc(k) at layer L** = fraction of variance in final prediction explained by swapping the layer-L representation of token 4 from A to B.
4. **Ground truth**: gc(k) should peak at layer where token 4 is processed for the harmonic rule = layer 2 (by construction).

### Validation procedure
1. Train MicroGPT-Audio to >90% accuracy.
2. Run DAS sweep: for each layer L and each "causal position" p, measure IIA of interchange intervention.
3. **Expected result**: IIA peaks at (layer=2, position=4) because that's where the causal rule is implemented.
4. If DAS *finds* this peak → method validated → transfer to Whisper.
5. If DAS *misses* this peak → diagnose: is it a DAS hyperparameter issue, an alignment map issue, or a signal-to-noise issue?

### Why this beats doing DAS directly on Whisper
| Property | MicroGPT-Audio | Whisper-small |
|----------|---------------|---------------|
| Ground truth causal graph | ✅ Known by construction | ❌ Unknown |
| Iteration time | ~1s per sweep | ~3min per sweep |
| Distributional mismatch on swap | ❌ None (in-vocab) | ⚠️ Possible |
| Scale (params) | ~200K | ~244M |
| DAS diagnosis if it fails | Easy (ablate components) | Hard (too many confounds) |

---

## MacBook Training Time Estimate

| Component | Time |
|-----------|------|
| Dataset generation (synthetic) | <1s |
| Codebook training (STE, 64 codes) | ~5s |
| Transformer training (1000 epochs, 150 samples) | ~30s |
| DAS sweep (4 layers × 8 positions × 500 pairs) | ~20s |
| **Total first run** | **~60s** |

Subsequent runs (after initial training): ~25s (skip dataset + codebook gen).

**MacBook Air M2 (8GB): fully feasible.** No GPU needed. No external dependencies beyond NumPy + PyTorch CPU.

---

## 3 Key Advantages Over Full Whisper

### 1. Falsifiability by design
With Whisper, a positive DAS result could be:
- (a) Real mechanistic discovery
- (b) DAS overfitting to low-dim subspace
- (c) Lucky correlation in pre-trained features

With MicroGPT-Audio: if DAS correctly localizes the planted causal rule, we have strong evidence for (a). Failed localization diagnoses (b) or (c).

### 2. Controllable "grounding collapse"
We can deliberately create a "text-prior-dominant" version of MicroGPT-Audio by training with 80% context-based prediction (guessing from token 1-3 alone) and 20% causal grounding (using token 4). This mimics modality collapse (Zhao et al. 2602.23136). Then measure: does gc(k) correctly diagnose this as "low grounding"? → validates gc(k) as a *detector* of modality collapse, not just a passive measurement tool.

### 3. Fast iteration on gc_eval.py
gc_eval.py (cycle #225) needs unit tests. MicroGPT-Audio provides ground truth for `test_gc_eval.py`:
- `assert gc_layer(toy_model, layer=2, position=4) > 0.8` (should find the planted causal rule)
- `assert gc_layer(toy_model, layer=0, position=4) < 0.2` (early layer shouldn't show it yet)
- `assert gc_layer(collapsed_model, layer=2, position=4) < 0.3` (collapsed model should score low)

These are *quantitative correctness tests* for the eval harness — something impossible to write for Whisper where ground truth is unknown.

---

## Open Questions

1. **Codebook collapse**: Standard VQ training often collapses to using <20% of codebook codes. Does this matter for DAS? (Probably not — we only need the codes actually used in the synthetic task.) *Resolution: run k-means init + EMA updates; monitor code usage histogram.*

2. **STE vs. Gumbel-softmax**: For the tiny model, does the choice of VQ gradient estimator affect whether DAS finds the correct layer? *Resolution: test both, report which gives cleaner IIA curves.*

3. **Generalization**: Once DAS works on MicroGPT-Audio, which part of the method requires re-validation on Whisper? *Answer: the linear alignment map assumption (Gap #25, Sutter et al.). The toy has linear causal rules by construction; Whisper might have nonlinear ones.*

---

## Connection to Papers

- **Paper A §3 (Methods)**: "We first validate the gc(k) metric on a controlled toy model (MicroGPT-Audio) where the ground truth causal graph is known, then transfer to Whisper-small."
- **Paper B (AudioSAEBench)**: MicroGPT-Audio VQ codebook = natural testbed for monosemanticity evaluation (Category 1, M3 steering).
- **gc_eval.py unit tests**: MicroGPT-Audio provides ground truth for `test_gc_eval.py` assertion suite.
- **Gap #25 (Non-linear representations)**: MicroGPT-Audio = linear DAS baseline; nonlinear extension on Whisper = explicit follow-up.

---

## Next Steps (not for this cycle)

1. Build `skills/autodidact/scripts/microgpt_audio_toy.py` (Tier 1, need Leo green light on CPU experiment)
2. Write `skills/autodidact/scripts/test_microgpt_das.py` (unit tests for gc_eval.py)
3. Run sweep: confirm IIA peaks at layer 2, position 4 (MacBook, ~60s)
4. Document result in Paper A §3 methods box as "methodology validation"
