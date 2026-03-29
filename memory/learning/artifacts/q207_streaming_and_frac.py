"""
q207_streaming_and_frac.py — Q207
AND-frac Streaming Monitor: Real-Time Commitment Detection on Partial Audio

Hypothesis: AND-frac at L* (Listen Layer) computed on sliding audio windows
can detect the onset of model commitment *before* the full utterance is
processed. This enables real-time ASR quality monitoring and early-exit
decoding.

Design:
  - Simulate 200 utterances (LibriSpeech-style, 2–8 second range)
  - Each utterance is divided into T frames (T = total_duration / frame_ms)
  - For each utterance, compute AND-frac on sliding windows:
      window_t = frames [0 .. t] (causal streaming — no future frames)
  - "Commit onset" = first t where AND-frac crosses threshold θ
  - Metrics:
      (a) Detection latency: ms from start to commit onset
      (b) AUROC: can commit-onset predict final high-confidence token?
      (c) Full-window AND-frac as reference (upper bound)
  - Baseline: detect commit only after full window (latency = utterance length)
  - Target: AUROC > 0.75 with average latency < 70% of full utterance length

CPU runtime: <5 min (pure numpy)

Author: autodidact | 2026-03-29
"""

import numpy as np
import json
from typing import Dict, List, Tuple, Optional

# ─── Config ────────────────────────────────────────────────────────────────────
RNG_SEED = 42
N_UTTERANCES = 200
FRAME_MS = 20          # 20ms per frame (standard ASR)
MIN_DUR_MS = 2000      # 2 seconds min utterance
MAX_DUR_MS = 8000      # 8 seconds max
L_STAR_FRAC = 0.60     # L* ≈ 60% through model depth (Whisper-base: layer 3/6)
N_HEADS = 6            # Whisper-base attention heads at L*
D_MODEL = 512          # Model hidden dim
COMMIT_THRESHOLD = 0.65  # AND-frac threshold for "committed" state
TARGET_AUROC = 0.75

# ─── Mock Attention Generator ──────────────────────────────────────────────────

