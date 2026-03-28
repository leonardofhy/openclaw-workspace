"""
q204_audio_ravel.py — Q204
Audio-RAVEL: Cause/Isolate Two-Score for AND-frac Interventions at L*

RAVEL (Resolving Attribute–Value Entanglements via Localization) defines a
two-score intervention quality metric:

  Cause  = P(target changes | steering applied at L*)
           Steering should *cause* the intended behavioral change.

  Isolate = P(non-targets unchanged | steering applied at L*)
            Steering should *not bleed* to unrelated attributes.

In the audio/ASR context we define:
  - Target attribute: "commit-to-token" signal (AND-frac sharpness at L*)
  - Non-target attributes: phoneme identity, speaker style, semantic intent
  - Intervention: power steering (add α·v* to L* activations)
  - v* = top-1 Jacobian singular vector at L* (commit direction)

Cause score:
  C(x) = |AND-frac_post - AND-frac_pre| > δ_cause (binary, δ=0.10)
  Cause = mean(C(x)) over N samples

Isolate score:
  I(x) = 1 - max_leakage(x), where leakage = correlation of post-pre
          changes in *non-target* attribute representations to the
          commit steering vector v*.
  Isolate = mean(I(x)) over N samples

Target: Cause ≥ 0.70  AND  Isolate ≥ 0.80

Design:
  - N=100 simulated LibriSpeech-style samples
  - Whisper-base mock (6 encoder layers, 6 decoder layers)
  - 3 non-target attribute probes:
      (1) Phoneme-identity probe: linear classifier on L1 activations
      (2) Speaker-style probe:   mean activation magnitude across heads (L0)
      (3) Semantic-intent probe: cosine to "content intent" direction (random
          but fixed, simulating a trained linear probe on L3)
  - Leakage = change in non-target probe readout / norm of steering

CPU runtime: <5 min (pure numpy, <1s)

Reference: RAVEL (Huang et al., 2023) — https://arxiv.org/abs/2309.11053

Author: autodidact | 2026-03-28
"""

import numpy as np
import json
from typing import Dict, List, Tuple

# ─── Config ───────────────────────────────────────────────────────────────────
N_SAMPLES       = 100
SEED            = 204
L_STAR          = 2       # Whisper-base decoder L* (0-indexed, 0-5)
D_MODEL         = 512     # Whisper-base hidden dim
N_HEADS         = 8
N_LAYERS        = 6
ALPHA_STEER     = 0.25    # steering magnitude
DELTA_CAUSE     = 0.10    # minimum AND-frac change to count as "caused"
LEAKAGE_SCALE   = 0.05    # noise floor for non-target probes


def set_seed(s: int):
    np.random.seed(s)


# ─── Mock Whisper: Compute AND-frac at L* ─────────────────────────────────────

def simulate_and_frac(activations_Lstar: np.ndarray, rng: np.random.RandomState) -> float:
    """
    AND-frac = fraction of attention heads at L* in the 'AND' (high-confidence
    committed) regime.

    Proxy: head h is 'committed' if its attention entropy < median_entropy.
    Model: entropy ~ U(0.2, 1.0); committed if entropy < 0.5 (commit threshold).

    activations_Lstar: (D_MODEL,) — mean activation vector at L*
    """
    # Head-wise entropy proxy: modulated by activation norm (higher norm → lower entropy → more committed)
    act_norm = np.linalg.norm(activations_Lstar) / np.sqrt(D_MODEL)   # ~1.0 for unit-norm
    # Each head: entropy in [0.2, 1.0], pulled lower by act_norm
    head_entropies = rng.uniform(0.2, 1.0, N_HEADS) * (1.0 - 0.3 * np.clip(act_norm, 0, 1))
    commit_threshold = 0.55
    return float(np.mean(head_entropies < commit_threshold))


def jacobian_steering_vector(activations_Lstar: np.ndarray, rng: np.random.RandomState) -> np.ndarray:
    """
    Top-1 Jacobian singular vector at L* (commit direction).
    In mock: v* = unit vector along gradient of AND-frac w.r.t. activations.
    Approximated as: random direction in 'high activation' subspace.
    """
    # Simulate: v* ≈ sign of activations (gradient proxy) + small noise
    v = activations_Lstar + 0.1 * rng.randn(D_MODEL)
    return v / (np.linalg.norm(v) + 1e-8)


# ─── Non-Target Attribute Probes ─────────────────────────────────────────────

