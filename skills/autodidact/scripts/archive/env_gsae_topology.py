#!/usr/bin/env python3
"""
Q120 — env_gsae_topology.py
ENV taxonomy × GSAE topology: ENV-3 isolated = sparse graph nodes.
Mock: 200 features × 3 ENV types. Build GSAE graph. Verify topology prediction.
"""
import argparse
import json
import sys
import numpy as np
from dataclasses import dataclass, asdict
from typing import List


# ENV taxonomy:
# ENV-1: Hub features (high degree, many connections)
# ENV-2: Connector features (medium degree, bridge nodes)
# ENV-3: Isolated features (low degree, sparse connections)

@dataclass
class ENVTopologyResult:
    env_type: int
    n_features: int
    mean_degree: float
    mean_local_density: float
    mean_betweenness_proxy: float  # # of nodes reachable in 2 hops


def parse_args():
    p = argparse.ArgumentParser(description="Q120: ENV taxonomy × GSAE topology")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-features", type=int, default=200)
    p.add_argument("--n-stimuli", type=int, default=80)
    p.add_argument("--edge-thresh", type=float, default=0.35)
    p.add_argument("--json", action="store_true")
    return p.parse_args()


def assign_env_types(n_features, rng):
    """
    Assign ENV types with realistic proportions:
    ENV-1 (hub): ~20%, ENV-2 (connector): ~40%, ENV-3 (isolated): ~40%
    """
    env_types = np.zeros(n_features, dtype=int)
    env_types[:int(n_features * 0.2)] = 1   # ENV-1 hub
    env_types[int(n_features * 0.2):int(n_features * 0.6)] = 2  # ENV-2 connector
    env_types[int(n_features * 0.6):] = 3   # ENV-3 isolated
    rng.shuffle(env_types)
    return env_types


def generate_activations(rng, n_features, n_stimuli, env_types):
    """
    Generate activations with ENV-structured co-activation patterns.
    ENV-1 hubs: shared activation with many others → high correlation.
    ENV-3 isolated: unique activation patterns → low correlation.
    """
    activations = rng.standard_normal((n_features, n_stimuli))

    env1_idx = np.where(env_types == 1)[0]
    env2_idx = np.where(env_types == 2)[0]
    env3_idx = np.where(env_types == 3)[0]

    # Shared hub signal
    hub_signal = rng.standard_normal(n_stimuli)
    for idx in env1_idx:
        activations[idx] = hub_signal * rng.uniform(0.6, 1.0) + rng.standard_normal(n_stimuli) * 0.2

    # Connector signal (partially shared)
    conn_signal = rng.standard_normal(n_stimuli)
    for idx in env2_idx:
        alpha = rng.uniform(0.3, 0.6)
        activations[idx] = (alpha * hub_signal + (1 - alpha) * conn_signal
                            + rng.standard_normal(n_stimuli) * 0.3)

    # Isolated: independent noise
    for idx in env3_idx:
        activations[idx] = rng.standard_normal(n_stimuli)

    return activations


def build_gsae_graph(activations, edge_thresh):
    corr = np.corrcoef(activations)
    adj  = (corr > edge_thresh).astype(float)
    np.fill_diagonal(adj, 0)
    return adj


def two_hop_reachability(adj, node):
    """Number of nodes reachable within 2 hops."""
    neighbors1 = set(np.where(adj[node] > 0)[0])
    neighbors2 = set()
    for n in neighbors1:
        neighbors2.update(np.where(adj[n] > 0)[0])
    return len(neighbors1 | neighbors2) - (1 if node in neighbors1 | neighbors2 else 0)


def compute_local_density(adj, i):
    neighbors = np.where(adj[i] > 0)[0]
    k = len(neighbors)
    if k < 2:
        return 0.0
    sub = adj[np.ix_(neighbors, neighbors)]
    edges = sub.sum() / 2
    max_e = k * (k - 1) / 2
    return edges / max_e if max_e > 0 else 0.0


def run_experiment(args):
    rng = np.random.default_rng(args.seed)

    print("Q120: ENV Taxonomy × GSAE Topology")
    print(f"  Features: {args.n_features}, Stimuli: {args.n_stimuli}, "
          f"Edge thresh: {args.edge_thresh}, Seed: {args.seed}")
    print()

    env_types   = assign_env_types(args.n_features, rng)
    activations = generate_activations(rng, args.n_features, args.n_stimuli, env_types)
    adj         = build_gsae_graph(activations, args.edge_thresh)

    degrees      = adj.sum(axis=1)
    local_dens   = np.array([compute_local_density(adj, i) for i in range(args.n_features)])

    # Two-hop reachability for subset (expensive)
    two_hop = np.zeros(args.n_features)
    for i in range(args.n_features):
        two_hop[i] = two_hop_reachability(adj, i)

    # Aggregate by ENV type
    results: List[ENVTopologyResult] = []
    for env_t in [1, 2, 3]:
        idx = np.where(env_types == env_t)[0]
        results.append(ENVTopologyResult(
            env_type=env_t,
            n_features=len(idx),
            mean_degree=float(degrees[idx].mean()),
            mean_local_density=float(local_dens[idx].mean()),
            mean_betweenness_proxy=float(two_hop[idx].mean()),
        ))

    global_density = float(adj.sum() / (args.n_features * (args.n_features - 1)))

    print(f"GSAE Global density: {global_density:.4f}")
    print()
    print(f"{'ENV Type':<10} {'N':>4} {'Mean Degree':>12} {'Local Density':>14} {'2-Hop Reach':>12}")
    print("-" * 58)
    env_names = {1: "ENV-1 Hub", 2: "ENV-2 Conn", 3: "ENV-3 Isol"}
    for r in results:
        print(f"{env_names[r.env_type]:<10} {r.n_features:>4} "
              f"{r.mean_degree:>12.2f} {r.mean_local_density:>14.4f} "
              f"{r.mean_betweenness_proxy:>12.2f}")

    print()
    env1 = results[0]
    env3 = results[2]

    h1_pass = env1.mean_degree > env3.mean_degree * 2
    print(f"H1: ENV-1 hub degree > 2× ENV-3 isolated degree")
    print(f"    {env1.mean_degree:.2f} > 2×{env3.mean_degree:.2f}={env3.mean_degree*2:.2f} "
          f"→ {'PASS' if h1_pass else 'FAIL'}")

    h2_pass = env3.mean_degree < 5
    print(f"H2: ENV-3 isolated features have low degree (< 5)")
    print(f"    degree = {env3.mean_degree:.2f} < 5 → {'PASS' if h2_pass else 'FAIL'}")

    h3_pass = env1.mean_betweenness_proxy > env3.mean_betweenness_proxy * 1.5
    print(f"H3: ENV-1 features have higher 2-hop reachability than ENV-3")
    print(f"    {env1.mean_betweenness_proxy:.2f} > 1.5×{env3.mean_betweenness_proxy:.2f} "
          f"→ {'PASS' if h3_pass else 'FAIL'}")

    if args.json:
        output = {
            "experiment": "Q120",
            "global_density": global_density,
            "results": [asdict(r) for r in results],
            "h1": h1_pass, "h2": h2_pass, "h3": h3_pass,
        }
        print(json.dumps(output, indent=2))

    return results


def main():
    args = parse_args()
    run_experiment(args)
    print("\nQ120 complete.")
    sys.exit(0)


if __name__ == "__main__":
    main()
