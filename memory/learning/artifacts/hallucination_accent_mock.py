"""
hallucination_accent_mock.py — Q169

Hypothesis: Accented phonemes behave like silence from the model's perspective.
AND-frac drop (due to acoustic OOD-ness) → more hallucination steps.
AND-frac mediates the relationship between accent_level and hallucination_steps.

Theory chain:
  Q149: silence → t* leftward shift → hallucination risk
  Q164: accent → t* leftward shift (same mechanism)
  Q163: accented phonemes → AND-frac deficit
  Q167: AFG = AND-frac Fairness Gap → predicts WER gap
  Q168: accent×noise → compound AND-frac collapse (2x slope)
  Q169: accent_level → AND-frac drop → hallucination_steps  ← THIS SCRIPT

Mediation analysis (Baron-Kenny, mock):
  Path a: accent_level → AND-frac  (already validated Q162/Q167)
  Path b: AND-frac → hallucination_steps (already validated Q134)
  Path c: accent_level → hallucination_steps (total effect)
  Path c': accent_level → hallucination_steps | AND-frac (direct effect)
  Mediation = (c - c') / c  → percentage mediated by AND-frac

Design:
  - Sweep accent_level ∈ [0.0, 0.2, 0.4, 0.6, 0.8, 1.0] (N=200 per level)
  - Per sample: simulate AND-frac curve over decoder steps
  - Hallucination steps = steps where AND-frac < 0.40 (threshold from Q134)
  - AND-frac mediator = mean AND-frac over peak-commitment region (steps 5-10)
  - Run Baron-Kenny mediation on the 1200-sample dataset

DoD:
  1. r(accent_level, hallucination_steps) < -0.6  [more accent → more hall steps]
     (Note: accent_level↑ → AND-frac↓ → hall_steps↑, so r should be POSITIVE)
     Corrected: r(accent_level, hallucination_steps) > 0.6
  2. AND-frac mediates ≥40% of the total effect
  3. Highest-accent group (VIE/ARA) has hallucination_steps ≥ 3x native
"""

import json
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

rng = np.random.default_rng(42)

# ── Constants (aligned with Q134, Q164) ───────────────────────────────────────

N_STEPS      = 20     # decoder steps per utterance
N_SAMPLES    = 200    # per accent_level
AND_THRESH   = 0.40   # below = hallucination risk (from Q134)
COMMIT_STEPS = slice(5, 11)  # peak-commitment region for mediator

# L1 accent profiles (from Q162, Q167)
L1_PROFILES = {
    "native": {"accent_level": 0.00, "and_frac_mean": 0.347, "and_frac_ceil": 0.380},
    "HIN":    {"accent_level": 0.60, "and_frac_mean": 0.179, "and_frac_ceil": 0.280},
    "SPA":    {"accent_level": 0.60, "and_frac_mean": 0.174, "and_frac_ceil": 0.275},
    "MAN":    {"accent_level": 0.65, "and_frac_mean": 0.171, "and_frac_ceil": 0.272},
    "KOR":    {"accent_level": 0.70, "and_frac_mean": 0.165, "and_frac_ceil": 0.265},
    "ARA":    {"accent_level": 0.75, "and_frac_mean": 0.162, "and_frac_ceil": 0.260},
    "VIE":    {"accent_level": 0.80, "and_frac_mean": 0.155, "and_frac_ceil": 0.255},
}

ACCENT_SWEEP = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]


# ── Simulation ────────────────────────────────────────────────────────────────

def simulate_and_frac_curve(accent_level: float) -> np.ndarray:
    """
    Simulate AND-frac per decoder step for a given accent_level.

    accent_level=0.0 (native):
      - AND-frac peaks at step ~6, stays elevated (0.65-0.75)
      - Few sub-threshold steps
    accent_level=1.0 (strong accent, like silence):
      - AND-frac depressed throughout (0.15-0.30)
      - Majority of steps below threshold → hallucination

    Mechanism: Accented phonemes are acoustically OOD → AND-gate features
    fail to fire reliably → model falls back to text prior (same as silence).
    """
    # Baseline AND-frac curve (native, from Q134 clean mode)
    base_peak   = 0.70 + 0.08 * np.sin(np.linspace(0, np.pi, N_STEPS))
    native_curve = np.clip(base_peak + rng.normal(0, 0.04, N_STEPS), 0.55, 0.90)

    # Accent degradation: linearly scale down AND-frac
    # At accent_level=1.0: AND-frac ceiling drops to ~0.25 (from Q162/Q167)
    # Degradation is NOT uniform: commitment region (steps 5-10) degrades more
    # because it requires the most audio-dependent features
    degradation = np.ones(N_STEPS) * (1.0 - accent_level * 0.65)
    # Extra degradation in commitment region (the model tries harder there)
    degradation[COMMIT_STEPS] *= (1.0 - accent_level * 0.25)
    degradation = np.clip(degradation, 0.15, 1.0)

    accented_curve = native_curve * degradation
    # Add noise that scales with accent (OOD → more variable activations)
    noise_std = 0.04 + accent_level * 0.06
    accented_curve += rng.normal(0, noise_std, N_STEPS)
    accented_curve = np.clip(accented_curve, 0.05, 0.90)
    return accented_curve


