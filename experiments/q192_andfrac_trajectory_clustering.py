"""
AND-frac Trajectory Clustering: Commitment Archetypes
Task: Q192 | Track: T3 | Priority: 2

Hypothesis: AND-frac(L) curves across layers are not random — they cluster
into distinct "commitment archetypes" that reveal qualitatively different
processing strategies in Whisper.

Motivation:
  Prior experiments showed AND-frac rises sharply at L* (layer 4 for
  Whisper-base). But the *shape* of the curve varies. Some samples show:
    - Early commitment: AND-frac high from L=1 onward
    - Late commitment: AND-frac rises only at L*
    - Ambiguous: AND-frac never fully saturates
    - Collapsed: AND-frac stays low (hallucination/jailbreak risk)

  Clustering these curves reveals archetypes useful for:
    - Explaining model behavior to reviewers
    - Targeted intervention (early vs. late committers need different steering)
    - Anomaly detection (collapsed = immediate alert)

Method:
  1. Generate 500 mock AND-frac(L) curves (6 layers for Whisper-base)
  2. Use k-means clustering (k=4) on flattened/normalized curves
  3. Validate with silhouette score (target: >0.4)
  4. Label archetypes by curve shape
  5. Correlate archetype with sample category (clean/accented/hallucinated/jailbreak)

Definition of Done:
  - 500 Whisper-base mock samples (6 layers each)
  - k-means k=3 or 4; silhouette >0.4
  - Archetypes labeled + correlation table
  - CPU <5min
"""

import numpy as np
import time
from typing import Dict, List, Tuple

RNG = np.random.default_rng(42)

# ── CONFIG ────────────────────────────────────────────────────────────────────
N_SAMPLES = 500
N_LAYERS = 6         # Whisper-base encoder layers
LISTEN_LAYER = 4     # L* (0-indexed: layer index 3 = 4th layer)
K_CLUSTERS = 4       # number of archetypes
N_HEADS = 6

# ── SIGMOID HELPER ────────────────────────────────────────────────────────────
def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))

