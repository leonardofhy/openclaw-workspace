#!/usr/bin/env python3
"""
Q125 — schelling_tsae.py
Schelling stability × T-SAE: IIA-stable features = temporally consistent.
Mock: 3 seeds × 20 time steps × 100 features. Correlate temporal consistency with IIA.
"""
import argparse
import json
import sys
import numpy as np
from dataclasses import dataclass, asdict
from typing import List


@dataclass
class FeatureStabilityResult:
    feature_id: int
    iia_stability: float         # IIA across seeds (0=unstable, 1=perfectly stable)
    temporal_consistency: float  # consistency across time steps within seed
    tsae_score: float            # temporal SAE score (consistency × stability)


def parse_args():
    p = argparse.ArgumentParser(description="Q125: Schelling stability × T-SAE temporal consistency")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-seeds", type=int, default=3)
    p.add_argument("--n-timesteps", type=int, default=20)
    p.add_argument("--n-features", type=int, default=100)
    p.add_argument("--json", action="store_true")
    return p.parse_args()


def generate_feature_trajectories(n_seeds, n_timesteps, n_features, master_rng):
    """
    Generate feature activation trajectories.
    IIA-stable features: same activation pattern across seeds.
    Temporally consistent features: smooth trajectory across time.
    """
    # Ground truth stability per feature
    true_stability = master_rng.uniform(0.0, 1.0, size=n_features)

    trajectories = np.zeros((n_seeds, n_timesteps, n_features))

    # Base trajectory (seed-independent)
    base_traj = np.zeros((n_timesteps, n_features))
    for f in range(n_features):
        # Smooth trajectory: sinusoidal + trend
        t = np.linspace(0, 2 * np.pi, n_timesteps)
        base_traj[:, f] = (0.5 + 0.3 * np.sin(t + master_rng.uniform(0, 2 * np.pi))
                           + master_rng.uniform(-0.1, 0.1) * t / n_timesteps)

    for seed_idx in range(n_seeds):
        seed_rng = np.random.default_rng(master_rng.integers(0, 10000))
        for f in range(n_features):
            stab = true_stability[f]
            # Stable features: low perturbation across seeds
            noise_scale = (1.0 - stab) * 0.5
            seed_noise  = seed_rng.standard_normal(n_timesteps) * noise_scale
            # Temporal noise: stable features = smooth
            temporal_noise_scale = (1.0 - stab) * 0.3
            temporal_noise = seed_rng.standard_normal(n_timesteps) * temporal_noise_scale

            trajectories[seed_idx, :, f] = base_traj[:, f] + seed_noise + temporal_noise

    return trajectories, true_stability, base_traj


def compute_iia_stability(trajectories):
    """
    IIA (Interchange Intervention Accuracy) stability:
    How consistent is the mean activation pattern across seeds?
    Computed as 1 - (std across seeds) / (mean abs activation + eps).
    """
    n_seeds, n_timesteps, n_features = trajectories.shape
    eps = 1e-6
    iia = np.zeros(n_features)
    for f in range(n_features):
        traj_f = trajectories[:, :, f]  # (n_seeds, n_timesteps)
        mean_act = np.abs(traj_f).mean()
        std_across_seeds = traj_f.std(axis=0).mean()  # std at each timestep, averaged
        iia[f] = max(0.0, 1.0 - std_across_seeds / (mean_act + eps))
    return iia


def compute_temporal_consistency(trajectories):
    """
    Temporal consistency: how smooth is the trajectory?
    Computed as 1 - mean(|diff(traj)|) / (std(traj) + eps).
    Averaged across seeds.
    """
    n_seeds, n_timesteps, n_features = trajectories.shape
    consistency = np.zeros(n_features)
    for f in range(n_features):
        seed_consistencies = []
        for s in range(n_seeds):
            traj = trajectories[s, :, f]
            roughness = np.abs(np.diff(traj)).mean()
            variability = traj.std() + 1e-6
            seed_consistencies.append(max(0.0, 1.0 - roughness / variability))
        consistency[f] = np.mean(seed_consistencies)
    return consistency


