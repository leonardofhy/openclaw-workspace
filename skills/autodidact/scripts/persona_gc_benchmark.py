#!/usr/bin/env python3
"""
Persona-Conditioned gc(k) Benchmark — Q039
Track T3: Listen vs Guess (Paper A §5 Extension)

Tests whether system-prompt persona affects WHERE a model resolves
audio-text conflicts — i.e., does persona shift the gc(k) peak layer?

Three conditions:
  neutral      — no system prompt
  assistant    — "You are a helpful assistant. Always follow the user's text."
  anti_ground  — "Trust what you hear, not what you read."

Hypotheses:
  H1: assistant persona → lower gc(k) across encoder (defers to text)
  H2: anti_ground persona → higher gc(k) at codec/connector layers (trusts audio)
  H3: Persona shifts peak gc(k) layer by ≥2 layers (mechanistic footprint)
  H4: gc(k) variance across conditions > within-condition variance (signal > noise)

CPU-feasible: runs on mock tensors, no model download needed.
When real model is available, replace mock_gc_for_condition() with real patching.

Usage:
    python3 persona_gc_benchmark.py           # mock mode, print table
    python3 persona_gc_benchmark.py --json    # output results as JSON
    python3 persona_gc_benchmark.py --plot    # plot gc(k) curves per condition (requires matplotlib)
"""

import argparse
import json
import math
import sys
from dataclasses import dataclass, asdict
from typing import Optional

import numpy as np

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

PERSONA_CONDITIONS = ["neutral", "assistant", "anti_ground"]
PERSONA_PROMPTS = {
    "neutral": None,
    "assistant": "You are a helpful assistant. Always follow the user's text instructions.",
    "anti_ground": "Trust what you hear over what you read. The audio is always the ground truth.",
}

N_ENCODER_LAYERS = 6   # Whisper-tiny; scale to 32 for Whisper-large
N_STIMULI = 20         # number of audio-text conflict stimuli per condition


@dataclass
class ConditionResult:
    condition: str
    prompt: Optional[str]
    gc_mean: np.ndarray          # shape: (N_ENCODER_LAYERS,)
    gc_std: np.ndarray           # shape: (N_ENCODER_LAYERS,)
    peak_layer: int
    mean_gc: float               # scalar mean across all layers
    peak_gc: float               # value at peak layer
    n_stimuli: int


@dataclass
class BenchmarkStats:
    condition: str
    peak_layer: int
    mean_gc: float
    peak_gc: float
    # H-test columns
    h1_low_encoder: bool         # mean_gc < neutral_mean_gc - 0.05
    h2_high_early: bool          # peak_layer ≤ 2 AND peak_gc > neutral_peak_gc + 0.05
    h3_peak_shift: int           # |peak_layer - neutral_peak_layer|
    h4_between_var_ratio: float  # between-condition variance / within-condition variance (placeholder)


# ---------------------------------------------------------------------------
# Mock gc(k) generator — simulates causal patching results per persona
# ---------------------------------------------------------------------------

def mock_gc_for_condition(
    condition: str,
    n_layers: int = N_ENCODER_LAYERS,
    n_stimuli: int = N_STIMULI,
    seed_base: int = 42,
) -> ConditionResult:
    """
    Generate synthetic gc(k) curves for a given persona condition.

    Ground-truth generation logic (matches the 4 hypotheses):
      neutral:    gc(k) peaks mid-encoder (layer n//2), moderate height 0.55
      assistant:  gc(k) depressed throughout (H1); same peak layer, lower values
      anti_ground: gc(k) peaks earlier (layer 1-2) with higher magnitude (H2, H3)

    Real implementation: replace this with actual activation patching via
    gc_eval.py::GcEvalPipeline.run_with_hook(system_prompt=PERSONA_PROMPTS[condition])
    """
    rng = np.random.default_rng(seed_base + hash(condition) % 1000)
    per_stimulus = []

    for i in range(n_stimuli):
        stim_rng = np.random.default_rng(seed_base + i * 7 + hash(condition) % 999)
        layers = np.arange(n_layers, dtype=float)

        if condition == "neutral":
            # Bell curve peaking at middle layer
            center = n_layers / 2.0
            sigma = n_layers / 4.0
            gc = 0.55 * np.exp(-0.5 * ((layers - center) / sigma) ** 2)
        elif condition == "assistant":
            # Depressed — text persona reduces audio reliance (H1)
            center = n_layers / 2.0
            sigma = n_layers / 4.0
            gc = 0.38 * np.exp(-0.5 * ((layers - center) / sigma) ** 2)
        elif condition == "anti_ground":
            # Earlier peak, higher magnitude (H2 + H3)
            center = max(1.0, n_layers / 4.0)
            sigma = n_layers / 5.0
            gc = 0.70 * np.exp(-0.5 * ((layers - center) / sigma) ** 2)
        else:
            raise ValueError(f"Unknown condition: {condition!r}")

        # Add per-stimulus noise
        noise = stim_rng.normal(0, 0.04, n_layers)
        gc = np.clip(gc + noise, 0.0, 1.0)
        per_stimulus.append(gc)

    stacked = np.stack(per_stimulus, axis=0)   # (n_stimuli, n_layers)
    gc_mean = stacked.mean(axis=0)
    gc_std = stacked.std(axis=0)
    peak_layer = int(np.argmax(gc_mean))

    return ConditionResult(
        condition=condition,
        prompt=PERSONA_PROMPTS[condition],
        gc_mean=gc_mean,
        gc_std=gc_std,
        peak_layer=peak_layer,
        mean_gc=float(gc_mean.mean()),
        peak_gc=float(gc_mean[peak_layer]),
        n_stimuli=n_stimuli,
    )


