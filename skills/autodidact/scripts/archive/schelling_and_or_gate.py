#!/usr/bin/env python3
"""
Schelling Features × AND/OR Gates — Q092
Track T3: Listen vs Guess

Hypothesis: cross-seed-stable SAE features (Schelling points) are more likely
to be AND-gates. Stable features represent robust, causally essential detectors
for audio content — exactly the conjunctive integration pattern of AND-gates.

Mock: 3 seeds × 200 features.
  - Schelling stability = cosine similarity of feature vectors across seeds
  - Gate type = AND / OR / Passthrough from denoising protocol
  - Correlation: stability score vs AND-gate probability

Usage:
    python3 schelling_and_or_gate.py
    python3 schelling_and_or_gate.py --seeds 5
    python3 schelling_and_or_gate.py --json

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

N_FEATURES = 200
N_SEEDS = 3
D_MODEL = 16         # feature vector dimension for cosine similarity
N_STIMULI = 60
GC_PEAK_LAYER = 3
N_LAYERS = 8
SEED = 42

ACT_THRESHOLD = 0.5
RECOVERY_FRAC = 0.4

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FeatureEntry:
    feature_id: int
    stability_score: float    # mean pairwise cosine similarity across seeds
    gate_type: str
    and_flag: int             # 1=AND, 0=other


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a); nb = np.linalg.norm(b)
    if na < 1e-9 or nb < 1e-9:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def compute_stability(feature_vecs: List[np.ndarray]) -> float:
    """Mean pairwise cosine similarity across seed runs."""
    n = len(feature_vecs)
    sims = []
    for i in range(n):
        for j in range(i + 1, n):
            sims.append(cosine_sim(feature_vecs[i], feature_vecs[j]))
    return float(np.mean(sims)) if sims else 0.0


def classify_gate(clean: float, noisy: float, patched: float) -> str:
    if clean <= ACT_THRESHOLD:
        return "Silent"
    drop = (clean - noisy) / (clean + 1e-8)
    if drop < 0.2:
        return "OR"
    rec = (patched - noisy) / (clean - noisy + 1e-8) if (clean - noisy) > 0.05 else 0.0
    return "AND" if rec >= RECOVERY_FRAC else "Passthrough"


def pearson_r(x: np.ndarray, y: np.ndarray) -> float:
    xm = x - x.mean(); ym = y - y.mean()
    denom = np.sqrt((xm ** 2).sum() * (ym ** 2).sum())
    return float(np.dot(xm, ym) / (denom + 1e-12))


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def run(n_features: int, n_seeds: int, seed: int) -> List[FeatureEntry]:
    rng = np.random.default_rng(seed)

    # For each feature, assign a "true stability level" (0..1)
    # High-stability features will have consistent vectors and AND-gate tendency
    true_stability = rng.uniform(0.0, 1.0, n_features)

    # Simulate per-seed feature vectors
    # Stable features → vectors close across seeds; unstable → noisy
    all_vecs: List[List[np.ndarray]] = []
    for f in range(n_features):
        base_vec = rng.normal(0, 1, D_MODEL)
        base_vec /= np.linalg.norm(base_vec) + 1e-9
        seed_vecs = []
        for _ in range(n_seeds):
            noise_scale = 1.0 - true_stability[f]  # low stability → more noise
            noise = rng.normal(0, noise_scale * 0.5, D_MODEL)
            v = base_vec + noise
            v /= np.linalg.norm(v) + 1e-9
            seed_vecs.append(v)
        all_vecs.append(seed_vecs)

    # Compute measured stability scores
    stability_scores = np.array([compute_stability(all_vecs[f]) for f in range(n_features)])

    # Simulate gate classification at gc peak layer
    # AND-gate probability scales with true_stability (with noise)
    entries: List[FeatureEntry] = []
    for f in range(n_features):
        stab = true_stability[f]
        # AND-gate if stability > threshold (with some noise)
        p_and = 0.2 + 0.6 * stab  # 0.2..0.8
        p_or  = 0.5 * (1.0 - stab)
        rand_u = rng.uniform()
        if rand_u < p_and:
            gate = "AND"
        elif rand_u < p_and + p_or:
            gate = "OR"
        else:
            gate = "Passthrough"
        entries.append(FeatureEntry(
            feature_id=f,
            stability_score=round(float(stability_scores[f]), 4),
            gate_type=gate,
            and_flag=1 if gate == "AND" else 0,
        ))

    return entries


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Q092: Schelling Features × AND/OR Gates — stability vs gate correlation"
    )
    parser.add_argument("--seeds", type=int, default=N_SEEDS)
    parser.add_argument("--features", type=int, default=N_FEATURES)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    entries = run(args.features, args.seeds, args.seed)

    if args.as_json:
        print(json.dumps([asdict(e) for e in entries], indent=2))
        return 0

    # Statistics
    stab = np.array([e.stability_score for e in entries])
    and_flags = np.array([e.and_flag for e in entries])
    r = pearson_r(stab, and_flags.astype(float))

    gate_counts = {g: sum(1 for e in entries if e.gate_type == g)
                   for g in ["AND", "OR", "Passthrough"]}

    # Split into stable (top-50%) vs unstable (bottom-50%)
    median_stab = float(np.median(stab))
    stable_entries   = [e for e in entries if e.stability_score >= median_stab]
    unstable_entries = [e for e in entries if e.stability_score <  median_stab]

    stable_and_pct   = sum(e.and_flag for e in stable_entries)   / len(stable_entries)   * 100
    unstable_and_pct = sum(e.and_flag for e in unstable_entries) / len(unstable_entries) * 100

    print("=" * 60)
    print("Q092 — Schelling Features × AND/OR Gates")
    print(f"Config: {args.features} features × {args.seeds} seeds, seed={args.seed}")
    print("=" * 60)

    print(f"\nOverall gate distribution ({args.features} features):")
    for g, c in gate_counts.items():
        print(f"  {g:<12} {c:>4}  ({c/args.features*100:.1f}%)")

    print(f"\nStability split (median={median_stab:.3f}):")
    print(f"  {'Group':<12} {'N':>5}  {'AND%':>7}")
    print(f"  {'stable':<12} {len(stable_entries):>5}  {stable_and_pct:>7.1f}%")
    print(f"  {'unstable':<12} {len(unstable_entries):>5}  {unstable_and_pct:>7.1f}%")

    print(f"\nPearson r(stability, AND-flag) = {r:.4f}")

    confirmed = stable_and_pct > unstable_and_pct and r > 0.2
    print(f"\nHypothesis: stable features → AND-gates  → {'CONFIRMED' if confirmed else 'NOT CONFIRMED'}")
    print(f"  Stable AND%={stable_and_pct:.1f}%  Unstable AND%={unstable_and_pct:.1f}%")

    return 0


if __name__ == "__main__":
    sys.exit(main())
