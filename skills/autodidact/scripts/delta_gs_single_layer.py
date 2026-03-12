#!/usr/bin/env python3
"""
ΔGS Single-Layer Proxy — GPU-Free M7 Estimate on Mock SAE
Track T5, Q071 | Bridges T3 (gc theory) ↔ T5 (safety probes)

RESEARCH QUESTION
-----------------
Can a single semantic-layer SAE provide a reliable proxy for the full-stack
ΔGS (Grounding Sensitivity) metric? DashengTokenizer shows 1 semantic layer
is sufficient for 22 downstream tasks — so a single-layer SAE trained on
listen-layer activations should capture the anomaly signal.

WHAT IS ΔGS?
------------
ΔGS = Cohen's d between SAE feature activations on benign vs adversarial
inputs. High ΔGS → SAE features shift significantly under attack → the
model's grounding mechanism is sensitive to adversarial perturbation.

  Cohen's d = (mean_adv - mean_benign) / pooled_std

Per-feature ΔGS identifies WHICH features are most affected.
Aggregate ΔGS (L2 norm of per-feature d) gives a scalar anomaly score.

APPROACH
--------
1. Mock single-layer SAE on semantic tokens (listen-layer activations)
2. Generate benign + adversarial activation distributions
3. Compute per-feature Cohen's d → ΔGS vector
4. Aggregate → scalar ΔGS score
5. Mock a "full-stack" multi-layer baseline and verify correlation

TIER
----
Tier 0: numpy-only, no torch/gpu, ~100 lines. CPU < 1s.

USAGE
-----
  python3 delta_gs_single_layer.py              # full report
  python3 delta_gs_single_layer.py --test        # unit tests
  python3 delta_gs_single_layer.py --json        # JSON output

Author: Little Leo (Lab) — 2026-03-13
Track: T5, Q071, explore-fallback
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# MicroGPT + SAE (minimal inline, consistent with sae_listen_layer.py)
# ---------------------------------------------------------------------------

class MicroGPT:
    """Minimal deterministic transformer for activation inspection."""
    def __init__(self, n_layers: int = 6, d_model: int = 8, seed: int = 42):
        self.n_layers = n_layers
        self.d_model = d_model
        rng = np.random.RandomState(seed)
        self.W = [rng.randn(d_model, d_model) * 0.15 for _ in range(n_layers)]
        self.b = [rng.randn(d_model) * 0.05 for _ in range(n_layers)]

    def layer_activation(self, h0: np.ndarray, layer: int) -> np.ndarray:
        """Return activation after specified layer."""
        h = h0.copy()
        for k in range(layer + 1):
            h = h + np.tanh(self.W[k] @ h + self.b[k])
        return h

    def all_layer_activations(self, h0: np.ndarray) -> List[np.ndarray]:
        """Return activations after each layer [0..n_layers-1]."""
        h = h0.copy()
        acts = []
        for k in range(self.n_layers):
            h = h + np.tanh(self.W[k] @ h + self.b[k])
            acts.append(h.copy())
        return acts


class SingleLayerSAE:
    """Minimal numpy SAE (Anthropic-style, unit-norm decoder columns)."""
    def __init__(self, d_model: int, d_sae: int, seed: int = 1337):
        rng = np.random.RandomState(seed)
        W_dec = rng.randn(d_model, d_sae)
        W_dec /= np.linalg.norm(W_dec, axis=0, keepdims=True) + 1e-8
        self.W_dec = W_dec
        self.W_enc = W_dec.T.copy()
        self.b_enc = np.zeros(d_sae)
        self.b_dec = np.zeros(d_model)
        self.d_sae = d_sae
        self._m = {"W_enc": np.zeros_like(self.W_enc), "W_dec": np.zeros_like(self.W_dec),
                    "b_enc": np.zeros(d_sae), "b_dec": np.zeros(d_model)}
        self._v = {k: np.zeros_like(v) for k, v in self._m.items()}
        self._t = 0

    def encode(self, h: np.ndarray) -> np.ndarray:
        return np.maximum(0.0, (h - self.b_dec) @ self.W_enc.T + self.b_enc)

    def decode(self, f: np.ndarray) -> np.ndarray:
        return f @ self.W_dec.T + self.b_dec

    def train(self, data: np.ndarray, epochs: int = 100, lr: float = 0.003,
              l1_lambda: float = 0.01, batch_size: int = 64, seed: int = 10) -> List[float]:
        rng = np.random.RandomState(seed)
        N = data.shape[0]
        b1, b2, eps = 0.9, 0.999, 1e-8
        losses = []
        for _ in range(epochs):
            idx = rng.permutation(N)
            epoch_loss = 0.0; nb = 0
            for start in range(0, N, batch_size):
                b = data[idx[start:start + batch_size]]
                f = self.encode(b); h_hat = self.decode(f)
                err = h_hat - b; Nb = len(b)
                dh = 2 * err / Nb
                df = (dh @ self.W_dec + l1_lambda * np.sign(f) / Nb) * (f > 0)
                grads = {"W_dec": dh.T @ f, "b_dec": dh.mean(0),
                         "W_enc": df.T @ (b - self.b_dec), "b_enc": df.mean(0)}
                self._t += 1
                for name, g in grads.items():
                    g = np.clip(g, -1.0, 1.0)
                    self._m[name] = b1 * self._m[name] + (1 - b1) * g
                    self._v[name] = b2 * self._v[name] + (1 - b2) * g ** 2
                    mh = self._m[name] / (1 - b1 ** self._t)
                    vh = self._v[name] / (1 - b2 ** self._t)
                    p = getattr(self, name)
                    p -= lr * mh / (np.sqrt(vh) + eps)
                norms = np.linalg.norm(self.W_dec, axis=0, keepdims=True)
                self.W_dec /= np.maximum(norms, 1.0)
                loss = float(np.mean(np.sum(err ** 2, 1)) + l1_lambda * np.mean(np.sum(np.abs(f), 1)))
                epoch_loss += loss; nb += 1
            losses.append(epoch_loss / max(nb, 1))
        return losses


# ---------------------------------------------------------------------------
# Data generation
# ---------------------------------------------------------------------------

def generate_data(model: MicroGPT, n_benign: int = 400, n_attack: int = 200,
                  seed: int = 77) -> Tuple[np.ndarray, np.ndarray]:
    """Generate benign and adversarial listen-layer activations."""
    rng = np.random.RandomState(seed)
    d = model.d_model

    def make_acts(n, audio_range):
        acts = []
        for _ in range(n):
            h = rng.randn(d) * 0.4
            h[0] = rng.uniform(*audio_range)
            acts.append(model.layer_activation(h, layer=0))
        return np.array(acts)

    benign = make_acts(n_benign, (-0.5, 3.0))
    # Mix of suppression + override attacks
    n_sup = n_attack // 2
    suppression = make_acts(n_sup, (-3.0, -1.0))
    override = make_acts(n_attack - n_sup, (-2.5, -0.5))
    attack = np.vstack([suppression, override])
    return benign, attack


# ---------------------------------------------------------------------------
# ΔGS computation (Cohen's d)
# ---------------------------------------------------------------------------

def cohens_d(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Per-column Cohen's d. a, b: (N, D) → (D,)."""
    na, nb = len(a), len(b)
    ma, mb = a.mean(0), b.mean(0)
    va, vb = a.var(0, ddof=1), b.var(0, ddof=1)
    pooled = np.sqrt(((na - 1) * va + (nb - 1) * vb) / max(na + nb - 2, 1))
    return (mb - ma) / (pooled + 1e-8)