# ---------------------------------------------------------------------------
# Hypothesis tests
# ---------------------------------------------------------------------------

def run_hypothesis_tests(
    results: dict[str, ConditionResult],
) -> dict[str, BenchmarkStats]:
    """
    Compute hypothesis test outcomes against neutral baseline.
    Returns BenchmarkStats for each condition.
    """
    neutral = results["neutral"]
    stats = {}

    for cond, res in results.items():
        h1 = res.mean_gc < (neutral.mean_gc - 0.05)
        h2 = (res.peak_layer <= 2) and (res.peak_gc > neutral.peak_gc + 0.05)
        h3 = abs(res.peak_layer - neutral.peak_layer)

        # H4: rough between/within variance ratio (simplistic for mock)
        gc_values = np.stack([r.gc_mean for r in results.values()])
        between_var = float(gc_values.mean(axis=1).var())
        within_var = float(np.mean([r.gc_std.mean() for r in results.values()]))
        h4_ratio = between_var / max(within_var, 1e-8)

        stats[cond] = BenchmarkStats(
            condition=cond,
            peak_layer=res.peak_layer,
            mean_gc=round(res.mean_gc, 4),
            peak_gc=round(res.peak_gc, 4),
            h1_low_encoder=bool(h1),
            h2_high_early=bool(h2),
            h3_peak_shift=int(h3),
            h4_between_var_ratio=round(h4_ratio, 4),
        )

    return stats


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def print_stats_table(stats: dict[str, BenchmarkStats], results: dict[str, ConditionResult]) -> None:
    """Print a human-readable results table."""
    print("\n" + "=" * 70)
    print("  Persona-Conditioned gc(k) Benchmark — Q039")
    print("=" * 70)
    print(f"  Encoder layers: {N_ENCODER_LAYERS}  |  Stimuli per condition: {N_STIMULI}")
    print("  NOTE: Mock mode — replace mock_gc_for_condition() with real patching")
    print("-" * 70)
    print(f"{'Condition':<14} {'Peak Layer':>10} {'Mean gc(k)':>12} {'Peak gc(k)':>12} {'Peak Shift':>11}")
    print("-" * 70)
    for cond in PERSONA_CONDITIONS:
        s = stats[cond]
        shift_str = f"{s.h3_peak_shift:+d}" if cond != "neutral" else "—"
        print(f"  {cond:<12} {s.peak_layer:>10} {s.mean_gc:>12.4f} {s.peak_gc:>12.4f} {shift_str:>11}")
    print("-" * 70)

    print("\n  Hypothesis Test Results:")
    neutral_stats = stats["neutral"]
    for cond in PERSONA_CONDITIONS:
        s = stats[cond]
        if cond == "neutral":
            print(f"  neutral: baseline reference")
            continue
        print(f"\n  [{cond}]")
        h1_icon = "✅" if (cond == "assistant" and s.h1_low_encoder) or (cond == "anti_ground" and not s.h1_low_encoder) else "❌"
        h2_icon = "✅" if (cond == "anti_ground" and s.h2_high_early) else ("N/A" if cond == "assistant" else "❌")
        h3_icon = "✅" if s.h3_peak_shift >= 2 else "❌"
        print(f"    H1 (lower encoder gc): {h1_icon}  mean_gc={s.mean_gc:.4f} vs neutral {neutral_stats.mean_gc:.4f}")
        print(f"    H2 (early+high peak):  {h2_icon}  peak_layer={s.peak_layer}, peak_gc={s.peak_gc:.4f}")
        print(f"    H3 (≥2 layer shift):   {h3_icon}  |shift|={s.h3_peak_shift}")

    # H4 — report once
    sample = list(stats.values())[0]
    h4_icon = "✅" if sample.h4_between_var_ratio > 1.5 else "❌"
    print(f"\n  H4 (between/within variance ratio): {h4_icon}  ratio={sample.h4_between_var_ratio:.4f} (threshold: >1.5)")

    print("\n  gc(k) curves (mean ± std per layer):")
    print(f"  {'Layer':<6}", end="")
    for cond in PERSONA_CONDITIONS:
        print(f"  {cond:<20}", end="")
    print()
    for k in range(N_ENCODER_LAYERS):
        print(f"  {k:<6}", end="")
        for cond in PERSONA_CONDITIONS:
            r = results[cond]
            print(f"  {r.gc_mean[k]:.3f} ± {r.gc_std[k]:.3f}       ", end="")
        print()
    print("=" * 70)


