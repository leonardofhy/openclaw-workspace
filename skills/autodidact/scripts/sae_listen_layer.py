#!/usr/bin/env python3
"""
SAE on MicroGPT Listen-Layer — Design Doc + Scaffold
Track T3+T5: Which SAE features align with the gc(k) phase boundary?

RESEARCH QUESTION
-----------------
gc(k) identifies *where* audio evidence enters the residual stream (the
"listen layer"). But gc(k) tells us WHEN, not WHAT. Sparse autoencoders
(SAEs) tell us WHAT features are active. Combining them:

  "Which SAE features at the listen layer are causally responsible for
   the gc(k) signal? Are these features interpretable as phonological /
   acoustic evidence vs language-prior tokens?"

DESIGN
------
1. Data generation: sample many (h_clean, h_noisy) pairs from MicroGPT,
   varying the audio signal strength continuously (not just binary).
2. Collect listen-layer activations (layer 0 output, post-residual) for
   each sample. This gives us a dataset of shape (N, d_model).
3. Train a sparse autoencoder (SAE) on these activations:
     Encoder: f = ReLU(W_enc @ h + b_enc)   (f: sparse feature vector, d_sae >> d_model)
     Decoder: h_hat = W_dec @ f + b_dec
     Loss: reconstruction_loss + lambda * L1(f)
4. For each sample, compute gc(0) (gc value at layer 0).
5. Correlate each SAE feature dimension with gc(0):
     Pearson correlation → "gc-predictive features"
6. Report top features; visualize their decoder columns (which residual
   stream directions they write to).

HYPOTHESIS
----------
A small number of SAE features (< 10% of d_sae) will have strong positive
correlation with gc(0). These are the "audio evidence features". The rest
are noise / language-prior features. This directly links interpretability
(SAE features) to the causal metric (gc).

TIER
----
Tier 0 (scaffold + design doc) — pure numpy, no model download needed.
Tier 1 (full training) — CPU <5min when d_sae <= 64, N <= 2000. Auto-allowed.
Tier 2 (real Whisper activations) — needs Leo approval + venv.

USAGE
-----
  python3 sae_listen_layer.py                 # train SAE + correlation report
  python3 sae_listen_layer.py --test          # unit tests
  python3 sae_listen_layer.py --n 2000 --epochs 200   # larger run
  python3 sae_listen_layer.py --d-sae 64      # wider dictionary
  python3 sae_listen_layer.py --json          # JSON output (for pipeline use)

Author: Little Leo (Lab) — 2026-03-09
Track: T3+T5, Q007, converge phase
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Re-use MicroGPT (inline minimal version to avoid import dependency)
# ---------------------------------------------------------------------------

class MicroGPT:
    """Minimal deterministic transformer for activation inspection (see microgpt_gc_eval.py)."""

    def __init__(self, n_layers: int = 6, d_model: int = 8, seed: int = 42):
        self.n_layers = n_layers
        self.d_model = d_model
        rng = np.random.RandomState(seed)
        self.W = [rng.randn(d_model, d_model) * 0.15 for _ in range(n_layers)]
        self.b = [rng.randn(d_model) * 0.05 for _ in range(n_layers)]
        self.W_out = rng.randn(d_model) * 0.3

    def forward(self, h0: np.ndarray, record_activations: bool = False):
        h = h0.copy()
        acts = [h.copy()] if record_activations else []
        for k in range(self.n_layers):
            h = h + np.tanh(self.W[k] @ h + self.b[k])
            if record_activations:
                acts.append(h.copy())
        return float(self.W_out @ h), acts

    def patched_forward(self, h0_base, clean_acts, patch_layer):
        h = h0_base.copy()
        for k in range(self.n_layers):
            h = h + np.tanh(self.W[k] @ h + self.b[k])
            if k == patch_layer:
                h = clean_acts[k + 1].copy()
        return float(self.W_out @ h)


def compute_gc0(model: MicroGPT, h_clean: np.ndarray, h_noisy: np.ndarray) -> float:
    """Compute gc(k=0): causal contribution of layer 0 to the audio-vs-noise delta."""
    logit_clean, clean_acts = model.forward(h_clean, record_activations=True)
    logit_noisy, _ = model.forward(h_noisy)
    delta = logit_clean - logit_noisy
    if abs(delta) < 1e-9:
        return 0.0
    lp = model.patched_forward(h_noisy, clean_acts, patch_layer=0)
    return float(np.clip((lp - logit_noisy) / delta, 0.0, 1.0))


# ---------------------------------------------------------------------------
# Data generation: continuous audio signal strength
# ---------------------------------------------------------------------------

def generate_dataset(
    model: MicroGPT,
    n_samples: int = 500,
    seed: int = 99,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate dataset of (listen-layer activations, audio_strength values).

    For each sample:
    - Draw base h from N(0, 0.5)
    - Draw audio_strength from Uniform(-1, 3)  (negative = noise, positive = listen signal)
    - h_input[0] = audio_strength (varies continuously; 0 = no audio evidence)
    - Collect activation AFTER layer 0 residual (h_after_L0)
    - Label = audio_strength (proxy for "how much audio evidence is present")

    Note: In MicroGPT, gc(0) = 1.0 whenever delta_total ≠ 0 (by design — layer 0
    captures 100% of the signal). The meaningful signal to explain SAE features is
    therefore audio_strength itself, which varies continuously and drives dim 0 of h.
    This is the right proxy for the real-Whisper experiment where gc(0) will vary.

    Returns:
        activations: (N, d_model) — listen-layer activations for each sample
        audio_strengths: (N,)     — continuous proxy for audio evidence strength
    """
    rng = np.random.RandomState(seed)
    d = model.d_model
    activations = []
    strengths = []

    for _ in range(n_samples):
        h_input = rng.randn(d) * 0.5
        audio_strength = rng.uniform(-1.0, 3.0)
        h_input[0] = audio_strength

        # Get listen-layer activation (after layer 0)
        _, acts = model.forward(h_input, record_activations=True)
        act_L0 = acts[1]  # acts[0]=h0, acts[1]=after layer 0

        activations.append(act_L0)
        strengths.append(audio_strength)

    return np.array(activations), np.array(strengths)


