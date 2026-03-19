#!/usr/bin/env python3
"""
Temporal gc(k) × AND/OR Gate — Q89
Track T3: Listen vs Guess (Paper A)

Question: Do AND-gate features appear EARLIER in the decoder time axis than
OR-gate features? AND-gates require joint audio+text activation → they should
fire early when audio grounding is strongest. OR-gate features need only one
modality → they can persist even after audio info collapses.

Pipeline (mock):
  1. Tag N SAE features as AND / OR / Passthrough using denoising protocol
     (extends Q087 AND/OR gate classification logic)
  2. Per feature, compute temporal_onset_step = first decoder step t where
     feature activation exceeds ACT_THRESHOLD (extends Q085 collapse onset)
  3. Aggregate: onset distribution per gate type
  4. Test hypothesis: mean_onset(AND) < mean_onset(OR)

Hypotheses:
  H1: AND-gate features have earlier mean temporal onset than OR-gate features
  H2: AND-gate onset variance < OR-gate onset variance (more concentrated)
  H3: At gc peak layer, AND-gate fraction is highest at t=0 (declines with t)
  H4: Passthrough features span the full temporal range (uniform distribution)

Mock model:
  - AND-gates: onset drawn from Normal(mu=1.5, sigma=0.8), clipped to [0, T-1]
  - OR-gates:  onset drawn from Normal(mu=4.5, sigma=1.2), clipped to [0, T-1]
  - Passthrough: onset drawn from Uniform[0, T-1]
  - Gate classification from denoising protocol (identical to Q087/Q092 logic)

Replace mock_feature_gate_type() and mock_feature_onset() with real
SAE feature analysis against Whisper-base encoder.

Usage:
    python3 temporal_gate_onset.py              # ASCII report
    python3 temporal_gate_onset.py --json       # JSON output
    python3 temporal_gate_onset.py --plot       # matplotlib (if available)
    python3 temporal_gate_onset.py --features 200 --steps 10

Dependencies: numpy only (matplotlib optional for --plot)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from typing import List, Dict

import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

N_FEATURES = 100           # SAE features to analyze
T_STEPS = 8                # decoder steps (t=0..T-1)
GC_PEAK_LAYER = 3          # encoder layer where gc(k) peaks
N_LAYERS = 6               # total encoder layers
N_STIMULI = 40             # stimuli per feature for gate classification
SEED = 42

# Denoising protocol thresholds (from Q087)
ACT_THRESHOLD = 0.50       # feature is "active" above this
RECOVERY_FRAC = 0.40       # OR-gate: partial recovery ≥ this fraction of baseline
AND_GATE_STRICT = 0.10     # AND-gate: recovery < this fraction (collapses with noise)

# Gate type labels
GATE_AND = "AND"
GATE_OR = "OR"
GATE_PASS = "Passthrough"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FeatureRecord:
    feature_id: int
    gate_type: str           # AND / OR / Passthrough
    temporal_onset: int      # first decoder step t where feature activates (or T if never)
    onset_curve: List[float] # activation level per decoder step
    is_and: bool
    is_or: bool


@dataclass
class GateOnsetSummary:
    gate_type: str
    n_features: int
    mean_onset: float
    std_onset: float
    median_onset: float
    min_onset: int
    max_onset: int
    onset_distribution: List[int]    # count per step t


# ---------------------------------------------------------------------------
# Step 1: Mock gate classification (denoising protocol, Q087 logic)
# ---------------------------------------------------------------------------

def classify_gate(feature_id: int, rng: np.random.Generator) -> str:
    """
    Denoising protocol: run N_STIMULI trials.
    For each stimulus:
      - baseline_act: activation without noise
      - noisy_act:    activation with audio noise applied
      - text_act:     activation with only text pathway

    Gate type:
      AND: baseline high AND noisy_act collapses (< AND_GATE_STRICT * baseline)
      OR:  baseline high AND noisy_act partially recovers (≥ RECOVERY_FRAC * baseline)
      Passthrough: low baseline or inconsistent pattern

    The feature_id seeds the gate tendency, giving stable mock classifications.
    """
    # Use feature_id as seed offset → stable gate assignment per feature
    feat_rng = np.random.default_rng(SEED + feature_id * 7)

    # Assign ground-truth gate type based on feature_id ranges
    # This mimics a realistic distribution: ~40% AND, ~45% OR, ~15% Passthrough
    prob = feat_rng.random()
    if prob < 0.40:
        true_gate = GATE_AND
    elif prob < 0.85:
        true_gate = GATE_OR
    else:
        true_gate = GATE_PASS

    # Run mock denoising trials to classify (with some classification noise)
    baseline_acts = feat_rng.uniform(0.55, 0.95, N_STIMULI)
    noise_level = feat_rng.uniform(0.1, 0.3, N_STIMULI)

    if true_gate == GATE_AND:
        # AND-gate: collapses when audio is perturbed
        noisy_recovery = feat_rng.uniform(0.02, 0.12, N_STIMULI)  # low recovery
    elif true_gate == GATE_OR:
        # OR-gate: partially recovers via text pathway
        noisy_recovery = feat_rng.uniform(0.35, 0.80, N_STIMULI)  # high recovery
    else:
        # Passthrough: variable recovery
        noisy_recovery = feat_rng.uniform(0.10, 0.60, N_STIMULI)

    noisy_acts = baseline_acts * noisy_recovery

    # Decision rule
    mean_baseline = baseline_acts.mean()
    mean_noisy = noisy_acts.mean()
    recovery_ratio = mean_noisy / (mean_baseline + 1e-9)

    if mean_baseline < ACT_THRESHOLD * 0.6:
        classified = GATE_PASS
    elif recovery_ratio < AND_GATE_STRICT:
        classified = GATE_AND
    elif recovery_ratio >= RECOVERY_FRAC:
        classified = GATE_OR
    else:
        classified = GATE_PASS

    return classified


# ---------------------------------------------------------------------------
# Step 2: Mock temporal onset (extends Q085 collapse onset logic)
# ---------------------------------------------------------------------------

def simulate_onset_curve(
    gate_type: str,
    feature_id: int,
    t_steps: int,
    rng: np.random.Generator,
) -> tuple[int, List[float]]:
    """
    Simulate feature activation curve over decoder steps.

    AND-gate temporal model:
      - Activates early (audio grounding peak at low t)
      - Decays quickly as decoder moves away from audio
      - onset ~ Normal(1.5, 0.8), clipped to [0, T-1]

    OR-gate temporal model:
      - Activates later (text pathway compensates)
      - More persistent across steps
      - onset ~ Normal(4.5, 1.2), clipped to [0, T-1]

    Passthrough temporal model:
      - No strong temporal preference
      - onset ~ Uniform[0, T-1]

    Returns: (temporal_onset, activation_curve)
    """
    feat_rng = np.random.default_rng(SEED + feature_id * 11 + abs(hash(gate_type)) % 9999)

    if gate_type == GATE_AND:
        onset_raw = feat_rng.normal(loc=1.5, scale=0.8)
        peak_height = feat_rng.uniform(0.70, 0.95)
        decay_rate = feat_rng.uniform(0.35, 0.55)   # fast decay
    elif gate_type == GATE_OR:
        onset_raw = feat_rng.normal(loc=4.5, scale=1.2)
        peak_height = feat_rng.uniform(0.55, 0.85)
        decay_rate = feat_rng.uniform(0.10, 0.25)   # slow decay
    else:  # Passthrough
        onset_raw = feat_rng.uniform(0, t_steps - 1)
        peak_height = feat_rng.uniform(0.40, 0.75)
        decay_rate = feat_rng.uniform(0.15, 0.40)

    onset = int(np.clip(round(onset_raw), 0, t_steps - 1))

    # Build activation curve: ramp up at onset, then decay
    steps = np.arange(t_steps, dtype=float)
    curve = np.zeros(t_steps, dtype=float)

    for t in range(t_steps):
        if t < onset:
            # Pre-onset: low activation
            curve[t] = feat_rng.uniform(0.02, 0.15)
        else:
            # Post-onset: exponential decay from peak
            curve[t] = peak_height * np.exp(-decay_rate * (t - onset))

    # Add noise
    noise = feat_rng.normal(0, 0.03, t_steps)
    curve = np.clip(curve + noise, 0.0, 1.0)

    act_list = [round(float(v), 4) for v in curve]
    return onset, act_list


# ---------------------------------------------------------------------------
# Step 3: Build feature records
# ---------------------------------------------------------------------------

def build_features(n_features: int, t_steps: int) -> List[FeatureRecord]:
    rng = np.random.default_rng(SEED)
    records = []

    for fid in range(n_features):
        gate = classify_gate(fid, rng)
        onset, curve = simulate_onset_curve(gate, fid, t_steps, rng)
        records.append(FeatureRecord(
            feature_id=fid,
            gate_type=gate,
            temporal_onset=onset,
            onset_curve=curve,
            is_and=(gate == GATE_AND),
            is_or=(gate == GATE_OR),
        ))

    return records


# ---------------------------------------------------------------------------
# Step 4: Summarize per gate type
# ---------------------------------------------------------------------------

def summarize_gate(
    features: List[FeatureRecord],
    gate_type: str,
    t_steps: int,
) -> GateOnsetSummary:
    subset = [f for f in features if f.gate_type == gate_type]
    if not subset:
        return GateOnsetSummary(
            gate_type=gate_type, n_features=0,
            mean_onset=float("nan"), std_onset=float("nan"),
            median_onset=float("nan"), min_onset=-1, max_onset=-1,
            onset_distribution=[0] * t_steps,
        )

    onsets = np.array([f.temporal_onset for f in subset], dtype=float)
    dist = [int(np.sum(onsets == t)) for t in range(t_steps)]

    return GateOnsetSummary(
        gate_type=gate_type,
        n_features=len(subset),
        mean_onset=float(onsets.mean()),
        std_onset=float(onsets.std()),
        median_onset=float(np.median(onsets)),
        min_onset=int(onsets.min()),
        max_onset=int(onsets.max()),
        onset_distribution=dist,
    )


# ---------------------------------------------------------------------------
# Step 5: AND-gate fraction per decoder step
# ---------------------------------------------------------------------------

def and_fraction_per_step(features: List[FeatureRecord], t_steps: int) -> List[float]:
    """
    At each decoder step t, compute the fraction of features that have already
    activated (onset <= t) and are AND-gates vs all activated features.
    """
    fracs = []
    for t in range(t_steps):
        activated = [f for f in features if f.temporal_onset <= t]
        if not activated:
            fracs.append(0.0)
        else:
            n_and = sum(1 for f in activated if f.is_and)
            fracs.append(round(n_and / len(activated), 4))
    return fracs


# ---------------------------------------------------------------------------
# Step 6: Hypothesis tests
# ---------------------------------------------------------------------------

def test_hypotheses(
    summaries: Dict[str, GateOnsetSummary],
    and_frac_per_step: List[float],
    t_steps: int,
) -> Dict:
    s_and = summaries[GATE_AND]
    s_or  = summaries[GATE_OR]
    s_pt  = summaries[GATE_PASS]

    # H1: mean_onset(AND) < mean_onset(OR)
    h1_passed = s_and.mean_onset < s_or.mean_onset
    h1_delta = s_or.mean_onset - s_and.mean_onset

    # H2: std_onset(AND) < std_onset(OR)
    h2_passed = s_and.std_onset < s_or.std_onset

    # H3: AND-gate fraction is highest at t=0 and declines
    frac = and_frac_per_step
    h3_passed = len(frac) >= 2 and frac[0] >= frac[-1]
    h3_delta = round(frac[0] - frac[-1], 4) if len(frac) >= 2 else 0.0

    # H4: Passthrough onset range spans full temporal range
    h4_passed = s_pt.n_features > 0 and (s_pt.max_onset - s_pt.min_onset) >= (t_steps - 2)

    return {
        "H1_AND_onset_earlier": {
            "passed": h1_passed,
            "mean_onset_AND": round(s_and.mean_onset, 3),
            "mean_onset_OR": round(s_or.mean_onset, 3),
            "delta": round(h1_delta, 3),
        },
        "H2_AND_onset_less_variable": {
            "passed": h2_passed,
            "std_AND": round(s_and.std_onset, 3),
            "std_OR": round(s_or.std_onset, 3),
        },
        "H3_AND_fraction_declines": {
            "passed": h3_passed,
            "frac_t0": frac[0] if frac else None,
            "frac_tT": frac[-1] if frac else None,
            "delta": h3_delta,
        },
        "H4_Passthrough_wide_range": {
            "passed": h4_passed,
            "range": (s_pt.min_onset, s_pt.max_onset) if s_pt.n_features > 0 else None,
        },
    }


# ---------------------------------------------------------------------------
# ASCII report
# ---------------------------------------------------------------------------

def print_report(
    features: List[FeatureRecord],
    summaries: Dict[str, GateOnsetSummary],
    and_frac: List[float],
    hyp: Dict,
    t_steps: int,
) -> None:
    gate_counts = {g: sum(1 for f in features if f.gate_type == g)
                   for g in [GATE_AND, GATE_OR, GATE_PASS]}

    print("=" * 70)
    print("  Q89 — Temporal gc(k) × AND/OR Gate Onset Analysis")
    print("  Q: Do AND-gate features activate EARLIER in decoding?")
    print(f"  Features: {len(features)}  |  T_steps: {t_steps}  |  Seed: {SEED}")
    print("=" * 70)

    # Gate distribution
    total = len(features)
    print(f"\n  ── Gate Classification (denoising protocol) ──────────────────────────")
    for g in [GATE_AND, GATE_OR, GATE_PASS]:
        n = gate_counts[g]
        print(f"    {g:<14}: {n:>4}  ({n/total*100:.1f}%)")

    # Summary table
    print(f"\n  ── Temporal Onset Summary ────────────────────────────────────────────")
    print(f"  {'Gate':<14} {'N':>5} {'Mean t*':>8} {'Std t*':>8} {'Median':>8} {'Min':>5} {'Max':>5}")
    print(f"  {'─' * 58}")
    for g in [GATE_AND, GATE_OR, GATE_PASS]:
        s = summaries[g]
        if s.n_features == 0:
            print(f"  {g:<14}  (no features)")
            continue
        print(f"  {g:<14} {s.n_features:>5} {s.mean_onset:>8.2f} {s.std_onset:>8.2f} "
              f"{s.median_onset:>8.1f} {s.min_onset:>5} {s.max_onset:>5}")

    # Temporal onset distribution (histogram)
    print(f"\n  ── Onset Distribution by Decoder Step ────────────────────────────────")
    print(f"  {'t':<4}  {'AND':>6}  {'OR':>6}  {'Pass':>6}  Bar (AND=■ OR=□ Pass=·)")
    print(f"  {'─' * 55}")
    max_count = max(
        max((s.onset_distribution[t] for s in summaries.values() if s.n_features > 0), default=1)
        for t in range(t_steps)
    )
    for t in range(t_steps):
        and_n = summaries[GATE_AND].onset_distribution[t] if summaries[GATE_AND].n_features > 0 else 0
        or_n  = summaries[GATE_OR].onset_distribution[t]  if summaries[GATE_OR].n_features > 0 else 0
        pt_n  = summaries[GATE_PASS].onset_distribution[t] if summaries[GATE_PASS].n_features > 0 else 0

        scale = 20
        and_bar = "■" * max(1, int(and_n / max(max_count, 1) * scale)) if and_n else ""
        or_bar  = "□" * max(1, int(or_n  / max(max_count, 1) * scale)) if or_n else ""
        pt_bar  = "·" * max(1, int(pt_n  / max(max_count, 1) * scale)) if pt_n else ""

        print(f"  t={t}  {and_n:>6}  {or_n:>6}  {pt_n:>6}  {and_bar}{or_bar}{pt_bar}")

    # AND-gate fraction per step
    print(f"\n  ── AND-Gate Fraction per Decoder Step ────────────────────────────────")
    print(f"  (Among all features activated by step t, what fraction are AND-gates?)")
    print(f"  {'t':<4}  {'AND frac':>9}  Bar")
    print(f"  {'─' * 40}")
    for t, frac in enumerate(and_frac):
        bar_len = int(frac * 30)
        bar = "█" * bar_len
        print(f"  t={t}  {frac:>9.3f}  {bar}")

    # Hypotheses
    print(f"\n  ── Hypothesis Test Results ───────────────────────────────────────────")
    icons = {True: "✅", False: "❌"}
    for hname, hres in hyp.items():
        icon = icons[hres["passed"]]
        detail = {k: v for k, v in hres.items() if k != "passed"}
        print(f"  {icon} {hname}")
        for k, v in detail.items():
            print(f"       {k}: {v}")

    # Interpretation
    print(f"\n  ── Mechanistic Interpretation ────────────────────────────────────────")
    print(f"  AND-gate features: require audio+text → peak activation at early t")
    print(f"    → Timing signature = conjunctive grounding (both modalities needed)")
    print(f"    → Mean onset t* ≈ {summaries[GATE_AND].mean_onset:.2f}")
    print(f"  OR-gate features: satisfied by either modality → persist later")
    print(f"    → Timing signature = fallback grounding (text rescues after audio fades)")
    print(f"    → Mean onset t* ≈ {summaries[GATE_OR].mean_onset:.2f}")
    if hyp["H1_AND_onset_earlier"]["passed"]:
        delta = hyp["H1_AND_onset_earlier"]["delta"]
        print(f"  ✓ Timing gap: Δt* = {delta:.2f} steps (OR activates {delta:.2f} steps later)")
        print(f"    → Supports: audio-grounded features are temporally early in decoding")
    else:
        print(f"  ✗ No significant timing gap observed (hypothesis rejected on mock data)")

    print("\n" + "=" * 70)
    print("  ✓ Q89 DONE: temporal_gate_onset.py — AND/OR gate onset analysis")
    print("  Artifacts: temporal_gate_onset.py")
    print("  Connection: extends Q085 (collapse_onset_step) + Q087 (AND/OR gate tagging)")
    print("  Next: Q93 — Collapse Onset × AND/OR Gate (do AND-gates deactivate at t*?)")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Matplotlib plot
# ---------------------------------------------------------------------------

def plot_matplotlib(
    summaries: Dict[str, GateOnsetSummary],
    and_frac: List[float],
    t_steps: int,
) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not available — skipping --plot")
        return

    import os
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    # Left: onset distribution
    ax = axes[0]
    steps = np.arange(t_steps)
    colors = {GATE_AND: "steelblue", GATE_OR: "coral", GATE_PASS: "gray"}
    width = 0.28
    for i, g in enumerate([GATE_AND, GATE_OR, GATE_PASS]):
        s = summaries[g]
        if s.n_features == 0:
            continue
        dist = np.array(s.onset_distribution, dtype=float)
        ax.bar(steps + i * width, dist, width=width, label=g, color=colors[g], alpha=0.8)
    ax.set_xlabel("Decoder step t")
    ax.set_ylabel("Feature count")
    ax.set_title("Temporal Onset Distribution by Gate Type")
    ax.legend()

    # Middle: AND-gate fraction per step
    ax = axes[1]
    ax.plot(steps, and_frac, marker="o", color="steelblue", linewidth=2)
    ax.set_xlabel("Decoder step t")
    ax.set_ylabel("AND-gate fraction")
    ax.set_title("AND-Gate Fraction Among Activated Features")
    ax.set_ylim(0, 1)
    ax.axhline(0.5, linestyle="--", color="gray", linewidth=1)

    # Right: mean onset comparison
    ax = axes[2]
    gate_types = [GATE_AND, GATE_OR, GATE_PASS]
    means = [summaries[g].mean_onset for g in gate_types]
    stds  = [summaries[g].std_onset for g in gate_types]
    n_list = [summaries[g].n_features for g in gate_types]
    bars = ax.bar(
        [f"{g}\n(n={n})" for g, n in zip(gate_types, n_list)],
        means, yerr=stds, capsize=5,
        color=[colors[g] for g in gate_types], alpha=0.8
    )
    ax.set_ylabel("Mean temporal onset t*")
    ax.set_title("Mean Onset Step by Gate Type")
    ax.set_ylim(0, t_steps)

    fig.suptitle("Q89: Temporal gc(k) × AND/OR Gate Onset (Mock Mode)", fontsize=12)
    plt.tight_layout()

    os.makedirs("memory/learning/cycles", exist_ok=True)
    out = "memory/learning/cycles/q89_temporal_gate_onset.png"
    plt.savefig(out, dpi=120)
    print(f"  Plot saved → {out}")
    plt.close()


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

def to_json(
    features: List[FeatureRecord],
    summaries: Dict[str, GateOnsetSummary],
    and_frac: List[float],
    hyp: Dict,
) -> Dict:
    gate_counts = {g: sum(1 for f in features if f.gate_type == g)
                   for g in [GATE_AND, GATE_OR, GATE_PASS]}
    return {
        "task": "Q89",
        "description": "Temporal gc(k) × AND/OR Gate: do AND-gate features activate earlier?",
        "config": {
            "n_features": len(features),
            "t_steps": T_STEPS,
            "n_stimuli_per_feature": N_STIMULI,
            "seed": SEED,
        },
        "gate_distribution": gate_counts,
        "summaries": {
            g: asdict(s) for g, s in summaries.items()
        },
        "and_fraction_per_step": and_frac,
        "hypotheses": hyp,
        "key_finding": (
            f"AND-gate features activate at mean t*={summaries[GATE_AND].mean_onset:.2f}, "
            f"OR-gate at t*={summaries[GATE_OR].mean_onset:.2f}. "
            f"H1={'CONFIRMED' if hyp['H1_AND_onset_earlier']['passed'] else 'REJECTED'}."
        ),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Q89: Temporal gc(k) × AND/OR Gate Onset Analysis"
    )
    parser.add_argument("--features", type=int, default=N_FEATURES)
    parser.add_argument("--steps",    type=int, default=T_STEPS)
    parser.add_argument("--json",     action="store_true")
    parser.add_argument("--plot",     action="store_true")
    args = parser.parse_args()

    # Build features
    features = build_features(args.features, args.steps)

    # Summarize per gate type
    summaries = {g: summarize_gate(features, g, args.steps)
                 for g in [GATE_AND, GATE_OR, GATE_PASS]}

    # AND-gate fraction per step
    and_frac = and_fraction_per_step(features, args.steps)

    # Hypothesis tests
    hyp = test_hypotheses(summaries, and_frac, args.steps)

    if args.json:
        print(json.dumps(to_json(features, summaries, and_frac, hyp), indent=2))
        return 0

    print_report(features, summaries, and_frac, hyp, args.steps)

    if args.plot:
        plot_matplotlib(summaries, and_frac, args.steps)

    # Validation
    for f in features:
        assert f.gate_type in (GATE_AND, GATE_OR, GATE_PASS), f"Invalid gate: {f.gate_type}"
        assert 0 <= f.temporal_onset < args.steps, f"Invalid onset: {f.temporal_onset}"
        assert len(f.onset_curve) == args.steps, f"Curve length mismatch for f{f.feature_id}"
        assert all(0.0 <= v <= 1.0 for v in f.onset_curve), f"Out-of-range in f{f.feature_id}"

    return 0


if __name__ == "__main__":
    sys.exit(main())
