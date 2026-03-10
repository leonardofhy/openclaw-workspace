# Q042: Critical-Layer Patching Checklist for LALMs
> Cycle: c-20260311-0131 | Phase: explore-fallback | Action: build (Tier 0 write)
> Track: T3 | Task: Q042
> Created: 2026-03-11 01:31 (Asia/Taipei)

## Purpose

A **reproducible checklist** for practitioners running causal patching sweeps on Large Audio-Language Models (LALMs).
Covers setup, gate conditions (AND/OR), execution stages, denoising correction, attribution patching (AtP),
and top-k aggregation — with concrete examples from Paper A / Whisper / Qwen2-Audio.

The checklist is designed to answer: *"Where in this LALM does audio grounding occur?"*
while avoiding the three most common failure modes: vanilla patching fragility, polysemanticity noise, and stimulus confounds.

---

## Phase 0 — Prerequisites (Gate: ALL must pass before patching)

### 0A. Model + Infrastructure
- [ ] Model weights accessible (local or API); float32 or bfloat16 (not quantized for patching)
- [ ] Hook library available: `pyvene` (DAS/IIT), `baukit`, or `nnsight` for NNsight-compatible models
- [ ] GPU memory: ≥ 4GB for Whisper-small; ≥ 24GB for Qwen2-Audio-7B (or use AtP for budget sweeps)
- [ ] CPU fallback: AtP + variance pre-screen can run on MacBook (no GPU needed for Tier 0/1 experiments)

### 0B. Stimuli Quality (AND gate — all conditions required)
- [ ] **Minimal pair guarantee**: source (clean) and base (corrupt) differ on exactly ONE variable of interest
  - Example: voicing contrast [b]/[p] holds manner + place constant (Choi et al. 2602.18899)
  - Example: RVQ-layer-1 swap keeps speaker voice (RVQ L2+) unchanged (SpeechTokenizer, Sadok et al.)
- [ ] **Behavioral baseline confirmed**: model shows different outputs on clean vs. corrupt *before* patching
  - If model already gives same output: patching will be uninformative (floor effect)
  - Minimum: ≥ 70% correct on clean; ≤ 40% on corrupt (delta ≥ 30 pp)
- [ ] **N ≥ 20 pairs per condition** (for statistical reliability of IIA at each layer)
- [ ] **Confound audit**: check that corrupt audio doesn't differ in length, RMS volume, or sampling rate
  - Use `assert audio_len_clean == audio_len_corrupt` and RMS normalization

### 0C. Evaluation Setup
- [ ] Target behavior $y^*$ is **binary or low-cardinality** (IIA requires clean source → expected output mapping)
  - Good: "audio-grounded response" vs. "text-prior response" on conflict stimuli
  - Harder: free-form transcript (use token-level accuracy instead of IIA; less principled)
- [ ] **Baseline IIA computed**: IIA without patching (should be at chance level ≈ 50% for binary)
- [ ] **Upper bound IIA computed**: patch ALL residual stream positions (should approach 100% if stimuli are clean)

---

## Phase 1 — Layer Pre-Screen (skip if ≤ 24 layers)

### 1A. Variance-Based Pre-Screen (fast, CPU-feasible)
```python
# For each layer L:
var_score[L] = mean( Var_batch( h_L(x_clean) - h_L(x_corrupt) ) )
# Keep top-k=8 layers by var_score for full DAS
```
- **Rationale**: Layers where activations differ most between clean/corrupt are prime candidates
- **Caveat**: High variance ≠ high causal contribution (SCD) — use as filter, not conclusion
- **Implementation**: `skills/autodidact/scripts/gc_eval.py` (mock harness, extend for real activations)

### 1B. Attribution Patching (AtP) — gradient-based causal approximation
```
AtP(L) ≈ ⟨ ∂L_IIT/∂h_L , (h_L_clean − h_L_corrupt) ⟩
```
- Linear approximation to causal patching; order-of-magnitude faster than full DAS sweep
- **Gate**: Run AtP across ALL layers first; shortlist top-k by |AtP(L)|
- **Nanda caution**: AtP can be negatively correlated with true patching effect at noisy layers — verify top-3 manually
- **Implementation**: Use `baukit` or `pyvene`; 1 backward pass per layer pair

---

## Phase 2 — Distributed Alignment Search (DAS) — Core Patching

### 2A. DAS Setup
```python
# pyvene RotatedSpaceIntervention
from pyvene import IntervenableModel, RotatedSpaceIntervention

config = IntervenableConfig(
    representations=[{
        "layer": L,
        "component": "block_output",
        "low_rank_dimension": d_intervention  # start with 32 or 64
    }],
    intervention_types=[RotatedSpaceIntervention]
)
model_intervenable = IntervenableModel(config, base_model)
```
- **Low-rank dimension**: Start with d=32; increase to 128 if gc(L) < 0.6 at pre-screened layers
- **Optimizer**: AdamW, lr=1e-3, warmup 100 steps, cosine decay
- **Epochs**: 5–10 per layer; early-stop if IIA plateaus (delta < 0.005 over 2 epochs)
- **Batch size**: 8 minimal pairs (limited by GPU memory and N)

### 2B. Denoising Correction (CRITICAL — addresses Heimersheim & Nanda fragility)
**Problem**: Vanilla patching corrupts ALL features at layer L, including noise. IIA inflated by denoising effect.
**Solution**: Activate denoising IIT (disentangle causal signal from incidental variance):

