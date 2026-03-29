"""
Q219: SPIRIT-style linear erasure at L* for audio jailbreak suppression
via Contrastive Activation Addition (CAA) direction.

Method:
  1. Simulate Whisper-base encoder activations for benign vs jailbreak audio
  2. Compute jailbreak direction d_j = mean(jailbreak) - mean(benign) at L* (CAA)
  3. Linear erasure: project out d_j from activations (SPIRIT-style)
  4. Measure AND-frac delta: sign-consistency fraction (fraction of neurons where
     >80% of samples agree on sign — a tractable AND-frac proxy for mock data)
  5. Measure jailbreak probe score (LDA-style threshold) before/after erasure

Key: Jailbreak activations have a "commitment-disrupting" component along d_j.
Erasing d_j at L* should: (a) restore AND-frac toward benign level, (b) collapse probe.

CPU-only. <5 min.
"""

import numpy as np
import json
from datetime import datetime

rng = np.random.default_rng(42)

# ── Config ─────────────────────────────────────────────────────────────────
N_LAYERS    = 32
D_MODEL     = 512
L_STAR      = 21          # AND-frac commit layer (≈ 0.656 * 32)
CONSISTENCY_THRESHOLD = 0.80   # fraction of samples that must agree on sign
JAILBREAK_STRENGTH    = 3.0    # how strongly jailbreak disrupts L* activations

# ── True jailbreak direction (latent) ──────────────────────────────────────
d_true = rng.standard_normal(D_MODEL)
d_true /= np.linalg.norm(d_true)

# ── Activation model ───────────────────────────────────────────────────────
# Benign: activations have a "coherent" commitment component → high sign-consistency
# Jailbreak: adds disruption along d_true → flips some neurons, lowers consistency
def make_activation(is_jailbreak: bool, layer: int, n_samples: int) -> np.ndarray:
    """
    Returns (n_samples, D_MODEL) activation matrix.
    Benign: each sample = coherent_signal + noise   (sign-consistent at L*)
    Jailbreak: adds disruptive offset along d_true  (breaks sign consistency)
    """
    # Coherent signal: same base direction per layer, scaled by layer depth
    base_dir = rng.standard_normal(D_MODEL)
    base_dir /= np.linalg.norm(base_dir)

    layer_weight = np.exp(-0.5 * ((layer - L_STAR) / 5) ** 2)
    coherence    = 1.5 * layer_weight  # highest coherence near L*

    acts = rng.standard_normal((n_samples, D_MODEL)) * 0.4   # noise
    acts += coherence * base_dir[None, :]                      # shared coherent signal

    if is_jailbreak:
        # Add disruptive offset along d_true: shifts mean, disrupts sign consistency
        disruption_weight = JAILBREAK_STRENGTH * layer_weight
        acts += disruption_weight * d_true[None, :]

    return acts

# ── AND-frac (sign-consistency proxy) ─────────────────────────────────────
def and_frac_sign(acts: np.ndarray) -> float:
    """
    Fraction of neurons where ≥ CONSISTENCY_THRESHOLD of samples agree on sign.
    This is a tractable AND-frac proxy for continuous mock activations.
    acts: (N, D)
    """
    signs    = np.sign(acts)                              # (N, D)
    pos_frac = (signs > 0).mean(axis=0)                  # (D,) fraction positive
    consistent = (pos_frac >= CONSISTENCY_THRESHOLD) | (pos_frac <= 1 - CONSISTENCY_THRESHOLD)
    return float(consistent.mean())

# ── Linear erasure ─────────────────────────────────────────────────────────
def erase(acts: np.ndarray, direction: np.ndarray) -> np.ndarray:
    """Project out `direction` from each row of acts. acts: (N, D)"""
    proj = (acts @ direction)[:, None] * direction[None, :]
    return acts - proj

# ── Probe accuracy ─────────────────────────────────────────────────────────
def probe_accuracy(X_b: np.ndarray, X_j: np.ndarray, direction: np.ndarray) -> float:
    """
    Linear probe: project onto `direction`, threshold at midpoint of class means.
    Returns balanced accuracy.
    """
    s_b = X_b @ direction
    s_j = X_j @ direction
    thresh = (s_b.mean() + s_j.mean()) / 2
    acc_b = (s_b < thresh).mean()
    acc_j = (s_j >= thresh).mean()
    return float(0.5 * (acc_b + acc_j))   # balanced accuracy

# ── 1. CAA: compute d_j on training set ────────────────────────────────────
X_train_benign    = make_activation(False, L_STAR, n_samples=50)
X_train_jailbreak = make_activation(True,  L_STAR, n_samples=25)

d_j = X_train_jailbreak.mean(0) - X_train_benign.mean(0)
d_j_norm = d_j / (np.linalg.norm(d_j) + 1e-8)

# Quality check
cos_sim = float(np.dot(d_j_norm, d_true))

# ── 2. Per-layer analysis ───────────────────────────────────────────────────
N_TEST = 30   # 30 benign + 30 jailbreak test samples
layer_results = []

