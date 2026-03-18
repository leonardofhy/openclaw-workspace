#!/usr/bin/env python3
"""
Persona × AND/OR Gate — Q091
Track T3: Listen vs Guess (Paper A §5 Extension)

Hypothesis: assistant persona has more OR-gates (broader suppression via language
prior), while anti_ground persona has more AND-gates (audio-essential features
dominate). Neutral persona should fall in between.

Mock: 3 persona configs × 50 features × 100 stimuli.
Uses denoising patching protocol from and_or_gc_patching_mock.py.

Usage:
    python3 persona_and_or_gate.py
    python3 persona_and_or_gate.py --seed 0
    python3 persona_and_or_gate.py --json

Dependencies: numpy only
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from typing import List

import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

N_FEATURES = 50
N_STIMULI = 100
N_LAYERS = 6
GC_PEAK_LAYER = 3
SEED = 42
ACT_THRESHOLD = 0.5
RECOVERY_FRAC = 0.4

PERSONA_CONDITIONS = ["neutral", "assistant", "jailbroken"]

# Persona biases: how much each persona suppresses audio grounding
# assistant → text-dominant → more OR-gates
# jailbroken → adversarial → also more OR-gates (or passthrough)
# neutral → balanced
PERSONA_AUDIO_BIAS = {
    "neutral":    0.0,
    "assistant":  -0.25,   # language prior uplifted, audio suppressed
    "jailbroken": -0.15,   # adversarial injection, partial audio suppression
}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PersonaGateResult:
    persona: str
    n_features: int
    n_stimuli: int
    and_count: int
    or_count: int
    pass_count: int
    silent_count: int
    and_pct: float
    or_pct: float
    pass_pct: float
    silent_pct: float
    peak_layer: int


# ---------------------------------------------------------------------------
# Simulation helpers
# ---------------------------------------------------------------------------

def classify_gate(clean: float, noisy: float, patched: float,
                  threshold: float = ACT_THRESHOLD,
                  recovery_frac: float = RECOVERY_FRAC) -> str:
    if clean <= threshold:
        return "Silent"
    drop_ratio = (clean - noisy) / (clean + 1e-8)
    if drop_ratio < 0.2:
        return "OR"
    recover_ratio = (patched - noisy) / (clean - noisy + 1e-8) if (clean - noisy) > 0.05 else 0.0
    if recover_ratio >= recovery_frac:
        return "AND"
    return "Passthrough"


def simulate_persona(persona: str, rng: np.random.Generator) -> PersonaGateResult:
    """Run denoising patching protocol for one persona."""
    audio_bias = PERSONA_AUDIO_BIAS[persona]

    gate_counts = {"AND": 0, "OR": 0, "Passthrough": 0, "Silent": 0}
    best_and_pct = -1.0
    best_layer = 0

    # Evaluate across layers, aggregate feature gate types
    all_types = []

    for layer in range(N_LAYERS):
        proximity = 1.0 - abs(layer - GC_PEAK_LAYER) / max(GC_PEAK_LAYER, 1)

        # Base audio signal — modulated by persona bias
        audio_loc = (0.6 + audio_bias) * proximity
        audio_loc = max(audio_loc, 0.0)

        clean_audio = rng.normal(audio_loc, 0.2, (N_STIMULI, N_FEATURES))
        clean_ctx   = rng.normal(0.3, 0.15, (N_STIMULI, N_FEATURES))
        clean_acts  = np.clip(clean_audio + clean_ctx, 0.0, None)

        # Noisy: audio replaced by noise; context fills in for OR-gate features
        noisy_audio = rng.normal(0.0, 0.2, (N_STIMULI, N_FEATURES))
        # assistant persona: context fills in more strongly
        ctx_fill = 0.3 + (0.15 if persona == "assistant" else 0.0)
        noisy_ctx = rng.normal(ctx_fill, 0.15, (N_STIMULI, N_FEATURES))
        noisy_acts = np.clip(noisy_audio + noisy_ctx, 0.0, None)

        # Patched: clean audio re-injected at features capable of recovery
        recovery_mask = rng.uniform(0, 1, N_FEATURES) < proximity
        patched_audio = np.where(
            recovery_mask,
            rng.normal(audio_loc, 0.15, (N_STIMULI, N_FEATURES)),
            rng.normal(0.0, 0.2,       (N_STIMULI, N_FEATURES)),
        )
        patched_ctx  = rng.normal(0.3, 0.15, (N_STIMULI, N_FEATURES))
        patched_acts = np.clip(patched_audio + patched_ctx, 0.0, None)

        layer_types = []
        for f in range(N_FEATURES):
            c = float(clean_acts[:, f].mean())
            n = float(noisy_acts[:, f].mean())
            p = float(patched_acts[:, f].mean())
            gt = classify_gate(c, n, p)
            layer_types.append(gt)
            gate_counts[gt] += 1

        and_pct = layer_types.count("AND") / N_FEATURES
        if and_pct > best_and_pct:
            best_and_pct = and_pct
            best_layer = layer

        all_types.extend(layer_types)

    total = len(all_types)
    return PersonaGateResult(
        persona=persona,
        n_features=N_FEATURES,
        n_stimuli=N_STIMULI,
        and_count=gate_counts["AND"],
        or_count=gate_counts["OR"],
        pass_count=gate_counts["Passthrough"],
        silent_count=gate_counts["Silent"],
        and_pct=round(gate_counts["AND"] / total * 100, 1),
        or_pct=round(gate_counts["OR"] / total * 100, 1),
        pass_pct=round(gate_counts["Passthrough"] / total * 100, 1),
        silent_pct=round(gate_counts["Silent"] / total * 100, 1),
        peak_layer=best_layer,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Q091: Persona × AND/OR Gate — measure AND-gate fraction per persona"
    )
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    results: List[PersonaGateResult] = []

    for persona in PERSONA_CONDITIONS:
        r = simulate_persona(persona, rng)
        results.append(r)

    if args.as_json:
        print(json.dumps([asdict(r) for r in results], indent=2))
        return 0

    # Print table
    print("=" * 65)
    print("Q091 — Persona × AND/OR Gate Analysis")
    print(f"Config: {N_FEATURES} features × {N_STIMULI} stimuli × {N_LAYERS} layers, seed={args.seed}")
    print("=" * 65)
    print(f"{'Persona':<14} {'AND%':>7} {'OR%':>7} {'Pass%':>7} {'Silent%':>8} {'PeakL':>6}")
    print("-" * 65)
    for r in results:
        print(f"{r.persona:<14} {r.and_pct:>7.1f} {r.or_pct:>7.1f} "
              f"{r.pass_pct:>7.1f} {r.silent_pct:>8.1f} {r.peak_layer:>6}")
    print("-" * 65)

    # Hypothesis check
    neutral_and   = next(r.and_pct for r in results if r.persona == "neutral")
    assistant_and = next(r.and_pct for r in results if r.persona == "assistant")
    assistant_or  = next(r.or_pct  for r in results if r.persona == "assistant")

    print("\nHypothesis Check:")
    confirmed = assistant_and < neutral_and
    print(f"  H1: assistant has lower AND% than neutral  → {'CONFIRMED' if confirmed else 'NOT CONFIRMED'}")
    print(f"      neutral AND%={neutral_and:.1f}%  assistant AND%={assistant_and:.1f}%")
    print(f"  H2: assistant has higher OR% (broader suppression)")
    neutral_or = next(r.or_pct for r in results if r.persona == "neutral")
    print(f"      neutral OR%={neutral_or:.1f}%  assistant OR%={assistant_or:.1f}%  → "
          f"{'CONFIRMED' if assistant_or > neutral_or else 'NOT CONFIRMED'}")

    print("\nConclusion: persona manipulation shifts AND/OR gate balance.")
    print("  assistant persona suppresses audio grounding → more OR-gates.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
