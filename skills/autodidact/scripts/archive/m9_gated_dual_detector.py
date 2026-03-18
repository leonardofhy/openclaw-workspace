#!/usr/bin/env python3
"""
M9-Gated Dual-Factor Adversarial Detector
Track T5, Q083

RESEARCH QUESTION
-----------------
Does gating SAE-anomaly alerts (M7) on causal consistency (M9) reduce the
false-positive rate versus single-factor detection?

Two-factor alert rule:
  ALERT iff  M7_score >= thresh_M7  AND  M9_consistency <= thresh_M9

If M9 is high (model has intact causal abstraction), we suppress the alert
even when M7 fires — the model is geometrically stressed but still causally
consistent (benign hardcase, not adversarial).

KEY METRICS
-----------
M7 proxy: SAE L1 anomaly score from gc_proj direction (sae_adversarial_detector
          approach). High = model under geometric stress.

M9 proxy: Causal Abstraction Consistency (CAC) — AND-gate fraction × Schelling
          stability among top-k SAE features. High CAC = clean causal graph.
          Under adversarial attack, features decohere → M9 drops.

HYPOTHESES
----------
H1 (Dual wins): Two-factor FP rate < single-factor FP at same recall.
H2 (M9 is noise): M9 adds no information → two-factor = single-factor.
H3 (M9 gate too tight): Low-FP but recall drops below acceptable level.

TIER: 0 (numpy-only mock, <2 min CPU)

USAGE
-----
  python3 m9_gated_dual_detector.py              # full comparison report
  python3 m9_gated_dual_detector.py --test       # unit tests
  python3 m9_gated_dual_detector.py --json       # JSON output
  python3 m9_gated_dual_detector.py --n 1000     # larger run

Author: Little Leo (Lab) — 2026-03-18
Track: T5, Q083, explore-fallback build
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Re-use MicroGPT + SAE from sae_adversarial_detector (inline copy, no import)
# ---------------------------------------------------------------------------

class MicroGPT:
    def __init__(self, n_layers: int = 6, d_model: int = 8, seed: int = 42):
        self.n_layers = n_layers
        self.d_model = d_model
        rng = np.random.RandomState(seed)
        self.W = [rng.randn(d_model, d_model) * 0.15 for _ in range(n_layers)]
        self.b = [rng.randn(d_model) * 0.05 for _ in range(n_layers)]
        self.W_out = rng.randn(d_model) * 0.3

    def listen_layer_activation(self, h0: np.ndarray) -> np.ndarray:
        h = h0.copy()
        h = h + np.tanh(self.W[0] @ h + self.b[0])
        return h


class SAE:
    """Minimal numpy SAE (unit-norm decoder, Adam)."""

    def __init__(self, d_model: int = 8, d_sae: int = 32, seed: int = 1337):
        rng = np.random.RandomState(seed)
        W_dec = rng.randn(d_model, d_sae)
        W_dec /= np.linalg.norm(W_dec, axis=0, keepdims=True) + 1e-8
        self.W_dec = W_dec
        self.W_enc = W_dec.T.copy()
        self.b_enc = np.zeros(d_sae)
        self.b_dec = np.zeros(d_model)
        self.d_model = d_model
        self.d_sae = d_sae
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

    def train(self, data: np.ndarray, epochs: int = 100, lr: float = 0.003,
              l1_lambda: float = 0.01, batch_size: int = 64):
        rng = np.random.RandomState(99)
        N = data.shape[0]
        b1, b2, eps = 0.9, 0.999, 1e-8
        for epoch in range(epochs):
            idx = rng.permutation(N)
            for start in range(0, N, batch_size):
                b = data[idx[start:start + batch_size]]
                f = self.encode(b); h_hat = self.decode(f)
                rec = h_hat - b
                dh = 2 * rec / len(b)
                df = (dh @ self.W_dec) * (f > 0) + l1_lambda * np.sign(f) / len(b)
                grads = {
                    "W_dec": dh.T @ f,
                    "b_dec": dh.mean(0),
                    "W_enc": df.T @ (b - self.b_dec),
                    "b_enc": df.mean(0),
                }
                self._t += 1
                for name, g in grads.items():
                    g = np.clip(g, -1, 1)
                    self._m[name] = b1 * self._m[name] + (1 - b1) * g
                    self._v[name] = b2 * self._v[name] + (1 - b2) * g ** 2
                    m_hat = self._m[name] / (1 - b1 ** self._t)
                    v_hat = self._v[name] / (1 - b2 ** self._t)
                    getattr(self, name).__isub__(lr * m_hat / (np.sqrt(v_hat) + eps))
                self._normalize_decoder()


# ---------------------------------------------------------------------------
# Data generation
# ---------------------------------------------------------------------------

def generate_data(model: MicroGPT, n_benign: int, n_attack: int,
                  n_benign_hard: int, seed: int = 77):
    """
    Three classes:
      - benign: normal audio, h[0] in (-0.5, 3.0)
      - benign_hard: geometrically stressed (loud audio), h[0] in (2.8, 5.0)
                     → M7 fires but M9 should still be high (no adversarial)
      - attack: adversarial, h[0] suppressed/inverted, causal features decohere

    Benign-hard is the key test class: single-factor detector raises FP,
    dual-factor should suppress it (M9 still high for benign-hard).
    """
    rng = np.random.RandomState(seed)
    d = model.d_model

    def make_acts(n, h0_range, noise_scale=0.4, decohere=False):
        acts = []
        for _ in range(n):
            h = rng.randn(d) * noise_scale
            h[0] = rng.uniform(*h0_range)
            if decohere:
                # adversarial: inject cross-feature noise to break causal structure
                h += rng.randn(d) * 1.2  # large random perturbation
                h[0] = rng.uniform(-3.0, -0.5)  # suppress audio signal
            acts.append(model.listen_layer_activation(h))
        return np.array(acts)

    benign = make_acts(n_benign, (-0.5, 3.0))
    benign_hard = make_acts(n_benign_hard, (2.8, 5.0))  # stressed but not adversarial
    attack = make_acts(n_attack, (-3.0, -0.5), decohere=True)

    return benign, benign_hard, attack


# ---------------------------------------------------------------------------
# M7 score: SAE L1 anomaly relative to benign reference
# ---------------------------------------------------------------------------

def compute_m7_scores(acts: np.ndarray, sae: SAE,
                      benign_ref_feats: np.ndarray) -> np.ndarray:
    """
    M7 = SAE L1 anomaly: how much does feature activity deviate from benign?
    Score = L1(f) - benign_mean_L1 (z-scored by benign_std)
    """
    feats = sae.encode(acts)
    l1 = feats.sum(axis=1)
    benign_l1 = benign_ref_feats.sum(axis=1)
    mu = benign_l1.mean()
    sigma = benign_l1.std() + 1e-6
    return (l1 - mu) / sigma


# ---------------------------------------------------------------------------
# M9 score: Causal Abstraction Consistency
# ---------------------------------------------------------------------------

def compute_m9_scores(acts: np.ndarray, sae: SAE,
                      benign_ref_acts: np.ndarray,
                      n_top_features: int = 8) -> np.ndarray:
    """
    M9 proxy = CAC (Causal Abstraction Consistency):
      1. For each sample, get top-k SAE features by activation
      2. AND-gate proxy: feature fires together with its expected co-activators
         (proxy: inter-feature correlation stability vs benign reference)
      3. Schelling stability proxy: cosine similarity of feature pattern
         to the "typical" benign feature cluster center

    Score in [0, 1]. High = causally consistent (benign-like). Low = decoherent (adversarial).
    """
    feats = sae.encode(acts)         # (N, d_sae)
    benign_feats = sae.encode(benign_ref_acts)  # (N_ref, d_sae)

    # Benign cluster: mean feature vector (normalized)
    benign_mean_feat = benign_feats.mean(axis=0)  # (d_sae,)
    benign_mean_norm = benign_mean_feat / (np.linalg.norm(benign_mean_feat) + 1e-8)

    # Benign inter-feature co-activation structure (top-k co-activation correlation)
    # Proxy: correlation matrix of top features among benign samples
    top_feat_idx = np.argsort(benign_feats.mean(0))[-n_top_features:]
    benign_top = benign_feats[:, top_feat_idx]  # (N_ref, k)
    # Correlation structure: (k, k) matrix
    benign_corr = np.corrcoef(benign_top.T)  # (k, k), benign reference
    benign_corr = np.nan_to_num(benign_corr)

    scores = np.zeros(len(acts))
    for i, f in enumerate(feats):
        # Component 1: Schelling stability — cosine to benign centroid
        f_norm = f / (np.linalg.norm(f) + 1e-8)
        cos_sim = float(np.dot(f_norm, benign_mean_norm))
        schelling = (cos_sim + 1) / 2  # map [-1,1] → [0,1]

        # Component 2: AND-gate fraction — how well co-activation structure matches
        f_top = f[top_feat_idx]
        # Correlation of this sample's top features vs benign expected
        # Use: for each pair, sign-match of (f_i - mean_i)(f_j - mean_j) vs benign_corr_ij
        benign_top_mean = benign_feats[:, top_feat_idx].mean(0)
        diff = f_top - benign_top_mean
        outer = np.outer(diff, diff)  # (k, k)
        # Normalize
        max_abs = np.abs(outer).max() + 1e-8
        outer_norm = outer / max_abs
        # Sign match with benign_corr (ignoring diagonal)
        mask = 1 - np.eye(n_top_features)
        sign_match = (np.sign(outer_norm) == np.sign(benign_corr)) * mask
        and_gate_frac = sign_match.sum() / (mask.sum() + 1e-6)

        # CAC = geometric mean of two components
        scores[i] = np.sqrt(schelling * and_gate_frac + 1e-6)

    return scores  # high = consistent, low = decoherent


# ---------------------------------------------------------------------------
# Detector comparison
# ---------------------------------------------------------------------------

@dataclass
class DetectionResult:
    name: str
    tp: int; fp: int; tn: int; fn: int
    precision: float; recall: float; fpr: float; f1: float


def evaluate_detector(
    preds: np.ndarray, labels: np.ndarray, name: str
) -> DetectionResult:
    """labels: 1=attack, 0=benign. preds: 1=alert."""
    tp = int(((preds == 1) & (labels == 1)).sum())
    fp = int(((preds == 1) & (labels == 0)).sum())
    tn = int(((preds == 0) & (labels == 0)).sum())
    fn = int(((preds == 0) & (labels == 1)).sum())
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    fpr = fp / max(fp + tn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-6)
    return DetectionResult(name=name, tp=tp, fp=fp, tn=tn, fn=fn,
                           precision=precision, recall=recall, fpr=fpr, f1=f1)


def sweep_dual_thresholds(
    m7_scores: np.ndarray,
    m9_scores: np.ndarray,
    labels: np.ndarray,
    n_thresholds: int = 30,
) -> Tuple[float, float, DetectionResult]:
    """Grid search best (thresh_M7, thresh_M9) by F1."""
    best_f1 = -1.0
    best_t7 = 0.0
    best_t9 = 0.5
    best_result = None

    t7_vals = np.percentile(m7_scores, np.linspace(20, 80, n_thresholds))
    t9_vals = np.percentile(m9_scores, np.linspace(20, 80, n_thresholds))

    for t7 in t7_vals:
        for t9 in t9_vals:
            preds = ((m7_scores >= t7) & (m9_scores <= t9)).astype(int)
            r = evaluate_detector(preds, labels, "dual_sweep")
            if r.f1 > best_f1:
                best_f1 = r.f1
                best_t7 = t7
                best_t9 = t9
                best_result = r

    return best_t7, best_t9, best_result


@dataclass
class ComparisonReport:
    n_benign: int
    n_benign_hard: int
    n_attack: int
    single_factor: DetectionResult
    dual_factor: DetectionResult
    thresh_m7: float
    thresh_m9: float
    m7_benign_mean: float
    m7_benign_hard_mean: float
    m7_attack_mean: float
    m9_benign_mean: float
    m9_benign_hard_mean: float
    m9_attack_mean: float
    dual_wins_fpr: bool
    dual_wins_f1: bool


def run_comparison(n_benign: int = 500, n_attack: int = 200, n_benign_hard: int = 100,
                   d_sae: int = 32, seed: int = 42) -> ComparisonReport:
    model = MicroGPT(n_layers=6, d_model=8, seed=seed)
    benign, benign_hard, attack = generate_data(
        model, n_benign, n_attack, n_benign_hard, seed=seed + 1
    )

    # Train SAE on benign only
    sae = SAE(d_model=8, d_sae=d_sae, seed=seed + 2)
    sae.train(benign, epochs=100)

    # Compute scores for all splits
    benign_ref_feats = sae.encode(benign)

    m7_benign = compute_m7_scores(benign, sae, benign)
    m7_hard = compute_m7_scores(benign_hard, sae, benign)
    m7_attack = compute_m7_scores(attack, sae, benign)

    m9_benign = compute_m9_scores(benign, sae, benign)
    m9_hard = compute_m9_scores(benign_hard, sae, benign)
    m9_attack = compute_m9_scores(attack, sae, benign)

    # Build val set: benign_val (50%) + benign_hard + attack
    rng = np.random.RandomState(seed + 3)
    val_idx = rng.choice(n_benign, n_benign // 2, replace=False)
    m7_all = np.concatenate([m7_benign[val_idx], m7_hard, m7_attack])
    m9_all = np.concatenate([m9_benign[val_idx], m9_hard, m9_attack])
    labels = np.array([0] * (n_benign // 2 + n_benign_hard) + [1] * n_attack)

    # Single-factor: sweep M7 threshold only
    best_single_f1 = -1.0
    best_single_thresh = 0.0
    best_single_result = None
    for t7 in np.percentile(m7_all, np.linspace(20, 80, 40)):
        preds = (m7_all >= t7).astype(int)
        r = evaluate_detector(preds, labels, "single_M7")
        if r.f1 > best_single_f1:
            best_single_f1 = r.f1
            best_single_thresh = t7
            best_single_result = r

    # Dual-factor: grid search M7 AND M9 thresholds
    best_t7, best_t9, best_dual_result = sweep_dual_thresholds(m7_all, m9_all, labels)
    best_dual_result.name = "dual_M7+M9"

    return ComparisonReport(
        n_benign=n_benign,
        n_benign_hard=n_benign_hard,
        n_attack=n_attack,
        single_factor=best_single_result,
        dual_factor=best_dual_result,
        thresh_m7=best_t7,
        thresh_m9=best_t9,
        m7_benign_mean=float(m7_benign.mean()),
        m7_benign_hard_mean=float(m7_hard.mean()),
        m7_attack_mean=float(m7_attack.mean()),
        m9_benign_mean=float(m9_benign.mean()),
        m9_benign_hard_mean=float(m9_hard.mean()),
        m9_attack_mean=float(m9_attack.mean()),
        dual_wins_fpr=best_dual_result.fpr < best_single_result.fpr,
        dual_wins_f1=best_dual_result.f1 >= best_single_result.f1,
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_report(r: ComparisonReport):
    print("=" * 65)
    print("M9-Gated Dual-Factor Adversarial Detector: Comparison Report")
    print("=" * 65)
    print(f"  Dataset: {r.n_benign} benign | {r.n_benign_hard} benign-hard | "
          f"{r.n_attack} attack")
    print()

    print("  Score distributions:")
    print(f"  {'Class':<15}  {'M7 (anomaly)':<15}  {'M9 (consistency)'}")
    print(f"  {'-'*55}")
    print(f"  {'benign':<15}  {r.m7_benign_mean:>+.3f}σ        "
          f"     {r.m9_benign_mean:.4f}")
    print(f"  {'benign-hard':<15}  {r.m7_benign_hard_mean:>+.3f}σ        "
          f"     {r.m9_benign_hard_mean:.4f}  ← FP risk for single-factor")
    print(f"  {'attack':<15}  {r.m7_attack_mean:>+.3f}σ        "
          f"     {r.m9_attack_mean:.4f}  ← should be low")
    print()

    print(f"  Thresholds: M7 >= {r.thresh_m7:.3f}  AND  M9 <= {r.thresh_m9:.3f}")
    print()

    header = f"  {'Detector':<18}  {'Prec':>6}  {'Recall':>7}  {'FPR':>6}  {'F1':>6}  {'TP':>4}  {'FP':>4}"
    print(header)
    print("  " + "-" * 58)
    for det in [r.single_factor, r.dual_factor]:
        print(f"  {det.name:<18}  {det.precision:>6.3f}  {det.recall:>7.3f}  "
              f"{det.fpr:>6.3f}  {det.f1:>6.3f}  {det.tp:>4}  {det.fp:>4}")
    print()

    fpr_delta = r.single_factor.fpr - r.dual_factor.fpr
    f1_delta = r.dual_factor.f1 - r.single_factor.f1
    print(f"  Δ FPR (single − dual): {fpr_delta:+.3f}  "
          f"({'improvement' if fpr_delta > 0 else 'no improvement'})")
    print(f"  Δ F1  (dual − single): {f1_delta:+.3f}")
    print()

    # Verdict
    if r.dual_wins_fpr and r.dual_wins_f1:
        v = "✓ H1 SUPPORTED: Dual-factor reduces FPR AND maintains/improves F1."
    elif r.dual_wins_fpr and not r.dual_wins_f1:
        v = ("~ H3 PARTIAL: Dual-factor cuts FPR but recall drops. "
             "M9 gate is too tight — try higher thresh_M9.")
    elif not r.dual_wins_fpr and m9_signal(r):
        v = "~ H1 PARTIAL: M9 adds discrimination signal but threshold tuning needed."
    else:
        v = "✗ H2 (NULL): M9 adds no benefit at this mock resolution — needs real activations."

    print(f"  Verdict: {v}")
    print()
    print("  Interpretation:")
    m9_sep = r.m9_benign_mean - r.m9_attack_mean
    print(f"  M9 separation (benign − attack): Δ={m9_sep:.4f} "
          f"({'✓ M9 discriminates' if m9_sep > 0.03 else '✗ M9 flat — try larger d_sae or more training'})")
    print()
    print("  Next: Apply to real Whisper listen-layer activations with genuine")
    print("  adversarial audio. Expect M9 separation to increase significantly")
    print("  since causal structure in real models is richer than MicroGPT.")
    print("=" * 65)


def m9_signal(r: ComparisonReport) -> bool:
    return r.m9_benign_mean > r.m9_attack_mean + 0.01


def to_json(r: ComparisonReport) -> dict:
    def det_dict(d: DetectionResult):
        return {"precision": round(d.precision, 4), "recall": round(d.recall, 4),
                "fpr": round(d.fpr, 4), "f1": round(d.f1, 4),
                "tp": d.tp, "fp": d.fp, "tn": d.tn, "fn": d.fn}
    return {
        "n_benign": r.n_benign, "n_benign_hard": r.n_benign_hard, "n_attack": r.n_attack,
        "thresh_m7": round(r.thresh_m7, 4), "thresh_m9": round(r.thresh_m9, 4),
        "scores": {
            "m7": {"benign": round(r.m7_benign_mean, 4),
                   "benign_hard": round(r.m7_benign_hard_mean, 4),
                   "attack": round(r.m7_attack_mean, 4)},
            "m9": {"benign": round(r.m9_benign_mean, 4),
                   "benign_hard": round(r.m9_benign_hard_mean, 4),
                   "attack": round(r.m9_attack_mean, 4)},
        },
        "single_factor": det_dict(r.single_factor),
        "dual_factor": det_dict(r.dual_factor),
        "dual_wins_fpr": r.dual_wins_fpr,
        "dual_wins_f1": r.dual_wins_f1,
    }


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def run_tests() -> bool:
    failures = []

    def check(name, cond, detail=""):
        if not cond:
            failures.append(f"FAIL [{name}]: {detail}")

    model = MicroGPT(n_layers=6, d_model=8, seed=0)
    benign, benign_hard, attack = generate_data(model, 60, 20, 10, seed=1)

    # Shape tests
    check("benign_shape", benign.shape == (60, 8), str(benign.shape))
    check("benign_hard_shape", benign_hard.shape == (10, 8), str(benign_hard.shape))
    check("attack_shape", attack.shape == (20, 8), str(attack.shape))

    # SAE trains
    sae = SAE(d_model=8, d_sae=16, seed=2)
    sae.train(benign, epochs=20)

    # Score shapes
    m7_b = compute_m7_scores(benign, sae, benign)
    m7_a = compute_m7_scores(attack, sae, benign)
    check("m7_benign_shape", m7_b.shape == (60,), str(m7_b.shape))
    check("m7_attack_shape", m7_a.shape == (20,), str(m7_a.shape))

    m9_b = compute_m9_scores(benign[:20], sae, benign)
    m9_a = compute_m9_scores(attack[:10], sae, benign)
    check("m9_benign_shape", m9_b.shape == (20,), str(m9_b.shape))
    check("m9_range_benign", ((m9_b >= 0) & (m9_b <= 2)).all(), str(m9_b.min()))
    check("m9_range_attack", ((m9_a >= 0) & (m9_a <= 2)).all(), str(m9_a.min()))

    # Detector evaluation
    preds = np.array([1, 0, 1, 0, 1])
    labels = np.array([1, 0, 0, 1, 1])
    r = evaluate_detector(preds, labels, "test")
    check("eval_tp", r.tp == 2, str(r.tp))
    check("eval_fp", r.fp == 1, str(r.fp))
    check("eval_fn", r.fn == 1, str(r.fn))
    check("eval_prec", abs(r.precision - 2/3) < 1e-5, str(r.precision))
    check("eval_recall", abs(r.recall - 2/3) < 1e-5, str(r.recall))

    # Full comparison runs
    try:
        rpt = run_comparison(n_benign=100, n_attack=40, n_benign_hard=20,
                             d_sae=16, seed=7)
        check("report_type", isinstance(rpt, ComparisonReport))
        check("single_f1_valid", 0 <= rpt.single_factor.f1 <= 1, str(rpt.single_factor.f1))
        check("dual_f1_valid", 0 <= rpt.dual_factor.f1 <= 1, str(rpt.dual_factor.f1))
        check("bool_fields", isinstance(rpt.dual_wins_fpr, bool))
    except Exception as e:
        failures.append(f"FAIL [run_comparison]: {e}")

    n_total = 3 + 2 + 2 + 4 + 5 + 4
    passed = n_total - len(failures)
    if failures:
        print(f"UNIT TEST RESULTS: FAIL ({passed}/{n_total})")
        for f in failures:
            print(f"  {f}")
        return False
    print(f"UNIT TEST RESULTS: PASS ({n_total}/{n_total})")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="M9-gated dual-factor adversarial detector comparison"
    )
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--n", type=int, default=500, help="Benign training samples")
    parser.add_argument("--n-attack", type=int, default=200)
    parser.add_argument("--n-hard", type=int, default=100,
                        help="Benign-hard samples (high M7, should NOT alert)")
    parser.add_argument("--d-sae", type=int, default=32)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.test:
        ok = run_tests()
        sys.exit(0 if ok else 1)

    rpt = run_comparison(
        n_benign=args.n,
        n_attack=args.n_attack,
        n_benign_hard=args.n_hard,
        d_sae=args.d_sae,
        seed=args.seed,
    )
    if args.json:
        print(json.dumps(to_json(rpt), indent=2))
    else:
        print_report(rpt)


if __name__ == "__main__":
    main()
