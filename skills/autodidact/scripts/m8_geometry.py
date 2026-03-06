#!/usr/bin/env python3
"""
AudioSAEBench M8: Feature Geometry (Phonological Cluster Geometry)
Ports SAEBench M8 to audio — analyzes the cosine similarity structure
between SAE feature vectors to detect superposition and phonological clustering.

Motivation (AudioSAEBench Paper B §3.8):
  SAEBench (text) M8: Cosine similarity structure between feature vectors;
  anti-podal features (cosine ≈ -1.0) encode binary semantic distinctions.

  Audio advantage: Phonological features have STRONGER theoretical priors
  for geometry than text:
    - voiced/unvoiced = binary → expect anti-podal feature pairs (/b/ vs /p/)
    - place of articulation = categorical → expect intra-class clusters
      (bilabials: /p/, /b/, /m/ should cluster together)
    - Audio SAEs should score BETTER than text SAEs on geometry (Paper B §2.1 framing)

  GeometryScore:
    - Phonological Cluster Geometry:
        cluster_score = mean(intra_class_cosim) / mean(inter_class_cosim)
        (should be > 2.0 for well-structured SAE)
    - Anti-podal Detection:
        n_antipodal = count of (F_i, F_j) pairs with cosine < -0.5
        (voiced/unvoiced features should be anti-podal)
    - Superposition Index:
        fraction of features with multiple high-cosine neighbors (> 0.5)
        (low = good; high = superposition)

Usage (Tier 0 — mock mode, no SAE or real audio required):
    python3 m8_geometry.py --mock
    python3 m8_geometry.py --mock --n-features 100
    python3 m8_geometry.py --mock --plot

Real mode (Tier 1, needs: pre-trained SAE — feature weight matrix):
    python3 m8_geometry.py --weights /path/to/sae_weights.npz

Reference:
  - SAEBench: Karvonen, Nanda et al. ICML 2025 (M8 feature geometry)
  - AudioSAEBench design: memory/learning/pitches/audio_saebench_design.md §M8
  - Choi et al. 2602.18899 (phonological feature space, IPA categories)
  - Matryoshka SAE: Bussmann et al. ICML 2025 (hierarchical geometry)
"""

import argparse
import json
import math
import random
import sys
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Phonological class definitions (from m7_spurious.py articulatory space)
# ---------------------------------------------------------------------------

PHONOLOGICAL_CLASSES: Dict[str, List[str]] = {
    "bilabial_stop": ["/p/", "/b/"],
    "bilabial_nasal": ["/m/"],
    "labiodental_fricative": ["/f/", "/v/"],
    "alveolar_stop": ["/t/", "/d/"],
    "alveolar_nasal": ["/n/"],
    "alveolar_fricative": ["/s/", "/z/"],
    "alveolar_approximant": ["/l/", "/r/"],
    "velar_stop": ["/k/", "/g/"],
    "velar_nasal": ["/ŋ/"],
    "glottal": ["/h/"],
    "palatal_approx": ["/j/", "/w/"],
    "high_vowel": ["/i/", "/u/"],
    "mid_vowel": ["/e/", "/o/"],
    "low_vowel": ["/æ/", "/ɑ/", "/ʌ/"],
}

# Voiced/unvoiced pairs (expected anti-podal)
VOICING_PAIRS: List[Tuple[str, str]] = [
    ("/p/", "/b/"),  # bilabial stop: unvoiced / voiced
    ("/t/", "/d/"),  # alveolar stop: unvoiced / voiced
    ("/k/", "/g/"),  # velar stop: unvoiced / voiced
    ("/f/", "/v/"),  # labiodental fricative: unvoiced / voiced
    ("/s/", "/z/"),  # alveolar fricative: unvoiced / voiced
]

# Broader manner-of-articulation groups for cluster analysis
MANNER_GROUPS: Dict[str, List[str]] = {
    "stop": ["/p/", "/b/", "/t/", "/d/", "/k/", "/g/"],
    "nasal": ["/m/", "/n/", "/ŋ/"],
    "fricative": ["/f/", "/v/", "/s/", "/z/", "/h/"],
    "approximant": ["/l/", "/r/", "/w/", "/j/"],
    "vowel": ["/i/", "/u/", "/e/", "/o/", "/æ/", "/ɑ/", "/ʌ/"],
}

