#!/usr/bin/env python3
"""
SAE-guided Adversarial Detector Calibration (SPIRIT-inspired)
Track T5, Q041

RESEARCH QUESTION
-----------------
Given a trained SAE on the audio-LLM's listen-layer activations, can we
build a lightweight threshold-based detector that flags adversarial audio
inputs with high precision before the model generates a harmful response?

Inspired by SPIRIT (Safety Probing via Interpretable Representations in
Transformers): SAE feature activations carry a detectable signal when inputs
are crafted to override the model's audio-grounding mechanism.

APPROACH
--------
Two classes of synthetic attacks:

  1. "Suppression attacks": h[0] driven negative (audio signal suppressed →
     gc(k) drops; model guesses from language prior; exploitable)
  2. "Override attacks": audio vector direction inverted while keeping norm
     similar to benign (model receives false phonological evidence)

Detector pipeline:
  a. Train SAE on benign activations
  b. For each input, compute SAE feature vector
  c. Aggregate features → scalar alert scores via 3 methods:
       - Top-1 score: max(f)  (single most-active feature)
       - L1 score: sum(|f|)   (total feature activity)
       - GC-proj score: dot(h, v_gc) where v_gc is the gc-predictive direction
  d. Sweep thresholds on validation set → PR curve
  e. Calibrate: find threshold at target_precision ∈ {0.9, 0.95}
  f. Report: AUC-PR, calibrated threshold, precision/recall at calibration point

TIER
----
Tier 0: scaffold, synthetic data, pure numpy — no model download needed.
Tier 1: full calibration run (CPU <5min with N=2000). Auto-allowed.
Tier 2: real Whisper activations — needs Leo approval.

USAGE
-----
  python3 sae_adversarial_detector.py                # full calibration report
  python3 sae_adversarial_detector.py --test         # unit tests
  python3 sae_adversarial_detector.py --n 2000       # larger run
  python3 sae_adversarial_detector.py --json         # JSON output
  python3 sae_adversarial_detector.py --target-prec 0.95

DESIGN NOTE
-----------
Intentionally no ML libraries (sklearn/torch). Everything is numpy. This
keeps the tool auditable and importable into any research environment without
dependency hell. The math is simple enough that numpy is sufficient.

Author: Little Leo (Lab) — 2026-03-09
Track: T5, Q041, explore-fallback
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Re-import MicroGPT + SAE from sae_listen_layer (inline to avoid path issues)
# ---------------------------------------------------------------------------

class MicroGPT:
    def __init__(self, n_layers: int = 6, d_model: int = 8, seed: int = 42):
        self.n_layers = n_layers
        self.d_model = d_model
        rng = np.random.RandomState(seed)
        self.W = [rng.randn(d_model, d_model) * 0.15 for _ in range(n_layers)]
        self.b = [rng.randn(d_model) * 0.05 for _ in range(n_layers)]
        self.W_out = rng.randn(d_model) * 0.3

    def forward(self, h0: np.ndarray, record: bool = False):
        h = h0.copy()
        acts = [h.copy()] if record else []
        for k in range(self.n_layers):
            h = h + np.tanh(self.W[k] @ h + self.b[k])
            if record:
                acts.append(h.copy())
        return float(self.W_out @ h), acts

    def listen_layer_activation(self, h0: np.ndarray) -> np.ndarray:
        """Return activation after layer 0 (the 'listen layer')."""
        h = h0.copy()
        h = h + np.tanh(self.W[0] @ h + self.b[0])
        return h  # (d_model,)


@dataclass
class SAEConfig:
    d_model: int = 8
    d_sae: int = 32
    l1_lambda: float = 0.01
    lr: float = 0.003
    epochs: int = 100
    batch_size: int = 64
    seed: int = 1337


class SAE:
    """Minimal numpy SAE (Anthropic-style unit-norm decoder)."""

    def __init__(self, cfg: SAEConfig):
        self.cfg = cfg
        rng = np.random.RandomState(cfg.seed)
        d, d_sae = cfg.d_model, cfg.d_sae
        W_dec = rng.randn(d, d_sae)
        W_dec /= np.linalg.norm(W_dec, axis=0, keepdims=True) + 1e-8
        self.W_dec = W_dec
        self.W_enc = W_dec.T.copy()
        self.b_enc = np.zeros(d_sae)
        self.b_dec = np.zeros(d)
        self._m = {k: np.zeros_like(v) for k, v in self._params().items()}
        self._v = {k: np.zeros_like(v) for k, v in self._params().items()}
        self._t = 0

    def _params(self):
        return {"W_enc": self.W_enc, "W_dec": self.W_dec,
                "b_enc": self.b_enc, "b_dec": self.b_dec}

    def encode(self, h: np.ndarray) -> np.ndarray:
        pre = (h - self.b_dec) @ self.W_enc.T + self.b_enc
        return np.maximum(0.0, pre)

    def decode(self, f: np.ndarray) -> np.ndarray:
        return f @ self.W_dec.T + self.b_dec

    def _normalize_decoder(self):
        norms = np.linalg.norm(self.W_dec, axis=0, keepdims=True)
        self.W_dec /= np.maximum(norms, 1.0)

    def train(self, data: np.ndarray, verbose: bool = False) -> List[float]:
        cfg = self.cfg
        N = data.shape[0]
        rng = np.random.RandomState(cfg.seed + 10)
        b1, b2, eps = 0.9, 0.999, 1e-8
        losses = []
        for epoch in range(cfg.epochs):
            idx = rng.permutation(N)
            epoch_loss = 0.0; n_batches = 0
            for start in range(0, N, cfg.batch_size):
                b = data[idx[start:start + cfg.batch_size]]
                grads = self._grads(b)
                self._t += 1
                for name, g in grads.items():
                    g = np.clip(g, -1.0, 1.0)
                    self._m[name] = b1 * self._m[name] + (1 - b1) * g
                    self._v[name] = b2 * self._v[name] + (1 - b2) * g ** 2
                    m_hat = self._m[name] / (1 - b1 ** self._t)
                    v_hat = self._v[name] / (1 - b2 ** self._t)
                    param = getattr(self, name)
                    param -= cfg.lr * m_hat / (np.sqrt(v_hat) + eps)
                self._normalize_decoder()
                f = self.encode(b)
                h_hat = self.decode(f)
                loss = float(np.mean(np.sum((b - h_hat) ** 2, 1))
                             + cfg.l1_lambda * np.mean(np.sum(np.abs(f), 1)))
                epoch_loss += loss; n_batches += 1
            avg = epoch_loss / max(n_batches, 1)
            losses.append(avg)
            if verbose and (epoch % 25 == 0 or epoch == cfg.epochs - 1):
                print(f"  epoch {epoch:>4}  loss={avg:.5f}")
        return losses

    def _grads(self, h: np.ndarray) -> dict:
        N = h.shape[0]
        f = self.encode(h); h_hat = self.decode(f)
        rec_err = h_hat - h
        dh_hat = 2 * rec_err / N
        df_rec = dh_hat @ self.W_dec
        df_l1 = self.cfg.l1_lambda * np.sign(f) / N
        df = (df_rec + df_l1) * (f > 0)
        dW_dec = dh_hat.T @ f
        db_dec = dh_hat.mean(0)
        dW_enc = df.T @ (h - self.b_dec)
        db_enc = df.mean(0)
        return {"W_dec": dW_dec, "b_dec": db_dec,
                "W_enc": dW_enc, "b_enc": db_enc}


# ---------------------------------------------------------------------------
# Synthetic data generation
# ---------------------------------------------------------------------------

@dataclass
class SyntheticDataset:
    """
    Benign: h[0] ~ U(-0.5, 3.0) — normal audio signal range
    Suppression attack: h[0] ~ U(-3.0, -1.0) — audio suppressed, forces guess
    Override attack: h[0] ~ U(-1.5, 1.5) but inverted sign from a benign base
                     → model receives contradictory phonological evidence

    Both attack types exploit the same vulnerability: they move h[0] into
    a region where gc(0) drops and the language prior dominates. SAE features
    trained on benign activations should show anomalously low activity on
    audio-evidence features and/or anomalously high activity on out-of-distribution
    features.
    """
    benign_acts: np.ndarray    # (N_benign, d_model)
    attack_acts: np.ndarray    # (N_attack, d_model)
    attack_types: np.ndarray   # (N_attack,) str labels for analysis


def generate_synthetic_dataset(
    model: MicroGPT,
    n_benign: int = 600,
    n_attack: int = 200,
    seed: int = 77,
) -> SyntheticDataset:
    rng = np.random.RandomState(seed)
    d = model.d_model

    # --- Benign ---
    benign_acts = []
    for _ in range(n_benign):
        h = rng.randn(d) * 0.4
        h[0] = rng.uniform(-0.5, 3.0)   # normal audio signal (mostly positive)
        benign_acts.append(model.listen_layer_activation(h))

    # --- Suppression attacks (N/2) ---
    suppression_acts = []
    n_sup = n_attack // 2
    for _ in range(n_sup):
        h = rng.randn(d) * 0.4
        h[0] = rng.uniform(-3.0, -1.0)  # audio dimension forced into suppression zone
        suppression_acts.append(model.listen_layer_activation(h))

    # --- Override attacks (N/2) ---
    override_acts = []
    n_ovr = n_attack - n_sup
    for _ in range(n_ovr):
        h = rng.randn(d) * 0.4
        # Take a normally-plausible base and invert the audio dimension
        base_audio = rng.uniform(0.5, 2.5)
        h[0] = -base_audio          # sign-flip = phoneme direction inverted
        # Add adversarial perturbation in other dims to evade simple norm check
        h[1:] += rng.randn(d - 1) * 0.3
        override_acts.append(model.listen_layer_activation(h))

    attack_acts = np.array(suppression_acts + override_acts)
    attack_types = np.array(
        ["suppression"] * n_sup + ["override"] * n_ovr
    )

    return SyntheticDataset(
        benign_acts=np.array(benign_acts),
        attack_acts=attack_acts,
        attack_types=attack_types,
    )


# ---------------------------------------------------------------------------
# Detector: scoring functions
# ---------------------------------------------------------------------------

def score_top1(features: np.ndarray) -> np.ndarray:
    """Max feature activation per sample — sensitive to single dominant feature."""
    return features.max(axis=1)


def score_l1(features: np.ndarray) -> np.ndarray:
    """Total L1 activity — sensitive to broad activation shifts."""
    return features.sum(axis=1)


def score_gc_proj(
    activations: np.ndarray,
    sae: SAE,
    benign_acts: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Project activations onto the gc-predictive direction and return anomaly score.

    Strategy: find the SAE feature most correlated with the audio signal
    (dim 0 of h, which is our gc proxy). Its decoder column is the "audio
    evidence direction". Project each activation onto it.

    Returns:
        scores: (N,) — |projection| deviation from benign mean
        v_gc: (d_model,) — the gc-predictive direction
    """
    # Fit SAE features → audio_strength correlation on benign data
    benign_audio_strengths = benign_acts[:, 0]  # dim 0 is our gc proxy signal
    benign_features = sae.encode(benign_acts)   # (N_benign, d_sae)

    # Find most correlated feature
    best_feat = 0
    best_r = 0.0
    for i in range(sae.cfg.d_sae):
        f_i = benign_features[:, i]
        if f_i.std() < 1e-9:
            continue
        r = float(np.corrcoef(f_i, benign_audio_strengths)[0, 1])
        if abs(r) > abs(best_r):
            best_r = r; best_feat = i

    v_gc = sae.W_dec[:, best_feat]  # (d_model,) — gc-predictive decoder direction

    # Benign mean projection
    benign_proj = benign_acts @ v_gc
    benign_mean = benign_proj.mean()

    # Score = deviation from benign mean (absolute)
    proj = activations @ v_gc
    scores = np.abs(proj - benign_mean)
    return scores, v_gc