# ── GENERATE AND-FRAC CURVES ──────────────────────────────────────────────────
def generate_andfrac_curves(n: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate mock AND-frac(L) curves.
    Each curve = AND-frac at layers 0..N_LAYERS-1.

    Four underlying archetypes (ground truth for validation):
      0: Early committer  — rises by L=2, stays high
      1: Late committer   — rises sharply at L* (L=3)
      2: Ambiguous        — gradual rise, never fully saturates
      3: Collapsed        — stays low throughout

    Mix: 35% early, 35% late, 20% ambiguous, 10% collapsed
    (reflecting realistic distribution from prior experiments)
    """
    probs = [0.35, 0.35, 0.20, 0.10]
    true_labels = RNG.choice(K_CLUSTERS, size=n, p=probs)

    curves = np.zeros((n, N_LAYERS))
    layers = np.arange(N_LAYERS)

    for i, lbl in enumerate(true_labels):
        if lbl == 0:  # Early committer
            # AND-frac rises steeply early, plateau ~0.85
            base = sigmoid((layers - 1.0) * 2.5) * 0.85
            noise = RNG.normal(0, 0.04, N_LAYERS)
            curve = np.clip(base + noise, 0.0, 1.0)

        elif lbl == 1:  # Late committer (canonical — mirrors prior experiments)
            # Relatively flat until L*, then sharp rise
            base = np.where(layers < LISTEN_LAYER - 1,
                            0.2 + layers * 0.04,
                            sigmoid((layers - (LISTEN_LAYER - 0.5)) * 3.0) * 0.82 + 0.05)
            noise = RNG.normal(0, 0.05, N_LAYERS)
            curve = np.clip(base + noise, 0.0, 1.0)

        elif lbl == 2:  # Ambiguous / gradual
            # Slow linear rise, never exceeds ~0.60
            base = 0.15 + layers * 0.07 + RNG.normal(0, 0.02)
            noise = RNG.normal(0, 0.06, N_LAYERS)
            curve = np.clip(base + noise, 0.0, 1.0)

        else:  # lbl == 3: Collapsed
            # Low throughout — jailbreak/hallucination risk
            base = 0.10 + RNG.normal(0, 0.02) + layers * 0.01
            noise = RNG.normal(0, 0.04, N_LAYERS)
            curve = np.clip(base + noise, 0.0, 0.40)

        curves[i] = curve

    return curves, true_labels


# ── K-MEANS (pure numpy, no sklearn) ─────────────────────────────────────────
def kmeans(X: np.ndarray, k: int, n_init: int = 10, max_iter: int = 300
           ) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Simple k-means. Returns (labels, centroids, inertia).
    Multiple restarts via n_init; keeps best inertia.
    """
    best_labels = None
    best_centroids = None
    best_inertia = float("inf")

    for _ in range(n_init):
        # Random init
        idx = RNG.choice(len(X), size=k, replace=False)
        centroids = X[idx].copy()

        for _ in range(max_iter):
            # Assignment
            dists = np.linalg.norm(X[:, None, :] - centroids[None, :, :], axis=2)  # (N, k)
            labels = np.argmin(dists, axis=1)

            # Update
            new_centroids = np.array([
                X[labels == j].mean(axis=0) if (labels == j).any() else centroids[j]
                for j in range(k)
            ])

            if np.allclose(new_centroids, centroids, atol=1e-6):
                break
            centroids = new_centroids

        inertia = sum(
            np.sum((X[labels == j] - centroids[j]) ** 2)
            for j in range(k)
            if (labels == j).any()
        )
        if inertia < best_inertia:
            best_inertia = inertia
            best_labels = labels.copy()
            best_centroids = centroids.copy()

    return best_labels, best_centroids, best_inertia


def silhouette_score(X: np.ndarray, labels: np.ndarray) -> float:
    """Compute mean silhouette coefficient."""
    n = len(X)
    k = len(np.unique(labels))
    if k <= 1:
        return 0.0

    s_scores = []
    for i in range(n):
        own = labels[i]
        own_mask = labels == own
        own_mask[i] = False
        if own_mask.sum() == 0:
            s_scores.append(0.0)
            continue

        a = np.mean(np.linalg.norm(X[i] - X[own_mask], axis=1))

        b_vals = []
        for j in range(k):
            if j == own:
                continue
            other_mask = labels == j
            if other_mask.sum() == 0:
                continue
            b_vals.append(np.mean(np.linalg.norm(X[i] - X[other_mask], axis=1)))

        b = min(b_vals) if b_vals else 0.0
        s = (b - a) / max(a, b) if max(a, b) > 0 else 0.0
        s_scores.append(s)

    return float(np.mean(s_scores))


# ── ARCHETYPE LABELS ──────────────────────────────────────────────────────────
def label_archetype(centroid: np.ndarray) -> str:
    """Heuristic labeling based on centroid shape."""
    mean_val = centroid.mean()
    final_val = centroid[-1]
    early_val = centroid[1]  # L=1 (0-indexed)
    slope = centroid[-1] - centroid[0]

    if mean_val < 0.25:
        return "Collapsed (jailbreak/halluc risk)"
    if early_val > 0.60:
        return "Early Committer (audio-dominant)"
    if slope > 0.35 and early_val < 0.40:
        return "Late Committer (canonical L* transition)"
    return "Ambiguous (gradual commitment)"


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    t0 = time.time()
    print("=" * 60)
    print("Q192: AND-frac Trajectory Clustering")
    print(f"N={N_SAMPLES} samples | Whisper-base {N_LAYERS} layers | k={K_CLUSTERS}")
    print("=" * 60)

    # 1. Generate curves
    curves, true_labels = generate_andfrac_curves(N_SAMPLES)
    print(f"\n[1] Generated {N_SAMPLES} AND-frac(L) curves")
    print(f"    True distribution: "
          + ", ".join(f"A{i}={np.sum(true_labels==i)}" for i in range(K_CLUSTERS)))

    # 2. Normalize curves to [0,1] range per-sample (shape-based clustering)
    c_min = curves.min(axis=1, keepdims=True)
    c_max = curves.max(axis=1, keepdims=True)
    c_range = np.where((c_max - c_min) > 1e-8, c_max - c_min, 1.0)
    X_norm = (curves - c_min) / c_range

    # 3. K-means
    labels, centroids, inertia = kmeans(X_norm, k=K_CLUSTERS, n_init=15, max_iter=300)
    print(f"\n[2] K-means (k={K_CLUSTERS}, 15 restarts) complete")
    print(f"    Inertia: {inertia:.3f}")
    print(f"    Cluster sizes: " + ", ".join(
        f"C{i}={np.sum(labels==i)}" for i in range(K_CLUSTERS)))

    # 4. Silhouette
    sil = silhouette_score(X_norm, labels)
    print(f"\n[3] Silhouette score: {sil:.4f}", "✅ PASS" if sil > 0.40 else "⚠️ BELOW 0.40")

    # 5. Label archetypes
    print("\n[4] Archetype Centroids (raw AND-frac):")
    archetype_names = []
    raw_centroids = []
    for i in range(K_CLUSTERS):
        # Recover centroid in raw space (approximate, using cluster mean of raw curves)
        raw_c = curves[labels == i].mean(axis=0)
        raw_centroids.append(raw_c)
        name = label_archetype(raw_c)
        archetype_names.append(name)
        curve_str = " ".join(f"L{j}={raw_c[j]:.3f}" for j in range(N_LAYERS))
        print(f"    C{i} [{name}]: {curve_str}")

    # 6. Correlation: cluster assignment vs true labels
    print("\n[5] Cluster × True-Label Cross-tab (alignment validation):")
    print("    (rows=true label, cols=predicted cluster)")
    header = "         " + "  ".join(f"C{j:2d}" for j in range(K_CLUSTERS))
    print("   " + header)
    for ti in range(K_CLUSTERS):
        row = [np.sum((true_labels == ti) & (labels == j)) for j in range(K_CLUSTERS)]
        label_names = ["Early", "Late", "Ambig", "Collap"]
        print(f"   T{ti}({label_names[ti]:5s}):  " + "  ".join(f"{v:4d}" for v in row))

    # 7. Commitment profile per archetype
    print("\n[6] Commitment Profiles:")
    print("    (AND-frac at L*, mean ± std per cluster)")
    for i in range(K_CLUSTERS):
        lstar_vals = curves[labels == i, LISTEN_LAYER - 1]  # L* = layer index 3
        print(f"    C{i} [{archetype_names[i][:30]}]: "
              f"AND-frac@L*={lstar_vals.mean():.3f} ± {lstar_vals.std():.3f}")

    # 8. Research implications
    print("\n[7] Research Implications:")
    collapsed_idx = [i for i, n in enumerate(archetype_names) if "Collapsed" in n]
    canonical_idx = [i for i, n in enumerate(archetype_names) if "Late" in n or "canonical" in n.lower()]

    if collapsed_idx:
        ci = collapsed_idx[0]
        frac = np.sum(labels == ci) / N_SAMPLES
        print(f"    • Collapsed archetype (C{ci}): {frac*100:.1f}% of samples → jailbreak/halluc risk tier")

    if canonical_idx:
        ci = canonical_idx[0]
        frac = np.sum(labels == ci) / N_SAMPLES
        print(f"    • Canonical late-commit (C{ci}): {frac*100:.1f}% → matches AND-frac theory")

    print("    • Archetypes suggest targeted interventions per cluster")
    print("      (early: no steering needed; late: standard L* power steering;")
    print("       ambig: softer steering; collapsed: alert + refuse)")
    print("    • Cluster membership = lightweight real-time triage signal")

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"Done in {elapsed:.2f}s | PASS: silhouette={sil:.4f}>0.40: {sil>0.40}")
    print(f"{'='*60}")

    return {
        "silhouette": sil,
        "k": K_CLUSTERS,
        "n_samples": N_SAMPLES,
        "cluster_sizes": [int(np.sum(labels == i)) for i in range(K_CLUSTERS)],
        "archetype_names": archetype_names,
        "elapsed_sec": elapsed,
        "pass": sil > 0.40
    }


if __name__ == "__main__":
    result = main()
