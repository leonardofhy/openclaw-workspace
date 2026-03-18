#!/usr/bin/env python3
"""
Collapse Onset × AND/OR Gate — Q093
Track T3: Listen vs Guess

Measures when audio information collapses in the decoder using a layer-wise
Isolate_in(t) metric, then correlates the collapse onset layer t* with AND/OR
gate type per feature.

Hypothesis: AND-gate features deactivate AT t* (collapse onset), whereas OR-gate
features remain active past t* (language prior takes over as substitute).

Mock: 10 layers × 50 features × 100 stimuli.

Usage:
    python3 collapse_onset_and_or.py
    python3 collapse_onset_and_or.py --layers 12
    python3 collapse_onset_and_or.py --json

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

N_LAYERS   = 10
N_FEATURES = 50
N_STIMULI  = 100
TRUE_COLLAPSE_LAYER = 6   # t* for the mock — audio info collapses here
SEED = 42

ACT_THRESHOLD = 0.5
RECOVERY_FRAC  = 0.4

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FeatureCollapseRecord:
    feature_id: int
    t_star: int           # layer where feature deactivates (Isolate minimum)
    gate_type: str        # AND / OR / Passthrough / Silent
    isolate_curve: List[float]   # Isolate_in value per layer


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

def simulate_isolate_curve(feature_id: int, gate_type: str,
                            n_layers: int, collapse_layer: int,
                            rng: np.random.Generator) -> List[float]:
    """
    Isolate_in(t): how much audio information is isolated at layer t.
    - AND-gate features: Isolate high before t*, drops sharply at t*
    - OR-gate features: Isolate starts lower, drops gradually (context fills in)
    - Passthrough: Isolate uniform decay
    """
    layers = np.arange(n_layers, dtype=float)
    noise = rng.normal(0, 0.05, n_layers)

    if gate_type == "AND":
        # Sharp step-drop at collapse_layer
        curve = np.where(layers < collapse_layer, 0.8, 0.1)
        curve += noise
    elif gate_type == "OR":
        # Gradual decay, never reaches low (context substitutes)
        curve = 0.6 - 0.03 * layers + noise
    elif gate_type == "Passthrough":
        # Linear decay
        curve = 0.7 - 0.06 * layers + noise
    else:  # Silent
        curve = 0.05 + noise * 0.5

    return list(np.clip(curve, 0.0, 1.0).round(4))


def run(n_layers: int, n_features: int, n_stimuli: int,
        collapse_layer: int, seed: int) -> List[FeatureCollapseRecord]:
    rng = np.random.default_rng(seed)

    records: List[FeatureCollapseRecord] = []

    for f in range(n_features):
        # Assign gate type with AND more likely near peak, OR at extremes
        # For mock, distribute: ~40% AND, ~35% OR, ~20% Passthrough, ~5% Silent
        r_u = rng.uniform()
        if r_u < 0.40:
            gate_type = "AND"
        elif r_u < 0.75:
            gate_type = "OR"
        elif r_u < 0.95:
            gate_type = "Passthrough"
        else:
            gate_type = "Silent"

        isolate = simulate_isolate_curve(f, gate_type, n_layers, collapse_layer, rng)

        # t_star = layer where Isolate curve drops most sharply (argmin of diff)
        arr = np.array(isolate)
        diffs = np.diff(arr)
        t_star = int(np.argmin(diffs))   # layer of steepest drop

        records.append(FeatureCollapseRecord(
            feature_id=f,
            t_star=t_star,
            gate_type=gate_type,
            isolate_curve=isolate,
        ))

    return records


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Q093: Collapse Onset × AND/OR Gate — t* vs gate type analysis"
    )
    parser.add_argument("--layers",   type=int, default=N_LAYERS)
    parser.add_argument("--features", type=int, default=N_FEATURES)
    parser.add_argument("--stimuli",  type=int, default=N_STIMULI)
    parser.add_argument("--collapse-layer", type=int, default=TRUE_COLLAPSE_LAYER)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    records = run(args.layers, args.features, args.stimuli,
                  args.collapse_layer, args.seed)

    if args.as_json:
        print(json.dumps([asdict(r) for r in records], indent=2))
        return 0

    # Aggregate t* per gate type
    gate_types = ["AND", "OR", "Passthrough", "Silent"]
    gate_tstar: dict = {g: [] for g in gate_types}
    for rec in records:
        gate_tstar[rec.gate_type].append(rec.t_star)

    # Pearson r(gate_is_and, t_star)
    and_flags = np.array([1 if r.gate_type == "AND" else 0 for r in records], dtype=float)
    t_stars   = np.array([r.t_star for r in records], dtype=float)
    r_val = pearson_r(and_flags, t_stars)

    print("=" * 60)
    print("Q093 — Collapse Onset × AND/OR Gate")
    print(f"Config: {args.layers} layers × {args.features} features × {args.stimuli} stimuli")
    print(f"True collapse layer (t*): {args.collapse_layer}, seed={args.seed}")
    print("=" * 60)

    print(f"\n{'Gate Type':<14} {'Count':>6}  {'Mean t*':>9}  {'Std t*':>8}")
    print("-" * 45)
    for g in gate_types:
        ts = gate_tstar[g]
        if ts:
            print(f"{g:<14} {len(ts):>6}  {np.mean(ts):>9.2f}  {np.std(ts):>8.2f}")
        else:
            print(f"{g:<14} {0:>6}  {'N/A':>9}  {'N/A':>8}")

    and_tstar_mean = float(np.mean(gate_tstar["AND"])) if gate_tstar["AND"] else float("nan")
    or_tstar_mean  = float(np.mean(gate_tstar["OR"]))  if gate_tstar["OR"]  else float("nan")

    print(f"\nPearson r(AND-flag, t*) = {r_val:.4f}")
    print(f"\nLayer-wise Isolate collapse summary:")
    print(f"  AND-gate mean t*       = {and_tstar_mean:.2f}  (expect ≈ {args.collapse_layer})")
    print(f"  OR-gate  mean t*       = {or_tstar_mean:.2f}   (expect > {args.collapse_layer}, later collapse)")

    # Hypothesis
    hyp_confirmed = (abs(and_tstar_mean - args.collapse_layer) < 2.0 and
                     or_tstar_mean > and_tstar_mean)
    print(f"\nHypothesis: AND-gates collapse at t*, OR-gates persist longer")
    print(f"  → {'CONFIRMED' if hyp_confirmed else 'NOT CONFIRMED'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
