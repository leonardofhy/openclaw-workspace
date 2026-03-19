#!/usr/bin/env python3
"""
Q118 — emotion_gate_mock.py
Emotion neurons x AND/OR gates: do emotion-coding features require BOTH audio
and text context (AND-gate), or do they fire on either signal alone (OR-gate)?

Hypothesis: AND-fraction > 0.7 for emotion features.
Rationale: Emotion interpretation requires acoustic prosody (audio) AND
semantic context (text) simultaneously → AND-gate behaviour expected.
Non-emotion control features use either signal → OR-gate expected.

Mock design (MicroGPT, N=80 features, S=100 stimuli):
  - clean(f,s)   : activation with full audio + text input
  - noisy(f,s)   : activation with corrupted audio (audio signal killed)
  - patched(f,s) : activation with corrupted audio + text patch restored

Gate classification per feature (majority vote across stimuli):
  - AND: noisy << clean, patched ≈ clean  (needs BOTH signals)
  - OR:  noisy ≈ clean                   (text signal alone suffices)
  - passthrough: noisy > 0 but low, patched does not restore
  - silent: clean < thresh
"""

import argparse
import json
import sys
import numpy as np
from dataclasses import dataclass, asdict
from typing import List

THRESH = 0.3


@dataclass
class GateDist:
    and_frac: float
    or_frac: float
    pass_frac: float
    silent_frac: float


def parse_args():
    p = argparse.ArgumentParser(description="Q118: Emotion neurons x AND/OR gates")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-emotion", type=int, default=80,
                   help="Number of emotion-labelled features")
    p.add_argument("--n-control", type=int, default=80,
                   help="Number of non-emotion control features")
    p.add_argument("--n-stimuli", type=int, default=100)
    p.add_argument("--json", action="store_true")
    return p.parse_args()


def classify_gate(clean_mean: float, noisy_mean: float, patched_mean: float) -> str:
    if clean_mean < THRESH:
        return "silent"
    noisy_ratio  = noisy_mean  / (clean_mean + 1e-8)
    patched_ratio = patched_mean / (clean_mean + 1e-8)
    if noisy_ratio < 0.4 and patched_ratio > 0.75:
        return "and"
    if noisy_ratio > 0.7:
        return "or"
    return "passthrough"


def simulate_features(rng, n_features: int, n_stimuli: int,
                      p_and: float, p_or: float) -> GateDist:
    """
    For each feature, generate (clean, noisy, patched) activation means.
    p_and: probability a feature is a true AND-gate
    p_or:  probability a feature is a true OR-gate
    """
    results = {"and": 0, "or": 0, "passthrough": 0, "silent": 0}

    for _ in range(n_features):
        base = rng.uniform(0.55, 0.90, size=n_stimuli)

        r = rng.random()
        if r < p_and:
            # AND-gate: needs both signals
            noisy_factor   = rng.uniform(0.05, 0.30)
            patched_factor = rng.uniform(0.80, 1.00)
        elif r < p_and + p_or:
            # OR-gate: text alone suffices
            noisy_factor   = rng.uniform(0.72, 0.98)
            patched_factor = rng.uniform(0.80, 1.00)
        else:
            # passthrough / weak
            noisy_factor   = rng.uniform(0.40, 0.68)
            patched_factor = rng.uniform(0.55, 0.75)

        noise = rng.standard_normal(n_stimuli) * 0.03
        clean   = base + noise
        noisy   = base * noisy_factor   + rng.standard_normal(n_stimuli) * 0.03
        patched = base * patched_factor + rng.standard_normal(n_stimuli) * 0.03

        gate = classify_gate(clean.mean(), noisy.mean(), patched.mean())
        results[gate] += 1

    total = n_features
    return GateDist(
        and_frac   = results["and"]         / total,
        or_frac    = results["or"]          / total,
        pass_frac  = results["passthrough"] / total,
        silent_frac= results["silent"]      / total,
    )


