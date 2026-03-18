#!/usr/bin/env python3
"""
Q118 — emotion_and_or_gate.py
Emotion-coding features → AND or OR gate?
Mock: 50 emotion features + 50 non-emotion. Compare gate type distribution.
"""
import argparse
import json
import sys
import numpy as np
from dataclasses import dataclass, asdict
from typing import Dict, List


@dataclass
class GateDistribution:
    group: str
    n_features: int
    and_fraction: float
    or_fraction: float
    passthrough_fraction: float
    silent_fraction: float


def parse_args():
    p = argparse.ArgumentParser(description="Q118: Emotion features AND/OR gate analysis")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-emotion", type=int, default=50)
    p.add_argument("--n-non-emotion", type=int, default=50)
    p.add_argument("--n-stimuli", type=int, default=80)
    p.add_argument("--json", action="store_true")
    return p.parse_args()


def classify_gate(clean, noisy, patched, thresh=0.3):
    """Classify feature gate type from activation triplet."""
    if clean < thresh and noisy < thresh and patched < thresh:
        return "silent"
    if noisy >= thresh * 0.8:
        return "or"
    if noisy < thresh * 0.5 and patched >= thresh * 0.8:
        return "and"
    return "passthrough"


def generate_emotion_activations(rng, n_features, n_stimuli, is_emotion):
    """
    Emotion features hypothesis: emotion requires BOTH audio prosody (signal A)
    AND semantic context (signal B) → AND-gate behavior.
    Non-emotion features: purely acoustic → OR-gate (fires from audio alone).
    """
    clean   = np.zeros((n_features, n_stimuli))
    noisy   = np.zeros((n_features, n_stimuli))
    patched = np.zeros((n_features, n_stimuli))

    for f in range(n_features):
        base = rng.uniform(0.5, 0.85, size=n_stimuli)
        clean[f] = base + rng.standard_normal(n_stimuli) * 0.04

        if is_emotion:
            # Emotion: AND-gate dominant — drops in noise, recovers with patch
            and_prob = rng.uniform(0.55, 0.85)
            for s in range(n_stimuli):
                if rng.random() < and_prob:
                    noisy[f, s]   = base[s] * rng.uniform(0.05, 0.25)
                    patched[f, s] = base[s] * rng.uniform(0.80, 1.00)
                else:
                    noisy[f, s]   = base[s] * rng.uniform(0.70, 0.95)
                    patched[f, s] = base[s] * rng.uniform(0.80, 1.00)
        else:
            # Non-emotion: OR-gate dominant — robust to noise
            or_prob = rng.uniform(0.55, 0.85)
            for s in range(n_stimuli):
                if rng.random() < or_prob:
                    noisy[f, s]   = base[s] * rng.uniform(0.70, 0.95)
                    patched[f, s] = base[s] * rng.uniform(0.80, 1.00)
                else:
                    noisy[f, s]   = base[s] * rng.uniform(0.05, 0.30)
                    patched[f, s] = base[s] * rng.uniform(0.80, 1.00)

        noisy[f]   += rng.standard_normal(n_stimuli) * 0.04
        patched[f] += rng.standard_normal(n_stimuli) * 0.04

    return clean, noisy, patched


def compute_gate_distribution(clean, noisy, patched, thresh=0.3):
    n_features, n_stimuli = clean.shape
    gate_counts: Dict[str, int] = {"and": 0, "or": 0, "passthrough": 0, "silent": 0}

    per_feature_majority = []
    for f in range(n_features):
        feature_gates: Dict[str, int] = {"and": 0, "or": 0, "passthrough": 0, "silent": 0}
        for s in range(n_stimuli):
            g = classify_gate(clean[f, s], noisy[f, s], patched[f, s], thresh)
            feature_gates[g] += 1
        majority = max(feature_gates, key=feature_gates.get)
        per_feature_majority.append(majority)
        gate_counts[majority] += 1

    total = n_features
    return {k: v / total for k, v in gate_counts.items()}, per_feature_majority


def run_experiment(args):
    rng = np.random.default_rng(args.seed)

    print("Q118: Emotion Features → AND/OR Gate Distribution")
    print(f"  Emotion features: {args.n_emotion}, Non-emotion: {args.n_non_emotion}, "
          f"Stimuli: {args.n_stimuli}, Seed: {args.seed}")
    print()

    # Generate activations
    clean_e, noisy_e, patched_e = generate_emotion_activations(
        rng, args.n_emotion, args.n_stimuli, is_emotion=True)
    clean_ne, noisy_ne, patched_ne = generate_emotion_activations(
        rng, args.n_non_emotion, args.n_stimuli, is_emotion=False)

    dist_e,  gates_e  = compute_gate_distribution(clean_e,  noisy_e,  patched_e)
    dist_ne, gates_ne = compute_gate_distribution(clean_ne, noisy_ne, patched_ne)

    dists = [
        GateDistribution("emotion",     args.n_emotion,     dist_e["and"],  dist_e["or"],
                         dist_e["passthrough"],  dist_e["silent"]),
        GateDistribution("non-emotion", args.n_non_emotion, dist_ne["and"], dist_ne["or"],
                         dist_ne["passthrough"], dist_ne["silent"]),
    ]

    print(f"{'Group':<14} {'N':>4} {'AND%':>8} {'OR%':>8} {'Pass%':>8} {'Silent%':>8}")
    print("-" * 55)
    for d in dists:
        print(f"{d.group:<14} {d.n_features:>4} "
              f"{d.and_fraction*100:>8.1f} {d.or_fraction*100:>8.1f} "
              f"{d.passthrough_fraction*100:>8.1f} {d.silent_fraction*100:>8.1f}")

    print()
    and_diff = dist_e["and"] - dist_ne["and"]
    or_diff  = dist_e["or"]  - dist_ne["or"]
    print(f"AND-gate fraction difference (emotion - non-emotion): {and_diff:+.3f}")
    print(f"OR-gate  fraction difference (emotion - non-emotion): {or_diff:+.3f}")

    print()
    h1_pass = and_diff > 0.15
    print(f"H1: Emotion features are more AND-gate than non-emotion")
    print(f"    AND diff = {and_diff:+.3f} > 0.15 → {'PASS' if h1_pass else 'FAIL'}")

    h2_pass = or_diff < -0.10
    print(f"H2: Non-emotion features are more OR-gate than emotion")
    print(f"    OR diff = {or_diff:+.3f} < -0.10 → {'PASS' if h2_pass else 'FAIL'}")

    # Chi-squared-like test
    emotion_and = int(dist_e["and"] * args.n_emotion)
    emotion_or  = int(dist_e["or"]  * args.n_emotion)
    nonem_and   = int(dist_ne["and"] * args.n_non_emotion)
    nonem_or    = int(dist_ne["or"]  * args.n_non_emotion)
    print()
    print("Contingency table (AND vs OR × emotion vs non-emotion):")
    print(f"               {'AND':>6} {'OR':>6}")
    print(f"  Emotion:     {emotion_and:>6} {emotion_or:>6}")
    print(f"  Non-emotion: {nonem_and:>6} {nonem_or:>6}")

    if args.json:
        output = {
            "experiment": "Q118",
            "results": [asdict(d) for d in dists],
            "and_diff": and_diff,
            "or_diff": or_diff,
            "h1_pass": h1_pass,
            "h2_pass": h2_pass,
        }
        print(json.dumps(output, indent=2))

    return dists


def main():
    args = parse_args()
    run_experiment(args)
    print("\nQ118 complete.")
    sys.exit(0)


if __name__ == "__main__":
    main()
