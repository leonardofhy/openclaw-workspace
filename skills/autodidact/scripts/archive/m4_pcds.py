#!/usr/bin/env python3
"""
AudioSAEBench M4: Pairwise Causal Disentanglement Score (PCDS)
Audio-RAVEL implementation — Cause(F, A) × Isolate(F, A) two-score metric.

Motivation (AudioSAEBench Paper B §3.4):
  SAEBench (text) shows SAEs score well on Cause but poorly on Isolate.
  Audio SAEs likely exhibit MORE cross-attribute leakage than text SAEs due to
  acoustic co-occurrence in training corpora:
    - Voiced consonants correlate with speaker gender in training data
    - Low-pitch voices correlate with male speaker identity
    → A "voicing" feature may also encode speaker gender = Isolate failure

  RAVEL (Huang et al. ACL 2024) introduced Cause/Isolate for TEXT LMs.
  This file ports RAVEL to audio SAE features.

PCDS Definition:
  For a feature F and phonological attribute A:
    Cause(F, A)  = fraction of interchange interventions on F that
                   correctly flip attribute A (localization)
    Isolate(F, A) = fraction of interchange interventions on F where
                   OTHER attributes are NOT accidentally flipped (isolation)
    PCDS(F, A) = harmonic_mean(Cause(F, A), Isolate(F, A))

  Audio-RAVEL mapping (from RAVEL paper):
    entity         → audio stimulus (minimal pair)
    attribute      → phonological feature (voicing, manner, place of articulation)
    interchange    → patch SAE feature F from source stimulus to target stimulus
    "flipped"      → attribute detector changes from source label to target label

Usage (Tier 0 — mock mode, no SAE or real audio required):
    python3 m4_pcds.py --mock
    python3 m4_pcds.py --mock --plot
    python3 m4_pcds.py --mock --attribute voicing --n-pairs 200

Real mode (Tier 1, needs: audio .wav + pre-trained SAE activations):
    python3 m4_pcds.py --activations /path/to/sae_acts.npz --labels /path/to/phoneme_labels.json

Reference:
  - RAVEL: Huang et al. ACL 2024 (Cause/Isolate framework)
  - AudioSAEBench design: memory/learning/pitches/audio_saebench_design.md
  - Choi et al. 2602.18899 (minimal pair stimuli design, 96 languages)
  - Modality Collapse: Zhao et al. 2602.23136 (Gap #30 in goals.md)
"""

import argparse
import json
import math
import random
import sys
from dataclasses import dataclass, asdict
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Phonological attributes under test (Audio-RAVEL §3.4)
PHONOLOGICAL_ATTRIBUTES = ["voicing", "manner", "place", "nasality"]

# Voicing pairs: [source, target] — IPA-style label (mock)
# In real mode: sourced from Choi et al. 2602.18899 validated minimal pairs
VOICING_MINIMAL_PAIRS = [
    ("/b/", "/p/"),  # bilabial voiced / unvoiced stop
    ("/d/", "/t/"),  # alveolar voiced / unvoiced stop
    ("/g/", "/k/"),  # velar voiced / unvoiced stop
    ("/v/", "/f/"),  # labiodental voiced / unvoiced fricative
    ("/z/", "/s/"),  # alveolar voiced / unvoiced fricative
]
MANNER_MINIMAL_PAIRS = [
    ("/b/", "/m/"),  # stop vs nasal (same place, different manner)
    ("/d/", "/n/"),
    ("/f/", "/v/"),  # fricative vs fricative (same manner, different voicing — sanity check)
]
PLACE_MINIMAL_PAIRS = [
    ("/p/", "/t/"),  # bilabial vs alveolar
    ("/t/", "/k/"),  # alveolar vs velar
    ("/b/", "/d/"),  # bilabial vs alveolar voiced
]

ATTRIBUTE_PAIRS = {
    "voicing": VOICING_MINIMAL_PAIRS,
    "manner": MANNER_MINIMAL_PAIRS,
    "place": PLACE_MINIMAL_PAIRS,
}

