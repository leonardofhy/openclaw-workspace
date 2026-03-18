#!/usr/bin/env python3
"""
RAVEL MDAS × AND/OR Gate — Q105
Track T3: Listen vs Guess

MDAS (Multi-Dimensional Attribute Score) from RAVEL benchmark:
  Cause(f): how much does activating feature f cause the right attribute?
  Isolate(f): how well does f isolate the target attribute (low bleed)?

Hypothesis: AND-gate features have LOW Cause error and HIGH Isolate score
            (they causally represent a single, well-isolated audio attribute).
            OR-gate features have HIGH Cause error (entangled with context).

Mock: 200 features. Compute MDAS Cause/Isolate scores, predict AND vs OR.

Usage:
    python3 ravel_mdas_and_or.py
    python3 ravel_mdas_and_or.py --features 400
    python3 ravel_mdas_and_or.py --json

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

N_FEATURES = 200
SEED = 42

ACT_THRESHOLD = 0.5
RECOVERY_FRAC  = 0.4

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FeatureMDAS:
    feature_id: int
    cause_score: float     # higher = better causal intervention
    isolate_score: float   # higher = less attribute bleed
    mdas_score: float      # combined: (cause + isolate) / 2
    gate_type: str
    predicted_gate: str    # predicted from MDAS
    correct: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def pearson_r(x: np.ndarray, y: np.ndarray) -> float:
    xm = x - x.mean(); ym = y - y.mean()
    denom = np.sqrt((xm**2).sum() * (ym**2).sum())
    return float(np.dot(xm, ym) / (denom + 1e-12))


def predict_gate_from_mdas(cause: float, isolate: float,
                            cause_thresh: float = 0.55,
                            isolate_thresh: float = 0.55) -> str:
    """Predict gate type from MDAS scores."""
    if cause >= cause_thresh and isolate >= isolate_thresh:
        return "AND"
    elif cause < cause_thresh and isolate < isolate_thresh:
        return "OR"
    else:
        return "Passthrough"


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def run(n_features: int, seed: int) -> List[FeatureMDAS]:
    rng = np.random.default_rng(seed)
    records: List[FeatureMDAS] = []

    for f in range(n_features):
        # Assign true gate type
        u = rng.uniform()
        if u < 0.40:
            true_gate = "AND"
        elif u < 0.72:
            true_gate = "OR"
        elif u < 0.95:
            true_gate = "Passthrough"
        else:
            true_gate = "Silent"

        # MDAS scores: AND-gates have high cause + high isolate
        if true_gate == "AND":
            cause   = rng.normal(0.75, 0.12)
            isolate = rng.normal(0.70, 0.12)
        elif true_gate == "OR":
            cause   = rng.normal(0.35, 0.12)
            isolate = rng.normal(0.40, 0.12)
        elif true_gate == "Passthrough":
            cause   = rng.normal(0.55, 0.15)
            isolate = rng.normal(0.35, 0.12)
        else:  # Silent
            cause   = rng.normal(0.20, 0.08)
            isolate = rng.normal(0.25, 0.08)

        cause   = float(np.clip(cause,   0.0, 1.0))
        isolate = float(np.clip(isolate, 0.0, 1.0))
        mdas    = (cause + isolate) / 2.0

        pred_gate = predict_gate_from_mdas(cause, isolate)
        correct = (pred_gate == true_gate)

        records.append(FeatureMDAS(
            feature_id=f,
            cause_score=round(cause, 4),
            isolate_score=round(isolate, 4),
            mdas_score=round(mdas, 4),
            gate_type=true_gate,
            predicted_gate=pred_gate,
            correct=correct,
        ))

    return records


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Q105: RAVEL MDAS × AND/OR Gate — MDAS predicts gate classification"
    )
    parser.add_argument("--features", type=int, default=N_FEATURES)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    records = run(args.features, args.seed)

    if args.as_json:
        print(json.dumps([asdict(r) for r in records], indent=2))
        return 0

    # Aggregate stats per gate type
    gate_types = ["AND", "OR", "Passthrough", "Silent"]

    print("=" * 65)
    print("Q105 — RAVEL MDAS × AND/OR Gate")
    print(f"Config: {args.features} features, seed={args.seed}")
    print("=" * 65)

    print(f"\nMDAS stats per gate type:")
    print(f"{'Gate Type':<14} {'N':>5}  {'Cause':>8}  {'Isolate':>9}  {'MDAS':>8}")
    print("-" * 52)
    for g in gate_types:
        subset = [r for r in records if r.gate_type == g]
        if not subset:
            continue
        causes   = [r.cause_score   for r in subset]
        isolates = [r.isolate_score for r in subset]
        mdas     = [r.mdas_score    for r in subset]
        print(f"{g:<14} {len(subset):>5}  {np.mean(causes):>8.3f}  "
              f"{np.mean(isolates):>9.3f}  {np.mean(mdas):>8.3f}")

    # Overall prediction accuracy
    total_correct = sum(1 for r in records if r.correct)
    accuracy = total_correct / len(records) * 100

    # Pearson r(MDAS, AND-flag)
    mdas_arr     = np.array([r.mdas_score for r in records])
    and_flag_arr = np.array([1 if r.gate_type == "AND" else 0 for r in records], dtype=float)
    r_val = pearson_r(mdas_arr, and_flag_arr)

    # Cause score for AND vs non-AND
    and_cause    = np.mean([r.cause_score for r in records if r.gate_type == "AND"])
    nonand_cause = np.mean([r.cause_score for r in records if r.gate_type != "AND"])

    print(f"\nPrediction accuracy (MDAS threshold classifier): {accuracy:.1f}%")
    print(f"Pearson r(MDAS score, AND-flag) = {r_val:.4f}")
    print(f"\nAND-gate Cause mean:    {and_cause:.3f}")
    print(f"Non-AND-gate Cause mean:{nonand_cause:.3f}")

    hyp_confirmed = (and_cause > nonand_cause + 0.1 and r_val > 0.3)
    print(f"\nHypothesis: AND-gates have higher Cause/Isolate (MDAS) than OR-gates")
    print(f"  → {'CONFIRMED' if hyp_confirmed else 'NOT CONFIRMED'}")
    print(f"  AND-gate MDAS predicts gate type with {accuracy:.0f}% accuracy.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
