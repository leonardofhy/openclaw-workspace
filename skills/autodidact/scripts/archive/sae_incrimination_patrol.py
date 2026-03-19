#!/usr/bin/env python3
"""
SAE Incrimination Patrol (Q078 — T5)
Track T5, Q078

RESEARCH QUESTION
-----------------
When the SAE adversarial detector fires, WHICH specific SAE features
triggered the alert? Can we produce a per-feature "blame report" that
traces a jailbreak detection back to individual audio feature activations?

CONNECTION TO GC(k) INCRIMINATION FRAMEWORK
--------------------------------------------
gc_incrimination_mock.py identifies *which decoder step* to blame for a
transcription error. This script does the analogous thing at the SAE feature
level for safety/adversarial detection:

  gc_incrimination:  token-level blame  →  which step made the wrong decision
  sae_incrimination: feature-level blame →  which SAE features triggered the alert

Together they form a two-level attribution stack:
  Macro: gc(k) step blame (did audio or text-prior dominate?)
  Micro: SAE feature blame (which specific features carried the signal?)

WHAT WE BUILD
-------------
Extend sae_adversarial_detector.py with:

1. FeatureIncriminator
   - For each triggered alert: compute per-feature contribution to the alert score
   - Contribution = how much feature f_i deviated from benign baseline
   - Methods: raw_activation, z-score deviation, directional contribution to gc_proj

2. IncriminationLog
   - For each flagged sample: dict {feature_idx: score, ...}
   - Top-K features ranked by blame score
   - Feature "motive type" tag: audio-suppression-feature vs prior-injection-feature

3. PatrolReport
   - Summary across a batch of samples
   - Feature hit-rate: which features fire most often across alerts
   - "Persistent offenders": features that appear in >50% of alerts

TIER
----
Tier 0: pure scaffold, mock data, numpy only. No model downloads.
Tier 1: run with N=2000 (CPU <5 min). Auto-allowed.

USAGE
-----
  python3 sae_incrimination_patrol.py              # full patrol demo
  python3 sae_incrimination_patrol.py --test       # unit tests
  python3 sae_incrimination_patrol.py --n 2000     # larger run
  python3 sae_incrimination_patrol.py --top-k 5    # top-5 features per alert
  python3 sae_incrimination_patrol.py --json       # JSON output

Author: Little Leo (Lab) — 2026-03-14
Track: T5, Q078, explore-fallback
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Reuse MicroGPT + SAE from sae_adversarial_detector (inline for portability)
# ---------------------------------------------------------------------------

class MicroGPT:
    def __init__(self, n_layers: int = 6, d_model: int = 8, seed: int = 42):
        self.n_layers = n_layers; self.d_model = d_model
        rng = np.random.RandomState(seed)
        self.W = [rng.randn(d_model, d_model) * 0.15 for _ in range(n_layers)]
        self.b = [rng.randn(d_model) * 0.05 for _ in range(n_layers)]
        self.W_out = rng.randn(d_model) * 0.3

    def listen_layer_activation(self, h0: np.ndarray) -> np.ndarray:
        h = h0.copy()
        h = h + np.tanh(self.W[0] @ h + self.b[0])
        return h


class SAE:
    """Minimal numpy SAE with Adam optimizer."""

    def __init__(self, d_model: int = 8, d_sae: int = 32, seed: int = 0):
        self.d_model = d_model; self.d_sae = d_sae
        rng = np.random.RandomState(seed)
        W_dec = rng.randn(d_model, d_sae)
        W_dec /= np.linalg.norm(W_dec, axis=0, keepdims=True) + 1e-8
        self.W_dec = W_dec; self.W_enc = W_dec.T.copy()
        self.b_enc = np.zeros(d_sae); self.b_dec = np.zeros(d_model)
        self._m = {k: np.zeros_like(v) for k, v in self._params().items()}
        self._v = {k: np.zeros_like(v) for k, v in self._params().items()}
        self._t = 0

    def _params(self):
        return {"W_enc": self.W_enc, "W_dec": self.W_dec,
                "b_enc": self.b_enc, "b_dec": self.b_dec}

    def encode(self, h: np.ndarray) -> np.ndarray:
        pre = (h - self.b_dec) @ self.W_enc.T + self.b_enc
        return np.maximum(0.0, pre)

    def decode(self, f: np.ndarray) -> np.ndarray:
        return f @ self.W_dec.T + self.b_dec

    def _normalize_decoder(self):
        norms = np.linalg.norm(self.W_dec, axis=0, keepdims=True)
        self.W_dec /= np.maximum(norms, 1.0)

    def train(self, data: np.ndarray, epochs: int = 100, lr: float = 0.003,
              l1_lambda: float = 0.01, batch_size: int = 64):
        rng = np.random.RandomState(42)
        N = data.shape[0]; b1, b2, eps = 0.9, 0.999, 1e-8
        for epoch in range(epochs):
            idx = rng.permutation(N)
            for start in range(0, N, batch_size):
                b = data[idx[start:start + batch_size]]
                f = self.encode(b); h_hat = self.decode(f)
                rec = h_hat - b; N_b = len(b)
                dh = 2 * rec / N_b
                df = (dh @ self.W_dec + l1_lambda * np.sign(f) / N_b) * (f > 0)
                grads = {
                    "W_dec": dh.T @ f, "b_dec": dh.mean(0),
                    "W_enc": df.T @ (b - self.b_dec), "b_enc": df.mean(0),
                }
                self._t += 1
                for name, g in grads.items():
                    g = np.clip(g, -1.0, 1.0)
                    self._m[name] = b1 * self._m[name] + (1 - b1) * g
                    self._v[name] = b2 * self._v[name] + (1 - b2) * g**2
                    m_h = self._m[name] / (1 - b1**self._t)
                    v_h = self._v[name] / (1 - b2**self._t)
                    param = getattr(self, name)
                    param -= lr * m_h / (np.sqrt(v_h) + eps)
                self._normalize_decoder()


# ---------------------------------------------------------------------------
# Synthetic dataset
# ---------------------------------------------------------------------------

@dataclass
class Dataset:
    benign_acts: np.ndarray   # (N_benign, d_model)
    attack_acts: np.ndarray   # (N_attack, d_model)
    attack_types: np.ndarray  # (N_attack,) str


def make_dataset(model: MicroGPT, n_benign: int = 600, n_attack: int = 200,
                 seed: int = 77) -> Dataset:
    rng = np.random.RandomState(seed); d = model.d_model
    benign, attacks, types = [], [], []
    for _ in range(n_benign):
        h = rng.randn(d) * 0.4; h[0] = rng.uniform(-0.5, 3.0)
        benign.append(model.listen_layer_activation(h))
    n_sup = n_attack // 2
    for _ in range(n_sup):
        h = rng.randn(d) * 0.4; h[0] = rng.uniform(-3.0, -1.0)
        attacks.append(model.listen_layer_activation(h))
        types.append("suppression")
    for _ in range(n_attack - n_sup):
        h = rng.randn(d) * 0.4; h[0] = -rng.uniform(0.5, 2.5)
        h[1:] += rng.randn(d - 1) * 0.3
        attacks.append(model.listen_layer_activation(h))
        types.append("override")
    return Dataset(np.array(benign), np.array(attacks), np.array(types))


# ---------------------------------------------------------------------------
# Baseline fitting (benign statistics per feature)
# ---------------------------------------------------------------------------

@dataclass
class Baseline:
    """Per-feature benign statistics: mean + std for z-score deviation."""
    feature_mean: np.ndarray   # (d_sae,)
    feature_std: np.ndarray    # (d_sae,)
    gc_direction: np.ndarray   # (d_model,) — most gc-correlated decoder column
    gc_feature_idx: int        # which SAE feature is most gc-correlated
    gc_benign_proj_mean: float # benign mean projection onto gc_direction
    gc_benign_proj_std: float  # benign std of that projection


def fit_baseline(sae: SAE, benign_train: np.ndarray) -> Baseline:
    """Compute per-feature statistics on benign training data."""
    feats = sae.encode(benign_train)         # (N, d_sae)
    feat_mean = feats.mean(0)                # (d_sae,)
    feat_std  = feats.std(0) + 1e-8         # (d_sae,)

    # Find SAE feature most correlated with audio signal (dim 0 = gc proxy)
    audio_signal = benign_train[:, 0]
    best_feat = 0; best_r = 0.0
    for i in range(sae.d_sae):
        f_i = feats[:, i]
        if f_i.std() < 1e-9: continue
        r = float(np.corrcoef(f_i, audio_signal)[0, 1])
        if abs(r) > abs(best_r): best_r = r; best_feat = i

    v_gc = sae.W_dec[:, best_feat]
    gc_proj = benign_train @ v_gc
    return Baseline(
        feature_mean=feat_mean, feature_std=feat_std,
        gc_direction=v_gc, gc_feature_idx=best_feat,
        gc_benign_proj_mean=float(gc_proj.mean()),
        gc_benign_proj_std=float(gc_proj.std()) + 1e-8,
    )


# ---------------------------------------------------------------------------
# FeatureIncriminator — per-sample per-feature blame scores
# ---------------------------------------------------------------------------

@dataclass
class IncriminatedSample:
    sample_idx: int
    attack_type: str                          # "suppression" | "override" | "benign"
    alert_score: float                        # aggregate detection score (gc_proj deviation)
    alerted: bool                             # True if score >= threshold
    blame: Dict[int, float]                   # {feature_idx: z_score_deviation}
    top_features: List[Tuple[int, float]]     # [(feature_idx, blame_score), ...] top-K
    motive_tags: Dict[int, str]               # {feature_idx: "audio_suppression" | "prior_injection" | "other"}
    gc_z_score: float                         # alert's deviation on gc-correlated feature


def incriminate_sample(
    activation: np.ndarray,  # (d_model,)
    sae: SAE,
    baseline: Baseline,
    threshold: float,
    sample_idx: int,
    attack_type: str,
    top_k: int = 5,
) -> IncriminatedSample:
    """
    For a single sample, compute:
    - aggregate alert score (gc_proj deviation)
    - per-feature blame (z-score deviation from benign mean)
    - top-K blamed features
    - motive tag: audio_suppression (feature underactivated relative to benign)
                  prior_injection (feature overactivated relative to benign)
    """
    features = sae.encode(activation.reshape(1, -1)).squeeze(0)  # (d_sae,)

    # Aggregate detection score: deviation of gc-direction projection from benign mean
    gc_proj = float(activation @ baseline.gc_direction)
    gc_deviation = abs(gc_proj - baseline.gc_benign_proj_mean)
    gc_z = gc_deviation / baseline.gc_benign_proj_std

    # Per-feature z-score deviation from benign baseline
    z_scores = (features - baseline.feature_mean) / baseline.feature_std  # (d_sae,)

    # Blame = absolute z-score (large deviation in either direction = suspicious)
    blame_scores = np.abs(z_scores)
    blame_dict = {i: float(blame_scores[i]) for i in range(len(blame_scores))}

    # Top-K features by blame score
    top_k_indices = np.argsort(blame_scores)[::-1][:top_k]
    top_features = [(int(i), float(blame_scores[i])) for i in top_k_indices]

    # Motive tags based on direction of z-score
    # Underactivation (z < -1.5): feature that normally fires on audio is silent → suppression
    # Overactivation  (z > +1.5): feature firing anomalously → prior injection
    motive_tags: Dict[int, str] = {}
    for i, _ in top_features:
        if z_scores[i] < -1.5:
            motive_tags[i] = "audio_suppression"  # audio-evidence feature silenced
        elif z_scores[i] > 1.5:
            motive_tags[i] = "prior_injection"     # non-audio feature anomalously active
        else:
            motive_tags[i] = "other"

    return IncriminatedSample(
        sample_idx=sample_idx,
        attack_type=attack_type,
        alert_score=gc_deviation,
        alerted=gc_deviation >= threshold,
        blame=blame_dict,
        top_features=top_features,
        motive_tags=motive_tags,
        gc_z_score=float(gc_z),
    )


# ---------------------------------------------------------------------------
# PatrolReport — aggregate across a batch
# ---------------------------------------------------------------------------

@dataclass
class PatrolReport:
    n_samples: int
    n_alerted: int
    alert_rate: float
    threshold: float
    top_k: int
    samples: List[IncriminatedSample]
    # Feature-level aggregates across all alerted samples
    feature_hit_rate: Dict[int, float]      # fraction of alerts where feature appears in top-K
    persistent_offenders: List[int]         # features in >50% of alerts
    motive_distribution: Dict[str, int]     # {"audio_suppression": N, "prior_injection": N, ...}
    attack_type_stats: Dict[str, Dict]      # per attack-type: alert_rate, mean_gc_z, top_feature


def build_patrol_report(
    samples: List[IncriminatedSample],
    threshold: float,
    top_k: int,
    d_sae: int,
) -> PatrolReport:
    n = len(samples)
    alerted = [s for s in samples if s.alerted]
    n_alerted = len(alerted)

    # Feature hit-rate across alerts
    feature_hits = np.zeros(d_sae)
    for s in alerted:
        for feat_idx, _ in s.top_features:
            feature_hits[feat_idx] += 1
    if n_alerted > 0:
        feature_hit_rate = {i: feature_hits[i] / n_alerted for i in range(d_sae)}
    else:
        feature_hit_rate = {i: 0.0 for i in range(d_sae)}

    # Persistent offenders (>50% of alerts)
    persistent = [i for i, rate in feature_hit_rate.items() if rate > 0.5]

    # Motive distribution across all top features in alerts
    motive_counts: Dict[str, int] = {}
    for s in alerted:
        for feat_idx, _ in s.top_features:
            tag = s.motive_tags.get(feat_idx, "other")
            motive_counts[tag] = motive_counts.get(tag, 0) + 1

    # Per attack-type stats
    attack_types = list(set(s.attack_type for s in samples))
    attack_type_stats = {}
    for atype in attack_types:
        atype_samples = [s for s in samples if s.attack_type == atype]
        atype_alerted = [s for s in atype_samples if s.alerted]
        alert_r = len(atype_alerted) / max(len(atype_samples), 1)
        mean_gz = np.mean([s.gc_z_score for s in atype_samples]) if atype_samples else 0.0
        # Most common top feature
        feat_counts: Dict[int, int] = {}
        for s in atype_alerted:
            for fi, _ in s.top_features[:1]:  # just top-1
                feat_counts[fi] = feat_counts.get(fi, 0) + 1
        top_feat = max(feat_counts, key=feat_counts.get) if feat_counts else -1
        attack_type_stats[atype] = {
            "n": len(atype_samples),
            "n_alerted": len(atype_alerted),
            "alert_rate": round(float(alert_r), 3),
            "mean_gc_z": round(float(mean_gz), 3),
            "most_common_top_feature": int(top_feat),
        }

    return PatrolReport(
        n_samples=n, n_alerted=n_alerted,
        alert_rate=n_alerted / max(n, 1),
        threshold=threshold, top_k=top_k,
        samples=samples,
        feature_hit_rate=feature_hit_rate,
        persistent_offenders=persistent,
        motive_distribution=motive_counts,
        attack_type_stats=attack_type_stats,
    )


# ---------------------------------------------------------------------------
# Full patrol pipeline
# ---------------------------------------------------------------------------

def run_patrol(
    n_benign: int = 600,
    n_attack: int = 200,
    d_sae: int = 32,
    top_k: int = 5,
    target_precision: float = 0.9,
    seed: int = 42,
) -> PatrolReport:
    rng = np.random.RandomState(seed)
    model = MicroGPT(n_layers=6, d_model=8, seed=seed)

    # Generate data
    ds = make_dataset(model, n_benign=n_benign, n_attack=n_attack, seed=seed + 1)

    # Train/val split on benign
    n_train = int(0.8 * n_benign)
    idx = rng.permutation(n_benign)
    benign_train = ds.benign_acts[idx[:n_train]]
    benign_val   = ds.benign_acts[idx[n_train:]]

    # Train SAE on benign train
    sae = SAE(d_model=model.d_model, d_sae=d_sae, seed=seed + 2)
    sae.train(benign_train)

    # Fit baseline statistics
    baseline = fit_baseline(sae, benign_train)

    # Determine threshold from benign_val (set to catch top_precision attacks)
    # Use gc_proj score to find threshold at benign FPR ~5%
    benign_val_projs = np.abs(benign_val @ baseline.gc_direction - baseline.gc_benign_proj_mean)
    threshold = float(np.percentile(benign_val_projs, 95))  # FPR = 5%

    # Run incrimination on all attack samples (and a benign subsample for sanity)
    incriminated: List[IncriminatedSample] = []

    # Benign val (sample 30)
    sample_benign = benign_val[:30]
    for i, act in enumerate(sample_benign):
        inc = incriminate_sample(act, sae, baseline, threshold,
                                 sample_idx=i, attack_type="benign", top_k=top_k)
        incriminated.append(inc)

    # All attacks
    for i, (act, atype) in enumerate(zip(ds.attack_acts, ds.attack_types)):
        inc = incriminate_sample(act, sae, baseline, threshold,
                                 sample_idx=i + 30, attack_type=atype, top_k=top_k)
        incriminated.append(inc)

    return build_patrol_report(incriminated, threshold, top_k, d_sae)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_patrol_report(report: PatrolReport):
    print("=" * 72)
    print("SAE Incrimination Patrol Report (Q078 — T5)")
    print("=" * 72)
    print(f"  Samples: {report.n_samples} | Alerted: {report.n_alerted} "
          f"({report.alert_rate:.1%}) | Threshold: {report.threshold:.4f}")
    print(f"  Top-K per sample: {report.top_k}")
    print()

    # Attack-type stats
    print("  Alert rate by attack type:")
    for atype, stats in report.attack_type_stats.items():
        print(f"    {atype:<15}: n={stats['n']:>3}  alerted={stats['n_alerted']:>3}  "
              f"rate={stats['alert_rate']:.3f}  mean_gc_z={stats['mean_gc_z']:.2f}  "
              f"top_feat=f{stats['most_common_top_feature']}")
    print()

    # Motive distribution
    print("  Motive distribution (across top features in alerts):")
    for motive, count in sorted(report.motive_distribution.items(), key=lambda x: -x[1]):
        print(f"    {motive:<25}: {count}")
    print()

    # Persistent offenders
    print(f"  Persistent offenders (>50% of alerts): "
          f"{['f'+str(i) for i in sorted(report.persistent_offenders)] or 'none'}")
    print()

    # Top-5 features by hit rate (across all alerts)
    top_features = sorted(report.feature_hit_rate.items(), key=lambda x: -x[1])[:5]
    print("  Top-5 features by hit rate across alerts:")
    for fi, rate in top_features:
        print(f"    f{fi:<4}  hit_rate={rate:.3f}")
    print()

    # Example alert: first alerted attack sample
    alerts = [s for s in report.samples if s.alerted and s.attack_type != "benign"]
    if alerts:
        ex = alerts[0]
        print(f"  Example alert (sample #{ex.sample_idx}, type={ex.attack_type}):")
        print(f"    Alert score: {ex.alert_score:.4f}  gc_z: {ex.gc_z_score:.2f}σ")
        print(f"    Blame report (top-{report.top_k} features):")
        for fi, score in ex.top_features:
            tag = ex.motive_tags.get(fi, "other")
            print(f"      f{fi:<4}  z={score:.3f}  motive={tag}")
    print()

    # Interpretation
    sup_stats = report.attack_type_stats.get("suppression", {})
    ovr_stats = report.attack_type_stats.get("override", {})
    sup_r = sup_stats.get("alert_rate", 0)
    ovr_r = ovr_stats.get("alert_rate", 0)
    n_offenders = len(report.persistent_offenders)
    sup_motive = report.motive_distribution.get("audio_suppression", 0)
    inj_motive = report.motive_distribution.get("prior_injection", 0)

    print("  Interpretation:")
    if sup_r > 0.7:
        print(f"  ✓ Suppression attacks detected at {sup_r:.1%} — audio-suppression "
              f"features dominate blame ({sup_motive} hits vs prior_injection {inj_motive})")
    if ovr_r > 0.7:
        print(f"  ✓ Override attacks detected at {ovr_r:.1%}")
    if n_offenders > 0:
        print(f"  ✓ {n_offenders} persistent offender feature(s) found — candidates for "
              f"interpretability study: {['f'+str(i) for i in sorted(report.persistent_offenders)]}")
    if n_offenders == 0:
        print("  ~ No persistent offenders — alert distributes across many features (diffuse signal)")

    print()
    print("  Connection to gc(k) framework:")
    print("  - gc_incrimination_env3.py: macro blame (which decoder step failed)")
    print("  - sae_incrimination_patrol.py: micro blame (which SAE features fired)")
    print("  - Together: two-level attribution stack for audio-LLM safety audits")
    print()
    print("  Next (T2, Leo approval): run on real Whisper activations with genuine")
    print("  adversarial audio to validate feature assignments with real speech data.")
    print("=" * 72)


def to_json_report(report: PatrolReport) -> dict:
    top_features_by_rate = sorted(report.feature_hit_rate.items(), key=lambda x: -x[1])[:10]
    example_alerts = []
    for s in [s for s in report.samples if s.alerted and s.attack_type != "benign"][:3]:
        example_alerts.append({
            "sample_idx": s.sample_idx,
            "attack_type": s.attack_type,
            "alert_score": round(s.alert_score, 5),
            "gc_z_score": round(s.gc_z_score, 3),
            "top_features": [{"feature": fi, "blame_z": round(bz, 3), "motive": s.motive_tags.get(fi, "other")}
                             for fi, bz in s.top_features],
        })
    return {
        "n_samples": report.n_samples,
        "n_alerted": report.n_alerted,
        "alert_rate": round(report.alert_rate, 4),
        "threshold": round(report.threshold, 5),
        "top_k": report.top_k,
        "attack_type_stats": report.attack_type_stats,
        "motive_distribution": report.motive_distribution,
        "persistent_offenders": report.persistent_offenders,
        "top_10_features_by_hit_rate": [
            {"feature": fi, "hit_rate": round(rate, 4)} for fi, rate in top_features_by_rate
        ],
        "example_alerts": example_alerts,
    }


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def run_tests() -> bool:
    failures = []

    def check(name, cond, detail=""):
        if not cond:
            failures.append(f"FAIL [{name}]: {detail}")

    model = MicroGPT(n_layers=6, d_model=8, seed=0)

    # T1: Dataset
    ds = make_dataset(model, n_benign=50, n_attack=20, seed=1)
    check("benign_shape", ds.benign_acts.shape == (50, 8))
    check("attack_shape", ds.attack_acts.shape == (20, 8))
    check("attack_types_len", len(ds.attack_types) == 20)

    # T2: SAE encode shape
    sae = SAE(d_model=8, d_sae=16, seed=0)
    feats = sae.encode(ds.benign_acts)
    check("encode_shape", feats.shape == (50, 16), str(feats.shape))
    check("feats_nonneg", (feats >= 0).all())

    # T3: Baseline fitting
    baseline = fit_baseline(sae, ds.benign_acts)
    check("baseline_mean_shape", baseline.feature_mean.shape == (16,))
    check("baseline_std_positive", (baseline.feature_std > 0).all())
    check("gc_direction_shape", baseline.gc_direction.shape == (8,))
    check("gc_feature_valid", 0 <= baseline.gc_feature_idx < 16)

    # T4: Incriminate single sample
    act = ds.attack_acts[0]
    inc = incriminate_sample(act, sae, baseline, threshold=0.5,
                              sample_idx=0, attack_type="suppression", top_k=3)
    check("blame_dict_len", len(inc.blame) == 16, str(len(inc.blame)))
    check("top_features_len", len(inc.top_features) == 3)
    check("top_features_sorted", inc.top_features[0][1] >= inc.top_features[-1][1])
    check("motive_tags_valid", all(v in {"audio_suppression", "prior_injection", "other"}
                                   for v in inc.motive_tags.values()))

    # T5: Patrol report on small run
    try:
        report = run_patrol(n_benign=100, n_attack=40, d_sae=16, top_k=3, seed=7)
        check("report_n_samples", report.n_samples > 0, str(report.n_samples))
        check("report_threshold_positive", report.threshold > 0)
        check("feature_hit_rate_len", len(report.feature_hit_rate) == 16)
        check("attack_types_present", "suppression" in report.attack_type_stats)
        check("alert_rate_valid", 0 <= report.alert_rate <= 1)
    except Exception as e:
        failures.append(f"FAIL [patrol_run]: {e}")

    # T6: JSON serialization
    try:
        report = run_patrol(n_benign=80, n_attack=30, d_sae=16, top_k=3, seed=5)
        j = to_json_report(report)
        check("json_keys", {"n_samples", "n_alerted", "attack_type_stats"}.issubset(j.keys()))
    except Exception as e:
        failures.append(f"FAIL [json_serial]: {e}")

    total = 3 + 2 + 4 + 5 + 6 + 2
    passed = total - len(failures)

    if failures:
        print(f"UNIT TEST RESULTS: FAIL ({passed}/{total})")
        for f in failures:
            print(f"  {f}")
        return False

    print(f"UNIT TEST RESULTS: PASS ({total}/{total})")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="SAE Incrimination Patrol (Q078 — T5)")
    parser.add_argument("--test", action="store_true", help="Run unit tests and exit")
    parser.add_argument("--n", type=int, default=600, help="Benign training samples")
    parser.add_argument("--n-attack", type=int, default=200, help="Attack samples")
    parser.add_argument("--d-sae", type=int, default=32, help="SAE dictionary size")
    parser.add_argument("--top-k", type=int, default=5, help="Top-K features per alert")
    parser.add_argument("--target-prec", type=float, default=0.9)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    if args.test:
        ok = run_tests()
        sys.exit(0 if ok else 1)

    report = run_patrol(
        n_benign=args.n, n_attack=args.n_attack, d_sae=args.d_sae,
        top_k=args.top_k, target_precision=args.target_prec, seed=args.seed,
    )

    if args.json:
        print(json.dumps(to_json_report(report), indent=2))
    else:
        print_patrol_report(report)


if __name__ == "__main__":
    main()
