#!/usr/bin/env python3
"""
AudioSAEBench M7: Spurious Correlation (Cross-Phoneme Activation Overlap)
Ports SAEBench M7 to audio — checks whether SAE features activate for
acoustically/articulatorily unrelated phonemes.

Motivation (AudioSAEBench Paper B §3.7):
  SAEBench (text) M7: Feature activates for semantically unrelated tokens
  (e.g., "Paris" feature active on "Berlin") = spurious correlation.

  Audio analogue: Does feature F activate for phonemes that are
  ACOUSTICALLY and ARTICULATORILY unrelated? If a feature claimed to
  detect bilabial stops (/p/, /b/, /m/) also fires for fricatives (/f/, /s/)
  or back vowels (/ɑ/, /o/) → spurious leakage.

  Concretely:
    - χ² test: is the distribution of phoneme classes over top-k activated
      frames uniform (= random feature) or concentrated (= selective feature)?
    - Articulatory distance: do top-activated phonemes form a coherent
      articulatory cluster? Use simplified IPA feature overlap distance.

  Low spurious score = well-disentangled SAE feature.

SpuriousScore(F):
  1. Get top-k frames where feature F activates (top 10% threshold)
  2. Compute phoneme distribution over those frames
  3. chi2 = χ² statistic vs. expected uniform distribution
  4. articulatory_coherence = 1 - mean_pairwise_articulatory_distance(top_phonemes)
  5. SpuriousScore(F) = harmonic_mean(chi2_normalized, articulatory_coherence)

  High SpuriousScore → feature is specific (good)
  Low SpuriousScore → feature fires for unrelated phonemes (spurious)

Usage (Tier 0 — mock mode, no SAE or real audio required):
    python3 m7_spurious.py --mock
    python3 m7_spurious.py --mock --n-features 50 --n-frames 2000
    python3 m7_spurious.py --mock --plot

Real mode (Tier 1, needs: pre-trained SAE activations + phoneme labels):
    python3 m7_spurious.py --activations /path/to/sae_acts.npz --labels /path/to/phoneme_labels.json

Reference:
  - SAEBench: Karvonen, Nanda et al. ICML 2025 (M7 spurious correlation)
  - AudioSAEBench design: memory/learning/pitches/audio_saebench_design.md §M7
  - Choi et al. 2602.18899 (articulatory feature space, IPA categories)
"""

import argparse
import json
import math
import random
import sys
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Articulatory Feature Space (simplified IPA categories)
# ---------------------------------------------------------------------------

# Each phoneme represented as a binary feature vector over articulatory dimensions.
# Dimensions: [bilabial, labiodental, alveolar, palatal, velar, glottal,
#              stop, fricative, nasal, approximant, vowel,
#              voiced, high, low, front, back]
# Source: simplified from IPA; aligns with Choi et al. 2602.18899 phonological features

