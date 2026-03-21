"""
cascade_wer_predictor_mock.py — Q140
AND-gate cascade density as utterance-level WER predictor.

Hypothesis: cascade_degree × gc_peak = error_risk_score → high correlation with WER.

Definitions:
  - gc(k): fraction of features at decoder step t=1 that are AND-gated at layer k.
            Peaks at gc_peak layer, then decays.
  - cascade_degree: how many downstream AND-gate features are "triggered by" the
                    AND-gate features at gc_peak layer (graph density × N_features).
  - error_risk = cascade_degree × gc_peak_value
  
Intuition:
  - High AND-frac at an early layer (low gc_peak layer index) = audio context arrives fast.
  - Dense cascade = many features depend on AND-gate signal = stronger audio-reliance.
  - Combined: cascade_degree × gc_peak_value captures BOTH depth and density of audio processing.
  - Low error_risk → model is using audio shallowly/sparsely → higher WER risk.

Comparison with Q128:
  - Q128 used single scalar AND-frac(t=1): Pearson r = 0.928 (vs WER, |r|)
  - Q140 uses composite score: cascade_degree × gc_peak_value
  - Hypothesis: composite captures more variance, better predictor (higher |r|)

Expected output:
  - Pearson |r|(error_risk, WER) > 0.85
  - error_risk outperforms AND-frac alone on WER prediction (compare RMSE)
  - Ablation: which component drives signal — gc_peak or cascade_degree?
"""

import numpy as np

try:
    from scipy import stats as _scipy_stats
    def pearsonr(x, y):
        r, p = _scipy_stats.pearsonr(x, y)
        return float(r), float(p)
except ImportError:
    def pearsonr(x, y):
        xm = x - x.mean(); ym = y - y.mean()
        r = float(np.dot(xm, ym) / (np.sqrt(np.dot(xm, xm)) * np.sqrt(np.dot(ym, ym)) + 1e-12))
        n = len(x)
        t = r * np.sqrt(n - 2) / np.sqrt(1 - r**2 + 1e-12)
        p = float(2 * (1 - min(0.9999, abs(t) / (abs(t) + n - 2))))
        return r, p

np.random.seed(42)
N = 200         # utterances
K = 32          # decoder layers (Whisper-base has 6, but use 32 for generality)
MAX_CASCADE = 50  # max downstream features cascaded


# ──────────────────────────────────────────────
# Data generation
# ──────────────────────────────────────────────