```
Denoising IIA(L) = IIA with clean→corrupt patch at L
Noising IIA(L)   = IIA with corrupt→clean patch at L
gc(L)            = max( Denoising IIA(L), Noising IIA(L) )
```

- **AND gate**: Only claim L* if BOTH denoising and noising agree on peak location (within ±2 layers)
- **Flag**: If denoising and noising disagree by > 5 layers → possible stimulus confound, revisit Phase 0B

### 2C. Subspace Linearity Check (Sutter et al. 2025 — prevents vacuous IIA)
- [ ] Run DAS with `d_intervention = 1` (rank-1 subspace); confirm gc(L) < 0.9 (not vacuous)
- [ ] Run DAS with **random orthogonal R** (no training); confirm gc(L) ≈ chance (model-valid check)
- [ ] If random R gives gc(L) > 0.7: subspace is too large; reduce `low_rank_dimension` or double N

---

## Phase 3 — Top-k Aggregation & gc(k) Profile

### 3A. Build gc(k) Curve
```python
gc_k = {}
for k in [1, 2, 4, 8]:  # top-k layers patched simultaneously
    patched_layers = top_k_layers_by_gc_single(k)
    gc_k[k] = evaluate_iia(patch_all=patched_layers)
# Expected: gc(1) < gc(2) < gc(4) up to saturation
```
- **Interpretation**: If gc(4) ≈ gc(1) → single-layer bottleneck (sharp Listen Layer)
- **Interpretation**: If gc(4) >> gc(1) → distributed processing across layers (softer Listen Layer)
- **Paper A target**: Sharp peak → single-layer L* → supports "Listen Layer" claim

### 3B. 3-Tier Diagnosis (from taxonomy in gap31-tier-taxonomy-predictions.md)
After computing gc(k) profile, apply the decision tree:

| gc(k) shape | Diagnosis | Next action |
|-------------|-----------|-------------|
| Flat ≈ 0 all layers | **Tier 1 (Codec)** — signal lost at RVQ | Inspect RVQ layer outputs; compare with DashengTokenizer |
| Peak in encoder, drops at connector | **Tier 2 (Connector)** — bottleneck collapse | Run GMI (Modality Collapse) test on connector states |
| Rise-then-fall peaking at ≈ 50% depth | **Tier 3 (LLM)** — text prior takes over | This is the L* = Listen Layer; proceed to Paper A §4 |
| Multiple peaks | Mixed failure | Decompose by stimulus type (phonological vs. conflict stimuli) |

---

## Phase 4 — Reporting Standards

### 4A. Per-Layer Table (minimum required in paper)
| Layer | gc_noising | gc_denoising | gc_final | AtP_score | Var_score | Notes |
|-------|-----------|--------------|----------|-----------|-----------|-------|
| ...   | ...       | ...          | ...      | ...       | ...       |       |

### 4B. Plot Requirements
- [ ] gc(L) curve with ±1 std error bars across stimulus pairs
- [ ] Noising and denoising curves overlaid (denoising correction visible)
- [ ] Vertical line at connector boundary (encoder↔LLM transition)
- [ ] Horizontal baseline: chance IIA (≈ 0.5 for binary)

### 4C. Failure Reporting Checklist
- [ ] Report N (pairs) and fraction meeting behavioral prerequisite (0B)
- [ ] Report d_intervention used and rank-1 sanity check result (2C)
- [ ] Report whether noising/denoising agreement holds (2B)
- [ ] Report top-k aggregation curve (3A)

---

## Examples from Paper A (Whisper-small, CPU Experiment E1)

**Setup**: 400 phonological minimal pair stimuli (Choi et al.) × 4 languages (EN/ZH/DE/JA)
**Pre-screen**: Variance scores → top-8 layers shortlisted (layers 2, 4, 5, 6, 7, 8, 9, 10 of 32)
**AtP**: Top-3 layers by |AtP| = {5, 6, 7} — connector boundary in Whisper ≈ layer 6
**DAS**: Run on top-8 layers, d_intervention=32, 5 epochs each
**gc(k) expected peak**: ≈ layer 5–6 (connector entry region, ≈ 50% encoder depth)
**Denoising check**: Both noising and denoising curves expected to agree at layer 5–6

**CPU time estimate**: ~2–3 hours for full sweep (400 pairs × 8 layers × 5 epochs, CPU-only)

---

## Common Failure Modes & Fixes

| Failure | Symptom | Fix |
|---------|---------|-----|
| Vanilla patching fragility (Heimersheim & Nanda) | gc(L) inflated; noising ≠ denoising | Apply denoising correction (Phase 2B) |
| Vacuous IIA (Sutter et al.) | gc(L) ≈ 1.0 with random R | Reduce d_intervention; increase N |
| Stimulus confound | gc(k) flat-high everywhere | Tighten minimal pair audit (Phase 0B) |
| Polysemanticity noise | gc(L) noisy, inconsistent across runs | Use AtP pre-screen to focus on top-k only |
| Floor effect | gc(L) ≈ 0.5 everywhere | Re-check behavioral baseline (need delta ≥ 30pp) |
| Wrong component type | gc(L) very low despite expected signal | Try "residual_stream" vs. "block_output" vs. "mlp_output" |

---

## Status: COMPLETE ✅
**Definition of done**: Reproducible checklist with AND/OR gates, denoising, AtP, top-k aggregate, and examples. ✓