def generate_mock_attention(
    n_frames: int,
    n_heads: int,
    utterance_type: str,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Generate mock attention weight matrix at L* for n_frames tokens.
    Shape: (n_heads, n_frames, n_frames) — causal self-attention.

    utterance_type:
      'clean'   → sharp AND-frac pattern that develops early
      'noisy'   → delayed commit, weaker signal
      'short'   → fast commit
    """
    # Base noise
    attn = rng.dirichlet(np.ones(n_frames) * 0.5, size=(n_heads, n_frames))
    # attn[h, t, :] = attention distribution for position t

    # Commit signal: at some onset frame, attention sharpens
    if utterance_type == 'clean':
        onset_frac = rng.uniform(0.3, 0.5)  # commit onset at 30-50% of frames
        sharpness = rng.uniform(2.0, 4.0)
    elif utterance_type == 'noisy':
        onset_frac = rng.uniform(0.5, 0.8)  # commit onset later
        sharpness = rng.uniform(0.5, 1.5)
    else:  # short
        onset_frac = rng.uniform(0.2, 0.4)
        sharpness = rng.uniform(2.5, 5.0)

    onset_frame = max(1, int(onset_frac * n_frames))
    for h in range(n_heads):
        for t in range(onset_frame, n_frames):
            # Sharpen attention toward most-attended position
            peak = rng.integers(0, t + 1)
            sharp_attn = np.zeros(n_frames)
            sharp_attn[peak] = sharpness
            sharp_attn = np.exp(sharp_attn)
            sharp_attn /= sharp_attn.sum()
            # Blend with base noise
            blend = min(1.0, (t - onset_frame + 1) / max(1, n_frames * 0.3))
            attn[h, t, :] = (1 - blend) * attn[h, t, :] + blend * sharp_attn

    return attn  # (n_heads, n_frames, n_frames)


def compute_and_frac(attn: np.ndarray, threshold: float = 0.1) -> float:
    """
    AND-frac at L*: fraction of heads × positions where attention weight
    exceeds threshold (captures "commit" — heads agree on a focused position).

    attn: (n_heads, n_frames, n_frames)
    Returns: scalar in [0, 1]
    """
    n_heads, n_frames, _ = attn.shape
    # For each head and each query position, is there a key with weight > thresh?
    # AND-frac = fraction of (head, query) pairs that "fired"
    max_weights = attn.max(axis=2)  # (n_heads, n_frames)
    fired = (max_weights > threshold).astype(float)
    return fired.mean()


# ─── Streaming Simulation ──────────────────────────────────────────────────────

def simulate_utterance(
    utterance_id: int,
    rng: np.random.Generator,
) -> Dict:
    """
    Simulate one utterance with streaming AND-frac computation.
    Returns per-utterance results dict.
    """
    # Utterance properties
    dur_ms = rng.integers(MIN_DUR_MS, MAX_DUR_MS + 1)
    n_frames = dur_ms // FRAME_MS
    utype = rng.choice(['clean', 'noisy', 'short'], p=[0.5, 0.3, 0.2])

    # Generate full utterance attention
    full_attn = generate_mock_attention(n_frames, N_HEADS, utype, rng)

    # Compute full-window AND-frac (reference)
    full_and_frac = compute_and_frac(full_attn)

    # "Ground truth": utterance is high-confidence if full AND-frac is high
    is_committed = float(full_and_frac >= COMMIT_THRESHOLD)

    # Streaming: compute AND-frac at each partial window
    streaming_and_frac = []
    for t in range(1, n_frames + 1):
        partial_attn = full_attn[:, :t, :t]  # causal: only first t×t
        af = compute_and_frac(partial_attn)
        streaming_and_frac.append(af)

    streaming_and_frac = np.array(streaming_and_frac)

    # Detect commit onset: first t where streaming AND-frac >= COMMIT_THRESHOLD
    onset_frame = None
    for t, af in enumerate(streaming_and_frac):
        if af >= COMMIT_THRESHOLD:
            onset_frame = t + 1  # 1-indexed
            break

    onset_ms = (onset_frame * FRAME_MS) if onset_frame is not None else dur_ms
    onset_frac_of_total = onset_ms / dur_ms

    return {
        "id": utterance_id,
        "type": utype,
        "dur_ms": int(dur_ms),
        "n_frames": int(n_frames),
        "full_and_frac": float(full_and_frac),
        "is_committed": float(is_committed),
        "onset_ms": int(onset_ms),
        "onset_frac": float(onset_frac_of_total),
        "detected": onset_frame is not None,
        "streaming_and_frac_final": float(streaming_and_frac[-1]),
        # For AUROC: use onset_frac as anomaly score (lower = detected earlier = more confident)
        "auroc_score": 1.0 - onset_frac_of_total,  # Higher = commit detected earlier
    }


# ─── AUROC Computation ────────────────────────────────────────────────────────

def compute_auroc(labels: np.ndarray, scores: np.ndarray) -> float:
    """Simple AUROC via trapezoidal rule."""
    thresholds = np.unique(scores)[::-1]
    tprs, fprs = [0.0], [0.0]
    pos = labels.sum()
    neg = len(labels) - pos
    if pos == 0 or neg == 0:
        return 0.5
    for t in thresholds:
        pred = (scores >= t).astype(float)
        tp = (pred * labels).sum()
        fp = (pred * (1 - labels)).sum()
        tprs.append(tp / pos)
        fprs.append(fp / neg)
    tprs.append(1.0)
    fprs.append(1.0)
    return float(np.trapezoid(tprs, fprs))


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    rng = np.random.default_rng(RNG_SEED)
    results = []

    for i in range(N_UTTERANCES):
        r = simulate_utterance(i, rng)
        results.append(r)

    # ── Latency Analysis ──
    detected = [r for r in results if r["detected"]]
    not_detected = [r for r in results if not r["detected"]]
    detection_rate = len(detected) / N_UTTERANCES
    avg_onset_ms = np.mean([r["onset_ms"] for r in detected]) if detected else 0
    avg_dur_ms = np.mean([r["dur_ms"] for r in results])
    avg_onset_frac = np.mean([r["onset_frac"] for r in detected]) if detected else 1.0

    # Baseline: detect only after full utterance → latency = 100%
    baseline_latency_frac = 1.0
    latency_reduction = baseline_latency_frac - avg_onset_frac

    # ── AUROC ──
    labels = np.array([r["is_committed"] for r in results])
    scores = np.array([r["auroc_score"] for r in results])
    auroc = compute_auroc(labels, scores)

    # ── By utterance type ──
    by_type = {}
    for utype in ["clean", "noisy", "short"]:
        subset = [r for r in results if r["type"] == utype]
        if subset:
            by_type[utype] = {
                "n": len(subset),
                "detection_rate": np.mean([r["detected"] for r in subset]),
                "avg_onset_frac": float(np.mean([r["onset_frac"] for r in subset])),
                "avg_full_and_frac": float(np.mean([r["full_and_frac"] for r in subset])),
            }

    # ── Streaming vs Full consistency ──
    full_afs = np.array([r["full_and_frac"] for r in results])
    stream_finals = np.array([r["streaming_and_frac_final"] for r in results])
    streaming_full_corr = float(np.corrcoef(full_afs, stream_finals)[0, 1])

    summary = {
        "n_utterances": N_UTTERANCES,
        "commit_threshold": COMMIT_THRESHOLD,
        "target_auroc": TARGET_AUROC,
        "detection_rate": float(detection_rate),
        "avg_onset_ms": float(avg_onset_ms),
        "avg_utterance_dur_ms": float(avg_dur_ms),
        "avg_onset_frac_of_total": float(avg_onset_frac),
        "latency_reduction_vs_full": float(latency_reduction),
        "auroc": float(auroc),
        "auroc_passes": bool(auroc >= TARGET_AUROC),
        "streaming_full_and_frac_correlation": float(streaming_full_corr),
        "by_utterance_type": by_type,
        "conclusion": "",
    }

    # Conclusion
    if auroc >= TARGET_AUROC and avg_onset_frac < 0.70:
        conclusion = (
            f"✅ PASS: AUROC={auroc:.3f} ≥ {TARGET_AUROC} "
            f"AND commit detected at {avg_onset_frac:.1%} of utterance "
            f"(latency reduction: {latency_reduction:.1%} vs full-window baseline). "
            f"AND-frac streaming monitor is viable for real-time ASR commitment detection."
        )
    elif auroc >= TARGET_AUROC:
        conclusion = (
            f"⚠️ PARTIAL: AUROC={auroc:.3f} ≥ {TARGET_AUROC} but "
            f"onset at {avg_onset_frac:.1%} of utterance (target: <70%). "
            f"Discriminative but not early enough for real-time use."
        )
    else:
        conclusion = (
            f"❌ FAIL: AUROC={auroc:.3f} < {TARGET_AUROC}. "
            f"AND-frac streaming monitor insufficient for commitment detection."
        )
    summary["conclusion"] = conclusion

    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    main()