def gen_gc_curves(n, k):
    """
    Mock gc(k) curves: each utterance has a Gaussian peak at some layer k*.
    - gc_peak_layer: uniform in [2, k//2] (early-to-mid layers)
    - gc_peak_value: Beta(4, 2) (skewed high — audio-reliant model)
    - curve: Gaussian around peak, decaying to sides
    """
    peak_layers = np.random.randint(2, k // 2, size=n)  # k* per utterance
    peak_values = np.random.beta(4, 2, size=n)           # max gc at peak
    curves = np.zeros((n, k))
    for i in range(n):
        kstar = peak_layers[i]
        pv = peak_values[i]
        sigma = k / 8.0
        for ki in range(k):
            curves[i, ki] = pv * np.exp(-0.5 * ((ki - kstar) / sigma) ** 2)
    return curves, peak_layers, peak_values


def gen_cascade_degree(n, peak_values, noise_scale=0.15):
    """
    Mock cascade_degree: positively correlated with gc_peak_value
    (more audio-reliant → denser AND-gate cascade graph).
    cascade_degree ∈ [1, MAX_CASCADE].
    """
    base = peak_values * MAX_CASCADE
    noise = np.random.normal(0, noise_scale * MAX_CASCADE, size=n)
    cascade = np.clip(base + noise, 1, MAX_CASCADE)
    return cascade


def gen_wer(error_risk, noise_scale=5.0):
    """
    WER as inverse function of error_risk + noise.
    error_risk = cascade_degree × gc_peak_value.
    High error_risk → high audio-reliance → low WER.
    WER = (1 - error_risk / max_risk) * 60 + noise.
    """
    max_risk = MAX_CASCADE  # peak_value ≤ 1, so max = MAX_CASCADE
    noise = np.random.normal(0, noise_scale, size=len(error_risk))
    wer = (1 - error_risk / max_risk) * 60 + noise
    return np.clip(wer, 0, 100)


# ──────────────────────────────────────────────
# Analysis
# ──────────────────────────────────────────────

def rmse(y_pred, y_true):
    return float(np.sqrt(np.mean((y_pred - y_true) ** 2)))


def linear_fit_rmse(x, y):
    """Fit y ~ a*x + b, return RMSE on same data (train = test, mock only)."""
    coeffs = np.polyfit(x, y, 1)
    y_hat = np.polyval(coeffs, x)
    return rmse(y_hat, y), coeffs


def report_corr(label, x, y):
    r, p = pearsonr(x, y)
    fit_rmse, _ = linear_fit_rmse(x, y)
    print(f"  {label:45s}  r={r:+.3f}  p={p:.1e}  RMSE={fit_rmse:.2f}%")
    return r, fit_rmse


def main():
    print("=" * 72)
    print("Q140: AND-gate cascade density × gc_peak as WER predictor (mock)")
    print("=" * 72)

    # Generate data
    curves, peak_layers, peak_values = gen_gc_curves(N, K)
    cascade_degree = gen_cascade_degree(N, peak_values)

    # Composite score
    error_risk = cascade_degree * peak_values  # cascade_degree × gc_peak_value

    # Normalised error_risk (for fair comparison)
    error_risk_norm = error_risk / error_risk.max()

    # WER (ground truth proxy)
    wer = gen_wer(error_risk)

    print(f"\nDataset: N={N} utterances, K={K} decoder layers")
    print(f"  gc_peak_value:   mean={peak_values.mean():.3f} ± {peak_values.std():.3f}")
    print(f"  cascade_degree:  mean={cascade_degree.mean():.1f} ± {cascade_degree.std():.1f}")
    print(f"  error_risk:      mean={error_risk.mean():.2f} ± {error_risk.std():.2f}")
    print(f"  WER:             mean={wer.mean():.1f}% ± {wer.std():.1f}%")

    print("\n── Correlations with WER (expect r < −0.7 for predictors of WER) ──")
    r_composite, rmse_composite = report_corr("error_risk = cascade × gc_peak", error_risk, wer)
    r_cascade,   rmse_cascade   = report_corr("cascade_degree alone",           cascade_degree, wer)
    r_peak,      rmse_peak      = report_corr("gc_peak_value alone",            peak_values, wer)
    r_and_frac,  rmse_andfrac   = report_corr("AND-frac(t=1) [Q128 baseline]",  peak_values, wer)

    # Note: AND-frac(t=1) ≈ gc_peak_value in this mock (both drawn from same Beta)
    # In reality AND-frac(t=1) = gc(k=0), while gc_peak is the max across layers.

    print("\n── Ablation: is composite better than components alone? ──")
    better = abs(r_composite) > max(abs(r_cascade), abs(r_peak))
    lower_rmse = rmse_composite < min(rmse_cascade, rmse_peak)
    print(f"  Composite |r| > max(components): {'✅ YES' if better else '❌ NO'}")
    print(f"  Composite RMSE < min(components): {'✅ YES' if lower_rmse else '❌ NO'}")
    print(f"  RMSE improvement vs gc_peak alone: {(rmse_peak - rmse_composite):+.2f}%")
    print(f"  RMSE improvement vs cascade alone: {(rmse_cascade - rmse_composite):+.2f}%")

    print("\n── Threshold test (error_risk below median = high WER risk) ──")
    median_risk = np.median(error_risk)
    low_mask  = error_risk < median_risk
    high_mask = ~low_mask
    print(f"  Low-risk  ({high_mask.sum():3d} utts, error_risk ≥ {median_risk:.1f}): mean WER = {wer[high_mask].mean():.1f}%")
    print(f"  High-risk ({low_mask.sum():3d} utts, error_risk <  {median_risk:.1f}): mean WER = {wer[low_mask].mean():.1f}%")
    gap = wer[low_mask].mean() - wer[high_mask].mean()
    print(f"  WER gap (high-risk vs low-risk): {gap:+.1f}%  → {'✅ meaningful' if gap > 5 else '❌ weak'}")

    print("\n── PASS / FAIL ──────────────────────────────────────────────────────")
    passed = abs(r_composite) > 0.85
    print(f"  Threshold: |r(error_risk, WER)| > 0.85")
    print(f"  Result:    |r| = {abs(r_composite):.3f}  →  {'✅ PASS' if passed else '❌ FAIL'}")

    print("\n── Conclusions ──────────────────────────────────────────────────────")
    if passed and better:
        print("  ✅ Composite score cascade_degree × gc_peak outperforms single-signal.")
        print("  ✅ Utterance-level WER can be predicted zero-cost (no forward pass needed).")
        print("  Next: Q123 (FAD bias × RAVEL Cause/Isolate) or Q127 (stressed syllable × AND-gate).")
    elif passed:
        print("  ✅ Composite passes threshold but does NOT beat components individually.")
        print("  → gc_peak_value is the dominant signal; cascade_degree adds noise in this mock.")
        print("  → In real data, cascade_degree may diverge from peak (graph density ≠ peak value).")
        print("  Next: Q123 or Q127.")
    else:
        print("  ❌ Composite did not reach threshold — reconsider cascade_degree definition.")
        print("  Suggest: use normalised cascade_degree (fraction of features, not count).")

    print("=" * 72)
    return abs(r_composite) > 0.85


if __name__ == "__main__":
    main()
