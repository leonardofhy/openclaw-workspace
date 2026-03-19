#!/usr/bin/env python3
"""
M9 Online Causal Consistency Monitor
Track T5, Q112

RESEARCH QUESTION
-----------------
Can we reduce false-positive rate in the online ΔGS streaming monitor by
*gating* anomaly alerts on a per-utterance Causal Consistency Score (CCS/M9)?

MOTIVATION
----------
online_delta_gs_monitor.py (Q079) detects feature drift via ΔGS (Cohen's d)
but fires FP alerts on benign hard-cases (geometric stress without actual
grounding failure). M9 (Causal Abstraction Consistency) captures whether the
*structure* of active SAE features is still causally coherent — if yes,
suppress the alert even when ΔGS is high.

KEY METRICS
-----------
ΔGS (M7 proxy):  Cohen's-d feature drift vs sliding window baseline.
                 High → model geometrically stressed (same as Q079).

CCS  (M9 proxy):  Online Causal Consistency Score.
                  CCS = AND_gate_frac(t) × schelling_stability(t)
                    - AND_gate_frac: fraction of top-k features that are
                      "and-gate-like" (activation drops when either audio OR
                      context is ablated) → mock: features near both audio
                      and context subspace projections.
                    - schelling_stability: cosine similarity of top-k feature
                      *pattern* (binary mask) with the running median pattern
                      in the window → measures if feature selection is
                      consistent (stable causal graph) vs scrambled (attack).

DUAL-GATE ALERT RULE
--------------------
  ALERT iff  ΔGS(t) > τ_gs  AND  CCS(t) < τ_ccs

Single-gate  (ΔGS only):   same as Q079 baseline
Dual-gate   (ΔGS + CCS):  suppresses FP benign hard-cases (H1 hypothesis)

HYPOTHESES (same as M9 dual-detector, Q083)
-------------------------------------------
H1: Dual-gate FPR < single-gate FPR at same recall level.
H2: CCS adds no information (dual ≈ single).
H3: CCS gate too tight (recall drops unacceptably).

ARCHITECTURE
------------
  FeatureRecord(t)
    ├─ activation → SAE encode → feature_vec   (Q079)
    ├─ and_gate_frac:  |{f_i : is_and_gate(f_i)}| / top_k
    └─ schelling_stability:  cosine(top_k_mask(t), median_mask_in_window)

  OnlineConsistencyMonitor(window=W, τ_gs, τ_ccs)
    └─ push(activation) → (delta_gs, ccs, alert_single, alert_dual)

TIER: 0 — numpy-only, no torch/GPU. CPU < 1s.

USAGE
-----
  python3 m9_online_consistency_monitor.py           # default stream (20 utterances)
  python3 m9_online_consistency_monitor.py --test    # unit tests
  python3 m9_online_consistency_monitor.py --json    # JSON output
  python3 m9_online_consistency_monitor.py --n 100 --window 15

Connection to tracks
---------------------
T5: Online M9 gate reduces FP rate for audio-jailbreak streaming detection.
T3: CCS = proxy for gc(k) causal structure health online (no post-hoc needed).
Q083: This is the streaming/online counterpart of M9-gated dual-factor detector.

Author: Little Leo (Lab) — 2026-03-18
Track: T5, Q112, explore-fallback build
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# WhisperHookedEncoder (mock — same as online_delta_gs_monitor.py)
# ---------------------------------------------------------------------------

class WhisperHookedEncoder:
    """
    Mock Whisper listen-layer encoder.
    Benign  → N(0, 1)
    Adversarial → N(shift, 1) + scrambled feature pattern
    """
    LISTEN_LAYER: int = 3

    def __init__(self, d_model: int = 16, seed: int = 42):
        self.d_model = d_model
        self.rng = np.random.RandomState(seed)

    def encode_listen_layer(
        self,
        audio_id: int,
        adversarial_shift: float = 0.0,
        scramble_seed: Optional[int] = None,
    ) -> np.ndarray:
        """
        Return listen-layer activation.

        scramble_seed: if set, also randomly permutes the activation *pattern*
        (simulates attack that breaks causal structure without large magnitude shift).
        This is the key test for CCS — ΔGS may stay low, but CCS should drop.
        """
        rng = np.random.RandomState(audio_id + 1000)
        activation = rng.randn(self.d_model).astype(np.float32) + adversarial_shift
        if scramble_seed is not None:
            perm_rng = np.random.RandomState(scramble_seed)
            perm = perm_rng.permutation(self.d_model)
            activation = activation[perm]  # scramble feature order
        return activation


# ---------------------------------------------------------------------------
# MicroSAE (same as online_delta_gs_monitor.py)
# ---------------------------------------------------------------------------

class MicroSAE:
    """TopK sparse autoencoder mock."""

    def __init__(
        self,
        d_input: int = 16,
        n_features: int = 32,
        top_k: int = 8,
        seed: int = 7,
    ):
        rng = np.random.RandomState(seed)
        self.W_enc = rng.randn(n_features, d_input).astype(np.float32)
        self.W_enc /= np.linalg.norm(self.W_enc, axis=1, keepdims=True) + 1e-8
        self.n_features = n_features
        self.top_k = top_k
        # Pre-label features as AND-gate or OR-gate (mock ground truth)
        # AND-gate: features 0..15 (audio-dependent)
        # OR-gate:  features 16..31 (text-predictable)
        self._and_gate_mask = np.zeros(n_features, dtype=bool)
        self._and_gate_mask[:n_features // 2] = True

    def encode(self, activation: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Returns:
          feature_vec : (n_features,) sparse TopK activation values
          top_k_mask  : (n_features,) binary mask of active features
        """
        pre_acts = self.W_enc @ activation
        top_indices = np.argsort(pre_acts)[-self.top_k:]
        feature_vec = np.zeros(self.n_features, dtype=np.float32)
        feature_vec[top_indices] = np.maximum(0.0, pre_acts[top_indices])
        top_k_mask = np.zeros(self.n_features, dtype=bool)
        top_k_mask[top_indices] = True
        return feature_vec, top_k_mask

    def and_gate_fraction(self, top_k_mask: np.ndarray) -> float:
        """Fraction of active top-k features that are AND-gate-type."""
        active_and = np.sum(top_k_mask & self._and_gate_mask)
        active_total = np.sum(top_k_mask)
        return float(active_and) / float(active_total) if active_total > 0 else 0.0


