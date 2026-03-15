#!/usr/bin/env python3
"""
Online ΔGS Streaming Monitor — per-utterance SAE feature drift via WhisperHookedEncoder
Track T3, Q079 | Real-time audio grounding anomaly detection

RESEARCH QUESTION
-----------------
Can we detect audio grounding failures *online* (utterance-by-utterance) by
monitoring SAE feature drift (ΔGS) across a sliding window of recent inputs?

MOTIVATION
----------
gc(k) analysis is post-hoc (requires a baseline batch). For streaming/deployment
use-cases, we need an *online* anomaly detector that fires when the model's
listen-layer activations shift significantly from recent history.

Key idea: if the model is "guessing" (low gc) rather than listening, its SAE
feature activations will drift from a stable benign baseline. A sliding window
ΔGS monitor can catch this in real time without needing ground-truth transcripts.

METHOD
------
1. Maintain a sliding window W of the last N utterances' listen-layer activations
2. For each new utterance u_t:
   a. Encode u_t → listen-layer activation vector a_t (via WhisperHookedEncoder mock)
   b. Decode a_t through mock SAE → sparse feature vector f_t
   c. Compute ΔGS(t) = Cohen's d between f_t and the window's running stats
   d. Update window: evict oldest, add f_t
   e. Anomaly flag if ΔGS(t) > threshold τ

ARCHITECTURE
------------
  WhisperHookedEncoder (mock)
    └─ listen_layer_activation(audio_id) → activation vector
  MicroSAE
    └─ encode(activation) → sparse feature vector
  SlidingWindowMonitor
    └─ push(feature_vec) → ΔGS score, anomaly flag

TIER
----
Tier 0: numpy-only, no torch/GPU, ~200 lines. CPU < 1s.

USAGE
-----
  python3 online_delta_gs_monitor.py               # stream 20 utterances (2 injected anomalies)
  python3 online_delta_gs_monitor.py --test        # unit tests
  python3 online_delta_gs_monitor.py --json        # JSON output
  python3 online_delta_gs_monitor.py --window 5 --threshold 1.5  # custom params

DEFINITION OF DONE (Q079)
-------------------------
Script uses WhisperHookedEncoder to compute deltaGS on 10-utterance sliding window;
anomaly flag when drift > threshold. ✓

Author: Little Leo (Lab) — 2026-03-15
Track: T3, Q079, converge
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# WhisperHookedEncoder (mock)
# ---------------------------------------------------------------------------

class WhisperHookedEncoder:
    """
    Mock Whisper encoder that returns listen-layer activations.
    In production this wraps transformer_lens or nnsight to hook the
    actual listen layer (the gc(k) peak layer identified by gc_eval.py).

    Mock behaviour:
    - Benign audio → activations sampled from N(0, 1)
    - Adversarial / noisy audio → activations sampled from N(δ, 1)
    """

    LISTEN_LAYER: int = 3  # placeholder; real value from gc_eval.py argmax

    def __init__(self, d_model: int = 16, seed: int = 42):
        self.d_model = d_model
        self.rng = np.random.RandomState(seed)

    def encode_listen_layer(
        self, audio_id: int, adversarial_shift: float = 0.0
    ) -> np.ndarray:
        """
        Return listen-layer activation for a single utterance.

        Parameters
        ----------
        audio_id : int
            Unique ID for this utterance (used to seed the activation).
        adversarial_shift : float
            If > 0, inject a distributional shift to simulate adversarial input.
            This is the μ parameter of N(μ, 1) that the activation is drawn from.
        """
        rng = np.random.RandomState(audio_id + 1000)
        activation = rng.randn(self.d_model) + adversarial_shift
        return activation.astype(np.float32)


# ---------------------------------------------------------------------------
# MicroSAE (sparse autoencoder, mock)
# ---------------------------------------------------------------------------

class MicroSAE:
    """
    Minimal sparse autoencoder that maps listen-layer activations to sparse
    feature vectors. Mimics TopK-SAE used in saelens_audio experiments.

    In production: load actual SAE weights trained on Whisper listen-layer.
    """

    def __init__(
        self,
        d_input: int = 16,
        n_features: int = 32,
        top_k: int = 8,
        seed: int = 7,
    ):
        rng = np.random.RandomState(seed)
        self.W_enc = rng.randn(n_features, d_input).astype(np.float32)  # (F, D)
        self.W_enc /= np.linalg.norm(self.W_enc, axis=1, keepdims=True) + 1e-8
        self.n_features = n_features
        self.top_k = top_k

    def encode(self, activation: np.ndarray) -> np.ndarray:
        """Map activation → sparse feature vector (TopK ReLU)."""
        pre_acts = self.W_enc @ activation  # (F,)
        feature_vec = np.zeros(self.n_features, dtype=np.float32)
        top_indices = np.argsort(pre_acts)[-self.top_k :]
        feature_vec[top_indices] = np.maximum(0.0, pre_acts[top_indices])
        return feature_vec


# ---------------------------------------------------------------------------
# Sliding Window ΔGS Monitor
# ---------------------------------------------------------------------------

@dataclass
class UtteranceRecord:
    utterance_id: int
    feature_vec: np.ndarray
    delta_gs: float
    anomaly: bool
    label: str  # "benign" / "adversarial" (ground-truth for mock evaluation)


class SlidingWindowMonitor:
    """
    Maintains a sliding window of SAE feature vectors and computes per-utterance
    ΔGS (Cohen's d between the new utterance and the window distribution).

    Algorithm
    ---------
    Running stats (mean, variance) maintained with Welford's online algorithm.
    On each push:
      1. Compute Cohen's d: (f_t - window_mean) / (window_std + eps), L2-norm.
      2. If ΔGS > τ → anomaly flag.
      3. Update window (evict oldest, add new).

    Warm-up period: first min_window frames are used to build baseline (no anomaly
    flags during this period).
    """

    def __init__(
        self,
        window_size: int = 10,
        threshold: float = 2.0,
        min_window: int = 5,
    ):
        self.window_size = window_size
        self.threshold = threshold
        self.min_window = min_window
        self._window: List[np.ndarray] = []

    # ------------------------------------------------------------------
    # Welford running stats helpers
    # ------------------------------------------------------------------

    def _window_stats(self) -> Tuple[np.ndarray, np.ndarray]:
        """Return (mean, std) of current window features."""
        mat = np.stack(self._window, axis=0)  # (N, F)
        mean = mat.mean(axis=0)
        std = mat.std(axis=0)
        return mean, std

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def push(
        self, utterance_id: int, feature_vec: np.ndarray, label: str = "benign"
    ) -> UtteranceRecord:
        """
        Push a new utterance feature vector into the monitor.

        Returns an UtteranceRecord with ΔGS and anomaly flag.
        During warm-up (< min_window samples), ΔGS = 0.0, anomaly = False.
        """
        # Warm-up: no stats yet
        if len(self._window) < self.min_window:
            self._window.append(feature_vec)
            record = UtteranceRecord(
                utterance_id=utterance_id,
                feature_vec=feature_vec,
                delta_gs=0.0,
                anomaly=False,
                label=label,
            )
            return record

        # Compute ΔGS
        mean, std = self._window_stats()
        eps = 1e-6
        cohens_d_per_feature = (feature_vec - mean) / (std + eps)  # (F,)
        delta_gs = float(np.linalg.norm(cohens_d_per_feature) / len(feature_vec) ** 0.5)

        anomaly = delta_gs > self.threshold

        # Update window (sliding: evict oldest)
        self._window.append(feature_vec)
        if len(self._window) > self.window_size:
            self._window.pop(0)

        record = UtteranceRecord(
            utterance_id=utterance_id,
            feature_vec=feature_vec,
            delta_gs=delta_gs,
            anomaly=anomaly,
            label=label,
        )
        return record


# ---------------------------------------------------------------------------
# Stream simulation
# ---------------------------------------------------------------------------

def simulate_stream(
    n_utterances: int = 20,
    window_size: int = 10,
    threshold: float = 2.0,
    adversarial_indices: Optional[List[int]] = None,
    adversarial_shift: float = 3.0,
    seed: int = 0,
) -> List[UtteranceRecord]:
    """
    Simulate a stream of n_utterances, with optional adversarial injections.

    Parameters
    ----------
    adversarial_indices : list of int, optional
        Utterance IDs to inject adversarial shift. Default: [12, 13].
    adversarial_shift : float
        Magnitude of distributional shift for adversarial utterances.
    """
    if adversarial_indices is None:
        adversarial_indices = [12, 13]

    encoder = WhisperHookedEncoder(d_model=16, seed=seed)
    sae = MicroSAE(d_input=16, n_features=32, top_k=8, seed=seed + 1)
    monitor = SlidingWindowMonitor(
        window_size=window_size, threshold=threshold, min_window=5
    )

    records: List[UtteranceRecord] = []
    for i in range(n_utterances):
        is_adv = i in adversarial_indices
        shift = adversarial_shift if is_adv else 0.0
        label = "adversarial" if is_adv else "benign"
        activation = encoder.encode_listen_layer(audio_id=i, adversarial_shift=shift)
        features = sae.encode(activation)
        record = monitor.push(utterance_id=i, feature_vec=features, label=label)
        records.append(record)

    return records


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------

def evaluate_records(records: List[UtteranceRecord]) -> dict:
    """Compute precision/recall/F1 for anomaly detection vs ground-truth labels."""
    tp = fp = fn = tn = 0
    for r in records:
        gt_pos = r.label == "adversarial"
        if gt_pos and r.anomaly:
            tp += 1
        elif not gt_pos and r.anomaly:
            fp += 1
        elif gt_pos and not r.anomaly:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
    }


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def run_tests() -> bool:
    """Run unit tests. Returns True if all pass."""
    passed = 0
    failed = 0

    def check(name: str, condition: bool):
        nonlocal passed, failed
        if condition:
            print(f"  ✓ {name}")
            passed += 1
        else:
            print(f"  ✗ {name}")
            failed += 1

    print("── Unit Tests ──")

    # Test 1: WhisperHookedEncoder returns correct shape
    enc = WhisperHookedEncoder(d_model=16)
    act = enc.encode_listen_layer(audio_id=0)
    check("Encoder output shape matches d_model", act.shape == (16,))

    # Test 2: Adversarial shift raises mean
    act_benign = enc.encode_listen_layer(audio_id=1, adversarial_shift=0.0)
    act_adv = enc.encode_listen_layer(audio_id=1, adversarial_shift=5.0)
    check("Adversarial shift increases mean activation", act_adv.mean() > act_benign.mean())

    # Test 3: SAE output is sparse
    sae = MicroSAE(d_input=16, n_features=32, top_k=8)
    feat = sae.encode(act_benign)
    nonzero = np.count_nonzero(feat)
    check(f"SAE TopK sparsity (nonzero={nonzero} ≤ top_k=8)", nonzero <= 8)
    check("SAE output shape matches n_features", feat.shape == (32,))

    # Test 4: Monitor warm-up produces no anomaly flags
    monitor = SlidingWindowMonitor(window_size=10, threshold=2.0, min_window=5)
    warmup_records = []
    for i in range(5):
        fv = np.zeros(32)
        fv[i] = 1.0
        rec = monitor.push(i, fv)
        warmup_records.append(rec)
    check("Warm-up period: no anomaly flags", not any(r.anomaly for r in warmup_records))
    check("Warm-up delta_gs = 0.0", all(r.delta_gs == 0.0 for r in warmup_records))

    # Test 5: Anomaly detection fires on large shift
    # Add 5 benign frames (already done above), then inject a huge-shift adversarial
    huge_shift_vec = np.ones(32) * 100.0  # far from baseline
    rec_adv = monitor.push(999, huge_shift_vec, label="adversarial")
    check("Anomaly flag fires on large distributional shift", rec_adv.anomaly)
    check("ΔGS > threshold on large shift", rec_adv.delta_gs > 2.0)

    # Test 6: Window size cap (sliding eviction)
    monitor2 = SlidingWindowMonitor(window_size=3, threshold=5.0, min_window=2)
    for i in range(10):
        monitor2.push(i, np.random.randn(32))
    check("Sliding window capped at window_size", len(monitor2._window) <= 3)

    # Test 7: Full stream simulation
    records = simulate_stream(
        n_utterances=20, window_size=10, threshold=2.0,
        adversarial_indices=[12, 13], adversarial_shift=4.0
    )
    check("Simulation produces 20 records", len(records) == 20)
    adv_records = [r for r in records if r.label == "adversarial"]
    detected = [r for r in adv_records if r.anomaly]
    check(f"At least one adversarial detected ({len(detected)}/{len(adv_records)})", len(detected) >= 1)

    # Test 8: Evaluate function
    metrics = evaluate_records(records)
    check("Recall > 0 for adversarial detection", metrics["recall"] > 0.0)
    check("Precision defined (no division by zero)", "precision" in metrics)

    print(f"\nResults: {passed}/{passed+failed} passed")
    return failed == 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Online ΔGS Streaming Monitor (Q079)")
    parser.add_argument("--test", action="store_true", help="Run unit tests")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--n", type=int, default=20, help="Number of utterances to simulate")
    parser.add_argument("--window", type=int, default=10, help="Sliding window size")
    parser.add_argument("--threshold", type=float, default=2.0, help="ΔGS anomaly threshold τ")
    parser.add_argument("--shift", type=float, default=4.0, help="Adversarial shift magnitude")
    parser.add_argument("--adversarial", type=int, nargs="+", default=[12, 13],
                        help="Utterance indices to inject adversarial shift")
    args = parser.parse_args()

    if args.test:
        ok = run_tests()
        sys.exit(0 if ok else 1)

    # Run stream simulation
    records = simulate_stream(
        n_utterances=args.n,
        window_size=args.window,
        threshold=args.threshold,
        adversarial_indices=args.adversarial,
        adversarial_shift=args.shift,
    )
    metrics = evaluate_records(records)

    if args.json:
        output = {
            "config": {
                "n_utterances": args.n,
                "window_size": args.window,
                "threshold": args.threshold,
                "adversarial_shift": args.shift,
                "adversarial_indices": args.adversarial,
            },
            "records": [
                {
                    "id": r.utterance_id,
                    "delta_gs": round(r.delta_gs, 4),
                    "anomaly": r.anomaly,
                    "label": r.label,
                }
                for r in records
            ],
            "metrics": metrics,
        }
        print(json.dumps(output, indent=2))
        return

    # Human-readable output
    print("=" * 60)
    print("Online ΔGS Streaming Monitor — Q079")
    print(f"Window={args.window} | Threshold τ={args.threshold} | Shift={args.shift}")
    print("=" * 60)
    print(f"{'Utt':>4}  {'Label':>12}  {'ΔGS':>8}  {'Anomaly':>8}")
    print("-" * 40)
    for r in records:
        flag = "🚨 ALERT" if r.anomaly else ""
        warmup = "(warmup)" if r.delta_gs == 0.0 and not r.anomaly else ""
        label_tag = "⚠ ADV" if r.label == "adversarial" else "     "
        print(
            f"{r.utterance_id:>4}  {label_tag:>12}  {r.delta_gs:>8.4f}  {flag}{warmup}"
        )

    print("\n── Evaluation Metrics ──")
    print(f"  TP={metrics['tp']}  FP={metrics['fp']}  FN={metrics['fn']}  TN={metrics['tn']}")
    print(f"  Precision: {metrics['precision']:.3f}")
    print(f"  Recall:    {metrics['recall']:.3f}")
    print(f"  F1:        {metrics['f1']:.3f}")
    print()
    print("── Architecture Summary ──")
    print("  WhisperHookedEncoder.encode_listen_layer(audio_id) → activation (d=16)")
    print("  MicroSAE.encode(activation) → sparse feature vec (F=32, k=8)")
    print("  SlidingWindowMonitor.push(feature_vec) → ΔGS score + anomaly flag")
    print()
    print("── Connection to Research Tracks ──")
    print("  T3: ΔGS monitors gc(k) proxy in streaming context")
    print("  T5: Anomaly flag = candidate jailbreak detection signal")
    print("  Next: Extend to use real WhisperHookedEncoder (nnsight/transformer_lens)")
    print("        Calibrate τ on known-benign distribution (percentile threshold)")


if __name__ == "__main__":
    main()
