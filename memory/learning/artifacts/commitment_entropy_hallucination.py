#!/usr/bin/env python3
"""
Q173: Commitment Entropy as Hallucination Predictor
=====================================================
Logistic probe: commitment-head entropy → hallucination binary prediction.
Compares vs decode-confidence (max-prob) and perplexity baselines.

Design
------
- "Commitment heads" H00, H07, H01 (encoder layer L*; established in prior mocks)
- Entropy of attention distribution over query → lower entropy = more committed
- Hallucination proxy: WER(transcript, reference) > threshold (e.g. 0.3)
- Logistic regression: entropy_features → hallucination_label
- Baselines:
    - Max token probability (decode confidence)
    - Perplexity (mean neg log-prob of tokens)

CPU-only. Synthetic data (no GPU required).
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple

# ── Reproducibility ──────────────────────────────────────────────────────────
RNG = np.random.default_rng(42)

# ── Config ───────────────────────────────────────────────────────────────────
N_SAMPLES      = 200
COMMITMENT_HEADS = [0, 7, 1]   # H00, H07, H01 (0-indexed)
N_HEADS        = 8
WER_THRESHOLD  = 0.30          # WER > this → hallucination = 1
HAL_RATE       = 0.35          # synthetic hallucination prevalence

# ── Synthetic data generator ─────────────────────────────────────────────────

def simulate_sample(is_hallucination: bool) -> dict:
    """
    Generate one synthetic (audio, transcript) pair features.

    Commitment-head entropy:
      - non-hallucination → low entropy (sharp attention, committed)
      - hallucination     → high entropy (diffuse attention, uncertain)
    Decode confidence (max softmax prob):
      - non-hal → high (0.7–0.99)
      - hal     → lower (0.3–0.7) with overlap
    Perplexity:
      - non-hal → low (3–8)
      - hal     → higher (8–20)
    """
    # Attention distributions for each head
    attention_entropies = []
    for h in range(N_HEADS):
        if h in COMMITMENT_HEADS:
            if is_hallucination:
                # Diffuse attention → high entropy
                alpha = RNG.uniform(0.5, 1.5, 10)
            else:
                # Sharp attention → low entropy
                alpha = np.zeros(10) + 0.2
                alpha[RNG.integers(10)] = 5.0
        else:
            # Non-commitment heads: similar entropy regardless
            alpha = RNG.uniform(0.8, 1.2, 10)
        probs = alpha / alpha.sum()
        entropy = -np.sum(probs * np.log(probs + 1e-9))
        attention_entropies.append(entropy)

    # Add noise
    noise = RNG.normal(0, 0.1, N_HEADS)
    attention_entropies = np.clip(np.array(attention_entropies) + noise, 0.01, None)

    # Decode confidence (max token prob, averaged over tokens)
    if is_hallucination:
        decode_conf = RNG.uniform(0.25, 0.65)
    else:
        decode_conf = RNG.uniform(0.65, 0.98)

    # Perplexity
    if is_hallucination:
        perplexity = RNG.uniform(10, 22)
    else:
        perplexity = RNG.uniform(2.5, 9)

    return {
        "attention_entropies": attention_entropies,  # shape: (N_HEADS,)
        "decode_conf": decode_conf,
        "perplexity": perplexity,
        "label": int(is_hallucination),
    }


def build_dataset(n: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return (X_commit, X_conf, X_ppl, y)."""
    labels = (RNG.random(n) < HAL_RATE).astype(int)
    samples = [simulate_sample(bool(y)) for y in labels]

    # Feature matrices
    X_commit = np.array([
        [s["attention_entropies"][h] for h in COMMITMENT_HEADS]
        for s in samples
    ])  # (n, 3)
    X_conf   = np.array([[s["decode_conf"]] for s in samples])   # (n, 1)
    X_ppl    = np.array([[s["perplexity"]]  for s in samples])   # (n, 1)
    y        = np.array([s["label"] for s in samples])

    return X_commit, X_conf, X_ppl, y

# ── Logistic regression (pure numpy, no sklearn) ──────────────────────────────

def sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))

def train_logistic(X: np.ndarray, y: np.ndarray,
                   lr: float = 0.1, epochs: int = 200) -> Tuple[np.ndarray, float]:
    """Gradient-descent logistic regression. Returns (weights, bias)."""
    n, d = X.shape
    w = np.zeros(d)
    b = 0.0
    for _ in range(epochs):
        p   = sigmoid(X @ w + b)
        err = p - y
        w  -= lr * (X.T @ err) / n
        b  -= lr * err.mean()
    return w, b

def predict(X: np.ndarray, w: np.ndarray, b: float) -> np.ndarray:
    return (sigmoid(X @ w + b) >= 0.5).astype(int)

def accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return (y_true == y_pred).mean()

