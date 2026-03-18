#!/usr/bin/env python3
"""
Q123 — fad_ravel_cause_isolate.py
FAD bias × RAVEL Cause/Isolate: text-predictable phonemes have low Isolate.
Mock: 30 phonemes × 100 features. Correlate FAD with Isolate.
"""
import argparse
import json
import sys
import numpy as np
from dataclasses import dataclass, asdict
from typing import List


@dataclass
class PhonemeResult:
    phoneme_id: int
    fad_score: float      # Frequency/Acoustic Distinctiveness bias (higher = more text-predictable)
    cause_score: float    # RAVEL Cause: total causal influence
    isolate_score: float  # RAVEL Isolate: unique causal influence (low = shared causes)
    cause_isolate_gap: float


def parse_args():
    p = argparse.ArgumentParser(description="Q123: FAD bias × RAVEL Cause/Isolate correlation")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-phonemes", type=int, default=30)
    p.add_argument("--n-features", type=int, default=100)
    p.add_argument("--n-permutations", type=int, default=100)
    p.add_argument("--json", action="store_true")
    return p.parse_args()


def generate_fad_scores(rng, n_phonemes):
    """
    FAD (Frequency-Acoustic Distinctiveness) score per phoneme.
    High FAD = phoneme is highly text-predictable from context (e.g., schwa, common stops).
    Low FAD  = phoneme is acoustically unique, less predictable.
    """
    return rng.uniform(0.0, 1.0, size=n_phonemes)


def generate_feature_activations(rng, n_phonemes, n_features, fad_scores):
    """
    Feature activations shaped (n_features, n_phonemes).
    Text-predictable (high FAD) phonemes have MORE shared feature activation
    → lower Isolate (their cause is shared/contextual, not unique).
    """
    activations = rng.standard_normal((n_features, n_phonemes)) * 0.3

    # Shared text-context signal
    text_signal = rng.standard_normal(n_features)

    for p in range(n_phonemes):
        # High FAD → activations driven by shared text signal
        alpha = fad_scores[p]
        activations[:, p] += alpha * text_signal * rng.uniform(0.5, 1.5)
        # Low FAD → unique acoustic pattern
        if alpha < 0.4:
            unique = rng.standard_normal(n_features)
            activations[:, p] += (1 - alpha) * unique

    return activations


