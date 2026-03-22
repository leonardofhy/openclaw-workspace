# Q136 Design: Multi-speaker Audio × ENV-3 Clusters

**Task:** Multi-speaker audio x ENV-3 clusters: speaker boundaries create isolated ENV-3 clusters per speaker  
**Track:** T5 (Listen-Layer Audit)  
**Date:** 2026-03-22  

---

## Problem

ENV-3 features (from graph-SAE topology) are "isolated" — low connectivity, narrow activation scope.  
Prior work (Q126) mapped ENV-3 → RVQ-N acoustic layer (fine-grained, speaker-specific).  
**Hypothesis:** In multi-speaker audio, ENV-3 clusters partition per-speaker, enabling speaker diarization via feature topology alone.

---

## Background

- **ENV taxonomy:** ENV-1 = semantic hubs (many connections), ENV-3 = isolated acoustic leaves (few connections)
- **RVQ correspondence:** ENV-1 ↔ RVQ-1 (semantic codebook), ENV-3 ↔ RVQ-N (fine acoustic)
- **Speaker identity x AND-gate (Q131):** Speaker-specific features are AND-gate (Δ AND-frac = 0.317)
- **Safety relevance:** Speaker manipulation attacks (voice cloning, persona injection) operate at the acoustic level — precisely where ENV-3 features live

---

## Mechanism Hypothesis

```
Multi-speaker audio → different acoustic fingerprints per speaker
     ↓
ENV-3 features (acoustic leaves) activate for speaker-specific patterns
     ↓
ENV-3 cluster topology partitions naturally along speaker boundaries
     ↓
Speaker turn changes = cluster membership switch in feature space
```

Concrete prediction:
- **Speaker A tokens:** ENV-3 cluster centroid at C_A
- **Speaker B tokens:** ENV-3 cluster centroid at C_B  
- **|C_A − C_B|** >> **intra-speaker variance**
- Speaker boundary detection: monitor ENV-3 cluster assignment over decoder steps → label switch = speaker turn

---

## Testable Predictions

| Prediction | Metric | Expected |
|-----------|--------|---------|
| ENV-3 features separate per speaker | Silhouette score on speaker-labeled ENV-3 activations | > 0.5 |
| Speaker boundary = cluster switch | Cluster assignment discontinuity at turn | precision > 0.8 |
| ENV-1 (semantic) do NOT separate speakers | Silhouette for ENV-1 | < 0.2 (speaker-agnostic) |
| AND-gate features dominate within each cluster | AND-frac per cluster | > 0.6 (from Q131) |

---

## CPU Mock Protocol

```python
# multispeaker_env3_mock.py
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

# Mock: 2 speakers, alternating every T tokens
N_TOKENS = 100
T_TURN = 20  # speaker changes every 20 tokens
N_ENV3 = 50  # 50 ENV-3 features
N_ENV1 = 30  # 30 ENV-1 features (semantic, speaker-agnostic)

# Speaker-specific ENV-3: different mean per speaker
speaker_labels = np.array([0 if (i // T_TURN) % 2 == 0 else 1 for i in range(N_TOKENS)])
env3_A = np.random.randn(N_ENV3) * 0.5 + np.array([1.0] * N_ENV3)  # Speaker A centroid
env3_B = np.random.randn(N_ENV3) * 0.5 + np.array([-1.0] * N_ENV3)  # Speaker B centroid
env3_activations = np.stack([
    env3_A + np.random.randn(N_ENV3) * 0.3 if s == 0 else env3_B + np.random.randn(N_ENV3) * 0.3
    for s in speaker_labels
])

# Cluster ENV-3 activations
km = KMeans(n_clusters=2, random_state=42)
pred_clusters = km.fit_predict(env3_activations)
sil_env3 = silhouette_score(env3_activations, speaker_labels)
print(f"ENV-3 silhouette (speaker separation): {sil_env3:.3f}")  # Expected: > 0.5

# ENV-1 (semantic): speaker-agnostic
env1_activations = np.random.randn(N_TOKENS, N_ENV1) * 0.5  # No speaker signal
sil_env1 = silhouette_score(env1_activations, speaker_labels)
print(f"ENV-1 silhouette (should be low): {sil_env1:.3f}")  # Expected: < 0.2

# Boundary detection: monitor cluster assignment
boundaries_pred = np.where(np.diff(pred_clusters) != 0)[0] + 1
boundaries_true = np.where(np.diff(speaker_labels) != 0)[0] + 1
precision = len(set(boundaries_pred) & set(boundaries_true)) / max(len(boundaries_pred), 1)
print(f"Boundary detection precision: {precision:.3f}")  # Expected: > 0.8
```

---

## Safety Implication: Speaker Manipulation Detection

**Threat model:** Voice cloning attack inserts forged speaker segments.
- Forged segments: ENV-3 features don't match speaker's established cluster
- Detection: outlier ENV-3 activation relative to speaker's learned centroid

**Detection protocol:**
1. Establish speaker ENV-3 centroid from first N seconds (enrollment)
2. For each new segment: compute Mahalanobis distance from enrolled centroid
3. Threshold: distance > θ → flag as potential voice manipulation
4. Advantage over raw signal: operates in latent feature space (robust to signal-level obfuscation)

**Links to existing work:**
- Q129: adversarial audio → t* leftward shift (different manifestation of same attack surface)
- Q141: persona jailbreak dual-signal detector (AND-ratio + emotion AND-frac)
- Q138: emotion AND-gate suppression as jailbreak metric
- **This adds:** speaker-level identity verification via ENV-3 topology

---

## Connection to T5 Objective (MATS Proposal)

Multi-speaker ENV-3 partitioning is a **natural diarization probe** that requires no supervised training — purely mechanistic. Key for MATS pitch:

> "We identify speaker-specific acoustic features (ENV-3, AND-gate) that partition automatically during multi-party conversations. This enables zero-shot speaker diarization and voice manipulation detection as byproducts of interpretability analysis."

---

## Connections

- **Q126** (ENV taxonomy x Codec RVQ): ENV-3 = RVQ-N acoustic → our features are well-typed
- **Q131** (Speaker-ID x AND-gate): speaker features are AND-gate → ENV-3 AND features = speaker fingerprints
- **Q138/Q141** (jailbreak detectors): add speaker spoofing to detection suite
- **Paper C / T5**: ENV-3 clusters = interpretable diarization + security probe

---

## Open Questions

1. Does ENV-3 partitioning degrade for >3 speakers? (possible cluster confusion)
2. Is the cluster boundary aligned with Whisper's acoustic encoder outputs or decoder cross-attention?
3. Can ENV-3 centroids be used for zero-shot speaker verification (cosine similarity threshold)?
4. Overlap speech (diarization hard case): do ENV-3 clusters show mixed activations or snap to dominant speaker?

---

## Definition of Done: ✅

- Design doc written (this file)
- Mock protocol specified (`multispeaker_env3_mock.py`)
- Safety implication articulated (voice manipulation detection via ENV-3 outlier scoring)
- Connection to MATS proposal made explicit
