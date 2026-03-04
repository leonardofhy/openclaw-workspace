#!/usr/bin/env python3
"""
gc(k) Multi-Condition Experiment Runner — Paper A T3
Track T3: Listen vs Guess

Orchestrates gc_eval.py across 3 synthetic conditions:
  1. listen  — clean audio, high gc throughout (audio-driven)
  2. mid     — 50% masked, gc drops mid-decoder
  3. guess   — full noise/silence, gc collapses after encoder

Produces:
  - gc_summary.json         (stats per condition)
  - gc_curves_comparison.png (if matplotlib available)

Usage:
    python3 gc_experiment_runner.py                     # mock mode (Tier 0)
    python3 gc_experiment_runner.py --n-seeds 5         # avg over 5 seeds
    python3 gc_experiment_runner.py --json              # JSON output only
    python3 gc_experiment_runner.py --plot              # save plot
"""

import argparse
import json
import sys
import os
from typing import Optional

import numpy as np

# Add script dir to path so gc_eval imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gc_eval import generate_mock_gc_curve, print_curve


# ---------------------------------------------------------------------------
# Condition definitions
# ---------------------------------------------------------------------------

CONDITIONS = [
    {
        "id": "clean_vs_noise",
        "label": "Clean vs Gaussian Noise",
        "mode": "listen",
        "description": "Baseline listen regime — gc(k) should peak and stay elevated",
        "expected": "Peak at enc 3-5, mean_dec > 0.6",
    },
    {
        "id": "clean_vs_partial_mask",
        "label": "Clean vs 50% Masked",
        "mode": "listen",  # mid-confidence: use listen mode with lower amplitude
        "mid_scale": 0.65,  # scale down gc values to simulate partial uncertainty
        "description": "Mid-confidence — gc(k) partially elevated",
        "expected": "Peak at enc 2-4, drops to ~0.3 by dec layer 3",
    },
    {
        "id": "clean_vs_silence",
        "label": "Clean vs Full Silence",
        "mode": "guess",
        "description": "Extreme guess regime — decoder relies on language prior",
        "expected": "gc < 0.1 after enc layer 2",
    },
]


# ---------------------------------------------------------------------------
# Per-condition runner (mock)
# ---------------------------------------------------------------------------

def run_condition_mock(
    condition: dict,
    n_encoder_layers: int = 6,
    n_decoder_layers: int = 6,
    seeds: list[int] | None = None,
) -> dict:
    """Run a condition across N seeds, return stats."""
    if seeds is None:
        seeds = [42]

    all_gc = []
    for seed in seeds:
        result = generate_mock_gc_curve(
            n_encoder_layers=n_encoder_layers,
            n_decoder_layers=n_decoder_layers,
            seed=seed,
            mode=condition["mode"],
        )
        gc = np.array(result["gc_values"])
        # Apply mid-scale if specified (simulate partial masking)
        if "mid_scale" in condition:
            gc = gc * condition["mid_scale"]
        all_gc.append(gc)

    gc_array = np.stack(all_gc, axis=0)  # (n_seeds, n_layers)
    mean_gc = gc_array.mean(axis=0)
    std_gc = gc_array.std(axis=0)
    n_enc = n_encoder_layers

    # Key statistics
    listen_threshold = next(
        (i for i, v in enumerate(mean_gc[:n_enc]) if v > 0.5),
        None,
    )
    guess_transition = next(
        (i for i, v in enumerate(mean_gc[n_enc:]) if v < 0.2),
        None,
    )
    if guess_transition is not None:
        guess_transition += n_enc  # absolute layer index

    layers = list(range(n_encoder_layers + n_decoder_layers))
    return {
        "condition_id": condition["id"],
        "label": condition["label"],
        "description": condition["description"],
        "expected": condition["expected"],
        "n_seeds": len(seeds),
        "n_encoder_layers": n_encoder_layers,
        "n_decoder_layers": n_decoder_layers,
        "layers": layers,
        "mean_gc": mean_gc.tolist(),
        "std_gc": std_gc.tolist(),
        "stats": {
            "mean_enc": float(mean_gc[:n_enc].mean()),
            "mean_dec": float(mean_gc[n_enc:].mean()),
            "peak_layer": int(np.argmax(mean_gc)),
            "peak_value": float(mean_gc.max()),
            "listen_threshold_layer": listen_threshold,
            "guess_transition_layer": guess_transition,
        },
    }


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def print_summary_table(results: list[dict]) -> None:
    """Print comparison table across conditions."""
    print("\n" + "=" * 70)
    print("gc(k) Multi-Condition Comparison")
    print("=" * 70)
    header = f"{'Condition':<30}  {'Enc mean':>9}  {'Dec mean':>9}  {'Peak layer':>10}  {'Peak gc':>8}"
    print(header)
    print("-" * 70)
    for r in results:
        s = r["stats"]
        print(
            f"{r['label']:<30}  {s['mean_enc']:>9.3f}  {s['mean_dec']:>9.3f}"
            f"  {s['peak_layer']:>10}  {s['peak_value']:>8.3f}"
        )
    print()

    # Interpretation summary
    print("Interpretation:")
    for r in results:
        s = r["stats"]
        if s["mean_enc"] > 0.45 and s["mean_dec"] > 0.60:
            verdict = "✅ LISTEN — audio causally dominant throughout"
        elif s["mean_dec"] < 0.25:
            verdict = "⚠️  GUESS — model ignores audio in decoder"
        else:
            verdict = "〰️  MID — mixed listen/guess regime"
        lt = s["listen_threshold_layer"]
        gt = s["guess_transition_layer"]
        detail = (
            f"(listen_threshold=L{lt if lt is not None else 'none'}, "
            f"guess_transition=L{gt if gt is not None else 'none'})"
        )
        print(f"  {r['label']}: {verdict} {detail}")
    print()