def compute_ravel_cause_isolate(activations, n_permutations, rng):
    """
    RAVEL Cause: correlation between feature activation and phoneme index.
    RAVEL Isolate: partial cause — unique contribution after removing shared variance.

    Approximation:
    - Cause(p) = mean |corr(feature_f, indicator_p)| across features
    - Isolate(p) = Cause(p) - mean shared_cause
    """
    n_features, n_phonemes = activations.shape
    cause_scores   = np.zeros(n_phonemes)
    isolate_scores = np.zeros(n_phonemes)

    for p in range(n_phonemes):
        indicator = np.zeros(n_phonemes)
        indicator[p] = 1.0

        # Cause: how much do features predict this phoneme indicator?
        corrs = []
        for f in range(n_features):
            c = np.corrcoef(activations[f], indicator)[0, 1]
            if not np.isnan(c):
                corrs.append(abs(c))
        cause_scores[p] = np.mean(corrs) if corrs else 0.0

        # Isolate: permutation-based unique contribution
        perm_causes = []
        for _ in range(n_permutations // 5):
            perm_indicator = rng.permutation(indicator)
            perm_corrs = []
            for f in range(n_features):
                c = np.corrcoef(activations[f], perm_indicator)[0, 1]
                if not np.isnan(c):
                    perm_corrs.append(abs(c))
            perm_causes.append(np.mean(perm_corrs) if perm_corrs else 0.0)

        isolate_scores[p] = max(0.0, cause_scores[p] - np.mean(perm_causes) * 1.5)

    return cause_scores, isolate_scores


def run_experiment(args):
    rng = np.random.default_rng(args.seed)

    print("Q123: FAD Bias × RAVEL Cause/Isolate")
    print(f"  Phonemes: {args.n_phonemes}, Features: {args.n_features}, "
          f"Permutations: {args.n_permutations}, Seed: {args.seed}")
    print()

    fad_scores  = generate_fad_scores(rng, args.n_phonemes)
    activations = generate_feature_activations(rng, args.n_phonemes, args.n_features, fad_scores)
    cause, isolate = compute_ravel_cause_isolate(activations, args.n_permutations, rng)

    gap = cause - isolate

    results: List[PhonemeResult] = []
    for p in range(args.n_phonemes):
        results.append(PhonemeResult(
            phoneme_id=p,
            fad_score=float(fad_scores[p]),
            cause_score=float(cause[p]),
            isolate_score=float(isolate[p]),
            cause_isolate_gap=float(gap[p]),
        ))

    # Correlations
    r_fad_cause   = float(np.corrcoef(fad_scores, cause)[0, 1])
    r_fad_isolate = float(np.corrcoef(fad_scores, isolate)[0, 1])
    r_fad_gap     = float(np.corrcoef(fad_scores, gap)[0, 1])

    print(f"{'Metric':<40} {'Pearson r':>12}")
    print("-" * 54)
    print(f"{'FAD ↔ Cause':<40} {r_fad_cause:>12.4f}")
    print(f"{'FAD ↔ Isolate':<40} {r_fad_isolate:>12.4f}")
    print(f"{'FAD ↔ Cause-Isolate gap':<40} {r_fad_gap:>12.4f}")
    print()

    # Summary stats
    print(f"FAD:     mean={fad_scores.mean():.3f} ± {fad_scores.std():.3f}")
    print(f"Cause:   mean={cause.mean():.4f} ± {cause.std():.4f}")
    print(f"Isolate: mean={isolate.mean():.4f} ± {isolate.std():.4f}")
    print(f"Gap:     mean={gap.mean():.4f} ± {gap.std():.4f}")
    print()

    # Per-phoneme table (top and bottom FAD)
    sorted_by_fad = sorted(results, key=lambda r: r.fad_score, reverse=True)
    print("Top-5 high-FAD phonemes (most text-predictable):")
    print(f"{'ID':>4} {'FAD':>8} {'Cause':>8} {'Isolate':>9} {'Gap':>8}")
    for r in sorted_by_fad[:5]:
        print(f"{r.phoneme_id:>4} {r.fad_score:>8.4f} {r.cause_score:>8.4f} "
              f"{r.isolate_score:>9.4f} {r.cause_isolate_gap:>8.4f}")
    print()
    print("Top-5 low-FAD phonemes (most acoustically unique):")
    for r in sorted_by_fad[-5:]:
        print(f"{r.phoneme_id:>4} {r.fad_score:>8.4f} {r.cause_score:>8.4f} "
              f"{r.isolate_score:>9.4f} {r.cause_isolate_gap:>8.4f}")

    print()
    h1_pass = r_fad_isolate < -0.1
    print(f"H1: High-FAD phonemes have lower Isolate (shared causes)")
    print(f"    r(FAD, Isolate) = {r_fad_isolate:.4f} < -0.1 → {'PASS' if h1_pass else 'FAIL'}")

    h2_pass = r_fad_gap > 0.1
    print(f"H2: High-FAD phonemes have larger Cause-Isolate gap")
    print(f"    r(FAD, gap) = {r_fad_gap:.4f} > 0.1 → {'PASS' if h2_pass else 'FAIL'}")

    if args.json:
        output = {
            "experiment": "Q123",
            "r_fad_cause": r_fad_cause,
            "r_fad_isolate": r_fad_isolate,
            "r_fad_gap": r_fad_gap,
            "h1_pass": h1_pass,
            "h2_pass": h2_pass,
            "results": [asdict(r) for r in results],
        }
        print(json.dumps(output, indent=2))

    return results


def main():
    args = parse_args()
    run_experiment(args)
    print("\nQ123 complete.")
    sys.exit(0)


if __name__ == "__main__":
    main()
