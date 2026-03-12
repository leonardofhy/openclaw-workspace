# T3 CPU Experiment Spec: gc(k) Listen-vs-Guess Validation
**Track**: T3 — Listen vs Guess (Paper A)
**Status**: READY FOR LEO REVIEW
**Tier**: 1 (CPU-only, ~2 min runtime)
**Date**: 2026-03-06 (updated: +Asiaee variance pre-screen)

---

## Research Question

> At which layers of Whisper does the model transition from relying on audio evidence to language prior? Can gc(k) reliably distinguish "listen" regimes (audio-driven) from "guess" regimes (LM-prior-driven)?

---

## Hypothesis

**H1 (Listen)**: For clean, unambiguous audio, gc(k) should peak in mid-to-late encoder layers and remain elevated in early decoder layers.

**H2 (Guess)**: For heavily masked/noisy audio, gc(k) should drop sharply after encoder layer 3-4, indicating the decoder is relying on language prior rather than audio features.

**H3 (Connector)**: The cross-attention connector layers (encoder→decoder handoff) should show a sharp gc(k) gradient — this is the "listen gate."

---

## Method

### Step 1: Synthetic Stimuli (already built — `synthetic_stimuli.py`)
Generate 3 stimulus pairs:
- **Clean vs. Gaussian noise** — baseline listen/guess split
- **Clean vs. Partial mask (50%)** — mid-confidence regime
- **Clean vs. Full silence** — extreme guess regime

### Step 1.5: Asiaee Variance Pre-Screen (NEW — 3-5x speedup)
**Before running DAS on all layers**, filter candidate layers using activation variance as a first-order proxy.
Asiaee (2602.24266, NeurIPS 2025) shows: **activation variance across clean vs. noisy conditions correlates with causal contribution** — low-variance layers rarely produce high gc(k). Use this to prune the layer sweep.

```python
def asiaee_prescreen(A_clean, A_noisy, variance_threshold=0.05):
    """
    Returns list of layer indices worth running DAS on.
    
    A_clean, A_noisy: dict {layer_idx: activation_tensor}  (shape: [seq, d_model])
    variance_threshold: layers with normalized variance below this are skipped
    
    Algorithm (Asiaee 2026, efficient causal abstraction via structured pruning):
      1. For each layer k:
            delta[k] = ||A_clean[k] - A_noisy[k]||_F  (Frobenius norm of activation diff)
      2. Normalize: delta_norm[k] = delta[k] / sum(delta.values())
      3. Layer k passes if delta_norm[k] >= variance_threshold
      4. Return sorted list of passing layers (highest delta first)
    """
    deltas = {}
    for k in A_clean:
        diff = A_clean[k] - A_noisy[k]
        deltas[k] = float(np.linalg.norm(diff, 'fro'))
    
    total = sum(deltas.values()) + 1e-9
    delta_norm = {k: v / total for k, v in deltas.items()}
    
    passing = [(k, delta_norm[k]) for k in delta_norm
               if delta_norm[k] >= variance_threshold]
    passing.sort(key=lambda x: -x[1])
    
    return [k for k, _ in passing]

# Usage in experiment pipeline:
A_clean, A_noisy = extract_all_activations(model, clean_wav, noisy_wav)
candidate_layers = asiaee_prescreen(A_clean, A_noisy, variance_threshold=0.05)
# → typically filters 4-6 of 12 layers, reduces DAS compute by ~40-50%
```

**Important caveat (Risk A6)**: Rare phoneme features with HIGH causal weight but LOW variance may be missed.
Mitigation: if an expected phoneme class shows no gc(k) signal after filtering, fall back to full DAS on that class.
Report ablation delta per phoneme class separately in paper (not just aggregate).

---

### Step 2: gc(k) Computation (already built — `gc_eval.py`)
For each stimulus pair, run DAS only on `candidate_layers` from Step 1.5:
```
1. Run Whisper-tiny forward pass on clean → record activations A_clean[k] for each layer k
2. Run Whisper-tiny forward pass on noisy → record activations A_noisy[k]
3. Run asiaee_prescreen(A_clean, A_noisy) → candidate_layers
4. For each layer k in candidate_layers:
   - Patch A_noisy at layer k with A_clean[k]
   - Measure ΔP(correct token)
5. gc(k) = ΔP(k) / max_k(ΔP(k))   [normalized; gc(k)=0 for skipped layers]
```

### Step 3: Analysis
- Plot gc(k) curves (encoder layers 0-5, decoder layers 0-5) for all 3 conditions
- Identify "listen threshold" layer: first k where gc(k) > 0.5 in listen condition
- Identify "guess transition" layer: k where gc(k) drops below 0.2 in guess conditions
- Report: mean, std, confidence interval across 5 random seeds

---

## Command to Run

```bash
cd ~/.openclaw/workspace/skills/autodidact/scripts

# Mock mode (Tier 0 — no model, instant):
python3 gc_eval.py --mock --plot

# Tier 1 (CPU, Whisper-tiny, ~2 min, no GPU needed):
python3 gc_eval.py \
    --model-name openai/whisper-tiny \
    --audio-clean <path/to/clean.wav> \
    --audio-noisy <path/to/noisy.wav> \
    --layer-range 0 11
```

**Mock mode can run immediately.** Tier 1 requires a ~50 MB model download + one .wav file from Leo.

---

## Expected Outputs

| Condition | Expected gc(k) pattern |
|-----------|----------------------|
| Clean audio | Peak at enc layers 3-5, stays >0.6 in decoder |
| 50% mask | Peak at enc 2-4, drops to ~0.3 by dec layer 3 |
| Full silence | Drops to <0.1 after enc layer 2 |

Key artifact: `gc_curves_comparison.png` + `gc_summary.json`

---

## Decision Gates (for Leo)

| Gate | Condition | Action |
|------|-----------|--------|
| ✅ Mock validates | gc(k) curves show expected listen/guess split | Run Tier 1 |
| ✅ Tier 1 validates on clean/noisy .wav | Pattern holds on real model | Approve GPU Tier 2 |
| ❌ gc(k) flat across conditions | Patching method broken | Debug activation patching |
| ❌ gc(k) identical in listen/guess | gc metric not discriminative | Revise metric definition |

---

## What Leo Needs to Provide

1. One clean speech .wav (~10 sec, any sentence)
2. Confirm OK to download `openai/whisper-tiny` (~50 MB) via Hugging Face

Everything else is ready to run.

---

## Dependencies

- `transformers` (whisper support)
- `numpy`, `matplotlib`
- `synthetic_stimuli.py`, `gc_eval.py`, `test_gc_eval.py` — all exist in scripts/

---

## Phase Exit Contribution

Completing this spec + getting Leo to confirm Step 1 (mock run) satisfies:
- `experiment_spec_ready_T3` ✅
- After Leo provides .wav: `leo_approved_gpu_or_cpu_experiment` ✅
- Then: **converge → execute** transition is unlocked for T3
