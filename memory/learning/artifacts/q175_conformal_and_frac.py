"""
Q175: gc(k) as Epistemic Uncertainty Estimator
AND-frac conformal prediction calibration vs softmax baseline.

DoD: Frame AND-frac as model-internal uncertainty signal.
     Compare to conformal prediction on WER calibration.

Author: autodidact | 2026-03-26
"""

import numpy as np
from typing import Tuple, Dict, List
import json

np.random.seed(42)

# ── Synthetic data generator ──────────────────────────────────────────────────
# Models a Whisper-base decode on 200 utterances with varying SNR / accent.
# Each utterance has:
#   - and_frac_steps: AND-frac at each decode step
#   - softmax_conf: max softmax prob for top token (utterance avg)
#   - wer: word-error rate (0.0 = perfect)
#   - snr: signal-to-noise ratio (higher = cleaner)
#   - accent: 0=native, 1=accented

def generate_synthetic_corpus(n: int = 200, seed: int = 42) -> List[Dict]:
    rng = np.random.default_rng(seed)
    corpus = []
    for i in range(n):
        snr = rng.uniform(-5, 30)          # dB
        accent = int(i % 4 == 3)           # ~25% accented
        n_steps = rng.integers(8, 25)      # token steps

        # AND-frac: higher SNR → higher AND-frac; accent lowers it slightly
        base_af = 0.5 + 0.015 * snr - 0.08 * accent
        step_af = np.clip(base_af + rng.normal(0, 0.07, n_steps), 0.0, 1.0)
        mean_af = float(step_af.mean())

        # Softmax confidence: correlated with AND-frac but noisier
        mean_sm = float(np.clip(0.65 + 0.25 * mean_af + rng.normal(0, 0.08), 0.0, 1.0))

        # WER: inversely related to AND-frac + softmax
        logit_wer = -3.0 * mean_af - 1.5 * mean_sm + 2.0 + rng.normal(0, 0.4)
        wer = float(1.0 / (1.0 + np.exp(-logit_wer)))
        wer = float(np.clip(wer + rng.exponential(0.03), 0.0, 1.0))

        corpus.append({
            "id": f"utt-{i:03d}",
            "snr": snr,
            "accent": accent,
            "n_steps": int(n_steps),
            "and_frac_steps": step_af.tolist(),
            "mean_and_frac": mean_af,
            "mean_softmax": mean_sm,
            "wer": wer,
            "wer_binary": int(wer > 0.05),   # flag if any errors
        })
    return corpus


# ── Conformal Prediction ──────────────────────────────────────────────────────

def calibrate_conformal(
    scores: np.ndarray, labels: np.ndarray, alpha: float = 0.10
) -> Tuple[float, float]:
    """
    Split conformal calibration.
    Returns (threshold τ, empirical coverage on calibration set).
    scores: nonconformity score (higher = more uncertain)
    labels: 1 if utterance has errors (wer > threshold), 0 if clean
    """
    # τ = (1-α) quantile of calibration scores
    # Standard split-CP: τ s.t. coverage ≥ 1-α on cal set
    tau = float(np.quantile(scores, 1 - alpha))
    coverage = float(np.mean(scores <= tau))
    return tau, coverage


def evaluate_detector(
    scores: np.ndarray, labels: np.ndarray, tau: float
) -> Dict:
    """Evaluate binary detector (predict error if score > tau)."""
    preds = (scores > tau).astype(int)
    tp = int(np.sum((preds == 1) & (labels == 1)))
    fp = int(np.sum((preds == 1) & (labels == 0)))
    tn = int(np.sum((preds == 0) & (labels == 0)))
    fn = int(np.sum((preds == 0) & (labels == 1)))
    precision = tp / (tp + fp + 1e-9)
    recall = tp / (tp + fn + 1e-9)
    f1 = 2 * precision * recall / (precision + recall + 1e-9)

    # AUROC (trapezoidal) — sort by FPR ascending
    thresholds = np.linspace(scores.max(), scores.min(), 100)
    tprs, fprs = [0.0], [0.0]
    for t in thresholds:
        p = (scores > t).astype(int)
        tprs.append(float(np.sum((p == 1) & (labels == 1)) / (np.sum(labels) + 1e-9)))
        fprs.append(float(np.sum((p == 1) & (labels == 0)) / (np.sum(1 - labels) + 1e-9)))
    tprs.append(1.0); fprs.append(1.0)
    # Sort by fpr
    pairs = sorted(zip(fprs, tprs))
    fprs_s, tprs_s = zip(*pairs)
    auroc = float(np.trapezoid(tprs_s, fprs_s))

    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "auroc": round(auroc, 4),
    }


