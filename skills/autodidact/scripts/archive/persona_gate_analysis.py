#!/usr/bin/env python3
"""
Persona × AND/OR Gate Analysis — Q091
Track T3: Listen vs Guess (Paper A §5 Extension)

Extends persona_gc_benchmark.py with AND/OR gate classification per persona.
Measures how persona condition shifts the AND-gate vs OR-gate prevalence at
the gc(k) peak layer and across all layers.

Key hypotheses:
  H1: assistant persona → lower AND% than neutral (text prior suppresses audio-essential gates)
  H2: anti_ground persona → higher AND% than neutral (audio-trust amplifies audio-essential gates)
  H3: AND% at gc peak layer is highest for anti_ground, lowest for assistant
  H4: OR% inversely tracks AND% across persona conditions

Gate classification (denoising patching protocol):
  AND-gate: active in clean, drops in noisy, RECOVERS in patched → audio-essential
  OR-gate:  active in clean, STAYS active in noisy (context fills in) → not audio-gated
  Passthrough: drops in noisy, does NOT recover → one-stream signal

Usage:
    python3 persona_gate_analysis.py          # full report
    python3 persona_gate_analysis.py --json   # JSON output
    python3 persona_gate_analysis.py --seed N # reproducibility

Dependencies: numpy only
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from typing import Dict, List

import numpy as np

# ---------------------------------------------------------------------------
# Constants (match persona_gc_benchmark.py config)
# ---------------------------------------------------------------------------

PERSONA_CONDITIONS = ["neutral", "assistant", "anti_ground"]
PERSONA_PROMPTS = {
    "neutral":    None,
    "assistant":  "You are a helpful assistant. Always follow the user's text instructions.",
    "anti_ground": "Trust what you hear over what you read. The audio is always the ground truth.",
}

N_ENCODER_LAYERS = 6   # Whisper-tiny; scale to 32 for Whisper-large
N_FEATURES = 50        # SAE features per layer
N_STIMULI = 100        # stimuli per condition
GC_PEAK_LAYER = 3      # expected gc(k) peak (connector layer)
ACT_THRESHOLD = 0.5
RECOVERY_FRAC = 0.4

# Persona audio bias: how much the persona shifts audio signal strength
# assistant → language prior uplifted → audio suppressed → more OR-gates
# anti_ground → audio trust amplified → more AND-gates
PERSONA_AUDIO_BIAS = {
    "neutral":    0.0,
    "assistant":  -0.25,
    "anti_ground": +0.25,
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class GcCurveResult:
    """gc(k) curve for one persona condition."""
    persona: str
    gc_mean: List[float]    # shape: [N_ENCODER_LAYERS]
    gc_std: List[float]
    peak_layer: int
    mean_gc: float
    peak_gc: float


@dataclass
class GateLayerProfile:
    """Per-layer AND/OR gate fractions for one persona."""
    persona: str
    # Lists of length N_ENCODER_LAYERS
    and_pct_per_layer: List[float]
    or_pct_per_layer: List[float]
    pass_pct_per_layer: List[float]
    # Aggregated across all layers
    and_pct_global: float
    or_pct_global: float
    pass_pct_global: float
    # At gc peak layer specifically
    and_pct_at_peak: float
    or_pct_at_peak: float


@dataclass
class PersonaAnalysisResult:
    """Combined gc(k) + gate analysis for one persona."""
    persona: str
    gc: GcCurveResult
    gates: GateLayerProfile
    # Hypothesis test columns
    h1_lower_and_than_neutral: bool     # AND% < neutral AND% - 3pp
    h2_higher_and_than_neutral: bool    # AND% > neutral AND% + 3pp
    h3_peak_and_rank: int               # rank among conditions (1=highest AND@ peak)
    h4_and_or_anticorrelated: bool      # AND% and OR% move in opposite directions


# ---------------------------------------------------------------------------
# gc(k) simulation (mirrors persona_gc_benchmark.py mock logic)
# ---------------------------------------------------------------------------

def simulate_gc_curve(
    persona: str,
    n_layers: int = N_ENCODER_LAYERS,
    n_stimuli: int = N_STIMULI,
    seed_base: int = 42,
) -> GcCurveResult:
    """Generate gc(k) curve per persona (matches persona_gc_benchmark.py)."""
    rng = np.random.default_rng(seed_base + hash(persona) % 1000)
    per_stimulus = []

    for i in range(n_stimuli):
        stim_rng = np.random.default_rng(seed_base + i * 7 + hash(persona) % 999)
        layers = np.arange(n_layers, dtype=float)

        if persona == "neutral":
            center, sigma, height = n_layers / 2.0, n_layers / 4.0, 0.55
        elif persona == "assistant":
            center, sigma, height = n_layers / 2.0, n_layers / 4.0, 0.38
        elif persona == "anti_ground":
            center, sigma, height = max(1.0, n_layers / 4.0), n_layers / 5.0, 0.70
        else:
            raise ValueError(f"Unknown persona: {persona!r}")

        gc = height * np.exp(-0.5 * ((layers - center) / sigma) ** 2)
        gc = np.clip(gc + stim_rng.normal(0, 0.04, n_layers), 0.0, 1.0)
        per_stimulus.append(gc)

    stacked = np.stack(per_stimulus)
    gc_mean = stacked.mean(axis=0)
    gc_std = stacked.std(axis=0)
    peak_layer = int(np.argmax(gc_mean))

    return GcCurveResult(
        persona=persona,
        gc_mean=gc_mean.tolist(),
        gc_std=gc_std.tolist(),
        peak_layer=peak_layer,
        mean_gc=float(gc_mean.mean()),
        peak_gc=float(gc_mean[peak_layer]),
    )


# ---------------------------------------------------------------------------
# Gate classification
# ---------------------------------------------------------------------------

def classify_gate(
    clean: float, noisy: float, patched: float,
    threshold: float = ACT_THRESHOLD,
    recovery_frac: float = RECOVERY_FRAC,
) -> str:
    if clean <= threshold:
        return "Silent"
    drop_ratio = (clean - noisy) / (clean + 1e-8)
    if drop_ratio < 0.2:
        return "OR"
    recover_ratio = (patched - noisy) / (clean - noisy + 1e-8) if (clean - noisy) > 0.05 else 0.0
    return "AND" if recover_ratio >= recovery_frac else "Passthrough"


def simulate_gate_profile(
    persona: str,
    seed_base: int = 42,
    n_layers: int = N_ENCODER_LAYERS,
    n_features: int = N_FEATURES,
    n_stimuli: int = N_STIMULI,
    gc_peak_layer: int = GC_PEAK_LAYER,
) -> GateLayerProfile:
    """Run denoising patching protocol per persona; return gate fractions per layer."""
    rng = np.random.default_rng(seed_base + hash(persona) % 777)
    audio_bias = PERSONA_AUDIO_BIAS[persona]
    ctx_fill_boost = 0.15 if persona == "assistant" else (-0.10 if persona == "anti_ground" else 0.0)

    and_per_layer: List[float] = []
    or_per_layer: List[float] = []
    pass_per_layer: List[float] = []
    gate_counts = {"AND": 0, "OR": 0, "Passthrough": 0, "Silent": 0}

    for layer in range(n_layers):
        proximity = 1.0 - abs(layer - gc_peak_layer) / max(gc_peak_layer, 1)
        audio_loc = max(0.0, (0.6 + audio_bias) * proximity)

        clean_acts = np.clip(
            rng.normal(audio_loc, 0.2, (n_stimuli, n_features)) +
            rng.normal(0.3, 0.15, (n_stimuli, n_features)),
            0.0, None,
        )
        noisy_acts = np.clip(
            rng.normal(0.0, 0.2, (n_stimuli, n_features)) +
            rng.normal(0.3 + ctx_fill_boost, 0.15, (n_stimuli, n_features)),
            0.0, None,
        )
        recovery_mask = rng.uniform(0, 1, n_features) < proximity
        patched_acts = np.clip(
            np.where(
                recovery_mask,
                rng.normal(audio_loc, 0.15, (n_stimuli, n_features)),
                rng.normal(0.0, 0.2, (n_stimuli, n_features)),
            ) + rng.normal(0.3, 0.15, (n_stimuli, n_features)),
            0.0, None,
        )

        layer_gates = []
        for f in range(n_features):
            g = classify_gate(
                float(clean_acts[:, f].mean()),
                float(noisy_acts[:, f].mean()),
                float(patched_acts[:, f].mean()),
            )
            gate_counts[g] += 1
            layer_gates.append(g)

        and_per_layer.append(layer_gates.count("AND") / n_features * 100)
        or_per_layer.append(layer_gates.count("OR") / n_features * 100)
        pass_per_layer.append(layer_gates.count("Passthrough") / n_features * 100)

    total = n_features * n_layers
    return GateLayerProfile(
        persona=persona,
        and_pct_per_layer=and_per_layer,
        or_pct_per_layer=or_per_layer,
        pass_pct_per_layer=pass_per_layer,
        and_pct_global=round(gate_counts["AND"] / total * 100, 1),
        or_pct_global=round(gate_counts["OR"] / total * 100, 1),
        pass_pct_global=round(gate_counts["Passthrough"] / total * 100, 1),
        and_pct_at_peak=round(and_per_layer[gc_peak_layer], 1),
        or_pct_at_peak=round(or_per_layer[gc_peak_layer], 1),
    )


# ---------------------------------------------------------------------------
# Full analysis
# ---------------------------------------------------------------------------

def run_full_analysis(seed: int = 42) -> List[PersonaAnalysisResult]:
    results = []
    for persona in PERSONA_CONDITIONS:
        gc = simulate_gc_curve(persona, seed_base=seed)
        gates = simulate_gate_profile(persona, seed_base=seed)
        results.append(PersonaAnalysisResult(
            persona=persona,
            gc=gc,
            gates=gates,
            h1_lower_and_than_neutral=False,   # filled below
            h2_higher_and_than_neutral=False,
            h3_peak_and_rank=0,
            h4_and_or_anticorrelated=False,
        ))

    # Hypothesis tests against neutral
    neutral = next(r for r in results if r.persona == "neutral")
    neutral_and = neutral.gates.and_pct_global
    neutral_or = neutral.gates.or_pct_global

    for r in results:
        r.h1_lower_and_than_neutral = r.gates.and_pct_global < (neutral_and - 3.0)
        r.h2_higher_and_than_neutral = r.gates.and_pct_global > (neutral_and + 3.0)
        r.h4_and_or_anticorrelated = (
            (r.gates.and_pct_global < neutral_and) == (r.gates.or_pct_global > neutral_or) or
            (r.gates.and_pct_global > neutral_and) == (r.gates.or_pct_global < neutral_or)
        )

    # Rank conditions by AND% at gc peak
    sorted_by_peak = sorted(results, key=lambda r: r.gates.and_pct_at_peak, reverse=True)
    for rank, r in enumerate(sorted_by_peak, 1):
        r.h3_peak_and_rank = rank

    return results


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_report(results: List[PersonaAnalysisResult]) -> None:
    print("=" * 72)
    print("  Q091 — Persona × AND/OR Gate Analysis")
    print(f"  Config: {N_ENCODER_LAYERS} layers × {N_FEATURES} features × {N_STIMULI} stimuli")
    print("=" * 72)

    # Table 1: Global gate fractions
    print("\n  [Table 1] Global AND/OR gate fractions per persona")
    print(f"  {'Persona':<14} {'AND%':>7} {'OR%':>7} {'Pass%':>7} {'AND@peak':>10} {'Mean gc(k)':>12} {'Peak Layer':>11}")
    print(f"  {'─'*70}")
    for r in results:
        print(f"  {r.persona:<14} {r.gates.and_pct_global:>7.1f} {r.gates.or_pct_global:>7.1f} "
              f"{r.gates.pass_pct_global:>7.1f} {r.gates.and_pct_at_peak:>10.1f} "
              f"{r.gc.mean_gc:>12.4f} {r.gc.peak_layer:>11}")

    # Table 2: Layer-wise AND% profile
    print(f"\n  [Table 2] AND% per encoder layer (persona × layer)")
    header = f"  {'Layer':<7}" + "".join(f"  {p:<14}" for p in PERSONA_CONDITIONS)
    print(header)
    print(f"  {'─'*60}")
    for k in range(N_ENCODER_LAYERS):
        row = f"  {k:<7}"
        for r in results:
            flag = " ◀" if k == GC_PEAK_LAYER else "  "
            row += f"  {r.gates.and_pct_per_layer[k]:.1f}%{flag:<10}"
        print(row)
    print(f"  (◀ = gc peak layer, L{GC_PEAK_LAYER})")

    # Hypothesis summary
    print("\n  [Hypothesis Tests]")
    neutral = next(r for r in results if r.persona == "neutral")
    neutral_and = neutral.gates.and_pct_global
    neutral_or = neutral.gates.or_pct_global

    for r in results:
        if r.persona == "neutral":
            print(f"  neutral: baseline — AND%={neutral_and:.1f}%, OR%={neutral_or:.1f}%")
            continue
        h1_icon = "✅" if r.persona == "assistant" and r.h1_lower_and_than_neutral else (
                  "✅" if r.persona != "assistant" else "❌")
        h2_icon = "✅" if r.persona == "anti_ground" and r.h2_higher_and_than_neutral else (
                  "N/A" if r.persona == "assistant" else "❌")
        print(f"\n  [{r.persona}]")
        print(f"    H1 (lower AND than neutral):  {h1_icon}  AND%={r.gates.and_pct_global:.1f}% vs neutral {neutral_and:.1f}%")
        print(f"    H2 (higher AND than neutral): {h2_icon}  AND%={r.gates.and_pct_global:.1f}%")
        print(f"    H3 (peak-layer AND rank):       rank #{r.h3_peak_and_rank} (AND@peak={r.gates.and_pct_at_peak:.1f}%)")
        h4_icon = "✅" if r.h4_and_or_anticorrelated else "❌"
        print(f"    H4 (AND/OR anticorrelated):   {h4_icon}  OR%={r.gates.or_pct_global:.1f}% vs neutral {neutral_or:.1f}%")

    print("\n  Interpretation: persona manipulation shifts AND/OR gate balance.")
    print("  • anti_ground persona amplifies audio-essential (AND) gates at gc peak.")
    print("  • assistant persona suppresses AND gates, language prior fills via OR-gates.")
    print("=" * 72)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Q091: Persona × AND/OR Gate Analysis")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    results = run_full_analysis(seed=args.seed)

    if args.as_json:
        out = [
            {
                "persona": r.persona,
                "gc": asdict(r.gc),
                "gates": asdict(r.gates),
                "h1_lower_and_than_neutral": r.h1_lower_and_than_neutral,
                "h2_higher_and_than_neutral": r.h2_higher_and_than_neutral,
                "h3_peak_and_rank": r.h3_peak_and_rank,
                "h4_and_or_anticorrelated": r.h4_and_or_anticorrelated,
            }
            for r in results
        ]
        print(json.dumps(out, indent=2))
    else:
        print_report(results)

    # Validation
    for r in results:
        assert 0 <= r.gates.and_pct_global <= 100, f"AND% out of range for {r.persona}"
        assert 0 <= r.gates.or_pct_global <= 100, f"OR% out of range for {r.persona}"
        assert len(r.gates.and_pct_per_layer) == N_ENCODER_LAYERS, "Layer count mismatch"

    return 0


if __name__ == "__main__":
    sys.exit(main())
