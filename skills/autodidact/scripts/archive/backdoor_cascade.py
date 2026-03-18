#!/usr/bin/env python3
"""
Q116 — backdoor_cascade.py
Backdoor = cascade induction: t* leftward shift as universal backdoor signature.
Mock: 100 features × clean/backdoor. Measure t* shift.
"""
import argparse
import json
import sys
import numpy as np
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class BackdoorResult:
    feature_id: int
    t_star_clean: Optional[int]
    t_star_backdoor: Optional[int]
    t_star_shift: int   # negative = leftward (earlier) collapse
    backdoor_induced: bool


def parse_args():
    p = argparse.ArgumentParser(description="Q116: Backdoor cascade induction via t* shift")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-features", type=int, default=100)
    p.add_argument("--n-steps", type=int, default=10)
    p.add_argument("--n-stimuli", type=int, default=40)
    p.add_argument("--tau", type=float, default=0.35, help="gc threshold for t* detection")
    p.add_argument("--json", action="store_true")
    return p.parse_args()


def generate_gc_trajectories(rng, n_features, n_stimuli, n_steps, backdoor=False):
    """
    Mock gc(k, t) trajectories: n_features × n_stimuli × n_steps.
    Clean: gc stays high until late steps.
    Backdoor: gc collapses earlier (leftward t* shift).
    """
    trajs = np.zeros((n_features, n_stimuli, n_steps))

    for f in range(n_features):
        for s in range(n_stimuli):
            # Base: gc starts ~0.7, decays gently
            base_gc = rng.uniform(0.6, 0.85)
            decay_rate = rng.uniform(0.03, 0.10)

            # Collapse point
            if backdoor and rng.random() < 0.7:
                # Backdoor: earlier collapse
                collapse_step = rng.integers(2, n_steps // 2)
            else:
                # Clean: later collapse (or no collapse)
                collapse_step = rng.integers(n_steps // 2, n_steps + 1)

            for t in range(n_steps):
                val = base_gc - decay_rate * t
                if t >= collapse_step:
                    val -= rng.uniform(0.3, 0.5) * (t - collapse_step + 1)
                trajs[f, s, t] = np.clip(val + rng.standard_normal() * 0.03, 0.0, 1.0)

    return trajs


def detect_t_star(traj, tau):
    """First timestep where gc drops below tau. Returns None if never drops."""
    for t, val in enumerate(traj):
        if val < tau:
            return t
    return None


def compute_t_star_per_feature(trajs, tau):
    """Median t* across stimuli for each feature."""
    n_features, n_stimuli, n_steps = trajs.shape
    t_stars = []
    for f in range(n_features):
        per_stim = []
        for s in range(n_stimuli):
            ts = detect_t_star(trajs[f, s], tau)
            if ts is not None:
                per_stim.append(ts)
        if per_stim:
            t_stars.append(int(np.median(per_stim)))
        else:
            t_stars.append(None)
    return t_stars


def run_experiment(args):
    rng = np.random.default_rng(args.seed)

    print("Q116: Backdoor Cascade Induction — t* Leftward Shift")
    print(f"  Features: {args.n_features}, Steps: {args.n_steps}, "
          f"Stimuli: {args.n_stimuli}, τ: {args.tau}, Seed: {args.seed}")
    print()

    trajs_clean    = generate_gc_trajectories(rng, args.n_features, args.n_stimuli,
                                               args.n_steps, backdoor=False)
    trajs_backdoor = generate_gc_trajectories(rng, args.n_features, args.n_stimuli,
                                               args.n_steps, backdoor=True)

    t_stars_clean    = compute_t_star_per_feature(trajs_clean, args.tau)
    t_stars_backdoor = compute_t_star_per_feature(trajs_backdoor, args.tau)

    results = []
    for f in range(args.n_features):
        tc = t_stars_clean[f]
        tb = t_stars_backdoor[f]
        if tc is not None and tb is not None:
            shift = tb - tc
        elif tc is None and tb is not None:
            shift = -args.n_steps  # very early collapse
        else:
            shift = 0
        results.append(BackdoorResult(
            feature_id=f,
            t_star_clean=tc,
            t_star_backdoor=tb,
            t_star_shift=shift,
            backdoor_induced=(shift < -1),
        ))

    # Aggregate stats
    shifts = np.array([r.t_star_shift for r in results])
    induced_count = sum(r.backdoor_induced for r in results)

    t_clean_valid    = [r.t_star_clean    for r in results if r.t_star_clean is not None]
    t_backdoor_valid = [r.t_star_backdoor for r in results if r.t_star_backdoor is not None]

    mean_tc = np.mean(t_clean_valid)    if t_clean_valid    else float("nan")
    mean_tb = np.mean(t_backdoor_valid) if t_backdoor_valid else float("nan")

    print(f"{'Condition':<20} {'Mean t*':>10} {'Std t*':>10} {'N valid':>8}")
    print("-" * 52)
    print(f"{'Clean':<20} {mean_tc:>10.3f} {np.std(t_clean_valid):>10.3f} "
          f"{len(t_clean_valid):>8}")
    print(f"{'Backdoor':<20} {mean_tb:>10.3f} {np.std(t_backdoor_valid):>10.3f} "
          f"{len(t_backdoor_valid):>8}")
    print()

    mean_shift = float(np.mean(shifts))
    print(f"Mean t* shift (backdoor - clean): {mean_shift:.3f} steps")
    print(f"Features with leftward shift (shift < -1): {induced_count}/{args.n_features} "
          f"({100*induced_count/args.n_features:.1f}%)")
    print()

    h1_pass = mean_shift < -1.0
    print(f"H1: Backdoor induces leftward t* shift (earlier collapse)")
    print(f"    Mean shift = {mean_shift:.3f} < -1.0 → {'PASS' if h1_pass else 'FAIL'}")

    h2_pass = induced_count / args.n_features > 0.5
    print(f"H2: Majority of features show backdoor cascade induction")
    print(f"    Fraction = {induced_count/args.n_features:.3f} > 0.5 → {'PASS' if h2_pass else 'FAIL'}")

    # Show worst-affected features
    worst = sorted(results, key=lambda r: r.t_star_shift)[:5]
    print()
    print("Top-5 most backdoor-affected features:")
    print(f"{'FeatID':>6} {'t*_clean':>10} {'t*_back':>10} {'Shift':>8}")
    for r in worst:
        tc_s = str(r.t_star_clean)  if r.t_star_clean  is not None else "None"
        tb_s = str(r.t_star_backdoor) if r.t_star_backdoor is not None else "None"
        print(f"{r.feature_id:>6} {tc_s:>10} {tb_s:>10} {r.t_star_shift:>8}")

    if args.json:
        output = {
            "experiment": "Q116",
            "mean_t_star_clean": mean_tc,
            "mean_t_star_backdoor": mean_tb,
            "mean_shift": mean_shift,
            "backdoor_induced_fraction": induced_count / args.n_features,
            "h1_pass": h1_pass,
            "h2_pass": h2_pass,
        }
        print(json.dumps(output, indent=2))

    return results


def main():
    args = parse_args()
    run_experiment(args)
    print("\nQ116 complete.")
    sys.exit(0)


if __name__ == "__main__":
    main()