def auroc(y_true: np.ndarray, scores: np.ndarray) -> float:
    """Simple AUROC via Mann–Whitney U."""
    pos = scores[y_true == 1]
    neg = scores[y_true == 0]
    if len(pos) == 0 or len(neg) == 0:
        return 0.5
    u = sum(p > n for p in pos for n in neg) + 0.5 * sum(p == n for p in pos for n in neg)
    return u / (len(pos) * len(neg))

# ── Normalise features ────────────────────────────────────────────────────────

def normalise(X_tr: np.ndarray, X_te: np.ndarray):
    mu, sd = X_tr.mean(0), X_tr.std(0) + 1e-8
    return (X_tr - mu) / sd, (X_te - mu) / sd

# ── Evaluation ────────────────────────────────────────────────────────────────

def evaluate(name: str, X_tr: np.ndarray, X_te: np.ndarray,
             y_tr: np.ndarray, y_te: np.ndarray, flip_score: bool = False):
    """Train on train split, evaluate on test split. Return metrics dict."""
    X_tr_n, X_te_n = normalise(X_tr, X_te)
    w, b = train_logistic(X_tr_n, y_tr)
    y_pred = predict(X_te_n, w, b)
    scores = sigmoid(X_te_n @ w + b)
    if flip_score:
        scores = 1 - scores
    acc = accuracy(y_te, y_pred)
    auc = auroc(y_te, scores)
    return {"name": name, "acc": acc, "auroc": auc, "w": w, "b": b}

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 62)
    print("Q173: Commitment Entropy as Hallucination Predictor")
    print("=" * 62)

    # Build dataset
    X_commit, X_conf, X_ppl, y = build_dataset(N_SAMPLES)

    # 80/20 train/test split
    n_tr = int(0.8 * N_SAMPLES)
    idx  = RNG.permutation(N_SAMPLES)
    tr, te = idx[:n_tr], idx[n_tr:]

    results = []

    # 1. Commitment-entropy probe
    r = evaluate(
        "CommitEntropy (H00+H07+H01)",
        X_commit[tr], X_commit[te], y[tr], y[te],
    )
    results.append(r)

    # 2. Decode-confidence baseline (higher conf → less hal → flip)
    r = evaluate(
        "Decode-Confidence (max-prob)",
        X_conf[tr], X_conf[te], y[tr], y[te], flip_score=True,
    )
    results.append(r)

    # 3. Perplexity baseline (higher ppl → more hal → no flip)
    r = evaluate(
        "Perplexity (mean token)",
        X_ppl[tr], X_ppl[te], y[tr], y[te],
    )
    results.append(r)

    # 4. Combined: commit + conf + ppl
    X_all = np.hstack([X_commit, X_conf, X_ppl])
    r = evaluate(
        "Combined (CE + conf + ppl)",
        X_all[tr], X_all[te], y[tr], y[te],
    )
    results.append(r)

    # ── Print Results ───────────────────────────────────────────────────────
    print(f"\n{'Probe':<35} {'Acc':>6} {'AUROC':>7}")
    print("-" * 52)
    for r in results:
        print(f"{r['name']:<35} {r['acc']:.3f}  {r['auroc']:.3f}")

    # ── Definition-of-Done check ────────────────────────────────────────────
    commit = results[0]
    conf   = results[1]
    ppl    = results[2]

    print("\n── DoD Checks ─────────────────────────────────────────────")
    dod1 = commit["auroc"] > conf["auroc"]
    dod2 = commit["auroc"] > ppl["auroc"]
    dod3 = commit["auroc"] >= 0.70   # informative probe threshold
    dod4 = commit["acc"]   >= 0.65

    print(f"[{'PASS' if dod1 else 'FAIL'}] CE-entropy AUROC ({commit['auroc']:.3f}) > Decode-conf ({conf['auroc']:.3f})")
    print(f"[{'PASS' if dod2 else 'FAIL'}] CE-entropy AUROC ({commit['auroc']:.3f}) > Perplexity ({ppl['auroc']:.3f})")
    print(f"[{'PASS' if dod3 else 'FAIL'}] CE-entropy AUROC >= 0.70 (informative probe)")
    print(f"[{'PASS' if dod4 else 'FAIL'}] CE-entropy Accuracy >= 0.65")

    n_pass = sum([dod1, dod2, dod3, dod4])
    overall = n_pass >= 3
    print(f"\n{'✅ PASS' if overall else '❌ FAIL'} — {n_pass}/4 DoD criteria met")

    # ── Weights interpretation ──────────────────────────────────────────────
    head_names = ["H00", "H07", "H01"]
    print("\n── Commitment-head entropy weights (higher → more predictive of hal) ──")
    for h, (name, wi) in enumerate(zip(head_names, commit["w"])):
        print(f"  {name}: {wi:+.3f}")

    return overall

if __name__ == "__main__":
    ok = main()
    raise SystemExit(0 if ok else 1)