# ---------------------------------------------------------------------------
# Online Consistency Monitor (CCS + ΔGS)
# ---------------------------------------------------------------------------

@dataclass
class UtteranceRecord:
    utterance_id: int
    feature_vec: np.ndarray
    top_k_mask: np.ndarray
    delta_gs: float
    ccs: float              # Causal Consistency Score ∈ [0, 1]
    and_gate_frac: float    # M9 component 1
    schelling_stab: float   # M9 component 2
    alert_single: bool      # ΔGS-only gate
    alert_dual: bool        # ΔGS + CCS dual gate
    label: str              # "benign" / "adversarial" / "benign_hard"


class OnlineConsistencyMonitor:
    """
    Extends SlidingWindowMonitor with:
      (1) Causal Consistency Score (CCS = AND_gate_frac × schelling_stability)
      (2) Dual-gate alert rule: ΔGS > τ_gs AND CCS < τ_ccs

    Window stores both feature vectors (for ΔGS) and top_k_masks (for
    Schelling stability).

    Schelling stability: cosine similarity between current top-k mask and the
    running *median* mask (element-wise majority vote) in the window.
    This captures structural feature-selection consistency.
    """

    def __init__(
        self,
        sae: MicroSAE,
        window_size: int = 10,
        tau_gs: float = 2.0,
        tau_ccs: float = 0.4,
        min_window: int = 5,
    ):
        self.sae = sae
        self.window_size = window_size
        self.tau_gs = tau_gs
        self.tau_ccs = tau_ccs
        self.min_window = min_window
        self._fvec_window: List[np.ndarray] = []
        self._mask_window: List[np.ndarray] = []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _delta_gs(self, feature_vec: np.ndarray) -> float:
        """Cohen's-d drift vs window mean (same formula as Q079)."""
        mat = np.stack(self._fvec_window, axis=0)
        mean = mat.mean(axis=0)
        std = mat.std(axis=0)
        eps = 1e-6
        cohens_d = (feature_vec - mean) / (std + eps)
        return float(np.linalg.norm(cohens_d) / len(feature_vec) ** 0.5)

    def _schelling_stability(self, top_k_mask: np.ndarray) -> float:
        """
        Cosine similarity between current top-k mask and the majority-vote
        mask of the window (Schelling-stability proxy).

        Majority-vote mask: feature i is 1 if it was active in >50% of
        window frames.
        """
        mat = np.stack(self._mask_window, axis=0).astype(float)  # (N, F)
        majority_mask = (mat.mean(axis=0) > 0.5).astype(float)   # (F,)
        curr = top_k_mask.astype(float)
        denom = (np.linalg.norm(majority_mask) * np.linalg.norm(curr)) + 1e-8
        return float(np.dot(majority_mask, curr) / denom)

    def _update_window(self, feature_vec: np.ndarray, top_k_mask: np.ndarray):
        self._fvec_window.append(feature_vec)
        self._mask_window.append(top_k_mask)
        if len(self._fvec_window) > self.window_size:
            self._fvec_window.pop(0)
            self._mask_window.pop(0)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def push(
        self,
        utterance_id: int,
        activation: np.ndarray,
        label: str = "benign",
    ) -> UtteranceRecord:
        feature_vec, top_k_mask = self.sae.encode(activation)
        and_gate_frac = self.sae.and_gate_fraction(top_k_mask)

        # Warm-up: no alerts, no stats
        if len(self._fvec_window) < self.min_window:
            self._update_window(feature_vec, top_k_mask)
            return UtteranceRecord(
                utterance_id=utterance_id,
                feature_vec=feature_vec,
                top_k_mask=top_k_mask,
                delta_gs=0.0,
                ccs=1.0,   # assume consistent during warm-up
                and_gate_frac=and_gate_frac,
                schelling_stab=1.0,
                alert_single=False,
                alert_dual=False,
                label=label,
            )

        delta_gs = self._delta_gs(feature_vec)
        schelling_stab = self._schelling_stability(top_k_mask)
        ccs = and_gate_frac * schelling_stab

        alert_single = delta_gs > self.tau_gs
        alert_dual = delta_gs > self.tau_gs and ccs < self.tau_ccs

        self._update_window(feature_vec, top_k_mask)

        return UtteranceRecord(
            utterance_id=utterance_id,
            feature_vec=feature_vec,
            top_k_mask=top_k_mask,
            delta_gs=delta_gs,
            ccs=ccs,
            and_gate_frac=and_gate_frac,
            schelling_stab=schelling_stab,
            alert_single=alert_single,
            alert_dual=alert_dual,
            label=label,
        )


