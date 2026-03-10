"""
Q041: SAE-guided adversarial detector calibration (SPIRIT-inspired)

Goal: Given SAE feature activations, calibrate a threshold-based alert for
adversarial / misaligned audio inputs. Evaluate precision/recall on synthetic data.

SPIRIT reference: "Detecting Prompt Injection Attacks via LLM-Powered Input Semantic 
Analysis" — we adapt the idea to SAE feature-space detection rather than text prompts.

Architecture:
  - SAE encodes audio hidden states → sparse feature vector
  - Detector: a small rule set / linear classifier on top of SAE features
  - Calibration: sweep threshold on val set, pick F1-optimal
  - Evaluation: report precision, recall, F1, FPR on held-out test set

Usage:
    python3 sae_adversarial_calibrator.py [--seed 42] [--n-samples 500]
    python3 sae_adversarial_calibrator.py --sweep-thresholds --plot-roc
"""

import argparse
import json
import math
import random
from pathlib import Path

# ── Synthetic data generation ─────────────────────────────────────────────────

SAE_DIM = 512       # number of SAE latent features
ATTACK_FEATURES = [7, 23, 89, 134, 271]   # features that fire on adversarial inputs

def _sparse_activation(dim: int, active_features: list[int], magnitude: float, noise: float, rng) -> list[float]:
    """Generate a sparse SAE activation vector."""
    vec = [0.0] * dim
    for f in active_features:
        vec[f] = magnitude + rng.gauss(0, noise)
        vec[f] = max(0.0, vec[f])  # ReLU
    # random background sparsity
    n_bg = rng.randint(5, 20)
    for _ in range(n_bg):
        idx = rng.randint(0, dim - 1)
        vec[idx] = rng.expovariate(5.0)
    return vec

def generate_dataset(n: int, attack_ratio: float = 0.3, seed: int = 42) -> list[dict]:
    """
    Generate synthetic SAE activation examples.
    Benign: random sparse activations, attack features silent.
    Adversarial: attack features fire at high magnitude.
    """
    rng = random.Random(seed)
    samples = []
    n_attack = int(n * attack_ratio)
    n_benign = n - n_attack

    # Benign examples
    for _ in range(n_benign):
        # random active features (NOT from attack set)
        active = [rng.randint(0, SAE_DIM - 1) for _ in range(rng.randint(3, 10))]
        active = [f for f in active if f not in ATTACK_FEATURES]
        vec = _sparse_activation(SAE_DIM, active, magnitude=1.5, noise=0.3, rng=rng)
        samples.append({"features": vec, "label": 0, "type": "benign"})

    # Adversarial examples (attack features fire + some normal features)
    for _ in range(n_attack):
        normal_active = [rng.randint(0, SAE_DIM - 1) for _ in range(rng.randint(2, 8))]
        # Partial attack: 70% of attacks fire all ATTACK_FEATURES, 30% fire subset
        if rng.random() < 0.7:
            attack_active = ATTACK_FEATURES
        else:
            k = rng.randint(2, len(ATTACK_FEATURES))
            attack_active = rng.sample(ATTACK_FEATURES, k)
        active = list(set(normal_active + attack_active))
        vec = _sparse_activation(SAE_DIM, active, magnitude=2.2, noise=0.4, rng=rng)
        samples.append({"features": vec, "label": 1, "type": "adversarial"})

    rng.shuffle(samples)
    return samples

# ── Detector: L1-norm of attack features ──────────────────────────────────────

def attack_score(features: list[float]) -> float:
    """
    SPIRIT-inspired detector: sum of SAE feature activations for known attack features.
    In practice, attack feature indices come from SAE steering experiments.
    This is analogous to SPIRIT's "semantic coherence score" but in feature space.
    """
    return sum(features[f] for f in ATTACK_FEATURES)

# ── Calibration ───────────────────────────────────────────────────────────────

def calibrate(val_set: list[dict], thresholds: list[float]) -> dict:
    """Sweep thresholds on val set; return best F1 config."""
    scores = [(attack_score(s["features"]), s["label"]) for s in val_set]
    best = {"threshold": None, "f1": -1.0, "precision": 0.0, "recall": 0.0, "fpr": 0.0}

    for t in thresholds:
        tp = fp = tn = fn = 0
        for score, label in scores:
            pred = 1 if score >= t else 0
            if pred == 1 and label == 1: tp += 1
            elif pred == 1 and label == 0: fp += 1
            elif pred == 0 and label == 1: fn += 1
            else: tn += 1

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

        if f1 > best["f1"]:
            best = {"threshold": t, "f1": f1, "precision": prec, "recall": rec, "fpr": fpr,
                    "tp": tp, "fp": fp, "tn": tn, "fn": fn}

    return best

# ── Evaluation ────────────────────────────────────────────────────────────────

def evaluate(test_set: list[dict], threshold: float) -> dict:
    """Evaluate detector at given threshold on test set."""
    tp = fp = tn = fn = 0
    for s in test_set:
        score = attack_score(s["features"])
        pred = 1 if score >= threshold else 0
        label = s["label"]
        if pred == 1 and label == 1: tp += 1
        elif pred == 1 and label == 0: fp += 1
        elif pred == 0 and label == 1: fn += 1
        else: tn += 1

    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    return {"precision": prec, "recall": rec, "f1": f1, "fpr": fpr,
            "tp": tp, "fp": fp, "tn": tn, "fn": fn, "n_test": len(test_set)}

# ── ROC curve (text) ──────────────────────────────────────────────────────────

