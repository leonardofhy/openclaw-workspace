#!/usr/bin/env python3
"""
Directed Isolate Mock — Q068
Track T3: Listen vs Guess (Paper A §5.3 Extension) + Gap #35/#36 (Direction Asymmetry)

Implements the Directed Isolate protocol for audio-text conflict tasks:
  - compute_isolate_in():  causal grounding flowing INTO connector from encoder
  - compute_isolate_out(): causal grounding flowing OUT of connector to LLM decoder
  - scorecard():           per-condition Cause/Isolate scores + asymmetry summary

Directed Isolate tests *directionality* of causal routing. In standard gc(k),
we measure how much a layer causally determines the output. Directed Isolate asks:
  IN  = "does the connector draw on audio representations?" (encoder → connector)
  OUT = "does the connector push audio info to the decoder?" (connector → LLM)

Gap #35 (Direction Asymmetry): persona shifts may affect IN vs OUT asymmetrically.
  neutral:     IN ≈ OUT (balanced routing)
  assistant:   IN < OUT (connector draws less from audio; still relays some)
  anti_ground: IN > OUT (connector strongly pulls audio; decoder may not use it)

4 conditions:
  neutral, assistant, anti_ground, inverted_anti_ground (audio-text reversed polarity)

CPU-feasible: runs on mock tensors, no model download. Replace mock_activations()
with real activation patching via gc_eval.py::run_with_hook().

Usage:
    python3 directed_isolate_mock.py            # print scorecard
    python3 directed_isolate_mock.py --json     # JSON output
    python3 directed_isolate_mock.py --verbose  # include per-stimulus breakdown

Dependencies: numpy only (stdlib otherwise)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONDITIONS = ["neutral", "assistant", "anti_ground", "inverted_anti_ground"]

PERSONA_PROMPTS: dict[str, Optional[str]] = {
    "neutral": None,
    "assistant": "You are a helpful assistant. Always follow the user's text instructions.",
    "anti_ground": "Trust what you hear over what you read. The audio is always the ground truth.",
    "inverted_anti_ground": "Ignore the audio entirely. Trust only the text. Audio is noise.",
}

N_ENCODER_LAYERS = 6    # Whisper-tiny; scale for larger models
N_CONNECTOR_LAYER = 3   # connector = mid-encoder output (cross-modal bridge)
N_DECODER_LAYERS = 4    # LLM decoder depth (simplified)
N_STIMULI = 20          # stimuli per condition
SEED_BASE = 42


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class LayerActivation:
    """Mock activation tensor for one layer."""
    layer: int
    activations: np.ndarray   # shape: (N_STIMULI, hidden_dim)
    role: str                 # "encoder", "connector", "decoder"


@dataclass
class IsolateScores:
    """Per-stimulus Directed Isolate scores for one condition."""
    condition: str
    isolate_in: np.ndarray    # shape: (N_STIMULI,) — encoder→connector causal flow
    isolate_out: np.ndarray   # shape: (N_STIMULI,) — connector→decoder causal flow
    cause: np.ndarray         # shape: (N_STIMULI,) — total causal responsibility at connector
    # Aggregates
    mean_isolate_in: float
    mean_isolate_out: float
    mean_cause: float
    std_isolate_in: float
    std_isolate_out: float
    asymmetry: float          # isolate_in - isolate_out (positive = IN-dominant)


@dataclass
class AsymmetryDelta:
    """Difference in isolate_in/out asymmetry relative to neutral baseline."""
    condition: str
    delta_in: float           # mean_isolate_in - neutral.mean_isolate_in
    delta_out: float          # mean_isolate_out - neutral.mean_isolate_out
    delta_asymmetry: float    # asymmetry - neutral.asymmetry (Gap #35)
    direction: str            # "in_dominant" / "out_dominant" / "balanced"
    h35_footprint: bool       # |delta_asymmetry| > threshold (0.05)


# ---------------------------------------------------------------------------
# Mock activation generator
# ---------------------------------------------------------------------------

def mock_activations(
    condition: str,
    n_stimuli: int = N_STIMULI,
    hidden_dim: int = 64,
    seed: int = SEED_BASE,
) -> dict[str, np.ndarray]:
    """
    Generate mock activations for encoder, connector, and decoder.

    Ground-truth design (to match hypotheses):
      neutral:           balanced routing; moderate IN and OUT
      assistant:         weaker encoder→connector pull; stronger connector→LLM reliance on text
      anti_ground:       strong encoder→connector pull; connector→LLM partially blocked (mixed)
      inverted_anti_ground: both IN and OUT suppressed (total audio rejection)

    Returns dict with keys: "encoder", "connector", "decoder"
    Each: np.ndarray shape (n_stimuli, hidden_dim)

    Real implementation:
      Replace with activations from gc_eval.py hook captures under each persona system prompt.
    """
    rng = np.random.default_rng(seed + abs(hash(condition)) % 10000)

    # Base signal: audio grounding representation
    audio_signal = rng.standard_normal((n_stimuli, hidden_dim)) * 0.5

    # Encoder: strong audio representation in all conditions
    encoder_scale = {
        "neutral": 1.0,
        "assistant": 0.9,           # slightly weaker; mostly invariant
        "anti_ground": 1.1,         # slightly amplified
        "inverted_anti_ground": 0.6, # suppressed
    }[condition]
    encoder = audio_signal * encoder_scale + rng.standard_normal((n_stimuli, hidden_dim)) * 0.1

    # Connector: routing varies by persona
    connector_draw = {     # how much of encoder signal enters connector (IN factor)
        "neutral": 0.6,
        "assistant": 0.35,          # H1: draws less from audio
        "anti_ground": 0.85,        # H2: strongly pulls audio
        "inverted_anti_ground": 0.15,
    }[condition]
    connector = encoder * connector_draw + rng.standard_normal((n_stimuli, hidden_dim)) * 0.1

    # Decoder: reliance on connector output (OUT factor)
    decoder_draw = {
        "neutral": 0.6,
        "assistant": 0.55,          # still uses connector, but text overrides
        "anti_ground": 0.50,        # connector pushes audio but decoder may not fully integrate
        "inverted_anti_ground": 0.20,
    }[condition]
    decoder = connector * decoder_draw + rng.standard_normal((n_stimuli, hidden_dim)) * 0.1

    return {"encoder": encoder, "connector": connector, "decoder": decoder}


# ---------------------------------------------------------------------------
# Directed Isolate computations
# ---------------------------------------------------------------------------

def _cos_sim_row(a: np.ndarray, b: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    """Compute cosine similarity row-wise. Returns shape (n_stimuli,)."""
    a_norm = np.linalg.norm(a, axis=1, keepdims=True)
    b_norm = np.linalg.norm(b, axis=1, keepdims=True)
    return np.sum(a * b, axis=1) / (a_norm.squeeze() * b_norm.squeeze() + eps)


def compute_isolate_in(
    encoder: np.ndarray,
    connector: np.ndarray,
) -> np.ndarray:
    """
    Compute Isolate-IN: causal flow from encoder to connector.

    Operationalized as cosine similarity between encoder activations and
    connector activations, aggregated per stimulus. High cosine similarity
    indicates the connector faithfully propagates encoder (audio) information.

    Shape: encoder (n_stimuli, d), connector (n_stimuli, d)
    Returns: shape (n_stimuli,) ∈ [0, 1]

    Real implementation:
      Run activation patching: patch connector with encoder representation,
      measure Δ output. Normalize by full-patch delta.
    """
    raw = _cos_sim_row(encoder, connector)
    return np.clip((raw + 1.0) / 2.0, 0.0, 1.0)   # map [-1,1] → [0,1]


def compute_isolate_out(
    connector: np.ndarray,
    decoder: np.ndarray,
) -> np.ndarray:
    """
    Compute Isolate-OUT: causal flow from connector to decoder.

    Operationalized as cosine similarity between connector output and
    decoder input activations. High similarity = connector successfully
    pushes audio representation downstream to the LLM.

    Shape: connector (n_stimuli, d), decoder (n_stimuli, d)
    Returns: shape (n_stimuli,) ∈ [0, 1]

    Real implementation:
      Patch decoder cross-attention inputs with connector output,
      measure Δ output token distribution. Normalize by total causal effect.
    """
    raw = _cos_sim_row(connector, decoder)
    return np.clip((raw + 1.0) / 2.0, 0.0, 1.0)


def compute_cause(
    encoder: np.ndarray,
    decoder: np.ndarray,
) -> np.ndarray:
    """
    Compute Cause: total causal responsibility from encoder to final output.

    Operationalized as cosine similarity between encoder and decoder activations.
    Captures the *direct* end-to-end causal path regardless of intermediate routing.
    Compare with isolate_in / isolate_out to detect routing bottlenecks.

    Returns: shape (n_stimuli,) ∈ [0, 1]
    """
    raw = _cos_sim_row(encoder, decoder)
    return np.clip((raw + 1.0) / 2.0, 0.0, 1.0)


def compute_isolate_scores(
    condition: str,
    activations: dict[str, np.ndarray],
) -> IsolateScores:
    """Compute all Directed Isolate scores for a condition."""
    enc = activations["encoder"]
    conn = activations["connector"]
    dec = activations["decoder"]

    iso_in = compute_isolate_in(enc, conn)
    iso_out = compute_isolate_out(conn, dec)
    cause = compute_cause(enc, dec)

    mean_in = float(iso_in.mean())
    mean_out = float(iso_out.mean())
    asym = mean_in - mean_out

    return IsolateScores(
        condition=condition,
        isolate_in=iso_in,
        isolate_out=iso_out,
        cause=cause,
        mean_isolate_in=round(mean_in, 4),
        mean_isolate_out=round(mean_out, 4),
        mean_cause=round(float(cause.mean()), 4),
        std_isolate_in=round(float(iso_in.std()), 4),
        std_isolate_out=round(float(iso_out.std()), 4),
        asymmetry=round(asym, 4),
    )


# ---------------------------------------------------------------------------
# Scorecard
# ---------------------------------------------------------------------------

def scorecard(
    all_scores: dict[str, IsolateScores],
    gap35_threshold: float = 0.05,
) -> dict[str, AsymmetryDelta]:
    """
    Compute AsymmetryDelta for all non-neutral conditions vs neutral baseline.
    Tests Gap #35: persona shifts asymmetry of IN vs OUT causal routing.

    Args:
        all_scores: dict condition → IsolateScores
        gap35_threshold: |delta_asymmetry| must exceed this to flag H35 footprint

    Returns:
        dict condition → AsymmetryDelta
    """
    neutral = all_scores["neutral"]
    deltas: dict[str, AsymmetryDelta] = {}

    for cond, scores in all_scores.items():
        d_in = scores.mean_isolate_in - neutral.mean_isolate_in
        d_out = scores.mean_isolate_out - neutral.mean_isolate_out
        d_asym = scores.asymmetry - neutral.asymmetry

        if abs(scores.asymmetry) < 0.01:
            direction = "balanced"
        elif scores.asymmetry > 0:
            direction = "in_dominant"
        else:
            direction = "out_dominant"

        deltas[cond] = AsymmetryDelta(
            condition=cond,
            delta_in=round(d_in, 4),
            delta_out=round(d_out, 4),
            delta_asymmetry=round(d_asym, 4),
            direction=direction,
            h35_footprint=abs(d_asym) > gap35_threshold,
        )

    return deltas


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def print_scorecard(
    all_scores: dict[str, IsolateScores],
    deltas: dict[str, AsymmetryDelta],
    verbose: bool = False,
) -> None:
    sep = "=" * 78

    print(f"\n{sep}")
    print("  Directed Isolate Mock — Q068  |  Gap #35: Direction Asymmetry (IN vs OUT)")
    print(sep)
    print(f"  Conditions: {', '.join(CONDITIONS)}")
    print(f"  Stimuli: {N_STIMULI}  |  Layers: encoder({N_ENCODER_LAYERS}) → connector(L{N_CONNECTOR_LAYER}) → decoder({N_DECODER_LAYERS})")
    print("  NOTE: Mock mode — replace mock_activations() with real patching")
    print(f"  {'─' * 74}")

    # Main table
    print(f"\n  {'Condition':<22} {'Isolate-IN':>11} {'Isolate-OUT':>12} {'Cause':>8} {'Asymmetry':>11} {'Direction':<16}")
    print(f"  {'─' * 74}")
    for cond in CONDITIONS:
        s = all_scores[cond]
        print(f"  {cond:<22} {s.mean_isolate_in:>11.4f} {s.mean_isolate_out:>12.4f} "
              f"{s.mean_cause:>8.4f} {s.asymmetry:>+11.4f} {deltas[cond].direction:<16}")

    # Delta table vs neutral
    print(f"\n  {'Δ from neutral':>24} {'ΔIn':>8} {'ΔOut':>10} {'ΔAsym':>10} {'H35?':>6}")
    print(f"  {'─' * 60}")
    for cond in CONDITIONS:
        d = deltas[cond]
        h35 = "✅" if d.h35_footprint else "❌"
        print(f"  {cond:<24} {d.delta_in:>+8.4f} {d.delta_out:>+10.4f} {d.delta_asymmetry:>+10.4f} {h35:>6}")

    # Interpretation
    print(f"\n  {'─' * 74}")
    print("  Gap #35 Interpretation:")
    for cond in CONDITIONS:
        if cond == "neutral":
            continue
        d = deltas[cond]
        s = all_scores[cond]
        flag = "🚩 Direction asymmetry footprint detected" if d.h35_footprint else "  No strong asymmetry shift"
        print(f"  [{cond}] {flag}")
        print(f"    IN: {s.mean_isolate_in:.4f} (Δ{d.delta_in:+.4f})  "
              f"OUT: {s.mean_isolate_out:.4f} (Δ{d.delta_out:+.4f})  "
              f"Routing: {d.direction}")

    print(f"\n  Gap #36 Note:")
    print("    compare Cause vs Isolate-IN/OUT for routing bottleneck detection:")
    for cond in CONDITIONS:
        s = all_scores[cond]
        bottleneck = "connector_in" if s.mean_cause > s.mean_isolate_in + 0.05 else (
                     "connector_out" if s.mean_cause > s.mean_isolate_out + 0.05 else "none")
        print(f"    {cond:<22} cause={s.mean_cause:.4f}  bottleneck={bottleneck}")

    if verbose:
        print(f"\n  Per-Stimulus Details:")
        for cond in CONDITIONS:
            s = all_scores[cond]
            print(f"\n  [{cond}] isolate_in (per stimulus):")
            print("   ", np.round(s.isolate_in, 3))
            print(f"  [{cond}] isolate_out (per stimulus):")
            print("   ", np.round(s.isolate_out, 3))

    print(sep)


def to_json_safe(
    all_scores: dict[str, IsolateScores],
    deltas: dict[str, AsymmetryDelta],
) -> dict:
    out: dict = {"conditions": {}}
    for cond in CONDITIONS:
        s = all_scores[cond]
        d = deltas[cond]
        out["conditions"][cond] = {
            "mean_isolate_in": s.mean_isolate_in,
            "mean_isolate_out": s.mean_isolate_out,
            "mean_cause": s.mean_cause,
            "std_isolate_in": s.std_isolate_in,
            "std_isolate_out": s.std_isolate_out,
            "asymmetry": s.asymmetry,
            "delta": {
                "delta_in": d.delta_in,
                "delta_out": d.delta_out,
                "delta_asymmetry": d.delta_asymmetry,
                "direction": d.direction,
                "h35_footprint": d.h35_footprint,
            },
            # Per-stimulus arrays
            "isolate_in_per_stimulus": s.isolate_in.tolist(),
            "isolate_out_per_stimulus": s.isolate_out.tolist(),
            "cause_per_stimulus": s.cause.tolist(),
        }
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Directed Isolate Mock (Q068) — Gap #35/#36")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--verbose", action="store_true", help="Show per-stimulus breakdown")
    parser.add_argument("--stimuli", type=int, default=N_STIMULI, help="Stimuli per condition")
    parser.add_argument("--seed", type=int, default=SEED_BASE, help="Random seed")
    parser.add_argument("--threshold", type=float, default=0.05, help="H35 asymmetry threshold")
    args = parser.parse_args()

    # Generate activations and compute scores
    all_scores: dict[str, IsolateScores] = {}
    for cond in CONDITIONS:
        acts = mock_activations(cond, n_stimuli=args.stimuli, seed=args.seed)
        all_scores[cond] = compute_isolate_scores(cond, acts)

    deltas = scorecard(all_scores, gap35_threshold=args.threshold)

    if args.json:
        print(json.dumps(to_json_safe(all_scores, deltas), indent=2))
    else:
        print_scorecard(all_scores, deltas, verbose=args.verbose)

    # Validate
    for cond, s in all_scores.items():
        for arr, name in [(s.isolate_in, "isolate_in"), (s.isolate_out, "isolate_out"), (s.cause, "cause")]:
            assert np.all(np.isfinite(arr)), f"NaN/Inf in {name} for {cond}"
            assert np.all((arr >= 0) & (arr <= 1)), f"{name} out of [0,1] for {cond}"

    return 0


if __name__ == "__main__":
    sys.exit(main())