def sample_utterance(accent_level: float) -> Dict:
    """One utterance: simulate AND-frac curve, compute hallucination steps and mediator."""
    curve = simulate_and_frac_curve(accent_level)
    hall_steps    = int(np.sum(curve < AND_THRESH))
    mediator_andf = float(np.mean(curve[COMMIT_STEPS]))
    return {
        "accent_level": accent_level,
        "hallucination_steps": hall_steps,
        "and_frac_mediator": mediator_andf,
    }


def run_sweep() -> List[Dict]:
    """Full sweep across accent levels, N_SAMPLES each."""
    records = []
    for acc in ACCENT_SWEEP:
        for _ in range(N_SAMPLES):
            records.append(sample_utterance(acc))
    return records


def run_l1_groups() -> List[Dict]:
    """Per-L1 group utterances using inherent accent_level."""
    records = []
    for group, prof in L1_PROFILES.items():
        for _ in range(N_SAMPLES):
            r = sample_utterance(prof["accent_level"])
            r["group"] = group
            records.append(r)
    return records


# ── Baron-Kenny Mediation (OLS-based mock) ────────────────────────────────────

def ols_coeff(x: np.ndarray, y: np.ndarray) -> Tuple[float, float]:
    """Return (slope, r) from simple OLS."""
    x = np.array(x, dtype=float)
    y = np.array(y, dtype=float)
    r = float(np.corrcoef(x, y)[0, 1])
    slope = r * np.std(y) / (np.std(x) + 1e-9)
    return slope, r


def mediation_analysis(records: List[Dict]) -> Dict:
    """
    Baron-Kenny mediation:
      X = accent_level
      M = and_frac_mediator
      Y = hallucination_steps

    Paths:
      a  = X → M
      b  = M → Y
      c  = X → Y (total)
      c' = direct effect = c - a*b
      mediation_pct = a*b / c
    """
    X = np.array([r["accent_level"]         for r in records])
    M = np.array([r["and_frac_mediator"]     for r in records])
    Y = np.array([r["hallucination_steps"]   for r in records])

    # Multiple regression for c': Y ~ X + M
    # Use OLS via normal equations
    Xmat = np.column_stack([np.ones_like(X), X, M])
    try:
        beta, *_ = np.linalg.lstsq(Xmat, Y, rcond=None)
        c_prime  = beta[1]  # direct effect of X on Y controlling M
    except Exception:
        c_prime  = 0.0

    a_slope, r_XM = ols_coeff(X, M)
    b_slope, r_MY = ols_coeff(M, Y)
    c_slope, r_XY = ols_coeff(X, Y)

    indirect = a_slope * b_slope  # a*b (product of coefficients)
    mediation_pct = (indirect / (c_slope + 1e-9)) * 100 if abs(c_slope) > 1e-6 else 0.0

    return {
        "r_XY (accent→hall)":   r_XY,
        "r_XM (accent→andfrac)": r_XM,
        "r_MY (andfrac→hall)":  r_MY,
        "path_a (X→M slope)":   a_slope,
        "path_b (M→Y slope)":   b_slope,
        "path_c (total X→Y)":   c_slope,
        "path_c_prime (direct)": c_prime,
        "indirect (a*b)":        indirect,
        "mediation_pct":         mediation_pct,
    }


# ── Main Report ───────────────────────────────────────────────────────────────