def text_roc(val_set: list[dict], thresholds: list[float]) -> str:
    lines = [f"{'Threshold':>10} | {'Precision':>9} | {'Recall':>7} | {'F1':>6} | {'FPR':>6}"]
    lines.append("-" * 55)
    for t in thresholds[::max(1, len(thresholds) // 15)]:
        scores = [(attack_score(s["features"]), s["label"]) for s in val_set]
        tp = fp = tn = fn = 0
        for sc, lb in scores:
            pred = 1 if sc >= t else 0
            if pred == 1 and lb == 1: tp += 1
            elif pred == 1 and lb == 0: fp += 1
            elif pred == 0 and lb == 1: fn += 1
            else: tn += 1
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        lines.append(f"{t:>10.2f} | {prec:>9.3f} | {rec:>7.3f} | {f1:>6.3f} | {fpr:>6.3f}")
    return "\n".join(lines)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SAE adversarial detector calibration")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-samples", type=int, default=500)
    parser.add_argument("--attack-ratio", type=float, default=0.3)
    parser.add_argument("--sweep-thresholds", action="store_true")
    parser.add_argument("--output-json", type=str, default=None)
    args = parser.parse_args()

    # Generate full dataset, split 60/20/20 train/val/test
    data = generate_dataset(args.n_samples, attack_ratio=args.attack_ratio, seed=args.seed)
    n = len(data)
    n_train = int(n * 0.6)
    n_val = int(n * 0.2)
    train_set = data[:n_train]
    val_set = data[n_train:n_train + n_val]
    test_set = data[n_train + n_val:]

    print(f"\n{'='*60}")
    print("SAE Adversarial Detector Calibration (SPIRIT-inspired)")
    print(f"{'='*60}")
    print(f"Dataset: {n} samples | attack ratio={args.attack_ratio:.0%}")
    print(f"Train: {len(train_set)} | Val: {len(val_set)} | Test: {len(test_set)}")
    print(f"Attack features: {ATTACK_FEATURES}  SAE dim: {SAE_DIM}")
    print()

    # Compute score distribution on val set
    attack_scores = [attack_score(s["features"]) for s in val_set if s["label"] == 1]
    benign_scores = [attack_score(s["features"]) for s in val_set if s["label"] == 0]
    print(f"Val score dist (attack):  mean={sum(attack_scores)/len(attack_scores):.2f}, "
          f"max={max(attack_scores):.2f}, min={min(attack_scores):.2f}")
    print(f"Val score dist (benign):  mean={sum(benign_scores)/len(benign_scores):.2f}, "
          f"max={max(benign_scores):.2f}, min={min(benign_scores):.2f}")
    print()

    # Sweep thresholds
    all_scores = [attack_score(s["features"]) for s in val_set]
    t_min, t_max = min(all_scores), max(all_scores)
    thresholds = [t_min + (t_max - t_min) * i / 100 for i in range(101)]

    if args.sweep_thresholds:
        print("=== Threshold Sweep (Val) ===")
        print(text_roc(val_set, thresholds))
        print()

    # Calibrate
    best = calibrate(val_set, thresholds)
    print(f"=== Best Val Config ===")
    print(f"  Threshold  : {best['threshold']:.3f}")
    print(f"  Precision  : {best['precision']:.3f}")
    print(f"  Recall     : {best['recall']:.3f}")
    print(f"  F1         : {best['f1']:.3f}")
    print(f"  FPR        : {best['fpr']:.3f}")
    print(f"  Confusion  : TP={best.get('tp',0)} FP={best.get('fp',0)} TN={best.get('tn',0)} FN={best.get('fn',0)}")
    print()

    # Evaluate on test set at best threshold
    test_results = evaluate(test_set, best["threshold"])
    print(f"=== Test Set Evaluation (threshold={best['threshold']:.3f}) ===")
    print(f"  Precision  : {test_results['precision']:.3f}")
    print(f"  Recall     : {test_results['recall']:.3f}")
    print(f"  F1         : {test_results['f1']:.3f}")
    print(f"  FPR        : {test_results['fpr']:.3f}")
    print(f"  Confusion  : TP={test_results['tp']} FP={test_results['fp']} "
          f"TN={test_results['tn']} FN={test_results['fn']}")
    print()

    # SPIRIT leakage pattern note (akin to ESN leakage hypothesis in Q037)
    print("=== Leakage Pattern Analysis ===")
    partial_attacks = [s for s in test_set if s["label"] == 1 and
                       attack_score(s["features"]) < best["threshold"]]
    print(f"  Missed adversarial examples (FN): {test_results['fn']}")
    print(f"  These are likely partial-activation attacks (subset of ATTACK_FEATURES)")
    print(f"  Implication: detector is recall-limited for stealthy / partial attacks.")
    print(f"  Mitigation: ensemble multiple feature subsets as separate detectors (OR-gate),")
    print(f"              or train a linear probe on top of SAE features (next step).")
    print()

    result = {
        "config": {
            "n_samples": args.n_samples, "attack_ratio": args.attack_ratio,
            "seed": args.seed, "sae_dim": SAE_DIM,
            "attack_features": ATTACK_FEATURES
        },
        "calibration": {"threshold": best["threshold"], **{k: round(v, 4) for k, v in best.items()
                                                           if isinstance(v, float)}},
        "test": {k: round(v, 4) if isinstance(v, float) else v for k, v in test_results.items()}
    }

    if args.output_json:
        Path(args.output_json).write_text(json.dumps(result, indent=2))
        print(f"Results written to {args.output_json}")

    return result

if __name__ == "__main__":
    main()