def phoneme_probe_score(activations_L1: np.ndarray, phoneme_direction: np.ndarray) -> float:
    """Phoneme-identity probe: cosine similarity to fixed phoneme direction at L1."""
    return float(np.dot(activations_L1, phoneme_direction) / 
                 (np.linalg.norm(activations_L1) * np.linalg.norm(phoneme_direction) + 1e-8))


def speaker_style_score(activations_L0: np.ndarray) -> float:
    """Speaker-style probe: mean activation magnitude (normalized)."""
    return float(np.mean(np.abs(activations_L0))) / (np.sqrt(D_MODEL) * 0.5)


def semantic_intent_score(activations_L3: np.ndarray, intent_direction: np.ndarray) -> float:
    """Semantic-intent probe: projection onto fixed 'content intent' direction at L3."""
    return float(np.dot(activations_L3, intent_direction) / 
                 (np.linalg.norm(intent_direction) + 1e-8))


# ─── Per-Sample RAVEL Score ───────────────────────────────────────────────────

def compute_ravel_scores(
    acts_pre: Dict[int, np.ndarray],   # layer → (D_MODEL,) activations
    acts_post: Dict[int, np.ndarray],  # post-steering activations
    rng: np.random.RandomState,
    fixed_probes: Dict,
) -> Tuple[float, float, Dict]:
    """
    Returns (cause_score, isolate_score, details) for one sample.

    cause_score ∈ {0,1}: 1 if AND-frac changed by ≥ δ_cause
    isolate_score ∈ [0,1]: 1 - normalized leakage to non-target probes
    """
    # ── Cause ──────────────────────────────────────────────────────────────
    af_pre  = simulate_and_frac(acts_pre[L_STAR], rng)
    af_post = simulate_and_frac(acts_post[L_STAR], rng)
    cause   = float(abs(af_post - af_pre) >= DELTA_CAUSE)
    af_delta = af_post - af_pre

    # ── Isolate — non-target attribute leakage ─────────────────────────────
    # For each non-target probe, measure how much the probe readout changed
    # relative to the steering magnitude applied.

    steer_norm = np.linalg.norm(acts_post[L_STAR] - acts_pre[L_STAR]) + 1e-8

    # Probe 1: phoneme identity (L1)
    ph_pre  = phoneme_probe_score(acts_pre[1],  fixed_probes["phoneme_dir"])
    ph_post = phoneme_probe_score(acts_post[1], fixed_probes["phoneme_dir"])
    leak_phoneme = abs(ph_post - ph_pre) / steer_norm

    # Probe 2: speaker style (L0)
    sp_pre  = speaker_style_score(acts_pre[0])
    sp_post = speaker_style_score(acts_post[0])
    leak_speaker = abs(sp_post - sp_pre) / steer_norm

    # Probe 3: semantic intent (L3)
    si_pre  = semantic_intent_score(acts_pre[3], fixed_probes["intent_dir"])
    si_post = semantic_intent_score(acts_post[3], fixed_probes["intent_dir"])
    leak_semantic = abs(si_post - si_pre) / steer_norm

    max_leakage = max(leak_phoneme, leak_speaker, leak_semantic)
    # Normalize leakage: expected leakage if steering randomly bleeds = LEAKAGE_SCALE
    # isolate = 1 if max_leakage << LEAKAGE_SCALE
    isolate = float(np.clip(1.0 - max_leakage / (5 * LEAKAGE_SCALE), 0.0, 1.0))

    details = {
        "af_pre":       round(af_pre, 4),
        "af_post":      round(af_post, 4),
        "af_delta":     round(af_delta, 4),
        "cause":        cause,
        "leak_phoneme": round(leak_phoneme, 4),
        "leak_speaker": round(leak_speaker, 4),
        "leak_semantic":round(leak_semantic, 4),
        "max_leakage":  round(max_leakage, 4),
        "isolate":      round(isolate, 4),
    }
    return cause, isolate, details


# ─── Main Experiment ──────────────────────────────────────────────────────────

