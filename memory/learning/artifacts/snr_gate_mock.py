"""
snr_gate_mock.py
================
Q153: gc(k) × SNR robustness — AND-gate features degrade faster under noise than OR-gate.

Hypothesis:
  At high SNR (clean audio), AND-gate features dominate at gc(k) peak:
    the model is truly LISTENING (audio-grounded → AND-frac high).
  Under noise (low SNR), acoustic evidence is corrupted:
    AND-gate features degrade (can't ground in corrupted signal).
    OR-gate features partially persist (language priors remain active).
  Therefore:
    slope(AND-frac vs SNR) > 2 × slope(OR-frac vs SNR)  [in magnitude]

  This links to hearing degradation models:
    - Human auditory cortex: degraded SNR → cortical feature detectors fail (AND)
      but phoneme completion from context persists (OR / top-down prediction)
    - Whisper behaves similarly: audio commitment collapses under noise

Mock setup:
  - SNR levels: 0, 5, 10, 15, 20, 25, 30 dB
  - N_SAMPLES = 40 mock audio clips per SNR level
  - For each sample + SNR level:
      * gc_peak position: drawn from Uniform(3, 8) (Whisper encoder depth 0..11)
      * noise_corruption factor: alpha = 1 / (1 + 10^(SNR/10))
        (proportion of activation variance destroyed by noise)
      * AND-frac at gc_peak:
          base_and_frac ~ Uniform(0.55, 0.80) at clean SNR
          add noise: and_frac(SNR) = base × (1 - alpha) + Uniform(0.05, 0.15) × alpha
          [signal part degrades, replaced by random low AND-frac from noise]
      * OR-frac at gc_peak:
          base_or_frac = 1 - base_and_frac - Uniform(0.0, 0.15)  (mixed features)
          or_frac(SNR) = base_or_frac × (1 - 0.3*alpha) + Uniform(0.05, 0.10) × 0.3*alpha
          [OR-frac degrades only slightly — language priors are noise-robust]
  - Fit linear regression: AND-frac ~ SNR, OR-frac ~ SNR
  - Check: |slope_AND| > 2 × |slope_OR|

Connections to thesis:
  - AND-gate = audio-committed features (hear the phoneme) → SNR sensitive
  - OR-gate = language-prior features (predict the phoneme) → SNR robust
  - This explains Whisper's hallucination pattern: low SNR → collapse to OR-only → hallucination
  - Safety implication: adversarial audio at low SNR may preferentially disable AND-gate
    grounding while preserving OR-gate language generation → steered outputs

Open questions:
  - At what SNR threshold does AND-frac drop below OR-frac? (crossover point)
  - Do different phoneme classes have different SNR robustness?
  - Can we use SNR-dependent AND-frac as a confidence calibration signal?
"""

import numpy as np

# ── Reproducibility ─────────────────────────────────────────────────────────
RNG = np.random.default_rng(42)

# ── Config ───────────────────────────────────────────────────────────────────
SNR_DB   = [0, 5, 10, 15, 20, 25, 30]   # dB
N        = 40                            # samples per SNR level


def noise_alpha(snr_db: float) -> float:
    """Fraction of activation variance destroyed by noise."""
    return 1.0 / (1.0 + 10 ** (snr_db / 10.0))


def simulate_snr_level(snr_db: float, n: int) -> tuple[float, float]:
    """
    Returns (mean_and_frac, mean_or_frac) at a given SNR level.
    """
    alpha = noise_alpha(snr_db)

    # Base (clean) fractions — audio-grounded clip
    base_and = RNG.uniform(0.55, 0.80, size=n)
    base_or  = RNG.uniform(0.10, 0.30, size=n)
    # Ensure base_and + base_or <= 1 (remainder = "neutral" features)
    base_or  = np.minimum(base_or, 1.0 - base_and - 0.05)

    # Noise corruption
    noise_and   = RNG.uniform(0.05, 0.15, size=n)   # AND-frac collapses under noise
    noise_or    = RNG.uniform(0.05, 0.10, size=n)   # OR-frac barely changes (priors persist)

    and_frac = base_and * (1.0 - alpha)      + noise_and * alpha
    or_frac  = base_or  * (1.0 - 0.3*alpha) + noise_or  * (0.3*alpha)

    return float(and_frac.mean()), float(or_frac.mean())


def linear_slope(xs: list, ys: list) -> float:
    """OLS slope."""
    x = np.array(xs, dtype=float)
    y = np.array(ys, dtype=float)
    x_c = x - x.mean()
    return float((x_c @ y) / (x_c @ x_c))


def pearsonr(x, y):
    xm, ym = np.array(x) - np.mean(x), np.array(y) - np.mean(y)
    denom = (np.sqrt((xm**2).sum()) * np.sqrt((ym**2).sum()))
    return float((xm @ ym) / denom) if denom > 0 else 0.0


# ── Main ─────────────────────────────────────────────────────────────────────
def run():
    and_means, or_means = [], []

    print("SNR(dB) | AND-frac | OR-frac | AND/OR ratio")
    print("-" * 48)
    for snr in SNR_DB:
        a, o = simulate_snr_level(snr, N)
        and_means.append(a)
        or_means.append(o)
        print(f"  {snr:5d} |   {a:.3f}  |  {o:.3f}  |   {a/o:.2f}x")

    print()
    slope_and = linear_slope(SNR_DB, and_means)
    slope_or  = linear_slope(SNR_DB, or_means)
    r_and     = pearsonr(SNR_DB, and_means)
    r_or      = pearsonr(SNR_DB, or_means)

    print(f"AND-frac: slope = {slope_and:+.4f}/dB  r = {r_and:+.3f}")
    print(f"OR-frac:  slope = {slope_or:+.4f}/dB  r = {r_or:+.3f}")
    print()

    crossover = None
    for i in range(len(SNR_DB) - 1):
        if (and_means[i] > or_means[i]) and (and_means[i+1] <= or_means[i+1]):
            crossover = (SNR_DB[i] + SNR_DB[i+1]) / 2
    if crossover is not None:
        print(f"AND/OR crossover ≈ {crossover} dB  (AND-frac drops below OR-frac)")
    else:
        print("No crossover in tested SNR range (AND-frac dominant throughout)")

    print()
    ratio = abs(slope_and) / abs(slope_or) if abs(slope_or) > 1e-9 else float("inf")
    criterion = ratio > 2.0
    status = "✅ PASS" if criterion else "❌ FAIL"
    print(f"Criterion |slope_AND| > 2× |slope_OR|: {ratio:.2f}x  →  {status}")

    # Hearing degradation connection
    print()
    print("Hearing degradation analogy:")
    print("  AND-gate (audio-committed):   degrades like cortical feature detectors")
    print("  OR-gate  (language-prior):    persists like top-down phoneme prediction")
    and_drop = and_means[0] - and_means[-1]
    or_drop  = or_means[0]  - or_means[-1]
    print(f"  AND-frac drop (0→30dB SNR): {and_drop:+.3f}")
    print(f"  OR-frac  drop (0→30dB SNR): {or_drop:+.3f}")
    print(f"  → AND degrades {and_drop/or_drop:.1f}× faster than OR")

    return criterion, ratio, crossover


if __name__ == "__main__":
    ok, ratio, crossover = run()
    import sys
    sys.exit(0 if ok else 1)
