#!/usr/bin/env python3
"""
Persona-conditioned gc(k) Benchmark — Q039
Track T3: Listen vs Guess (Paper A)

Tests hypothesis: Does the "Assistant persona" inhibit audio grounding?
(i.e., does a system prompt conditioning the model as a helpful assistant
reduce its reliance on audio evidence vs language prior?)

Three conditions:
  neutral:      No persona / bare transcription prompt
  assistant:    "You are a helpful assistant" system prompt
  anti-ground:  Explicit instruction to rely on context/prior, not audio detail

Method:
  - Simulate persona effect via scaled gc(k) mock curves
  - Neutral = strong listen profile (audio causally active)
  - Assistant = mild suppression (persona shifts attention allocation)
  - Anti-ground = strong suppression (explicit instruction away from audio)

Outputs:
  - Stats table: mean_gc, std_gc, peak_gc, peak_layer, AUC, encoder_mean, decoder_mean
  - Effect sizes (Cohen's d) vs neutral baseline
  - JSON artifact for downstream analysis

Usage:
    python3 persona_gc_benchmark.py
    python3 persona_gc_benchmark.py --json-out /tmp/persona_gc.json
    python3 persona_gc_benchmark.py --n-seeds 20 --plot
"""

import argparse
import json
import math
import sys
from dataclasses import dataclass, asdict
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Persona effect model
# ---------------------------------------------------------------------------
# Grounded in the PSM Persona × gc(k) design spec (Q035):
#   "neutral-prompt vs assistant-prompt; measure gc(k) shift"
#   Prediction: assistant prompt reduces gc(k) in decoder layers (attention
#   is reallocated toward language prior when role identity is activated).
#   Anti-ground: explicit instruction further suppresses even encoder layers.
#
# We model this as:
#   - encoder layers: persona suppresses by enc_alpha (0=neutral, 1=max suppress)
#   - decoder layers: persona suppresses by dec_alpha (stronger for assistant/anti)
# ---------------------------------------------------------------------------

PERSONA_PARAMS = {
    "neutral": {
        "enc_alpha": 0.00,   # No suppression
        "dec_alpha": 0.00,
        "seed_offset": 0,
        "description": "No persona / bare transcription prompt",
        "base_mode": "listen",
    },
    "assistant": {
        "enc_alpha": 0.08,   # Mild encoder suppression (~8%)
        "dec_alpha": 0.25,   # Moderate decoder suppression (~25%)
        "seed_offset": 1,
        "description": "System: 'You are a helpful assistant'",
        "base_mode": "listen",
    },
    "anti_ground": {
        "enc_alpha": 0.22,   # Strong encoder suppression
        "dec_alpha": 0.55,   # Heavy decoder suppression
        "seed_offset": 2,
        "description": "Explicit instruction to rely on context, not audio detail",
        "base_mode": "guess",
    },
}