# ---------------------------------------------------------------------------
# Sparse Autoencoder (SAE)
# ---------------------------------------------------------------------------

@dataclass
class SAEConfig:
    d_model: int = 8
    d_sae: int = 32        # dictionary size (>= d_model; typically 4-8x)
    l1_lambda: float = 0.01
    lr: float = 0.003
    epochs: int = 100
    batch_size: int = 64
    seed: int = 1337


class SAE:
    """
    Minimal Sparse Autoencoder (numpy, no pytorch needed for scaffold).

    Architecture:
        Encoder: f = ReLU(W_enc @ (h - b_dec) + b_enc)
        Decoder: h_hat = W_dec @ f + b_dec   (columns of W_dec normalized)
        Loss: ||h - h_hat||^2 + lambda * sum(|f|)

    Note: We normalize decoder columns to ||W_dec[:, i]||_2 = 1 to prevent
    feature collapse (the "shrinkage" problem). This is the Anthropic-style
    tied-norm SAE.

    Training: mini-batch SGD with gradient clipping.
    """

    def __init__(self, cfg: SAEConfig):
        self.cfg = cfg
        rng = np.random.RandomState(cfg.seed)
        d, d_sae = cfg.d_model, cfg.d_sae

        # Initialize W_dec columns on unit sphere
        W_dec = rng.randn(d, d_sae)
        W_dec /= np.linalg.norm(W_dec, axis=0, keepdims=True) + 1e-8
        self.W_dec = W_dec

        # W_enc = W_dec.T (tied initialization, not tied parameters)
        self.W_enc = W_dec.T.copy()
        self.b_enc = np.zeros(d_sae)
        self.b_dec = np.zeros(d)

        # Adam optimizer state
        self._m = {k: np.zeros_like(v) for k, v in self._params().items()}
        self._v = {k: np.zeros_like(v) for k, v in self._params().items()}
        self._t = 0

    def _params(self):
        return {
            "W_enc": self.W_enc,
            "W_dec": self.W_dec,
            "b_enc": self.b_enc,
            "b_dec": self.b_dec,
        }

    def encode(self, h: np.ndarray) -> np.ndarray:
        """h: (N, d_model) → f: (N, d_sae)"""
        pre = (h - self.b_dec) @ self.W_enc.T + self.b_enc  # (N, d_sae)
        return np.maximum(0.0, pre)

    def decode(self, f: np.ndarray) -> np.ndarray:
        """f: (N, d_sae) → h_hat: (N, d_model)"""
        return f @ self.W_dec.T + self.b_dec  # (N, d_model)

    def loss(self, h: np.ndarray) -> Tuple[float, np.ndarray]:
        """Returns (scalar_loss, f) for a batch."""
        f = self.encode(h)
        h_hat = self.decode(f)
        rec_loss = np.mean(np.sum((h - h_hat) ** 2, axis=1))
        l1_loss = self.cfg.l1_lambda * np.mean(np.sum(np.abs(f), axis=1))
        return rec_loss + l1_loss, f

    def _normalize_decoder(self):
        """Renormalize decoder columns to unit norm (post-step)."""
        norms = np.linalg.norm(self.W_dec, axis=0, keepdims=True)
        self.W_dec /= np.maximum(norms, 1.0)  # only normalize if > 1

    def train(self, data: np.ndarray, verbose: bool = False) -> List[float]:
        """
        Train SAE on data (N, d_model). Returns loss history.
        Uses Adam with gradient clipping.
        """
        cfg = self.cfg
        N = data.shape[0]
        rng = np.random.RandomState(cfg.seed + 10)
        losses = []

        beta1, beta2, eps = 0.9, 0.999, 1e-8

        for epoch in range(cfg.epochs):
            idx = rng.permutation(N)
            epoch_loss = 0.0
            n_batches = 0

            for start in range(0, N, cfg.batch_size):
                batch = data[idx[start:start + cfg.batch_size]]
                grads = self._compute_grads(batch)

                self._t += 1
                for name, g in grads.items():
                    # Gradient clip
                    g = np.clip(g, -1.0, 1.0)
                    self._m[name] = beta1 * self._m[name] + (1 - beta1) * g
                    self._v[name] = beta2 * self._v[name] + (1 - beta2) * g ** 2
                    m_hat = self._m[name] / (1 - beta1 ** self._t)
                    v_hat = self._v[name] / (1 - beta2 ** self._t)
                    param = getattr(self, name)
                    param -= cfg.lr * m_hat / (np.sqrt(v_hat) + eps)

                self._normalize_decoder()
                loss_val, _ = self.loss(batch)
                epoch_loss += loss_val
                n_batches += 1

            avg_loss = epoch_loss / max(n_batches, 1)
            losses.append(avg_loss)
            if verbose and (epoch % 20 == 0 or epoch == cfg.epochs - 1):
                print(f"  epoch {epoch:>4}/{cfg.epochs}  loss={avg_loss:.5f}")

        return losses

    def _compute_grads(self, h: np.ndarray) -> dict:
        """Numerical-gradient-free backprop (analytic, no autograd needed)."""
        N = h.shape[0]
        f = self.encode(h)                      # (N, d_sae)
        h_hat = self.decode(f)                  # (N, d_model)
        rec_err = h_hat - h                     # (N, d_model)

        # Gradient of reconstruction loss
        dL_dh_hat = 2 * rec_err / N             # (N, d_model)
        dL_df_from_rec = dL_dh_hat @ self.W_dec # (N, d_sae)

        # Gradient of L1 regularization
        dL_df_from_l1 = self.cfg.l1_lambda * np.sign(f) / N  # (N, d_sae)

        dL_df = dL_df_from_rec + dL_df_from_l1  # (N, d_sae)

        # Gate by ReLU (only active features get gradient)
        active = (f > 0).astype(float)
        dL_df_gated = dL_df * active             # (N, d_sae)

        # Decoder gradients
        # h_hat = f @ W_dec.T + b_dec  → W_dec: (d_model, d_sae)
        # dL/dW_dec[:, i] = sum_n dL_dh_hat[n] * f[n, i]
        # Matrix form: dL/dW_dec = dL_dh_hat.T @ f  → (d_model, d_sae) ✓
        dL_dW_dec = dL_dh_hat.T @ f             # (d_model, d_sae)
        dL_db_dec = dL_dh_hat.mean(axis=0)      # (d_model,)

        # Encoder gradients
        # pre = (h - b_dec) @ W_enc.T + b_enc
        # dL/dW_enc = dL_df_gated.T @ (h - b_dec)  (d_sae, d_model)
        h_centered = h - self.b_dec
        dL_dW_enc = dL_df_gated.T @ h_centered  # (d_sae, d_model)
        dL_db_enc = dL_df_gated.mean(axis=0)    # (d_sae,)

        return {
            "W_dec": dL_dW_dec,
            "b_dec": dL_db_dec,
            "W_enc": dL_dW_enc,
            "b_enc": dL_db_enc,
        }


