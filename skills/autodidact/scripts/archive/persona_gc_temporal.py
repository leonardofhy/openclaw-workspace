#!/usr/bin/env python3
"""
Persona × Temporal gc(k,t) — Q073
Track T3: Listen vs Guess (Paper A §5 Extension)

Extends persona_gc_benchmark.py (Q039) to a 2D analysis:
  - Axis 1: encoder layer k (spatial, where audio info is resolved)
  - Axis 2: decoder CoT step t (temporal, when audio info is used)

Produces:
  1. 2D gc(k,t) × persona heatmap (3 personas × N_ENCODER_LAYERS × N_DECODER_STEPS)
  2. delta_persona_decay: how quickly each persona's gc signal decays across CoT steps
     delta_persona_decay[cond] = gc(k*,t=1) - gc(k*,t=T)  (peak layer, first vs last step)
  3. Cross-condition asymmetry: does the persona effect strengthen or weaken across CoT steps?

Hypotheses (extending H1-H4 from Q039):
  H5: assistant persona → faster gc decay across CoT steps (defers to text earlier)
  H6: anti_ground persona → slower gc decay (trusts audio longer through CoT)
  H7: peak layer k* shifts earlier as CoT step t increases (audio influence migrates to lower layers)
  H8: delta_persona_decay(assistant) < delta_persona_decay(neutral) < delta_persona_decay(anti_ground)
      (ordering predicts persona-induced decay ordering)

CPU-feasible: runs on mock tensors, no model download needed.

Usage:
    python3 persona_gc_temporal.py                 # mock mode, text heatmap
    python3 persona_gc_temporal.py --json          # JSON output
    python3 persona_gc_temporal.py --plot          # 2D heatmap (requires matplotlib)
    python3 persona_gc_temporal.py --layers 6 --steps 5 --stimuli 20
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict, field
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PERSONA_CONDITIONS = ["neutral", "assistant", "anti_ground"]
PERSONA_PROMPTS = {
    "neutral": None,
    "assistant": "You are a helpful assistant. Always follow the user's text instructions.",
    "anti_ground": "Trust what you hear over what you read. The audio is always the ground truth.",
}

N_ENCODER_LAYERS = 6    # Whisper-tiny scale; use 32 for large
N_DECODER_STEPS = 5     # CoT decoding steps (t=0..T-1)
N_STIMULI = 20          # stimuli per condition


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Temporal2DResult:
    """2D gc(k,t) for one persona condition."""
    condition: str
    prompt: Optional[str]
    # shape: (N_ENCODER_LAYERS, N_DECODER_STEPS) — mean over stimuli
    gc_mean_2d: np.ndarray
    # shape: (N_ENCODER_LAYERS, N_DECODER_STEPS) — std over stimuli
    gc_std_2d: np.ndarray
    n_stimuli: int

    # Derived 1D summaries
    gc_mean_over_t: np.ndarray   # shape: (N_ENCODER_LAYERS,) — averaged over t
    gc_mean_over_k: np.ndarray   # shape: (N_DECODER_STEPS,) — averaged over k

    # Peak layer at each step t
    peak_layer_per_t: np.ndarray  # shape: (N_DECODER_STEPS,)

    # Scalar metrics
    delta_persona_decay: float   # gc(k*, t=0) - gc(k*, t=T-1) at peak layer k*
    peak_layer_t0: int           # peak layer at t=0 (first CoT step)
    peak_layer_tT: int           # peak layer at t=T-1 (last CoT step)
    mean_gc_all: float           # grand mean across all k,t


@dataclass
class HypothesisResults:
    condition: str
    h5_fast_decay: bool           # assistant: decay > neutral + 0.05
    h6_slow_decay: bool           # anti_ground: decay < neutral - 0.05
    h7_peak_shift_early: bool     # peak_layer_tT < peak_layer_t0 (shifts to earlier layers)
    h7_delta_layer: int           # peak_layer_t0 - peak_layer_tT
    h8_decay_ordering: Optional[str]  # "correct" / "incorrect" / "baseline"
    delta_persona_decay: float
    peak_layer_t0: int
    peak_layer_tT: int


# ---------------------------------------------------------------------------
# Mock generator: 2D gc(k,t) per persona
# ---------------------------------------------------------------------------

def mock_gc_2d_for_condition(
    condition: str,
    n_layers: int = N_ENCODER_LAYERS,
    n_steps: int = N_DECODER_STEPS,
    n_stimuli: int = N_STIMULI,
    seed_base: int = 42,
) -> Temporal2DResult:
    """
    Generate synthetic 2D gc(k,t) for a persona condition.

    Ground-truth generation logic:
      Each stimulus: gc(k,t) = spatial_profile(k, condition) × temporal_decay(t, condition)

      spatial_profile (k):
        neutral:    bell curve at k = n_layers/2, height 0.55
        assistant:  depressed bell curve, height 0.38, same center
        anti_ground: earlier peak (n_layers/4), higher height 0.70

      temporal_decay (t):
        neutral:    slow decay — gc * exp(-0.15 * t)
        assistant:  fast decay — gc * exp(-0.35 * t)   [H5]
        anti_ground: slow decay — gc * exp(-0.05 * t)  [H6]

      Peak layer migration (H7):
        The gc(k,t) peak shifts toward earlier layers at higher t
        (audio integration migrates from mid-encoder to lower layers as CoT deepens)
        Implemented by shifting the bell center: center(t) = center(t=0) - t * 0.3

    Real implementation: for each decoder step t, run gc(k) patching conditioned
    on the partial CoT prefix up to step t. Replace mock functions below.
    """
    rng = np.random.default_rng(seed_base + abs(hash(condition)) % 10000)

    # Condition-specific parameters
    if condition == "neutral":
        height = 0.55
        sigma = n_layers / 4.0
        center_t0 = n_layers / 2.0
        decay_rate = 0.15
    elif condition == "assistant":
        height = 0.38
        sigma = n_layers / 4.0
        center_t0 = n_layers / 2.0
        decay_rate = 0.35   # faster decay [H5]
    elif condition == "anti_ground":
        height = 0.70
        sigma = n_layers / 5.0
        center_t0 = max(1.0, n_layers / 4.0)
        decay_rate = 0.05   # slower decay [H6]
    else:
        raise ValueError(f"Unknown condition: {condition!r}")

    # Generate per-stimulus 2D arrays
    all_stimuli = []
    layers = np.arange(n_layers, dtype=float)
    steps = np.arange(n_steps, dtype=float)

    for i in range(n_stimuli):
        stim_rng = np.random.default_rng(seed_base + i * 13 + abs(hash(condition)) % 9999)

        gc_2d = np.zeros((n_layers, n_steps), dtype=float)
        for t in range(n_steps):
            # Peak migrates earlier as t increases (H7)
            center_t = max(0.0, center_t0 - t * 0.3)
            spatial = height * np.exp(-0.5 * ((layers - center_t) / sigma) ** 2)

            # Temporal decay factor
            temporal = np.exp(-decay_rate * t)

            # Combined: gc(k,t) = spatial(k) × decay(t)
            gc_slice = spatial * temporal

            # Add per-stimulus noise
            noise = stim_rng.normal(0, 0.03, n_layers)
            gc_2d[:, t] = np.clip(gc_slice + noise, 0.0, 1.0)

        all_stimuli.append(gc_2d)

    stacked = np.stack(all_stimuli, axis=0)   # (n_stimuli, n_layers, n_steps)
    gc_mean_2d = stacked.mean(axis=0)          # (n_layers, n_steps)
    gc_std_2d = stacked.std(axis=0)

    # Derived
    gc_mean_over_t = gc_mean_2d.mean(axis=1)     # (n_layers,)
    gc_mean_over_k = gc_mean_2d.mean(axis=0)     # (n_steps,)
    peak_layer_per_t = gc_mean_2d.argmax(axis=0) # (n_steps,)
    peak_layer_t0 = int(peak_layer_per_t[0])
    peak_layer_tT = int(peak_layer_per_t[-1])

    # delta_persona_decay: gc at peak layer (averaged over k), first step vs last step
    k_star = int(gc_mean_over_t.argmax())        # peak layer in time-averaged sense
    delta_decay = float(gc_mean_2d[k_star, 0] - gc_mean_2d[k_star, -1])

    mean_gc_all = float(gc_mean_2d.mean())

    return Temporal2DResult(
        condition=condition,
        prompt=PERSONA_PROMPTS[condition],
        gc_mean_2d=gc_mean_2d,
        gc_std_2d=gc_std_2d,
        n_stimuli=n_stimuli,
        gc_mean_over_t=gc_mean_over_t,
        gc_mean_over_k=gc_mean_over_k,
        peak_layer_per_t=peak_layer_per_t,
        delta_persona_decay=delta_decay,
        peak_layer_t0=peak_layer_t0,
        peak_layer_tT=peak_layer_tT,
        mean_gc_all=mean_gc_all,
    )


# ---------------------------------------------------------------------------
# Hypothesis tests
# ---------------------------------------------------------------------------

def run_hypothesis_tests(
    results: dict[str, Temporal2DResult],
) -> dict[str, HypothesisResults]:
    """Test H5–H8 across conditions."""
    neutral = results["neutral"]
    all_decays = {c: r.delta_persona_decay for c, r in results.items()}
    out = {}

    for cond, res in results.items():
        h5 = (cond == "assistant") and (res.delta_persona_decay > neutral.delta_persona_decay + 0.05)
        h6 = (cond == "anti_ground") and (res.delta_persona_decay < neutral.delta_persona_decay - 0.05)
        h7_flag = res.peak_layer_tT < res.peak_layer_t0
        h7_delta = res.peak_layer_t0 - res.peak_layer_tT

        # H8: ordering = assistant < neutral < anti_ground
        if cond == "neutral":
            h8_str = "baseline"
        else:
            asst = all_decays.get("assistant", 0.0)
            anti = all_decays.get("anti_ground", 0.0)
            neut = all_decays.get("neutral", 0.0)
            h8_str = "correct" if (asst > neut > anti) else "incorrect"
            # Note: anti_ground has SLOWER decay = smaller delta_decay value
            # So ordering of delta_decay: anti_ground < neutral < assistant = H8 correct

        out[cond] = HypothesisResults(
            condition=cond,
            h5_fast_decay=bool(h5),
            h6_slow_decay=bool(h6),
            h7_peak_shift_early=bool(h7_flag),
            h7_delta_layer=int(h7_delta),
            h8_decay_ordering=h8_str,
            delta_persona_decay=round(res.delta_persona_decay, 4),
            peak_layer_t0=res.peak_layer_t0,
            peak_layer_tT=res.peak_layer_tT,
        )

    return out


# ---------------------------------------------------------------------------
# Output: text heatmap
# ---------------------------------------------------------------------------

def print_heatmap_ascii(results: dict[str, Temporal2DResult]) -> None:
    """Print ASCII 2D heatmap with block chars."""
    BLOCKS = " ░▒▓█"

    def to_block(v: float) -> str:
        idx = min(int(v / 0.2), len(BLOCKS) - 1)
        return BLOCKS[idx]

    for cond in PERSONA_CONDITIONS:
        r = results[cond]
        n_layers, n_steps = r.gc_mean_2d.shape
        print(f"\n  [{cond}]  δ_decay={r.delta_persona_decay:+.4f}  "
              f"k*(t=0)={r.peak_layer_t0}  k*(t={n_steps-1})={r.peak_layer_tT}")
        header = "  k\\t  " + "  ".join(f"t={t}" for t in range(n_steps))
        print(f"  {header}")
        for k in range(n_layers):
            row_str = f"  k={k}  "
            for t in range(n_steps):
                v = r.gc_mean_2d[k, t]
                row_str += f" {to_block(v)} {v:.2f}"
            print(row_str)


def print_full_report(
    results: dict[str, Temporal2DResult],
    hyp: dict[str, HypothesisResults],
) -> None:
    n_layers = results["neutral"].gc_mean_2d.shape[0]
    n_steps = results["neutral"].gc_mean_2d.shape[1]

    print("\n" + "=" * 72)
    print("  Persona × Temporal gc(k,t) Benchmark — Q073")
    print("=" * 72)
    print(f"  Encoder layers: {n_layers}  |  Decoder steps: {n_steps}  |  Stimuli: {results['neutral'].n_stimuli}")
    print("  NOTE: Mock mode — replace mock_gc_2d_for_condition() with real patching\n")

    # 2D heatmaps
    print("  ── 2D gc(k,t) Heatmaps (mean over stimuli) ─────────────────────────")
    print("  Legend: ' '=0–0.19  '░'=0.2–0.39  '▒'=0.4–0.59  '▓'=0.6–0.79  '█'=0.8–1.0")
    print("  Each cell: [block] value")
    print("  Columns = decoder CoT step t | Rows = encoder layer k\n")
    print_heatmap_ascii(results)

    # Summary metrics
    print("\n  ── Summary Metrics ──────────────────────────────────────────────────")
    print(f"  {'Condition':<16} {'Mean gc(all)':>13} {'δ_decay':>9} {'k*(t=0)':>8} {'k*(t=T)':>8} {'ΔLayer':>8}")
    print(f"  {'─' * 67}")
    for cond in PERSONA_CONDITIONS:
        r = results[cond]
        h = hyp[cond]
        print(f"  {cond:<16} {r.mean_gc_all:>13.4f} {r.delta_persona_decay:>+9.4f} "
              f"{r.peak_layer_t0:>8} {r.peak_layer_tT:>8} {h.h7_delta_layer:>+8}")

    # Hypothesis results
    print("\n  ── Hypothesis Test Results ──────────────────────────────────────────")
    for cond in PERSONA_CONDITIONS:
        h = hyp[cond]
        if cond == "neutral":
            print(f"\n  [neutral]: baseline (δ_decay={h.delta_persona_decay:+.4f})")
            continue
        print(f"\n  [{cond}]")
        h5_icon = "✅" if (cond == "assistant" and h.h5_fast_decay) else ("N/A" if cond == "anti_ground" else "❌")
        h6_icon = "✅" if (cond == "anti_ground" and h.h6_slow_decay) else ("N/A" if cond == "assistant" else "❌")
        h7_icon = "✅" if h.h7_peak_shift_early else "❌"
        h8_icon = "✅" if h.h8_decay_ordering == "correct" else ("baseline" if h.h8_decay_ordering == "baseline" else "❌")
        print(f"    H5 (fast decay, assistant):  {h5_icon}  δ_decay={h.delta_persona_decay:+.4f}")
        print(f"    H6 (slow decay, anti_ground): {h6_icon}  δ_decay={h.delta_persona_decay:+.4f}")
        print(f"    H7 (peak shifts earlier, ≥1): {h7_icon}  Δlayer={h.h7_delta_layer:+d}")
        print(f"    H8 (decay ordering correct):  {h8_icon}")

    # delta_persona_decay explanation
    print("\n  ── delta_persona_decay Definition ───────────────────────────────────")
    print("  δ_decay = gc(k*, t=0) - gc(k*, t=T-1) at time-averaged peak layer k*")
    print("  Positive = audio signal decays (as expected); larger = faster decay")
    print("  Hypothesis H5/H6: assistant decays faster, anti_ground decays slower")
    print("  than neutral → ordering: δ(anti_ground) < δ(neutral) < δ(assistant)")

    # gc_mean_over_k (temporal slice)
    print("\n  ── gc(k) Averaged over CoT Steps (marginal spatial profile) ─────────")
    print(f"  {'k':<5}", end="")
    for cond in PERSONA_CONDITIONS:
        print(f"  {cond:<20}", end="")
    print()
    for k in range(n_layers):
        print(f"  {k:<5}", end="")
        for cond in PERSONA_CONDITIONS:
            v = results[cond].gc_mean_over_t[k]
            print(f"  {v:.4f}               ", end="")
        print()

    # gc_mean_over_k (spatial slices by step)
    print("\n  ── gc(t) Averaged over Encoder Layers (temporal decay) ─────────────")
    print(f"  {'t':<5}", end="")
    for cond in PERSONA_CONDITIONS:
        print(f"  {cond:<20}", end="")
    print()
    for t in range(n_steps):
        print(f"  {t:<5}", end="")
        for cond in PERSONA_CONDITIONS:
            v = results[cond].gc_mean_over_k[t]
            print(f"  {v:.4f}               ", end="")
        print()

    print("=" * 72)


# ---------------------------------------------------------------------------
# JSON serializer
# ---------------------------------------------------------------------------

def to_json_safe(
    results: dict[str, Temporal2DResult],
    hyp: dict[str, HypothesisResults],
) -> dict:
    out = {
        "task": "Q073",
        "description": "Persona x Temporal gc(k,t) 2D benchmark",
        "conditions": {},
        "metrics": {
            "delta_persona_decay": {},
            "peak_layer_migration": {},
        },
        "hypotheses": {},
    }
    for cond in PERSONA_CONDITIONS:
        r = results[cond]
        h = hyp[cond]
        out["conditions"][cond] = {
            "gc_mean_2d": r.gc_mean_2d.tolist(),
            "gc_std_2d": r.gc_std_2d.tolist(),
            "gc_mean_over_t": r.gc_mean_over_t.tolist(),
            "gc_mean_over_k": r.gc_mean_over_k.tolist(),
            "peak_layer_per_t": r.peak_layer_per_t.tolist(),
            "delta_persona_decay": r.delta_persona_decay,
            "peak_layer_t0": r.peak_layer_t0,
            "peak_layer_tT": r.peak_layer_tT,
            "mean_gc_all": r.mean_gc_all,
        }
        out["metrics"]["delta_persona_decay"][cond] = r.delta_persona_decay
        out["metrics"]["peak_layer_migration"][cond] = {
            "t0": r.peak_layer_t0,
            "tT": r.peak_layer_tT,
            "delta": r.peak_layer_t0 - r.peak_layer_tT,
        }
        out["hypotheses"][cond] = asdict(h)
    return out


# ---------------------------------------------------------------------------
# Matplotlib heatmap
# ---------------------------------------------------------------------------

def plot_heatmaps(results: dict[str, Temporal2DResult]) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available — skipping plot")
        return

    n_conds = len(PERSONA_CONDITIONS)
    fig, axes = plt.subplots(1, n_conds, figsize=(5 * n_conds, 4), sharey=True)

    for ax, cond in zip(axes, PERSONA_CONDITIONS):
        r = results[cond]
        im = ax.imshow(
            r.gc_mean_2d,
            aspect="auto",
            origin="lower",
            cmap="viridis",
            vmin=0.0, vmax=1.0,
        )
        ax.set_title(f"{cond}\nδ_decay={r.delta_persona_decay:+.3f}", fontsize=10)
        ax.set_xlabel("Decoder step t")
        n_layers, n_steps = r.gc_mean_2d.shape
        ax.set_xticks(range(n_steps))
        ax.set_yticks(range(n_layers))

    axes[0].set_ylabel("Encoder layer k")
    fig.colorbar(im, ax=axes, label="gc(k,t)")
    fig.suptitle("Persona × Temporal gc(k,t) — Q073 (Mock Mode)", fontsize=12)
    plt.tight_layout()

    out_path = "memory/learning/cycles/persona_gc_temporal_heatmap.png"
    plt.savefig(out_path, dpi=120)
    print(f"\n  Plot saved → {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Persona × Temporal gc(k,t) — Q073")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--plot", action="store_true", help="Generate heatmap (matplotlib)")
    parser.add_argument("--layers", type=int, default=N_ENCODER_LAYERS)
    parser.add_argument("--steps", type=int, default=N_DECODER_STEPS)
    parser.add_argument("--stimuli", type=int, default=N_STIMULI)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    # Generate 2D results
    results: dict[str, Temporal2DResult] = {}
    for cond in PERSONA_CONDITIONS:
        results[cond] = mock_gc_2d_for_condition(
            cond,
            n_layers=args.layers,
            n_steps=args.steps,
            n_stimuli=args.stimuli,
            seed_base=args.seed,
        )

    hyp = run_hypothesis_tests(results)

    if args.json:
        print(json.dumps(to_json_safe(results, hyp), indent=2))
    else:
        print_full_report(results, hyp)

    if args.plot:
        plot_heatmaps(results)

    # Validation
    for cond, r in results.items():
        assert r.gc_mean_2d.shape == (args.layers, args.steps), f"Shape mismatch for {cond}"
        assert np.all(np.isfinite(r.gc_mean_2d)), f"NaN/Inf in {cond}"
        assert np.all((r.gc_mean_2d >= 0) & (r.gc_mean_2d <= 1)), f"Out-of-range in {cond}"

    return 0


if __name__ == "__main__":
    sys.exit(main())
