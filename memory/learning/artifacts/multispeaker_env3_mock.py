"""
Q136: Multi-speaker audio x ENV-3 clusters
Hypothesis: ENV-3 (acoustic leaf features) partition per-speaker in multi-speaker audio.
Speaker boundaries = ENV-3 cluster membership switches.
Safety implication: voice manipulation detection via ENV-3 outlier scoring.
"""
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

np.random.seed(42)

N_TOKENS = 100
T_TURN = 20        # speaker changes every 20 tokens
N_ENV3 = 50        # ENV-3 (acoustic) features
N_ENV1 = 30        # ENV-1 (semantic, hub) features
SPEAKER_SEPARATION = 2.0  # distance between speaker centroids in ENV-3 space

# Ground truth speaker labels
speaker_labels = np.array([0 if (i // T_TURN) % 2 == 0 else 1 for i in range(N_TOKENS)])
boundaries_true = np.where(np.diff(speaker_labels) != 0)[0] + 1

# --- ENV-3: speaker-specific (AND-gate, acoustic fingerprint per Q131) ---
centroid_A = np.ones(N_ENV3) * (SPEAKER_SEPARATION / 2)
centroid_B = np.ones(N_ENV3) * (-SPEAKER_SEPARATION / 2)
env3_activations = np.stack([
    centroid_A + np.random.randn(N_ENV3) * 0.3 if s == 0
    else centroid_B + np.random.randn(N_ENV3) * 0.3
    for s in speaker_labels
])

# --- ENV-1: semantic, speaker-agnostic ---
env1_activations = np.random.randn(N_TOKENS, N_ENV1) * 0.5

# --- Clustering ---
km3 = KMeans(n_clusters=2, random_state=42, n_init=10)
pred_clusters = km3.fit_predict(env3_activations)
sil_env3 = silhouette_score(env3_activations, speaker_labels)
sil_env1 = silhouette_score(env1_activations, speaker_labels)

# --- Boundary detection ---
boundaries_pred = np.where(np.diff(pred_clusters) != 0)[0] + 1
true_set = set(boundaries_true)
pred_set = set(boundaries_pred)
precision = len(pred_set & true_set) / max(len(pred_set), 1)
recall = len(pred_set & true_set) / max(len(true_set), 1)

# --- Voice manipulation detection mock ---
# Enrollment: first 20 tokens of speaker A
enrolled_centroid = env3_activations[:T_TURN].mean(axis=0)
# Forged segment: inject speaker with different centroid (attack)
forged_segment = centroid_B + np.random.randn(T_TURN, N_ENV3) * 0.3
genuine_segment = centroid_A + np.random.randn(T_TURN, N_ENV3) * 0.3

dist_forged = np.linalg.norm(forged_segment - enrolled_centroid, axis=1).mean()
dist_genuine = np.linalg.norm(genuine_segment - enrolled_centroid, axis=1).mean()
separation_ratio = dist_forged / dist_genuine

print("=" * 55)
print("Q136: Multi-speaker ENV-3 Cluster Separation")
print("=" * 55)
print(f"\n[Prediction 1] ENV-3 silhouette (speaker sep): {sil_env3:.3f}  (expected > 0.5)")
print(f"[Prediction 2] ENV-1 silhouette (should be ~0): {sil_env1:.3f}  (expected < 0.2)")
print(f"[Prediction 3] Boundary precision: {precision:.3f}  (expected > 0.8)")
print(f"               Boundary recall:    {recall:.3f}")
print(f"\n[Safety] Voice manipulation detection:")
print(f"  Enrolled centroid (speaker A) dist to forged: {dist_forged:.3f}")
print(f"  Enrolled centroid (speaker A) dist to genuine: {dist_genuine:.3f}")
print(f"  Separation ratio (forged/genuine): {separation_ratio:.2f}x  (expected > 3.0)")

# Assertions
assert sil_env3 > 0.5, f"ENV-3 silhouette too low: {sil_env3}"
assert sil_env1 < 0.2, f"ENV-1 silhouette too high: {sil_env1}"
assert precision > 0.8, f"Boundary precision too low: {precision}"
assert separation_ratio > 3.0, f"Manipulation detection separation too low: {separation_ratio}"
print("\n✅ All assertions passed")
