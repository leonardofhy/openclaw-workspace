#!/usr/bin/env python3
"""
Temporal SAE × gc-incrimination — Q094
Track T3: Listen vs Guess

Temporal SAE (T-SAE): SAE features tracked over decoding time steps.
gc-incrimination: identify which features are causally responsible for
audio-grounding collapse.

Hypothesis: features with high temporal gc(k,t) trajectory variance are
'incriminated' — they show contrastive deactivation at collapse onset t*.

Mock: 20 time steps × 100 features.
  - Track gc(k,t) trajectories per feature
  - Identify 'incriminated' features: high variance + sharp drop near t*
  - Report top-10 incriminated features

Usage:
    python3 tsae_gc_incrimination.py
    python3 tsae_gc_incrimination.py --top-k 5
    python3 tsae_gc_incrimination.py --json

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

N_STEPS    = 20    # decoding time steps
N_FEATURES = 100
COLLAPSE_T = 12    # t* — gc collapse time step
SEED = 42
TOP_K = 10

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FeatureTrajectory:
    feature_id: int
    gc_trajectory: List[float]   # gc(k,t) at each time step
    variance: float
    drop_magnitude: float         # max drop near t*
    incrimination_score: float    # variance × drop_magnitude
    incriminated: bool


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def simulate_gc_trajectory(feature_id: int, collapse_t: int,
                            n_steps: int, rng: np.random.Generator) -> np.ndarray:
    """
    Simulate gc(k,t) trajectory for one feature.
    ~30% of features: sharp drop at collapse_t (incriminated)
    ~70%: smooth or flat trajectories (not incriminated)
    """
    t = np.arange(n_steps, dtype=float)
    noise = rng.normal(0, 0.05, n_steps)

    is_incriminated = (feature_id % 3 == 0)  # ~33% incriminated

    if is_incriminated:
        # High gc(k,t) before t*, sharp drop at t*
        gc = np.where(t < collapse_t, 0.7 + 0.1 * rng.uniform(), 0.1)
        gc += noise
    else:
        # Smooth decay or flat
        choice = feature_id % 3
        if choice == 1:
            # Gradual decay
            gc = 0.5 - 0.02 * t + noise
        else:
            # Flat baseline
            gc = rng.uniform(0.2, 0.4) + noise * 0.5

    return np.clip(gc, 0.0, 1.0)


def compute_incrimination_score(traj: np.ndarray, collapse_t: int) -> tuple:
    """Return (variance, drop_magnitude, score)."""
    variance = float(np.var(traj))

    # Drop around collapse_t: compare mean in window [t*-2,t*] vs [t*,t*+2]
    window = 2
    pre_window  = traj[max(0, collapse_t - window):collapse_t]
    post_window = traj[collapse_t:min(len(traj), collapse_t + window)]

    if len(pre_window) == 0 or len(post_window) == 0:
        drop_mag = 0.0
    else:
        drop_mag = float(pre_window.mean() - post_window.mean())
        drop_mag = max(drop_mag, 0.0)

    score = variance * drop_mag
    return variance, drop_mag, score


def run(n_steps: int, n_features: int, collapse_t: int,
        seed: int, top_k: int) -> List[FeatureTrajectory]:
    rng = np.random.default_rng(seed)
    records: List[FeatureTrajectory] = []

    for f in range(n_features):
        traj = simulate_gc_trajectory(f, collapse_t, n_steps, rng)
        var, drop_mag, score = compute_incrimination_score(traj, collapse_t)

        records.append(FeatureTrajectory(
            feature_id=f,
            gc_trajectory=list(traj.round(4)),
            variance=round(var, 5),
            drop_magnitude=round(drop_mag, 4),
            incrimination_score=round(score, 5),
            incriminated=False,  # set later
        ))

    # Mark top-k incriminated
    sorted_records = sorted(records, key=lambda r: r.incrimination_score, reverse=True)
    for rec in sorted_records[:top_k]:
        rec.incriminated = True

    return records


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Q094: T-SAE × gc-incrimination — contrastive feature deactivation"
    )
    parser.add_argument("--steps",    type=int, default=N_STEPS)
    parser.add_argument("--features", type=int, default=N_FEATURES)
    parser.add_argument("--collapse-t", type=int, default=COLLAPSE_T)
    parser.add_argument("--top-k", type=int, default=TOP_K)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    records = run(args.steps, args.features, args.collapse_t, args.seed, args.top_k)

    if args.as_json:
        print(json.dumps([asdict(r) for r in records], indent=2))
        return 0

    print("=" * 65)
    print("Q094 — Temporal SAE × gc-Incrimination")
    print(f"Config: {args.steps} time steps × {args.features} features")
    print(f"Collapse onset t*={args.collapse_t}, top-k={args.top_k}, seed={args.seed}")
    print("=" * 65)

    # Overall stats
    all_scores = [r.incrimination_score for r in records]
    print(f"\nIncrimination score stats:")
    print(f"  Mean:    {np.mean(all_scores):.5f}")
    print(f"  Std:     {np.std(all_scores):.5f}")
    print(f"  Max:     {np.max(all_scores):.5f}")
    print(f"  Min:     {np.min(all_scores):.5f}")

    # Top-k table
    incriminated = [r for r in records if r.incriminated]
    incriminated.sort(key=lambda r: r.incrimination_score, reverse=True)

    print(f"\nTop-{args.top_k} incriminated features (high variance × large drop at t*):")
    print(f"{'FeatID':>7} {'Variance':>10} {'Drop@t*':>9} {'Inc.Score':>11}")
    print("-" * 45)
    for r in incriminated:
        print(f"{r.feature_id:>7} {r.variance:>10.5f} {r.drop_magnitude:>9.4f} "
              f"{r.incrimination_score:>11.5f}")

    # Trajectory sketch for top feature
    top = incriminated[0]
    traj = top.gc_trajectory
    print(f"\ngc(k,t) trajectory for top incriminated feature (id={top.feature_id}):")
    bar_chars = [int(v * 20) for v in traj]
    for t_i, (v, bc) in enumerate(zip(traj, bar_chars)):
        marker = " ← t*" if t_i == args.collapse_t else ""
        print(f"  t={t_i:2d}: {'█' * bc:<20} {v:.3f}{marker}")

    print(f"\nConclusion: {len(incriminated)} features incriminated at t*={args.collapse_t}.")
    print("  High-score features show contrastive deactivation at collapse onset.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
