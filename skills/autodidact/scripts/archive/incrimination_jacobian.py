#!/usr/bin/env python3
"""
Q122 — incrimination_jacobian.py
Incrimination features × Jacobian SVD: top blame SVD directions.
Mock: 100 features × 50 dim. SVD of blame matrix. Report top singular values.
"""
import argparse
import json
import sys
import numpy as np
from dataclasses import dataclass, asdict
from typing import List


@dataclass
class SVDResult:
    rank: int
    singular_value: float
    variance_explained: float
    cumulative_variance: float
    top_feature_idx: int
    top_feature_blame: float


def parse_args():
    p = argparse.ArgumentParser(description="Q122: Incrimination features × Jacobian SVD")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-features", type=int, default=100)
    p.add_argument("--n-dim", type=int, default=50)
    p.add_argument("--n-stimuli", type=int, default=40)
    p.add_argument("--top-k", type=int, default=10)
    p.add_argument("--json", action="store_true")
    return p.parse_args()


def generate_incrimination_scores(rng, n_features, n_stimuli):
    """
    Mock incrimination scores: sparse blame matrix.
    A few features get high blame across many stimuli.
    """
    blame = rng.standard_normal((n_features, n_stimuli)) * 0.1

    # Top ~10% features are highly incriminated
    n_incriminated = max(5, n_features // 10)
    incrim_idx = rng.choice(n_features, size=n_incriminated, replace=False)

    for idx in incrim_idx:
        blame[idx] += rng.uniform(0.5, 2.0) * rng.choice([-1, 1]) * rng.uniform(0.5, 1.0, size=n_stimuli)

    return blame, incrim_idx


def generate_jacobian(rng, n_features, n_dim, incrim_idx):
    """
    Mock Jacobian: d(output) / d(features), shape (n_dim, n_features).
    Incriminated features have higher Jacobian magnitude.
    """
    J = rng.standard_normal((n_dim, n_features)) * 0.1

    # Incriminated features have structured Jacobian directions
    n_directions = min(5, len(incrim_idx))
    for k in range(n_directions):
        direction = rng.standard_normal(n_dim)
        direction /= np.linalg.norm(direction) + 1e-8
        for idx in incrim_idx:
            J[:, idx] += direction * rng.uniform(0.5, 1.5)

    return J


def compute_blame_jacobian_matrix(blame, J):
    """
    Blame-weighted Jacobian: B = J @ diag(blame_mean) shaped (n_dim, n_features).
    Then SVD to find top directions in feature space.
    """
    mean_blame = np.abs(blame).mean(axis=1)  # (n_features,)
    BJ = J * mean_blame[np.newaxis, :]       # (n_dim, n_features) broadcast
    return BJ, mean_blame


def run_experiment(args):
    rng = np.random.default_rng(args.seed)

    print("Q122: Incrimination Features × Jacobian SVD")
    print(f"  Features: {args.n_features}, Dim: {args.n_dim}, "
          f"Stimuli: {args.n_stimuli}, Top-k: {args.top_k}, Seed: {args.seed}")
    print()

    blame, incrim_idx = generate_incrimination_scores(rng, args.n_features, args.n_stimuli)
    J = generate_jacobian(rng, args.n_features, args.n_dim, incrim_idx)

    BJ, mean_blame = compute_blame_jacobian_matrix(blame, J)

    # SVD of blame-weighted Jacobian
    U, S, Vt = np.linalg.svd(BJ, full_matrices=False)

    total_var = float((S ** 2).sum())
    cumvar = 0.0
    results: List[SVDResult] = []

    print(f"{'Rank':>5} {'Singular Val':>14} {'Var Explained':>14} {'Cumulative':>12} "
          f"{'Top Feature':>12} {'Blame':>8}")
    print("-" * 70)

    for i in range(min(args.top_k, len(S))):
        var_exp = float(S[i] ** 2) / total_var
        cumvar += var_exp
        # Top feature for this SVD direction (largest absolute loading)
        top_f = int(np.argmax(np.abs(Vt[i])))
        top_blame = float(mean_blame[top_f])
        res = SVDResult(
            rank=i + 1,
            singular_value=float(S[i]),
            variance_explained=var_exp,
            cumulative_variance=cumvar,
            top_feature_idx=top_f,
            top_feature_blame=top_blame,
        )
        results.append(res)
        print(f"{res.rank:>5} {res.singular_value:>14.4f} {res.variance_explained*100:>13.2f}% "
              f"{res.cumulative_variance*100:>11.2f}% {res.top_feature_idx:>12} "
              f"{res.top_feature_blame:>8.4f}")

    print()

    # How many incriminated features appear in top SVD directions?
    top_features_set = {r.top_feature_idx for r in results}
    incrim_in_top = len(top_features_set & set(incrim_idx.tolist()))

    print(f"Incriminated features (ground truth): {len(incrim_idx)}")
    print(f"  Top-{args.top_k} SVD top-feature overlap: {incrim_in_top} / {len(top_features_set)}")

    # Blame score stats
    incrim_blame = mean_blame[incrim_idx]
    other_idx    = [i for i in range(args.n_features) if i not in incrim_idx]
    other_blame  = mean_blame[other_idx]

    print()
    print(f"Blame score — incriminated: {incrim_blame.mean():.4f} ± {incrim_blame.std():.4f}")
    print(f"Blame score — other:        {other_blame.mean():.4f} ± {other_blame.std():.4f}")

    # Singular value spectrum
    s_top1 = float(S[0])
    s_ratio = float(S[0] / S[1]) if len(S) > 1 else float("inf")
    top1_var = float(S[0] ** 2) / total_var

    print()
    print(f"Top singular value: {s_top1:.4f}  (σ₁/σ₂ = {s_ratio:.2f})")
    print(f"Variance explained by top-1: {top1_var*100:.2f}%")
    print(f"Variance explained by top-{args.top_k}: {cumvar*100:.2f}%")

    print()
    h1_pass = incrim_blame.mean() > other_blame.mean() * 2
    print(f"H1: Incriminated features have higher mean blame")
    print(f"    {incrim_blame.mean():.4f} > 2×{other_blame.mean():.4f} → {'PASS' if h1_pass else 'FAIL'}")

    h2_pass = top1_var > 0.10
    print(f"H2: Top singular value captures >10% variance")
    print(f"    {top1_var*100:.2f}% > 10% → {'PASS' if h2_pass else 'FAIL'}")

    h3_pass = incrim_in_top >= 2
    print(f"H3: At least 2 incriminated features appear in top-{args.top_k} SVD directions")
    print(f"    {incrim_in_top} ≥ 2 → {'PASS' if h3_pass else 'FAIL'}")

    if args.json:
        output = {
            "experiment": "Q122",
            "results": [asdict(r) for r in results],
            "n_incriminated": len(incrim_idx),
            "incrim_in_top_k": incrim_in_top,
            "mean_blame_incrim": float(incrim_blame.mean()),
            "mean_blame_other": float(other_blame.mean()),
            "h1": h1_pass, "h2": h2_pass, "h3": h3_pass,
        }
        print(json.dumps(output, indent=2))

    return results


def main():
    args = parse_args()
    run_experiment(args)
    print("\nQ122 complete.")
    sys.exit(0)


if __name__ == "__main__":
    main()