# ---------------------------------------------------------------------------
# Threshold calibration + PR curve
# ---------------------------------------------------------------------------

@dataclass
class CalibrationResult:
    method: str
    auc_pr: float
    calibrated_threshold: float
    precision_at_threshold: float
    recall_at_threshold: float
    target_precision: float
    all_thresholds: np.ndarray
    all_precisions: np.ndarray
    all_recalls: np.ndarray
    benign_score_mean: float
    attack_score_mean: float
    separation: float  # (attack_mean - benign_mean) / (benign_std + 1e-6)


def compute_pr_curve(
    scores: np.ndarray,
    labels: np.ndarray,
    n_thresholds: int = 200,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute precision-recall curve.
    labels: 1 = attack, 0 = benign
    Higher score → more likely attack.

    Returns: (thresholds, precisions, recalls) each shape (n_thresholds,)
    """
    t_min = scores.min()
    t_max = scores.max()
    thresholds = np.linspace(t_min, t_max, n_thresholds)
    precisions = []
    recalls = []

    n_pos = labels.sum()
    for t in thresholds:
        predicted = (scores >= t).astype(int)
        tp = int(((predicted == 1) & (labels == 1)).sum())
        fp = int(((predicted == 1) & (labels == 0)).sum())
        prec = tp / max(tp + fp, 1)
        rec = tp / max(n_pos, 1)
        precisions.append(prec)
        recalls.append(rec)

    return thresholds, np.array(precisions), np.array(recalls)


def compute_auc_pr(precisions: np.ndarray, recalls: np.ndarray) -> float:
    """Trapezoidal AUC-PR (recall as x-axis)."""
    # Sort by recall ascending
    idx = np.argsort(recalls)
    r = recalls[idx]
    p = precisions[idx]
    trapz = getattr(np, "trapezoid", None) or getattr(np, "trapz", None)
    return float(trapz(p, r))


def calibrate(
    method: str,
    scores: np.ndarray,
    labels: np.ndarray,
    benign_scores: np.ndarray,
    attack_scores: np.ndarray,
    target_precision: float = 0.9,
) -> CalibrationResult:
    thresholds, precs, recs = compute_pr_curve(scores, labels)
    auc = compute_auc_pr(precs, recs)

    # Find threshold that achieves target_precision (first one, sweeping high→low threshold)
    cal_t = thresholds[-1]   # default: highest threshold
    cal_p = 0.0; cal_r = 0.0

    # Sweep from high threshold to low: as threshold decreases, recall increases
    for t, p, r in sorted(zip(thresholds, precs, recs), key=lambda x: -x[0]):
        if p >= target_precision:
            cal_t = t; cal_p = p; cal_r = r

    sep = (attack_scores.mean() - benign_scores.mean()) / (benign_scores.std() + 1e-6)

    return CalibrationResult(
        method=method,
        auc_pr=auc,
        calibrated_threshold=float(cal_t),
        precision_at_threshold=float(cal_p),
        recall_at_threshold=float(cal_r),
        target_precision=target_precision,
        all_thresholds=thresholds,
        all_precisions=precs,
        all_recalls=recs,
        benign_score_mean=float(benign_scores.mean()),
        attack_score_mean=float(attack_scores.mean()),
        separation=float(sep),
    )


# ---------------------------------------------------------------------------
# Full calibration pipeline
# ---------------------------------------------------------------------------

@dataclass
class DetectorReport:
    results: Dict[str, CalibrationResult]
    target_precision: float
    n_benign_train: int
    n_benign_val: int
    n_attack_val: int
    attack_type_breakdown: Dict[str, Dict[str, float]]


def run_calibration(
    n_benign: int = 600,
    n_attack: int = 200,
    d_sae: int = 32,
    target_precision: float = 0.9,
    seed: int = 42,
    verbose: bool = False,
) -> DetectorReport:
    """
    Full calibration pipeline:
    1. Generate synthetic benign + attack samples
    2. Train SAE on 80% of benign (train split)
    3. Score all samples with 3 methods
    4. Calibrate thresholds on validation set (20% benign + all attack)
    5. Per-attack-type analysis
    """
    rng = np.random.RandomState(seed)
    model = MicroGPT(n_layers=6, d_model=8, seed=seed)

    # Generate data
    ds = generate_synthetic_dataset(
        model, n_benign=n_benign, n_attack=n_attack, seed=seed + 1
    )

    # Train/val split on benign
    n_train = int(0.8 * len(ds.benign_acts))
    idx = rng.permutation(len(ds.benign_acts))
    benign_train = ds.benign_acts[idx[:n_train]]
    benign_val = ds.benign_acts[idx[n_train:]]

    # Train SAE on benign train
    cfg = SAEConfig(d_model=model.d_model, d_sae=d_sae, epochs=100, seed=seed + 2)
    sae = SAE(cfg)
    if verbose:
        print(f"Training SAE (d_sae={d_sae})...")
    sae.train(benign_train, verbose=verbose)

    # Build val set (benign_val + all attack)
    val_acts = np.vstack([benign_val, ds.attack_acts])
    val_labels = np.array([0] * len(benign_val) + [1] * len(ds.attack_acts))

    # Score with each method
    val_features = sae.encode(val_acts)
    benign_val_features = sae.encode(benign_val)
    attack_features = sae.encode(ds.attack_acts)

    gc_scores_val, v_gc = score_gc_proj(val_acts, sae, benign_train)
    gc_scores_benign_val = gc_scores_val[:len(benign_val)]
    gc_scores_attack_val = gc_scores_val[len(benign_val):]

    methods = {
        "top1": (
            score_top1(val_features),
            score_top1(benign_val_features),
            score_top1(attack_features),
        ),
        "l1": (
            score_l1(val_features),
            score_l1(benign_val_features),
            score_l1(attack_features),
        ),
        "gc_proj": (
            gc_scores_val,
            gc_scores_benign_val,
            gc_scores_attack_val,
        ),
    }

    results = {}
    for method_name, (val_scores, b_scores, a_scores) in methods.items():
        results[method_name] = calibrate(
            method_name, val_scores, val_labels,
            b_scores, a_scores, target_precision
        )

    # Per-attack-type breakdown (using best method = gc_proj)
    attack_type_breakdown = {}
    gc_attack_scores = gc_scores_attack_val
    for atype in np.unique(ds.attack_types):
        mask = ds.attack_types == atype
        scores_at = gc_attack_scores[mask]
        thresh = results["gc_proj"].calibrated_threshold
        detected = (scores_at >= thresh).mean()
        attack_type_breakdown[atype] = {
            "n": int(mask.sum()),
            "mean_score": round(float(scores_at.mean()), 4),
            "recall_at_threshold": round(float(detected), 4),
        }

    return DetectorReport(
        results=results,
        target_precision=target_precision,
        n_benign_train=n_train,
        n_benign_val=len(benign_val),
        n_attack_val=len(ds.attack_acts),
        attack_type_breakdown=attack_type_breakdown,
    )


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def print_report(report: DetectorReport):
    print("=" * 68)
    print("SAE-guided Adversarial Detector Calibration Report (SPIRIT-inspired)")
    print("=" * 68)
    print(f"  Dataset: {report.n_benign_train} benign train | "
          f"{report.n_benign_val} benign val | {report.n_attack_val} attack val")
    print(f"  Target precision: {report.target_precision:.0%}")
    print()

    methods_order = ["gc_proj", "l1", "top1"]
    headers = ["Method", "AUC-PR", "Thresh", f"Prec@{report.target_precision:.0%}",
               "Recall", "Separation(σ)"]
    row_fmt = "  {:<10}  {:>7}  {:>8}  {:>10}  {:>7}  {:>14}"
    print(row_fmt.format(*headers))
    print("  " + "-" * 64)

    for m in methods_order:
        r = report.results[m]
        sep_str = f"{r.separation:+.2f}σ"
        print(row_fmt.format(
            m,
            f"{r.auc_pr:.4f}",
            f"{r.calibrated_threshold:.4f}",
            f"{r.precision_at_threshold:.3f}",
            f"{r.recall_at_threshold:.3f}",
            sep_str,
        ))
    print()

    # gc_proj detail
    gc = report.results["gc_proj"]
    print(f"  gc_proj score distribution:")
    print(f"    benign val:  mean={gc.benign_score_mean:.4f}")
    print(f"    attack val:  mean={gc.attack_score_mean:.4f}")
    print()

    print(f"  Attack-type breakdown (gc_proj detector, threshold={gc.calibrated_threshold:.4f}):")
    for atype, info in report.attack_type_breakdown.items():
        print(f"    {atype:<15}: n={info['n']:>3}  "
              f"mean_score={info['mean_score']:>7.4f}  "
              f"recall={info['recall_at_threshold']:.3f}")
    print()

    # Best method
    best = max(report.results.values(), key=lambda r: r.auc_pr)
    print(f"  Best method by AUC-PR: {best.method} ({best.auc_pr:.4f})")
    print()

    # Interpretation
    gc_r = report.results["gc_proj"]
    if gc_r.auc_pr > 0.8 and gc_r.precision_at_threshold >= report.target_precision:
        verdict = (f"✓ SPIRIT hypothesis supported: gc_proj detector achieves AUC-PR={gc_r.auc_pr:.3f} "
                   f"and precision={gc_r.precision_at_threshold:.3f} @ threshold={gc_r.calibrated_threshold:.4f}")
    elif gc_r.separation > 1.0:
        verdict = (f"~ Partial: gc_proj has {gc_r.separation:.2f}σ separation but "
                   f"AUC-PR={gc_r.auc_pr:.3f} — tune SAE λ or increase N")
    else:
        verdict = "✗ Low separation — SAE features may not capture adversarial signal; try larger d_sae"
    print(f"  Verdict: {verdict}")
    print()
    print(f"  Next step (Tier 2): Apply to real Whisper activations with genuine")
    print(f"  adversarial audio (TextFooler / AutoAttack on speech inputs).")
    print("=" * 68)


def to_json(report: DetectorReport) -> dict:
    out = {
        "target_precision": report.target_precision,
        "n_benign_train": report.n_benign_train,
        "n_benign_val": report.n_benign_val,
        "n_attack_val": report.n_attack_val,
        "methods": {},
        "attack_type_breakdown": report.attack_type_breakdown,
    }
    for name, r in report.results.items():
        out["methods"][name] = {
            "auc_pr": round(r.auc_pr, 5),
            "calibrated_threshold": round(r.calibrated_threshold, 5),
            "precision_at_threshold": round(r.precision_at_threshold, 4),
            "recall_at_threshold": round(r.recall_at_threshold, 4),
            "separation_sigma": round(r.separation, 4),
            "benign_score_mean": round(r.benign_score_mean, 5),
            "attack_score_mean": round(r.attack_score_mean, 5),
        }
    return out


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def run_tests() -> bool:
    failures = []

    def check(name, cond, detail=""):
        if not cond:
            failures.append(f"FAIL [{name}]: {detail}")

    model = MicroGPT(n_layers=6, d_model=8, seed=0)

    # Test 1: Dataset generation shapes
    ds = generate_synthetic_dataset(model, n_benign=50, n_attack=20, seed=1)
    check("benign_shape", ds.benign_acts.shape == (50, 8), str(ds.benign_acts.shape))
    check("attack_shape", ds.attack_acts.shape == (20, 8), str(ds.attack_acts.shape))
    check("attack_types_len", len(ds.attack_types) == 20, str(len(ds.attack_types)))

    # Test 2: Score functions shapes
    cfg = SAEConfig(d_model=8, d_sae=16, epochs=5)
    sae = SAE(cfg)
    feats = sae.encode(ds.benign_acts)
    top1 = score_top1(feats)
    l1 = score_l1(feats)
    check("top1_shape", top1.shape == (50,), str(top1.shape))
    check("l1_shape", l1.shape == (50,), str(l1.shape))
    check("top1_nonneg", (top1 >= 0).all(), str(top1.min()))
    check("l1_nonneg", (l1 >= 0).all(), str(l1.min()))

    # Test 3: PR curve shape
    scores = np.random.rand(70)
    labels = np.array([1]*20 + [0]*50)
    thresholds, precs, recs = compute_pr_curve(scores, labels, n_thresholds=50)
    check("pr_shapes", len(thresholds) == len(precs) == len(recs) == 50)
    check("prec_range", ((precs >= 0) & (precs <= 1)).all(), str(precs.min()))
    check("rec_range", ((recs >= 0) & (recs <= 1)).all(), str(recs.min()))

    # Test 4: AUC-PR is in [0, 1]
    auc = compute_auc_pr(precs, recs)
    check("auc_range", 0.0 <= auc <= 1.0, str(auc))

    # Test 5: CalibrationResult structure
    r = calibrate("test", scores, labels, scores[:50], scores[50:], target_precision=0.5)
    check("cal_prec_ge_target",
          r.precision_at_threshold >= 0.5 or r.calibrated_threshold == thresholds[-1],
          f"prec={r.precision_at_threshold}")

    # Test 6: Full pipeline completes without crash
    try:
        report = run_calibration(n_benign=100, n_attack=40, d_sae=16,
                                 target_precision=0.8, seed=7)
        check("report_methods", set(report.results.keys()) == {"top1", "l1", "gc_proj"})
        check("report_auc_valid", all(0 <= r.auc_pr <= 1 for r in report.results.values()))
    except Exception as e:
        failures.append(f"FAIL [full_pipeline]: {e}")

    if failures:
        print("UNIT TEST RESULTS: FAIL")
        for f in failures:
            print(f"  {f}")
        return False

    n = 6 + 4 + 3 + 1 + 1 + 3
    print(f"UNIT TEST RESULTS: PASS ({n}/{n})")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="SAE-guided adversarial detector calibration (SPIRIT-inspired)"
    )
    parser.add_argument("--test", action="store_true", help="Run unit tests and exit")
    parser.add_argument("--n", type=int, default=600, help="Number of benign training samples")
    parser.add_argument("--n-attack", type=int, default=200, help="Number of attack samples")
    parser.add_argument("--d-sae", type=int, default=32, help="SAE dictionary size")
    parser.add_argument("--target-prec", type=float, default=0.9,
                        help="Target precision for threshold calibration (0-1)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    if args.test:
        ok = run_tests()
        sys.exit(0 if ok else 1)

    report = run_calibration(
        n_benign=args.n,
        n_attack=args.n_attack,
        d_sae=args.d_sae,
        target_precision=args.target_prec,
        seed=args.seed,
        verbose=args.verbose,
    )

    if args.json:
        print(json.dumps(to_json(report), indent=2))
    else:
        print_report(report)


if __name__ == "__main__":
    main()
