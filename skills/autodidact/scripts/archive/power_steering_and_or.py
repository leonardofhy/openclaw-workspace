#!/usr/bin/env python3
"""
Q127 — power_steering_and_or.py
Power steering × AND/OR gates: top Jacobian singular vectors = effective steering
directions for AND-gate features.
Mock: 100 features × 50 dim. Compute Jacobian, SVD, correlate with gate type.
"""
import argparse
import json
import sys
import numpy as np
from dataclasses import dataclass, asdict
from typing import List


@dataclass
class SteeringResult:
    feature_id: int
    gate_type: str
    svd_alignment: float    # alignment with top singular vector
    steering_efficacy: float  # how much intervention changes activation


def parse_args():
    p = argparse.ArgumentParser(
        description="Q127: Power steering × AND/OR gate Jacobian SVD")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-features", type=int, default=100)
    p.add_argument("--n-dim", type=int, default=50)
    p.add_argument("--n-stimuli", type=int, default=60)
    p.add_argument("--top-k-svd", type=int, default=5)
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


def generate_feature_data(rng, n_features, n_stimuli):
    """Generate clean/noisy/patched activations with 50/50 AND/OR split."""
    clean   = np.zeros((n_features, n_stimuli))
    noisy   = np.zeros((n_features, n_stimuli))
    patched = np.zeros((n_features, n_stimuli))
    gate_types_true = []

    for f in range(n_features):
        base = rng.uniform(0.5, 0.85, size=n_stimuli)
        clean[f] = base + rng.standard_normal(n_stimuli) * 0.04

        if f < n_features // 2:  # AND-gate features
            gate_types_true.append("and")
            noisy[f]   = base * rng.uniform(0.03, 0.20, size=n_stimuli)
            patched[f] = base * rng.uniform(0.80, 1.00, size=n_stimuli)
        else:  # OR-gate features
            gate_types_true.append("or")
            noisy[f]   = base * rng.uniform(0.75, 0.95, size=n_stimuli)
            patched[f] = base * rng.uniform(0.85, 1.00, size=n_stimuli)

        noisy[f]   += rng.standard_normal(n_stimuli) * 0.04
        patched[f] += rng.standard_normal(n_stimuli) * 0.04

    return clean, noisy, patched, gate_types_true


def generate_jacobian(rng, n_features, n_dim, gate_types_true):
    """
    Mock Jacobian: d(output) / d(representation), shape (n_features, n_dim).
    AND-gate features have structured Jacobian (aligned with top SVD directions).
    OR-gate features have diffuse Jacobian.
    """
    J = rng.standard_normal((n_features, n_dim)) * 0.2

    # Create dominant steering directions
    n_directions = 3
    steering_dirs = []
    for k in range(n_directions):
        d = rng.standard_normal(n_dim)
        d /= np.linalg.norm(d) + 1e-8
        steering_dirs.append(d)

    # AND-gate features align with steering directions
    for f, g in enumerate(gate_types_true):
        if g == "and":
            k = f % n_directions
            strength = rng.uniform(0.8, 1.5)
            J[f] += steering_dirs[k] * strength
        else:  # OR-gate: diffuse
            J[f] += rng.standard_normal(n_dim) * 0.3

    return J


def compute_steering_efficacy(J, U_top, clean, patched):
    """
    Steering efficacy: how much does projecting onto top SVD direction
    and steering in that direction change the feature activation?
    Approximation: magnitude of J @ u_top per feature.
    """
    n_features, n_dim = J.shape
    efficacy = np.zeros(n_features)
    for f in range(n_features):
        efficacy[f] = abs(np.dot(J[f], U_top))
    return efficacy


