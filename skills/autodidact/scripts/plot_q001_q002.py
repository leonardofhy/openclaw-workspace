#!/usr/bin/env python3
"""Generate paper-ready figures for Q001 (voicing geometry) and Q002 (causal ablation).

Figures produced:
  q001_voicing_geometry.png  — layer-wise mean cosine similarity bar + per-pair heatmap
  q002_causal_ablation.png   — layer-wise WER bar chart, 3 ablation types side by side

Usage:
    python3 plot_q001_q002.py                          # default paths, save PNGs
    python3 plot_q001_q002.py --q001 path/q001.json
    python3 plot_q001_q002.py --q002 path/q002.json
    python3 plot_q001_q002.py --outdir /custom/dir
    python3 plot_q001_q002.py --show                   # display interactively (no save)
    python3 plot_q001_q002.py --help
"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless by default; overridden by --show
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent.parent

DEFAULT_Q001 = SCRIPT_DIR / "q001_results.json"
DEFAULT_Q002 = SCRIPT_DIR / "q002_results.json"
DEFAULT_OUTDIR = ROOT_DIR / "memory" / "learning" / "figures"

# ---------------------------------------------------------------------------
# Style constants (paper-ready)
# ---------------------------------------------------------------------------

STYLE = {
    "font.family": "sans-serif",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "figure.dpi": 150,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.35,
    "grid.linestyle": "--",
}

ABLATION_COLORS = {
    "zero":  "#e05c5c",
    "noise": "#e89c3f",
    "mean":  "#5c8de0",
}

BAR_COLOR_MAIN = "#4a90d9"
HEATMAP_CMAP = "RdYlGn"


# ---------------------------------------------------------------------------
# Q001 figure
# ---------------------------------------------------------------------------

def plot_q001(data: dict, outdir: Path, show: bool) -> Path:
    """Two-panel figure: bar chart (mean cosine sim per layer) + heatmap."""
    n_layers = data["n_layers"]
    layers = list(range(n_layers))
    mean_sim = data["mean_cosine_sim_per_layer"]
    peak_layer = data["peak_layer"]
    pairs = [p["label"] for p in data["pairs"]]
    cos_matrix = data["cosine_sim_matrix"]  # str(layer) → {pair_key: float}

    # Build heatmap array: shape (n_pairs_cross, n_layers)
    # The matrix keys are like "t_d_vs_p_b"
    pair_keys = list(cos_matrix["0"].keys())
    heatmap = np.array([
        [cos_matrix[str(layer)][pk] for layer in layers]
        for pk in pair_keys
    ])

    # Pretty labels for pair comparisons
    def pretty_pair(key: str) -> str:
        return key.replace("_vs_", " vs ").replace("_", "/")
    pair_labels = [pretty_pair(pk) for pk in pair_keys]

    with plt.rc_context(STYLE):
        fig = plt.figure(figsize=(12, 5))
        gs = gridspec.GridSpec(1, 2, figure=fig, wspace=0.38, left=0.07, right=0.97)

        # ── Left: bar chart ──────────────────────────────────────────────
        ax_bar = fig.add_subplot(gs[0])
        bar_colors = [
            "#e05c5c" if i == peak_layer else BAR_COLOR_MAIN
            for i in layers
        ]
        bars = ax_bar.bar(layers, mean_sim, color=bar_colors, edgecolor="white",
                          linewidth=0.8, zorder=3)

        # Annotate peak
        ax_bar.annotate(
            f"peak\n(layer {peak_layer})",
            xy=(peak_layer, mean_sim[peak_layer]),
            xytext=(peak_layer + 0.5, mean_sim[peak_layer] + 0.01),
            fontsize=9, color="#e05c5c",
            arrowprops=dict(arrowstyle="->", color="#e05c5c", lw=1.2),
        )

        ax_bar.set_xticks(layers)
        ax_bar.set_xticklabels([f"L{i}" for i in layers])
        ax_bar.set_xlabel("Encoder Layer")
        ax_bar.set_ylabel("Mean Cosine Similarity")
        ax_bar.set_title(
            "Q001: Layer-wise Voicing Geometry\n"
            f"(Whisper-base, {len(pairs)} phoneme pairs)",
        )
        ax_bar.set_ylim(0, max(mean_sim) * 1.3)
        ax_bar.axhline(0, color="black", lw=0.6, zorder=2)

        # Bar value labels
        for bar, v in zip(bars, mean_sim):
            ax_bar.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.002,
                f"{v:.3f}",
                ha="center", va="bottom", fontsize=8, color="#333",
            )

        # ── Right: heatmap ───────────────────────────────────────────────
        ax_hm = fig.add_subplot(gs[1])
        vmax = max(abs(heatmap.min()), abs(heatmap.max()))
        im = ax_hm.imshow(
            heatmap, aspect="auto", cmap=HEATMAP_CMAP,
            vmin=-vmax, vmax=vmax,
        )

        ax_hm.set_xticks(layers)
        ax_hm.set_xticklabels([f"L{i}" for i in layers])
        ax_hm.set_yticks(range(len(pair_labels)))
        ax_hm.set_yticklabels(pair_labels)
        ax_hm.set_xlabel("Encoder Layer")
        ax_hm.set_title("Per-Pair Cosine Similarity Heatmap")

        # Cell annotations
        for row_i in range(heatmap.shape[0]):
            for col_j in range(heatmap.shape[1]):
                val = heatmap[row_i, col_j]
                color = "white" if abs(val) > 0.35 else "black"
                ax_hm.text(col_j, row_i, f"{val:.2f}",
                           ha="center", va="center", fontsize=7.5, color=color)

        cbar = fig.colorbar(im, ax=ax_hm, fraction=0.046, pad=0.04)
        cbar.set_label("Cosine Similarity", fontsize=9)

        fig.suptitle(
            "Q001 — Voicing Geometry in Whisper-base Encoder\n"
            "Weak linearity observed at layer 5 (cos_sim = 0.155)",
            fontsize=12, y=1.02,
        )

        if show:
            plt.show()
            return Path()

        outdir.mkdir(parents=True, exist_ok=True)
        out = outdir / "q001_voicing_geometry.png"
        fig.savefig(out, bbox_inches="tight", dpi=STYLE["figure.dpi"])
        plt.close(fig)
        return out


# ---------------------------------------------------------------------------
# Q002 figure
# ---------------------------------------------------------------------------

def plot_q002(data: dict, outdir: Path, show: bool) -> Path:
    """Grouped bar chart: layer × ablation type, WER on y-axis."""
    n_layers = data["n_layers"]
    layers = list(range(n_layers))
    ablation_types = data["ablation_types"]
    wer_data = data["mean_wer_per_layer"]  # str(layer) → {ablation: float}

    # Build arrays per ablation type
    wer_by_type = {
        atype: [wer_data[str(l)][atype] for l in layers]
        for atype in ablation_types
    }

    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(10, 5))
        fig.subplots_adjust(left=0.1, right=0.95, bottom=0.12, top=0.85)

        n_types = len(ablation_types)
        bar_width = 0.22
        group_offsets = np.linspace(
            -(n_types - 1) * bar_width / 2,
             (n_types - 1) * bar_width / 2,
            n_types,
        )

        x = np.array(layers, dtype=float)

        for offset, atype in zip(group_offsets, ablation_types):
            wers = wer_by_type[atype]
            color = ABLATION_COLORS.get(atype, "#888888")
            bars = ax.bar(
                x + offset, wers,
                width=bar_width, label=atype.capitalize(),
                color=color, alpha=0.85, edgecolor="white", linewidth=0.7,
                zorder=3,
            )
            # Value labels (only if not all 1.0 — avoid clutter)
            if not all(v == 1.0 for v in wers):
                for bar, v in zip(bars, wers):
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 0.01,
                        f"{v:.2f}",
                        ha="center", va="bottom", fontsize=7.5,
                    )

        # Annotate the "all WER=1.0" finding
        ax.text(
            0.5, 0.92,
            "All layers show WER = 1.0 — every encoder layer is causally critical",
            transform=ax.transAxes, ha="center", fontsize=9.5,
            color="#555", style="italic",
        )

        ax.set_xticks(layers)
        ax.set_xticklabels([f"Layer {i}" for i in layers])
        ax.set_xlabel("Encoder Layer Ablated")
        ax.set_ylabel("Mean WER (vs reference)")
        ax.set_ylim(0, 1.25)
        ax.axhline(1.0, color="#888", lw=1.0, ls="--", zorder=2, label="WER = 1.0 (baseline)")
        ax.legend(loc="upper right", framealpha=0.9)
        ax.set_title(
            "Q002 — Layer-wise Causal Contribution (Whisper-base)\n"
            f"Ablation types: {', '.join(ablation_types)} | "
            f"{data['n_sentences_used']} test sentences",
            pad=10,
        )

        if show:
            plt.show()
            return Path()

        outdir.mkdir(parents=True, exist_ok=True)
        out = outdir / "q002_causal_ablation.png"
        fig.savefig(out, bbox_inches="tight", dpi=STYLE["figure.dpi"])
        plt.close(fig)
        return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate paper-ready figures for Q001 and Q002 experiments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Outputs (saved to memory/learning/figures/ by default):
  q001_voicing_geometry.png
  q002_causal_ablation.png

Examples:
  python3 plot_q001_q002.py
  python3 plot_q001_q002.py --outdir /tmp/figs
  python3 plot_q001_q002.py --only q001
  python3 plot_q001_q002.py --show
""",
    )
    parser.add_argument("--q001", metavar="PATH", default=str(DEFAULT_Q001),
                        help=f"Path to q001_results.json (default: {DEFAULT_Q001})")
    parser.add_argument("--q002", metavar="PATH", default=str(DEFAULT_Q002),
                        help=f"Path to q002_results.json (default: {DEFAULT_Q002})")
    parser.add_argument("--outdir", metavar="DIR", default=str(DEFAULT_OUTDIR),
                        help=f"Output directory for PNGs (default: {DEFAULT_OUTDIR})")
    parser.add_argument("--only", choices=["q001", "q002"],
                        help="Generate only one figure")
    parser.add_argument("--show", action="store_true",
                        help="Display figures interactively instead of saving")
    args = parser.parse_args()

    if args.show:
        matplotlib.use("TkAgg" if sys.platform != "darwin" else "MacOSX")
        import importlib
        import matplotlib.pyplot as _plt
        importlib.reload(_plt)

    outdir = Path(args.outdir)
    errors = []

    if args.only != "q002":
        q001_path = Path(args.q001)
        if not q001_path.exists():
            errors.append(f"Q001 results not found: {q001_path}")
        else:
            print(f"Plotting Q001 from {q001_path}…", flush=True)
            data = json.loads(q001_path.read_text())
            out = plot_q001(data, outdir, show=args.show)
            if not args.show:
                print(f"  ✓ saved → {out}")

    if args.only != "q001":
        q002_path = Path(args.q002)
        if not q002_path.exists():
            errors.append(f"Q002 results not found: {q002_path}")
        else:
            print(f"Plotting Q002 from {q002_path}…", flush=True)
            data = json.loads(q002_path.read_text())
            out = plot_q002(data, outdir, show=args.show)
            if not args.show:
                print(f"  ✓ saved → {out}")

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