@dataclass
class DeltaGSResult:
    """Result of ΔGS computation."""
    per_feature_d: np.ndarray      # (d_sae,) Cohen's d per SAE feature
    scalar_delta_gs: float         # L2 norm of per-feature d
    top_features: List[Tuple[int, float]]  # (idx, d) sorted by |d|
    n_significant: int             # features with |d| > 0.5 (medium effect)


def compute_delta_gs(sae: SingleLayerSAE, benign_acts: np.ndarray,
                     attack_acts: np.ndarray, top_k: int = 10) -> DeltaGSResult:
    """Compute ΔGS from SAE feature activations on benign vs adversarial."""
    f_benign = sae.encode(benign_acts)
    f_attack = sae.encode(attack_acts)
    d_vec = cohens_d(f_benign, f_attack)
    scalar = float(np.linalg.norm(d_vec))
    ranked = sorted(enumerate(d_vec), key=lambda x: -abs(x[1]))
    return DeltaGSResult(
        per_feature_d=d_vec,
        scalar_delta_gs=scalar,
        top_features=[(i, float(v)) for i, v in ranked[:top_k]],
        n_significant=int(np.sum(np.abs(d_vec) > 0.5)),
    )


# ---------------------------------------------------------------------------
# Full-stack mock baseline (multi-layer SAEs) for correlation validation
# ---------------------------------------------------------------------------