def run_experiment(args):
    rng = np.random.default_rng(args.seed)

    print("Q127: Power Steering × AND/OR Gate Jacobian SVD")
    print(f"  Features: {args.n_features}, Dim: {args.n_dim}, "
          f"Stimuli: {args.n_stimuli}, Top-k SVD: {args.top_k_svd}, Seed: {args.seed}")
    print()

    clean, noisy, patched, gate_types_true = generate_feature_data(
        rng, args.n_features, args.n_stimuli)
    J = generate_jacobian(rng, args.n_features, args.n_dim, gate_types_true)

    # SVD of Jacobian
    # Shape: J is (n_features, n_dim) → SVD gives U (n_features × k), S, Vt (k × n_dim)
    U, S, Vt = np.linalg.svd(J, full_matrices=False)

    top_k = args.top_k_svd
    top_singular_vals = S[:top_k]
    top_right_vecs    = Vt[:top_k]  # steering directions in representation space

    total_var = float((S ** 2).sum())

    print(f"Jacobian SVD Top-{top_k} Singular Values:")
    print(f"{'Rank':>5} {'Singular Val':>14} {'Var%':>8} {'CumVar%':>10}")
    print("-" * 42)
    cumvar = 0.0
    for i in range(top_k):
        var_pct = (S[i] ** 2 / total_var) * 100
        cumvar += var_pct
        print(f"{i+1:>5} {S[i]:>14.4f} {var_pct:>8.2f} {cumvar:>10.2f}")

    print()

    # SVD alignment per feature: project each feature's Jacobian onto top-1 right vector
    top_right = Vt[0]  # (n_dim,)
    # Feature alignment = |J[f] @ v_1| / ||J[f]||
    J_norms = np.linalg.norm(J, axis=1) + 1e-8
    alignments = np.abs(J @ top_right) / J_norms  # (n_features,)

    # Steering efficacy = |J[f] @ v_1| (raw projection)
    efficacy = np.abs(J @ top_right)

    # Classify gates from data
    gate_types_obs = []
    for f in range(args.n_features):
        per_stim = []
        for s in range(args.n_stimuli):
            g = classify_gate(clean[f, s], noisy[f, s], patched[f, s])
            per_stim.append(g)
        majority = max(set(per_stim), key=per_stim.count)
        gate_types_obs.append(majority)

    results: List[SteeringResult] = []
    for f in range(args.n_features):
        results.append(SteeringResult(
            feature_id=f,
            gate_type=gate_types_obs[f],
            svd_alignment=float(alignments[f]),
            steering_efficacy=float(efficacy[f]),
        ))

    # Compare AND vs OR gate alignment
    and_results = [r for r in results if r.gate_type == "and"]
    or_results  = [r for r in results if r.gate_type == "or"]

    and_align = np.mean([r.svd_alignment    for r in and_results]) if and_results else 0.0
    or_align  = np.mean([r.svd_alignment    for r in or_results])  if or_results  else 0.0
    and_eff   = np.mean([r.steering_efficacy for r in and_results]) if and_results else 0.0
    or_eff    = np.mean([r.steering_efficacy for r in or_results])  if or_results  else 0.0

    print(f"{'Gate Type':<12} {'N':>4} {'Mean Alignment':>16} {'Mean Efficacy':>14}")
    print("-" * 50)
    print(f"{'AND-gate':<12} {len(and_results):>4} {and_align:>16.4f} {and_eff:>14.4f}")
    print(f"{'OR-gate':<12}  {len(or_results):>4} {or_align:>16.4f} {or_eff:>14.4f}")
    print()

    # Correlation: gate_type (binary) with alignment
    gate_binary = np.array([1.0 if r.gate_type == "and" else 0.0 for r in results])
    r_gate_align = float(np.corrcoef(gate_binary, alignments)[0, 1])
    r_gate_eff   = float(np.corrcoef(gate_binary, efficacy)[0, 1])

    print(f"{'Correlation':<40} {'r':>8}")
    print("-" * 50)
    print(f"{'AND-gate indicator ↔ SVD alignment':<40} {r_gate_align:>8.4f}")
    print(f"{'AND-gate indicator ↔ steering efficacy':<40} {r_gate_eff:>8.4f}")
    print()

    h1_pass = and_align > or_align
    print(f"H1: AND-gate features align more with top SVD direction")
    print(f"    AND={and_align:.4f} > OR={or_align:.4f} → {'PASS' if h1_pass else 'FAIL'}")

    h2_pass = and_eff > or_eff
    print(f"H2: AND-gate features have higher steering efficacy")
    print(f"    AND={and_eff:.4f} > OR={or_eff:.4f} → {'PASS' if h2_pass else 'FAIL'}")

    h3_pass = r_gate_align > 0.2
    print(f"H3: Positive correlation between AND-gate status and SVD alignment")
    print(f"    r = {r_gate_align:.4f} > 0.2 → {'PASS' if h3_pass else 'FAIL'}")

    if args.json:
        output = {
            "experiment": "Q127",
            "top_singular_values": top_singular_vals.tolist(),
            "and_mean_alignment": and_align,
            "or_mean_alignment":  or_align,
            "r_gate_alignment": r_gate_align,
            "h1": h1_pass, "h2": h2_pass, "h3": h3_pass,
        }
        print(json.dumps(output, indent=2))

    return results


def main():
    args = parse_args()
    run_experiment(args)
    print("\nQ127 complete.")
    sys.exit(0)


if __name__ == "__main__":
    main()