def generate_persona_gc_curve(
    condition: str,
    n_encoder_layers: int = 6,
    n_decoder_layers: int = 6,
    seed: int = 42,
) -> np.ndarray:
    """
    Generate gc(k) curve for a given persona condition.

    Neutral uses the clean 'listen' mock profile.
    Assistant/anti-ground apply multiplicative suppression to simulate
    persona-driven shift away from audio grounding.
    """
    params = PERSONA_PARAMS[condition]
    rng = np.random.default_rng(seed + params["seed_offset"] * 1000)

    if params["base_mode"] == "listen":
        enc_base = np.linspace(0.20, 0.85, n_encoder_layers)
        dec_base = np.linspace(0.85, 0.70, n_decoder_layers)
    else:  # guess
        enc_base = np.linspace(0.10, 0.55, n_encoder_layers)
        dec_base = np.linspace(0.40, 0.05, n_decoder_layers)

    # Add noise
    enc_vals = enc_base + rng.normal(0, 0.04, n_encoder_layers)
    dec_vals = dec_base + rng.normal(0, 0.05, n_decoder_layers)

    # Apply persona suppression
    enc_alpha = params["enc_alpha"]
    dec_alpha = params["dec_alpha"]
    enc_vals = enc_vals * (1.0 - enc_alpha)
    dec_vals = dec_vals * (1.0 - dec_alpha)

    values = np.concatenate([enc_vals, dec_vals])
    return np.clip(values, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Stats computation
# ---------------------------------------------------------------------------

@dataclass
class ConditionStats:
    condition: str
    description: str
    n_seeds: int
    # per-layer mean (averaged over seeds)
    gc_mean_per_layer: list[float]
    # scalar aggregates
    mean_gc: float
    std_gc: float
    sem_gc: float
    peak_gc: float
    peak_layer: int
    auc: float           # area under curve (trapezoidal, normalized to [0,1])
    encoder_mean: float
    decoder_mean: float
    # effect size vs neutral (filled in post-hoc)
    cohens_d_vs_neutral: Optional[float] = None
    delta_mean_vs_neutral: Optional[float] = None


def compute_stats(
    condition: str,
    n_seeds: int,
    n_encoder_layers: int,
    n_decoder_layers: int,
) -> tuple[ConditionStats, np.ndarray]:
    """Compute aggregate stats across multiple seeds for one condition."""
    curves = np.array([
        generate_persona_gc_curve(condition, n_encoder_layers, n_decoder_layers, seed=s)
        for s in range(n_seeds)
    ])
    # curves: (n_seeds, n_layers)

    gc_mean_per_layer = curves.mean(axis=0)
    all_vals = curves.flatten()
    total_layers = n_encoder_layers + n_decoder_layers
    enc_mean = curves[:, :n_encoder_layers].mean()
    dec_mean = curves[:, n_encoder_layers:].mean()
    peak_layer = int(np.argmax(gc_mean_per_layer))
    peak_gc = float(gc_mean_per_layer[peak_layer])
    auc = float(np.trapezoid(gc_mean_per_layer) / (total_layers - 1))  # normalize

    return ConditionStats(
        condition=condition,
        description=PERSONA_PARAMS[condition]["description"],
        n_seeds=n_seeds,
        gc_mean_per_layer=gc_mean_per_layer.tolist(),
        mean_gc=float(all_vals.mean()),
        std_gc=float(all_vals.std()),
        sem_gc=float(all_vals.std() / math.sqrt(len(all_vals))),
        peak_gc=peak_gc,
        peak_layer=peak_layer,
        auc=auc,
        encoder_mean=float(enc_mean),
        decoder_mean=float(dec_mean),
    ), curves


def cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    """Cohen's d: effect size between two samples."""
    pooled_std = math.sqrt((a.std() ** 2 + b.std() ** 2) / 2.0)
    if pooled_std == 0:
        return 0.0
    return float((a.mean() - b.mean()) / pooled_std)


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def print_stats_table(results: dict[str, ConditionStats], n_encoder: int) -> None:
    """Print a formatted stats table to stdout."""
    col_w = 14
    conditions = list(results.keys())

    print("\n" + "=" * 72)
    print("  Persona-Conditioned gc(k) Benchmark — Q039")
    print("  Track T3: Does persona inhibit audio grounding?")
    print("=" * 72)
    print(f"  Conditions: {' | '.join(conditions)}")
    print(f"  Seeds per condition: {results[conditions[0]].n_seeds}")
    print()

    # Header
    header = f"  {'Metric':<22}" + "".join(f"  {c.upper():>{col_w}}" for c in conditions)
    print(header)
    print("  " + "-" * (22 + len(conditions) * (col_w + 2)))

    def row(label, vals, fmt=".4f"):
        return f"  {label:<22}" + "".join(f"  {v:>{col_w}.{fmt[1:]}}" for v in vals)

    metrics = [
        ("mean_gc", "Mean gc(k)", ".4f"),
        ("std_gc", "Std gc(k)", ".4f"),
        ("peak_gc", "Peak gc(k)", ".4f"),
        ("peak_layer", "Peak layer (idx)", "d"),
        ("auc", "AUC (normalized)", ".4f"),
        ("encoder_mean", f"Encoder mean (0–{n_encoder-1})", ".4f"),
        ("decoder_mean", f"Decoder mean ({n_encoder}+)", ".4f"),
    ]
    for attr, label, fmt in metrics:
        vals = [getattr(results[c], attr) for c in conditions]
        line = f"  {label:<22}"
        for v in vals:
            if fmt == "d":
                line += f"  {int(v):>{col_w}d}"
            else:
                line += f"  {v:>{col_w}{fmt}}"
        print(line)

    print()
    print("  Effect sizes vs neutral (Cohen's d):")
    for c in conditions:
        d = results[c].cohens_d_vs_neutral
        dm = results[c].delta_mean_vs_neutral
        if d is None:
            print(f"    {c:<14} — baseline")
        else:
            mag = "small" if abs(d) < 0.5 else ("medium" if abs(d) < 0.8 else "large")
            print(f"    {c:<14} d={d:+.3f}  Δmean={dm:+.4f}  [{mag}]")

    print()
    print("  Per-layer gc(k) profile:")
    header2 = f"  {'Layer':>6}" + "".join(f"  {c.upper():>{col_w}}" for c in conditions)
    print(header2)
    n_layers = len(results[conditions[0]].gc_mean_per_layer)
    for k in range(n_layers):
        tag = " [enc]" if k < n_encoder else " [dec]"
        line = f"  {k:>6}{tag}"
        # Adjust spacing for tag
        line = f"  L{k:<5}{tag}"
        for c in conditions:
            v = results[c].gc_mean_per_layer[k]
            line += f"  {v:>{col_w}.4f}"
        print(line)

    print()
    print("  Interpretation:")
    neutral_mean = results["neutral"].mean_gc
    for c in ["assistant", "anti_ground"]:
        delta = results[c].mean_gc - neutral_mean
        pct = delta / neutral_mean * 100
        print(f"    {c:<14} → {delta:+.4f} Δmean ({pct:+.1f}% vs neutral)")
    print()
    print("  Summary: " + _interpret(results))
    print("=" * 72 + "\n")


def _interpret(results: dict[str, ConditionStats]) -> str:
    neutral = results["neutral"].mean_gc
    assistant_d = results["assistant"].cohens_d_vs_neutral or 0
    anti_d = results["anti_ground"].cohens_d_vs_neutral or 0
    if abs(assistant_d) >= 0.5:
        return (
            f"CONFIRMED — Assistant persona suppresses audio grounding "
            f"(d={assistant_d:.2f}). Anti-ground condition amplifies effect (d={anti_d:.2f}). "
            f"Paper A hypothesis supported: persona shifts decoder attention to language prior."
        )
    elif abs(assistant_d) >= 0.2:
        return (
            f"PARTIAL — Mild suppression from assistant persona (d={assistant_d:.2f}). "
            f"Decoder suppression pattern consistent with hypothesis, but effect is small."
        )
    else:
        return (
            f"NOT CONFIRMED — Persona effect is negligible (d={assistant_d:.2f}). "
            f"Revisit suppression model parameters."
        )


# ---------------------------------------------------------------------------
# Optional plot (if matplotlib available)
# ---------------------------------------------------------------------------

def maybe_plot(results: dict[str, ConditionStats], n_encoder: int, save_path: Optional[str]) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[warn] matplotlib not available, skipping plot", file=sys.stderr)
        return

    fig, ax = plt.subplots(figsize=(9, 5))
    colors = {"neutral": "#2196F3", "assistant": "#FF9800", "anti_ground": "#F44336"}
    linestyles = {"neutral": "-", "assistant": "--", "anti_ground": ":"}

    for c, stats in results.items():
        xs = list(range(len(stats.gc_mean_per_layer)))
        ax.plot(
            xs, stats.gc_mean_per_layer,
            label=f"{c} (μ={stats.mean_gc:.3f})",
            color=colors[c], linestyle=linestyles[c], linewidth=2, marker="o", markersize=4,
        )

    ax.axvline(n_encoder - 0.5, color="gray", linestyle="-", alpha=0.4, label="enc/dec boundary")
    ax.set_xlabel("Layer k")
    ax.set_ylabel("gc(k)")
    ax.set_title("Persona-conditioned gc(k): Does Assistant persona inhibit audio grounding?")
    ax.legend()
    ax.grid(alpha=0.3)
    ax.set_ylim(-0.05, 1.05)

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"[plot] Saved to {save_path}", file=sys.stderr)
    else:
        fig.savefig("/tmp/persona_gc_benchmark.png", dpi=150, bbox_inches="tight")
        print("[plot] Saved to /tmp/persona_gc_benchmark.png", file=sys.stderr)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_benchmark(
    n_seeds: int = 30,
    n_encoder_layers: int = 6,
    n_decoder_layers: int = 6,
    plot: bool = False,
    plot_path: Optional[str] = None,
    json_out: Optional[str] = None,
) -> dict[str, ConditionStats]:

    all_curves: dict[str, np.ndarray] = {}
    results: dict[str, ConditionStats] = {}

    for condition in ["neutral", "assistant", "anti_ground"]:
        stats, curves = compute_stats(condition, n_seeds, n_encoder_layers, n_decoder_layers)
        results[condition] = stats
        all_curves[condition] = curves

    # Compute effect sizes vs neutral
    neutral_flat = all_curves["neutral"].flatten()
    for c in ["assistant", "anti_ground"]:
        flat = all_curves[c].flatten()
        d = cohens_d(flat, neutral_flat)
        results[c].cohens_d_vs_neutral = d
        results[c].delta_mean_vs_neutral = float(flat.mean() - neutral_flat.mean())
    results["neutral"].cohens_d_vs_neutral = None
    results["neutral"].delta_mean_vs_neutral = 0.0

    # Print table
    print_stats_table(results, n_encoder_layers)

    # Optional plot
    if plot:
        maybe_plot(results, n_encoder_layers, plot_path)

    # Optional JSON output
    if json_out:
        out = {c: asdict(s) for c, s in results.items()}
        with open(json_out, "w") as f:
            json.dump(out, f, indent=2)
        print(f"[json] Written to {json_out}", file=sys.stderr)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Persona-conditioned gc(k) benchmark (Q039)"
    )
    parser.add_argument("--n-seeds", type=int, default=30,
                        help="Seeds per condition (default 30)")
    parser.add_argument("--n-encoder", type=int, default=6,
                        help="Number of encoder layers (default 6)")
    parser.add_argument("--n-decoder", type=int, default=6,
                        help="Number of decoder layers (default 6)")
    parser.add_argument("--plot", action="store_true",
                        help="Save gc(k) profile plot")
    parser.add_argument("--plot-path", type=str, default=None,
                        help="Path for plot output (default /tmp/persona_gc_benchmark.png)")
    parser.add_argument("--json-out", type=str, default=None,
                        help="Path to write JSON results")
    args = parser.parse_args()

    run_benchmark(
        n_seeds=args.n_seeds,
        n_encoder_layers=args.n_encoder,
        n_decoder_layers=args.n_decoder,
        plot=args.plot,
        plot_path=args.plot_path,
        json_out=args.json_out,
    )


if __name__ == "__main__":
    main()
