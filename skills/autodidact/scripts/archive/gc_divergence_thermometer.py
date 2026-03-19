#!/usr/bin/env python3
"""
gc(k) Divergence Thermometer — Tier 0 (CPU-only, no model needed)
Track T3+T5: gc(k) as jailbreak thermometer

PURPOSE
-------
The classifier (gc_jailbreak_classifier.py) operates on a single sample.
This script operates on POPULATIONS:

  Given N_benign gc(k) curves and N_jailbreak gc(k) curves,
  compute per-layer Jensen–Shannon divergence (JSD) between the two
  distributions → identify which layers are most diagnostic.

This is the "thermometer reading": a per-layer heatmap of how much the
benign vs jailbreak populations diverge at each transformer layer.

HYPOTHESIS
----------
The jailbreak signal concentrates in decoder layers (low gc(k) collapse).
JSD should spike in decoder-middle layers, NOT early encoder layers.
This would confirm that jailbreak detection can be a lightweight probe
on mid-to-late decoder activations only.

USAGE
-----
  python3 gc_divergence_thermometer.py --mock           # synthetic baseline
  python3 gc_divergence_thermometer.py --mock --n 100   # larger sample
  python3 gc_divergence_thermometer.py --mock --plot    # print ASCII heatmap
  python3 gc_divergence_thermometer.py --file curves.json  # real gc(k) curves JSON

INPUT FORMAT (--file)
---------------------
JSON with two keys:
{
  "benign":    [ {"layers": [...], "gc_values": [...], "n_encoder_layers": 6}, ... ],
  "jailbreak": [ {"layers": [...], "gc_values": [...], "n_encoder_layers": 6}, ... ]
}

OUTPUT
------
JSON: {
  "n_benign": int, "n_jailbreak": int, "n_layers": int,
  "n_encoder_layers": int, "n_decoder_layers": int,
  "per_layer_jsd": [float, ...],           // JSD in nats, range [0, ln2 ≈ 0.693]
  "per_layer_jsd_normalized": [float, ...], // JSD / ln2, range [0, 1]
  "top_diagnostic_layers": [int, ...],     // layer indices sorted by JSD desc
  "encoder_mean_jsd": float,
  "decoder_mean_jsd": float,
  "decoder_encoder_jsd_ratio": float,      // > 1 confirms decoder-dominant signal
  "per_layer_benign_mean": [float, ...],
  "per_layer_jailbreak_mean": [float, ...],
  "per_layer_diff": [float, ...],          // benign_mean - jailbreak_mean
  "most_diagnostic_layer": int,
  "hypothesis_confirmed": bool             // decoder JSD > encoder JSD
}
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Jensen–Shannon Divergence (binned, per-layer)
# ---------------------------------------------------------------------------

N_BINS = 20  # gc(k) ∈ [0, 1], 20 bins → 0.05 resolution


def _kl_div(p: np.ndarray, q: np.ndarray, eps: float = 1e-10) -> float:
    """KL(P||Q) in nats. p and q are probability vectors (sum to 1)."""
    p = p + eps
    q = q + eps
    p = p / p.sum()
    q = q / q.sum()
    return float(np.sum(p * np.log(p / q)))


def jsd_from_samples(samples_p: np.ndarray, samples_q: np.ndarray) -> float:
    """
    Compute Jensen–Shannon Divergence between two 1-D sample arrays.
    Returns JSD in nats ∈ [0, ln2 ≈ 0.693].
    """
    bins = np.linspace(0.0, 1.0, N_BINS + 1)
    hist_p, _ = np.histogram(samples_p, bins=bins, density=False)
    hist_q, _ = np.histogram(samples_q, bins=bins, density=False)
    hist_p = hist_p.astype(float) + 1e-8
    hist_q = hist_q.astype(float) + 1e-8
    hist_p /= hist_p.sum()
    hist_q /= hist_q.sum()
    m = 0.5 * (hist_p + hist_q)
    return 0.5 * _kl_div(hist_p, m) + 0.5 * _kl_div(hist_q, m)


def compute_per_layer_jsd(benign_matrix: np.ndarray, jailbreak_matrix: np.ndarray) -> np.ndarray:
    """
    benign_matrix: (N_benign, n_layers) — gc(k) values per sample per layer
    jailbreak_matrix: (N_jailbreak, n_layers)
    Returns: (n_layers,) array of JSD values
    """
    assert benign_matrix.shape[1] == jailbreak_matrix.shape[1], \
        "Mismatched layer counts between benign and jailbreak"
    n_layers = benign_matrix.shape[1]
    jsds = np.zeros(n_layers)
    for layer in range(n_layers):
        jsds[layer] = jsd_from_samples(benign_matrix[:, layer], jailbreak_matrix[:, layer])
    return jsds


# ---------------------------------------------------------------------------
# Mock data generator (extends gc_jailbreak_classifier modes)
# ---------------------------------------------------------------------------

def generate_mock_population(
    mode: str,
    n: int = 50,
    n_enc: int = 6,
    n_dec: int = 6,
    base_seed: int = 0,
) -> np.ndarray:
    """
    Generate (n, n_enc+n_dec) gc(k) matrix for a population.
    mode: "benign" | "jailbreak"
    """
    rng = np.random.default_rng(base_seed)
    n_total = n_enc + n_dec
    matrix = np.zeros((n, n_total))

    for i in range(n):
        seed_i = base_seed + i * 13
        rng_i = np.random.default_rng(seed_i)

        if mode == "benign":
            # Mix of "listen" and "guess" — both show coherent enc→dec
            if rng.random() < 0.6:  # listen-dominant
                enc = np.linspace(0.25 + rng_i.uniform(-0.05, 0.05), 0.80 + rng_i.uniform(-0.05, 0.10), n_enc)
                dec = np.linspace(0.78 + rng_i.uniform(-0.05, 0.05), 0.65 + rng_i.uniform(-0.10, 0.05), n_dec)
            else:  # guess-like
                enc = np.linspace(0.15 + rng_i.uniform(-0.05, 0.05), 0.55 + rng_i.uniform(-0.05, 0.10), n_enc)
                dec = np.linspace(0.45 + rng_i.uniform(-0.05, 0.05), 0.20 + rng_i.uniform(-0.05, 0.05), n_dec)
            enc += rng_i.normal(0, 0.04, n_enc)
            dec += rng_i.normal(0, 0.04, n_dec)

        else:  # jailbreak
            # Encoder looks normal-ish, decoder COLLAPSES
            enc = np.linspace(0.20 + rng_i.uniform(-0.05, 0.10), 0.68 + rng_i.uniform(-0.10, 0.10), n_enc)
            # Collapse depth varies: mild to severe
            end_val = rng_i.uniform(0.02, 0.12)
            dec = np.linspace(0.60 + rng_i.uniform(-0.05, 0.10), end_val, n_dec)
            enc += rng_i.normal(0, 0.04, n_enc)
            dec += rng_i.normal(0, 0.025, n_dec)

        matrix[i] = np.clip(np.concatenate([enc, dec]), 0.0, 1.0)

    return matrix


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze(
    benign_matrix: np.ndarray,
    jailbreak_matrix: np.ndarray,
    n_enc: int,
) -> dict:
    """Full thermometer analysis."""
    jsds = compute_per_layer_jsd(benign_matrix, jailbreak_matrix)
    ln2 = math.log(2)
    n_layers = jsds.shape[0]
    n_dec = n_layers - n_enc

    jsd_norm = (jsds / ln2).tolist()
    enc_jsd = float(jsds[:n_enc].mean())
    dec_jsd = float(jsds[n_enc:].mean())
    ratio = dec_jsd / (enc_jsd + 1e-10)

    benign_means = benign_matrix.mean(axis=0).tolist()
    jail_means = jailbreak_matrix.mean(axis=0).tolist()
    diff = (benign_matrix.mean(axis=0) - jailbreak_matrix.mean(axis=0)).tolist()

    top_layers = sorted(range(n_layers), key=lambda i: jsds[i], reverse=True)
    most_diag = int(top_layers[0])
    hypothesis_confirmed = dec_jsd > enc_jsd  # jailbreak signal is decoder-dominant

    return {
        "n_benign": int(benign_matrix.shape[0]),
        "n_jailbreak": int(jailbreak_matrix.shape[0]),
        "n_layers": n_layers,
        "n_encoder_layers": n_enc,
        "n_decoder_layers": n_dec,
        "per_layer_jsd": [round(float(v), 6) for v in jsds],
        "per_layer_jsd_normalized": [round(v, 6) for v in jsd_norm],
        "top_diagnostic_layers": top_layers[:5],
        "encoder_mean_jsd": round(enc_jsd, 6),
        "decoder_mean_jsd": round(dec_jsd, 6),
        "decoder_encoder_jsd_ratio": round(ratio, 4),
        "per_layer_benign_mean": [round(v, 4) for v in benign_means],
        "per_layer_jailbreak_mean": [round(v, 4) for v in jail_means],
        "per_layer_diff": [round(v, 4) for v in diff],
        "most_diagnostic_layer": most_diag,
        "hypothesis_confirmed": bool(hypothesis_confirmed),
    }


# ---------------------------------------------------------------------------
# ASCII thermometer
# ---------------------------------------------------------------------------

def print_thermometer(result: dict) -> None:
    n_enc = result["n_encoder_layers"]
    jsds = result["per_layer_jsd_normalized"]
    benign_m = result["per_layer_benign_mean"]
    jail_m = result["per_layer_jailbreak_mean"]

    bar_width = 30
    print("\n" + "=" * 65)
    print("  gc(k) DIVERGENCE THERMOMETER (JSD normalized, range [0,1])")
    print("  Higher = more diagnostic for jailbreak detection")
    print("=" * 65)
    print(f"  {'Layer':<7} {'Type':<5} {'JSD':>6}  {'Bar':<32} gc(k): benign→jail")
    print("-" * 65)

    for layer, jsd in enumerate(jsds):
        layer_type = "ENC" if layer < n_enc else "DEC"
        bar_len = int(jsd * bar_width)
        bar = "█" * bar_len + "░" * (bar_width - bar_len)
        indicator = "◄ TOP" if layer == result["most_diagnostic_layer"] else ""
        bm = benign_m[layer]
        jm = jail_m[layer]
        print(f"  L{layer:<6d} {layer_type:<5} {jsd:>6.3f}  [{bar}] {bm:.2f}→{jm:.2f} {indicator}")

    print("-" * 65)
    print(f"  Encoder mean JSD : {result['encoder_mean_jsd']:.4f}")
    print(f"  Decoder mean JSD : {result['decoder_mean_jsd']:.4f}")
    print(f"  Dec/Enc ratio    : {result['decoder_encoder_jsd_ratio']:.2f}x")
    hyp = "✅ CONFIRMED" if result["hypothesis_confirmed"] else "❌ NOT confirmed"
    print(f"  Hypothesis       : decoder-dominant signal → {hyp}")
    print(f"  N benign / jail  : {result['n_benign']} / {result['n_jailbreak']}")
    print("=" * 65 + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="gc(k) Divergence Thermometer — per-layer JSD between benign and jailbreak populations"
    )
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--mock", action="store_true",
                            help="Use synthetic populations")
    mode_group.add_argument("--file", type=str,
                            help="JSON file with benign + jailbreak gc(k) curves")
    parser.add_argument("--n", type=int, default=50,
                        help="Number of mock samples per condition (default: 50)")
    parser.add_argument("--n-enc", type=int, default=6,
                        help="Number of encoder layers (default: 6, Whisper-small)")
    parser.add_argument("--n-dec", type=int, default=6,
                        help="Number of decoder layers (default: 6, Whisper-small)")
    parser.add_argument("--plot", action="store_true",
                        help="Print ASCII thermometer heatmap")
    parser.add_argument("--quiet", action="store_true",
                        help="JSON output only")
    args = parser.parse_args()

    if args.mock:
        n_enc, n_dec = args.n_enc, args.n_dec
        benign_matrix = generate_mock_population("benign", n=args.n, n_enc=n_enc, n_dec=n_dec, base_seed=0)
        jailbreak_matrix = generate_mock_population("jailbreak", n=args.n, n_enc=n_enc, n_dec=n_dec, base_seed=100)
    else:
        with open(args.file) as f:
            data = json.load(f)
        # Build matrices from curve dicts
        benign_curves = data["benign"]
        jailbreak_curves = data["jailbreak"]
        n_enc = benign_curves[0].get("n_encoder_layers", 6)
        benign_matrix = np.array([c["gc_values"] for c in benign_curves])
        jailbreak_matrix = np.array([c["gc_values"] for c in jailbreak_curves])

    result = analyze(benign_matrix, jailbreak_matrix, n_enc=args.n_enc if args.mock else n_enc)

    if not args.quiet:
        print_thermometer(result)

    if args.quiet or not args.plot:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
