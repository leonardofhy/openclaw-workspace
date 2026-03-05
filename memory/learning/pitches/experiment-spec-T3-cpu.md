# T3 CPU Experiment Spec: gc(k) Listen-vs-Guess Validation
**Track**: T3 — Listen vs Guess (Paper A)
**Status**: READY FOR LEO REVIEW
**Tier**: 1 (CPU-only, ~2 min runtime)
**Date**: 2026-03-03

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

### Step 2: gc(k) Computation (already built — `gc_eval.py`)
For each stimulus pair:
```
1. Run Whisper-tiny forward pass on clean → record activations A_clean[k] for each layer k
2. Run Whisper-tiny forward pass on noisy → record activations A_noisy[k]
3. For each layer k:
   - Patch A_noisy at layer k with A_clean[k]
   - Measure ΔP(correct token)
4. gc(k) = ΔP(k) / max_k(ΔP(k))   [normalized]
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
