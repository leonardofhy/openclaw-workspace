#!/usr/bin/env python3
"""
Q128 — jailbreak_isolate_env.py
Jailbreak Isolate shift × ENV-3 pruning: pruning ENV-3 isolated features
reduces jailbreak attack success.
Mock: 200 features × clean/jailbreak. Prune ENV-3, measure attack success change.
"""
import argparse
import json
import sys
import numpy as np
from dataclasses import dataclass, asdict
from typing import List, Dict


@dataclass
class JailbreakResult:
    condition: str
    n_pruned_env3: int
    attack_success_rate: float
    mean_isolate_score: float
    mean_gc_score: float


def parse_args():
    p = argparse.ArgumentParser(
        description="Q128: Jailbreak Isolate shift × ENV-3 pruning")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-features", type=int, default=200)
    p.add_argument("--n-stimuli", type=int, default=60)
    p.add_argument("--n-attacks", type=int, default=50)
    p.add_argument("--json", action="store_true")
    return p.parse_args()


def assign_env_types(rng, n_features):
    """ENV-1=hub(20%), ENV-2=connector(40%), ENV-3=isolated(40%)."""
    env_types = np.zeros(n_features, dtype=int)
    env_types[:int(n_features * 0.2)] = 1
    env_types[int(n_features * 0.2):int(n_features * 0.6)] = 2
    env_types[int(n_features * 0.6):] = 3
    rng.shuffle(env_types)
    return env_types


def compute_isolate_scores(rng, n_features, env_types):
    """
    ENV-3 isolated features have HIGH Isolate score (they act independently).
    Isolate score: how uniquely a feature causes output variance.
    """
    isolate = np.zeros(n_features)
    for f in range(n_features):
        env = env_types[f]
        if env == 3:    # isolated: high unique contribution
            isolate[f] = rng.uniform(0.6, 1.0)
        elif env == 2:  # connector: medium
            isolate[f] = rng.uniform(0.3, 0.6)
        else:           # hub: low (shared with many others)
            isolate[f] = rng.uniform(0.0, 0.3)
    return isolate


def simulate_attack_success(rng, activations, mask, n_attacks, jailbreak=False):
    """
    Mock attack success: jailbreak works when isolated ENV-3 features are active.
    Pruning ENV-3 (mask=False for those features) reduces attack success.
    """
    n_features, n_stimuli = activations.shape
    successes = 0

    for _ in range(n_attacks):
        # Random stimulus
        stim_idx = rng.integers(0, n_stimuli)
        feat_acts = activations[:, stim_idx].copy()

        # Apply mask (pruning = zero out masked features)
        feat_acts = feat_acts * mask

        if jailbreak:
            # Jailbreak: adds adversarial perturbation to isolated features
            adv = rng.standard_normal(n_features) * 0.5 * mask
            feat_acts += adv

        # Attack succeeds if mean activation of ENV-3-like features exceeds threshold
        # (proxy for jailbreak bypass)
        attack_strength = np.mean(np.abs(feat_acts)) + rng.standard_normal() * 0.05
        if jailbreak:
            threshold = 0.35
        else:
            threshold = 0.60  # harder without jailbreak
        successes += int(attack_strength > threshold)

    return successes / n_attacks


def generate_activations(rng, n_features, n_stimuli, env_types):
    """
    Feature activations: ENV-3 features have high variance (isolated = unique).
    """
    acts = np.zeros((n_features, n_stimuli))
    for f in range(n_features):
        env = env_types[f]
        if env == 1:    # hub: consistent high activation
            acts[f] = rng.uniform(0.6, 0.9, size=n_stimuli)
        elif env == 2:  # connector
            acts[f] = rng.uniform(0.3, 0.7, size=n_stimuli)
        else:           # isolated: high variance
            acts[f] = rng.uniform(0.0, 1.0, size=n_stimuli)
        acts[f] += rng.standard_normal(n_stimuli) * 0.05
    return acts