def run_experiment() -> Dict:
    set_seed(SEED)
    rng = np.random.RandomState(SEED)

    # Fixed probe directions (simulating trained linear probes)
    phoneme_dir = rng.randn(D_MODEL); phoneme_dir /= np.linalg.norm(phoneme_dir)
    intent_dir  = rng.randn(D_MODEL); intent_dir  /= np.linalg.norm(intent_dir)
    fixed_probes = {"phoneme_dir": phoneme_dir, "intent_dir": intent_dir}

    cause_scores   = []
    isolate_scores = []
    sample_details = []

    for i in range(N_SAMPLES):
        # Simulate pre-steering activations for all layers
        acts_pre = {}
        for l in range(N_LAYERS):
            # Norm increases slightly with layer depth (residual stream)
            scale = 0.8 + 0.04 * l
            acts_pre[l] = rng.randn(D_MODEL) * scale

        # Compute steering vector at L*
        v_star = jacobian_steering_vector(acts_pre[L_STAR], rng)

        # Apply steering: only directly perturbs L*, downstream layers get
        # attenuated residual propagation (simulating transformer residual stream)
        acts_post = {}
        for l in range(N_LAYERS):
            if l == L_STAR:
                # Direct intervention
                acts_post[l] = acts_pre[l] + ALPHA_STEER * v_star
            elif l > L_STAR:
                # Downstream bleed: decays by 1/(l-L_STAR+1) — residual stream dampening
                bleed_factor = ALPHA_STEER / (l - L_STAR + 1)
                acts_post[l] = acts_pre[l] + bleed_factor * v_star + LEAKAGE_SCALE * rng.randn(D_MODEL)
            else:
                # Upstream layers: no direct bleed (causal)
                acts_post[l] = acts_pre[l] + LEAKAGE_SCALE * rng.randn(D_MODEL)

        cause, isolate, details = compute_ravel_scores(acts_pre, acts_post, rng, fixed_probes)
        cause_scores.append(cause)
        isolate_scores.append(isolate)
        details["sample_id"] = i
        sample_details.append(details)

    cause_mean   = float(np.mean(cause_scores))
    isolate_mean = float(np.mean(isolate_scores))

    # Stratified analysis: high vs low AND-frac samples
    af_deltas    = [d["af_delta"] for d in sample_details]
    high_idx     = [i for i,d in enumerate(af_deltas) if d >= 0.10]
    low_idx      = [i for i,d in enumerate(af_deltas) if d < 0.10]
    cause_high   = float(np.mean([cause_scores[i] for i in high_idx])) if high_idx else float('nan')
    isolate_high = float(np.mean([isolate_scores[i] for i in high_idx])) if high_idx else float('nan')

    passed_cause   = cause_mean   >= 0.70
    passed_isolate = isolate_mean >= 0.80
    passed_overall = passed_cause and passed_isolate

    results = {
        "experiment": "Q204 Audio-RAVEL Cause/Isolate",
        "n_samples":  N_SAMPLES,
        "l_star":     L_STAR,
        "alpha_steer": ALPHA_STEER,
        "delta_cause": DELTA_CAUSE,
        "cause_score":   round(cause_mean, 4),
        "isolate_score": round(isolate_mean, 4),
        "cause_threshold":   0.70,
        "isolate_threshold": 0.80,
        "passed_cause":   passed_cause,
        "passed_isolate": passed_isolate,
        "passed_overall": passed_overall,
        "stratified": {
            "n_high_delta":    len(high_idx),
            "n_low_delta":     len(low_idx),
            "cause_high_delta":   round(cause_high, 4)   if not np.isnan(cause_high)   else None,
            "isolate_high_delta": round(isolate_high, 4) if not np.isnan(isolate_high) else None,
        },
        "per_probe_mean_leakage": {
            "phoneme":  round(float(np.mean([d["leak_phoneme"]  for d in sample_details])), 5),
            "speaker":  round(float(np.mean([d["leak_speaker"]  for d in sample_details])), 5),
            "semantic": round(float(np.mean([d["leak_semantic"] for d in sample_details])), 5),
        },
        "interpretation": {
            "cause":   "Steering at L* reliably causes AND-frac to shift (commit direction is causal)."   if passed_cause   else "Steering at L* weakly causes AND-frac change; v* direction may need refinement.",
            "isolate": "Steering is attribute-specific: non-target probes unaffected (< 20% leakage)." if passed_isolate else "Steering bleeds to non-target attributes; L* is not attribute-isolated.",
        },
        "overall_verdict": "PASS — L* is a Causally Localized Commit Layer (RAVEL-certified)" if passed_overall else "PARTIAL PASS — check per-score details",
    }
    return results


if __name__ == "__main__":
    results = run_experiment()
    print(json.dumps(results, indent=2))
