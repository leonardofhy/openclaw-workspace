#!/usr/bin/env python3
"""
SAE Incrimination × ENV Taxonomy — Q106
Track T5: Safety (Extension of sae_incrimination_patrol.py)

ENV taxonomy classifies persistent offender features by their network role:
  ENV-1 (Hub):      high-degree node — connected to many other features
  ENV-2 (Bridge):   bridges two clusters — moderate degree, high betweenness
  ENV-3 (Isolated): low-degree — few connections, standalone detector

Hypothesis:
  - ENV-1 hub features are most frequently incriminated (cascading blame)
  - ENV-3 isolated features are rarely incriminated (peripheral detectors)
  - ENV-2 bridge features have intermediate incrimination rates

Intervention strategies differ by ENV type:
  - ENV-1: reduce hub connectivity (prune edges)
  - ENV-2: sever bridge (disconnect clusters)
  - ENV-3: deactivate isolated node (safest, lowest collateral)

Mock: 200 features × 3 ENV types. Incrimination patrol + ENV label report.

Usage:
    python3 sae_incrimination_env_taxonomy.py
    python3 sae_incrimination_env_taxonomy.py --features 400
    python3 sae_incrimination_env_taxonomy.py --json

Dependencies: numpy only
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from typing import Dict, List

import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

N_FEATURES = 200
N_SAMPLES  = 500    # number of alert samples for patrol
TOP_K_PERSISTENT = 30   # features appearing in > this % of alerts
ALERT_RATE = 0.15   # fraction of samples that trigger an alert
SEED = 42

ENV_TYPES = ["ENV-1", "ENV-2", "ENV-3"]
ENV_DISTRIBUTION = [0.20, 0.35, 0.45]  # hubs rare, isolated common
ENV_DEGREE_PARAMS = {
    "ENV-1": (15, 3),    # mean degree=15, std=3
    "ENV-2": (7,  2),    # mean degree=7,  std=2
    "ENV-3": (2,  1),    # mean degree=2,  std=1
}
# Incrimination hit-rate per ENV type (probability feature appears in any alert)
ENV_HIT_RATE = {
    "ENV-1": 0.65,
    "ENV-2": 0.40,
    "ENV-3": 0.15,
}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FeatureRecord:
    feature_id: int
    env_type: str
    degree: int
    hit_count: int        # number of alerts this feature appeared in
    hit_rate: float       # hit_count / n_alerts
    persistent_offender: bool
    intervention: str


@dataclass
class PatrolSummary:
    n_features: int
    n_samples: int
    n_alerts: int
    persistent_offenders: int
    env_breakdown: Dict[str, Dict]


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def assign_env_types(n_features: int, rng: np.random.Generator) -> List[str]:
    """Assign ENV type to each feature according to distribution."""
    choices = rng.choice(ENV_TYPES, size=n_features, p=ENV_DISTRIBUTION)
    return list(choices)


def simulate_patrol(
    n_features: int, n_samples: int, alert_rate: float,
    env_types: List[str], rng: np.random.Generator
) -> np.ndarray:
    """
    Returns hit_counts: shape (n_features,).
    Each 'alert' selects a random subset of features, weighted by ENV hit-rate.
    """
    n_alerts = int(n_samples * alert_rate)
    hit_counts = np.zeros(n_features, dtype=int)

    hit_probs = np.array([ENV_HIT_RATE[e] for e in env_types])
    # Normalize to avoid sum > 1 per sample; each feature independently draws
    for _ in range(n_alerts):
        fires = rng.uniform(0, 1, n_features) < hit_probs
        hit_counts += fires.astype(int)

    return hit_counts, n_alerts


def intervention_for_env(env: str) -> str:
    if env == "ENV-1":
        return "Prune hub edges (reduce connectivity)"
    elif env == "ENV-2":
        return "Sever bridge (disconnect clusters)"
    else:
        return "Deactivate node (safest, isolated)"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Q106: SAE Incrimination × ENV Taxonomy — persistent offender ENV labels"
    )
    parser.add_argument("--features", type=int, default=N_FEATURES)
    parser.add_argument("--samples",  type=int, default=N_SAMPLES)
    parser.add_argument("--top-k-pct", type=float, default=0.5,
                        help="Fraction of alerts to qualify as persistent offender")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)

    env_types = assign_env_types(args.features, rng)
    hit_counts, n_alerts = simulate_patrol(
        args.features, args.samples, ALERT_RATE, env_types, rng
    )

    persistent_threshold = n_alerts * args.top_k_pct

    features: List[FeatureRecord] = []
    for f in range(args.features):
        env = env_types[f]
        degree_mean, degree_std = ENV_DEGREE_PARAMS[env]
        degree = max(1, int(rng.normal(degree_mean, degree_std)))
        hit = int(hit_counts[f])
        hr = hit / max(n_alerts, 1)
        persistent = hit >= persistent_threshold
        features.append(FeatureRecord(
            feature_id=f,
            env_type=env,
            degree=degree,
            hit_count=hit,
            hit_rate=round(hr, 4),
            persistent_offender=persistent,
            intervention=intervention_for_env(env),
        ))

    if args.as_json:
        summary = PatrolSummary(
            n_features=args.features,
            n_samples=args.samples,
            n_alerts=n_alerts,
            persistent_offenders=sum(1 for f in features if f.persistent_offender),
            env_breakdown={},
        )
        out = {
            "summary": asdict(summary),
            "features": [asdict(f) for f in features],
        }
        print(json.dumps(out, indent=2))
        return 0

    # Summary
    persistent = [f for f in features if f.persistent_offender]

    print("=" * 65)
    print("Q106 — SAE Incrimination × ENV Taxonomy")
    print(f"Config: {args.features} features × {args.samples} samples")
    print(f"Alerts: {n_alerts}  |  Persistent threshold: {persistent_threshold:.0f} hits "
          f"({args.top_k_pct*100:.0f}% of alerts)  |  seed={args.seed}")
    print("=" * 65)

    print(f"\nPersistent offenders by ENV type:")
    print(f"{'ENV Type':<12} {'Total':>7}  {'Persistent':>11}  {'Offender%':>10}  {'Mean HitRate':>13}")
    print("-" * 58)
    for env in ENV_TYPES:
        env_feats = [f for f in features if f.env_type == env]
        env_pers  = [f for f in env_feats if f.persistent_offender]
        if not env_feats:
            continue
        pct = len(env_pers) / len(env_feats) * 100
        mean_hr = np.mean([f.hit_rate for f in env_feats])
        print(f"{env:<12} {len(env_feats):>7}  {len(env_pers):>11}  {pct:>9.1f}%  {mean_hr:>13.4f}")

    print(f"\nOverall: {len(persistent)} / {args.features} features are persistent offenders")

    print(f"\nTop-10 persistent offenders:")
    top10 = sorted(persistent, key=lambda f: f.hit_rate, reverse=True)[:10]
    print(f"{'FeatID':>7} {'ENV':>6} {'Degree':>7} {'HitRate':>9} {'Intervention'}")
    print("-" * 65)
    for f in top10:
        print(f"{f.feature_id:>7} {f.env_type:>6} {f.degree:>7} "
              f"{f.hit_rate:>9.4f}  {f.intervention}")

    print(f"\nIntervention strategy summary:")
    for env in ENV_TYPES:
        env_pers = [f for f in persistent if f.env_type == env]
        if env_pers:
            print(f"  {env} ({len(env_pers)} offenders): {intervention_for_env(env)}")

    # Hypothesis check
    env1_hr = np.mean([f.hit_rate for f in features if f.env_type == "ENV-1"])
    env3_hr = np.mean([f.hit_rate for f in features if f.env_type == "ENV-3"])
    hyp_confirmed = env1_hr > env3_hr
    print(f"\nHypothesis: ENV-1 hubs > ENV-3 isolated in incrimination rate")
    print(f"  ENV-1 mean hit_rate={env1_hr:.4f}  ENV-3 mean hit_rate={env3_hr:.4f}")
    print(f"  → {'CONFIRMED' if hyp_confirmed else 'NOT CONFIRMED'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
