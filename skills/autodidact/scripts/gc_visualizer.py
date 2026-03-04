#!/usr/bin/env python3
"""
gc(k) Visualizer — Paper A Figure Generator (Tier 0)
Track T3: Listen vs Guess

Generates 3 paper-ready figures from gc(k) experiment data:
  Fig 1: gc(k) Confidence Curves — listen/mid/guess conditions across all layers
  Fig 2: Listen vs Guess Separation — scatter of mean_enc vs mean_dec with 2D decision boundary
  Fig 3: Patching Effect Heatmap — layer × condition patching Δgc(k) matrix

Works with:
  - Synthetic data from gc_experiment_runner.py (--mock, default)
  - Real JSON output from gc_experiment_runner.py (--input gc_summary.json)

Usage:
    python3 gc_visualizer.py                                  # mock, show all figures
    python3 gc_visualizer.py --input gc_summary.json          # from runner output
    python3 gc_visualizer.py --save --outdir figures/         # save PNG files
    python3 gc_visualizer.py --save --format pdf              # PDF for paper
    python3 gc_visualizer.py --fig 1                          # single figure
"""

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")  # headless by default
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("[gc_visualizer] WARNING: matplotlib not available — ASCII preview mode", flush=True)


# ---------------------------------------------------------------------------
# Mock data generator (Tier 0 — no real model needed)
# ---------------------------------------------------------------------------

def _gc_curve_listen(n_enc=6, n_dec=6, seed=42):
    """High gc — audio signal dominates throughout."""
    rng = np.random.default_rng(seed)
    # Encoder: ramp up from ~0.4 to ~0.85
    enc = np.linspace(0.38, 0.82, n_enc) + rng.normal(0, 0.03, n_enc)
    enc = np.clip(enc, 0.0, 1.0)
    # Decoder: stays elevated (0.65–0.80), slight drift down
    dec = np.linspace(0.78, 0.62, n_dec) + rng.normal(0, 0.03, n_dec)
    dec = np.clip(dec, 0.0, 1.0)
    return enc, dec


def _gc_curve_mid(n_enc=6, n_dec=6, seed=42):
    """Mid gc — partial audio; drops in decoder."""
    rng = np.random.default_rng(seed)
    enc = np.linspace(0.32, 0.60, n_enc) + rng.normal(0, 0.04, n_enc)
    enc = np.clip(enc, 0.0, 1.0)
    dec = np.linspace(0.55, 0.28, n_dec) + rng.normal(0, 0.04, n_dec)
    dec = np.clip(dec, 0.0, 1.0)
    return enc, dec


def _gc_curve_guess(n_enc=6, n_dec=6, seed=42):
    """Low gc — audio absent; decoder guesses from prior."""
    rng = np.random.default_rng(seed)
    enc = np.linspace(0.18, 0.22, n_enc) + rng.normal(0, 0.03, n_enc)
    enc = np.clip(enc, 0.0, 1.0)
    dec = np.linspace(0.20, 0.05, n_dec) + rng.normal(0, 0.02, n_dec)
    dec = np.clip(dec, 0.0, 1.0)
    return enc, dec


def generate_mock_data(n_enc=6, n_dec=6, n_seeds=5):
    """Generate synthetic gc(k) data for all 3 conditions."""
    conditions = {
        "listen": {"label": "Listen (clean audio)", "color": "#2196F3", "fn": _gc_curve_listen},
        "mid":    {"label": "Mid (50% masked)",      "color": "#FF9800", "fn": _gc_curve_mid},
        "guess":  {"label": "Guess (silence/noise)", "color": "#F44336", "fn": _gc_curve_guess},
    }
    data = {}
    for cond_id, cond in conditions.items():
        enc_all, dec_all = [], []
        for s in range(n_seeds):
            enc, dec = cond["fn"](n_enc, n_dec, seed=s)
            enc_all.append(enc)
            dec_all.append(dec)
        enc_arr = np.array(enc_all)
        dec_arr = np.array(dec_all)
        data[cond_id] = {
            "label": cond["label"],
            "color": cond["color"],
            "enc_mean": enc_arr.mean(0).tolist(),
            "enc_std":  enc_arr.std(0).tolist(),
            "dec_mean": dec_arr.mean(0).tolist(),
            "dec_std":  dec_arr.std(0).tolist(),
            "mean_enc": float(enc_arr.mean()),
            "mean_dec": float(dec_arr.mean()),
        }
    return data, n_enc, n_dec


