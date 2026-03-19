#!/usr/bin/env python3
"""
Q117 — cascade_gsae_density.py
Cascade degree = GSAE graph density: three-metric convergence.
Mock: 200 features, build GSAE graph, measure density + cascade + AND%.
Three-way correlation.
"""
import argparse
import json
import sys
import numpy as np
from dataclasses import dataclass


@dataclass
class FeatureMetrics:
    feature_id: int
    cascade_degree: float
    and_fraction: float
    gsae_local_density: float  # fraction of neighbors with shared edges


def parse_args():
    p = argparse.ArgumentParser(description="Q117: Cascade degree ↔ GSAE graph density convergence")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-features", type=int, default=200)
    p.add_argument("--n-stimuli", type=int, default=60)
    p.add_argument("--edge-thresh", type=float, default=0.4)
    p.add_argument("--json", action="store_true")
    return p.parse_args()


def build_gsae_graph(activations, edge_thresh):
    """
    Build GSAE co-activation graph.
    Edge (i, j) exists if corr(act_i, act_j) > edge_thresh.
    """
    n_features = activations.shape[0]
    corr = np.corrcoef(activations)  # (n_features, n_features)
    adj = (corr > edge_thresh).astype(float)
    np.fill_diagonal(adj, 0)
    return adj, corr


def compute_local_density(adj):
    """
    Local density of each node = #edges / (degree * (degree-1) / 2)
    i.e., clustering coefficient approximation.
    """
    n = adj.shape[0]
    density = np.zeros(n)
    for i in range(n):
        neighbors = np.where(adj[i] > 0)[0]
        k = len(neighbors)
        if k < 2:
            density[i] = 0.0
            continue
        # Count edges among neighbors
        sub = adj[np.ix_(neighbors, neighbors)]
        edges = sub.sum() / 2
        max_edges = k * (k - 1) / 2
        density[i] = edges / max_edges if max_edges > 0 else 0.0
    return density


def compute_cascade_degree(clean, noisy):
    """cascade_degree[f] = mean(noisy[f] / clean[f])"""
    eps = 1e-6
    return np.mean(noisy / (clean + eps), axis=1)


def compute_and_fraction(clean, noisy, patched, thresh=0.3):
    n_features, n_stimuli = clean.shape
    and_frac = np.zeros(n_features)
    for f in range(n_features):
        count = 0
        for s in range(n_stimuli):
            if (clean[f, s] >= thresh and noisy[f, s] < thresh * 0.5
                    and patched[f, s] >= thresh * 0.8):
                count += 1
        and_frac[f] = count / n_stimuli
    return and_frac


def generate_data(rng, n_features, n_stimuli):
    """
    Generate mock activations where:
    - Low cascade / high AND fraction → sparse neighborhood in GSAE
    - High cascade / low AND fraction → dense neighborhood in GSAE

    Theoretical basis: AND-gate features require BOTH modalities, making
    them fragile (low cascade) but independent (sparse co-activation).
    High-cascade features activate broadly and co-activate in clusters,
    yielding dense local subgraphs in the GSAE co-activation graph.
    """
    # Latent "cascade strength" per feature
    cascade_strength = rng.uniform(0.0, 1.0, size=n_features)

    # Sort features by cascade_strength so grouping captures real structure
    sort_idx = np.argsort(cascade_strength)
    cascade_strength = cascade_strength[sort_idx]

    clean   = np.zeros((n_features, n_stimuli))
    noisy   = np.zeros((n_features, n_stimuli))
    patched = np.zeros((n_features, n_stimuli))

    for f in range(n_features):
        cs = cascade_strength[f]
        base = rng.uniform(0.5, 0.9, size=n_stimuli)
        clean[f]   = base + rng.standard_normal(n_stimuli) * 0.05
        noisy[f]   = base * (cs * 0.8 + 0.1) + rng.standard_normal(n_stimuli) * 0.05
        patched[f] = base * rng.uniform(0.85, 1.0, size=n_stimuli)

    # Add co-activation structure: group features by cascade_strength.
    # High-cascade groups get a strong shared signal → dense co-activation.
    # Low-cascade groups get weak/no shared signal → sparse co-activation.
    # The shared signal is added to BOTH clean and noisy (scaled by cs)
    # so that cascade_degree = noisy/clean still reflects cascade_strength.
    groups = 8
    group_size = n_features // groups
    for g in range(groups):
        start = g * group_size
        end   = start + group_size
        mean_cs = np.mean(cascade_strength[start:end])
        shared = rng.standard_normal(n_stimuli)
        signal_strength = mean_cs ** 2 * 0.6
        for f in range(start, end):
            cs = cascade_strength[f]
            clean[f]   += shared * signal_strength
            noisy[f]   += shared * signal_strength * (cs * 0.8 + 0.1)
            patched[f] += shared * signal_strength * 0.9

    return clean, noisy, patched, cascade_strength


