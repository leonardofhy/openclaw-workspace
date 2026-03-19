#!/usr/bin/env python3
"""
gc(k) Predicts Whisper Hallucination — Q110
Track T3: Listen vs Guess (Paper A)

Hypothesis: low gc(k) frames = hallucination onset.
When Whisper's graded causality signal drops early (model stops "listening"),
the decoder falls back to language prior → produces hallucinated tokens
(repetitions, confabulations, or prior-conditioned phrases).

Mock design:
  - 3 utterance types: CORRECT, HALLUCINATION_REPEAT, HALLUCINATION_CONFAB
  - Each type gets a synthetic gc(k) curve reflecting the mechanism
  - Compute: mean_gc, collapse_onset_step t*, gc_gap between correct vs hallucinated
  - Result: hallucinated examples have significantly lower gc(k) at all layers,
    and earlier collapse onset t*

CPU-feasible: pure numpy mock, no model download needed.

Hypotheses:
  H1: mean_gc(CORRECT) > mean_gc(HALLUCINATION_REPEAT) > mean_gc(HALLUCINATION_CONFAB)
  H2: t*(CORRECT) > t*(HALLUCINATION_REPEAT) > t*(HALLUCINATION_CONFAB)
      (later collapse = more genuine listening)
  H3: gc(k) at peak layer k* is predictive of hallucination label (AUC > 0.80)
  H4: low_gc_fraction (fraction of layers with gc < 0.2) inversely correlates with correctness

Usage:
    python3 gc_hallucination_mock.py             # text summary
    python3 gc_hallucination_mock.py --json      # JSON output
    python3 gc_hallucination_mock.py --plot      # ASCII bar chart
    python3 gc_hallucination_mock.py --n 50      # larger N per condition
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict, field
from typing import List, Optional

import numpy as np


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

N_ENCODER_LAYERS = 6   # Whisper-tiny scale
N_STIMULI = 30         # per condition
T_STAR_THRESHOLD = 0.1 # gc(k) < threshold = collapsed

UTTERANCE_TYPES = ["correct", "halluc_repeat", "halluc_confab"]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class UtteranceSample:
    utype: str
    gc_curve: np.ndarray       # shape: (N_ENCODER_LAYERS,)
    mean_gc: float
    peak_gc: float
    peak_layer: int
    t_star: int                # first layer where gc drops below T_STAR_THRESHOLD
    low_gc_fraction: float     # fraction of layers with gc < 0.2


@dataclass
class HallucinationResult:
    n_per_condition: int
    n_layers: int
    conditions: dict           # utype -> aggregated stats
    hypothesis_tests: dict
    conclusions: List[str]


# ---------------------------------------------------------------------------
# Mock gc(k) curve generators
# ---------------------------------------------------------------------------

def _mock_gc_correct(rng: np.random.Generator) -> np.ndarray:
    """
    CORRECT utterance: Whisper genuinely listens to audio.
    gc(k) rises to a peak at mid-to-late encoder layers (k=3-5),
    then stays elevated. Reflects strong causal audio contribution.
    """
    layers = np.arange(N_ENCODER_LAYERS)
    peak = rng.uniform(3.0, 5.0)
    peak_height = rng.uniform(0.65, 0.90)
    width = rng.uniform(1.5, 2.5)
    curve = peak_height * np.exp(-0.5 * ((layers - peak) / width) ** 2)
    # Keep a sustained floor after peak
    sustained = np.where(layers >= int(peak), curve * rng.uniform(0.7, 0.9), curve)
    noise = rng.normal(0, 0.03, N_ENCODER_LAYERS)
    return np.clip(sustained + noise, 0.0, 1.0)


def _mock_gc_halluc_repeat(rng: np.random.Generator) -> np.ndarray:
    """
    HALLUCINATION (repetition): Model defaults to language prior early.
    gc(k) rises briefly but collapses mid-sequence (k~2-3),
    leaving a low-gc plateau. Prior-driven repetition.
    """
    layers = np.arange(N_ENCODER_LAYERS)
    peak = rng.uniform(1.5, 2.5)
    peak_height = rng.uniform(0.30, 0.50)
    width = rng.uniform(1.0, 1.5)
    curve = peak_height * np.exp(-0.5 * ((layers - peak) / width) ** 2)
    # Rapid decay after peak
    decay = np.where(layers > int(peak), curve * 0.4, curve)
    noise = rng.normal(0, 0.02, N_ENCODER_LAYERS)
    return np.clip(decay + noise, 0.0, 1.0)


def _mock_gc_halluc_confab(rng: np.random.Generator) -> np.ndarray:
    """
    HALLUCINATION (confabulation): Model ignores audio almost entirely.
    gc(k) stays near zero across all layers. Language prior dominates.
    """
    layers = np.arange(N_ENCODER_LAYERS)
    base = rng.uniform(0.02, 0.12, N_ENCODER_LAYERS)
    # Small spurious bump at early layer
    bump_layer = rng.integers(0, 2)
    base[bump_layer] += rng.uniform(0.05, 0.15)
    noise = rng.normal(0, 0.015, N_ENCODER_LAYERS)
    return np.clip(base + noise, 0.0, 1.0)


_CURVE_GENERATORS = {
    "correct": _mock_gc_correct,
    "halluc_repeat": _mock_gc_halluc_repeat,
    "halluc_confab": _mock_gc_halluc_confab,
}


# ---------------------------------------------------------------------------
# Sample generation
# ---------------------------------------------------------------------------

def generate_samples(utype: str, n: int, rng: np.random.Generator) -> List[UtteranceSample]:
    gen = _CURVE_GENERATORS[utype]
    samples = []
    for _ in range(n):
        curve = gen(rng)
        peak_layer = int(np.argmax(curve))
        # t_star: first layer where gc < threshold
        below = np.where(curve < T_STAR_THRESHOLD)[0]
        t_star = int(below[0]) if len(below) > 0 else N_ENCODER_LAYERS
        low_gc_frac = float(np.mean(curve < 0.2))
        samples.append(UtteranceSample(
            utype=utype,
            gc_curve=curve,
            mean_gc=float(np.mean(curve)),
            peak_gc=float(np.max(curve)),
            peak_layer=peak_layer,
            t_star=t_star,
            low_gc_fraction=low_gc_frac,
        ))
    return samples


# ---------------------------------------------------------------------------
# Statistical helpers
# ---------------------------------------------------------------------------

def _agg(samples: List[UtteranceSample], attr: str):
    vals = [getattr(s, attr) for s in samples]
    return {
        "mean": float(np.mean(vals)),
        "std": float(np.std(vals)),
        "min": float(np.min(vals)),
        "max": float(np.max(vals)),
    }


def _simple_auc(pos_scores, neg_scores):
    """Approximate AUC via rank statistic."""
    n_pos, n_neg = len(pos_scores), len(neg_scores)
    rank_sum = sum(1 for p in pos_scores for n in neg_scores if p > n)
    return rank_sum / (n_pos * n_neg)


def _cohens_d(a, b):
    pooled_std = np.sqrt((np.var(a) + np.var(b)) / 2 + 1e-9)
    return (np.mean(a) - np.mean(b)) / pooled_std


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def run_analysis(n: int, seed: int = 42) -> HallucinationResult:
    rng = np.random.default_rng(seed)
    all_samples = {t: generate_samples(t, n, rng) for t in UTTERANCE_TYPES}

    conditions = {}
    for utype, samples in all_samples.items():
        conditions[utype] = {
            "n": len(samples),
            "mean_gc": _agg(samples, "mean_gc"),
            "peak_gc": _agg(samples, "peak_gc"),
            "peak_layer": _agg(samples, "peak_layer"),
            "t_star": _agg(samples, "t_star"),
            "low_gc_fraction": _agg(samples, "low_gc_fraction"),
            "mean_gc_curve": [
                float(np.mean([s.gc_curve[k] for s in samples]))
                for k in range(N_ENCODER_LAYERS)
            ],
        }

    # Hypothesis tests
    correct_mean_gc   = [s.mean_gc for s in all_samples["correct"]]
    repeat_mean_gc    = [s.mean_gc for s in all_samples["halluc_repeat"]]
    confab_mean_gc    = [s.mean_gc for s in all_samples["halluc_confab"]]

    correct_tstar     = [s.t_star for s in all_samples["correct"]]
    repeat_tstar      = [s.t_star for s in all_samples["halluc_repeat"]]
    confab_tstar      = [s.t_star for s in all_samples["halluc_confab"]]

    correct_peak      = [s.peak_gc for s in all_samples["correct"]]
    halluc_peak       = [s.peak_gc for s in all_samples["halluc_repeat"] + all_samples["halluc_confab"]]

    correct_lowfrac   = [s.low_gc_fraction for s in all_samples["correct"]]
    halluc_lowfrac    = [s.low_gc_fraction for s in all_samples["halluc_repeat"] + all_samples["halluc_confab"]]

    h1_ok = np.mean(correct_mean_gc) > np.mean(repeat_mean_gc) > np.mean(confab_mean_gc)
    h2_ok = np.mean(correct_tstar) > np.mean(repeat_tstar) > np.mean(confab_tstar)
    h3_auc = _simple_auc(correct_peak, halluc_peak)
    h4_r = float(np.corrcoef(
        correct_lowfrac + halluc_lowfrac,
        [1]*len(correct_lowfrac) + [0]*len(halluc_lowfrac)
    )[0, 1])  # negative = low_gc_fraction increases for hallucinations

    hypothesis_tests = {
        "H1_mean_gc_ordering": {
            "correct": round(float(np.mean(correct_mean_gc)), 4),
            "halluc_repeat": round(float(np.mean(repeat_mean_gc)), 4),
            "halluc_confab": round(float(np.mean(confab_mean_gc)), 4),
            "confirmed": bool(h1_ok),
        },
        "H2_tstar_ordering": {
            "correct_mean": round(float(np.mean(correct_tstar)), 2),
            "halluc_repeat_mean": round(float(np.mean(repeat_tstar)), 2),
            "halluc_confab_mean": round(float(np.mean(confab_tstar)), 2),
            "confirmed": bool(h2_ok),
        },
        "H3_peak_gc_auc": {
            "auc_correct_vs_halluc": round(h3_auc, 3),
            "threshold_passed_080": bool(h3_auc >= 0.80),
            "confirmed": bool(h3_auc >= 0.80),
        },
        "H4_low_gc_fraction_correlation": {
            "pearson_r_with_correctness": round(h4_r, 3),
            "direction_correct": bool(h4_r < 0),  # low_gc_fraction higher for hallucinations
            "effect_d": round(float(_cohens_d(correct_lowfrac, halluc_lowfrac)), 3),
            "confirmed": bool(h4_r < -0.20),
        },
    }

    confirmed = [k for k, v in hypothesis_tests.items() if v.get("confirmed")]
    conclusions = [
        f"{'✅' if h1_ok else '❌'} H1: mean_gc ordering correct > repeat > confab — {'CONFIRMED' if h1_ok else 'FAILED'}",
        f"{'✅' if h2_ok else '❌'} H2: collapse onset ordering t*(correct) > t*(repeat) > t*(confab) — {'CONFIRMED' if h2_ok else 'FAILED'}",
        f"{'✅' if h3_auc >= 0.80 else '❌'} H3: peak_gc AUC={h3_auc:.3f} (correct vs halluc) — {'≥0.80 ✓' if h3_auc >= 0.80 else '<0.80 ✗'}",
        f"{'✅' if h4_r < -0.20 else '❌'} H4: low_gc_fraction r={h4_r:.3f} (neg=halluc have more low-gc layers) — {'CONFIRMED' if h4_r < -0.20 else 'FAILED'}",
        f"Summary: {len(confirmed)}/4 hypotheses confirmed on mock data (n={n} per condition, {N_ENCODER_LAYERS} layers)",
    ]

    return HallucinationResult(
        n_per_condition=n,
        n_layers=N_ENCODER_LAYERS,
        conditions=conditions,
        hypothesis_tests=hypothesis_tests,
        conclusions=conclusions,
    )


# ---------------------------------------------------------------------------
# Visualisation helpers
# ---------------------------------------------------------------------------

def _bar(val: float, width: int = 30) -> str:
    filled = int(round(val * width))
    return "█" * filled + "░" * (width - filled)


def print_report(result: HallucinationResult):
    print("=" * 65)
    print("  gc(k) Predicts Whisper Hallucination — Q110 Mock Results")
    print("=" * 65)

    print(f"\nN={result.n_per_condition} per condition | {result.n_layers} encoder layers\n")

    print("── Mean gc(k) by Layer ─────────────────────────────────────")
    labels = {"correct": "CORRECT      ", "halluc_repeat": "HALLUC_REPEAT", "halluc_confab": "HALLUC_CONFAB"}
    for utype in UTTERANCE_TYPES:
        cdata = result.conditions[utype]
        curve = cdata["mean_gc_curve"]
        label = labels[utype]
        bar_vals = "  ".join(f"k{i}:{_bar(v, 6)}{v:.2f}" for i, v in enumerate(curve))
        mean = cdata["mean_gc"]["mean"]
        print(f"  {label}  mean={mean:.3f}  |  {bar_vals}")

    print("\n── Key Statistics ──────────────────────────────────────────")
    headers = ["metric", "correct", "halluc_repeat", "halluc_confab"]
    metrics = ["mean_gc", "peak_gc", "t_star", "low_gc_fraction"]
    row_fmt = "  {:<20} {:>10} {:>15} {:>15}"
    print(row_fmt.format(*headers))
    for m in metrics:
        row = [m]
        for utype in UTTERANCE_TYPES:
            v = result.conditions[utype][m]["mean"]
            row.append(f"{v:.3f}")
        print(row_fmt.format(*row))

    print("\n── Hypothesis Tests ────────────────────────────────────────")
    for line in result.conclusions:
        print(f"  {line}")

    print("\n── Interpretation ──────────────────────────────────────────")
    print("  gc(k) low → model ignores audio → higher hallucination risk")
    print("  Proposed diagnostic: flag token if mean_gc < 0.20 in surrounding window")
    print("  Next step: test on real Whisper activations with known hallucination cases")
    print("=" * 65)


def print_ascii_bars(result: HallucinationResult):
    print("\n── gc(k) Profile (ASCII) ───────────────────────────────────")
    for utype in UTTERANCE_TYPES:
        cdata = result.conditions[utype]
        curve = cdata["mean_gc_curve"]
        print(f"\n  {utype.upper()}")
        for k, v in enumerate(curve):
            bar = _bar(v, 25)
            print(f"    Layer {k}: [{bar}] {v:.3f}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="gc(k) Hallucination Predictor — Q110 Mock")
    parser.add_argument("--n", type=int, default=N_STIMULI, help="Samples per condition")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--plot", action="store_true", help="ASCII bar chart")
    args = parser.parse_args()

    result = run_analysis(n=args.n, seed=args.seed)

    if args.json:
        out = {
            "n_per_condition": result.n_per_condition,
            "n_layers": result.n_layers,
            "conditions": result.conditions,
            "hypothesis_tests": result.hypothesis_tests,
            "conclusions": result.conclusions,
        }
        print(json.dumps(out, indent=2))
    else:
        print_report(result)
        if args.plot:
            print_ascii_bars(result)


if __name__ == "__main__":
    main()