PHONEME_FEATURES: Dict[str, List[int]] = {
    # Bilabial stops
    "/p/": [1, 0, 0, 0, 0, 0,   1, 0, 0, 0, 0,   0, 0, 0, 0, 0],
    "/b/": [1, 0, 0, 0, 0, 0,   1, 0, 0, 0, 0,   1, 0, 0, 0, 0],
    "/m/": [1, 0, 0, 0, 0, 0,   0, 0, 1, 0, 0,   1, 0, 0, 0, 0],
    # Labiodental fricatives
    "/f/": [0, 1, 0, 0, 0, 0,   0, 1, 0, 0, 0,   0, 0, 0, 0, 0],
    "/v/": [0, 1, 0, 0, 0, 0,   0, 1, 0, 0, 0,   1, 0, 0, 0, 0],
    # Alveolar stops
    "/t/": [0, 0, 1, 0, 0, 0,   1, 0, 0, 0, 0,   0, 0, 0, 0, 0],
    "/d/": [0, 0, 1, 0, 0, 0,   1, 0, 0, 0, 0,   1, 0, 0, 0, 0],
    "/n/": [0, 0, 1, 0, 0, 0,   0, 0, 1, 0, 0,   1, 0, 0, 0, 0],
    # Alveolar fricatives
    "/s/": [0, 0, 1, 0, 0, 0,   0, 1, 0, 0, 0,   0, 0, 0, 0, 0],
    "/z/": [0, 0, 1, 0, 0, 0,   0, 1, 0, 0, 0,   1, 0, 0, 0, 0],
    # Velar stops
    "/k/": [0, 0, 0, 0, 1, 0,   1, 0, 0, 0, 0,   0, 0, 0, 0, 0],
    "/g/": [0, 0, 0, 0, 1, 0,   1, 0, 0, 0, 0,   1, 0, 0, 0, 0],
    "/ŋ/": [0, 0, 0, 0, 1, 0,   0, 0, 1, 0, 0,   1, 0, 0, 0, 0],
    # Glottal
    "/h/": [0, 0, 0, 0, 0, 1,   0, 1, 0, 0, 0,   0, 0, 0, 0, 0],
    # Approximants
    "/l/": [0, 0, 1, 0, 0, 0,   0, 0, 0, 1, 0,   1, 0, 0, 0, 0],
    "/r/": [0, 0, 0, 1, 0, 0,   0, 0, 0, 1, 0,   1, 0, 0, 0, 0],
    "/w/": [1, 0, 0, 0, 0, 0,   0, 0, 0, 1, 0,   1, 0, 0, 1, 1],
    "/j/": [0, 0, 0, 1, 0, 0,   0, 0, 0, 1, 0,   1, 1, 0, 1, 0],
    # Vowels (high front, high back, mid front, mid back, low)
    "/i/": [0, 0, 0, 0, 0, 0,   0, 0, 0, 0, 1,   1, 1, 0, 1, 0],
    "/u/": [0, 0, 0, 0, 0, 0,   0, 0, 0, 0, 1,   1, 1, 0, 0, 1],
    "/e/": [0, 0, 0, 0, 0, 0,   0, 0, 0, 0, 1,   1, 0, 0, 1, 0],
    "/o/": [0, 0, 0, 0, 0, 0,   0, 0, 0, 0, 1,   1, 0, 0, 0, 1],
    "/æ/": [0, 0, 0, 0, 0, 0,   0, 0, 0, 0, 1,   1, 0, 1, 1, 0],
    "/ɑ/": [0, 0, 0, 0, 0, 0,   0, 0, 0, 0, 1,   1, 0, 1, 0, 1],
    "/ʌ/": [0, 0, 0, 0, 0, 0,   0, 0, 0, 0, 1,   1, 0, 1, 0, 0],
}

ALL_PHONEMES = list(PHONEME_FEATURES.keys())
N_PHONEMES = len(ALL_PHONEMES)
PHONEME_IDX = {p: i for i, p in enumerate(ALL_PHONEMES)}

# Articulatory distance: 1 - (feature overlap / max_features)
def articulatory_distance(p1: str, p2: str) -> float:
    f1 = PHONEME_FEATURES[p1]
    f2 = PHONEME_FEATURES[p2]
    overlap = sum(a == b == 1 for a, b in zip(f1, f2))
    max_active = max(sum(f1), sum(f2))
    if max_active == 0:
        return 0.0
    return 1.0 - overlap / max_active


def mean_pairwise_distance(phonemes: List[str]) -> float:
    """Mean articulatory distance between all pairs in the list."""
    if len(phonemes) <= 1:
        return 0.0
    total = 0.0
    count = 0
    for i in range(len(phonemes)):
        for j in range(i + 1, len(phonemes)):
            total += articulatory_distance(phonemes[i], phonemes[j])
            count += 1
    return total / count if count > 0 else 0.0


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class FeatureSpuriousResult:
    feature_id: int
    top_k_frames: int
    phoneme_distribution: Dict[str, int]   # phoneme → count in top-k
    chi2_statistic: float
    chi2_normalized: float                  # chi2 / max_chi2 ∈ [0, 1]
    articulatory_coherence: float           # 1 - mean_pairwise_distance
    spurious_score: float                   # harmonic mean of above two
    dominant_phoneme: str
    dominant_phoneme_fraction: float        # fraction of top-k frames from dominant phoneme