# ── Word-level uncertainty (step-wise AND-frac) ───────────────────────────────

def word_level_uncertainty(
    corpus: List[Dict], high_wer_frac: float = 0.3
) -> Dict:
    """
    Novel contribution: use step-wise AND-frac to compute per-step uncertainty.
    Hypothesis: final steps (higher wer) have lower AND-frac than early steps.
    """
    wers = sorted(u["wer"] for u in corpus)
    lo_thresh = wers[int(0.25 * len(wers))]  # bottom 25%
    hi_thresh = wers[int(0.75 * len(wers))]  # top 25%
    high_wer = [u for u in corpus if u["wer"] >= hi_thresh]
    low_wer = [u for u in corpus if u["wer"] <= lo_thresh]

    def step_profile(utts, n_bins=8):
        profiles = []
        for u in utts:
            steps = np.array(u["and_frac_steps"])
            # Normalize to n_bins bins
            bins = np.array_split(steps, min(n_bins, len(steps)))
            profiles.append([b.mean() for b in bins[:n_bins]])
        # Pad shorter ones
        padded = [p + [p[-1]] * (n_bins - len(p)) for p in profiles]
        return np.mean(padded, axis=0)

    if len(high_wer) < 5 or len(low_wer) < 5:
        return {"skipped": "insufficient data"}

    high_profile = step_profile(high_wer)
    low_profile = step_profile(low_wer)

    return {
        "n_high_wer": len(high_wer),
        "n_low_wer": len(low_wer),
        "high_wer_step_profile": [round(x, 3) for x in high_profile.tolist()],
        "low_wer_step_profile": [round(x, 3) for x in low_profile.tolist()],
        "late_step_gap": round(float(low_profile[-3:].mean() - high_profile[-3:].mean()), 4),
        "interpretation": (
            "positive gap = low-WER utterances maintain higher AND-frac in final steps "
            "(model stays grounded vs 'going language-prior' in error-prone regions)"
        ),
    }


# ── Main experiment ───────────────────────────────────────────────────────────

def run_experiment(alpha: float = 0.10) -> Dict:
    corpus = generate_synthetic_corpus(n=200)

    # Cal/test split 50/50
    rng = np.random.default_rng(0)
    idx = rng.permutation(len(corpus))
    cal_idx, test_idx = idx[:100], idx[100:]
    cal = [corpus[i] for i in cal_idx]
    test = [corpus[i] for i in test_idx]

    # Nonconformity scores
    cal_af = np.array([1 - u["mean_and_frac"] for u in cal])
    test_af = np.array([1 - u["mean_and_frac"] for u in test])
    cal_sm = np.array([1 - u["mean_softmax"] for u in cal])
    test_sm = np.array([1 - u["mean_softmax"] for u in test])

    cal_labels = np.array([u["wer_binary"] for u in cal])
    test_labels = np.array([u["wer_binary"] for u in test])

    # Calibrate on cal set
    tau_af, cov_af = calibrate_conformal(cal_af, cal_labels, alpha)
    tau_sm, cov_sm = calibrate_conformal(cal_sm, cal_labels, alpha)

    # Evaluate on test set
    metrics_af = evaluate_detector(test_af, test_labels, tau_af)
    metrics_sm = evaluate_detector(test_sm, test_labels, tau_sm)

    # Test coverage on test set (CP guarantee should hold OOD)
    test_coverage_af = float(np.mean(test_af <= tau_af))
    test_coverage_sm = float(np.mean(test_sm <= tau_sm))

    # Word-level analysis
    wl = word_level_uncertainty(corpus)

    # Distribution shift: accented vs native
    native_test = [u for u in test if u["accent"] == 0]
    accent_test = [u for u in test if u["accent"] == 1]

    def wer_at_threshold(utts, tau, key):
        scores = np.array([1 - u[key] for u in utts])
        flagged = scores > tau
        flagged_wer = np.mean([u["wer"] for u, f in zip(utts, flagged) if f]) if flagged.any() else 0
        unflagged_wer = np.mean([u["wer"] for u, f in zip(utts, flagged) if not f]) if (~flagged).any() else 0
        return round(float(flagged_wer), 4), round(float(unflagged_wer), 4)

    af_key = "mean_and_frac"
    sm_key = "mean_softmax"

    return {
        "n_cal": len(cal), "n_test": len(test),
        "alpha": alpha,

        "calibration": {
            "and_frac": {"tau": round(tau_af, 4), "coverage": round(cov_af, 4)},
            "softmax":  {"tau": round(tau_sm, 4), "coverage": round(cov_sm, 4)},
        },

        "test_coverage": {
            "and_frac": round(test_coverage_af, 4),
            "softmax":  round(test_coverage_sm, 4),
            "note": f"Both should be >= {1-alpha:.2f} (CP guarantee)",
        },

        "detection_metrics": {
            "and_frac": metrics_af,
            "softmax":  metrics_sm,
        },

        "distribution_shift": {
            "and_frac": {
                "native_flagged_wer": wer_at_threshold(native_test, tau_af, af_key)[0],
                "native_unflagged_wer": wer_at_threshold(native_test, tau_af, af_key)[1],
                "accent_flagged_wer": wer_at_threshold(accent_test, tau_af, af_key)[0],
                "accent_unflagged_wer": wer_at_threshold(accent_test, tau_af, af_key)[1],
            },
            "softmax": {
                "native_flagged_wer": wer_at_threshold(native_test, tau_sm, sm_key)[0],
                "native_unflagged_wer": wer_at_threshold(native_test, tau_sm, sm_key)[1],
                "accent_flagged_wer": wer_at_threshold(accent_test, tau_sm, sm_key)[0],
                "accent_unflagged_wer": wer_at_threshold(accent_test, tau_sm, sm_key)[1],
            },
        },

        "word_level_uncertainty": wl,
    }