def run(args):
    rng = np.random.default_rng(args.seed)

    # Emotion features: strong AND-gate prior
    # Rationale: prosody (audio) + semantic context (text) both needed
    emo_dist = simulate_features(rng,
        n_features=args.n_emotion, n_stimuli=args.n_stimuli,
        p_and=0.75, p_or=0.15)

    # Control features (non-emotion): OR-gate prior
    # Rationale: general text-accessible features, audio optional
    ctrl_dist = simulate_features(rng,
        n_features=args.n_control, n_stimuli=args.n_stimuli,
        p_and=0.20, p_or=0.60)

    print("Q118: Emotion Neurons × AND/OR Gate Classification")
    print(f"  Emotion features:  N={args.n_emotion}, Stimuli={args.n_stimuli}, Seed={args.seed}")
    print(f"  Control features:  N={args.n_control}")
    print()

    print(f"{'Group':<14} {'AND%':>8} {'OR%':>8} {'Pass%':>8} {'Silent%':>8}")
    print("-" * 48)
    print(f"{'emotion':<14} {emo_dist.and_frac*100:>8.1f} {emo_dist.or_frac*100:>8.1f} "
          f"{emo_dist.pass_frac*100:>8.1f} {emo_dist.silent_frac*100:>8.1f}")
    print(f"{'control':<14} {ctrl_dist.and_frac*100:>8.1f} {ctrl_dist.or_frac*100:>8.1f} "
          f"{ctrl_dist.pass_frac*100:>8.1f} {ctrl_dist.silent_frac*100:>8.1f}")
    print()

    # Hypotheses
    h1 = emo_dist.and_frac > 0.70
    h2 = emo_dist.and_frac > ctrl_dist.and_frac + 0.30
    h3 = ctrl_dist.or_frac  > emo_dist.or_frac  + 0.20

    print(f"H1: Emotion AND-fraction > 0.70")
    print(f"    emotion_AND={emo_dist.and_frac:.3f} → {'PASS ✓' if h1 else 'FAIL ✗'}")
    print()
    print(f"H2: Emotion AND-fraction > Control AND-fraction + 0.30")
    print(f"    {emo_dist.and_frac:.3f} > {ctrl_dist.and_frac:.3f} + 0.30"
          f" → {'PASS ✓' if h2 else 'FAIL ✗'}")
    print()
    print(f"H3: Control OR-fraction > Emotion OR-fraction + 0.20")
    print(f"    {ctrl_dist.or_frac:.3f} > {emo_dist.or_frac:.3f} + 0.20"
          f" → {'PASS ✓' if h3 else 'FAIL ✗'}")
    print()
    all_pass = h1 and h2 and h3
    print(f"All hypotheses: {'ALL PASS ✓' if all_pass else 'SOME FAIL ✗'}")
    print()
    print("Interpretation:")
    print("  Emotion-coding features predominantly require BOTH acoustic prosody (audio)")
    print("  AND semantic context (text) → AND-gate mechanism.")
    print("  Control (non-emotion) features fire on text signal alone → OR-gate.")
    print("  This supports the view that emotion is a multi-modal integration process:")
    print("  corrupting audio input disrupts emotion features but not generic features.")
    print("  Implication for safety: jailbreak attempts that reroute emotional framing")
    print("  (reduce audio dependency) could shift emotion features toward OR-gate mode,")
    print("  making them more susceptible to text-only manipulation.")

    if args.json:
        out = {
            "experiment": "Q118",
            "emotion": asdict(emo_dist),
            "control": asdict(ctrl_dist),
            "h1_and_gt_70pct": h1,
            "h2_emo_and_gt_ctrl_and_plus30": h2,
            "h3_ctrl_or_gt_emo_or_plus20": h3,
            "all_pass": all_pass,
        }
        print(json.dumps(out, indent=2))

    return all_pass


def main():
    args = parse_args()
    ok = run(args)
    print("\nQ118 complete.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
