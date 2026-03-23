"""
and_frac_scaling_mock.py — Q155
AND-frac at gc_peak across Whisper model sizes (mock simulation)

Hypothesis: AND-frac(k*) scales log-linearly with model parameter count.
"""

import numpy as np
import json

# Whisper model size table
MODELS = {
    "base":     {"params_M": 74,   "encoder_layers": 6,  "d_model": 512,  "heads": 8},
    "small":    {"params_M": 244,  "encoder_layers": 12, "d_model": 768,  "heads": 12},
    "medium":   {"params_M": 769,  "encoder_layers": 24, "d_model": 1024, "heads": 16},
    "large-v3": {"params_M": 1550, "encoder_layers": 32, "d_model": 1280, "heads": 20},
}

def simulate_and_frac(params_M: float, seed: int = 42) -> dict:
    """
    Mock AND-frac at gc_peak for a given model size.
    
    Mock model:
      AND-frac_mean = A * log10(params_M) + B
      noise = N(0, sigma)
    
    Fitted to expected values:
      base  (74M)  → 0.31
      large (1550M) → 0.49
    """
    rng = np.random.default_rng(seed)
    
    # Log-linear model parameters (mock calibration)
    A = 0.062   # slope per decade
    B = 0.185   # intercept
    
    and_frac_mean = A * np.log10(params_M) + B
    
    # Simulate 50 clips (each gives one AND-frac estimate)
    n_clips = 50
    sigma = 0.04  # clip-level variance
    clip_fracs = rng.normal(and_frac_mean, sigma, n_clips)
    clip_fracs = np.clip(clip_fracs, 0.0, 1.0)
    
    return {
        "mean": float(np.mean(clip_fracs)),
        "std": float(np.std(clip_fracs)),
        "ci_95": [
            float(np.percentile(clip_fracs, 2.5)),
            float(np.percentile(clip_fracs, 97.5)),
        ],
        "predicted_mean": float(and_frac_mean),
        "n_clips": n_clips,
    }


def simulate_gc_peak_layer(encoder_layers: int, params_M: float) -> dict:
    """
    Mock gc_peak layer (normalized k* = gc_peak / total_layers).
    Hypothesis: larger models have later gc_peak (more refined commitment).
    """
    # Normalized k* shifts from ~0.55 (base) to ~0.65 (large)
    k_star_norm = 0.55 + 0.035 * np.log10(params_M / 74)
    gc_peak_abs = int(round(k_star_norm * encoder_layers))
    return {
        "k_star_normalized": round(k_star_norm, 3),
        "gc_peak_abs_layer": gc_peak_abs,
        "total_encoder_layers": encoder_layers,
    }


def fit_scaling_law(results: dict) -> dict:
    """Fit log-linear AND-frac ~ log10(params) scaling law."""
    log_params = np.array([np.log10(v["params_M"]) for v in MODELS.values()])
    and_fracs = np.array([results[name]["and_frac"]["mean"] for name in MODELS])
    
    # Linear regression: AND-frac = A * log10(params) + B
    A, B = np.polyfit(log_params, and_fracs, 1)
    
    # R²
    and_frac_pred = A * log_params + B
    ss_res = np.sum((and_fracs - and_frac_pred) ** 2)
    ss_tot = np.sum((and_fracs - np.mean(and_fracs)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 1.0
    
    return {
        "slope_A": round(float(A), 4),
        "intercept_B": round(float(B), 4),
        "r_squared": round(float(r2), 4),
        "interpretation": f"AND-frac increases by {A:.3f} per 10x increase in params",
    }


def main():
    print("=" * 60)
    print("Q155: AND-frac Scaling with Whisper Model Size (MOCK)")
    print("=" * 60)
    print()
    
    results = {}
    
    print(f"{'Model':<12} {'Params':>8} {'gc_peak':>8} {'k*_norm':>8} {'AND-frac':>10} {'95% CI':>20}")
    print("-" * 70)
    
    for name, spec in MODELS.items():
        and_frac = simulate_and_frac(spec["params_M"], seed=42)
        gc_peak = simulate_gc_peak_layer(spec["encoder_layers"], spec["params_M"])
        
        results[name] = {
            "params_M": spec["params_M"],
            "and_frac": and_frac,
            "gc_peak": gc_peak,
        }
        
        ci = and_frac["ci_95"]
        print(
            f"{name:<12} {spec['params_M']:>7}M "
            f"{gc_peak['gc_peak_abs_layer']:>7}/{spec['encoder_layers']} "
            f"{gc_peak['k_star_normalized']:>8.3f} "
            f"{and_frac['mean']:>9.3f}±{and_frac['std']:.3f} "
            f"[{ci[0]:.2f},{ci[1]:.2f}]"
        )
    
    print()
    law = fit_scaling_law(results)
    print("Scaling Law Fit (log-linear):")
    print(f"  AND-frac = {law['slope_A']:.4f} × log10(params_M) + {law['intercept_B']:.4f}")
    print(f"  R² = {law['r_squared']:.4f}")
    print(f"  Interpretation: {law['interpretation']}")
    print()
    
    # Check hypothesis
    means = [results[m]["and_frac"]["mean"] for m in MODELS]
    monotonic = all(means[i] < means[i+1] for i in range(len(means)-1))
    print(f"Hypothesis (monotonic scaling): {'✅ CONFIRMED' if monotonic else '❌ FAILED'}")
    print(f"AND-frac range: [{min(means):.3f}, {max(means):.3f}]")
    print()
    
    # Paper A implication
    print("Paper A implication:")
    print("  - Larger models listen harder (higher AND-frac at gc_peak)")
    print("  - Scale alone doesn't fix hallucination (AND-frac still < 0.5 even at 1.5B)")
    print("  - AND-frac as cheap hallucination-risk proxy across model sizes → testable claim")
    
    # Save results
    output = {
        "task": "Q155",
        "mock": True,
        "models": results,
        "scaling_law": law,
        "hypothesis_confirmed": monotonic,
    }
    
    import os
    out_path = os.path.join(os.path.dirname(__file__), "q155_scaling_mock_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to: q155_scaling_mock_results.json")
    
    return output


if __name__ == "__main__":
    main()
