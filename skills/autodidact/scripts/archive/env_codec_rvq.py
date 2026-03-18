#!/usr/bin/env python3
"""
Q126 — env_codec_rvq.py
ENV taxonomy × Codec Probe RVQ: ENV-1 hub features appear at RVQ-1.
Mock: 3 ENV × 8 RVQ × 100 features. Cross-tabulate.
"""
import argparse
import json
import sys
import numpy as np
from dataclasses import dataclass, asdict
from typing import List, Dict


# ENV taxonomy: ENV-1=hub, ENV-2=connector, ENV-3=isolated
# RVQ levels: 1=semantic/coarse, 8=acoustic/fine
# Hypothesis: ENV-1 hubs concentrate at RVQ-1 (semantic level)

@dataclass
class CrossTabEntry:
    env_type: int
    rvq_level: int
    count: int
    fraction_of_env: float
    fraction_of_rvq: float


def parse_args():
    p = argparse.ArgumentParser(description="Q126: ENV taxonomy × Codec Probe RVQ cross-tabulation")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-features", type=int, default=100)
    p.add_argument("--n-rvq-levels", type=int, default=8)
    p.add_argument("--json", action="store_true")
    return p.parse_args()


def assign_env_and_rvq(rng, n_features, n_rvq):
    """
    Assign ENV type and dominant RVQ level to each feature.
    ENV-1 hubs: concentrated at RVQ-1 (semantic features are hubs).
    ENV-2 connectors: spread across mid-RVQ levels.
    ENV-3 isolated: concentrated at high RVQ levels (fine acoustic detail).
    """
    env_types = np.zeros(n_features, dtype=int)
    rvq_levels = np.zeros(n_features, dtype=int)

    # ENV assignment (20% hub, 40% connector, 40% isolated)
    env_types[:int(n_features * 0.2)] = 1
    env_types[int(n_features * 0.2):int(n_features * 0.6)] = 2
    env_types[int(n_features * 0.6):] = 3
    rng.shuffle(env_types)

    # RVQ assignment based on ENV type
    for f in range(n_features):
        env = env_types[f]
        if env == 1:  # Hub: concentrated at RVQ-1 and 2
            probs = np.array([0.45, 0.30, 0.10, 0.05, 0.04, 0.03, 0.02, 0.01])
        elif env == 2:  # Connector: spread across mid-levels
            probs = np.array([0.10, 0.15, 0.20, 0.20, 0.15, 0.10, 0.05, 0.05])
        else:  # Isolated: concentrated at high RVQ levels
            probs = np.array([0.01, 0.02, 0.03, 0.05, 0.10, 0.20, 0.29, 0.30])
        probs /= probs.sum()
        rvq_levels[f] = rng.choice(np.arange(1, n_rvq + 1), p=probs)

    return env_types, rvq_levels


def build_cross_tab(env_types, rvq_levels, n_rvq):
    """Build cross-tabulation matrix: ENV × RVQ."""
    env_vals = [1, 2, 3]
    rvq_vals = list(range(1, n_rvq + 1))

    tab = {}
    for env in env_vals:
        for rvq in rvq_vals:
            tab[(env, rvq)] = 0

    for f in range(len(env_types)):
        tab[(env_types[f], rvq_levels[f])] += 1

    return tab