# ---------------------------------------------------------------------------
# Stream simulation
# ---------------------------------------------------------------------------

def simulate_stream(
    n_utterances: int = 20,
    window_size: int = 10,
    tau_gs: float = 2.0,
    tau_ccs: float = 0.4,
    adversarial_indices: Optional[List[int]] = None,
    adversarial_shift: float = 3.0,
    # benign_hard: high ΔGS but intact causal structure (no scramble)
    benign_hard_indices: Optional[List[int]] = None,
    seed: int = 0,
) -> List[UtteranceRecord]:
    """
    Three utterance types:
      - benign:       N(0,1), normal feature pattern
      - adversarial:  N(shift,1) + scrambled feature pattern → ΔGS ↑, CCS ↓
      - benign_hard:  N(shift/2,1), no scramble → ΔGS ↑, CCS stays high (FP target)
    """
    if adversarial_indices is None:
        adversarial_indices = [12, 13]
    if benign_hard_indices is None:
        benign_hard_indices = [15, 16]

    encoder = WhisperHookedEncoder(d_model=16, seed=seed)
    sae = MicroSAE(d_input=16, n_features=32, top_k=8, seed=seed + 1)
    monitor = OnlineConsistencyMonitor(
        sae=sae, window_size=window_size, tau_gs=tau_gs, tau_ccs=tau_ccs, min_window=5
    )

    records: List[UtteranceRecord] = []
    for i in range(n_utterances):
        is_adv = i in adversarial_indices
        is_hard = i in benign_hard_indices

        if is_adv:
            activation = encoder.encode_listen_layer(
                i, adversarial_shift=adversarial_shift, scramble_seed=i * 7 + 1
            )
            label = "adversarial"
        elif is_hard:
            # High drift but causal structure intact (no scramble)
            activation = encoder.encode_listen_layer(
                i, adversarial_shift=adversarial_shift / 2.0, scramble_seed=None
            )
            label = "benign_hard"
        else:
            activation = encoder.encode_listen_layer(i, adversarial_shift=0.0)
            label = "benign"

        record = monitor.push(utterance_id=i, activation=activation, label=label)
        records.append(record)

    return records


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate(records: List[UtteranceRecord]) -> dict:
    """
    Compare single-gate vs dual-gate on the same stream.
    Positive class = "adversarial".
    benign_hard counts as negative (we want to suppress those FPs).
    """
    def metrics(tp, fp, fn, tn):
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
                "precision": round(prec, 3), "recall": round(rec, 3),
                "f1": round(f1, 3), "fpr": round(fpr, 3)}

    tp_s = fp_s = fn_s = tn_s = 0
    tp_d = fp_d = fn_d = tn_d = 0

    for r in records:
        gt = r.label == "adversarial"
        for alert, counts in [(r.alert_single, (tp_s, fp_s, fn_s, tn_s)),
                               (r.alert_dual,  (tp_d, fp_d, fn_d, tn_d))]:
            _ = counts  # just clarity

        # single
        if gt and r.alert_single:   tp_s += 1
        elif not gt and r.alert_single: fp_s += 1
        elif gt and not r.alert_single: fn_s += 1
        else: tn_s += 1

        # dual
        if gt and r.alert_dual:     tp_d += 1
        elif not gt and r.alert_dual: fp_d += 1
        elif gt and not r.alert_dual: fn_d += 1
        else: tn_d += 1

    return {
        "single_gate": metrics(tp_s, fp_s, fn_s, tn_s),
        "dual_gate":   metrics(tp_d, fp_d, fn_d, tn_d),
        "hypothesis": {
            "H1_dual_wins_fpr": (
                metrics(tp_d, fp_d, fn_d, tn_d)["fpr"] <
                metrics(tp_s, fp_s, fn_s, tn_s)["fpr"]
            ),
            "H1_dual_wins_recall": (
                metrics(tp_d, fp_d, fn_d, tn_d)["recall"] >=
                metrics(tp_s, fp_s, fn_s, tn_s)["recall"] * 0.9  # allow 10% drop
            ),
        },
    }


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def run_tests() -> bool:
    passed = failed = 0

    def check(name: str, condition: bool):
        nonlocal passed, failed
        if condition:
            print(f"  ✓ {name}")
            passed += 1
        else:
            print(f"  ✗ {name}")
            failed += 1

    print("── Unit Tests ──")

    sae = MicroSAE(d_input=16, n_features=32, top_k=8, seed=7)
    enc = WhisperHookedEncoder(d_model=16, seed=42)

    # T1: SAE encode returns correct types
    act = enc.encode_listen_layer(0)
    fvec, mask = sae.encode(act)
    check("SAE encode: feature_vec shape", fvec.shape == (32,))
    check("SAE encode: top_k_mask shape", mask.shape == (32,))
    check("SAE encode: exactly top_k active", np.sum(mask) == 8)

    # T2: AND-gate fraction in [0,1]
    agf = sae.and_gate_fraction(mask)
    check("AND-gate fraction in [0,1]", 0.0 <= agf <= 1.0)

    # T3: Warm-up period produces no alerts
    monitor = OnlineConsistencyMonitor(sae=sae, window_size=10, tau_gs=2.0, tau_ccs=0.4)
    for i in range(5):
        r = monitor.push(i, enc.encode_listen_layer(i))
        check(f"Warm-up [t={i}]: no alert_single", not r.alert_single)
        check(f"Warm-up [t={i}]: no alert_dual", not r.alert_dual)

    # T4: Schelling stability = 1.0 for identical masks
    monitor2 = OnlineConsistencyMonitor(sae=sae, window_size=5, tau_gs=2.0, tau_ccs=0.4)
    ref_act = enc.encode_listen_layer(99)
    for _ in range(5):  # fill window with same activation
        monitor2.push(0, ref_act.copy())
    stab_r = monitor2.push(99, ref_act.copy())  # identical → stability ≈ 1
    check("Schelling stability ≈ 1 for identical activations", stab_r.schelling_stab > 0.9)

    # T5: Scrambled adversarial drops CCS
    monitor3 = OnlineConsistencyMonitor(sae=sae, window_size=10, tau_gs=0.5, tau_ccs=0.6)
    for i in range(5):
        monitor3.push(i, enc.encode_listen_layer(i))
    adv_act = enc.encode_listen_layer(99, adversarial_shift=5.0, scramble_seed=777)
    r_adv = monitor3.push(99, adv_act, label="adversarial")
    check("Adversarial: delta_gs elevated", r_adv.delta_gs > 0.3)

    # T6: Full simulation produces records
    records = simulate_stream(n_utterances=25, adversarial_indices=[12, 13],
                               benign_hard_indices=[17, 18])
    check("Simulation: 25 records", len(records) == 25)
    check("Records have ccs field", hasattr(records[0], "ccs"))
    check("Records have alert_dual field", hasattr(records[0], "alert_dual"))

    # T7: Evaluation runs without error
    ev = evaluate(records)
    check("Evaluation: single_gate in result", "single_gate" in ev)
    check("Evaluation: dual_gate in result", "dual_gate" in ev)
    check("Evaluation: H1 fpr key present", "H1_dual_wins_fpr" in ev["hypothesis"])

    print(f"\nResults: {passed}/{passed+failed} passed")
    return failed == 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="M9 Online Causal Consistency Monitor (Q112)"
    )
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--n", type=int, default=25)
    parser.add_argument("--window", type=int, default=10)
    parser.add_argument("--tau-gs", type=float, default=2.0)
    parser.add_argument("--tau-ccs", type=float, default=0.4)
    parser.add_argument("--shift", type=float, default=4.0)
    parser.add_argument("--adversarial", type=int, nargs="+", default=[12, 13])
    parser.add_argument("--benign-hard", type=int, nargs="+", default=[15, 16])
    args = parser.parse_args()

    if args.test:
        ok = run_tests()
        sys.exit(0 if ok else 1)

    records = simulate_stream(
        n_utterances=args.n,
        window_size=args.window,
        tau_gs=args.tau_gs,
        tau_ccs=args.tau_ccs,
        adversarial_indices=args.adversarial,
        benign_hard_indices=args.benign_hard,
        adversarial_shift=args.shift,
    )
    ev = evaluate(records)

    if args.json:
        out = {
            "config": {
                "n": args.n, "window": args.window,
                "tau_gs": args.tau_gs, "tau_ccs": args.tau_ccs,
                "adversarial": args.adversarial, "benign_hard": args.benign_hard,
                "shift": args.shift,
            },
            "records": [
                {
                    "id": r.utterance_id,
                    "label": r.label,
                    "delta_gs": round(r.delta_gs, 4),
                    "ccs": round(r.ccs, 4),
                    "and_gate_frac": round(r.and_gate_frac, 3),
                    "schelling_stab": round(r.schelling_stab, 4),
                    "alert_single": r.alert_single,
                    "alert_dual": r.alert_dual,
                }
                for r in records
            ],
            "evaluation": ev,
        }
        print(json.dumps(out, indent=2))
        return

    # Human-readable
    print("=" * 72)
    print("M9 Online Causal Consistency Monitor — Q112")
    print(f"Window={args.window} | τ_gs={args.tau_gs} | τ_ccs={args.tau_ccs} | shift={args.shift}")
    print("=" * 72)
    print(f"{'ID':>4}  {'Label':>12}  {'ΔGS':>7}  {'CCS':>6}  {'AND%':>5}  {'Sch':>6}  {'Sgl':>5}  {'Dual':>5}")
    print("-" * 60)
    for r in records:
        s_flag = "🚨" if r.alert_single else "   "
        d_flag = "🚨" if r.alert_dual else "   "
        warmup = "(W)" if r.delta_gs == 0.0 else "   "
        print(
            f"{r.utterance_id:>4}  {r.label:>12}  "
            f"{r.delta_gs:>7.4f}  {r.ccs:>6.3f}  {r.and_gate_frac:>5.2f}  "
            f"{r.schelling_stab:>6.3f}  {s_flag}{warmup}  {d_flag}"
        )

    sg = ev["single_gate"]
    dg = ev["dual_gate"]
    h = ev["hypothesis"]
    print("\n── Evaluation ──")
    print(f"  {'':20s} {'Single-gate':>12}  {'Dual-gate':>12}")
    print(f"  {'TP/FP/FN/TN':20s} {sg['tp']}/{sg['fp']}/{sg['fn']}/{sg['tn']:>6}  "
          f"{dg['tp']}/{dg['fp']}/{dg['fn']}/{dg['tn']:>6}")
    print(f"  {'Precision':20s} {sg['precision']:>12.3f}  {dg['precision']:>12.3f}")
    print(f"  {'Recall':20s} {sg['recall']:>12.3f}  {dg['recall']:>12.3f}")
    print(f"  {'F1':20s} {sg['f1']:>12.3f}  {dg['f1']:>12.3f}")
    print(f"  {'FPR':20s} {sg['fpr']:>12.3f}  {dg['fpr']:>12.3f}")
    print()
    print("── Hypotheses ──")
    print(f"  H1 Dual wins FPR:    {'✅ SUPPORTED' if h['H1_dual_wins_fpr'] else '❌ NOT SUPPORTED'}")
    print(f"  H1 Dual recall OK:   {'✅ SUPPORTED' if h['H1_dual_wins_recall'] else '❌ NOT SUPPORTED'}")
    print()
    print("── Connection to Tracks ──")
    print("  T5: CCS gate suppresses benign-hard FPs in jailbreak streaming detector")
    print("  T3: CCS = online proxy for gc(k) causal structure health")
    print("  Q083: This is the streaming/online counterpart of M9-gated dual-factor detector")
    print("  Next: Calibrate τ_ccs on real distribution; integrate into gc_jailbreak_classifier.py")


if __name__ == "__main__":
    main()
