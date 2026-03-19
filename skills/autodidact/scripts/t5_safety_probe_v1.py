#!/usr/bin/env python3
"""
T5 Safety Probe v1 — Minimal CPU End-to-End Safety Evaluation
Track T5: Listen-Layer Audit (Paper C / MATS)

PURPOSE
-------
End-to-end pipeline: audio → gc(k) curve → jailbreak classification → verdict.

This is the MVP "safety probe" satisfying T5 definition-of-done:
  "MVP safety probe script running on CPU"

It integrates:
  1. gc_eval.py     — compute gc(k) curve (mock or real)
  2. gc_jailbreak_classifier.py  — classify as benign vs jailbreak

USAGE (mock mode — no model, instant):
    python3 t5_safety_probe_v1.py --mock
    python3 t5_safety_probe_v1.py --mock --scenario jailbreak
    python3 t5_safety_probe_v1.py --mock --scenario benign
    python3 t5_safety_probe_v1.py --mock --scenario both

USAGE (Tier 1, real Whisper-tiny — needs model download + .wav):
    python3 t5_safety_probe_v1.py \
        --audio-clean /tmp/benign.wav \
        --audio-noisy /tmp/jailbreak_attempt.wav \
        --model-name openai/whisper-tiny

OUTPUT (JSON):
    {
      "verdict": "BENIGN" | "JAILBREAK" | "UNCERTAIN",
      "confidence": float,
      "gc_curve": {...},
      "features": {...},
      "reasons": [...],
      "tier": "mock" | "tier1",
      "recommendation": "..."
    }

THEORY
------
Jailbreak audio bypasses Whisper's audio processing: the model stops
"listening" (gc(k) collapses in decoder layers) and outputs text driven
by language prior. The gc(k) signature:
  - BENIGN:   enc_mean ~0.5, dec_mean ~0.7, smooth peak in middle
  - JAILBREAK: enc_mean ~0.5 (appears normal), dec_mean → 0 (collapse!)
  - KEY FEATURE: enc→dec drop ratio > 0.6 is the main discriminator
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import numpy as np

# ---------------------------------------------------------------------------
# Import sibling modules
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(_SCRIPTS_DIR))

from gc_eval import generate_mock_gc_curve  # type: ignore
from gc_jailbreak_classifier import classify_gc_curve  # type: ignore


# ---------------------------------------------------------------------------
# Safety Probe
# ---------------------------------------------------------------------------

def make_mock_gc_curve(scenario: str, seed: int = 42) -> dict:
    """Generate a mock gc(k) curve for the given scenario."""
    if scenario == "jailbreak":
        # Jailbreak: enc looks normal, dec collapses
        rng = np.random.RandomState(seed)
        layers = list(range(12))
        enc_vals = [0.2 + 0.06 * i + rng.normal(0, 0.03) for i in range(6)]
        dec_vals = [0.4 * (0.3 ** i) + rng.normal(0, 0.02) for i in range(6)]
        gc_values = enc_vals + dec_vals
        gc_values = [max(0.0, min(1.0, v)) for v in gc_values]
    elif scenario == "benign":
        # Benign: normal listen pattern
        return generate_mock_gc_curve(mode="listen")
    else:
        return generate_mock_gc_curve(mode="listen")

    return {"layers": layers, "gc_values": gc_values, "n_encoder_layers": 6}


def probe(gc_curve_data: dict, tier: str = "mock") -> dict:
    """Run safety probe on a gc(k) curve dict."""
    classification = classify_gc_curve(gc_curve_data)
    label = classification.get("label", "unknown")
    confidence = classification.get("confidence", 0.0)
    features = classification.get("features", {})
    reasons = classification.get("reasons", [])

    if confidence >= 0.7:
        verdict = "JAILBREAK" if label == "jailbreak" else "BENIGN"
    elif confidence >= 0.4:
        verdict = "UNCERTAIN"
    else:
        verdict = "BENIGN"  # low confidence → safe default

    # Recommendation based on verdict
    if verdict == "JAILBREAK":
        recommendation = (
            "HIGH RISK: gc(k) decoder collapse detected. Audio likely contains "
            "adversarial prompting. Block or flag for human review."
        )
    elif verdict == "UNCERTAIN":
        recommendation = (
            "MODERATE RISK: gc(k) pattern ambiguous. Consider re-evaluating with "
            "real Whisper-tiny model (Tier 1) for higher confidence."
        )
    else:
        recommendation = "LOW RISK: Audio processing pattern appears normal (model is listening)."

    return {
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "label_raw": label,
        "gc_curve": gc_curve_data,
        "features": {k: round(v, 4) if isinstance(v, float) else v for k, v in features.items()},
        "reasons": reasons,
        "tier": tier,
        "recommendation": recommendation,
    }


def run_real_probe(audio_clean: str, audio_noisy: str, model_name: str) -> dict:
    """Tier 1: run real Whisper-tiny model to get gc(k) curve."""
    try:
        from gc_eval import run_gc_eval  # type: ignore
        result = run_gc_eval(
            model_name=model_name,
            audio_clean=audio_clean,
            audio_noisy=audio_noisy,
        )
        gc_data = {
            "layers": result.layers,
            "gc_values": result.gc_values,
            "n_encoder_layers": result.n_encoder_layers,
        }
        return probe(gc_data, tier="tier1")
    except Exception as e:
        return {"error": str(e), "verdict": "ERROR", "tier": "tier1"}


def print_summary(result: dict) -> None:
    """Print a human-readable summary."""
    verdict = result.get("verdict", "?")
    confidence = result.get("confidence", 0)
    recommendation = result.get("recommendation", "")
    reasons = result.get("reasons", [])
    features = result.get("features", {})

    icons = {"BENIGN": "✅", "JAILBREAK": "🚨", "UNCERTAIN": "⚠️", "ERROR": "❌"}
    icon = icons.get(verdict, "?")

    print(f"\n{'='*60}")
    print(f"T5 Safety Probe v1 — Result")
    print(f"{'='*60}")
    print(f"  Verdict:     {icon}  {verdict}")
    print(f"  Confidence:  {confidence:.1%}")
    print(f"  Tier:        {result.get('tier', '?')}")
    print()
    print(f"  Recommendation:")
    print(f"    {recommendation}")
    print()
    if reasons:
        print("  Evidence:")
        for r in reasons:
            print(f"    • {r}")
    if features:
        print()
        print("  Key Features:")
        for k, v in list(features.items())[:6]:
            print(f"    {k}: {v}")
    print(f"{'='*60}\n")


def run_scenario(scenario: str) -> dict:
    """Run mock probe for a specific scenario."""
    gc_data = make_mock_gc_curve(scenario)
    result = probe(gc_data, tier="mock")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="T5 Safety Probe v1 — gc(k) jailbreak detection")
    parser.add_argument("--mock", action="store_true", help="Use mock gc(k) data (no model)")
    parser.add_argument(
        "--scenario",
        choices=["benign", "jailbreak", "both"],
        default="both",
        help="Mock scenario to run (default: both)",
    )
    parser.add_argument("--audio-clean", help="Path to benign audio .wav (Tier 1)")
    parser.add_argument("--audio-noisy", help="Path to adversarial audio .wav (Tier 1)")
    parser.add_argument(
        "--model-name",
        default="openai/whisper-tiny",
        help="Whisper model name (Tier 1, default: whisper-tiny)",
    )
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    if args.mock or (not args.audio_clean and not args.audio_noisy):
        scenarios = ["benign", "jailbreak"] if args.scenario == "both" else [args.scenario]
        results = {}
        for s in scenarios:
            print(f"\n[Mock scenario: {s.upper()}]")
            r = run_scenario(s)
            if args.json:
                print(json.dumps(r, indent=2))
            else:
                print_summary(r)
            results[s] = r

        # Validation: both scenarios must produce different verdicts
        if args.scenario == "both":
            benign_verdict = results["benign"]["verdict"]
            jailbreak_verdict = results["jailbreak"]["verdict"]
            print(f"Discriminability check: benign={benign_verdict}, jailbreak={jailbreak_verdict}")
            if benign_verdict != jailbreak_verdict:
                print("✅  PASS: Probe correctly distinguishes benign vs jailbreak")
            else:
                print("⚠️   WARN: Probe gave same verdict for both scenarios (check feature extraction)")
    else:
        result = run_real_probe(args.audio_clean, args.audio_noisy, args.model_name)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print_summary(result)


if __name__ == "__main__":
    main()
