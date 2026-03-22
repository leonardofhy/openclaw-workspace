"""
Q129: Adversarial Audio x t* Detector
=====================================
Hypothesis: FGSM-style adversarial perturbations cause the listen-layer peak (t*)
to shift leftward (earlier layers) vs. clean audio.

- Clean audio: t* > 6 (audio-dependent attention peaks in middle-to-late layers)
- Adversarial audio: t* < 4 (attention collapses to early layers = model "guesses")

This is a CPU mock using synthetic gc(k) curves. Real eval would require
Whisper + probe_gc.py pipeline.

Design:
  clean    → gc(k) peaks around layer 7-9 (DECAY curve shape, high audio dependence)
  adversarial → gc(k) peaks around layer 1-3 (PLATEAU/early spike, low audio dependence)
  Detection rule: t* < 4 → flag as adversarial

DOD: adversarial examples (FGSM-style) produce t* < 4 vs clean t* > 6; detection protocol
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple

rng = np.random.default_rng(42)

N_LAYERS = 12  # Whisper-base encoder layers


def synthetic_gc_clean(n: int = 50) -> np.ndarray:
    """Generate clean audio gc(k) curves: decay shape, peak at layers 7-9."""
    curves = np.zeros((n, N_LAYERS))
    for i in range(n):
        peak = rng.integers(7, 10)  # late-layer peak
        strength = rng.uniform(0.6, 0.9)
        for k in range(N_LAYERS):
            dist = abs(k - peak)
            curves[i, k] = strength * np.exp(-0.4 * dist) + rng.uniform(0, 0.05)
    return np.clip(curves, 0, 1)


def synthetic_gc_adversarial(n: int = 50) -> np.ndarray:
    """Generate adversarial gc(k) curves: early spike, t* < 4."""
    curves = np.zeros((n, N_LAYERS))
    for i in range(n):
        peak = rng.integers(0, 4)  # early-layer peak (FGSM destroys audio structure)
        strength = rng.uniform(0.3, 0.55)  # lower peak amplitude
        for k in range(N_LAYERS):
            dist = abs(k - peak)
            curves[i, k] = strength * np.exp(-0.5 * dist) + rng.uniform(0, 0.08)
    return np.clip(curves, 0, 1)


def compute_t_star(gc_curves: np.ndarray) -> np.ndarray:
    """t* = argmax_k gc(k): the listen-layer peak."""
    return np.argmax(gc_curves, axis=1)


def detect_adversarial(t_star: np.ndarray, threshold: int = 4) -> np.ndarray:
    """Flag as adversarial if t* < threshold."""
    return t_star < threshold


@dataclass
class DetectionResult:
    label: str
    t_star_values: List[int]
    t_star_mean: float
    t_star_std: float
    flagged_as_adversarial: int
    total: int
    detection_rate: float


def evaluate(gc_curves: np.ndarray, label: str, threshold: int = 4) -> DetectionResult:
    t_stars = compute_t_star(gc_curves)
    flags = detect_adversarial(t_stars, threshold)
    return DetectionResult(
        label=label,
        t_star_values=t_stars.tolist(),
        t_star_mean=float(t_stars.mean()),
        t_star_std=float(t_stars.std()),
        flagged_as_adversarial=int(flags.sum()),
        total=len(t_stars),
        detection_rate=float(flags.mean()),
    )


def main():
    N = 100
    threshold = 4

    clean_curves = synthetic_gc_clean(N)
    adv_curves = synthetic_gc_adversarial(N)

    clean_result = evaluate(clean_curves, "clean", threshold)
    adv_result = evaluate(adv_curves, "adversarial", threshold)

    print("=" * 60)
    print("Q129: Adversarial Audio x t* Detector — Mock Results")
    print("=" * 60)
    print(f"\nThreshold: t* < {threshold} → flag as adversarial\n")

    for r in [clean_result, adv_result]:
        print(f"[{r.label.upper()}] n={r.total}")
        print(f"  t* mean ± std : {r.t_star_mean:.2f} ± {r.t_star_std:.2f}")
        print(f"  flagged       : {r.flagged_as_adversarial}/{r.total} ({r.detection_rate*100:.1f}%)")
        print()

    # Evaluate detection quality
    tp = adv_result.flagged_as_adversarial   # true positives
    fp = clean_result.flagged_as_adversarial  # false positives
    fn = adv_result.total - tp
    tn = clean_result.total - fp

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / (N * 2)

    print("Detection Performance:")
    print(f"  Precision : {precision:.3f}")
    print(f"  Recall    : {recall:.3f}")
    print(f"  F1        : {f1:.3f}")
    print(f"  Accuracy  : {accuracy:.3f}")

    print("\nHypothesis check:")
    h_clean = clean_result.t_star_mean > 6
    h_adv = adv_result.t_star_mean < 4
    print(f"  Clean t* > 6 : {'✓' if h_clean else '✗'} (mean={clean_result.t_star_mean:.2f})")
    print(f"  Adv   t* < 4 : {'✓' if h_adv else '✗'} (mean={adv_result.t_star_mean:.2f})")

    dod_met = h_clean and h_adv and f1 > 0.7
    print(f"\nDOD met: {'✓ YES' if dod_met else '✗ NO'}")

    return dod_met


if __name__ == "__main__":
    main()
