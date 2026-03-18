#!/usr/bin/env python3
"""
Q124 — codec_probe_and_or.py
Codec Probe RVQ × AND/OR gates: RVQ-1 semantic features = OR-gate.
Mock: 8 RVQ levels × 50 features. Classify by level, measure gate distribution.
"""
import argparse
import json
import sys
import numpy as np
from dataclasses import dataclass, asdict
from typing import List


# RVQ hierarchy: level 1 = coarse semantic, level 8 = fine acoustic detail
# Hypothesis: RVQ-1 features are OR-gate (fire with either signal = semantic redundancy)
# RVQ-8 features are AND-gate (require precise acoustic alignment)

@dataclass
class RVQLevelResult:
    rvq_level: int
    n_features: int
    and_fraction: float
    or_fraction: float
    passthrough_fraction: float
    silent_fraction: float
    semantic_score: float  # proxy: higher = more semantic (lower RVQ level)


def parse_args():
    p = argparse.ArgumentParser(description="Q124: Codec Probe RVQ × AND/OR gate distribution")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-rvq-levels", type=int, default=8)
    p.add_argument("--n-features-per-level", type=int, default=50)
    p.add_argument("--n-stimuli", type=int, default=80)
    p.add_argument("--json", action="store_true")
    return p.parse_args()


def classify_gate(clean, noisy, patched, thresh=0.3):
    if clean < thresh and noisy < thresh:
        return "silent"
    if noisy >= thresh * 0.8:
        return "or"
    if noisy < thresh * 0.5 and patched >= thresh * 0.8:
        return "and"
    return "passthrough"


def generate_rvq_activations(rng, n_features, n_stimuli, rvq_level, n_rvq_levels):
    """
    RVQ level determines gate type distribution:
    - Level 1 (semantic): OR-gate dominant (semantic info available in any modality)
    - Level 8 (acoustic): AND-gate dominant (precise acoustic detail needs both streams)
    """
    # Fraction of features that are OR-gate decreases with level
    p_or  = 1.0 - (rvq_level - 1) / (n_rvq_levels - 1)  # level 1→1.0, level 8→0.0
    p_and = (rvq_level - 1) / (n_rvq_levels - 1)          # level 1→0.0, level 8→1.0

    clean   = np.zeros((n_features, n_stimuli))
    noisy   = np.zeros((n_features, n_stimuli))
    patched = np.zeros((n_features, n_stimuli))

    for f in range(n_features):
        base = rng.uniform(0.5, 0.85, size=n_stimuli)
        clean[f] = base + rng.standard_normal(n_stimuli) * 0.04

        for s in range(n_stimuli):
            r = rng.random()
            if r < p_or:  # OR-gate
                noisy[f, s]   = base[s] * rng.uniform(0.75, 0.95)
                patched[f, s] = base[s] * rng.uniform(0.85, 1.00)
            elif r < p_or + p_and:  # AND-gate
                noisy[f, s]   = base[s] * rng.uniform(0.03, 0.20)
                patched[f, s] = base[s] * rng.uniform(0.80, 1.00)
            else:  # passthrough
                noisy[f, s]   = base[s] * rng.uniform(0.30, 0.60)
                patched[f, s] = base[s] * rng.uniform(0.80, 1.00)

        noisy[f]   += rng.standard_normal(n_stimuli) * 0.04
        patched[f] += rng.standard_normal(n_stimuli) * 0.04

    return clean, noisy, patched


def compute_gate_distribution(clean, noisy, patched, thresh=0.3):
    n_features, n_stimuli = clean.shape
    majority_gates = []
    for f in range(n_features):
        counts = {"and": 0, "or": 0, "passthrough": 0, "silent": 0}
        for s in range(n_stimuli):
            g = classify_gate(clean[f, s], noisy[f, s], patched[f, s], thresh)
            counts[g] += 1
        majority_gates.append(max(counts, key=counts.get))

    gate_fracs = {}
    for g in ["and", "or", "passthrough", "silent"]:
        gate_fracs[g] = majority_gates.count(g) / n_features
    return gate_fracs


