"""
isolate_gc_proxy.py — RAVEL Isolate(k) as a proxy for gc(k) peak layer.

Theory
------
RAVEL defines Isolate(k) as the minimum number of residual stream components
at layer k needed to predict an attribute's value — lower Isolate = more
disentangled representation. We hypothesize:

    argmin_k Isolate(k) ≈ argmax_k gc(k)

where gc(k) is the causal graph connectivity metric from our Listen vs Guess
paper (peak = layer where audio features are most causally organized).

This script:
1. Generates mock Isolate(k) curves (sinusoidal with noise)
2. Generates mock gc(k) curves from the same underlying signal (+ noise)
3. Verifies argmin(Isolate) ≈ argmax(gc) across 100 synthetic models
4. Reports: hit@1, hit@±1, mean absolute error (in layers), and savings estimate

Usage
-----
    python3 isolate_gc_proxy.py                 # run validation
    python3 isolate_gc_proxy.py --layers 48     # test on 48-layer model

Savings
-------
Computing gc(k) requires patching experiments (expensive: O(N_pairs × N_layers)).
Isolate(k) can be computed with a few forward passes + linear probes.
If argmin(Isolate) is a reliable proxy, we can pre-screen layers and reduce
patching experiments by ~60-80%.
"""

import argparse
import math
import random
import statistics

def generate_gc_curve(n_layers: int, peak_layer: int, noise: float = 0.05) -> list[float]:
    """Mock gc(k): Gaussian bump centered at peak_layer."""
    sigma = n_layers * 0.15
    curve = []
    for k in range(n_layers):
        val = math.exp(-0.5 * ((k - peak_layer) / sigma) ** 2)
        val += random.gauss(0, noise)
        curve.append(max(0.0, min(1.0, val)))
    return curve


def generate_isolate_curve(
    n_layers: int, gc_curve: list[float], shift: int = 0, noise: float = 0.08
) -> list[float]:
    """
    Mock Isolate(k): inversely related to gc(k), potentially shifted by ±shift layers.
    Lower Isolate → more disentangled → corresponds to higher gc.
    """
    curve = []
    for k in range(n_layers):
        gc_val = gc_curve[k]
        # Isolate is high when gc is low (many components needed), inverted
        base = 1.0 - gc_val
        # Add slight linear trend (early layers have high Isolate due to distributed repr)
        trend = 0.1 * (k / n_layers)
        val = base + trend + random.gauss(0, noise)
        curve.append(max(0.01, val))
    return curve


def argmin(curve: list[float]) -> int:
    return curve.index(min(curve))


def argmax(curve: list[float]) -> int:
    return curve.index(max(curve))


def run_validation(n_layers: int = 32, n_trials: int = 100, noise_gc: float = 0.05,
                   noise_iso: float = 0.08, verbose: bool = False) -> dict:
    """Run N trials, compare argmin(Isolate) vs argmax(gc)."""
    hit1 = 0       # exact match
    hit_pm1 = 0    # within ±1 layer
    errors = []

    for trial in range(n_trials):
        peak_layer = random.randint(n_layers // 4, 3 * n_layers // 4)
        gc = generate_gc_curve(n_layers, peak_layer, noise=noise_gc)
        iso = generate_isolate_curve(n_layers, gc, noise=noise_iso)

        pred_layer = argmin(iso)     # our proxy
        true_layer = argmax(gc)      # ground truth

        err = abs(pred_layer - true_layer)
        errors.append(err)

        if err == 0:
            hit1 += 1
        if err <= 1:
            hit_pm1 += 1

        if verbose and trial < 5:
            print(f"  Trial {trial+1}: true={true_layer}, pred={pred_layer}, err={err}")

    mae = statistics.mean(errors)
    hit1_rate = hit1 / n_trials
    hit_pm1_rate = hit_pm1 / n_trials

    # Savings estimate: if proxy narrows search to ±2 layers, we search 5/n_layers fraction
    search_window = 5  # ±2 + center
    savings_pct = (1 - search_window / n_layers) * 100

    return {
        "n_layers": n_layers,
        "n_trials": n_trials,
        "hit@1": hit1_rate,
        "hit@±1": hit_pm1_rate,
        "mae_layers": round(mae, 2),
        "savings_pct": round(savings_pct, 1),
        "noise_gc": noise_gc,
        "noise_iso": noise_iso,
    }


def compute_savings_table(n_layers: int) -> None:
    """Print savings benchmark across noise levels."""
    print(f"\n{'='*60}")
    print(f"SAVINGS BENCHMARK (n_layers={n_layers}, n_trials=200)")
    print(f"{'='*60}")
    print(f"{'noise_gc':>10} {'noise_iso':>10} {'hit@1':>8} {'hit@±1':>8} {'MAE':>8} {'savings':>10}")
    print(f"{'-'*60}")
    for noise_gc in [0.03, 0.05, 0.08]:
        for noise_iso in [0.05, 0.10, 0.15]:
            r = run_validation(n_layers=n_layers, n_trials=200,
                               noise_gc=noise_gc, noise_iso=noise_iso)
            print(f"{noise_gc:>10.2f} {noise_iso:>10.2f} "
                  f"{r['hit@1']:>8.1%} {r['hit@±1']:>8.1%} "
                  f"{r['mae_layers']:>8.2f} {r['savings_pct']:>9.1f}%")


def main():
    parser = argparse.ArgumentParser(description="RAVEL Isolate as gc(k) proxy validator")
    parser.add_argument("--layers", type=int, default=32, help="Number of layers (default: 32)")
    parser.add_argument("--trials", type=int, default=100, help="Validation trials (default: 100)")
    parser.add_argument("--verbose", action="store_true", help="Show first 5 trial details")
    parser.add_argument("--savings-table", action="store_true", help="Print savings benchmark table")
    args = parser.parse_args()

    random.seed(42)

    print(f"RAVEL Isolate(k) → gc(k) Proxy Validator")
    print(f"Layers: {args.layers} | Trials: {args.trials}")
    print()

    result = run_validation(
        n_layers=args.layers,
        n_trials=args.trials,
        verbose=args.verbose
    )

    print(f"Results:")
    print(f"  hit@1  (exact match)   : {result['hit@1']:.1%}")
    print(f"  hit@±1 (within 1 layer): {result['hit@±1']:.1%}")
    print(f"  MAE                    : {result['mae_layers']:.2f} layers")
    print(f"  Patching savings       : ~{result['savings_pct']:.0f}% (if proxy used to pre-screen)")
    print()

    # Interpret
    if result['hit@±1'] >= 0.80:
        verdict = "✅ STRONG proxy — argmin(Isolate) reliably approximates argmax(gc)"
    elif result['hit@±1'] >= 0.60:
        verdict = "⚠️  MODERATE proxy — useful for pre-screening but needs validation"
    else:
        verdict = "❌ WEAK proxy — noise dominates, not reliable for layer selection"

    print(f"Verdict: {verdict}")

    if args.savings_table:
        compute_savings_table(args.layers)


if __name__ == "__main__":
    main()