def run_experiment(args):
    rng = np.random.default_rng(args.seed)
    n_rvq = args.n_rvq_levels

    print("Q126: ENV Taxonomy × Codec Probe RVQ Cross-tabulation")
    print(f"  Features: {args.n_features}, RVQ levels: {n_rvq}, Seed: {args.seed}")
    print()

    env_types, rvq_levels = assign_env_and_rvq(rng, args.n_features, n_rvq)
    tab = build_cross_tab(env_types, rvq_levels, n_rvq)

    # Count by ENV and RVQ
    env_counts = {1: (env_types == 1).sum(), 2: (env_types == 2).sum(), 3: (env_types == 3).sum()}
    rvq_counts = {l: (rvq_levels == l).sum() for l in range(1, n_rvq + 1)}

    # Print cross-tab
    env_names = {1: "ENV-1 Hub", 2: "ENV-2 Conn", 3: "ENV-3 Isol"}
    print(f"{'':12}", end="")
    for l in range(1, n_rvq + 1):
        print(f"RVQ-{l:>1}  ", end="")
    print(f"  {'Total':>6}")
    print("-" * (12 + 8 * n_rvq + 8))

    for env in [1, 2, 3]:
        print(f"{env_names[env]:<12}", end="")
        for l in range(1, n_rvq + 1):
            print(f"{tab[(env, l)]:>7} ", end="")
        print(f"  {env_counts[env]:>6}")

    print(f"{'Total':<12}", end="")
    for l in range(1, n_rvq + 1):
        print(f"{rvq_counts[l]:>7} ", end="")
    print(f"  {args.n_features:>6}")

    # Build CrossTabEntry results
    results: List[CrossTabEntry] = []
    for env in [1, 2, 3]:
        for l in range(1, n_rvq + 1):
            count = tab[(env, l)]
            results.append(CrossTabEntry(
                env_type=env,
                rvq_level=l,
                count=count,
                fraction_of_env=count / env_counts[env] if env_counts[env] > 0 else 0.0,
                fraction_of_rvq=count / rvq_counts[l]   if rvq_counts[l]   > 0 else 0.0,
            ))

    print()
    print("Fraction of ENV-type at each RVQ level:")
    print(f"{'':12}", end="")
    for l in range(1, n_rvq + 1):
        print(f"RVQ-{l:>1}  ", end="")
    print()
    print("-" * (12 + 8 * n_rvq))

    for env in [1, 2, 3]:
        print(f"{env_names[env]:<12}", end="")
        for l in range(1, n_rvq + 1):
            frac = tab[(env, l)] / env_counts[env] if env_counts[env] > 0 else 0.0
            print(f"{frac*100:>6.1f}% ", end="")
        print()

    print()

    # Key metrics for hypotheses
    env1_rvq1_frac = tab[(1, 1)] / env_counts[1] if env_counts[1] > 0 else 0.0
    env3_rvq8_frac = tab[(3, n_rvq)] / env_counts[3] if env_counts[3] > 0 else 0.0
    env1_rvq8_frac = tab[(1, n_rvq)] / env_counts[1] if env_counts[1] > 0 else 0.0
    env3_rvq1_frac = tab[(3, 1)] / env_counts[3] if env_counts[3] > 0 else 0.0

    print(f"ENV-1 at RVQ-1:     {env1_rvq1_frac*100:.1f}%")
    print(f"ENV-3 at RVQ-{n_rvq}:     {env3_rvq8_frac*100:.1f}%")
    print(f"ENV-1 at RVQ-{n_rvq}: {env1_rvq8_frac*100:.1f}% (should be low)")
    print(f"ENV-3 at RVQ-1:     {env3_rvq1_frac*100:.1f}% (should be low)")
    print()

    h1_pass = env1_rvq1_frac > 0.30
    print(f"H1: ENV-1 hub features concentrate at RVQ-1 (>30%)")
    print(f"    {env1_rvq1_frac*100:.1f}% > 30% → {'PASS' if h1_pass else 'FAIL'}")

    h2_pass = env3_rvq8_frac > 0.20
    print(f"H2: ENV-3 isolated features concentrate at RVQ-{n_rvq} (>20%)")
    print(f"    {env3_rvq8_frac*100:.1f}% > 20% → {'PASS' if h2_pass else 'FAIL'}")

    h3_pass = env1_rvq1_frac > env3_rvq1_frac * 3
    print(f"H3: ENV-1 is 3× more concentrated at RVQ-1 than ENV-3")
    print(f"    {env1_rvq1_frac*100:.1f}% vs {env3_rvq1_frac*100:.1f}% → {'PASS' if h3_pass else 'FAIL'}")

    if args.json:
        output = {
            "experiment": "Q126",
            "env_counts": {str(k): int(v) for k, v in env_counts.items()},
            "rvq_counts": {str(k): int(v) for k, v in rvq_counts.items()},
            "results": [asdict(r) for r in results],
            "env1_rvq1_frac": env1_rvq1_frac,
            "env3_rvq8_frac": env3_rvq8_frac,
            "h1": h1_pass, "h2": h2_pass, "h3": h3_pass,
        }
        print(json.dumps(output, indent=2))

    return results


def main():
    args = parse_args()
    run_experiment(args)
    print("\nQ126 complete.")
    sys.exit(0)


if __name__ == "__main__":
    main()
