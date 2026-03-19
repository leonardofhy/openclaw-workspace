#!/usr/bin/env python3
"""
FAD Bias × AND/OR Gate — Q096
Track T3: Listen vs Guess

FAD (Feature Attribution Decomposition) bias hypothesis:
  - Text-predictable phonemes rely on language prior → OR-gate features
    (context alone can substitute for audio)
  - Audio-dependent / acoustic-only phonemes require actual audio → AND-gate
    features (conjunctive integration required)

Mock: 30 phonemes × 100 features.
  Phonemes labelled text-predictable (high LM prior) vs acoustic-only (low LM prior).
  Compare AND/OR gate ratio between groups.

Usage:
    python3 fad_and_or_gate.py
    python3 fad_and_or_gate.py --phonemes 40
    python3 fad_and_or_gate.py --json

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

N_PHONEMES  = 30
N_FEATURES  = 100
SEED = 42

ACT_THRESHOLD = 0.5
RECOVERY_FRAC  = 0.4

# Representative phoneme inventory with text-predictability labels
# text_pred_prob: probability phoneme is text-predictable (high LM prior)
PHONEME_SET = [
    ("th",  0.90),  # very common, highly predictable from context
    ("the", 0.92),
    ("s",   0.85),
    ("n",   0.83),
    ("t",   0.82),
    ("r",   0.80),
    ("l",   0.78),
    ("a",   0.75),
    ("e",   0.74),
    ("d",   0.72),
    ("i",   0.70),
    ("o",   0.68),
    ("m",   0.65),
    ("ng",  0.62),
    ("w",   0.60),
    ("v",   0.55),
    ("b",   0.52),
    ("f",   0.50),
    ("h",   0.47),
    ("k",   0.44),
    ("p",   0.42),
    ("g",   0.38),
    ("dh",  0.35),
    ("sh",  0.30),
    ("ch",  0.28),
    ("zh",  0.22),
    ("jh",  0.20),
    ("z",   0.18),
    ("aw",  0.12),   # diphthong — acoustic, harder to predict from text
    ("er",  0.10),   # rhotic vowel — highly acoustic-dependent
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PhonemeGateResult:
    phoneme: str
    text_pred_prob: float
    text_predictable: bool    # True if text_pred_prob > 0.5
    n_features: int
    and_pct: float
    or_pct: float
    pass_pct: float
    dominant_gate: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
    denom = np.sqrt((xm**2).sum() * (ym**2).sum())
    return float(np.dot(xm, ym) / (denom + 1e-12))


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def simulate_phoneme(phoneme: str, text_pred_prob: float,
                     n_features: int, rng: np.random.Generator) -> PhonemeGateResult:
    """
    For text-predictable phonemes: OR-gate probability scales with text_pred_prob.
    For acoustic-only phonemes: AND-gate probability scales with (1 - text_pred_prob).
    """
    gate_counts = {"AND": 0, "OR": 0, "Passthrough": 0, "Silent": 0}

    for _ in range(n_features):
        # Context fill-in probability: high for text-predictable phonemes
        ctx_fill = text_pred_prob * 0.5 + 0.1

        # Audio signal strength: high for acoustic-only phonemes
        audio_strength = (1.0 - text_pred_prob) * 0.6 + 0.1

        clean   = rng.normal(audio_strength + ctx_fill, 0.15)
        noisy   = rng.normal(ctx_fill + 0.1, 0.15)          # audio removed
        patched = rng.normal(audio_strength * 0.8 + ctx_fill, 0.15)  # partial recovery

        gt = classify_gate(max(clean, 0), max(noisy, 0), max(patched, 0))
        gate_counts[gt] += 1

    total = n_features
    dominant = max(["AND", "OR", "Passthrough"], key=lambda g: gate_counts[g])
    return PhonemeGateResult(
        phoneme=phoneme,
        text_pred_prob=text_pred_prob,
        text_predictable=text_pred_prob > 0.5,
        n_features=n_features,
        and_pct=round(gate_counts["AND"] / total * 100, 1),
        or_pct=round(gate_counts["OR"] / total * 100, 1),
        pass_pct=round(gate_counts["Passthrough"] / total * 100, 1),
        dominant_gate=dominant,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Q096: FAD Bias × AND/OR Gate — text-predictable phonemes vs acoustic-only"
    )
    parser.add_argument("--phonemes", type=int, default=N_PHONEMES,
                        help="Number of phonemes to use (up to 30)")
    parser.add_argument("--features", type=int, default=N_FEATURES)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    n_ph = min(args.phonemes, len(PHONEME_SET))
    phonemes_used = PHONEME_SET[:n_ph]

    results: List[PhonemeGateResult] = []
    for ph, prob in phonemes_used:
        r = simulate_phoneme(ph, prob, args.features, rng)
        results.append(r)

    if args.as_json:
        print(json.dumps([asdict(r) for r in results], indent=2))
        return 0

    print("=" * 70)
    print("Q096 — FAD Bias × AND/OR Gate Analysis")
    print(f"Config: {n_ph} phonemes × {args.features} features, seed={args.seed}")
    print("=" * 70)
    print(f"\n{'Phoneme':<8} {'TextPred':>9} {'Predictable':>12} {'AND%':>7} {'OR%':>7} "
          f"{'Pass%':>7} {'Dominant':>10}")
    print("-" * 70)
    for r in results:
        flag = "YES" if r.text_predictable else "NO"
        print(f"{r.phoneme:<8} {r.text_pred_prob:>9.2f} {flag:>12} {r.and_pct:>7.1f} "
              f"{r.or_pct:>7.1f} {r.pass_pct:>7.1f} {r.dominant_gate:>10}")

    # Aggregate by text-predictable vs acoustic-only
    text_pred_group  = [r for r in results if r.text_predictable]
    acoustic_group   = [r for r in results if not r.text_predictable]

    tp_and_mean = np.mean([r.and_pct for r in text_pred_group]) if text_pred_group else 0
    tp_or_mean  = np.mean([r.or_pct  for r in text_pred_group]) if text_pred_group else 0
    ac_and_mean = np.mean([r.and_pct for r in acoustic_group])  if acoustic_group  else 0
    ac_or_mean  = np.mean([r.or_pct  for r in acoustic_group])  if acoustic_group  else 0

    # Pearson r(text_pred_prob, AND%)
    text_probs = np.array([r.text_pred_prob for r in results])
    and_pcts   = np.array([r.and_pct for r in results])
    r_val = pearson_r(text_probs, and_pcts)

    print("-" * 70)
    print(f"\nAggregate by phoneme type:")
    print(f"  {'Group':<20} {'N':>4}  {'AND%':>7}  {'OR%':>7}")
    print(f"  {'text-predictable':<20} {len(text_pred_group):>4}  {tp_and_mean:>7.1f}  {tp_or_mean:>7.1f}")
    print(f"  {'acoustic-only':<20} {len(acoustic_group):>4}  {ac_and_mean:>7.1f}  {ac_or_mean:>7.1f}")

    print(f"\nPearson r(text_pred_prob, AND%) = {r_val:.4f}  (negative = FAD bias confirmed)")

    hyp_confirmed = (tp_or_mean > ac_or_mean) and (ac_and_mean > tp_and_mean)
    print(f"\nHypothesis: text-predictable phonemes → more OR-gates; acoustic-only → more AND-gates")
    print(f"  → {'CONFIRMED' if hyp_confirmed else 'NOT CONFIRMED'}")
    print(f"     text-pred OR%={tp_or_mean:.1f}  acoustic-only OR%={ac_or_mean:.1f}")
    print(f"     text-pred AND%={tp_and_mean:.1f}  acoustic-only AND%={ac_and_mean:.1f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
