#!/usr/bin/env python3
"""
AND/OR Gate x gc(k): Denoising Patching Protocol Mock — Q070
Track T3: Listen vs Guess (Paper A §5.5 Extension)

Core idea:
  The AND/OR gate taxonomy classifies SAE features by their causal structure:
    - AND-gate feature: fires only when BOTH audio and context evidence are present
      → Conjunctive integration; conservative; robust to noise (requires both)
    - OR-gate feature: fires when EITHER audio OR context evidence is present
      → Disjunctive integration; flexible; can "guess" from context alone
    - Passthrough feature: signal correlates with one stream only (no gating)

  Key hypothesis (Gap #36 extension):
    AND-gate features should dominate at the gc(k) PEAK layer — because the peak
    gc layer is precisely where the model integrates audio most causally.
    OR-gate features should dominate at EARLY decoder layers (still audio-accessible)
    and LATE layers (language priors take over with OR = context-only paths).

  Denoising patching protocol:
    For each feature f at each layer k:
      1. "clean" run: audio+context (normal)
      2. "noisy" run: audio replaced with Gaussian noise
      3. "patched" run: re-inject clean audio activations at f while keeping noise elsewhere
    Gate classification:
      AND-gate:  feature active in clean, drops in noisy, RECOVERS in patched  → audio-essential, recoverable
      OR-gate:   feature active in clean, STAYS active in noisy (context fills in) → not audio-gated
      Passthrough: feature active in clean, drops in noisy, does NOT recover in patched

  gc(k) prediction:
    gc_peak_layer should have highest AND-gate fraction.
    Result table: per-layer AND%, OR%, Passthrough%, and gc(k) score.

CPU-feasible: mock tensors, no model download.

Usage:
    python3 and_or_gc_patching_mock.py          # print full report
    python3 and_or_gc_patching_mock.py --json   # JSON output
    python3 and_or_gc_patching_mock.py --seed N # reproducibility

Dependencies: numpy only
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from typing import NamedTuple

import numpy as np


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

N_LAYERS = 8            # total layers (encoder + connector + decoder-early)
GC_PEAK_LAYER = 3       # ground-truth gc(k) peak (connector / cross-modal bridge)
N_FEATURES = 64         # SAE feature count per layer
N_STIMULI = 30          # stimuli per run
SEED_BASE = 42
ACTIVATION_THRESHOLD = 0.5   # binarisation threshold for gate classification
RECOVERY_THRESHOLD = 0.4     # how much feature must recover in patched run (fraction of clean)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FeatureRecord:
    """One SAE feature at one layer."""
    layer: int
    feature_id: int
    clean_mean: float       # mean activation in clean run
    noisy_mean: float       # mean activation in noisy run
    patched_mean: float     # mean activation in patched run
    gate_type: str          # "AND", "OR", "Passthrough", "Silent"


@dataclass
class LayerStats:
    """Aggregate gate statistics for one layer."""
    layer: int
    gc_score: float         # simulated gc(k) at this layer
    n_features: int
    and_pct: float
    or_pct: float
    pass_pct: float
    silent_pct: float
    and_count: int
    or_count: int
    pass_count: int
    silent_count: int


class PatrolResult(NamedTuple):
    layer_stats: list[LayerStats]
    feature_records: list[FeatureRecord]
    gc_peak_predicted: int
    gc_peak_actual: int
    hypothesis_confirmed: bool
    and_peak_correlation: float     # Pearson r(AND%, gc_score) across layers


# ---------------------------------------------------------------------------
# Simulation helpers
# ---------------------------------------------------------------------------

def simulate_gc_profile(n_layers: int, peak_layer: int, rng: np.random.Generator) -> np.ndarray:
    """
    Simulate a realistic gc(k) profile — peaked at peak_layer with
    a smooth bell-shaped envelope + noise.
    """
    layers = np.arange(n_layers)
    # Bell curve centred at peak_layer
    sigma = 1.5
    gc = np.exp(-0.5 * ((layers - peak_layer) / sigma) ** 2)
    # Add small noise
    gc += rng.normal(0, 0.04, n_layers)
    gc = np.clip(gc, 0.05, 1.0)
    return gc


def mock_activations(
    layer: int,
    peak_layer: int,
    n_stimuli: int,
    n_features: int,
    condition: str,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Generate mock SAE feature activations (shape: n_stimuli x n_features).

    The structure encodes the expected AND/OR/Passthrough distribution:
    - Features near the peak layer are biased toward AND-gate structure
      (require audio signal to be active)
    - Features far from peak are biased toward OR-gate or Passthrough

    condition: "clean" | "noisy" | "patched"
    """
    proximity = 1.0 - abs(layer - peak_layer) / peak_layer  # 0..1, max at peak
    # Base signal: correlated with audio (high near peak)
    audio_signal = rng.normal(loc=0.6 * proximity, scale=0.2, size=(n_stimuli, n_features))

    if condition == "clean":
        # Clean: full audio + context both available
        context_signal = rng.normal(0.3, 0.15, (n_stimuli, n_features))
        activations = audio_signal + context_signal
    elif condition == "noisy":
        # Noisy: audio replaced with Gaussian noise (no structured signal)
        noise = rng.normal(0.0, 0.2, (n_stimuli, n_features))
        context_signal = rng.normal(0.3, 0.15, (n_stimuli, n_features))
        # Near peak: AND-gate features lose audio dependency → drop more
        # Far from peak: OR-gate features can use context as substitute → stay up
        audio_contribution = noise * (1 - 0.7 * proximity)  # near peak: mostly noise
        activations = audio_contribution + context_signal
    elif condition == "patched":
        # Patched: re-inject clean audio activations at peak-proximate features
        # only features that were audio-gated (AND-type) actually recover
        context_signal = rng.normal(0.3, 0.15, (n_stimuli, n_features))
        # Recovery strength scales with proximity to peak
        recovery_mask = rng.uniform(0, 1, n_features) < proximity  # features that CAN recover
        patched_audio = np.where(
            recovery_mask,
            rng.normal(0.6 * proximity, 0.15, (n_stimuli, n_features)),  # recovered
            rng.normal(0.0, 0.2, (n_stimuli, n_features)),               # still noisy
        )
        activations = patched_audio + context_signal
    else:
        raise ValueError(f"Unknown condition: {condition}")

    return np.clip(activations, 0.0, None)