def run_experiment(args):
    rng = np.random.default_rng(args.seed)

    print("Q117: Cascade Degree ↔ GSAE Graph Density Three-way Convergence")
    print(f"  Features: {args.n_features}, Stimuli: {args.n_stimuli}, "
          f"Edge thresh: {args.edge_thresh}, Seed: {args.seed}")
    print()

    clean, noisy, patched, true_cascade = generate_data(rng, args.n_features, args.n_stimuli)

    # Compute all three metrics
    cascade_degs = compute_cascade_degree(clean, noisy)
    and_fracs    = compute_and_fraction(clean, noisy, patched)
    adj, corr    = build_gsae_graph(clean, args.edge_thresh)
    local_density = compute_local_density(adj)

    global_density = float(adj.sum() / (args.n_features * (args.n_features - 1)))
    mean_degree    = float(adj.sum(axis=1).mean())

    print(f"GSAE Graph Stats:")
    print(f"  Global edge density: {global_density:.4f}")
    print(f"  Mean node degree:    {mean_degree:.2f}")
    print(f"  Mean local density:  {local_density.mean():.4f}")
    print()

    # Three-way correlations
    r_cd_and  = float(np.corrcoef(cascade_degs, and_fracs)[0, 1])
    r_cd_dens = float(np.corrcoef(cascade_degs, local_density)[0, 1])
    r_and_dens = float(np.corrcoef(and_fracs, local_density)[0, 1])
    r_true_cd  = float(np.corrcoef(true_cascade, cascade_degs)[0, 1])

    print(f"{'Correlation':<45} {'r':>8}")
    print("-" * 55)
    print(f"{'cascade_degree ↔ AND_fraction':<45} {r_cd_and:>8.4f}")
    print(f"{'cascade_degree ↔ GSAE_local_density':<45} {r_cd_dens:>8.4f}")
    print(f"{'AND_fraction   ↔ GSAE_local_density':<45} {r_and_dens:>8.4f}")
    print(f"{'true_cascade   ↔ cascade_degree':<45} {r_true_cd:>8.4f}")
    print()

    # Metric distributions
    print(f"Cascade degree:   mean={cascade_degs.mean():.3f} ± {cascade_degs.std():.3f}")
    print(f"AND fraction:     mean={and_fracs.mean():.3f} ± {and_fracs.std():.3f}")
    print(f"GSAE local dens:  mean={local_density.mean():.3f} ± {local_density.std():.3f}")
    print()

    # Hypotheses
    h1_pass = r_cd_and < -0.5
    print(f"H1: Cascade degree negatively correlated with AND-gate fraction")
    print(f"    r = {r_cd_and:.4f} < -0.5 → {'PASS' if h1_pass else 'FAIL'}")

    h2_pass = r_cd_dens > 0.3
    print(f"H2: Cascade degree positively correlated with GSAE local density")
    print(f"    r = {r_cd_dens:.4f} > 0.3 → {'PASS' if h2_pass else 'FAIL'}")

    h3_pass = r_and_dens < -0.2
    print(f"H3: AND fraction negatively correlated with GSAE local density")
    print(f"    r = {r_and_dens:.4f} < -0.2 → {'PASS' if h3_pass else 'FAIL'}")

    if args.json:
        output = {
            "experiment": "Q117",
            "global_density": global_density,
            "r_cascade_vs_and": r_cd_and,
            "r_cascade_vs_gsae_density": r_cd_dens,
            "r_and_vs_gsae_density": r_and_dens,
            "h1": h1_pass, "h2": h2_pass, "h3": h3_pass,
        }
        print(json.dumps(output, indent=2))

    return r_cd_and, r_cd_dens, r_and_dens


def main():
    args = parse_args()
    run_experiment(args)
    print("\nQ117 complete.")
    sys.exit(0)


if __name__ == "__main__":
    main()