def generate_patching_mock(conditions_data, n_enc=6, n_dec=6):
    """
    Simulate patching Δgc(k): patching listen→guess at layer k.
    Returns (n_conditions × n_layers) matrix of Δgc effect.
    """
    rng = np.random.default_rng(0)
    n_layers = n_enc + n_dec
    cond_ids = list(conditions_data.keys())
    matrix = np.zeros((len(cond_ids), n_layers))
    for i, cid in enumerate(cond_ids):
        # Effect peaks at encoder layers 3-5 for listen, flat for guess
        base_effect = np.concatenate([
            np.linspace(0.02, 0.30 - i * 0.12, n_enc),
            np.linspace(0.25 - i * 0.10, 0.08 - i * 0.03, n_dec),
        ])
        noise = rng.normal(0, 0.02, n_layers)
        matrix[i] = np.clip(base_effect + noise, -0.05, 0.45)
    return cond_ids, matrix


# ---------------------------------------------------------------------------
# Figure 1: gc(k) Confidence Curves
# ---------------------------------------------------------------------------

def fig1_gc_curves(data, n_enc, n_dec, ax=None, standalone=False):
    """Layer-by-layer gc(k) curves with ±1σ bands."""
    show = standalone and ax is None
    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 4))

    n_layers = n_enc + n_dec
    xs = list(range(n_layers))
    enc_xs = xs[:n_enc]
    dec_xs = xs[n_enc:]

    for cond_id, cond in data.items():
        enc_mean = np.array(cond["enc_mean"])
        enc_std  = np.array(cond["enc_std"])
        dec_mean = np.array(cond["dec_mean"])
        dec_std  = np.array(cond["dec_std"])
        color    = cond["color"]
        label    = cond["label"]

        all_mean = np.concatenate([enc_mean, dec_mean])
        all_std  = np.concatenate([enc_std, dec_std])

        ax.plot(xs, all_mean, color=color, linewidth=2, label=label)
        ax.fill_between(xs, all_mean - all_std, all_mean + all_std,
                        color=color, alpha=0.15)

    # Encoder / decoder boundary
    ax.axvline(x=n_enc - 0.5, color="gray", linestyle="--", linewidth=1.2,
               alpha=0.7, label="enc|dec boundary")

    ax.set_xlim(-0.3, n_layers - 0.7)
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("Layer k", fontsize=11)
    ax.set_ylabel("gc(k)", fontsize=11)
    ax.set_title("Fig 1: gc(k) Confidence Curves by Condition", fontsize=12, fontweight="bold")

    # X-axis tick labels: E0…E5, D0…D5
    enc_labels = [f"E{i}" for i in range(n_enc)]
    dec_labels = [f"D{i}" for i in range(n_dec)]
    ax.set_xticks(xs)
    ax.set_xticklabels(enc_labels + dec_labels, fontsize=9)

    ax.legend(fontsize=9, loc="lower left")
    ax.grid(True, alpha=0.3)

    if standalone and show:
        plt.tight_layout()
        plt.show()
    return ax


# ---------------------------------------------------------------------------
# Figure 2: Listen vs Guess Separation Scatter
# ---------------------------------------------------------------------------