def classify_gate(
    clean: float, noisy: float, patched: float, threshold: float, recovery_frac: float
) -> str:
    """
    Classify one feature into AND / OR / Passthrough / Silent gate type.

    AND-gate:     clean > threshold AND noisy drops significantly AND patched recovers
    OR-gate:      clean > threshold AND noisy stays near clean (context fills in)
    Passthrough:  clean > threshold AND noisy drops AND patched does NOT recover
    Silent:       clean ≤ threshold (feature not meaningfully active)
    """
    if clean <= threshold:
        return "Silent"

    drop_ratio = (clean - noisy) / (clean + 1e-8)
    recover_ratio = (patched - noisy) / (clean - noisy + 1e-8) if (clean - noisy) > 0.05 else 0.0

    if drop_ratio < 0.2:
        # Feature doesn't drop much in noise → OR-gate (context can substitute)
        return "OR"
    elif recover_ratio >= recovery_frac:
        # Feature drops in noise AND recovers when audio is patched back → AND-gate
        return "AND"
    else:
        # Feature drops in noise but doesn't recover → audio-correlated passthrough
        return "Passthrough"


# ---------------------------------------------------------------------------
# Main protocol
# ---------------------------------------------------------------------------

def run_patching_protocol(
    n_layers: int = N_LAYERS,
    gc_peak_layer: int = GC_PEAK_LAYER,
    n_features: int = N_FEATURES,
    n_stimuli: int = N_STIMULI,
    seed: int = SEED_BASE,
) -> PatrolResult:
    """Execute the AND/OR Gate × gc(k) denoising patching protocol."""

    rng = np.random.default_rng(seed)
    gc_profile = simulate_gc_profile(n_layers, gc_peak_layer, rng)

    layer_stats: list[LayerStats] = []
    all_features: list[FeatureRecord] = []

    for layer in range(n_layers):
        # Generate activations for each condition
        clean_acts = mock_activations(layer, gc_peak_layer, n_stimuli, n_features, "clean", rng)
        noisy_acts = mock_activations(layer, gc_peak_layer, n_stimuli, n_features, "noisy", rng)
        patched_acts = mock_activations(layer, gc_peak_layer, n_stimuli, n_features, "patched", rng)

        # Per-feature means
        clean_means = clean_acts.mean(axis=0)
        noisy_means = noisy_acts.mean(axis=0)
        patched_means = patched_acts.mean(axis=0)

        gate_counts = {"AND": 0, "OR": 0, "Passthrough": 0, "Silent": 0}
        for feat_id in range(n_features):
            gate = classify_gate(
                clean=clean_means[feat_id],
                noisy=noisy_means[feat_id],
                patched=patched_means[feat_id],
                threshold=ACTIVATION_THRESHOLD,
                recovery_frac=RECOVERY_THRESHOLD,
            )
            gate_counts[gate] += 1
            all_features.append(FeatureRecord(
                layer=layer,
                feature_id=feat_id,
                clean_mean=round(float(clean_means[feat_id]), 4),
                noisy_mean=round(float(noisy_means[feat_id]), 4),
                patched_mean=round(float(patched_means[feat_id]), 4),
                gate_type=gate,
            ))

        nf = n_features
        stats = LayerStats(
            layer=layer,
            gc_score=round(float(gc_profile[layer]), 4),
            n_features=nf,
            and_pct=round(100 * gate_counts["AND"] / nf, 1),
            or_pct=round(100 * gate_counts["OR"] / nf, 1),
            pass_pct=round(100 * gate_counts["Passthrough"] / nf, 1),
            silent_pct=round(100 * gate_counts["Silent"] / nf, 1),
            and_count=gate_counts["AND"],
            or_count=gate_counts["OR"],
            pass_count=gate_counts["Passthrough"],
            silent_count=gate_counts["Silent"],
        )
        layer_stats.append(stats)

    # Evaluate hypothesis: predicted gc_peak = layer with highest AND%
    and_pcts = np.array([s.and_pct for s in layer_stats])
    gc_scores = np.array([s.gc_score for s in layer_stats])
    gc_peak_predicted = int(np.argmax(and_pcts))

    # Pearson correlation between AND% and gc_score across layers
    r = float(np.corrcoef(and_pcts, gc_scores)[0, 1])

    hypothesis_confirmed = (gc_peak_predicted == gc_peak_layer) and (r > 0.6)

    return PatrolResult(
        layer_stats=layer_stats,
        feature_records=all_features,
        gc_peak_predicted=gc_peak_predicted,
        gc_peak_actual=gc_peak_layer,
        hypothesis_confirmed=hypothesis_confirmed,
        and_peak_correlation=round(r, 4),
    )


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def print_report(result: PatrolResult) -> None:
    print("=" * 70)
    print("AND/OR Gate × gc(k): Denoising Patching Protocol Mock — Q070")
    print("=" * 70)
    print(f"\nHypothesis: gc(k) peak layer = layer with highest AND-gate fraction")
    print(f"Ground-truth peak: Layer {result.gc_peak_actual}")
    print(f"Predicted peak (max AND%): Layer {result.gc_peak_predicted}")
    status = "✓ CONFIRMED" if result.hypothesis_confirmed else "✗ NOT CONFIRMED"
    print(f"Status: {status}")
    print(f"AND% × gc(k) Pearson r = {result.and_peak_correlation:.4f}")

    print("\n--- Per-Layer Gate Taxonomy Table ---")
    header = f"{'L':>3}  {'gc(k)':>6}  {'AND%':>6}  {'OR%':>6}  {'Pass%':>6}  {'Sil%':>6}  {'Note'}"
    print(header)
    print("-" * 60)
    for s in result.layer_stats:
        note = ""
        if s.layer == result.gc_peak_actual:
            note = "← gc(k) PEAK [ground truth]"
        elif s.layer == result.gc_peak_predicted and s.layer != result.gc_peak_actual:
            note = "← AND% peak [predicted, MISMATCH]"
        elif s.layer == result.gc_peak_predicted:
            note = "← AND% peak [predicted ✓]"
        print(
            f"{s.layer:>3}  {s.gc_score:>6.3f}  {s.and_pct:>6.1f}  {s.or_pct:>6.1f}  "
            f"{s.pass_pct:>6.1f}  {s.silent_pct:>6.1f}  {note}"
        )

    print("\n--- Gate Distribution at gc(k) Peak Layer ---")
    peak_stats = result.layer_stats[result.gc_peak_actual]
    total_active = peak_stats.n_features - peak_stats.silent_count
    print(f"Layer {result.gc_peak_actual}: gc(k) = {peak_stats.gc_score:.3f}")
    print(f"  AND-gate:   {peak_stats.and_count:>3} / {total_active} active  ({peak_stats.and_pct:.1f}%)")
    print(f"  OR-gate:    {peak_stats.or_count:>3} / {total_active} active  ({peak_stats.or_pct:.1f}%)")
    print(f"  Passthrough:{peak_stats.pass_count:>3} / {total_active} active  ({peak_stats.pass_pct:.1f}%)")
    print(f"  Silent:     {peak_stats.silent_count:>3}")

    print("\n--- Interpretation ---")
    print(
        "AND-gate features require BOTH audio + context to activate. Their")
    print("dominance at the gc(k) peak layer confirms that this layer acts as a")
    print("conjunctive audio-grounding gate: it causally integrates both streams")
    print("rather than using context alone (OR) or passing audio through (Pass).")
    print()
    if result.hypothesis_confirmed:
        print("✓ Mock validates the AND-gate hypothesis: gc peak = AND-gate peak.")
        print("  → Real-data test: run with Whisper activations + LibriSpeech clean/noisy.")
        print("  → Paper A §5.5: AND-gate fraction as a proxy for gc(k) localization.")
    else:
        print("⚠ Hypothesis not confirmed in this mock. Possible causes:")
        print("  - gc peak too close to boundary (adjust peak_layer or n_layers)")
        print("  - Recovery threshold too strict (adjust RECOVERY_THRESHOLD)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="AND/OR Gate × gc(k) patching mock (Q070)")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--seed", type=int, default=SEED_BASE, help="Random seed")
    parser.add_argument("--layers", type=int, default=N_LAYERS, help="Number of layers")
    parser.add_argument("--peak", type=int, default=GC_PEAK_LAYER, help="gc(k) peak layer")
    parser.add_argument("--features", type=int, default=N_FEATURES, help="SAE features per layer")
    parser.add_argument("--stimuli", type=int, default=N_STIMULI, help="Stimuli per run")
    args = parser.parse_args()

    result = run_patching_protocol(
        n_layers=args.layers,
        gc_peak_layer=args.peak,
        n_features=args.features,
        n_stimuli=args.stimuli,
        seed=args.seed,
    )

    if args.json:
        out = {
            "gc_peak_actual": result.gc_peak_actual,
            "gc_peak_predicted": result.gc_peak_predicted,
            "hypothesis_confirmed": result.hypothesis_confirmed,
            "and_peak_correlation": result.and_peak_correlation,
            "layer_stats": [asdict(s) for s in result.layer_stats],
        }
        print(json.dumps(out, indent=2))
    else:
        print_report(result)


if __name__ == "__main__":
    main()