def run_experiment(args):
    rng = np.random.default_rng(args.seed)

    print("Q128: Jailbreak Isolate Shift × ENV-3 Pruning")
    print(f"  Features: {args.n_features}, Stimuli: {args.n_stimuli}, "
          f"Attacks: {args.n_attacks}, Seed: {args.seed}")
    print()

    env_types    = assign_env_types(rng, args.n_features)
    isolate_scrs = compute_isolate_scores(rng, args.n_features, env_types)
    activations  = generate_activations(rng, args.n_features, args.n_stimuli, env_types)

    env3_idx = np.where(env_types == 3)[0]
    n_env3   = len(env3_idx)
    print(f"Feature breakdown: ENV-1={int((env_types==1).sum())}, "
          f"ENV-2={int((env_types==2).sum())}, ENV-3={n_env3}")
    print()

    # Test conditions: no pruning, 25% prune, 50% prune, 100% prune of ENV-3
    prune_fracs = [0.0, 0.25, 0.50, 0.75, 1.0]
    results: List[JailbreakResult] = []

    print(f"{'Condition':<20} {'Pruned ENV3':>12} {'Clean ASR':>12} {'Jailbreak ASR':>14} {'ASR Δ':>8}")
    print("-" * 72)

    for frac in prune_fracs:
        n_pruned = int(frac * n_env3)
        mask = np.ones(args.n_features)

        if n_pruned > 0:
            prune_idx = rng.choice(env3_idx, size=n_pruned, replace=False)
            mask[prune_idx] = 0.0

        clean_asr    = simulate_attack_success(rng, activations, mask, args.n_attacks, jailbreak=False)
        jailbrk_asr  = simulate_attack_success(rng, activations, mask, args.n_attacks, jailbreak=True)

        mean_isolate = float(isolate_scrs[mask > 0].mean()) if mask.sum() > 0 else 0.0
        mean_gc      = float(activations[mask > 0].mean())  if mask.sum() > 0 else 0.0
        delta        = jailbrk_asr - clean_asr

        cond_name = f"prune={int(frac*100)}%"
        res = JailbreakResult(
            condition=cond_name,
            n_pruned_env3=n_pruned,
            attack_success_rate=jailbrk_asr,
            mean_isolate_score=mean_isolate,
            mean_gc_score=mean_gc,
        )
        results.append(res)
        print(f"{cond_name:<20} {n_pruned:>12} {clean_asr:>12.3f} {jailbrk_asr:>14.3f} {delta:>8.3f}")

    print()

    # Correlations
    prune_counts = np.array([r.n_pruned_env3    for r in results], dtype=float)
    asr_vals     = np.array([r.attack_success_rate for r in results])
    isolate_means = np.array([r.mean_isolate_score for r in results])

    r_prune_asr    = float(np.corrcoef(prune_counts, asr_vals)[0, 1])    if len(results) > 2 else float("nan")
    r_isolate_asr  = float(np.corrcoef(isolate_means, asr_vals)[0, 1])   if len(results) > 2 else float("nan")

    print(f"{'Correlation':<45} {'r':>8}")
    print("-" * 55)
    print(f"{'Prune count ↔ Jailbreak ASR':<45} {r_prune_asr:>8.4f}")
    print(f"{'Mean Isolate score ↔ Jailbreak ASR':<45} {r_isolate_asr:>8.4f}")
    print()

    # ASR change from no-prune to full-prune
    asr_no_prune   = results[0].attack_success_rate
    asr_full_prune = results[-1].attack_success_rate
    asr_reduction  = asr_no_prune - asr_full_prune

    print(f"Jailbreak ASR: no-prune={asr_no_prune:.3f}, full-prune={asr_full_prune:.3f}, "
          f"reduction={asr_reduction:.3f}")
    print()

    h1_pass = asr_reduction > 0.05
    print(f"H1: Pruning ENV-3 features reduces jailbreak attack success rate")
    print(f"    ASR reduction = {asr_reduction:.3f} > 0.05 → {'PASS' if h1_pass else 'FAIL'}")

    h2_pass = r_prune_asr < -0.3 if not np.isnan(r_prune_asr) else False
    print(f"H2: Prune count negatively correlates with jailbreak ASR")
    print(f"    r = {r_prune_asr:.4f} < -0.3 → {'PASS' if h2_pass else 'FAIL'}")

    h3_pass = r_isolate_asr > 0.2 if not np.isnan(r_isolate_asr) else False
    print(f"H3: Higher mean Isolate score correlates with higher jailbreak ASR")
    print(f"    r = {r_isolate_asr:.4f} > 0.2 → {'PASS' if h3_pass else 'FAIL'}")

    if args.json:
        output = {
            "experiment": "Q128",
            "results": [asdict(r) for r in results],
            "asr_reduction": asr_reduction,
            "r_prune_asr": r_prune_asr,
            "r_isolate_asr": r_isolate_asr,
            "h1": h1_pass, "h2": h2_pass, "h3": h3_pass,
        }
        print(json.dumps(output, indent=2))

    return results


def main():
    args = parse_args()
    run_experiment(args)
    print("\nQ128 complete.")
    sys.exit(0)


if __name__ == "__main__":
    main()