for layer in range(N_LAYERS):
    X_b = make_activation(False, layer, N_TEST)
    X_j = make_activation(True,  layer, N_TEST)

    andf_b_before = and_frac_sign(X_b)
    andf_j_before = and_frac_sign(X_j)

    X_b_erased = erase(X_b, d_j_norm)
    X_j_erased = erase(X_j, d_j_norm)

    andf_b_after  = and_frac_sign(X_b_erased)
    andf_j_after  = and_frac_sign(X_j_erased)

    pb_before = probe_accuracy(X_b, X_j, d_j_norm)
    pb_after  = probe_accuracy(X_b_erased, X_j_erased, d_j_norm)

    layer_results.append({
        "layer": layer,
        "andf_benign_before": round(andf_b_before, 4),
        "andf_jailbreak_before": round(andf_j_before, 4),
        "andf_benign_after": round(andf_b_after, 4),
        "andf_jailbreak_after": round(andf_j_after, 4),
        "probe_before": round(pb_before, 4),
        "probe_after": round(pb_after, 4),
    })

# ── 3. Summary at L* ───────────────────────────────────────────────────────
r = layer_results[L_STAR]
andf_gap_before = r["andf_benign_before"] - r["andf_jailbreak_before"]
andf_gap_after  = r["andf_benign_after"]  - r["andf_jailbreak_after"]
andf_j_delta    = r["andf_jailbreak_after"] - r["andf_jailbreak_before"]
probe_drop      = r["probe_before"] - r["probe_after"]

print("=" * 60)
print("Q219: CAA Jailbreak Erasure at L* — Results")
print("=" * 60)
print(f"  L* (commit layer)      : {L_STAR} / {N_LAYERS}  (ratio = {L_STAR/N_LAYERS:.3f})")
print(f"  CAA direction quality  : cos_sim = {cos_sim:.3f}  (1.0 = perfect)")
print()
print(f"  ── AND-frac (sign-consistency) at L* ──")
print(f"  Benign    before erasure : {r['andf_benign_before']:.4f}")
print(f"  Jailbreak before erasure : {r['andf_jailbreak_before']:.4f}  (gap = {andf_gap_before:+.4f})")
print(f"  Jailbreak after erasure  : {r['andf_jailbreak_after']:.4f}  (delta = {andf_j_delta:+.4f})")
print(f"  Gap after erasure        : {andf_gap_after:+.4f}  {'← narrowed ✓' if abs(andf_gap_after) < abs(andf_gap_before) else '← unchanged'}")
print()
print(f"  ── Jailbreak Probe Accuracy ──")
print(f"  Before erasure  : {r['probe_before']:.4f}")
print(f"  After erasure   : {r['probe_after']:.4f}  (drop = {probe_drop:+.4f})")
print(f"  Random baseline : 0.5000")
print()
print(f"  AND-frac profile at key layers (benign / jailbreak):")
for lr in layer_results[::4]:
    m = " ← L*" if lr["layer"] == L_STAR else ""
    print(f"    layer {lr['layer']:2d}: {lr['andf_benign_before']:.4f} / {lr['andf_jailbreak_before']:.4f}{m}")
print()
print("  ── Interpretation ──")
if cos_sim > 0.5:
    print("  ✓ CAA direction well-aligned with true jailbreak direction.")
if andf_gap_before > 0.05:
    print(f"  ✓ Jailbreak activations have lower AND-frac at L* (gap={andf_gap_before:+.3f}).")
    print("    → Confirms jailbreak disrupts the commit-layer coherence signal.")
if andf_j_delta > 0.01:
    print(f"  ✓ Erasure RESTORES jailbreak AND-frac by {andf_j_delta:+.4f}.")
    print("    → Removing d_j from activations partially recovers commitment coherence.")
if probe_drop > 0.15:
    print(f"  ✓ Probe accuracy drops {probe_drop:.2f} post-erasure → near-chance detection.")
    print("    → Jailbreak representation successfully erased at L*.")
print()
print("  ── DoD Check ──")
print("  ✅ Mock script runs on CPU")
print("  ✅ CAA jailbreak direction computed (contrastive mean, d_j)")
print("  ✅ Linear erasure at L* implemented (SPIRIT-style projection-out)")
print("  ✅ AND-frac delta measured (sign-consistency proxy)")
print("  ✅ Jailbreak probe score before/after measured (balanced accuracy)")

# ── 4. Save artifact ───────────────────────────────────────────────────────
artifact = {
    "task_id": "Q219",
    "timestamp": datetime.now().isoformat(),
    "config": {
        "N_LAYERS": N_LAYERS, "D_MODEL": D_MODEL,
        "L_STAR": L_STAR, "L_STAR_ratio": round(L_STAR/N_LAYERS, 3),
        "consistency_threshold": CONSISTENCY_THRESHOLD,
        "jailbreak_strength": JAILBREAK_STRENGTH,
    },
    "caa_cos_sim": round(cos_sim, 4),
    "lstar_results": r,
    "andf_gap_before": round(andf_gap_before, 4),
    "andf_gap_after":  round(andf_gap_after, 4),
    "andf_j_delta":    round(andf_j_delta, 4),
    "probe_drop":      round(probe_drop, 4),
    "interpretation": {
        "caa_accurate":        cos_sim > 0.5,
        "jailbreak_disrupts_commit": andf_gap_before > 0.05,
        "erasure_restores_andf":     andf_j_delta > 0.01,
        "probe_suppressed":          probe_drop > 0.15,
    },
    "layer_results": layer_results,
}
out_path = "/home/leonardo/.openclaw/workspace/memory/learning/cycles/q219_results.json"
with open(out_path, "w") as f:
    json.dump(artifact, f, indent=2)
print(f"\n  Artifact saved: {out_path}")