ALL_PHONEMES = [p for phonemes in MANNER_GROUPS.values() for p in phonemes]
N_PHONEMES = len(ALL_PHONEMES)
PHONEME_TO_CLASS = {}
for cls_name, phonemes in MANNER_GROUPS.items():
    for p in phonemes:
        PHONEME_TO_CLASS[p] = cls_name


# ---------------------------------------------------------------------------
# Vector math helpers
# ---------------------------------------------------------------------------

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a ** 2 for a in v1))
    norm2 = math.sqrt(sum(b ** 2 for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def normalize(v: List[float]) -> List[float]:
    norm = math.sqrt(sum(x ** 2 for x in v))
    if norm == 0:
        return v
    return [x / norm for x in v]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PairGeometry:
    feature_i: int
    feature_j: int
    phoneme_i: str       # dominant phoneme for feature i
    phoneme_j: str       # dominant phoneme for feature j
    cosine_sim: float
    same_manner: bool    # same manner-of-articulation class
    is_voicing_pair: bool  # is this a known voiced/unvoiced pair


@dataclass
class GeometryResult:
    n_features: int
    d_model: int
    # Cluster geometry
    mean_intra_class_cosim: float    # same manner-of-articulation
    mean_inter_class_cosim: float    # different manner
    cluster_score: float             # intra / inter (> 2.0 = good structure)
    # Anti-podal pairs
    n_antipodal_pairs: int           # cosine < -0.5
    n_voicing_antipodal: int         # voicing pairs with cosine < -0.5
    n_voicing_pairs_total: int       # total voicing pair feature counts found
    # Superposition index
    superposition_index: float       # fraction of features with > 1 high-cosim neighbor (>0.5)
    # Distribution summary
    mean_pairwise_cosim: float
    std_pairwise_cosim: float
    # Top-k pair examples
    most_similar_pairs: List[PairGeometry] = field(default_factory=list)
    most_antipodal_pairs: List[PairGeometry] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Mock SAE weight generation
# ---------------------------------------------------------------------------

class MockSAEWeights:
    """
    Generate synthetic SAE feature weight vectors with phonological structure.

    Each feature has a 'dominant phoneme'. Feature vectors are constructed
    so that same-class features are more similar, and voiced/unvoiced pairs
    have partially opposing directions.

    Three archetypes:
      - Phonological: feature weight vector = noisy version of a canonical
        phoneme direction in a shared d_model-dimensional space.
        Same-manner phonemes share a subspace → intra-class cosim high.
        Voicing dimension is a unit vector; voiced features have +1, unvoiced -1
        → anti-podal when voicing is the dominant dimension.
      - Polysemantic: mixture of two phoneme directions (different manners)
        → blurs cluster structure.
      - Random: uniformly random unit vectors → no structure.
    """

    def __init__(
        self,
        n_features: int = 100,
        d_model: int = 64,
        seed: int = 42,
        n_phonological: Optional[int] = None,
        n_poly: Optional[int] = None,
    ):
        random.seed(seed)
        self.n_features = n_features
        self.d_model = d_model

        n_phonological = n_phonological if n_phonological is not None else int(n_features * 0.6)
        n_poly = n_poly if n_poly is not None else int(n_features * 0.2)
        n_random = n_features - n_phonological - n_poly

        self.feature_type = (
            ["phonological"] * n_phonological
            + ["polysemantic"] * n_poly
            + ["random"] * n_random
        )

        # Generate canonical phoneme basis vectors (one per phoneme)
        # Manner groups share a subspace (first d_manner dims overlap)
        d_manner = d_model // len(MANNER_GROUPS)
        self.phoneme_bases: Dict[str, List[float]] = {}
        manner_offsets = {m: i * d_manner for i, m in enumerate(MANNER_GROUPS.keys())}

        for phoneme, manner in PHONEME_TO_CLASS.items():
            base = [0.0] * d_model
            offset = manner_offsets[manner]
            # Set the manner subspace dims
            for k in range(d_manner):
                base[offset + k] = random.gauss(1.0, 0.2)
            # Add voicing dimension (last dim in d_model)
            # Voiced = +1, unvoiced = -1 (creates anti-podal structure)
            voiced_phonemes = ["/b/", "/d/", "/g/", "/v/", "/z/", "/m/", "/n/", "/ŋ/",
                               "/l/", "/r/", "/w/", "/j/",
                               "/i/", "/u/", "/e/", "/o/", "/æ/", "/ɑ/", "/ʌ/"]
            base[d_model - 1] = 1.0 if phoneme in voiced_phonemes else -1.0
            self.phoneme_bases[phoneme] = normalize(base)

        # Assign dominant phoneme to each feature
        self.dominant_phonemes: List[str] = []
        for i in range(n_features):
            self.dominant_phonemes.append(random.choice(ALL_PHONEMES))

    def get_feature_vector(self, feature_id: int) -> List[float]:
        """Return weight vector for a given feature."""
        feat_type = self.feature_type[feature_id]
        dominant = self.dominant_phonemes[feature_id]

        if feat_type == "phonological":
            base = self.phoneme_bases[dominant]
            # Add small noise
            noisy = [b + random.gauss(0, 0.15) for b in base]
            return normalize(noisy)

        elif feat_type == "polysemantic":
            # Mix two phonemes from DIFFERENT manner groups
            p2 = random.choice([p for p in ALL_PHONEMES if PHONEME_TO_CLASS[p] != PHONEME_TO_CLASS[dominant]])
            b1 = self.phoneme_bases[dominant]
            b2 = self.phoneme_bases[p2]
            alpha = random.uniform(0.4, 0.6)
            mixed = [alpha * a + (1 - alpha) * b + random.gauss(0, 0.1) for a, b in zip(b1, b2)]
            return normalize(mixed)

        else:  # random
            vec = [random.gauss(0, 1.0) for _ in range(self.d_model)]
            return normalize(vec)

    def get_all_vectors(self) -> List[List[float]]:
        return [self.get_feature_vector(i) for i in range(self.n_features)]


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def run_geometry_audit(
    n_features: int = 100,
    d_model: int = 64,
    seed: int = 42,
    top_k_pairs: int = 5,
) -> GeometryResult:
    """Run M8 feature geometry audit on mock SAE weights."""
    mock = MockSAEWeights(n_features=n_features, d_model=d_model, seed=seed)
    vectors = mock.get_all_vectors()
    dominant_phonemes = mock.dominant_phonemes

    # Compute all pairwise cosine similarities
    all_pairs: List[PairGeometry] = []
    intra_cosims: List[float] = []
    inter_cosims: List[float] = []
    all_cosims: List[float] = []
    high_cosim_neighbors: Dict[int, int] = {i: 0 for i in range(n_features)}

    for i in range(n_features):
        for j in range(i + 1, n_features):
            csim = cosine_similarity(vectors[i], vectors[j])
            all_cosims.append(csim)

            p_i = dominant_phonemes[i]
            p_j = dominant_phonemes[j]
            same_manner = PHONEME_TO_CLASS.get(p_i) == PHONEME_TO_CLASS.get(p_j)
            is_voicing_pair = (
                (p_i, p_j) in VOICING_PAIRS or (p_j, p_i) in VOICING_PAIRS
            )

            pair = PairGeometry(
                feature_i=i,
                feature_j=j,
                phoneme_i=p_i,
                phoneme_j=p_j,
                cosine_sim=csim,
                same_manner=same_manner,
                is_voicing_pair=is_voicing_pair,
            )
            all_pairs.append(pair)

            if same_manner:
                intra_cosims.append(csim)
            else:
                inter_cosims.append(csim)

            if csim > 0.5:
                high_cosim_neighbors[i] += 1
                high_cosim_neighbors[j] += 1

    mean_intra = sum(intra_cosims) / len(intra_cosims) if intra_cosims else 0.0
    mean_inter = sum(inter_cosims) / len(inter_cosims) if inter_cosims else 1.0
    cluster_score = mean_intra / mean_inter if mean_inter != 0 else float("inf")

    # Anti-podal pairs
    antipodal = [p for p in all_pairs if p.cosine_sim < -0.5]
    n_antipodal = len(antipodal)
    n_voicing_antipodal = sum(1 for p in antipodal if p.is_voicing_pair)
    n_voicing_pairs_total = sum(1 for p in all_pairs if p.is_voicing_pair)

    # Superposition index
    superposition_count = sum(1 for i in range(n_features) if high_cosim_neighbors[i] > 1)
    superposition_index = superposition_count / n_features

    # Overall cosim stats
    mean_cosim = sum(all_cosims) / len(all_cosims) if all_cosims else 0.0
    var_cosim = sum((c - mean_cosim) ** 2 for c in all_cosims) / len(all_cosims) if all_cosims else 0.0
    std_cosim = math.sqrt(var_cosim)

    # Top-k most similar and most anti-podal
    sorted_by_sim = sorted(all_pairs, key=lambda p: p.cosine_sim, reverse=True)
    most_similar = sorted_by_sim[:top_k_pairs]
    most_antipodal = sorted_by_sim[-top_k_pairs:]

    return GeometryResult(
        n_features=n_features,
        d_model=d_model,
        mean_intra_class_cosim=mean_intra,
        mean_inter_class_cosim=mean_inter,
        cluster_score=cluster_score,
        n_antipodal_pairs=n_antipodal,
        n_voicing_antipodal=n_voicing_antipodal,
        n_voicing_pairs_total=n_voicing_pairs_total,
        superposition_index=superposition_index,
        mean_pairwise_cosim=mean_cosim,
        std_pairwise_cosim=std_cosim,
        most_similar_pairs=most_similar,
        most_antipodal_pairs=most_antipodal,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AudioSAEBench M8: Feature Geometry Audit")
    parser.add_argument("--mock", action="store_true", default=True, help="Run in mock mode (Tier 0)")
    parser.add_argument("--n-features", type=int, default=100, help="Number of SAE features")
    parser.add_argument("--d-model", type=int, default=64, help="Feature vector dimensionality")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--top-k", type=int, default=5, help="Show top-k most/least similar pairs")
    parser.add_argument("--plot", action="store_true", help="Show cosine similarity distribution (requires matplotlib)")
    parser.add_argument("--json", action="store_true", help="Output full JSON results")
    parser.add_argument("--weights", type=str, default=None, help="[Tier 1] Path to .npz SAE weight matrix")
    args = parser.parse_args()

    if args.weights:
        print("⚠️  Real-mode (Tier 1) not yet implemented. Falling back to mock mode.")

    result = run_geometry_audit(
        n_features=args.n_features,
        d_model=args.d_model,
        seed=args.seed,
        top_k_pairs=args.top_k,
    )

    print("=" * 60)
    print("AudioSAEBench M8 — Feature Geometry Audit")
    print("=" * 60)
    print(f"Features: {result.n_features}  |  d_model: {result.d_model}")
    print()
    print(f"{'Metric':<40} {'Value':>10}")
    print("-" * 52)
    print(f"{'Cluster Score (intra/inter cosim)':<40} {result.cluster_score:>10.3f}")
    print(f"{'  Mean intra-class cosim':<40} {result.mean_intra_class_cosim:>10.3f}")
    print(f"{'  Mean inter-class cosim':<40} {result.mean_inter_class_cosim:>10.3f}")
    print(f"{'Anti-podal pairs (cosim < -0.5)':<40} {result.n_antipodal_pairs:>10d}")
    print(f"{'  Of which voicing pairs':<40} {result.n_voicing_antipodal:>10d}  "
          f"(/ {result.n_voicing_pairs_total} voicing pairs total)")
    print(f"{'Superposition Index':<40} {result.superposition_index:>10.3f}")
    print(f"{'Mean pairwise cosim':<40} {result.mean_pairwise_cosim:>10.3f}")
    print(f"{'Std pairwise cosim':<40} {result.std_pairwise_cosim:>10.3f}")

    # Interpret cluster score
    print()
    cluster_interp = (
        "✅ Strong phonological clustering (> 2.0)"
        if result.cluster_score >= 2.0
        else "🟡 Moderate clustering (1.0–2.0)"
        if result.cluster_score >= 1.0
        else "🔴 No phonological structure (< 1.0)"
    )
    print(f"Cluster Score interpretation: {cluster_interp}")

    superposition_interp = (
        "✅ Low superposition (< 20%)"
        if result.superposition_index < 0.2
        else "🟡 Moderate superposition (20–40%)"
        if result.superposition_index < 0.4
        else "🔴 High superposition (> 40%)"
    )
    print(f"Superposition interpretation: {superposition_interp}")

    print()
    print(f"Top-{args.top_k} Most Similar Feature Pairs:")
    for p in result.most_similar_pairs:
        manner_tag = "same-manner" if p.same_manner else "cross-manner"
        voice_tag = " [VOICING PAIR]" if p.is_voicing_pair else ""
        print(f"  F{p.feature_i:03d}({p.phoneme_i}) ↔ F{p.feature_j:03d}({p.phoneme_j})  "
              f"cosim={p.cosine_sim:+.3f}  {manner_tag}{voice_tag}")

    print()
    print(f"Top-{args.top_k} Most Anti-podal Feature Pairs:")
    for p in result.most_antipodal_pairs:
        manner_tag = "same-manner" if p.same_manner else "cross-manner"
        voice_tag = " [VOICING PAIR]" if p.is_voicing_pair else ""
        print(f"  F{p.feature_i:03d}({p.phoneme_i}) ↔ F{p.feature_j:03d}({p.phoneme_j})  "
              f"cosim={p.cosine_sim:+.3f}  {manner_tag}{voice_tag}")

    if args.plot:
        try:
            import matplotlib.pyplot as plt
            cosims = [p.cosine_sim for p in
                      # Recompute for plot — just show all_pairs distribution
                      result.most_similar_pairs + result.most_antipodal_pairs]
            # Note: only plotting top/bottom pairs here as all_pairs not stored
            # For a full distribution plot, run with --json and parse
            all_cosims_intra = []
            all_cosims_inter = []
            mock = MockSAEWeights(n_features=result.n_features, d_model=result.d_model)
            vectors = mock.get_all_vectors()
            dom = mock.dominant_phonemes
            for i in range(result.n_features):
                for j in range(i + 1, result.n_features):
                    csim = cosine_similarity(vectors[i], vectors[j])
                    same = PHONEME_TO_CLASS.get(dom[i]) == PHONEME_TO_CLASS.get(dom[j])
                    if same:
                        all_cosims_intra.append(csim)
                    else:
                        all_cosims_inter.append(csim)

            plt.figure(figsize=(9, 4))
            plt.hist(all_cosims_intra, bins=40, alpha=0.6, color="steelblue", label=f"Intra-class (n={len(all_cosims_intra)})")
            plt.hist(all_cosims_inter, bins=40, alpha=0.6, color="salmon", label=f"Inter-class (n={len(all_cosims_inter)})")
            plt.axvline(0.5, color="green", linestyle="--", label="Superposition threshold (0.5)")
            plt.axvline(-0.5, color="red", linestyle="--", label="Anti-podal threshold (-0.5)")
            plt.xlabel("Cosine Similarity")
            plt.ylabel("Pair Count")
            plt.title("AudioSAEBench M8 — Feature Pair Cosine Similarity Distribution")
            plt.legend()
            plt.tight_layout()
            plt.show()
        except ImportError:
            print("⚠️  matplotlib not available — skipping plot.")

    if args.json:
        output = asdict(result)
        # Convert nested PairGeometry objects
        output["most_similar_pairs"] = [asdict(p) for p in result.most_similar_pairs]
        output["most_antipodal_pairs"] = [asdict(p) for p in result.most_antipodal_pairs]
        print(json.dumps(output, indent=2))

    # Exit: 0 if cluster_score >= 1.0 (some structure present), 1 if flat
    sys.exit(0 if result.cluster_score >= 1.0 else 1)


if __name__ == "__main__":
    main()
