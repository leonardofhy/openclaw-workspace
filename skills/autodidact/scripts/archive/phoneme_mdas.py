#!/usr/bin/env python3
"""
Q109 — phoneme_mdas.py
SAE feature disentanglement across phoneme attributes (manner, place, voicing).
MDAS Cause/Isolate per attribute.
Mock: 50 features × 3 attributes × 30 phonemes.
"""
import argparse
import json
import sys
import numpy as np
from dataclasses import dataclass, asdict
from typing import List, Dict


@dataclass
class MDASResult:
    attribute: str
    cause_mean: float
    cause_std: float
    isolate_mean: float
    isolate_std: float
    disentanglement_score: float  # cause - isolate gap


def parse_args():
    p = argparse.ArgumentParser(description="Q109: Phoneme MDAS disentanglement analysis")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-features", type=int, default=50)
    p.add_argument("--n-phonemes", type=int, default=30)
    p.add_argument("--json", action="store_true", help="Output JSON")
    return p.parse_args()


def generate_phoneme_activations(rng, n_features, n_phonemes):
    """
    Mock: features activate differentially for phoneme attributes.
    Manner (stop/fricative/nasal), Place (labial/alveolar/velar), Voicing (voiced/unvoiced).
    """
    # Phoneme attribute labels
    manner = rng.integers(0, 3, size=n_phonemes)    # 0=stop,1=fricative,2=nasal
    place  = rng.integers(0, 3, size=n_phonemes)    # 0=labial,1=alveolar,2=velar
    voicing = rng.integers(0, 2, size=n_phonemes)   # 0=unvoiced,1=voiced

    # Feature activations: shape (n_features, n_phonemes)
    # Each feature has a "preferred" attribute combination
    activations = rng.standard_normal((n_features, n_phonemes)) * 0.3

    # Add attribute-driven structure
    for f in range(n_features):
        attr_pref = f % 3
        if attr_pref == 0:  # manner-tuned feature
            for p in range(n_phonemes):
                activations[f, p] += 1.5 * (manner[p] == (f % 3))
        elif attr_pref == 1:  # place-tuned
            for p in range(n_phonemes):
                activations[f, p] += 1.5 * (place[p] == (f % 3))
        else:  # voicing-tuned
            activations[f, p] += 1.2 * voicing[p]

    return activations, manner, place, voicing


def compute_mdas(activations, labels, n_permutations=200, rng=None):
    """
    MDAS Cause: how much does knowing this feature's activation predict the attribute?
    MDAS Isolate: how much does this feature uniquely cause the attribute (minus shared causes)?
    Mock via correlation-based approximation.
    """
    if rng is None:
        rng = np.random.default_rng(42)

    n_features, n_phonemes = activations.shape
    cause_scores = np.zeros(n_features)
    isolate_scores = np.zeros(n_features)

    for f in range(n_features):
        feat = activations[f]
        # Cause: correlation with label
        label_float = labels.astype(float)
        corr = np.corrcoef(feat, label_float)[0, 1]
        cause_scores[f] = abs(corr)

        # Isolate: partial correlation (residual after removing shared variance)
        # Approximate: use permutation-based unique contribution
        perm_corrs = []
        for _ in range(n_permutations // 10):
            perm_label = rng.permutation(label_float)
            perm_corrs.append(abs(np.corrcoef(feat, perm_label)[0, 1]))
        isolate_scores[f] = max(0.0, cause_scores[f] - np.mean(perm_corrs) * 2)

    return cause_scores, isolate_scores


def run_experiment(args):
    rng = np.random.default_rng(args.seed)
    n_features = args.n_features
    n_phonemes = args.n_phonemes

    print(f"Q109: Phoneme MDAS Disentanglement")
    print(f"  Features: {n_features}, Phonemes: {n_phonemes}, Seed: {args.seed}")
    print()

    activations, manner, place, voicing = generate_phoneme_activations(
        rng, n_features, n_phonemes
    )

    attributes = {
        "manner":  manner,
        "place":   place,
        "voicing": voicing,
    }

    results: List[MDASResult] = []

    print(f"{'Attribute':<12} {'Cause μ':>8} {'±σ':>6} {'Isolate μ':>10} {'±σ':>6} {'Disentangle':>12}")
    print("-" * 60)

    for attr_name, labels in attributes.items():
        cause, isolate = compute_mdas(activations, labels, rng=rng)
        res = MDASResult(
            attribute=attr_name,
            cause_mean=float(np.mean(cause)),
            cause_std=float(np.std(cause)),
            isolate_mean=float(np.mean(isolate)),
            isolate_std=float(np.std(isolate)),
            disentanglement_score=float(np.mean(cause) - np.mean(isolate)),
        )
        results.append(res)
        print(
            f"{attr_name:<12} {res.cause_mean:>8.4f} {res.cause_std:>6.4f} "
            f"{res.isolate_mean:>10.4f} {res.isolate_std:>6.4f} "
            f"{res.disentanglement_score:>12.4f}"
        )

    print()

    # Hypothesis: voicing has highest disentanglement (binary, cleanest)
    best = max(results, key=lambda r: r.disentanglement_score)
    print(f"H1: Highest disentanglement attribute = '{best.attribute}' "
          f"(score={best.disentanglement_score:.4f})")

    # Feature specialization: fraction of features that are attribute-selective
    specialization = {}
    thresh = 0.3
    for attr_name, labels in attributes.items():
        cause, _ = compute_mdas(activations, labels, rng=rng)
        specialization[attr_name] = float(np.mean(cause > thresh))

    print()
    print("Feature specialization (fraction with Cause > 0.3):")
    for attr_name, frac in specialization.items():
        print(f"  {attr_name:<12}: {frac:.3f}")

    # Overall disentanglement: mean gap across attributes
    mean_gap = np.mean([r.disentanglement_score for r in results])
    print(f"\nMean disentanglement gap: {mean_gap:.4f}")
    print("\nH2: Features are partially disentangled across phoneme attributes "
          f"[gap={mean_gap:.4f} > 0.05: {'PASS' if mean_gap > 0.05 else 'FAIL'}]")

    if args.json:
        output = {
            "experiment": "Q109",
            "results": [asdict(r) for r in results],
            "specialization": specialization,
            "mean_disentanglement_gap": mean_gap,
        }
        print(json.dumps(output, indent=2))

    return results


def main():
    args = parse_args()
    run_experiment(args)
    print("\nQ109 complete.")
    sys.exit(0)


if __name__ == "__main__":
    main()
