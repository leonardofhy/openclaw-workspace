"""
q208_spirit_erasing_jailbreak.py — Q208
SPIRIT-Style Linear Erasing at L* for Audio Jailbreak Defense

Hypothesis: The "jailbreak direction" in activation space at L* (Listen Layer)
can be identified and linearly erased without degrading normal ASR commitment
(AND-frac). This adapts SPIRIT (Suppressing Representation-mediated Information
leaking via Erasing Targeted directions) to the audio domain.

Design (JALMBench-v0 mock):
  - 200 utterances: 100 benign (normal ASR) + 100 jailbreak (adversarial commands)
  - Jailbreak direction d_jb: mean(jailbreak activations at L*) - mean(benign activations at L*)
    (PCA-normalized to unit sphere)
  - SPIRIT erasing: h_erased = h - (h · d_jb) * d_jb  (projection subtraction)
  - Metrics:
      (a) AND-frac at L* before/after erasing (benign utterances — should stay high)
      (b) Jailbreak suppression rate: fraction of jailbreak inputs where projection onto
          d_jb falls below threshold θ (i.e., erasing removed the jailbreak signal)
      (c) Cosine similarity of erased activations to benign mean (closer = better defense)
  - Ablations:
      (a) Vary erasing strength α ∈ {0.5, 1.0, 1.5, 2.0} (partial vs full vs over-erase)
      (b) Erase at L* vs. L*-1 vs. L*+1 (layer sensitivity)
  - Target: AND-frac restoration ≥ 0.8 of baseline, suppression_rate ≥ 0.85
  - CPU runtime: <5 min (pure numpy)

Connections:
  - Q205: censored behavior x AND-frac (refusal via commit suppression)
  - Q206: power steering for hallucination suppression (additive direction)
  - Q207: streaming monitor (AND-frac as diagnostic)
  - SPIRIT (Bricken et al. 2023): linear concept erasure in LLM residual stream
  - T5 (Track 5): audio jailbreak detection prototype for MATS proposal

Author: autodidact | 2026-03-29
"""

import numpy as np
from typing import Dict, List, Tuple
import json

# ─── Reproducibility ─────────────────────────────────────────────────────────
np.random.seed(208)

# ─── Constants ───────────────────────────────────────────────────────────────
N_BENIGN      = 100
N_JAILBREAK   = 100
N_LAYERS      = 12          # Whisper-base encoder depth
L_STAR        = 8           # Listen Layer (empirical from prior work)
D_MODEL       = 512         # Whisper-base hidden dim
JAILBREAK_SNR = 2.5         # How separable jailbreaks are from benign (signal/noise)
THRESHOLD_AND = 0.35        # AND-frac threshold for "committed" token
THRESHOLD_JB  = 0.15        # Projection threshold below which jailbreak is suppressed

# ─── Simulate Activations ────────────────────────────────────────────────────

def simulate_activations(n_samples: int, is_jailbreak: bool, layer: int) -> np.ndarray:
    """
    Generate mock activations at a given layer.
    
    Benign: Normal gaussian in activation space.
    Jailbreak: Shifted along a fixed adversarial direction with extra SNR.
    L* has maximum separability (JAILBREAK_SNR × layer_factor peaks at L_STAR).
    """
    # Layer-dependent separability (peaks at L_STAR)
    layer_factor = np.exp(-0.5 * ((layer - L_STAR) / 2.0) ** 2)
    
    # Base activations (gaussian)
    acts = np.random.randn(n_samples, D_MODEL) * 0.5
    
    if is_jailbreak:
        # Adversarial direction (fixed, normalized)
        jb_direction = np.random.randn(D_MODEL)
        jb_direction /= np.linalg.norm(jb_direction)
        # Shift along jailbreak direction
        shift = JAILBREAK_SNR * layer_factor
        acts += shift * jb_direction[np.newaxis, :]
        # Save true direction in first call for reproducibility
        return acts, jb_direction * shift
    
    return acts, None


def compute_and_frac(acts: np.ndarray, threshold: float = THRESHOLD_AND) -> float:
    """
    AND-frac: fraction of tokens where ALL top-k features are active (>threshold).
    Mock: fraction of samples where mean(abs(acts)) > threshold * scale.
    """
    per_sample = np.mean(np.abs(acts), axis=1)
    return float(np.mean(per_sample > threshold))