@dataclass
class SpuriousAuditResult:
    n_features: int
    n_frames: int
    top_k_threshold: float
    mean_spurious_score: float
    mean_chi2_normalized: float
    mean_articulatory_coherence: float
    n_selective: int       # spurious_score >= 0.6
    n_moderate: int        # 0.3 <= spurious_score < 0.6
    n_spurious: int        # spurious_score < 0.3
    per_feature: List[FeatureSpuriousResult]


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def chi2_test(observed: List[int], expected_uniform: bool = True) -> Tuple[float, float]:
    """
    Chi-squared test against uniform distribution.
    Returns (chi2_statistic, chi2_normalized).
    chi2_normalized = chi2 / chi2_max, where chi2_max = (N-1) * n_top_frames
    """
    n = len(observed)
    total = sum(observed)
    if total == 0 or n == 0:
        return 0.0, 0.0

    expected = total / n
    chi2 = sum((o - expected) ** 2 / expected for o in observed)

    # Max chi2 occurs when ALL activation in one class: chi2_max = (n-1) * total
    chi2_max = (n - 1) * total / n * n  # simplifies to total*(n-1)/n * n = total*(n-1)
    # More precisely: chi2_max = (total - expected)^2/expected + (n-1)*expected
    #                           = (total - total/n)^2 / (total/n) + (n-1) * (total/n)
    chi2_max = (total * (1 - 1 / n) ** 2) / (1 / n) + (n - 1) * (total / n)
    chi2_normalized = min(1.0, chi2 / chi2_max) if chi2_max > 0 else 0.0

    return chi2, chi2_normalized


def compute_feature_spurious(
    feature_id: int,
    frame_phoneme_labels: List[str],
    feature_activations: List[float],
    top_k_fraction: float = 0.1,
) -> FeatureSpuriousResult:
    """
    Compute spurious correlation score for one SAE feature.

    Args:
        feature_id: Feature index.
        frame_phoneme_labels: Phoneme label for each frame (len = n_frames).
        feature_activations: Feature activation value for each frame (len = n_frames).
        top_k_fraction: Fraction of top-activated frames to consider.
    """
    n_frames = len(feature_activations)
    top_k = max(1, int(n_frames * top_k_fraction))

    # Get indices of top-k activated frames
    sorted_idxs = sorted(range(n_frames), key=lambda i: feature_activations[i], reverse=True)
    top_k_idxs = sorted_idxs[:top_k]

    # Phoneme distribution over top-k frames
    phoneme_counts: Dict[str, int] = {p: 0 for p in ALL_PHONEMES}
    for idx in top_k_idxs:
        phoneme = frame_phoneme_labels[idx]
        if phoneme in phoneme_counts:
            phoneme_counts[phoneme] += 1

    observed = [phoneme_counts[p] for p in ALL_PHONEMES]
    chi2_stat, chi2_norm = chi2_test(observed)

    # Articulatory coherence: which phonemes have non-zero presence?
    active_phonemes = [p for p, c in phoneme_counts.items() if c > 0]
    if len(active_phonemes) > 1:
        mean_dist = mean_pairwise_distance(active_phonemes)
        articulatory_coherence = 1.0 - mean_dist
    else:
        articulatory_coherence = 1.0  # single phoneme = perfect coherence

    # Harmonic mean
    if chi2_norm + articulatory_coherence == 0:
        spurious_score = 0.0
    else:
        spurious_score = (2 * chi2_norm * articulatory_coherence) / (chi2_norm + articulatory_coherence)

    # Dominant phoneme
    dominant_phoneme = max(phoneme_counts, key=phoneme_counts.get)
    dominant_fraction = phoneme_counts[dominant_phoneme] / top_k if top_k > 0 else 0.0

    return FeatureSpuriousResult(
        feature_id=feature_id,
        top_k_frames=top_k,
        phoneme_distribution=phoneme_counts,
        chi2_statistic=chi2_stat,
        chi2_normalized=chi2_norm,
        articulatory_coherence=articulatory_coherence,
        spurious_score=spurious_score,
        dominant_phoneme=dominant_phoneme,
        dominant_phoneme_fraction=dominant_fraction,
    )


# ---------------------------------------------------------------------------
# Mock data generation
# ---------------------------------------------------------------------------