def report(sweep_records: List[Dict], l1_records: List[Dict]) -> bool:
    print("=" * 72)
    print("Q169: Hallucination × Accent Mock — Mediation Analysis")
    print("=" * 72)

    # ── Sweep summary ──────────────────────────────────────────────────────
    print("\nACCENT LEVEL SWEEP (N=200 per level):")
    print(f"  {'accent_level':<15} {'mean_hall_steps':<18} {'mean_AND-frac':<16} {'P(hall>0)'}")
    print("  " + "-" * 60)
    for acc in ACCENT_SWEEP:
        rows = [r for r in sweep_records if r["accent_level"] == acc]
        mh   = float(np.mean([r["hallucination_steps"] for r in rows]))
        maf  = float(np.mean([r["and_frac_mediator"]   for r in rows]))
        ppos = float(np.mean([r["hallucination_steps"] > 0 for r in rows]))
        print(f"  {acc:<15.1f} {mh:<18.2f} {maf:<16.3f} {ppos:.2f}")

    # ── Correlation: accent_level × hallucination_steps ────────────────────
    X_all = np.array([r["accent_level"]       for r in sweep_records])
    Y_all = np.array([r["hallucination_steps"] for r in sweep_records])
    r_XY  = float(np.corrcoef(X_all, Y_all)[0, 1])
    print(f"\nr(accent_level, hallucination_steps) = {r_XY:+.4f}  "
          f"{'✓ strong positive' if r_XY > 0.6 else '✗ weak'}")

    # ── Mediation analysis ─────────────────────────────────────────────────
    print("\nMEDIATION ANALYSIS (Baron-Kenny, N=1200):")
    med = mediation_analysis(sweep_records)
    for k, v in med.items():
        unit = "%" if "pct" in k else ""
        print(f"  {k:<32} = {v:+.4f}{unit}")

    # ── L1 group comparison ────────────────────────────────────────────────
    print("\nL1 GROUP COMPARISON:")
    print(f"  {'Group':<8} {'acc_level':<12} {'mean_hall_steps':<18} "
          f"{'mean_AND-frac':<16} {'vs native (×)'}")
    print("  " + "-" * 68)
    native_rows  = [r for r in l1_records if r["group"] == "native"]
    native_hall  = float(np.mean([r["hallucination_steps"] for r in native_rows]))
    for group in ["native", "HIN", "SPA", "MAN", "KOR", "ARA", "VIE"]:
        rows = [r for r in l1_records if r["group"] == group]
        mh   = float(np.mean([r["hallucination_steps"] for r in rows]))
        maf  = float(np.mean([r["and_frac_mediator"]   for r in rows]))
        ratio = mh / (native_hall + 1e-6)
        prof  = L1_PROFILES[group]
        print(f"  {group:<8} {prof['accent_level']:<12.2f} {mh:<18.2f} "
              f"{maf:<16.3f} {ratio:.2f}x")

    # ── Definition of Done ─────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("DEFINITION OF DONE:")

    # 1. r(accent_level, hallucination_steps) > 0.6
    dod1 = r_XY > 0.6
    print(f"  1. r(accent_level, hall_steps) > 0.6: {r_XY:.4f} → {'✓' if dod1 else '✗'}")

    # 2. Mediation ≥ 40%
    med_pct = med["mediation_pct"]
    dod2 = med_pct >= 40.0
    print(f"  2. AND-frac mediates ≥40%: {med_pct:.1f}% → {'✓' if dod2 else '✗'}")

    # 3. Highest-accent group shows ≥3x hallucination steps vs native
    vie_rows  = [r for r in l1_records if r["group"] == "VIE"]
    vie_hall  = float(np.mean([r["hallucination_steps"] for r in vie_rows]))
    ratio_vie = vie_hall / (native_hall + 1e-6)
    dod3 = ratio_vie >= 3.0
    print(f"  3. VIE hall_steps ≥ 3× native: {ratio_vie:.2f}x → {'✓' if dod3 else '✗'}")

    doi_pass = dod1 and dod2 and dod3
    print(f"  OVERALL: {'✓ PASS' if doi_pass else '✗ FAIL (partial)'}")

    print()
    print("MECHANISTIC STORY:")
    print("  Accented phonemes are acoustically OOD for Whisper's native-trained features.")
    print("  → AND-gate features fail to fire (AND-frac drops below native baseline).")
    print("  → With fewer audio-grounded features active, decoder falls back to LM prior.")
    print("  → More decoder steps become 'hallucination-prone' (AND-frac < 0.40 threshold).")
    print("  → This is structurally IDENTICAL to silence-induced hallucination (Q134/Q149):")
    print("    'audio is absent' ≅ 'audio is unrecognizable'.")
    print(f"  → Mediation: {med_pct:.0f}% of the accent→hallucination link passes through AND-frac.")
    print()
    print("  Full chain:")
    print("    Q149 (silence → t* → hallucination)")
    print("    Q163 (L2 phonemes → AND-frac deficit)")
    print("    Q164 (accent → t* leftward shift)")
    print("    Q169 (accent_level → AND-frac → hallucination_steps)  ← THIS SCRIPT")
    print("    Q167 (AFG fairness gap = quantified AND-frac bias)")

    return doi_pass


def save_results(sweep: List[Dict], l1: List[Dict], med: Dict) -> str:
    out = {
        "script": "hallucination_accent_mock.py",
        "task": "Q169",
        "sweep_summary": [
            {
                "accent_level": acc,
                "mean_hallucination_steps": float(np.mean([
                    r["hallucination_steps"] for r in sweep if r["accent_level"] == acc])),
                "mean_and_frac_mediator": float(np.mean([
                    r["and_frac_mediator"]   for r in sweep if r["accent_level"] == acc])),
            }
            for acc in ACCENT_SWEEP
        ],
        "l1_summary": [
            {
                "group": group,
                "accent_level": L1_PROFILES[group]["accent_level"],
                "mean_hallucination_steps": float(np.mean([
                    r["hallucination_steps"] for r in l1 if r["group"] == group])),
                "mean_and_frac_mediator": float(np.mean([
                    r["and_frac_mediator"]   for r in l1 if r["group"] == group])),
            }
            for group in L1_PROFILES
        ],
        "mediation": med,
    }
    path = "memory/learning/artifacts/hallucination_accent_results.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    return path


if __name__ == "__main__":
    import sys
    sweep_records = run_sweep()
    l1_records    = run_l1_groups()
    med           = mediation_analysis(sweep_records)
    doi_pass      = report(sweep_records, l1_records)
    path          = save_results(sweep_records, l1_records, med)
    print(f"\nResults saved → {path}")
    sys.exit(0 if doi_pass else 1)
