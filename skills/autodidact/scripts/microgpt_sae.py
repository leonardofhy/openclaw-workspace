#!/usr/bin/env python3
"""
Q052 — microgpt_sae.py
First fully-transparent phoneme SAE on microgpt activations.

Task: Train a Sparse Autoencoder (SAE) on the TinyPhonDASModel activations
(from microgpt_phon_das_suite.py). Identify sparse features that are
phoneme-selective (respond to voicing, place-of-articulation, or individual phonemes).

SAE architecture:
  Encoder: Linear(d_model, n_features) -> ReLU  (sparse bottleneck)
  Decoder: Linear(n_features, d_model)            (reconstruction)
  Loss:    MSE(reconstruction, input) + lambda_l1 * ||features||_1

Success criterion:
  >= 1 sparse feature that achieves selectivity_score >= 0.7 for any phoneme attribute
  (voicing or place-of-articulation) measured as mean_active_class / mean_other_class >= 2.0

Ground-truth circuit (TinyPhonDASModel):
  Layer 1, dim 0: dominant voicing feature (designed causal site)
  Embedding dim 0: voicing signal
  Embedding dims 1-2: place-of-articulation

Usage:
  python3 microgpt_sae.py [--layer 1] [--n-features 16] [--lambda-l1 0.01] [--epochs 2000]
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Import microgpt phoneme model (inline, no import dependency)
# ---------------------------------------------------------------------------

PHONEMES = ["p", "b", "t", "d", "k", "g"]
VOICING  = {"p": 0, "b": 1, "t": 0, "d": 1, "k": 0, "g": 1}
PLACE    = {"p": 0, "b": 0, "t": 1, "d": 1, "k": 2, "g": 2}  # 0=labial, 1=alveolar, 2=velar


class TinyPhonModel:
    """Deterministic residual stack with analytically-set phoneme embeddings."""

    def __init__(self, n_layers: int = 5, d_model: int = 4, seed: int = 42):
        self.n_layers = n_layers
        self.d_model = d_model

        # Embedding: dim0=voicing, dim1=place1, dim2=place2, dim3=bias
        self.emb = {
            "p": np.array([-1.0,  1.0,  0.0, 1.0], dtype=np.float32),
            "b": np.array([ 1.0,  1.0,  0.0, 1.0], dtype=np.float32),
            "t": np.array([-1.0,  0.0,  1.0, 1.0], dtype=np.float32),
            "d": np.array([ 1.0,  0.0,  1.0, 1.0], dtype=np.float32),
            "k": np.array([-1.0, -1.0, -1.0, 1.0], dtype=np.float32),
            "g": np.array([ 1.0, -1.0, -1.0, 1.0], dtype=np.float32),
        }

        rng = np.random.RandomState(seed)
        self.W = [rng.randn(d_model, d_model).astype(np.float32) * 0.08 for _ in range(n_layers)]
        self.b = [rng.randn(d_model).astype(np.float32) * 0.03 for _ in range(n_layers)]

    def activations_at_layer(self, phoneme: str, layer: int) -> np.ndarray:
        """Return hidden state after processing `layer` residual blocks."""
        h = self.emb[phoneme].copy()
        for k in range(layer + 1):
            h = h + np.tanh(self.W[k] @ h + self.b[k])
            if k == 1:
                h[0] *= 1.35  # designed causal site for voicing
        return h

    def all_layer_activations(self, phoneme: str) -> List[np.ndarray]:
        """Return activations at every layer [0..n_layers-1]."""
        h = self.emb[phoneme].copy()
        acts = []
        for k in range(self.n_layers):
            h = h + np.tanh(self.W[k] @ h + self.b[k])
            if k == 1:
                h[0] *= 1.35
            acts.append(h.copy())
        return acts


# ---------------------------------------------------------------------------
# SAE
# ---------------------------------------------------------------------------

class SparseAutoencoder:
    """
    Single-layer SAE: Linear(d_model -> n_features) -> ReLU -> Linear(n_features -> d_model).
    Trained with SGD + L1 penalty on feature activations.
    """

    def __init__(self, d_model: int, n_features: int, seed: int = 0):
        rng = np.random.RandomState(seed)
        scale = 1.0 / np.sqrt(d_model)
        self.W_enc = rng.randn(n_features, d_model).astype(np.float32) * scale
        self.b_enc = np.zeros(n_features, dtype=np.float32)
        self.W_dec = rng.randn(d_model, n_features).astype(np.float32) * scale
        self.b_dec = np.zeros(d_model, dtype=np.float32)
        # Normalize decoder columns to unit norm (standard SAE init)
        norms = np.linalg.norm(self.W_dec, axis=0, keepdims=True) + 1e-8
        self.W_dec /= norms

    def encode(self, x: np.ndarray) -> np.ndarray:
        """x: (d_model,) -> features: (n_features,) >= 0"""
        pre = self.W_enc @ x + self.b_enc
        return np.maximum(pre, 0.0)

    def decode(self, f: np.ndarray) -> np.ndarray:
        """f: (n_features,) -> x_hat: (d_model,)"""
        return self.W_dec @ f + self.b_dec

    def forward(self, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Returns (features, reconstruction)."""
        f = self.encode(x)
        x_hat = self.decode(f)
        return f, x_hat

    def loss(self, x: np.ndarray, lambda_l1: float) -> Tuple[float, np.ndarray, np.ndarray]:
        """Returns (total_loss, features, x_hat)."""
        f, x_hat = self.forward(x)
        mse = float(np.mean((x - x_hat) ** 2))
        l1  = float(np.mean(np.abs(f)))
        return mse + lambda_l1 * l1, f, x_hat

    def grad_step(self, x: np.ndarray, lambda_l1: float, lr: float) -> float:
        """In-place SGD step. Returns total loss."""
        f, x_hat = self.forward(x)
        mse = float(np.mean((x - x_hat) ** 2))
        l1  = float(np.sum(np.abs(f)))

        # dL/dx_hat = 2*(x_hat - x) / d_model
        d_xhat = 2.0 * (x_hat - x) / len(x)

        # Decoder grads
        dW_dec = np.outer(d_xhat, f)
        db_dec = d_xhat.copy()

        # Back through decoder → features
        df = self.W_dec.T @ d_xhat  # (n_features,)

        # L1 grad (subgradient)
        df += lambda_l1 * np.sign(f) / len(f)

        # Back through ReLU
        df_pre = df * (f > 0).astype(np.float32)

        # Encoder grads
        dW_enc = np.outer(df_pre, x)
        db_enc = df_pre.copy()

        # Update
        self.W_enc -= lr * dW_enc
        self.b_enc -= lr * db_enc
        self.W_dec -= lr * dW_dec
        self.b_dec -= lr * db_dec

        # Renormalize decoder columns
        norms = np.linalg.norm(self.W_dec, axis=0, keepdims=True) + 1e-8
        self.W_dec /= norms

        return mse + lambda_l1 * l1


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def collect_activations(model: TinyPhonModel, layer: int,
                         n_repeats: int = 200, noise_std: float = 0.02,
                         seed: int = 0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Build a dataset of (activation, phoneme_idx, voicing, place) by repeating
    each phoneme n_repeats times with small Gaussian noise to mimic variability.

    Returns: (X, y_phoneme, y_voicing, y_place)
    """
    rng = np.random.RandomState(seed)
    rows, yp, yv, ypl = [], [], [], []
    for ph_idx, ph in enumerate(PHONEMES):
        base = model.activations_at_layer(ph, layer)
        for _ in range(n_repeats):
            noisy = base + rng.randn(len(base)).astype(np.float32) * noise_std
            rows.append(noisy)
            yp.append(ph_idx)
            yv.append(VOICING[ph])
            ypl.append(PLACE[ph])
    X  = np.stack(rows)
    return X, np.array(yp), np.array(yv), np.array(ypl)


def train_sae(sae: SparseAutoencoder, X: np.ndarray,
              epochs: int = 2000, lr: float = 0.01, lambda_l1: float = 0.01,
              seed: int = 0) -> List[float]:
    rng = np.random.RandomState(seed)
    n = len(X)
    losses = []
    for epoch in range(epochs):
        idx = rng.permutation(n)
        ep_loss = 0.0
        for i in idx:
            ep_loss += sae.grad_step(X[i], lambda_l1, lr)
        losses.append(ep_loss / n)
    return losses


# ---------------------------------------------------------------------------
# Selectivity analysis
# ---------------------------------------------------------------------------

@dataclass
class FeatureSelectivity:
    feature_idx: int
    attribute: str         # "voicing", "place", or "phoneme"
    class_label: str       # e.g. "voiced", "labial", "p"
    selectivity_ratio: float  # mean_active_class / mean_other_class
    mean_active: float
    mean_other: float
    active_frac: float     # fraction of class samples that activate this feature (>0)


def compute_selectivity(sae: SparseAutoencoder, X: np.ndarray,
                         y_phoneme: np.ndarray, y_voicing: np.ndarray,
                         y_place: np.ndarray,
                         min_ratio: float = 2.0) -> List[FeatureSelectivity]:
    """
    For each SAE feature, compute selectivity ratio for:
      - voicing (0=voiceless, 1=voiced)
      - place (0=labial, 1=alveolar, 2=velar)
      - individual phoneme
    Return all feature-attribute pairs with ratio >= min_ratio.
    """
    n, n_features = len(X), sae.W_enc.shape[0]

    # Collect feature activations
    F = np.stack([sae.encode(X[i]) for i in range(n)])  # (n, n_features)

    results: List[FeatureSelectivity] = []

    def check(feat_idx: int, attr: str, label: str, mask: np.ndarray):
        active = F[mask, feat_idx]
        other  = F[~mask, feat_idx]
        m_act  = float(np.mean(active))
        m_oth  = float(np.mean(other)) + 1e-8
        ratio  = m_act / m_oth
        if ratio >= min_ratio and m_act > 1e-4:
            frac = float(np.mean(active > 0))
            results.append(FeatureSelectivity(
                feature_idx=feat_idx,
                attribute=attr,
                class_label=label,
                selectivity_ratio=ratio,
                mean_active=m_act,
                mean_other=m_oth - 1e-8,
                active_frac=frac,
            ))

    for fi in range(n_features):
        # Voicing
        check(fi, "voicing", "voiced",    y_voicing == 1)
        check(fi, "voicing", "voiceless", y_voicing == 0)
        # Place
        for place_id, pname in enumerate(["labial", "alveolar", "velar"]):
            check(fi, "place", pname, y_place == place_id)
        # Individual phoneme
        for ph_idx, ph in enumerate(PHONEMES):
            check(fi, "phoneme", ph, y_phoneme == ph_idx)

    # Sort by ratio descending
    results.sort(key=lambda r: r.selectivity_ratio, reverse=True)
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Q052 — microgpt SAE on phoneme activations")
    parser.add_argument("--layer",      type=int,   default=1,    help="Which model layer to extract activations from")
    parser.add_argument("--n-features", type=int,   default=16,   help="SAE bottleneck size")
    parser.add_argument("--lambda-l1",  type=float, default=0.01, help="L1 sparsity penalty")
    parser.add_argument("--epochs",     type=int,   default=2000, help="Training epochs")
    parser.add_argument("--lr",         type=float, default=0.02)
    parser.add_argument("--n-repeats",  type=int,   default=300,  help="Dataset repeats per phoneme")
    parser.add_argument("--noise-std",  type=float, default=0.02, help="Noise for data augmentation")
    parser.add_argument("--min-ratio",  type=float, default=2.0,  help="Min selectivity ratio to report")
    parser.add_argument("--seed",       type=int,   default=42)
    parser.add_argument("--verbose",    action="store_true")
    parser.add_argument("--json-out",   type=str,   default=None)
    args = parser.parse_args()

    t0 = time.time()
    print("=== Q052 — microgpt SAE: phoneme sparse features ===")
    print(f"Config: layer={args.layer}, n_features={args.n_features}, "
          f"lambda_l1={args.lambda_l1}, epochs={args.epochs}")
    print(f"Ground-truth circuit: Layer 1 dim-0 = voicing (designed causal site)")

    # --- Model ---
    model = TinyPhonModel(n_layers=5, d_model=4, seed=42)
    d_model = model.d_model

    # --- Data ---
    print(f"\nCollecting activations at layer {args.layer} "
          f"({len(PHONEMES)} phonemes × {args.n_repeats} repeats)...")
    X, y_ph, y_v, y_pl = collect_activations(
        model, layer=args.layer,
        n_repeats=args.n_repeats, noise_std=args.noise_std, seed=args.seed
    )
    print(f"Dataset: {len(X)} samples, d_model={d_model}")

    # Quick sanity: PCA-style variance check — is dim 0 most informative for voicing?
    voiced_mask = y_v == 1
    dim0_sep = abs(X[voiced_mask, 0].mean() - X[~voiced_mask, 0].mean())
    print(f"Dim-0 voicing separation (sanity): {dim0_sep:.3f} (expected > 1.0)")

    # --- SAE ---
    print(f"\nTraining SAE ({args.n_features} features, {args.epochs} epochs)...")
    sae = SparseAutoencoder(d_model=d_model, n_features=args.n_features, seed=args.seed)
    losses = train_sae(sae, X, epochs=args.epochs, lr=args.lr,
                       lambda_l1=args.lambda_l1, seed=args.seed)

    final_loss = losses[-1]
    # Reconstruction MSE only (no L1)
    F_all = np.stack([sae.encode(X[i]) for i in range(len(X))])
    X_hat = np.stack([sae.decode(F_all[i]) for i in range(len(X))])
    recon_mse = float(np.mean((X - X_hat) ** 2))
    sparsity  = float(np.mean(F_all == 0))
    print(f"Final loss: {final_loss:.4f} | Recon MSE: {recon_mse:.4f} | Sparsity: {sparsity:.2%}")

    if recon_mse > 0.5:
        print("WARNING: High reconstruction error — SAE may not have converged.")

    # --- Selectivity ---
    print(f"\nAnalyzing feature selectivity (min_ratio={args.min_ratio})...")
    selective = compute_selectivity(sae, X, y_ph, y_v, y_pl, min_ratio=args.min_ratio)

    print(f"\nSelective features found: {len(selective)}")
    if selective:
        print(f"\n{'Feat':>4}  {'Attribute':>10}  {'Class':>10}  {'Ratio':>6}  {'Mean_on':>8}  {'Frac_on':>7}")
        print("-" * 58)
        shown = set()
        for r in selective[:20]:
            key = (r.feature_idx, r.attribute, r.class_label)
            if key in shown:
                continue
            shown.add(key)
            print(f"{r.feature_idx:>4}  {r.attribute:>10}  {r.class_label:>10}  "
                  f"{r.selectivity_ratio:>6.2f}  {r.mean_active:>8.4f}  {r.active_frac:>7.2%}")

    # --- Highlight top voicing feature ---
    voicing_sel = [r for r in selective if r.attribute == "voicing"]
    place_sel    = [r for r in selective if r.attribute == "place"]
    phoneme_sel  = [r for r in selective if r.attribute == "phoneme"]

    print(f"\n--- Summary by attribute ---")
    print(f"  Voicing-selective features:  {len({r.feature_idx for r in voicing_sel})}")
    print(f"  Place-selective features:    {len({r.feature_idx for r in place_sel})}")
    print(f"  Phoneme-selective features:  {len({r.feature_idx for r in phoneme_sel})}")

    # Connection to ground truth: does any SAE feature activate on dim-0 direction?
    if voicing_sel:
        top = voicing_sel[0]
        enc_vec = sae.W_enc[top.feature_idx]  # (d_model,)
        # How aligned is this encoder direction with dim 0 (the voicing dimension)?
        dim0_unit = np.zeros(d_model); dim0_unit[0] = 1.0
        alignment = float(abs(np.dot(enc_vec / (np.linalg.norm(enc_vec) + 1e-8), dim0_unit)))
        print(f"\n  Top voicing feature (#{top.feature_idx}):")
        print(f"    Ratio = {top.selectivity_ratio:.2f}x | "
              f"Encoder alignment with dim-0 (voicing dim): {alignment:.3f}")
        print(f"    (alignment > 0.5 = feature partly represents ground-truth voicing circuit)")

    # --- Success criterion ---
    success = len(selective) >= 1 and (len(voicing_sel) > 0 or len(place_sel) > 0)
    t_total = time.time() - t0

    print(f"\n{'='*55}")
    print(f"Q052 RESULT: {'✅ PASS' if success else '❌ FAIL'}")
    if success:
        n_voicing = len({r.feature_idx for r in voicing_sel})
        n_place   = len({r.feature_idx for r in place_sel})
        print(f"  ≥1 sparse feature identified as phoneme-attribute-selective")
        print(f"  Voicing features: {n_voicing} | Place features: {n_place} | Phoneme features: {len({r.feature_idx for r in phoneme_sel})}")
    else:
        print(f"  No selective features found (check lambda_l1, epochs, min_ratio)")
    print(f"  Wall time: {t_total:.1f}s")

    # --- JSON output ---
    if args.json_out:
        out = {
            "config": vars(args),
            "recon_mse": round(recon_mse, 5),
            "sparsity": round(sparsity, 4),
            "selective_features_total": len(selective),
            "voicing_features": len({r.feature_idx for r in voicing_sel}),
            "place_features":   len({r.feature_idx for r in place_sel}),
            "phoneme_features": len({r.feature_idx for r in phoneme_sel}),
            "success": success,
            "top_features": [
                {
                    "feature_idx": r.feature_idx,
                    "attribute": r.attribute,
                    "class_label": r.class_label,
                    "selectivity_ratio": round(r.selectivity_ratio, 3),
                    "mean_active": round(r.mean_active, 5),
                    "active_frac": round(r.active_frac, 3),
                }
                for r in selective[:10]
            ],
        }
        with open(args.json_out, "w") as f:
            json.dump(out, f, indent=2)
        print(f"\nResults written to {args.json_out}")

    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