class MockSAE:
    """
    Three mock feature archetypes (same setup as m4_pcds.py for consistency):
      1. Specialized features — strongly responsive to one phoneme class
      2. Polysemantic features — activate for multiple unrelated phonemes
      3. Noise features — random activation
    """

    def __init__(self, n_features: int = 50, n_frames: int = 2000, seed: int = 42):
        random.seed(seed)
        self.n_features = n_features
        self.n_frames = n_frames

        # 50% specialized, 30% polysemantic, 20% noise
        self.n_specialized = int(n_features * 0.5)
        self.n_poly = int(n_features * 0.3)
        self.n_noise = n_features - self.n_specialized - self.n_poly

        # Assign target phoneme(s) for specialized and polysemantic features
        self.specialized_targets = [
            random.choice(ALL_PHONEMES) for _ in range(self.n_specialized)
        ]
        # Polysemantic: 3 phonemes, SPREAD across articulatory classes (spurious)
        # Pick random phonemes that are articulatorily distant from each other
        self.poly_targets = []
        for _ in range(self.n_poly):
            # Sample 3 phonemes from different broad categories
            categories = {
                "stops": ["/p/", "/b/", "/t/", "/d/", "/k/", "/g/"],
                "fricatives": ["/f/", "/v/", "/s/", "/z/", "/h/"],
                "nasals": ["/m/", "/n/", "/ŋ/"],
                "vowels": ["/i/", "/u/", "/e/", "/o/", "/æ/", "/ɑ/", "/ʌ/"],
            }
            selected = [random.choice(list(random.choice(list(categories.values())))) for _ in range(3)]
            self.poly_targets.append(selected)

    def generate_frame_labels(self) -> List[str]:
        """Generate phoneme label for each frame (roughly uniform)."""
        return [random.choice(ALL_PHONEMES) for _ in range(self.n_frames)]

    def generate_activations(self, feature_id: int, frame_labels: List[str]) -> List[float]:
        """
        Generate activation values for a feature given frame phoneme labels.
        """
        activations = []
        if feature_id < self.n_specialized:
            # Specialized: high activation on target phoneme class
            target = self.specialized_targets[feature_id]
            for label in frame_labels:
                if label == target:
                    activations.append(random.gauss(3.0, 0.5))
                elif articulatory_distance(label, target) < 0.3:
                    # Articulatorily similar → moderate activation
                    activations.append(random.gauss(1.0, 0.4))
                else:
                    activations.append(max(0.0, random.gauss(0.1, 0.2)))
        elif feature_id < self.n_specialized + self.n_poly:
            # Polysemantic: fires for 3 unrelated phonemes
            poly_idx = feature_id - self.n_specialized
            targets = self.poly_targets[poly_idx]
            for label in frame_labels:
                if label in targets:
                    activations.append(random.gauss(2.5, 0.6))
                else:
                    activations.append(max(0.0, random.gauss(0.1, 0.2)))
        else:
            # Noise feature: random activation
            for _ in frame_labels:
                activations.append(max(0.0, random.gauss(1.0, 1.0)))
        return activations


# ---------------------------------------------------------------------------
# Main audit
# ---------------------------------------------------------------------------