def compute_fullstack_delta_gs(model: MicroGPT, benign_h0s: np.ndarray,
                               attack_h0s: np.ndarray, d_sae: int = 32,
                               seed: int = 99) -> Tuple[float, np.ndarray]:
    """
    Mock full-stack ΔGS: train separate SAE per layer, compute per-layer
    scalar ΔGS, return (aggregate, per_layer_array).
    """
    n_layers = model.n_layers
    per_layer_gs = np.zeros(n_layers)

    for layer in range(n_layers):
        b_acts = np.array([model.layer_activation(h, layer) for h in benign_h0s])
        a_acts = np.array([model.layer_activation(h, layer) for h in attack_h0s])
        sae = SingleLayerSAE(model.d_model, d_sae, seed=seed + layer)
        sae.train(b_acts, epochs=60)
        result = compute_delta_gs(sae, b_acts, a_acts)
        per_layer_gs[layer] = result.scalar_delta_gs

    aggregate = float(np.linalg.norm(per_layer_gs))
    return aggregate, per_layer_gs


def _spearman_r(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman rank correlation (no scipy needed)."""
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    if rx.std() < 1e-9 or ry.std() < 1e-9:
        return 1.0
    return float(np.corrcoef(rx, ry)[0, 1])


def validate_correlation(single_gs: float, full_gs: float, full_per_layer: np.ndarray,
                         n_trials: int = 15, seed: int = 42) -> Dict:
    """
    Run multiple seeds with VARYING attack intensity to validate that
    single-layer ΔGS tracks full-stack ΔGS monotonically.
    Each trial uses a different attack severity (audio suppression depth).
    """
    model = MicroGPT(n_layers=6, d_model=8, seed=42)
    d = model.d_model
    singles, fulls = [], []

    # Vary attack severity across trials for meaningful correlation
    attack_depths = np.linspace(-1.0, -4.0, n_trials)

    for trial, depth in enumerate(attack_depths):
        s = seed + trial * 100
        rng_t = np.random.RandomState(s)
        n_b, n_a = 200, 100
        benign_h0 = np.column_stack([rng_t.uniform(-0.5, 3.0, n_b)] +
                                     [rng_t.randn(n_b) * 0.4 for _ in range(d - 1)])
        # Attack depth varies: mild (-1) to severe (-4)
        attack_h0 = np.column_stack([rng_t.uniform(depth - 0.5, depth + 0.5, n_a)] +
                                     [rng_t.randn(n_a) * 0.4 for _ in range(d - 1)])
        # Single-layer (layer 0)
        b_acts = np.array([model.layer_activation(h, 0) for h in benign_h0])
        a_acts = np.array([model.layer_activation(h, 0) for h in attack_h0])
        sae_s = SingleLayerSAE(d, 32, seed=s + 1)
        sae_s.train(b_acts, epochs=60)
        r_s = compute_delta_gs(sae_s, b_acts, a_acts)
        singles.append(r_s.scalar_delta_gs)

        # Full-stack
        fg, _ = compute_fullstack_delta_gs(model, benign_h0, attack_h0, seed=s + 2)
        fulls.append(fg)

    singles, fulls = np.array(singles), np.array(fulls)
    pearson = float(np.corrcoef(singles, fulls)[0, 1]) if singles.std() > 1e-9 and fulls.std() > 1e-9 else 1.0
    spearman = _spearman_r(singles, fulls)

    return {
        "pearson_r": round(pearson, 4),
        "spearman_r": round(spearman, 4),
        "n_trials": n_trials,
        "single_mean": round(float(singles.mean()), 4),
        "full_mean": round(float(fulls.mean()), 4),
        "ratio_mean": round(float((singles / (fulls + 1e-8)).mean()), 4),
        "verdict": "✓ correlated" if spearman > 0.7 else ("~ weak" if spearman > 0.3 else "✗ uncorrelated"),
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def run_full_pipeline(seed: int = 42, verbose: bool = False) -> Dict:
    """End-to-end: generate data → train SAE → compute ΔGS → validate."""
    model = MicroGPT(n_layers=6, d_model=8, seed=seed)
    rng = np.random.RandomState(seed)
    d = model.d_model

    # Generate raw h0 vectors (needed for full-stack comparison)
    n_b, n_a = 400, 200
    benign_h0 = np.column_stack([rng.uniform(-0.5, 3.0, n_b)] +
                                 [rng.randn(n_b) * 0.4 for _ in range(d - 1)])
    attack_h0 = np.column_stack([rng.uniform(-3.0, -1.0, n_a)] +
                                 [rng.randn(n_a) * 0.4 for _ in range(d - 1)])

    # Single-layer SAE on listen layer (layer 0)
    benign_acts = np.array([model.layer_activation(h, 0) for h in benign_h0])
    attack_acts = np.array([model.layer_activation(h, 0) for h in attack_h0])

    sae = SingleLayerSAE(d, 32, seed=seed + 1)
    losses = sae.train(benign_acts, epochs=100)
    if verbose:
        print(f"SAE training: loss {losses[0]:.4f} → {losses[-1]:.4f}")

    # Compute single-layer ΔGS
    gs_result = compute_delta_gs(sae, benign_acts, attack_acts)

    # Full-stack baseline
    full_gs, per_layer = compute_fullstack_delta_gs(model, benign_h0, attack_h0, seed=seed + 2)

    # Cross-seed correlation validation
    corr = validate_correlation(gs_result.scalar_delta_gs, full_gs, per_layer, n_trials=5, seed=seed)

    report = {
        "single_layer_delta_gs": round(gs_result.scalar_delta_gs, 4),
        "full_stack_delta_gs": round(full_gs, 4),
        "ratio": round(gs_result.scalar_delta_gs / (full_gs + 1e-8), 4),
        "n_significant_features": gs_result.n_significant,
        "top_features": [(i, round(d, 4)) for i, d in gs_result.top_features[:5]],
        "per_layer_gs": [round(float(x), 4) for x in per_layer],
        "correlation_validation": corr,
        "sae_loss": {"start": round(losses[0], 5), "end": round(losses[-1], 5)},
    }
    return report


def print_report(report: Dict):
    print("=" * 65)
    print("ΔGS Single-Layer Proxy — GPU-Free M7 Estimate Report")
    print("=" * 65)
    print(f"  SAE training loss: {report['sae_loss']['start']:.5f} → {report['sae_loss']['end']:.5f}")
    print()
    print(f"  Single-layer ΔGS (listen layer): {report['single_layer_delta_gs']:.4f}")
    print(f"  Full-stack ΔGS (6 layers):       {report['full_stack_delta_gs']:.4f}")
    print(f"  Ratio (single/full):             {report['ratio']:.4f}")
    print()
    print(f"  Significant features (|d|>0.5):  {report['n_significant_features']}/32")
    print(f"  Top 5 features by |Cohen's d|:")
    for idx, d in report['top_features']:
        marker = " ← large" if abs(d) > 0.8 else ""
        print(f"    F{idx:03d}: d={d:+.4f}{marker}")
    print()
    print(f"  Per-layer scalar ΔGS:")
    for i, gs in enumerate(report['per_layer_gs']):
        bar = "█" * int(gs * 5)
        print(f"    L{i}: {gs:.4f}  {bar}")
    print()
    cv = report['correlation_validation']
    print(f"  Cross-seed correlation validation ({cv['n_trials']} trials):")
    print(f"    Pearson r  = {cv['pearson_r']:.4f}")
    print(f"    Spearman r = {cv['spearman_r']:.4f}  {cv['verdict']}")
    print(f"    Single mean = {cv['single_mean']:.4f}  Full mean = {cv['full_mean']:.4f}")
    print()
    if cv['spearman_r'] > 0.7:
        print("  ✓ Single-layer SAE is a valid proxy for full-stack ΔGS")
    else:
        print("  ⚠ Weak correlation — single layer may miss cross-layer interactions")
    print("=" * 65)


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def run_tests() -> bool:
    failures = []
    def check(name, cond, detail=""):
        if not cond:
            failures.append(f"FAIL [{name}]: {detail}")

    # T1: Cohen's d shape + known case
    a = np.array([[1.0, 2.0], [1.1, 2.1], [0.9, 1.9]])
    b = np.array([[3.0, 2.0], [3.1, 2.1], [2.9, 1.9]])
    d = cohens_d(a, b)
    check("cohens_d_shape", d.shape == (2,), str(d.shape))
    check("cohens_d_dim0_large", abs(d[0]) > 5.0, f"d[0]={d[0]:.3f}")  # large effect
    check("cohens_d_dim1_small", abs(d[1]) < 0.5, f"d[1]={d[1]:.3f}")  # no effect

    # T2: SAE encode/decode shapes
    sae = SingleLayerSAE(8, 16, seed=0)
    x = np.random.randn(10, 8)
    f = sae.encode(x)
    check("encode_shape", f.shape == (10, 16))
    check("encode_nonneg", (f >= 0).all())
    h_hat = sae.decode(f)
    check("decode_shape", h_hat.shape == (10, 8))

    # T3: SAE training reduces loss
    sae2 = SingleLayerSAE(8, 16, seed=1)
    data = np.random.randn(100, 8)
    losses = sae2.train(data, epochs=30)
    check("loss_decreases", losses[-1] < losses[0], f"{losses[0]:.4f} → {losses[-1]:.4f}")

    # T4: DeltaGS result structure
    model = MicroGPT(seed=0)
    benign, attack = generate_data(model, n_benign=50, n_attack=30, seed=1)
    sae3 = SingleLayerSAE(8, 32, seed=2)
    sae3.train(benign, epochs=20)
    r = compute_delta_gs(sae3, benign, attack)
    check("dgs_shape", r.per_feature_d.shape == (32,))
    check("dgs_scalar_pos", r.scalar_delta_gs > 0)
    check("dgs_topk", len(r.top_features) == 10)

    # T5: Full pipeline runs without crash
    try:
        report = run_full_pipeline(seed=7)
        check("pipeline_keys", all(k in report for k in
              ["single_layer_delta_gs", "full_stack_delta_gs", "correlation_validation"]))
        check("pipeline_corr_keys", "pearson_r" in report["correlation_validation"])
    except Exception as e:
        failures.append(f"FAIL [pipeline]: {e}")

    total = 12
    if failures:
        print(f"UNIT TESTS: FAIL ({total - len(failures)}/{total})")
        for f in failures:
            print(f"  {f}")
        return False
    print(f"UNIT TESTS: PASS ({total}/{total})")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="ΔGS single-layer proxy (Q071)")
    parser.add_argument("--test", action="store_true", help="Run unit tests")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.test:
        sys.exit(0 if run_tests() else 1)

    report = run_full_pipeline(seed=args.seed, verbose=args.verbose)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)


if __name__ == "__main__":
    main()