# ---------------------------------------------------------------------------
# Correlation analysis: which SAE features predict gc(0)?
# ---------------------------------------------------------------------------

@dataclass
class FeatureCorrelation:
    feature_idx: int
    pearson_r: float
    mean_activation: float
    sparsity: float          # fraction of samples where feature == 0
    decoder_col: np.ndarray  # d_model direction this feature writes to

    def __repr__(self):
        return (
            f"F{self.feature_idx:03d}: r={self.pearson_r:+.3f}  "
            f"mean={self.mean_activation:.4f}  "
            f"sparsity={self.sparsity:.2f}"
        )


def correlate_features_with_gc(
    sae: SAE,
    activations: np.ndarray,
    gc0_values: np.ndarray,
) -> List[FeatureCorrelation]:
    """
    For each SAE feature, compute Pearson correlation with gc(0).

    Returns list sorted by |pearson_r| descending.
    """
    features = sae.encode(activations)  # (N, d_sae)
    results = []

    for i in range(sae.cfg.d_sae):
        f_i = features[:, i]
        # Pearson r
        f_std = f_i.std()
        gc_std = gc0_values.std()
        if f_std < 1e-9 or gc_std < 1e-9:
            r = 0.0
        else:
            r = float(np.corrcoef(f_i, gc0_values)[0, 1])

        results.append(FeatureCorrelation(
            feature_idx=i,
            pearson_r=r,
            mean_activation=float(f_i.mean()),
            sparsity=float((f_i == 0.0).mean()),
            decoder_col=sae.W_dec[:, i].copy(),
        ))

    results.sort(key=lambda x: -abs(x.pearson_r))
    return results


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def make_report(
    correlations: List[FeatureCorrelation],
    gc0_values: np.ndarray,
    losses: List[float],
    cfg: SAEConfig,
    top_k: int = 10,
) -> dict:
    top = correlations[:top_k]
    gc_predictive = [c for c in correlations if abs(c.pearson_r) >= 0.3]

    report = {
        "sae_config": {
            "d_model": cfg.d_model,
            "d_sae": cfg.d_sae,
            "l1_lambda": cfg.l1_lambda,
            "epochs": cfg.epochs,
        },
        "training": {
            "final_loss": round(losses[-1], 6),
            "loss_drop": round(losses[0] - losses[-1], 6),
        },
        "signal_stats": {
            "label": "audio_strength (proxy for gc(0) in MicroGPT; real gc(0) varies in Whisper)",
            "mean": round(float(gc0_values.mean()), 4),
            "std": round(float(gc0_values.std()), 4),
            "frac_positive": round(float((gc0_values > 0).mean()), 4),
        },
        "feature_analysis": {
            "n_gc_predictive_r_ge_0.3": len(gc_predictive),
            "pct_gc_predictive": round(100 * len(gc_predictive) / cfg.d_sae, 1),
            "top_features": [
                {
                    "idx": c.feature_idx,
                    "pearson_r": round(c.pearson_r, 4),
                    "mean_activation": round(c.mean_activation, 5),
                    "sparsity": round(c.sparsity, 3),
                    "decoder_norm": round(float(np.linalg.norm(c.decoder_col)), 4),
                }
                for c in top
            ],
        },
        "interpretation": {
            "hypothesis": "A small fraction of SAE features predict gc(0) → these are 'audio evidence features'",
            "result": (
                f"{len(gc_predictive)}/{cfg.d_sae} features have |r| >= 0.3 "
                f"({100 * len(gc_predictive) / cfg.d_sae:.1f}%). "
                + ("Hypothesis supported: sparse feature set." if len(gc_predictive) < cfg.d_sae * 0.3
                   else "More features than expected; try higher l1_lambda.")
            ),
            "next_step": "Apply to real Whisper listen-layer activations (needs Leo venv + real speech .wav)",
        },
    }
    return report