def fig2_separation_scatter(data, ax=None, standalone=False):
    """Scatter of (mean_enc, mean_dec) per condition with decision boundary."""
    show = standalone and ax is None
    if ax is None:
        fig, ax = plt.subplots(figsize=(5, 5))

    for cond_id, cond in data.items():
        ax.scatter(
            cond["mean_enc"], cond["mean_dec"],
            color=cond["color"], s=200, zorder=5,
            label=cond["label"], edgecolors="white", linewidths=1.5
        )
        # Annotate with condition name
        ax.annotate(
            cond_id.capitalize(),
            (cond["mean_enc"], cond["mean_dec"]),
            textcoords="offset points", xytext=(8, 4),
            fontsize=9, color=cond["color"]
        )

    # Diagonal: mean_enc == mean_dec reference line
    lim_min, lim_max = 0.0, 1.0
    ax.plot([lim_min, lim_max], [lim_min, lim_max],
            "k--", alpha=0.4, linewidth=1, label="enc=dec (diagonal)")

    # Decision boundary sketch (horizontal at 0.5)
    ax.axhline(y=0.5, color="purple", linestyle=":", linewidth=1.2, alpha=0.5,
               label="dec=0.5 threshold")
    ax.axvline(x=0.5, color="teal", linestyle=":", linewidth=1.2, alpha=0.5,
               label="enc=0.5 threshold")

    ax.set_xlim(lim_min, lim_max)
    ax.set_ylim(lim_min, lim_max)
    ax.set_xlabel("Mean gc(k) — Encoder Layers", fontsize=11)
    ax.set_ylabel("Mean gc(k) — Decoder Layers", fontsize=11)
    ax.set_title("Fig 2: Listen vs Guess Separation", fontsize=12, fontweight="bold")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal")

    if standalone and show:
        plt.tight_layout()
        plt.show()
    return ax


# ---------------------------------------------------------------------------
# Figure 3: Patching Effect Heatmap
# ---------------------------------------------------------------------------

def fig3_patching_heatmap(conditions_data, n_enc=6, n_dec=6, ax=None, standalone=False):
    """Heatmap of causal patching Δgc(k) — conditions × layers."""
    show = standalone and ax is None
    if ax is None:
        fig, ax = plt.subplots(figsize=(9, 3))

    cond_ids, matrix = generate_patching_mock(conditions_data, n_enc, n_dec)
    cond_labels = [conditions_data[c]["label"] for c in cond_ids]

    im = ax.imshow(matrix, aspect="auto", cmap="RdYlGn", vmin=-0.1, vmax=0.45)

    # Axes
    n_layers = n_enc + n_dec
    enc_labels = [f"E{i}" for i in range(n_enc)]
    dec_labels = [f"D{i}" for i in range(n_dec)]
    ax.set_xticks(range(n_layers))
    ax.set_xticklabels(enc_labels + dec_labels, fontsize=9)
    ax.set_yticks(range(len(cond_labels)))
    ax.set_yticklabels(cond_labels, fontsize=9)

    # Encoder/decoder boundary
    ax.axvline(x=n_enc - 0.5, color="white", linewidth=2)

    # Cell annotations
    for i in range(len(cond_labels)):
        for j in range(n_layers):
            val = matrix[i, j]
            txt_color = "black" if 0.1 < val < 0.35 else "white"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                    fontsize=7, color=txt_color)

    plt.colorbar(im, ax=ax, label="Δgc(k) patching effect")
    ax.set_title("Fig 3: Causal Patching Effect Heatmap (Δgc per Layer)", fontsize=12, fontweight="bold")
    ax.set_xlabel("Layer k (patch target)", fontsize=11)

    # Boundary label
    ax.text(n_enc - 0.5, -0.7, "enc|dec", ha="center", va="top",
            fontsize=8, color="gray", style="italic")

    if standalone and show:
        plt.tight_layout()
        plt.show()
    return ax


# ---------------------------------------------------------------------------
# Combined figure (all 3)
# ---------------------------------------------------------------------------