def print_per_layer(result: dict) -> None:
    """Delegate to gc_eval.print_curve for a single condition."""
    print(f"\n--- {result['label']} ---")
    print_curve({
        "layers": result["layers"],
        "gc_values": result["mean_gc"],
        "n_encoder_layers": result["n_encoder_layers"],
        "n_decoder_layers": result["n_decoder_layers"],
        "mode": result["condition_id"],
    })


def plot_comparison(results: list[dict], output_path: str = "/tmp/gc_curves_comparison.png") -> None:
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
    except ImportError:
        print("[gc_runner] matplotlib not available; skipping plot.", file=sys.stderr)
        return

    colors = ["#2196F3", "#FF9800", "#F44336"]  # blue, orange, red
    n_enc = results[0]["n_encoder_layers"]
    layers = results[0]["layers"]

    fig, (ax_main, ax_stats) = plt.subplots(1, 2, figsize=(14, 5))

    # --- Left: gc(k) curves with std bands ---
    for i, (r, color) in enumerate(zip(results, colors)):
        mean = np.array(r["mean_gc"])
        std = np.array(r["std_gc"])
        ax_main.plot(layers, mean, color=color, linewidth=2, label=r["label"], marker="o", markersize=4)
        ax_main.fill_between(layers, mean - std, mean + std, color=color, alpha=0.15)

    ax_main.axvline(x=n_enc - 0.5, color="gray", linestyle="--", alpha=0.5, label="Enc/Dec boundary")
    ax_main.axhline(y=0.5, color="green", linestyle=":", alpha=0.4, label="gc=0.5 (balanced)")
    ax_main.set_xlabel("Layer k", fontsize=11)
    ax_main.set_ylabel("gc(k) — causal contribution of audio", fontsize=11)
    ax_main.set_title("gc(k) Curves: Listen vs Guess Regimes", fontsize=12)
    ax_main.legend(fontsize=9, loc="upper right")
    ax_main.set_ylim(0, 1.05)
    ax_main.set_xticks(layers)
    ax_main.set_xticklabels([f"{'E' if l < n_enc else 'D'}{l if l < n_enc else l - n_enc}" for l in layers])
    ax_main.grid(True, alpha=0.3)

    # --- Right: bar chart of enc_mean vs dec_mean ---
    x = np.arange(len(results))
    width = 0.35
    enc_means = [r["stats"]["mean_enc"] for r in results]
    dec_means = [r["stats"]["mean_dec"] for r in results]
    ax_stats.bar(x - width / 2, enc_means, width, label="Encoder mean gc", color=[c + "bb" for c in colors], edgecolor="black", linewidth=0.5)
    ax_stats.bar(x + width / 2, dec_means, width, label="Decoder mean gc", color=colors, edgecolor="black", linewidth=0.5)
    ax_stats.set_xticks(x)
    ax_stats.set_xticklabels([r["label"].split(" vs ")[1] if " vs " in r["label"] else r["label"] for r in results], fontsize=9)
    ax_stats.set_ylabel("Mean gc(k)", fontsize=11)
    ax_stats.set_title("Encoder vs Decoder gc Summary", fontsize=12)
    ax_stats.legend(fontsize=9)
    ax_stats.set_ylim(0, 1.0)
    ax_stats.axhline(y=0.5, color="green", linestyle=":", alpha=0.4)
    ax_stats.grid(True, alpha=0.3, axis="y")

    plt.suptitle("Paper A — T3: Listen-vs-Guess gc(k) Analysis (Mock Mode)", fontsize=11, style="italic", y=1.01)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"[gc_runner] Plot saved: {output_path}", file=sys.stderr)
    plt.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="gc(k) multi-condition experiment runner")
    parser.add_argument("--n-seeds", type=int, default=3, help="Number of random seeds to avg over")
    parser.add_argument("--n-encoder-layers", type=int, default=6)
    parser.add_argument("--n-decoder-layers", type=int, default=6)
    parser.add_argument("--json", action="store_true", help="Output raw JSON summary")
    parser.add_argument("--verbose", action="store_true", help="Print per-layer gc tables")
    parser.add_argument("--plot", action="store_true", help="Save comparison plot")
    parser.add_argument("--out-json", default="/tmp/gc_summary.json", help="JSON output path")
    parser.add_argument("--out-plot", default="/tmp/gc_curves_comparison.png", help="Plot output path")
    args = parser.parse_args()

    seeds = list(range(args.n_seeds))

    results = []
    for condition in CONDITIONS:
        r = run_condition_mock(
            condition=condition,
            n_encoder_layers=args.n_encoder_layers,
            n_decoder_layers=args.n_decoder_layers,
            seeds=seeds,
        )
        results.append(r)

    if args.json:
        summary = {"conditions": results, "n_seeds": args.n_seeds, "method": "mock_causal_patch"}
        print(json.dumps(summary, indent=2))
    else:
        print_summary_table(results)
        if args.verbose:
            for r in results:
                print_per_layer(r)

    if args.plot:
        plot_comparison(results, output_path=args.out_plot)

    # Always save JSON summary
    summary = {
        "conditions": results,
        "n_seeds": args.n_seeds,
        "method": "mock_causal_patch",
        "note": "Mock data only. Replace with real Whisper activations after Leo approves Tier 1.",
    }
    with open(args.out_json, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"[gc_runner] Summary saved: {args.out_json}", file=sys.stderr)


if __name__ == "__main__":
    main()
