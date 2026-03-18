#!/usr/bin/env python3
"""
RAVEL Isolate Curve as gc(k) Proxy — Q107
Track T3: Listen vs Guess

Hypothesis: argmin(Isolate(L)) ≈ argmax(gc(k,L)) — the layer where audio
information is most *isolated* (lowest bleed to other attributes) is the same
layer where gc(k) peaks (maximum audio grounding causality).

This would make Isolate(L) a cheap proxy for gc(k): instead of running full
patching protocol (3× forward passes), one Isolate measurement suffices.

Mock: 10 layers × 100 features.
  Compute Isolate(L) and gc(k,L) per layer per feature.
  Measure Spearman rank correlation between argmin(Isolate) and argmax(gc).

Usage:
    python3 ravel_isolate_gc_proxy.py
    python3 ravel_isolate_gc_proxy.py --layers 12
    python3 ravel_isolate_gc_proxy.py --json

Dependencies: numpy only
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from typing import List

import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

N_LAYERS   = 10
N_FEATURES = 100
TRUE_PEAK  = 4    # gc(k) true peak layer
SEED = 42

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FeatureLayerResult:
    feature_id: int
    gc_peak_layer: int        # argmax(gc_curve)
    isolate_min_layer: int    # argmin(Isolate_curve)
    layers_agree: bool        # within ±1 layer
    gc_curve: List[float]
    isolate_curve: List[float]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def spearman_r(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman rank correlation."""
    n = len(x)
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    d  = rx - ry
    return float(1 - 6 * (d**2).sum() / (n * (n**2 - 1)))


def pearson_r(x: np.ndarray, y: np.ndarray) -> float:
    xm = x - x.mean(); ym = y - y.mean()
    denom = np.sqrt((xm**2).sum() * (ym**2).sum())
    return float(np.dot(xm, ym) / (denom + 1e-12))


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def simulate_gc_curve(peak_layer: int, n_layers: int,
                      rng: np.random.Generator) -> np.ndarray:
    """Bell-shaped gc(k) profile centred at peak_layer."""
    layers = np.arange(n_layers, dtype=float)
    sigma = 1.8
    gc = np.exp(-0.5 * ((layers - peak_layer) / sigma) ** 2)
    gc += rng.normal(0, 0.04, n_layers)
    return np.clip(gc, 0.02, 1.0)


def simulate_isolate_curve(gc_curve: np.ndarray, n_layers: int,
                            rng: np.random.Generator,
                            alignment_noise: float = 0.1) -> np.ndarray:
    """
    Isolate(L) is inversely related to gc(k,L): at the gc peak, audio is most
    causally isolated. With noise, the relationship is imperfect.
    Isolate_min ≈ gc_max (with some noise added).
    """
    # Inverted gc curve (lower Isolate at gc peak) + noise
    isolate = 1.0 - gc_curve + rng.normal(0, alignment_noise, n_layers)
    return np.clip(isolate, 0.0, 1.0)


def run(n_layers: int, n_features: int, true_peak: int,
        seed: int) -> List[FeatureLayerResult]:
    rng = np.random.default_rng(seed)
    records: List[FeatureLayerResult] = []

    for f in range(n_features):
        # True peak per feature: mostly at true_peak with some variation
        feature_peak = int(rng.normal(true_peak, 1.2))
        feature_peak = max(0, min(n_layers - 1, feature_peak))

        gc_curve      = simulate_gc_curve(feature_peak, n_layers, rng)
        isolate_curve = simulate_isolate_curve(gc_curve, n_layers, rng)

        gc_peak_layer      = int(np.argmax(gc_curve))
        isolate_min_layer  = int(np.argmin(isolate_curve))
        layers_agree       = abs(gc_peak_layer - isolate_min_layer) <= 1

        records.append(FeatureLayerResult(
            feature_id=f,
            gc_peak_layer=gc_peak_layer,
            isolate_min_layer=isolate_min_layer,
            layers_agree=layers_agree,
            gc_curve=list(gc_curve.round(4)),
            isolate_curve=list(isolate_curve.round(4)),
        ))

    return records


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Q107: RAVEL Isolate curve as gc(k) proxy — argmin(Isolate) ≈ argmax(gc)"
    )
    parser.add_argument("--layers",   type=int, default=N_LAYERS)
    parser.add_argument("--features", type=int, default=N_FEATURES)
    parser.add_argument("--true-peak", type=int, default=TRUE_PEAK)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    records = run(args.layers, args.features, args.true_peak, args.seed)

    if args.as_json:
        print(json.dumps([asdict(r) for r in records], indent=2))
        return 0

    gc_peaks      = np.array([r.gc_peak_layer for r in records], dtype=float)
    isolate_mins  = np.array([r.isolate_min_layer for r in records], dtype=float)
    agreement_pct = sum(1 for r in records if r.layers_agree) / len(records) * 100

    spear_r = spearman_r(gc_peaks, isolate_mins)
    pear_r  = pearson_r(gc_peaks, isolate_mins)

    print("=" * 60)
    print("Q107 — RAVEL Isolate Curve as gc(k) Proxy")
    print(f"Config: {args.layers} layers × {args.features} features")
    print(f"True gc peak: layer {args.true_peak},  seed={args.seed}")
    print("=" * 60)

    # Layer-wise agreement table
    print(f"\nLayer agreement (argmin(Isolate) vs argmax(gc)):")
    print(f"  {'Layer':>6} {'gc_peak_N':>10} {'iso_min_N':>10} {'Match':>8}")
    print("-" * 40)
    for lyr in range(args.layers):
        gc_n  = int((gc_peaks    == lyr).sum())
        iso_n = int((isolate_mins == lyr).sum())
        both  = int(((gc_peaks == lyr) & (isolate_mins == lyr)).sum())
        print(f"  {lyr:>6} {gc_n:>10} {iso_n:>10} {both:>8}")

    print(f"\nAgreement (±1 layer): {agreement_pct:.1f}% of features")
    print(f"Pearson  r(gc_peak, iso_min) = {pear_r:.4f}")
    print(f"Spearman r(gc_peak, iso_min) = {spear_r:.4f}")

    # Savings benchmark: Isolate requires 1 fwd pass, gc patching requires 3
    savings_pct = (1 - 1/3) * 100
    print(f"\nCompute savings (Isolate vs full patching protocol):")
    print(f"  Full patching: 3 forward passes per layer per feature")
    print(f"  Isolate proxy: 1 forward pass per layer per feature")
    print(f"  Savings: {savings_pct:.0f}% compute if proxy is valid")

    hyp_confirmed = agreement_pct > 60 and spear_r > 0.5
    print(f"\nHypothesis: argmin(Isolate) ≈ argmax(gc) within ±1 layer")
    print(f"  → {'CONFIRMED' if hyp_confirmed else 'NOT CONFIRMED'}")
    print(f"  Agreement={agreement_pct:.1f}%  Spearman r={spear_r:.4f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