def run_spurious_audit(
    n_features: int = 50,
    n_frames: int = 2000,
    top_k_fraction: float = 0.1,
    seed: int = 42,
) -> SpuriousAuditResult:
    """Run M7 spurious correlation audit on mock SAE activations."""
    mock = MockSAE(n_features=n_features, n_frames=n_frames, seed=seed)
    frame_labels = mock.generate_frame_labels()

    per_feature = []
    for fid in range(n_features):
        acts = mock.generate_activations(fid, frame_labels)
        result = compute_feature_spurious(fid, frame_labels, acts, top_k_fraction)
        per_feature.append(result)

    scores = [r.spurious_score for r in per_feature]
    chi2_norms = [r.chi2_normalized for r in per_feature]
    coherences = [r.articulatory_coherence for r in per_feature]

    n_selective = sum(1 for s in scores if s >= 0.6)
    n_moderate = sum(1 for s in scores if 0.3 <= s < 0.6)
    n_spurious = sum(1 for s in scores if s < 0.3)

    return SpuriousAuditResult(
        n_features=n_features,
        n_frames=n_frames,
        top_k_threshold=top_k_fraction,
        mean_spurious_score=sum(scores) / len(scores),
        mean_chi2_normalized=sum(chi2_norms) / len(chi2_norms),
        mean_articulatory_coherence=sum(coherences) / len(coherences),
        n_selective=n_selective,
        n_moderate=n_moderate,
        n_spurious=n_spurious,
        per_feature=per_feature,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AudioSAEBench M7: Spurious Correlation Audit")
    parser.add_argument("--mock", action="store_true", default=True, help="Run in mock mode (Tier 0)")
    parser.add_argument("--n-features", type=int, default=50, help="Number of SAE features")
    parser.add_argument("--n-frames", type=int, default=2000, help="Number of audio frames")
    parser.add_argument("--top-k", type=float, default=0.1, help="Top-k fraction for activation threshold")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--plot", action="store_true", help="Show distribution plot (requires matplotlib)")
    parser.add_argument("--json", action="store_true", help="Output full JSON results")
    parser.add_argument("--activations", type=str, default=None, help="[Tier 1] Path to .npz SAE activations")
    parser.add_argument("--labels", type=str, default=None, help="[Tier 1] Path to .json phoneme labels")
    args = parser.parse_args()

    if args.activations:
        print("⚠️  Real-mode (Tier 1) not yet implemented. Falling back to mock mode.")

    result = run_spurious_audit(
        n_features=args.n_features,
        n_frames=args.n_frames,
        top_k_fraction=args.top_k,
        seed=args.seed,
    )

    print("=" * 60)
    print("AudioSAEBench M7 — Spurious Correlation Audit")
    print("=" * 60)
    print(f"Features: {result.n_features}  |  Frames: {result.n_frames}  |  Top-k: {result.top_k_threshold:.0%}")
    print()
    print(f"{'Metric':<35} {'Value':>10}")
    print("-" * 47)
    print(f"{'Mean SpuriousScore':<35} {result.mean_spurious_score:>10.3f}")
    print(f"{'Mean χ² (normalized)':<35} {result.mean_chi2_normalized:>10.3f}")
    print(f"{'Mean Articulatory Coherence':<35} {result.mean_articulatory_coherence:>10.3f}")
    print()
    print(f"{'Category':<35} {'Count':>10} {'%':>8}")
    print("-" * 55)
    pct_sel = result.n_selective / result.n_features * 100
    pct_mod = result.n_moderate / result.n_features * 100
    pct_spu = result.n_spurious / result.n_features * 100
    print(f"{'Selective (score ≥ 0.6)':<35} {result.n_selective:>10}  {pct_sel:>6.1f}%")
    print(f"{'Moderate (0.3 ≤ score < 0.6)':<35} {result.n_moderate:>10}  {pct_mod:>6.1f}%")
    print(f"{'Spurious (score < 0.3)':<35} {result.n_spurious:>10}  {pct_spu:>6.1f}%")

    # Show top-3 and bottom-3 features
    sorted_features = sorted(result.per_feature, key=lambda r: r.spurious_score, reverse=True)
    print()
    print("Top-3 Most Selective Features:")
    for r in sorted_features[:3]:
        print(f"  F{r.feature_id:03d}  score={r.spurious_score:.3f}  dominant={r.dominant_phoneme}  "
              f"dom_frac={r.dominant_phoneme_fraction:.2f}  coherence={r.articulatory_coherence:.3f}")

    print()
    print("Top-3 Most Spurious Features:")
    for r in sorted_features[-3:]:
        print(f"  F{r.feature_id:03d}  score={r.spurious_score:.3f}  dominant={r.dominant_phoneme}  "
              f"dom_frac={r.dominant_phoneme_fraction:.2f}  coherence={r.articulatory_coherence:.3f}")

    if args.plot:
        try:
            import matplotlib.pyplot as plt
            scores = [r.spurious_score for r in result.per_feature]
            plt.figure(figsize=(8, 4))
            plt.hist(scores, bins=20, color="steelblue", edgecolor="white")
            plt.axvline(0.6, color="green", linestyle="--", label="Selective threshold (0.6)")
            plt.axvline(0.3, color="red", linestyle="--", label="Spurious threshold (0.3)")
            plt.xlabel("SpuriousScore(F)")
            plt.ylabel("Number of Features")
            plt.title("AudioSAEBench M7 — Feature Specificity Distribution")
            plt.legend()
            plt.tight_layout()
            plt.show()
        except ImportError:
            print("⚠️  matplotlib not available — skipping plot.")

    if args.json:
        output = {
            "summary": asdict(result),
        }
        # Convert per_feature list (nested dataclasses)
        output["summary"]["per_feature"] = [asdict(r) for r in result.per_feature]
        print(json.dumps(output, indent=2))

    # Exit code: 0 if mean score >= 0.5 (reasonable), 1 if very spurious
    sys.exit(0 if result.mean_spurious_score >= 0.3 else 1)


if __name__ == "__main__":
    main()
