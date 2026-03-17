#!/usr/bin/env python3
"""
Audio Incrimination Graph — Q090 (Tier 0, CPU-only, mock data)
Track T5: Listen-Layer Audit (Paper C / MATS)

Hypothesis:
  Jailbreak audio causes gc(k) collapse at a specific decoding step t*.
  The "incrimination graph" traces WHICH SAE features are causally responsible
  for that collapse — bridging T5 (jailbreak detection) and T3 (gc(k) analysis).

Graph structure:
  Nodes: SAE features (indexed by feature_id, layer)
  Edges: directed causal influence on gc(k) at collapse step t*
  Edge weight: blame(f) = gc(k*, t* | f ablated) - gc(k*, t* | full)
    - blame < 0: feature WAS supporting audio grounding (incriminated)
    - blame > 0: feature WAS suppressing grounding (exonerating)
    - blame ≈ 0: feature irrelevant to collapse

Two scenarios:
  "benign"   — gc(k) stays high; no collapse; few incriminated features
  "jailbreak" — gc(k) collapses at t*=3; several T5-incriminated features

Usage:
    python3 audio_incrimination_graph.py                 # both scenarios
    python3 audio_incrimination_graph.py --scenario jailbreak
    python3 audio_incrimination_graph.py --scenario benign
    python3 audio_incrimination_graph.py --json          # machine-readable output
    python3 audio_incrimination_graph.py --tau 0.35      # collapse threshold
    python3 audio_incrimination_graph.py --delta 0.05    # blame threshold

Dependencies: numpy only
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from typing import Optional
import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

N_LAYERS = 8           # encoder (0-3) + decoder (4-7)
N_ENCODER = 4
N_DECODER_STEPS = 6    # T=6 decoding steps
N_SAE_FEATURES = 24    # mock: 24 SAE features per layer-of-interest (layer 5)
LAYER_OF_INTEREST = 5  # peak gc(k) layer for T5 audit

RNG_SEED = 42

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class FeatureNode:
    feature_id: int
    layer: int
    activation: float          # mean activation at t*
    blame: float               # gc change when ablated
    label: str                 # "incriminated" | "exonerating" | "neutral"
    activation_trajectory: list[float] = field(default_factory=list)  # activation per step

@dataclass
class IncriminationGraph:
    scenario: str
    t_star: Optional[int]           # collapse step (None if no collapse)
    gc_trajectory: list[float]      # gc(k*, t) for t in 0..T-1
    gc_at_collapse: Optional[float]
    tau: float                      # collapse threshold used
    delta: float                    # blame threshold
    features: list[FeatureNode]
    n_incriminated: int
    n_exonerating: int
    n_neutral: int
    top_incriminated: list[dict]    # top-3 by |blame|
    summary: str

# ---------------------------------------------------------------------------
# Mock data generation
# ---------------------------------------------------------------------------

def make_gc_trajectory(scenario: str, rng: np.random.Generator, T: int = N_DECODER_STEPS) -> list[float]:
    """Generate gc(k*, t) trajectory for each decoding step."""
    if scenario == "benign":
        # Healthy: gc stays high throughout decoding
        base = 0.72
        noise = rng.normal(0, 0.03, T)
        gc = np.clip(base + noise, 0.55, 0.95).tolist()
    else:
        # Jailbreak: normal at first, then collapses at step t=3
        gc = []
        for t in range(T):
            if t < 3:
                gc.append(float(np.clip(0.70 + rng.normal(0, 0.02), 0.60, 0.85)))
            elif t == 3:
                gc.append(float(np.clip(0.28 + rng.normal(0, 0.02), 0.20, 0.38)))  # collapse
            else:
                gc.append(float(np.clip(0.15 + rng.normal(0, 0.02), 0.05, 0.25)))  # stays low
    return gc


def make_feature_activations(scenario: str, rng: np.random.Generator,
                              n_features: int = N_SAE_FEATURES,
                              T: int = N_DECODER_STEPS) -> np.ndarray:
    """
    Generate SAE feature activation trajectories (n_features × T).
    In jailbreak scenario, 4-6 features spike at t=3 (attack features)
    and several audio-grounding features suddenly deactivate at t=3.
    """
    acts = rng.random((n_features, T)) * 0.3  # baseline low

    if scenario == "jailbreak":
        # Attack features: spike at t>=3
        attack_feats = [2, 7, 11, 15]
        for f in attack_feats:
            acts[f, 0:3] = rng.random(3) * 0.2
            acts[f, 3:] = 0.8 + rng.random(T - 3) * 0.1

        # Audio-grounding features: high before t=3, drop after
        grounding_feats = [0, 4, 9, 18]
        for f in grounding_feats:
            acts[f, 0:3] = 0.7 + rng.random(3) * 0.1
            acts[f, 3:] = rng.random(T - 3) * 0.1
    else:
        # Benign: audio-grounding features stay active throughout
        grounding_feats = [0, 4, 9, 18]
        for f in grounding_feats:
            acts[f, :] = 0.65 + rng.random(T) * 0.1

    return acts


def compute_blame(scenario: str, rng: np.random.Generator,
                  t_star: Optional[int], feature_acts: np.ndarray,
                  gc_at_tstar: float, delta: float) -> list[float]:
    """
    Mock ablation study at t*.
    blame(f) = gc(k*, t* | f ablated) - gc(k*, t* | full)
    Negative blame = feature was supporting grounding (incriminated).
    Positive blame = feature was suppressing grounding (exonerating).
    """
    if t_star is None:
        # No collapse → near-zero blame for all
        return list(rng.normal(0, 0.01, len(feature_acts)).astype(float))

    blames = []
    for f_idx, acts in enumerate(feature_acts):
        activation_at_tstar = acts[t_star]

        if scenario == "jailbreak":
            # Attack features (high activation at t*): ablating them partially restores gc
            if f_idx in [2, 7, 11, 15]:
                blame = activation_at_tstar * 0.4 + rng.normal(0, 0.01)  # positive = exonerating?
                # Actually these features are suppressing grounding → blame > 0
                blame = abs(blame)
            # Grounding features (low at t*, should be high): ablating them doesn't hurt further
            elif f_idx in [0, 4, 9, 18]:
                # Their ABSENCE is the problem; ablating what's left barely changes gc
                blame = rng.normal(-0.15, 0.02)  # slight negative (they were the grounding signal)
            else:
                blame = rng.normal(0, 0.015)
        else:
            blame = rng.normal(0, 0.01)

        blames.append(float(np.clip(blame, -1.0, 1.0)))

    return blames


def find_collapse_step(gc_traj: list[float], tau: float) -> Optional[int]:
    """t* = first step where gc < tau."""
    for t, gc in enumerate(gc_traj):
        if gc < tau:
            return t
    return None


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def run_scenario(scenario: str, tau: float, delta: float) -> IncriminationGraph:
    rng = np.random.default_rng(RNG_SEED)

    gc_traj = make_gc_trajectory(scenario, rng)
    t_star = find_collapse_step(gc_traj, tau)
    gc_at_tstar = gc_traj[t_star] if t_star is not None else None

    feature_acts = make_feature_activations(scenario, rng)
    blames = compute_blame(scenario, rng, t_star, feature_acts, gc_at_tstar or 0.0, delta)

    nodes = []
    for f_idx in range(N_SAE_FEATURES):
        b = blames[f_idx]
        if b < -delta:
            label = "incriminated"   # feature was supporting grounding; its drop caused collapse
        elif b > delta:
            label = "exonerating"    # feature was suppressing grounding; its spike caused collapse
        else:
            label = "neutral"

        act_at_tstar = float(feature_acts[f_idx, t_star]) if t_star is not None else float(np.mean(feature_acts[f_idx]))

        nodes.append(FeatureNode(
            feature_id=f_idx,
            layer=LAYER_OF_INTEREST,
            activation=act_at_tstar,
            blame=b,
            label=label,
            activation_trajectory=[round(float(a), 4) for a in feature_acts[f_idx]],
        ))

    n_incrim = sum(1 for n in nodes if n.label == "incriminated")
    n_exon = sum(1 for n in nodes if n.label == "exonerating")
    n_neut = sum(1 for n in nodes if n.label == "neutral")

    # Top-3 by absolute blame
    top3 = sorted(nodes, key=lambda n: abs(n.blame), reverse=True)[:3]
    top3_dicts = [{"feature_id": n.feature_id, "blame": round(n.blame, 4), "label": n.label,
                   "activation_at_tstar": round(n.activation, 4)} for n in top3]

    if scenario == "benign":
        summary = (f"BENIGN: No gc collapse (all gc ≥ {min(gc_traj):.3f} > tau={tau:.2f}). "
                   f"{n_incrim} incriminated / {n_exon} exonerating / {n_neut} neutral features.")
    else:
        summary = (f"JAILBREAK: Collapse detected at t*={t_star} (gc={gc_at_tstar:.3f} < tau={tau:.2f}). "
                   f"{n_incrim} incriminated / {n_exon} exonerating / {n_neut} neutral features. "
                   f"Top culprit: feature {top3[0].feature_id} (blame={top3[0].blame:.4f}, {top3[0].label}).")

    return IncriminationGraph(
        scenario=scenario,
        t_star=t_star,
        gc_trajectory=[round(g, 4) for g in gc_traj],
        gc_at_collapse=round(gc_at_tstar, 4) if gc_at_tstar is not None else None,
        tau=tau,
        delta=delta,
        features=nodes,
        n_incriminated=n_incrim,
        n_exonerating=n_exon,
        n_neutral=n_neut,
        top_incriminated=top3_dicts,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def print_report(g: IncriminationGraph) -> None:
    print(f"\n{'='*60}")
    print(f"Scenario: {g.scenario.upper()}")
    print(f"{'='*60}")
    print(f"gc(k*={LAYER_OF_INTEREST}) trajectory: {g.gc_trajectory}")
    if g.t_star is not None:
        print(f"Collapse step t* = {g.t_star}  (gc={g.gc_at_collapse:.3f} < tau={g.tau:.2f})")
    else:
        print(f"No collapse detected (all gc > tau={g.tau:.2f})")
    print(f"\nFeature blame summary (delta={g.delta}):")
    print(f"  Incriminated : {g.n_incriminated}")
    print(f"  Exonerating  : {g.n_exonerating}")
    print(f"  Neutral      : {g.n_neutral}")
    print(f"\nTop-3 features by |blame|:")
    for d in g.top_incriminated:
        print(f"  feature_{d['feature_id']:02d}  blame={d['blame']:+.4f}  ({d['label']})  "
              f"act@t*={d['activation_at_tstar']:.4f}")
    print(f"\nSummary: {g.summary}")


def main():
    parser = argparse.ArgumentParser(description="Audio Incrimination Graph (Tier-0 mock)")
    parser.add_argument("--scenario", choices=["benign", "jailbreak", "both"], default="both")
    parser.add_argument("--tau", type=float, default=0.35, help="gc collapse threshold")
    parser.add_argument("--delta", type=float, default=0.05, help="blame attribution threshold")
    parser.add_argument("--json", action="store_true", help="output JSON instead of report")
    args = parser.parse_args()

    scenarios = ["benign", "jailbreak"] if args.scenario == "both" else [args.scenario]
    results = [run_scenario(s, args.tau, args.delta) for s in scenarios]

    if args.json:
        out = []
        for g in results:
            d = asdict(g)
            d.pop("features")  # too verbose for JSON output; keep top_incriminated
            out.append(d)
        print(json.dumps(out, indent=2))
    else:
        for g in results:
            print_report(g)
        print()


if __name__ == "__main__":
    main()