def spirit_erase(acts: np.ndarray, direction: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    """
    SPIRIT linear erasing: subtract alpha × projection onto direction.
    h_erased = h - alpha * (h · d) * d   (direction must be unit norm)
    """
    direction = direction / (np.linalg.norm(direction) + 1e-8)
    projections = acts @ direction  # (N,)
    return acts - alpha * np.outer(projections, direction)


def jailbreak_suppression_rate(
    acts: np.ndarray,
    direction: np.ndarray,
    threshold: float = THRESHOLD_JB
) -> float:
    """
    Fraction of jailbreak inputs where projection onto jailbreak direction
    falls below threshold (i.e., the jailbreak signal has been erased).
    """
    direction_unit = direction / (np.linalg.norm(direction) + 1e-8)
    projections = np.abs(acts @ direction_unit)
    return float(np.mean(projections < threshold))


# ─── Main Experiment ─────────────────────────────────────────────────────────

def run_spirit_experiment() -> Dict:
    results = {}
    
    # ── 1. Simulate activations at L* ─────────────────────────────────────
    benign_acts, _    = simulate_activations(N_BENIGN,    is_jailbreak=False, layer=L_STAR)
    jailbreak_acts, _ = simulate_activations(N_JAILBREAK, is_jailbreak=True,  layer=L_STAR)
    
    # ── 2. Estimate jailbreak direction (PCA/mean-diff) ───────────────────
    benign_mean    = np.mean(benign_acts,    axis=0)
    jailbreak_mean = np.mean(jailbreak_acts, axis=0)
    jb_direction   = jailbreak_mean - benign_mean   # raw mean-diff
    jb_direction   /= np.linalg.norm(jb_direction)  # unit sphere
    
    # ── 3. Baseline metrics (before erasing) ──────────────────────────────
    baseline_and_frac_benign    = compute_and_frac(benign_acts)
    baseline_and_frac_jailbreak = compute_and_frac(jailbreak_acts)
    baseline_suppression        = jailbreak_suppression_rate(jailbreak_acts, jb_direction)
    baseline_cosine_benign      = float(np.mean(
        benign_acts @ jb_direction / (np.linalg.norm(benign_acts, axis=1) + 1e-8)
    ))
    
    results["baseline"] = {
        "and_frac_benign":    round(baseline_and_frac_benign,    4),
        "and_frac_jailbreak": round(baseline_and_frac_jailbreak, 4),
        "suppression_rate":   round(baseline_suppression,        4),
        "cosine_benign_to_jb_dir": round(baseline_cosine_benign, 4),
    }
    
    # ── 4. Ablation A: varying erasing strength α ─────────────────────────
    alphas = [0.5, 1.0, 1.5, 2.0]
    results["ablation_alpha"] = []
    
    for alpha in alphas:
        benign_erased    = spirit_erase(benign_acts,    jb_direction, alpha)
        jailbreak_erased = spirit_erase(jailbreak_acts, jb_direction, alpha)
        
        and_frac_benign_post    = compute_and_frac(benign_erased)
        and_frac_jailbreak_post = compute_and_frac(jailbreak_erased)
        suppression_post        = jailbreak_suppression_rate(jailbreak_erased, jb_direction)
        and_frac_retention      = and_frac_benign_post / (baseline_and_frac_benign + 1e-8)
        
        # Cosine similarity of erased benign to original benign mean
        cosine_preservation = float(np.mean(
            benign_erased @ benign_mean / (
                np.linalg.norm(benign_erased, axis=1) *
                np.linalg.norm(benign_mean) + 1e-8
            )
        ))
        
        results["ablation_alpha"].append({
            "alpha":                round(alpha,                   2),
            "and_frac_benign":      round(and_frac_benign_post,    4),
            "and_frac_jailbreak":   round(and_frac_jailbreak_post, 4),
            "suppression_rate":     round(suppression_post,        4),
            "and_frac_retention":   round(and_frac_retention,      4),
            "cosine_preservation":  round(cosine_preservation,     4),
            "passes_target":        (and_frac_retention >= 0.8 and suppression_post >= 0.85),
        })
    
    # ── 5. Ablation B: layer sensitivity (erase at L*-1, L*, L*+1) ────────
    layers_to_test = [L_STAR - 1, L_STAR, L_STAR + 1]
    results["ablation_layer"] = []
    
    for layer in layers_to_test:
        b_acts, _ = simulate_activations(N_BENIGN,    is_jailbreak=False, layer=layer)
        j_acts, _ = simulate_activations(N_JAILBREAK, is_jailbreak=True,  layer=layer)
        
        b_mean = np.mean(b_acts, axis=0)
        j_mean = np.mean(j_acts, axis=0)
        direction = j_mean - b_mean
        direction /= np.linalg.norm(direction) + 1e-8
        
        b_erased = spirit_erase(b_acts, direction, alpha=1.0)
        j_erased = spirit_erase(j_acts, direction, alpha=1.0)
        
        base_and = compute_and_frac(b_acts)
        erased_and = compute_and_frac(b_erased)
        
        results["ablation_layer"].append({
            "layer":              layer,
            "label":              f"L*{'+1' if layer > L_STAR else ('-1' if layer < L_STAR else '')}",
            "and_frac_pre":       round(base_and,                          4),
            "and_frac_post":      round(erased_and,                        4),
            "and_frac_retention": round(erased_and / (base_and + 1e-8),    4),
            "suppression_rate":   round(jailbreak_suppression_rate(j_erased, direction), 4),
        })
    
    # ── 6. Summary / Target Assessment ────────────────────────────────────
    # Use alpha=1.0 at L* for primary result
    best = next(r for r in results["ablation_alpha"] if r["alpha"] == 1.0)
    
    results["summary"] = {
        "primary_alpha": 1.0,
        "primary_layer": L_STAR,
        "and_frac_retention":   best["and_frac_retention"],
        "suppression_rate":     best["suppression_rate"],
        "target_and_retention": 0.80,
        "target_suppression":   0.85,
        "passes_both_targets":  best["passes_target"],
        "interpretation": (
            "SPIRIT erasing at L* with α=1.0 achieves "
            f"AND-frac retention={best['and_frac_retention']:.2%} "
            f"and jailbreak suppression={best['suppression_rate']:.2%}. "
            + ("✅ Both targets met." if best["passes_target"]
               else "⚠️ One or more targets missed.")
        ),
    }
    
    return results


# ─── Run ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    results = run_spirit_experiment()
    
    print("=" * 60)
    print("Q208: SPIRIT-Style Linear Erasing at L* — Results")
    print("=" * 60)
    
    b = results["baseline"]
    print(f"\n📊 Baseline (before erasing, at L*={L_STAR}):")
    print(f"   AND-frac benign:    {b['and_frac_benign']:.4f}")
    print(f"   AND-frac jailbreak: {b['and_frac_jailbreak']:.4f}")
    print(f"   Suppression rate:   {b['suppression_rate']:.4f}  (should be low before erasing)")
    print(f"   Cosine(benign, jb_dir): {b['cosine_benign_to_jb_dir']:.4f}")
    
    print(f"\n🔬 Ablation A: Erasing Strength α (L*={L_STAR})")
    print(f"   {'α':>5}  {'AND-frac↑':>10}  {'Retention↑':>10}  {'Suppress↑':>10}  {'Pass?':>6}")
    for r in results["ablation_alpha"]:
        print(f"   {r['alpha']:>5.1f}  {r['and_frac_benign']:>10.4f}  "
              f"{r['and_frac_retention']:>10.4f}  {r['suppression_rate']:>10.4f}  "
              f"{'✅' if r['passes_target'] else '❌':>6}")
    
    print(f"\n🔬 Ablation B: Layer Sensitivity (α=1.0)")
    print(f"   {'Layer':>7}  {'AND-pre':>8}  {'AND-post':>9}  {'Retention':>9}  {'Suppress':>9}")
    for r in results["ablation_layer"]:
        print(f"   {r['label']:>7}  {r['and_frac_pre']:>8.4f}  {r['and_frac_post']:>9.4f}  "
              f"{r['and_frac_retention']:>9.4f}  {r['suppression_rate']:>9.4f}")
    
    s = results["summary"]
    print(f"\n{'=' * 60}")
    print(f"🎯 Primary Result (α=1.0, L*={L_STAR}):")
    print(f"   {s['interpretation']}")
    print(f"{'=' * 60}")
    
    # Save JSON
    out_path = "memory/learning/artifacts/q208_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to {out_path}")