if __name__ == "__main__":
    import sys
    results = run_experiment(alpha=0.10)

    print("=" * 60)
    print("Q175: AND-frac Conformal Uncertainty Estimation")
    print("=" * 60)

    print(f"\nData: {results['n_cal']} cal / {results['n_test']} test | α={results['alpha']}")

    print("\n── Calibration τ ──────────────────────────────────────")
    for k, v in results["calibration"].items():
        print(f"  {k:12s}: τ={v['tau']:.4f}  cal_coverage={v['coverage']:.4f}")

    print(f"\n── Test Coverage (CP guarantee: ≥{1-results['alpha']:.2f}) ──────")
    tc = results["test_coverage"]
    for k in ["and_frac", "softmax"]:
        cov = tc[k]
        flag = "✅" if cov >= 1 - results["alpha"] else "❌"
        print(f"  {k:12s}: {cov:.4f}  {flag}")

    print("\n── Detection Metrics (test set) ───────────────────────")
    dm = results["detection_metrics"]
    print(f"  {'Method':12s} | {'AUROC':>6} | {'F1':>6} | {'Prec':>6} | {'Recall':>6}")
    print(f"  {'-'*50}")
    for k in ["and_frac", "softmax"]:
        m = dm[k]
        print(f"  {k:12s} | {m['auroc']:>6.4f} | {m['f1']:>6.4f} | {m['precision']:>6.4f} | {m['recall']:>6.4f}")

    print("\n── Word-level Uncertainty (step-wise AND-frac) ────────")
    wl = results["word_level_uncertainty"]
    if "skipped" not in wl:
        print(f"  High-WER ({wl['n_high_wer']} utts) step profile: {wl['high_wer_step_profile']}")
        print(f"  Low-WER  ({wl['n_low_wer']} utts) step profile:  {wl['low_wer_step_profile']}")
        print(f"  Late-step gap (low−high): {wl['late_step_gap']:+.4f}")
        print(f"  → {wl['interpretation']}")

    print("\n── Distribution Shift (native vs accented) ────────────")
    ds = results["distribution_shift"]
    for method in ["and_frac", "softmax"]:
        m = ds[method]
        print(f"  {method}: native flagged_WER={m['native_flagged_wer']:.3f} "
              f"unflagged={m['native_unflagged_wer']:.3f} | "
              f"accent flagged={m['accent_flagged_wer']:.3f} "
              f"unflagged={m['accent_unflagged_wer']:.3f}")

    print("\n── Saving results ──────────────────────────────────────")
    out = "memory/learning/artifacts/q175_conformal_results.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  → {out}")
    print("\nDone.")