def run_experiment(args):
    rng = np.random.default_rng(args.seed)

    print("Q125: Schelling Stability × T-SAE Temporal Consistency")
    print(f"  Seeds: {args.n_seeds}, Timesteps: {args.n_timesteps}, "
          f"Features: {args.n_features}, Seed: {args.seed}")
    print()

    trajectories, true_stability, base_traj = generate_feature_trajectories(
        args.n_seeds, args.n_timesteps, args.n_features, rng)

    iia          = compute_iia_stability(trajectories)
    temporal_con = compute_temporal_consistency(trajectories)
    tsae_scores  = iia * temporal_con  # joint T-SAE score

    results: List[FeatureStabilityResult] = []
    for f in range(args.n_features):
        results.append(FeatureStabilityResult(
            feature_id=f,
            iia_stability=float(iia[f]),
            temporal_consistency=float(temporal_con[f]),
            tsae_score=float(tsae_scores[f]),
        ))

    # Correlations
    r_iia_temp = float(np.corrcoef(iia, temporal_con)[0, 1])
    r_true_iia = float(np.corrcoef(true_stability, iia)[0, 1])
    r_true_tmp = float(np.corrcoef(true_stability, temporal_con)[0, 1])

    print(f"{'Correlation':<45} {'r':>8}")
    print("-" * 55)
    print(f"{'IIA stability ↔ Temporal consistency':<45} {r_iia_temp:>8.4f}")
    print(f"{'True stability ↔ IIA':<45} {r_true_iia:>8.4f}")
    print(f"{'True stability ↔ Temporal consistency':<45} {r_true_tmp:>8.4f}")
    print()

    # Distribution summary
    print(f"IIA stability:        mean={iia.mean():.3f} ± {iia.std():.3f}")
    print(f"Temporal consistency: mean={temporal_con.mean():.3f} ± {temporal_con.std():.3f}")
    print(f"T-SAE score:          mean={tsae_scores.mean():.3f} ± {tsae_scores.std():.3f}")
    print()

    # Quartile analysis
    q75 = np.percentile(iia, 75)
    q25 = np.percentile(iia, 25)
    high_iia  = temporal_con[iia >= q75].mean()
    low_iia   = temporal_con[iia <= q25].mean()
    print(f"Temporal consistency — high IIA (Q4): {high_iia:.3f}")
    print(f"Temporal consistency — low  IIA (Q1): {low_iia:.3f}")

    print()
    h1_pass = r_iia_temp > 0.3
    print(f"H1: IIA-stable features are temporally consistent")
    print(f"    r(IIA, temporal) = {r_iia_temp:.4f} > 0.3 → {'PASS' if h1_pass else 'FAIL'}")

    h2_pass = high_iia > low_iia
    print(f"H2: High-IIA features have higher temporal consistency than low-IIA")
    print(f"    {high_iia:.3f} > {low_iia:.3f} → {'PASS' if h2_pass else 'FAIL'}")

    h3_pass = r_true_iia > 0.5
    print(f"H3: True stability correlates with IIA (sanity check)")
    print(f"    r = {r_true_iia:.4f} > 0.5 → {'PASS' if h3_pass else 'FAIL'}")

    # Top stable features
    top_stable = sorted(results, key=lambda r: r.tsae_score, reverse=True)[:5]
    print()
    print("Top-5 most T-SAE stable features:")
    print(f"{'FeatID':>6} {'IIA':>8} {'TempCon':>10} {'TSAE':>8}")
    for r in top_stable:
        print(f"{r.feature_id:>6} {r.iia_stability:>8.4f} {r.temporal_consistency:>10.4f} "
              f"{r.tsae_score:>8.4f}")

    if args.json:
        output = {
            "experiment": "Q125",
            "r_iia_temporal": r_iia_temp,
            "r_true_iia": r_true_iia,
            "h1": h1_pass, "h2": h2_pass, "h3": h3_pass,
            "results": [asdict(r) for r in results],
        }
        print(json.dumps(output, indent=2))

    return results


def main():
    args = parse_args()
    run_experiment(args)
    print("\nQ125 complete.")
    sys.exit(0)


if __name__ == "__main__":
    main()