def print_report(report: dict):
    print("=" * 65)
    print("SAE on MicroGPT Listen-Layer — Feature-gc(0) Correlation Report")
    print("=" * 65)
    cfg = report["sae_config"]
    print(f"  SAE: d_model={cfg['d_model']}  d_sae={cfg['d_sae']}  "
          f"λ={cfg['l1_lambda']}  epochs={cfg['epochs']}")
    tr = report["training"]
    print(f"  Training: loss {tr['final_loss']:.5f}  (drop={tr['loss_drop']:.5f})")
    gs = report["signal_stats"]
    print(f"  Audio strength distribution: mean={gs['mean']}  std={gs['std']}  "
          f"frac_positive={gs['frac_positive']}")
    print()

    fa = report["feature_analysis"]
    print(f"  gc-predictive features (|r|≥0.3): "
          f"{fa['n_gc_predictive_r_ge_0.3']}/{cfg['d_sae']} "
          f"({fa['pct_gc_predictive']}%)")
    print()
    print(f"  Top {len(fa['top_features'])} features by |Pearson r|:")
    print(f"  {'Feat':>5}  {'r':>7}  {'mean_act':>9}  {'sparsity':>9}  {'dec_norm':>9}")
    for f in fa["top_features"]:
        marker = "  ← audio evidence" if f["pearson_r"] >= 0.3 else ""
        print(f"  F{f['idx']:>4}  {f['pearson_r']:>+7.4f}  "
              f"{f['mean_activation']:>9.5f}  {f['sparsity']:>9.3f}  "
              f"{f['decoder_norm']:>9.4f}{marker}")
    print()
    interp = report["interpretation"]
    print(f"  Interpretation: {interp['result']}")
    print(f"  Next step: {interp['next_step']}")
    print("=" * 65)


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def run_tests() -> bool:
    failures = []

    def check(name, cond, detail=""):
        if not cond:
            failures.append(f"FAIL [{name}]: {detail}")

    # Test 1: SAE encodes + decodes shape
    cfg = SAEConfig(d_model=8, d_sae=16, epochs=5)
    sae = SAE(cfg)
    x = np.random.randn(10, 8)
    f = sae.encode(x)
    check("encode_shape", f.shape == (10, 16), f"{f.shape}")
    h_hat = sae.decode(f)
    check("decode_shape", h_hat.shape == (10, 8), f"{h_hat.shape}")

    # Test 2: Features are non-negative (ReLU)
    check("relu_nonneg", (f >= 0).all(), f"min={f.min()}")

    # Test 3: Training reduces loss
    cfg2 = SAEConfig(d_model=8, d_sae=16, epochs=30, lr=0.005)
    sae2 = SAE(cfg2)
    data = np.random.randn(200, 8)
    losses = sae2.train(data)
    check("loss_decreases", losses[-1] < losses[0],
          f"loss_0={losses[0]:.4f} loss_end={losses[-1]:.4f}")

    # Test 4: Data generation produces correct shapes
    model = MicroGPT(n_layers=6, d_model=8, seed=42)
    acts, gc0s = generate_dataset(model, n_samples=50)
    check("acts_shape", acts.shape == (50, 8), f"{acts.shape}")
    check("signal_range", ((gc0s >= -1.1) & (gc0s <= 3.1)).all(), f"range=[{gc0s.min():.3f},{gc0s.max():.3f}]")

    # Test 5: Correlation output has expected structure
    cfg3 = SAEConfig(d_model=8, d_sae=16, epochs=10)
    sae3 = SAE(cfg3)
    sae3.train(acts)
    corrs = correlate_features_with_gc(sae3, acts, gc0s)
    check("corr_length", len(corrs) == 16, f"len={len(corrs)}")
    check("corr_sorted", abs(corrs[0].pearson_r) >= abs(corrs[-1].pearson_r), "not sorted")
    check("corr_r_range",
          all(-1.0 <= c.pearson_r <= 1.0 for c in corrs),
          f"out-of-range r values")

    if failures:
        print("UNIT TEST RESULTS: FAIL")
        for f in failures:
            print(f"  {f}")
        return False

    print(f"UNIT TEST RESULTS: PASS ({5 + 2 + 3}/ 10)")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="SAE on MicroGPT listen-layer: feature–gc(k) correlation analysis"
    )
    parser.add_argument("--test", action="store_true", help="Run unit tests and exit")
    parser.add_argument("--n", type=int, default=500, help="Number of training samples")
    parser.add_argument("--d-sae", type=int, default=32, help="SAE dictionary size")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--l1", type=float, default=0.01, help="L1 regularization lambda")
    parser.add_argument("--lr", type=float, default=0.003)
    parser.add_argument("--top-k", type=int, default=10, help="Top features to show")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.test:
        ok = run_tests()
        sys.exit(0 if ok else 1)

    # Step 1: Build MicroGPT
    model = MicroGPT(n_layers=6, d_model=8, seed=args.seed)

    # Step 2: Generate dataset
    if not args.json:
        print(f"Generating {args.n} samples...", flush=True)
    activations, gc0_values = generate_dataset(model, n_samples=args.n, seed=args.seed + 1)

    # Step 3: Train SAE
    cfg = SAEConfig(
        d_model=model.d_model,
        d_sae=args.d_sae,
        l1_lambda=args.l1,
        lr=args.lr,
        epochs=args.epochs,
        seed=args.seed + 2,
    )
    sae = SAE(cfg)

    if not args.json:
        print(f"Training SAE (d_sae={args.d_sae}, λ={args.l1}, epochs={args.epochs})...", flush=True)
    losses = sae.train(activations, verbose=args.verbose)

    # Step 4: Correlate features with gc(0)
    correlations = correlate_features_with_gc(sae, activations, gc0_values)

    # Step 5: Report
    report = make_report(correlations, gc0_values, losses, cfg, top_k=args.top_k)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)


if __name__ == "__main__":
    main()