def to_json_safe(stats: dict, results: dict) -> dict:
    """Convert results to JSON-serializable dict."""
    out = {"conditions": {}}
    for cond in PERSONA_CONDITIONS:
        s = stats[cond]
        r = results[cond]
        out["conditions"][cond] = {
            "peak_layer": s.peak_layer,
            "mean_gc": s.mean_gc,
            "peak_gc": s.peak_gc,
            "gc_mean_per_layer": r.gc_mean.tolist(),
            "gc_std_per_layer": r.gc_std.tolist(),
            "h1_low_encoder": s.h1_low_encoder,
            "h2_high_early": s.h2_high_early,
            "h3_peak_shift": s.h3_peak_shift,
            "h4_between_var_ratio": s.h4_between_var_ratio,
        }
    return out


def plot_curves(results: dict[str, ConditionResult]) -> None:
    """Plot gc(k) curves for all conditions (requires matplotlib)."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available — skipping plot")
        return

    fig, ax = plt.subplots(figsize=(8, 5))
    layers = np.arange(N_ENCODER_LAYERS)
    colors = {"neutral": "gray", "assistant": "royalblue", "anti_ground": "firebrick"}

    for cond, r in results.items():
        ax.plot(layers, r.gc_mean, label=cond, color=colors[cond], marker="o", linewidth=2)
        ax.fill_between(
            layers,
            r.gc_mean - r.gc_std,
            r.gc_mean + r.gc_std,
            alpha=0.15,
            color=colors[cond],
        )

    ax.set_xlabel("Encoder Layer k")
    ax.set_ylabel("gc(k) — Causal Grounding Score")
    ax.set_title("Persona-Conditioned gc(k) Benchmark (Q039)\nMock mode — replace with real patching")
    ax.legend()
    ax.set_ylim(0, 1)
    ax.set_xticks(layers)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    out_path = "memory/learning/cycles/persona_gc_benchmark_plot.png"
    plt.savefig(out_path, dpi=120)
    print(f"\n  Plot saved → {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Persona-Conditioned gc(k) Benchmark (Q039)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--plot", action="store_true", help="Generate matplotlib plot")
    parser.add_argument("--layers", type=int, default=N_ENCODER_LAYERS, help=f"Number of encoder layers (default: {N_ENCODER_LAYERS})")
    parser.add_argument("--stimuli", type=int, default=N_STIMULI, help=f"Stimuli per condition (default: {N_STIMULI})")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    n_layers = args.layers
    n_stimuli = args.stimuli

    # Run benchmark
    results = {}
    for cond in PERSONA_CONDITIONS:
        results[cond] = mock_gc_for_condition(
            cond,
            n_layers=n_layers,
            n_stimuli=n_stimuli,
            seed_base=args.seed,
        )

    stats = run_hypothesis_tests(results)

    if args.json:
        print(json.dumps(to_json_safe(stats, results), indent=2))
    else:
        print_stats_table(stats, results)

    if args.plot:
        plot_curves(results)

    # Validation: ensure all conditions produced finite output
    for cond, r in results.items():
        assert np.all(np.isfinite(r.gc_mean)), f"NaN/Inf in gc_mean for {cond}"
        assert np.all((r.gc_mean >= 0) & (r.gc_mean <= 1)), f"gc_mean out of [0,1] for {cond}"

    return 0


if __name__ == "__main__":
    sys.exit(main())
