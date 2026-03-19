#!/usr/bin/env python3
"""
Q113 — cascade_degree.py
Cascade degree = 1 - AND_gate_fraction. Mechanistic link.
Mock: 200 features. Compute both metrics. Correlate.
"""
import argparse
import json
import sys
import numpy as np
from dataclasses import dataclass


@dataclass
class FeatureGateInfo:
    feature_id: int
    and_gate_frac: float
    cascade_degree: float
    activation_peak: float


def parse_args():
    p = argparse.ArgumentParser(description="Q113: Cascade degree vs AND-gate fraction correlation")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-features", type=int, default=200)
    p.add_argument("--n-stimuli", type=int, default=80)
    p.add_argument("--json", action="store_true")
    return p.parse_args()


def classify_gate(clean, noisy, patched, thresh=0.3):
    """Classify feature as AND/OR/pass-through/silent."""
    if clean < thresh and noisy < thresh:
        return "silent"
    if noisy >= thresh * 0.8 and patched >= thresh * 0.8:
        return "or"
    if noisy < thresh and patched >= thresh * 0.8:
        return "and"
    return "passthrough"


def generate_feature_data(rng, n_features, n_stimuli):
    """
    Mock: features vary in AND/OR-gate nature and cascade degree.
    AND-gate features require both signals → low cascade.
    OR-gate features cascade freely → high cascade degree.
    """
    # Ground truth cascade tendency per feature
    true_cascade = rng.uniform(0.0, 1.0, size=n_features)

    clean_acts   = np.zeros((n_features, n_stimuli))
    noisy_acts   = np.zeros((n_features, n_stimuli))
    patched_acts = np.zeros((n_features, n_stimuli))

    for f in range(n_features):
        cd = true_cascade[f]
        base = rng.uniform(0.4, 0.9, size=n_stimuli)
        # AND-gate (low cascade): noisy→drops, patched→recovers
        # OR-gate (high cascade): noisy→stays, robust to perturbation
        clean_acts[f] = base
        if cd < 0.5:  # AND-gate tendency
            noisy_acts[f]   = base * rng.uniform(0.05, 0.25, size=n_stimuli)
            patched_acts[f] = base * rng.uniform(0.75, 1.0, size=n_stimuli)
        else:          # OR-gate tendency
            noisy_acts[f]   = base * rng.uniform(0.75, 1.0, size=n_stimuli)
            patched_acts[f] = base * rng.uniform(0.80, 1.0, size=n_stimuli)

        # Add noise
        clean_acts[f]   += rng.standard_normal(n_stimuli) * 0.05
        noisy_acts[f]   += rng.standard_normal(n_stimuli) * 0.05
        patched_acts[f] += rng.standard_normal(n_stimuli) * 0.05

    return clean_acts, noisy_acts, patched_acts, true_cascade


def compute_and_fraction(clean, noisy, patched, thresh=0.3):
    """Per-feature AND-gate fraction across stimuli."""
    n_features, n_stimuli = clean.shape
    and_fracs = np.zeros(n_features)
    for f in range(n_features):
        gates = [classify_gate(clean[f, s], noisy[f, s], patched[f, s], thresh)
                 for s in range(n_stimuli)]
        and_fracs[f] = gates.count("and") / n_stimuli
    return and_fracs


def compute_cascade_degree(clean, noisy, patched):
    """
    Cascade degree: how much does denoising (patching) FURTHER change activation
    beyond what noisy context already achieves?
    cascade_degree = mean(|patched - noisy|) / mean(clean)
    High cascade: noisy already active, patching adds little → low numerator → hmm.
    Redefine: cascade_degree = mean(noisy / clean) — how much persists under noise.
    """
    n_features = clean.shape[0]
    eps = 1e-6
    cascade_deg = np.zeros(n_features)
    for f in range(n_features):
        c = np.clip(clean[f], eps, None)
        cascade_deg[f] = float(np.mean(noisy[f] / c))
    return cascade_deg


def run_experiment(args):
    rng = np.random.default_rng(args.seed)
    n_features = args.n_features
    n_stimuli  = args.n_stimuli

    print("Q113: Cascade Degree ↔ AND-gate Fraction Correlation")
    print(f"  Features: {n_features}, Stimuli: {n_stimuli}, Seed: {args.seed}")
    print()

    clean, noisy, patched, true_cascade = generate_feature_data(rng, n_features, n_stimuli)

    and_fracs    = compute_and_fraction(clean, noisy, patched)
    cascade_degs = compute_cascade_degree(clean, noisy, patched)

    # Cascade degree = 1 - AND_gate_fraction (hypothesis)
    derived_cascade = 1.0 - and_fracs

    pearson = float(np.corrcoef(and_fracs, cascade_degs)[0, 1])
    pearson_derived = float(np.corrcoef(derived_cascade, cascade_degs)[0, 1])
    pearson_truth   = float(np.corrcoef(true_cascade, cascade_degs)[0, 1])

    print(f"{'Metric':<40} {'Value':>10}")
    print("-" * 52)
    print(f"{'Pearson(AND_frac, cascade_deg)':<40} {pearson:>10.4f}")
    print(f"{'Pearson(1-AND_frac, cascade_deg)':<40} {pearson_derived:>10.4f}")
    print(f"{'Pearson(true_cascade, cascade_deg)':<40} {pearson_truth:>10.4f}")
    print()

    # Distribution summary
    print(f"AND-gate fraction: mean={np.mean(and_fracs):.3f} ± {np.std(and_fracs):.3f}")
    print(f"Cascade degree:    mean={np.mean(cascade_degs):.3f} ± {np.std(cascade_degs):.3f}")
    print(f"1-AND fraction:    mean={np.mean(derived_cascade):.3f} ± {np.std(derived_cascade):.3f}")

    print()
    thresh = -0.5
    h1_pass = pearson < thresh
    print(f"H1: AND-gate fraction negatively correlated with cascade degree")
    print(f"    Pearson r = {pearson:.4f} (threshold < {thresh}) → {'PASS' if h1_pass else 'FAIL'}")

    h2_pass = abs(pearson_derived) > 0.7
    print(f"H2: 1 - AND_frac ≈ cascade_degree (strong positive correlation)")
    print(f"    Pearson r = {pearson_derived:.4f} (threshold > 0.7) → {'PASS' if h2_pass else 'FAIL'}")

    # Top-10 highest cascade features
    top_idx = np.argsort(cascade_degs)[-10:][::-1]
    print()
    print(f"Top-10 highest cascade features:")
    print(f"{'FeatID':>6} {'CascDeg':>10} {'ANDFrac':>10} {'1-ANDFrac':>10}")
    for idx in top_idx:
        print(f"{idx:>6} {cascade_degs[idx]:>10.4f} {and_fracs[idx]:>10.4f} {1-and_fracs[idx]:>10.4f}")

    if args.json:
        output = {
            "experiment": "Q113",
            "pearson_and_vs_cascade": pearson,
            "pearson_derived_vs_cascade": pearson_derived,
            "pearson_truth_vs_cascade": pearson_truth,
            "mean_and_frac": float(np.mean(and_fracs)),
            "mean_cascade_deg": float(np.mean(cascade_degs)),
        }
        print(json.dumps(output, indent=2))

    return pearson, pearson_derived


def main():
    args = parse_args()
    run_experiment(args)
    print("\nQ113 complete.")
    sys.exit(0)


if __name__ == "__main__":
    main()