def run_experiment(args):
    rng = np.random.default_rng(args.seed)
    n_levels = args.n_rvq_levels
    n_feat   = args.n_features_per_level
    n_stim   = args.n_stimuli

    print("Q124: Codec Probe RVQ Level × AND/OR Gate Distribution")
    print(f"  RVQ levels: {n_levels}, Features/level: {n_feat}, "
          f"Stimuli: {n_stim}, Seed: {args.seed}")
    print()

    results: List[RVQLevelResult] = []

    print(f"{'Level':<7} {'AND%':>8} {'OR%':>8} {'Pass%':>8} {'Silent%':>8} {'SemanticScore':>14}")
    print("-" * 60)

    for level in range(1, n_levels + 1):
        clean, noisy, patched = generate_rvq_activations(
            rng, n_feat, n_stim, level, n_levels)
        dist = compute_gate_distribution(clean, noisy, patched)
        sem_score = 1.0 - (level - 1) / (n_levels - 1)  # proxy

        res = RVQLevelResult(
            rvq_level=level,
            n_features=n_feat,
            and_fraction=dist["and"],
            or_fraction=dist["or"],
            passthrough_fraction=dist["passthrough"],
            silent_fraction=dist["silent"],
            semantic_score=sem_score,
        )
        results.append(res)
        print(f"RVQ-{level:<3} {dist['and']*100:>8.1f} {dist['or']*100:>8.1f} "
              f"{dist['passthrough']*100:>8.1f} {dist['silent']*100:>8.1f} {sem_score:>14.3f}")

    print()

    # Correlations across levels
    levels     = np.array([r.rvq_level      for r in results])
    and_fracs  = np.array([r.and_fraction    for r in results])
    or_fracs   = np.array([r.or_fraction     for r in results])
    sem_scores = np.array([r.semantic_score  for r in results])

    r_level_or  = float(np.corrcoef(levels, or_fracs)[0, 1])
    r_level_and = float(np.corrcoef(levels, and_fracs)[0, 1])
    r_sem_or    = float(np.corrcoef(sem_scores, or_fracs)[0, 1])

    print(f"{'Correlation':<40} {'r':>8}")
    print("-" * 50)
    print(f"{'RVQ level ↔ OR fraction':<40} {r_level_or:>8.4f}")
    print(f"{'RVQ level ↔ AND fraction':<40} {r_level_and:>8.4f}")
    print(f"{'Semantic score ↔ OR fraction':<40} {r_sem_or:>8.4f}")
    print()

    # RVQ-1 vs RVQ-8 comparison
    rvq1 = results[0]
    rvq8 = results[-1]
    print(f"RVQ-1 (semantic): OR={rvq1.or_fraction*100:.1f}%, AND={rvq1.and_fraction*100:.1f}%")
    print(f"RVQ-8 (acoustic): OR={rvq8.or_fraction*100:.1f}%, AND={rvq8.and_fraction*100:.1f}%")

    print()
    h1_pass = rvq1.or_fraction > rvq8.or_fraction
    print(f"H1: RVQ-1 features have higher OR-gate fraction than RVQ-8")
    print(f"    {rvq1.or_fraction:.3f} > {rvq8.or_fraction:.3f} → {'PASS' if h1_pass else 'FAIL'}")

    h2_pass = rvq8.and_fraction > rvq1.and_fraction
    print(f"H2: RVQ-8 features have higher AND-gate fraction than RVQ-1")
    print(f"    {rvq8.and_fraction:.3f} > {rvq1.and_fraction:.3f} → {'PASS' if h2_pass else 'FAIL'}")

    h3_pass = r_level_or < -0.5
    print(f"H3: OR fraction decreases with RVQ level (semantic→acoustic)")
    print(f"    r(level, OR) = {r_level_or:.4f} < -0.5 → {'PASS' if h3_pass else 'FAIL'}")

    if args.json:
        output = {
            "experiment": "Q124",
            "results": [asdict(r) for r in results],
            "r_level_or": r_level_or,
            "r_level_and": r_level_and,
            "h1": h1_pass, "h2": h2_pass, "h3": h3_pass,
        }
        print(json.dumps(output, indent=2))

    return results


def main():
    args = parse_args()
    run_experiment(args)
    print("\nQ124 complete.")
    sys.exit(0)


if __name__ == "__main__":
    main()
