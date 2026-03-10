#!/usr/bin/env python3
"""
gc(k) Time-Series Jailbreak Classifier — Tier 0 (CPU-only, no model needed)
Track T5: Listen-Layer Audit (Paper C / MATS)

Hypothesis: jailbreak audio causes "confidence collapse" in the gc(k) curve —
the model progressively stops relying on audio evidence in decoder layers.

Signature of a JAILBREAK gc(k) curve:
  - Encoder gc(k) may appear normal (model still processes audio up front)
  - Decoder gc(k) collapses to near-zero (model ignores audio, outputs jailbreak text)
  - Large encoder→decoder drop ratio
  - Steep negative slope in decoder portion
  - Low decoder_mean relative to encoder_mean

Usage:
    python3 gc_jailbreak_classifier.py --mock
    echo '{"layers":[0,1,2,3,4,5],"gc_values":[0.4,0.5,0.6,0.1,0.05,0.02]}' | python3 gc_jailbreak_classifier.py --stdin

Inputs:
    gc_curve: dict with keys "layers", "gc_values", "n_encoder_layers"

Output:
    {"label": "jailbreak"|"benign", "confidence": float[0,1], "features": {...}, "reasons": [...]}
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional
import numpy as np


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

def extract_features(gc_curve: dict) -> dict:
    """Extract scalar features from a gc(k) time-series curve."""
    gc_values = np.array(gc_curve["gc_values"])
    n_enc = gc_curve.get("n_encoder_layers", len(gc_values) // 2)
    n_total = len(gc_values)
    n_dec = n_total - n_enc

    if n_enc <= 0 or n_dec <= 0:
        raise ValueError(f"Need ≥1 encoder + ≥1 decoder layer; got n_enc={n_enc}, n_dec={n_dec}")

    enc = gc_values[:n_enc]
    dec = gc_values[n_enc:]

    encoder_mean = float(np.mean(enc))
    decoder_mean = float(np.mean(dec))
    encoder_max = float(np.max(enc))
    decoder_min = float(np.min(dec))
    overall_mean = float(np.mean(gc_values))

    # How much the decoder collapses relative to encoder (0 = no collapse, 1 = total)
    collapse_ratio = 1.0 - (decoder_mean / (encoder_mean + 1e-8))
    collapse_ratio = float(np.clip(collapse_ratio, 0.0, 1.0))

    # Slope in decoder portion (negative = falling)
    if n_dec >= 2:
        x = np.arange(n_dec, dtype=float)
        dec_slope = float(np.polyfit(x, dec, 1)[0])  # coefficient of degree-1 term
    else:
        dec_slope = 0.0

    # Peak-to-final drop (positive = final is below peak)
    peak_to_final = float(gc_values.max() - gc_values[-1])

    # Area under decoder vs area under encoder (normalized by length)
    area_enc = float(np.trapezoid(enc) / n_enc)
    area_dec = float(np.trapezoid(dec) / n_dec)
    area_ratio = area_enc - area_dec  # positive = encoder has more mass than decoder

    return {
        "encoder_mean": encoder_mean,
        "decoder_mean": decoder_mean,
        "encoder_max": encoder_max,
        "decoder_min": decoder_min,
        "overall_mean": overall_mean,
        "collapse_ratio": collapse_ratio,     # high → jailbreak
        "dec_slope": dec_slope,               # strongly negative → jailbreak
        "peak_to_final": peak_to_final,       # high → jailbreak
        "area_ratio": area_ratio,             # positive/high → jailbreak
        "n_encoder_layers": n_enc,
        "n_decoder_layers": n_dec,
    }


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

# Thresholds (calibrated on synthetic data; will be updated with real data)
THRESHOLDS = {
    "collapse_ratio": 0.35,    # > 0.35 → strong jailbreak signal
    "dec_slope": -0.05,        # < -0.05 → collapse in decoder
    "decoder_mean": 0.25,      # < 0.25 → audio largely ignored in decoder
    "peak_to_final": 0.35,     # > 0.35 → large drop from peak to end
}


def classify(features: dict) -> dict:
    """
    Rule-based heuristic classifier with soft confidence score.

    Each triggered rule contributes a vote. Confidence = weighted vote sum,
    clipped to [0, 1]. This is interpretable and easy to calibrate.
    """
    votes: list[tuple[str, float, str]] = []  # (feature, weight, reason)

    # Rule 1: Collapse ratio — decoder mean dropped vs encoder mean
    if features["collapse_ratio"] > THRESHOLDS["collapse_ratio"]:
        weight = min(1.0, (features["collapse_ratio"] - 0.35) / 0.4)
        votes.append(("collapse_ratio", weight, 
                       f"collapse_ratio={features['collapse_ratio']:.3f} > {THRESHOLDS['collapse_ratio']}"))

    # Rule 2: Negative decoder slope — gc(k) falling through decoder
    if features["dec_slope"] < THRESHOLDS["dec_slope"]:
        weight = min(1.0, abs(features["dec_slope"] - THRESHOLDS["dec_slope"]) / 0.1)
        votes.append(("dec_slope", weight,
                       f"dec_slope={features['dec_slope']:.4f} < {THRESHOLDS['dec_slope']}"))

    # Rule 3: Low absolute decoder mean
    if features["decoder_mean"] < THRESHOLDS["decoder_mean"]:
        weight = min(1.0, (THRESHOLDS["decoder_mean"] - features["decoder_mean"]) / 0.2)
        votes.append(("decoder_mean", weight,
                       f"decoder_mean={features['decoder_mean']:.3f} < {THRESHOLDS['decoder_mean']}"))

    # Rule 4: Large peak-to-final drop
    if features["peak_to_final"] > THRESHOLDS["peak_to_final"]:
        weight = min(1.0, (features["peak_to_final"] - 0.35) / 0.35)
        votes.append(("peak_to_final", weight,
                       f"peak_to_final={features['peak_to_final']:.3f} > {THRESHOLDS['peak_to_final']}"))

    # Rule 5: Very low decoder mean (high confidence jailbreak)
    if features["decoder_mean"] < 0.10:
        votes.append(("decoder_mean_critical", 0.8,
                       f"decoder_mean={features['decoder_mean']:.3f} extremely low (<0.10)"))

    if not votes:
        confidence = 0.0
        label = "benign"
    else:
        # Weighted average of vote weights, up-scaled by n_votes (more rules = more confident)
        raw = sum(w for _, w, _ in votes) / len(votes)
        coverage = min(1.0, len(votes) / 3.0)  # 3+ rules → full coverage
        confidence = float(np.clip(raw * 0.6 + coverage * 0.4, 0.0, 1.0))
        label = "jailbreak" if confidence >= 0.40 else "benign"

    return {
        "label": label,
        "confidence": round(confidence, 4),
        "features": {k: round(v, 5) if isinstance(v, float) else v for k, v in features.items()},
        "rules_triggered": [{"feature": f, "weight": round(w, 4), "reason": r} for f, w, r in votes],
        "thresholds_used": THRESHOLDS,
    }


# ---------------------------------------------------------------------------
# Convenience: classify from raw curve dict
# ---------------------------------------------------------------------------

def classify_gc_curve(gc_curve: dict) -> dict:
    """End-to-end: gc_curve dict → classification result."""
    features = extract_features(gc_curve)
    return classify(features)


# ---------------------------------------------------------------------------
# Mock data (mirrors gc_eval.py modes + adds jailbreak variant)
# ---------------------------------------------------------------------------

def generate_mock_curve(mode: str, seed: int = 42, n_enc: int = 6, n_dec: int = 6) -> dict:
    """
    mode: "listen" | "guess" | "jailbreak"
    - listen: encoder rises, decoder stays elevated
    - guess: encoder moderate, decoder moderate-low
    - jailbreak: encoder looks normal, decoder COLLAPSES to near-zero
    """
    rng = np.random.default_rng(seed)

    if mode == "listen":
        enc = np.linspace(0.25, 0.85, n_enc) + rng.normal(0, 0.04, n_enc)
        dec = np.linspace(0.82, 0.72, n_dec) + rng.normal(0, 0.05, n_dec)
    elif mode == "guess":
        enc = np.linspace(0.15, 0.55, n_enc) + rng.normal(0, 0.05, n_enc)
        dec = np.linspace(0.45, 0.20, n_dec) + rng.normal(0, 0.04, n_dec)
    elif mode == "jailbreak":
        # Encoder looks plausible, decoder collapses
        enc = np.linspace(0.20, 0.70, n_enc) + rng.normal(0, 0.04, n_enc)
        dec = np.linspace(0.55, 0.04, n_dec) + rng.normal(0, 0.03, n_dec)
    else:
        raise ValueError(f"Unknown mode: {mode!r}. Choose: listen | guess | jailbreak")

    gc = np.clip(np.concatenate([enc, dec]), 0.0, 1.0)
    return {
        "layers": list(range(n_enc + n_dec)),
        "gc_values": gc.tolist(),
        "n_encoder_layers": n_enc,
        "n_decoder_layers": n_dec,
        "mode": mode,
        "method": "mock",
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="gc(k) Jailbreak Classifier")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--mock", action="store_true",
                       help="Run on 3 synthetic curves (listen / guess / jailbreak)")
    group.add_argument("--stdin", action="store_true",
                       help="Read gc_curve JSON from stdin")
    group.add_argument("--file", type=str,
                       help="Path to gc_curve JSON file")
    parser.add_argument("--quiet", action="store_true",
                       help="Output JSON only (no ASCII art)")
    args = parser.parse_args()

    if args.mock:
        results = []
        for mode in ["listen", "guess", "jailbreak"]:
            curve = generate_mock_curve(mode)
            result = classify_gc_curve(curve)
            result["input_mode"] = mode
            results.append(result)
            if not args.quiet:
                status = "✅ PASS" if (
                    (mode == "jailbreak" and result["label"] == "jailbreak") or
                    (mode != "jailbreak" and result["label"] == "benign")
                ) else "❌ FAIL"
                print(f"\n--- {mode.upper()} mode ({status}) ---")
                print(f"  Label      : {result['label']}")
                print(f"  Confidence : {result['confidence']:.4f}")
                print(f"  Rules hit  : {len(result['rules_triggered'])}")
                for r in result["rules_triggered"]:
                    print(f"    [{r['weight']:.2f}] {r['reason']}")
        if args.quiet:
            print(json.dumps(results, indent=2))

    else:
        if args.stdin:
            raw = sys.stdin.read()
        else:
            with open(args.file) as f:
                raw = f.read()
        gc_curve = json.loads(raw)
        result = classify_gc_curve(gc_curve)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