# Attribute labels (binary, per phoneme)
PHONEME_ATTR_LABELS: dict[str, dict[str, int]] = {
    "/b/": {"voicing": 1, "manner": 0, "place": 0, "nasality": 0},  # voiced stop bilabial
    "/p/": {"voicing": 0, "manner": 0, "place": 0, "nasality": 0},  # unvoiced stop bilabial
    "/d/": {"voicing": 1, "manner": 0, "place": 1, "nasality": 0},  # voiced stop alveolar
    "/t/": {"voicing": 0, "manner": 0, "place": 1, "nasality": 0},  # unvoiced stop alveolar
    "/g/": {"voicing": 1, "manner": 0, "place": 2, "nasality": 0},  # voiced stop velar
    "/k/": {"voicing": 0, "manner": 0, "place": 2, "nasality": 0},  # unvoiced stop velar
    "/v/": {"voicing": 1, "manner": 1, "place": 0, "nasality": 0},  # voiced fricative bilabial
    "/f/": {"voicing": 0, "manner": 1, "place": 0, "nasality": 0},  # unvoiced fricative bilabial
    "/z/": {"voicing": 1, "manner": 1, "place": 1, "nasality": 0},  # voiced fricative alveolar
    "/s/": {"voicing": 0, "manner": 1, "place": 1, "nasality": 0},  # unvoiced fricative alveolar
    "/m/": {"voicing": 1, "manner": 0, "place": 0, "nasality": 1},  # voiced nasal bilabial
    "/n/": {"voicing": 1, "manner": 0, "place": 1, "nasality": 1},  # voiced nasal alveolar
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class MinimalPair:
    """A source–target phoneme pair for interchange intervention."""
    source_phoneme: str
    target_phoneme: str
    pair_id: int
    # Binary attribute labels for source and target
    source_attrs: dict[str, int]
    target_attrs: dict[str, int]


@dataclass
class SAEFeature:
    """Mock SAE feature with activation profile."""
    feature_id: int
    layer: int
    # For mock: whether this feature is truly attribute-specific
    true_attribute: Optional[str]  # None = polysemantic/noise
    # Activation on source and target stimuli (mock)
    activations: dict  # {pair_id: {"source": float, "target": float}}


@dataclass
class FeaturePCDS:
    """PCDS scores for a single feature × attribute pair."""
    feature_id: int
    attribute: str
    cause_score: float
    isolate_score: float
    pcds: float
    n_pairs: int
    cause_details: dict
    isolate_details: dict


# ---------------------------------------------------------------------------
# Minimal pair generator (mock)
# ---------------------------------------------------------------------------

def build_minimal_pairs(attribute: str, n_pairs: int, seed: int = 42) -> list[MinimalPair]:
    """
    Generate mock minimal pairs for a given phonological attribute.
    In real mode: load from Choi et al. 2602.18899 corpus.
    """
    rng = random.Random(seed)
    raw_pairs = ATTRIBUTE_PAIRS.get(attribute, VOICING_MINIMAL_PAIRS)
    pairs = []
    for i in range(n_pairs):
        src, tgt = raw_pairs[i % len(raw_pairs)]
        pairs.append(MinimalPair(
            source_phoneme=src,
            target_phoneme=tgt,
            pair_id=i,
            source_attrs=PHONEME_ATTR_LABELS.get(src, {}),
            target_attrs=PHONEME_ATTR_LABELS.get(tgt, {}),
        ))
    return pairs


# ---------------------------------------------------------------------------
# Mock SAE feature bank with activation profiles
# ---------------------------------------------------------------------------

def build_mock_feature_bank(
    pairs: list[MinimalPair],
    attribute: str,
    n_features: int = 256,
    pct_specialized: float = 0.15,
    pct_polysemantic: float = 0.10,
    seed: int = 7,
) -> list[SAEFeature]:
    """
    Build mock SAE feature bank.

    Three feature classes:
      A. Specialized (15%): true_attribute = attribute → high Cause AND high Isolate
      B. Polysemantic (10%): responds to multiple attributes → high Cause, LOW Isolate
         (this is the "audio leakage" hypothesis from AudioSAEBench §0)
      C. Noise (75%): true_attribute = None → low Cause AND low Isolate
    """
    rng = random.Random(seed)
    features = []
    n_specialized = int(n_features * pct_specialized)
    n_polysemantic = int(n_features * pct_polysemantic)

    for f_id in range(n_features):
        layer = rng.randint(0, 5)  # Whisper-small has 6 encoder layers

        if f_id < n_specialized:
            true_attr = attribute  # monosemantic — responds to target attribute only
        elif f_id < n_specialized + n_polysemantic:
            true_attr = "__polysemantic__"  # responds to ALL attributes (leakage)
        else:
            true_attr = None  # noise

        # Generate activations for each pair (source and target)
        activations = {}
        for pair in pairs:
            if true_attr == attribute:
                # Specialized feature: strong activation on TARGET phoneme of this attribute
                # High activation delta → triggers Cause flip
                src_act = rng.gauss(0.2, 0.1)   # low on source
                tgt_act = rng.gauss(2.8, 0.4)   # high on target → big delta → high Cause
            elif true_attr == "__polysemantic__":
                # Polysemantic: ALSO responds strongly to target phoneme (same as specialized)
                # but also leaks into OTHER attribute detectors (audio leakage)
                # → HIGH Cause (big delta, flips attribute A correctly)
                # → LOW Isolate (big delta also leaks into other attributes)
                src_act = rng.gauss(0.2, 0.1)   # low on source (same as specialized)
                tgt_act = rng.gauss(2.8, 0.4)   # high on target — responds like specialized
                # Polysemantic leakage is handled in compute_pcds via leak_multiplier=1.2
            else:
                # Noise: random, no systematic relationship → small delta → low Cause
                src_act = abs(rng.gauss(0.6, 0.3))
                tgt_act = abs(rng.gauss(0.6, 0.3))

            activations[pair.pair_id] = {
                "source": max(0.0, src_act),
                "target": max(0.0, tgt_act),
            }

        features.append(SAEFeature(
            feature_id=f_id,
            layer=layer,
            true_attribute=true_attr,
            activations=activations,
        ))

    return features


# ---------------------------------------------------------------------------
# Attribute detector (mock)
# ---------------------------------------------------------------------------

def mock_attribute_detector(
    activation_delta: float,
    true_source_label: int,
    true_target_label: int,
    threshold: float = 0.8,
    noise_std: float = 0.15,
    rng: random.Random = None,
) -> tuple[int, int]:
    """
    Simulate an attribute detector's output after SAE feature patching.

    In real mode: this would be a trained linear probe or MFA-aligned classifier.
    In mock mode: uses activation delta to simulate label flip.

    Returns: (detected_source_label, detected_post_patch_label)
    """
    if rng is None:
        rng = random.Random(0)

    # Probe confidence proportional to activation delta (mock)
    confidence = min(1.0, max(0.0, activation_delta / 3.0 + rng.gauss(0, noise_std)))

    # If confidence > threshold, detector flips from source to target label
    if confidence >= threshold:
        detected_post_patch = true_target_label
    else:
        detected_post_patch = true_source_label

    return true_source_label, detected_post_patch


# ---------------------------------------------------------------------------
# PCDS Computation
# ---------------------------------------------------------------------------

def compute_pcds(
    feature: SAEFeature,
    attribute: str,
    pairs: list[MinimalPair],
    other_attributes: list[str],
    threshold: float = 0.8,
    seed: int = 42,
) -> FeaturePCDS:
    """
    Compute Cause(F, A) and Isolate(F, A) for one feature × attribute pair.

    RAVEL interchange intervention protocol (adapted for audio):
      For each minimal pair (src_phoneme, tgt_phoneme):
        1. Take SAE activation from target stimulus (source of intervention)
        2. Patch feature F in source stimulus representation with target activation
        3. Run attribute detector on patched representation
        4. Cause: did the target attribute flip correctly (src_A → tgt_A)?
        5. Isolate: did ALL OTHER attributes remain unchanged?
    """
    rng = random.Random(seed)
    cause_flips = 0
    cause_total = 0
    isolate_no_collateral = 0
    isolate_total = 0

    cause_detail_rows = []
    isolate_detail_rows = []

    for pair in pairs:
        src_act = feature.activations[pair.pair_id]["source"]
        tgt_act = feature.activations[pair.pair_id]["target"]
        activation_delta = tgt_act - src_act

        # ── Cause(F, A): does patching F flip attribute A? ──
        src_label_A = pair.source_attrs.get(attribute, 0)
        tgt_label_A = pair.target_attrs.get(attribute, 0)

        if src_label_A != tgt_label_A:  # only count pairs where attribute actually differs
            _, detected_post_A = mock_attribute_detector(
                activation_delta, src_label_A, tgt_label_A,
                threshold=threshold, rng=rng
            )
            flipped_correctly = (detected_post_A == tgt_label_A)
            cause_flips += int(flipped_correctly)
            cause_total += 1
            cause_detail_rows.append({
                "pair_id": pair.pair_id,
                "src_phoneme": pair.source_phoneme,
                "tgt_phoneme": pair.target_phoneme,
                "delta": round(activation_delta, 3),
                "flipped_correctly": flipped_correctly,
            })

        # ── Isolate(F, A): do OTHER attributes stay unchanged? ──
        collateral_flip = False
        for other_attr in other_attributes:
            if other_attr == attribute:
                continue
            src_label_O = pair.source_attrs.get(other_attr, 0)

            # For Isolate: we ask "does patching F accidentally flip other_attr?"
            # Polysemantic features have a HIGH effective delta for other attributes too
            # (audio leakage hypothesis: acoustic co-occurrence bleeds across attributes)
            is_polysemantic = (feature.true_attribute == "__polysemantic__")
            # Polysemantic features leak strongly; specialized/noise features leak minimally
            leak_multiplier = 1.2 if is_polysemantic else 0.05
            _, detected_O = mock_attribute_detector(
                activation_delta * leak_multiplier,
                src_label_O,
                1 - src_label_O,  # "wrong" = flipped label (collateral damage)
                threshold=threshold,
                noise_std=0.08,
                rng=rng,
            )
            # Collateral flip = detector changed from source label to flipped label
            if detected_O != src_label_O:
                collateral_flip = True
                break

        # Isolation: no collateral flips
        no_collateral = not collateral_flip
        isolate_no_collateral += int(no_collateral)
        isolate_total += 1
        isolate_detail_rows.append({
            "pair_id": pair.pair_id,
            "no_collateral_flip": no_collateral,
            "activation_delta": round(activation_delta, 3),
        })

    # Scores
    cause = cause_flips / cause_total if cause_total > 0 else 0.0
    isolate = isolate_no_collateral / isolate_total if isolate_total > 0 else 0.0
    pcds = harmonic_mean(cause, isolate)

    return FeaturePCDS(
        feature_id=feature.feature_id,
        attribute=attribute,
        cause_score=round(cause, 4),
        isolate_score=round(isolate, 4),
        pcds=round(pcds, 4),
        n_pairs=len(pairs),
        cause_details={"n_flipped": cause_flips, "n_total": cause_total, "rows": cause_detail_rows[:5]},
        isolate_details={"n_no_collateral": isolate_no_collateral, "n_total": isolate_total,
                         "rows": isolate_detail_rows[:5]},
    )


def harmonic_mean(a: float, b: float) -> float:
    """H-mean of two non-negative floats. Returns 0 if either is 0."""
    if a <= 0 or b <= 0:
        return 0.0
    return 2 * a * b / (a + b)


# ---------------------------------------------------------------------------
# Fleet-level PCDS report
# ---------------------------------------------------------------------------

def fleet_report(
    results: list[FeaturePCDS],
    features: list[SAEFeature],
    attribute: str,
    top_k: int = 10,
) -> dict:
    """Aggregate PCDS scores across all features and produce report."""
    feat_map = {f.feature_id: f for f in features}
    n_features = len(features)

    # Statistics
    all_causes = [r.cause_score for r in results]
    all_isolates = [r.isolate_score for r in results]
    all_pcds = [r.pcds for r in results]

    mean_cause = sum(all_causes) / len(all_causes) if all_causes else 0.0
    mean_isolate = sum(all_isolates) / len(all_isolates) if all_isolates else 0.0
    mean_pcds = sum(all_pcds) / len(all_pcds) if all_pcds else 0.0

    # Ground-truth breakdown (mock only)
    specialized_results = [r for r in results
                           if feat_map[r.feature_id].true_attribute == attribute]
    polysemantic_results = [r for r in results
                            if feat_map[r.feature_id].true_attribute == "__polysemantic__"]
    noise_results = [r for r in results
                     if feat_map[r.feature_id].true_attribute is None]

    def mean_pcds_group(group: list[FeaturePCDS]) -> float:
        if not group:
            return 0.0
        return sum(g.pcds for g in group) / len(group)

    # Top-k by PCDS
    top_features = sorted(results, key=lambda r: r.pcds, reverse=True)[:top_k]

    # AudioSAEBench hypothesis check (Gap #30):
    # Polysemantic features should score HIGH Cause but LOW Isolate (audio leakage pattern)
    poly_mean_cause = sum(r.cause_score for r in polysemantic_results) / len(polysemantic_results) \
        if polysemantic_results else 0.0
    poly_mean_isolate = sum(r.isolate_score for r in polysemantic_results) / len(polysemantic_results) \
        if polysemantic_results else 0.0
    leakage_pattern_confirmed = (poly_mean_cause > poly_mean_isolate + 0.15)

    return {
        "version": "AudioSAEBench-M4-PCDS-v0.1",
        "mode": "mock",
        "attribute": attribute,
        "n_features": n_features,
        "fleet_stats": {
            "mean_cause": round(mean_cause, 4),
            "mean_isolate": round(mean_isolate, 4),
            "mean_pcds": round(mean_pcds, 4),
        },
        "gt_breakdown_mock": {
            "specialized": {
                "n": len(specialized_results),
                "mean_pcds": round(mean_pcds_group(specialized_results), 4),
                "mean_cause": round(sum(r.cause_score for r in specialized_results) /
                                    max(1, len(specialized_results)), 4),
                "mean_isolate": round(sum(r.isolate_score for r in specialized_results) /
                                      max(1, len(specialized_results)), 4),
            },
            "polysemantic": {
                "n": len(polysemantic_results),
                "mean_pcds": round(mean_pcds_group(polysemantic_results), 4),
                "mean_cause": round(poly_mean_cause, 4),
                "mean_isolate": round(poly_mean_isolate, 4),
                "leakage_pattern": leakage_pattern_confirmed,
            },
            "noise": {
                "n": len(noise_results),
                "mean_pcds": round(mean_pcds_group(noise_results), 4),
            },
        },
        "gap30_hypothesis": {
            "modality_collapse_proxy": leakage_pattern_confirmed,
            "description": (
                "TRUE: polysemantic features have high Cause but low Isolate — "
                "consistent with audio leakage hypothesis (Gap #30)"
                if leakage_pattern_confirmed
                else
                "FALSE: polysemantic features do not show predicted leakage pattern — "
                "revise hypothesis or check mock parameters"
            ),
        },
        "top_features": [asdict(r) for r in top_features],
    }


# ---------------------------------------------------------------------------
# ASCII plot
# ---------------------------------------------------------------------------

def plot_ascii(report: dict) -> None:
    WIDTH = 25
    top = report["top_features"][:12]
    attr = report["attribute"]
    stats = report["fleet_stats"]

    print(f"\n=== AudioSAEBench M4 PCDS — attribute: {attr} (mock) ===")
    print(f"Fleet: mean_cause={stats['mean_cause']:.3f}  "
          f"mean_isolate={stats['mean_isolate']:.3f}  "
          f"mean_pcds={stats['mean_pcds']:.3f}")
    print()
    gt = report["gt_breakdown_mock"]
    print(f"  Specialized  (n={gt['specialized']['n']:3d}): "
          f"cause={gt['specialized']['mean_cause']:.3f}  "
          f"isolate={gt['specialized']['mean_isolate']:.3f}  "
          f"PCDS={gt['specialized']['mean_pcds']:.3f}  ← expected HIGH")
    print(f"  Polysemantic (n={gt['polysemantic']['n']:3d}): "
          f"cause={gt['polysemantic']['mean_cause']:.3f}  "
          f"isolate={gt['polysemantic']['mean_isolate']:.3f}  "
          f"PCDS={gt['polysemantic']['mean_pcds']:.3f}  ← expected HIGH cause, LOW isolate")
    print(f"  Noise        (n={gt['noise']['n']:3d}): "
          f"PCDS={gt['noise']['mean_pcds']:.3f}  ← expected LOW")
    print()

    gap30 = report["gap30_hypothesis"]
    status = "✅ CONFIRMED" if gap30["modality_collapse_proxy"] else "❌ NOT confirmed"
    print(f"Gap #30 (modality collapse ↔ Isolate): {status}")
    print(f"  {gap30['description']}")
    print()

    print(f"{'FID':<6} {'Layer':<6} {'Cause':>7} {'Isolate':>8} {'PCDS':>7} {'Bar'}")
    print("-" * (WIDTH + 40))
    for r in top:
        bar_len = int(r["pcds"] * WIDTH)
        bar = "█" * bar_len + "░" * (WIDTH - bar_len)
        print(f"  {r['feature_id']:<4} {r.get('layer', '?'):<6} {r['cause_score']:>7.3f} "
              f"{r['isolate_score']:>8.3f} {r['pcds']:>7.3f} |{bar}|")
    print("-" * (WIDTH + 40))
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="AudioSAEBench M4: Pairwise Causal Disentanglement Score"
    )
    parser.add_argument("--mock", action="store_true",
                        help="Tier 0 mock mode (no SAE or audio required)")
    parser.add_argument("--attribute", default="voicing",
                        choices=list(ATTRIBUTE_PAIRS.keys()),
                        help="Phonological attribute to evaluate")
    parser.add_argument("--n-pairs", type=int, default=100,
                        help="Number of minimal pairs per attribute")
    parser.add_argument("--n-features", type=int, default=256,
                        help="Number of mock SAE features")
    parser.add_argument("--top-k", type=int, default=10,
                        help="Number of top features to report")
    parser.add_argument("--threshold", type=float, default=0.8,
                        help="Attribute detector flip threshold")
    parser.add_argument("--plot", action="store_true",
                        help="Print ASCII bar chart")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--activations", type=str, default=None,
                        help="[Tier 1] Path to SAE activations .npz")
    parser.add_argument("--labels", type=str, default=None,
                        help="[Tier 1] Path to phoneme labels .json")
    args = parser.parse_args()

    if not args.mock and (args.activations is None or args.labels is None):
        print("ERROR: Provide --activations and --labels for Tier 1, or use --mock for Tier 0.",
              file=sys.stderr)
        sys.exit(1)

    if not args.mock:
        print("ERROR: Tier 1 (real SAE) not yet implemented. Use --mock.", file=sys.stderr)
        sys.exit(1)

    # ── TIER 0: Mock mode ──
    attribute = args.attribute
    other_attributes = [a for a in PHONOLOGICAL_ATTRIBUTES if a != attribute]

    print(f"[AudioSAEBench M4] attribute={attribute} | n_pairs={args.n_pairs} | "
          f"n_features={args.n_features}", file=sys.stderr)

    # Step 1: Build minimal pairs
    pairs = build_minimal_pairs(attribute, n_pairs=args.n_pairs, seed=args.seed)
    print(f"[pairs] {len(pairs)} minimal pairs loaded", file=sys.stderr)

    # Step 2: Build mock SAE feature bank
    features = build_mock_feature_bank(
        pairs, attribute,
        n_features=args.n_features,
        seed=args.seed + 1,
    )
    n_spec = sum(1 for f in features if f.true_attribute == attribute)
    n_poly = sum(1 for f in features if f.true_attribute == "__polysemantic__")
    n_noise = sum(1 for f in features if f.true_attribute is None)
    print(f"[features] {args.n_features} total: "
          f"{n_spec} specialized / {n_poly} polysemantic / {n_noise} noise",
          file=sys.stderr)

    # Step 3: Compute PCDS for each feature
    print("[computing PCDS for all features...]", file=sys.stderr)
    results = []
    for feature in features:
        pcds_result = compute_pcds(
            feature, attribute, pairs, other_attributes,
            threshold=args.threshold,
            seed=args.seed + 2 + feature.feature_id,
        )
        results.append(pcds_result)

    # Step 4: Fleet report
    report = fleet_report(results, features, attribute, top_k=args.top_k)

    # Step 5: Output
    if args.plot:
        plot_ascii(report)

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
