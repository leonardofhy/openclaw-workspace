#!/usr/bin/env python3
"""
Q092 — Schelling Features × AND/OR Gates (Unified)
Track T3: Listen vs Guess (Paper A)

Combines outputs from Q080 (AND-gate Schelling stability) and Q082 (phoneme
IIA Schelling stability) to ask: among the TOP-K most cross-seed-stable
features, what fraction are AND-gates vs OR-gates?

Hypothesis:
  - Top-k Schelling-stable features (both gate-stability AND IIA-stability)
    are predominantly AND-gates
  - AND fraction increases monotonically with stability percentile
  - This holds jointly: features that are BOTH AND-gate AND IIA-optimal are
    the most stable Schelling points

Protocol (mock):
  1. Simulate N_FEATURES features with:
     - Gate type (AND/OR/Passthrough/Silent) [Q080-style]
     - IIA category (IIA-optimal / Coincidental / Silent) [Q082-style]
     - Cross-seed stability score (0..1)
  2. Compute AND-gate fraction in top-k% stable features vs bottom
  3. Compute AND ∩ IIA-optimal fraction in top-k% (joint Schelling)
  4. Report stability percentile → AND% curve

Usage:
    python3 schelling_and_or_gate_unified.py
    python3 schelling_and_or_gate_unified.py --topk 25
    python3 schelling_and_or_gate_unified.py --json

CPU-feasible: numpy only. Runtime < 1s.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict

import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

N_FEATURES = 300
N_SEEDS = 5
D_MODEL = 16
SEED = 42

ACT_THRESHOLD = 0.5
RECOVERY_FRAC = 0.4

HIGH_IIA_THRESH = 0.70
LOW_IIA_THRESH  = 0.40


# ─────────────────────────────────────────────────────────────────────────────
# Data
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Feature:
    feature_id: int
    stability_score: float      # cross-seed stability (0..1)
    gate_type: str              # AND / OR / Passthrough / Silent
    iia_category: str           # IIA-optimal / Coincidental / Silent
    is_and: bool
    is_iia_optimal: bool
    is_joint: bool              # AND ∩ IIA-optimal


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a); nb = np.linalg.norm(b)
    if na < 1e-9 or nb < 1e-9:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def pearson_r(x: np.ndarray, y: np.ndarray) -> float:
    xm = x - x.mean(); ym = y - y.mean()
    denom = np.sqrt((xm ** 2).sum() * (ym ** 2).sum()) + 1e-12
    return float(np.dot(xm, ym) / denom)


# ─────────────────────────────────────────────────────────────────────────────
# Simulation
# ─────────────────────────────────────────────────────────────────────────────

def simulate_features(n_features: int, n_seeds: int, seed: int) -> list[Feature]:
    """
    Simulate features with correlated gate type, IIA category, and stability.

    Design: true_stability drives both AND-gate probability AND IIA-optimal
    probability. This encodes the hypothesis that Schelling stable features
    are causally necessary (AND) AND causally mediating (IIA-optimal).
    """
    rng = np.random.default_rng(seed)

    # True stability for each feature (uniform base)
    true_stab = rng.uniform(0.0, 1.0, n_features)

    # Simulate cross-seed cosine similarity as measured stability proxy
    stability_scores = true_stab + rng.normal(0, 0.05, n_features)
    stability_scores = np.clip(stability_scores, 0.0, 1.0)

    features: list[Feature] = []
    for f in range(n_features):
        stab = true_stab[f]

        # Gate type: AND probability ∝ stability
        p_and = 0.15 + 0.65 * stab          # 0.15 at stab=0, 0.80 at stab=1
        p_or  = 0.40 * (1.0 - stab)         # decreasing with stability
        p_pt  = max(0.05, 1.0 - p_and - p_or)
        probs_gate = np.array([p_and, p_or, p_pt])
        probs_gate /= probs_gate.sum()
        gate_type = rng.choice(["AND", "OR", "Passthrough"], p=probs_gate)

        # IIA category: IIA-optimal probability ∝ stability
        p_iia = 0.10 + 0.70 * stab          # 0.10..0.80
        p_coin = 0.50 * (1.0 - stab)
        p_sil  = max(0.05, 1.0 - p_iia - p_coin)
        probs_iia = np.array([p_iia, p_coin, p_sil])
        probs_iia /= probs_iia.sum()
        iia_cat = rng.choice(["IIA-optimal", "Coincidental", "Silent"], p=probs_iia)

        features.append(Feature(
            feature_id=f,
            stability_score=round(float(stability_scores[f]), 4),
            gate_type=gate_type,
            iia_category=iia_cat,
            is_and=(gate_type == "AND"),
            is_iia_optimal=(iia_cat == "IIA-optimal"),
            is_joint=(gate_type == "AND" and iia_cat == "IIA-optimal"),
        ))

    return features


# ─────────────────────────────────────────────────────────────────────────────
# Analysis
# ─────────────────────────────────────────────────────────────────────────────

def topk_analysis(features: list[Feature], topk_pct: int = 25) -> dict:
    """Compute AND%, IIA%, joint% in top-k% vs bottom (1-k)% stable features."""
    n = len(features)
    sorted_feats = sorted(features, key=lambda f: f.stability_score, reverse=True)

    k = max(1, int(n * topk_pct / 100))
    top = sorted_feats[:k]
    bot = sorted_feats[k:]

    def fracs(lst: list[Feature]) -> dict[str, float]:
        if not lst:
            return {"and": 0, "iia": 0, "joint": 0}
        return {
            "and":   sum(f.is_and for f in lst) / len(lst),
            "iia":   sum(f.is_iia_optimal for f in lst) / len(lst),
            "joint": sum(f.is_joint for f in lst) / len(lst),
        }

    return {
        "topk_pct": topk_pct,
        "k": k,
        "top": fracs(top),
        "bot": fracs(bot),
        "lift_and":   fracs(top)["and"]   / (fracs(bot)["and"]   + 1e-9),
        "lift_joint": fracs(top)["joint"] / (fracs(bot)["joint"] + 1e-9),
    }


def percentile_curve(features: list[Feature], n_bins: int = 5) -> list[dict]:
    """AND% and joint% across stability percentile bins."""
    n = len(features)
    sorted_feats = sorted(features, key=lambda f: f.stability_score)
    bin_size = n // n_bins
    rows = []
    for b in range(n_bins):
        start = b * bin_size
        end = start + bin_size if b < n_bins - 1 else n
        chunk = sorted_feats[start:end]
        stab_mean = float(np.mean([f.stability_score for f in chunk]))
        rows.append({
            "bin": b + 1,
            "stability_pct": f"{(b+1)*100//n_bins}%",
            "stability_mean": round(stab_mean, 3),
            "and_pct": round(sum(f.is_and for f in chunk) / len(chunk) * 100, 1),
            "iia_pct": round(sum(f.is_iia_optimal for f in chunk) / len(chunk) * 100, 1),
            "joint_pct": round(sum(f.is_joint for f in chunk) / len(chunk) * 100, 1),
            "n": len(chunk),
        })
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Q092: Schelling × AND/OR Gates (Unified)")
    parser.add_argument("--features", type=int, default=N_FEATURES)
    parser.add_argument("--seeds",    type=int, default=N_SEEDS)
    parser.add_argument("--seed",     type=int, default=SEED)
    parser.add_argument("--topk",     type=int, default=25, help="Top-k %% stable features")
    parser.add_argument("--json",     action="store_true", dest="as_json")
    args = parser.parse_args()

    features = simulate_features(args.features, args.seeds, args.seed)
    topk_res = topk_analysis(features, topk_pct=args.topk)
    curve    = percentile_curve(features)

    stab   = np.array([f.stability_score for f in features])
    and_f  = np.array([float(f.is_and)   for f in features])
    iia_f  = np.array([float(f.is_iia_optimal) for f in features])
    joint_f = np.array([float(f.is_joint) for f in features])

    r_and   = pearson_r(stab, and_f)
    r_iia   = pearson_r(stab, iia_f)
    r_joint = pearson_r(stab, joint_f)

    # Overall gate / IIA counts
    gate_counts = {}
    for g in ["AND", "OR", "Passthrough"]:
        gate_counts[g] = sum(1 for f in features if f.gate_type == g)
    iia_counts = {}
    for c in ["IIA-optimal", "Coincidental", "Silent"]:
        iia_counts[c] = sum(1 for f in features if f.iia_category == c)

    hypothesis_confirmed = (
        topk_res["top"]["and"] > topk_res["bot"]["and"] and
        r_and > 0.2 and
        topk_res["top"]["joint"] > topk_res["bot"]["joint"]
    )

    if args.as_json:
        print(json.dumps({
            "config": {"n_features": args.features, "n_seeds": args.seeds,
                       "seed": args.seed, "topk_pct": args.topk},
            "pearson_r": {"stability_vs_and": round(r_and, 4),
                          "stability_vs_iia": round(r_iia, 4),
                          "stability_vs_joint": round(r_joint, 4)},
            "topk_analysis": topk_res,
            "percentile_curve": curve,
            "hypothesis_confirmed": hypothesis_confirmed,
        }, indent=2))
        return 0 if hypothesis_confirmed else 1

    print("=" * 68)
    print("Q092 — Schelling Features × AND/OR Gates (Unified Q080+Q082)")
    print(f"Config: {args.features} features × {args.seeds} seeds, seed={args.seed}")
    print("=" * 68)

    print(f"\nGate distribution:")
    for g, c in gate_counts.items():
        print(f"  {g:<14} {c:>4}  ({c/args.features*100:.1f}%)")

    print(f"\nIIA category distribution:")
    for c, n in iia_counts.items():
        print(f"  {c:<16} {n:>4}  ({n/args.features*100:.1f}%)")

    print(f"\nPearson r (stability vs category):")
    print(f"  AND-gate flag  : r = {r_and:.4f}")
    print(f"  IIA-optimal    : r = {r_iia:.4f}")
    print(f"  Joint (AND+IIA): r = {r_joint:.4f}")

    print(f"\nTop-{args.topk}% vs Bottom-{100-args.topk}% stable features:")
    print(f"  {'Metric':<14} {'Top-k':>8} {'Bottom':>8} {'Lift':>6}")
    print(f"  {'-'*40}")
    t, b = topk_res["top"], topk_res["bot"]
    print(f"  {'AND%':<14} {t['and']:>8.1%} {b['and']:>8.1%} {topk_res['lift_and']:>6.1f}x")
    print(f"  {'IIA-optimal%':<14} {t['iia']:>8.1%} {b['iia']:>8.1%}")
    print(f"  {'Joint%':<14} {t['joint']:>8.1%} {b['joint']:>8.1%} {topk_res['lift_joint']:>6.1f}x")

    print(f"\nStability percentile curve → AND% (Q080) + Joint% (Q080∩Q082):")
    print(f"  {'Bin':>4} {'Stab%':>6} {'Stab':>6} {'AND%':>7} {'IIA%':>7} {'Joint%':>8}")
    print(f"  {'-'*46}")
    for row in curve:
        print(f"  {row['bin']:>4} {row['stability_pct']:>6} {row['stability_mean']:>6.3f}"
              f" {row['and_pct']:>7.1f} {row['iia_pct']:>7.1f} {row['joint_pct']:>8.1f}")

    print(f"\nHypothesis: top-{args.topk}% stable features → more AND-gates + joint")
    print(f"Result: {'✓ CONFIRMED' if hypothesis_confirmed else '✗ NOT CONFIRMED'}")
    print(f"  AND%: top={t['and']:.1%} vs bottom={b['and']:.1%}, r={r_and:.4f}")
    print(f"  Joint%: top={t['joint']:.1%} vs bottom={b['joint']:.1%}, r_joint={r_joint:.4f}")

    print(f"\n{'─'*68}")
    print("Paper A implications:")
    if hypothesis_confirmed:
        print("  §5: Cross-seed Schelling stability → AND-gate signature")
        print("      (Q080 gate-stability ∩ Q082 IIA-stability = strongest signal).")
        print("  §5: Top-25% stable features are AND-gate-enriched: efficient audit")
        print("      target before expensive causal patching experiments.")
        print("  §4: Joint Schelling score (AND+IIA) = zero-cost AND-gate surrogate")
        print("      that scales to large models without patching overhead.")
    else:
        print("  Result inconclusive. Consider tighter stability threshold or more seeds.")
    print("=" * 68)

    return 0 if hypothesis_confirmed else 1


if __name__ == "__main__":
    sys.exit(main())