def make_combined_figure(data, n_enc, n_dec, save_path=None, fmt="png", dpi=150):
    """Compose all 3 figures into a single publication layout."""
    fig = plt.figure(figsize=(16, 5))
    gs = gridspec.GridSpec(1, 3, figure=fig, wspace=0.38)

    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    ax3 = fig.add_subplot(gs[2])

    fig1_gc_curves(data, n_enc, n_dec, ax=ax1)
    fig2_separation_scatter(data, ax=ax2)
    fig3_patching_heatmap(data, n_enc, n_dec, ax=ax3)

    fig.suptitle("Paper A — gc(k) Listen vs Guess Experimental Results (Synthetic)",
                 fontsize=13, fontweight="bold", y=1.01)
    plt.tight_layout()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, format=fmt, dpi=dpi, bbox_inches="tight")
        print(f"[gc_visualizer] Saved: {save_path}")
    return fig


# ---------------------------------------------------------------------------
# ASCII fallback preview
# ---------------------------------------------------------------------------

def ascii_preview(data, n_enc, n_dec):
    """Text preview when matplotlib unavailable."""
    print("\n=== gc(k) Visualizer — ASCII Preview ===\n")
    for cid, cond in data.items():
        enc_m = np.array(cond["enc_mean"])
        dec_m = np.array(cond["dec_mean"])
        print(f"[{cond['label']}]")
        enc_str = " ".join(f"{v:.2f}" for v in enc_m)
        dec_str = " ".join(f"{v:.2f}" for v in dec_m)
        print(f"  Encoder:  {enc_str}")
        print(f"  Decoder:  {dec_str}")
        print(f"  mean_enc={cond['mean_enc']:.3f}  mean_dec={cond['mean_dec']:.3f}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="gc(k) Visualizer — Paper A figures")
    parser.add_argument("--input", help="JSON file from gc_experiment_runner (optional)")
    parser.add_argument("--save", action="store_true", help="Save figures to files")
    parser.add_argument("--outdir", default="figures", help="Output directory (default: figures/)")
    parser.add_argument("--format", choices=["png", "pdf", "svg"], default="png")
    parser.add_argument("--fig", type=int, choices=[1, 2, 3], help="Show single figure only")
    parser.add_argument("--n-enc", type=int, default=6)
    parser.add_argument("--n-dec", type=int, default=6)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--dpi", type=int, default=150)
    args = parser.parse_args()

    # Load data
    if args.input and Path(args.input).exists():
        with open(args.input) as f:
            raw = json.load(f)
        # Normalize from gc_experiment_runner summary format
        data = {}
        colors = {"listen": "#2196F3", "mid": "#FF9800", "guess": "#F44336"}
        for cond_id, cond_data in raw.items():
            if isinstance(cond_data, dict) and "enc_mean" in cond_data:
                data[cond_id] = cond_data
                data[cond_id].setdefault("color", colors.get(cond_id, "#999999"))
        n_enc, n_dec = args.n_enc, args.n_dec
        print(f"[gc_visualizer] Loaded from {args.input}: {list(data.keys())}")
    else:
        data, n_enc, n_dec = generate_mock_data(args.n_enc, args.n_dec, args.seeds)
        print("[gc_visualizer] Using synthetic mock data (Tier 0)")

    if not HAS_MPL:
        ascii_preview(data, n_enc, n_dec)
        return 0

    outdir = Path(args.outdir)

    if args.fig:
        # Single figure
        fig_fns = {
            1: lambda: fig1_gc_curves(data, n_enc, n_dec, standalone=True),
            2: lambda: fig2_separation_scatter(data, standalone=True),
            3: lambda: fig3_patching_heatmap(data, n_enc, n_dec, standalone=True),
        }
        ax = fig_fns[args.fig]()
        if args.save:
            save_path = outdir / f"fig{args.fig}.{args.format}"
            plt.gcf().savefig(save_path, dpi=args.dpi, bbox_inches="tight")
            print(f"[gc_visualizer] Saved: {save_path}")
        else:
            plt.show()
    else:
        # Combined
        save_path = (outdir / f"paper_a_gc_combined.{args.format}") if args.save else None
        fig = make_combined_figure(data, n_enc, n_dec,
                                   save_path=save_path, fmt=args.format, dpi=args.dpi)
        if not args.save:
            plt.show()

    print("[gc_visualizer] Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
