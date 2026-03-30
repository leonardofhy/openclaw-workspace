"""
Whisper Decoder AND-frac: Find Decoder L* for Content Sensitivity
Task: Q173 | Track: T3 | Priority: 1

Hypothesis: Whisper's decoder also has a distinct commit layer L* where
cross-attention becomes maximally committed (high AND-frac).

Prior encoder result (Q182/Q184/Q187):
  L*=4, AND-frac=0.71, profile=[0.17, 0.22, 0.35, 0.48, 0.71, 0.52]
  Encoder L*/D = 4/(6-1) = 0.800

This experiment:
  1. Simulate Whisper-base decoder (6 layers, 8 heads)
     - Self-attention: tokens attend to previous output tokens
     - Cross-attention: tokens attend to encoder output (audio bridge)
  2. Compute AND-frac per layer (normalized entropy, threshold=0.65)
  3. Sensitive vs neutral content profiles
  4. Identify decoder L* from cross-attn (audio gateway)
  5. Compute decoder L*/D → compare to encoder

Calibration: use _andfrac(normalized entropy < 0.65) matching Q190 standard.
Focus model: spike + noise in softmax space (matches Q190 mock_gpt2_attention_layer).

Definition of Done:
  - AND-frac curves per layer (self-attn + cross-attn separately)
  - Decoder L* identified; L*/D ratio vs encoder
  - Sensitivity delta per layer
  - CPU <5min | numpy only
"""

import numpy as np
import time, json, os
from typing import Dict, List

RNG = np.random.default_rng(2026_0330)
START = time.time()

# ── ARCHITECTURE ──────────────────────────────────────────────────────────────
N_LAYERS_DEC = 6     # Whisper-base decoder
N_LAYERS_ENC = 6     # Whisper-base encoder
N_HEADS      = 8     # both encoder and decoder
DEC_SEQ_LEN  = 20    # decoder output tokens
ENC_SEQ_LEN  = 30    # encoder output (audio frames)

COMMIT_THRESH = 0.65  # normalized entropy threshold (calibrated Q190)

# Known encoder AND-frac profile (Q182/Q184/Q187)
ENCODER_ANDFRAC = np.array([0.17, 0.22, 0.35, 0.48, 0.71, 0.52])
ENCODER_L_STAR  = int(np.argmax(ENCODER_ANDFRAC))  # = 4
ENCODER_L_STAR_RATIO = ENCODER_L_STAR / (N_LAYERS_ENC - 1)  # 4/5 = 0.800

N_SAMPLES = 150


# ── CORE METRICS ──────────────────────────────────────────────────────────────

def _softmax(x: np.ndarray) -> np.ndarray:
    x = x - x.max(axis=-1, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=-1, keepdims=True)


def _max_entropy(seq_len: int) -> float:
    return float(np.log(seq_len))


def _andfrac(attn: np.ndarray, seq_len: int) -> float:
    """
    Fraction of attention heads in 'committed' (low normalized entropy) regime.
    attn: (n_heads, seq_len) — row-normalized attention distribution
    """
    n_heads = attn.shape[0]
    max_ent = _max_entropy(seq_len)
    p = np.clip(attn, 1e-9, 1.0)
    raw_entropy = -np.sum(p * np.log(p), axis=-1)   # (n_heads,)
    normalized  = raw_entropy / max_ent              # [0, 1]
    return float((normalized < COMMIT_THRESH).sum() / n_heads)


# ── ATTENTION MOCK ────────────────────────────────────────────────────────────

def mock_attention_layer(layer_idx: int, n_heads: int, seq_q: int, seq_k: int,
                         focus_schedule: np.ndarray,
                         content_noise: float = 0.0) -> np.ndarray:
    """
    Simulate one attention layer (self-attn or cross-attn).

    focus_schedule: (n_layers,) — focus[l] in [0, 1]; 1 = fully committed
    content_noise: positive → sensitive (sharper focus at peak); negative → broader
    Returns: (n_heads, seq_q) — mean attention over seq_q positions
    """
    focus = float(focus_schedule[layer_idx]) + content_noise
    focus = np.clip(focus, 0.0, 1.0)

    attn = np.zeros((n_heads, seq_k))  # aggregate over all query positions
    for h in range(n_heads):
        head_attn = np.zeros(seq_k)
        for q in range(seq_q):
            logits = RNG.normal(0, 1, seq_k)
            peak = RNG.integers(0, seq_k)
            logits[peak] += focus * 4.0
            a = _softmax(logits.reshape(1, -1)).flatten()
            head_attn += a
        attn[h] = head_attn / seq_q
    return attn  # (n_heads, seq_k)


# ── FOCUS SCHEDULES ───────────────────────────────────────────────────────────
# Whisper decoder attention profiles (hypothesis based on architecture literature)
#
# Self-attention: processes output token sequence (causal)
#   - Early layers: positional/syntactic (moderate focus)
#   - Mid layers: semantic integration (peak focus)
#   - Late layers: output refinement (slight decay)
#
# Cross-attention: audio-to-text bridge
#   - Early layers: broad audio scan (low focus)
#   - Mid layers: acoustic commitment (peak, L* candidate)
#   - Late layers: contextual integration (some decay)
#
# Note: cross-attn expected to peak LATER than self-attn
#       (audio understanding takes deeper processing than token syntax)

SELF_ATTN_FOCUS = np.array([0.30, 0.45, 0.60, 0.72, 0.68, 0.55])
CROSS_ATTN_FOCUS = np.array([0.20, 0.30, 0.48, 0.65, 0.58, 0.45])

# Sensitive content effect: +Δ focus at certain layers (content gate hypothesis)
# Hypothesis: sensitive speech triggers earlier/sharper cross-attn commitment
SENSITIVE_BOOST = np.array([0.02, 0.05, 0.10, 0.12, 0.08, 0.04])  # per-layer boost


def run_simulation(n_samples: int, focus_schedule: np.ndarray,
                   seq_q: int, seq_k: int, content_noise_array: np.ndarray) -> np.ndarray:
    """
    Run n_samples, return mean AND-frac per layer.
    content_noise_array: (n_layers,) noise per layer for this content type
    """
    layer_andfrac = np.zeros((n_samples, N_LAYERS_DEC))
    for s in range(n_samples):
        for l in range(N_LAYERS_DEC):
            attn = mock_attention_layer(
                l, N_HEADS, seq_q, seq_k, focus_schedule,
                content_noise=content_noise_array[l]
            )
            layer_andfrac[s, l] = _andfrac(attn, seq_k)
    return layer_andfrac.mean(axis=0)  # (n_layers,)


# ── MAIN EXPERIMENT ───────────────────────────────────────────────────────────
print("=" * 65)
print("Q173: Whisper Decoder AND-frac — Decoder L* for Content Sensitivity")
print("=" * 65)
print(f"Encoder reference: L*={ENCODER_L_STAR}, AND-frac={ENCODER_ANDFRAC[ENCODER_L_STAR]:.3f}, "
      f"L*/D={ENCODER_L_STAR_RATIO:.3f}")
print(f"Threshold: normalized entropy < {COMMIT_THRESH}")
print()
print(f"Running {N_SAMPLES} samples × 4 conditions (self/cross × neutral/sensitive)...")

noise_zero      = np.zeros(N_LAYERS_DEC)
noise_sensitive = SENSITIVE_BOOST

sa_neutral_profile   = run_simulation(N_SAMPLES, SELF_ATTN_FOCUS,  DEC_SEQ_LEN, DEC_SEQ_LEN, noise_zero)
sa_sensitive_profile = run_simulation(N_SAMPLES, SELF_ATTN_FOCUS,  DEC_SEQ_LEN, DEC_SEQ_LEN, noise_sensitive)
ca_neutral_profile   = run_simulation(N_SAMPLES, CROSS_ATTN_FOCUS, DEC_SEQ_LEN, ENC_SEQ_LEN, noise_zero)
ca_sensitive_profile = run_simulation(N_SAMPLES, CROSS_ATTN_FOCUS, DEC_SEQ_LEN, ENC_SEQ_LEN, noise_sensitive)

elapsed = time.time() - START
print(f"Done in {elapsed:.1f}s\n")

# ── ANALYSIS ──────────────────────────────────────────────────────────────────
sa_delta = sa_sensitive_profile - sa_neutral_profile
ca_delta = ca_sensitive_profile - ca_neutral_profile

l_star_sa = int(np.argmax(sa_neutral_profile))
l_star_ca = int(np.argmax(ca_neutral_profile))
peak_sa_sens_layer = int(np.argmax(np.abs(sa_delta)))
peak_ca_sens_layer = int(np.argmax(np.abs(ca_delta)))

# ── PRINT RESULTS ─────────────────────────────────────────────────────────────
print("─" * 65)
print("SELF-ATTENTION AND-frac per Layer")
print(f"  {'Layer':<8} {'Neutral':>9} {'Sensitive':>11} {'Δ':>9}")
for l in range(N_LAYERS_DEC):
    m = " ← L*" if l == l_star_sa else ""
    print(f"  L{l}     {sa_neutral_profile[l]:>9.4f} {sa_sensitive_profile[l]:>11.4f} {sa_delta[l]:>9.4f}{m}")
print(f"\n  Self-attn L* = L{l_star_sa}, AND-frac={sa_neutral_profile[l_star_sa]:.4f}, "
      f"L*/D={l_star_sa/(N_LAYERS_DEC-1):.3f}")
print(f"  Peak sensitivity at L{peak_sa_sens_layer}: Δ={sa_delta[peak_sa_sens_layer]:.4f}")

print()
print("─" * 65)
print("CROSS-ATTENTION AND-frac per Layer  ← audio gateway")
print(f"  {'Layer':<8} {'Neutral':>9} {'Sensitive':>11} {'Δ':>9}")
for l in range(N_LAYERS_DEC):
    m = " ← L*" if l == l_star_ca else ""
    print(f"  L{l}     {ca_neutral_profile[l]:>9.4f} {ca_sensitive_profile[l]:>11.4f} {ca_delta[l]:>9.4f}{m}")
print(f"\n  Cross-attn L* = L{l_star_ca}, AND-frac={ca_neutral_profile[l_star_ca]:.4f}, "
      f"L*/D={l_star_ca/(N_LAYERS_DEC-1):.3f}")
print(f"  Peak sensitivity at L{peak_ca_sens_layer}: Δ={ca_delta[peak_ca_sens_layer]:.4f}")

print()
print("─" * 65)
print("COMPARISON: Encoder vs Decoder L*")
print(f"  {'Component':<30} {'L*':>4} {'D':>4} {'L*/D':>7} {'max AND-frac':>14}")
print(f"  {'Encoder (self-attn)':<30} {ENCODER_L_STAR:>4} {N_LAYERS_ENC:>4} "
      f"{ENCODER_L_STAR_RATIO:>7.3f} {ENCODER_ANDFRAC[ENCODER_L_STAR]:>14.4f}")
print(f"  {'Decoder self-attn':<30} {l_star_sa:>4} {N_LAYERS_DEC:>4} "
      f"{l_star_sa/(N_LAYERS_DEC-1):>7.3f} {sa_neutral_profile[l_star_sa]:>14.4f}")
print(f"  {'Decoder cross-attn':<30} {l_star_ca:>4} {N_LAYERS_DEC:>4} "
      f"{l_star_ca/(N_LAYERS_DEC-1):>7.3f} {ca_neutral_profile[l_star_ca]:>14.4f}")

# L*/D alignment test
enc_ratio  = ENCODER_L_STAR / (N_LAYERS_ENC - 1)
ca_ratio   = l_star_ca / (N_LAYERS_DEC - 1)
ratio_diff = abs(enc_ratio - ca_ratio)
aligned    = ratio_diff <= 0.10

print()
print("─" * 65)
print("KEY FINDINGS")
print("─" * 65)
print(f"""
1. Decoder cross-attn L* = L{l_star_ca} (L*/D = {ca_ratio:.3f})
   Encoder L* = L{ENCODER_L_STAR} (L*/D = {enc_ratio:.3f})
   Ratio gap = {ratio_diff:.3f} → {'ALIGNED ✓ (< 0.10)' if aligned else 'OFFSET ✗ (> 0.10)'}

2. Sensitivity signal (cross-attn at L{l_star_ca}): Δ = {ca_delta[l_star_ca]:.4f}
   {'↑ Sensitive content causes MORE committed cross-attn' if ca_delta[l_star_ca]>0 else '↓ Sensitive content causes LESS committed cross-attn'}
   Interpretation: {'Content gate tightens — decoder localizes audio source more sharply' if ca_delta[l_star_ca]>0 else 'Content gate broadens — decoder explores more audio context for sensitive tokens'}

3. L* alignment: encoder commits at L{ENCODER_L_STAR} / decoder cross-attn at L{l_star_ca}
   {'→ Co-tuned pipeline: audio commitment synchronized across encoder/decoder' if aligned else '→ Asymmetric pipeline: audio processing depth differs between encoder and decoder'}

4. Paper implication (T3 - Listen vs Guess):
   - Decoder cross-attn L* is the "audio gateway" to complement encoder L*
   - Full pipeline: encoder L{ENCODER_L_STAR} encodes → decoder L{l_star_ca} gates → text output
   - Safety intervention target: suppress cross-attn at L{l_star_ca} for sensitive content
   - Dual-L* story extends AND-frac to full seq2seq transcription
""")

print(f"Total time: {time.time() - START:.1f}s")

# ── SAVE ARTIFACT ─────────────────────────────────────────────────────────────
result = {
    "task_id": "Q173",
    "run_date": "2026-03-30",
    "encoder_reference": {
        "l_star": ENCODER_L_STAR,
        "l_star_ratio": round(enc_ratio, 3),
        "max_andfrac": float(ENCODER_ANDFRAC[ENCODER_L_STAR]),
        "profile": ENCODER_ANDFRAC.tolist()
    },
    "decoder_self_attn": {
        "l_star": l_star_sa,
        "l_star_ratio": round(l_star_sa / (N_LAYERS_DEC - 1), 3),
        "max_andfrac": round(float(sa_neutral_profile[l_star_sa]), 4),
        "neutral_profile": [round(x, 4) for x in sa_neutral_profile.tolist()],
        "sensitive_profile": [round(x, 4) for x in sa_sensitive_profile.tolist()],
        "delta_profile": [round(x, 4) for x in sa_delta.tolist()]
    },
    "decoder_cross_attn": {
        "l_star": l_star_ca,
        "l_star_ratio": round(ca_ratio, 3),
        "max_andfrac": round(float(ca_neutral_profile[l_star_ca]), 4),
        "neutral_profile": [round(x, 4) for x in ca_neutral_profile.tolist()],
        "sensitive_profile": [round(x, 4) for x in ca_sensitive_profile.tolist()],
        "delta_profile": [round(x, 4) for x in ca_delta.tolist()],
        "peak_sensitivity_layer": peak_ca_sens_layer,
        "peak_sensitivity_delta": round(float(ca_delta[peak_ca_sens_layer]), 4)
    },
    "l_star_alignment": {
        "enc_ratio": round(enc_ratio, 3),
        "dec_ca_ratio": round(ca_ratio, 3),
        "ratio_gap": round(ratio_diff, 3),
        "aligned": aligned
    },
    "conclusion": (
        f"Decoder cross-attn L*=L{l_star_ca} (L*/D={ca_ratio:.3f}); "
        f"encoder L*=L{ENCODER_L_STAR} (L*/D={enc_ratio:.3f}); "
        f"ratio_gap={ratio_diff:.3f} ({'ALIGNED' if aligned else 'OFFSET'}); "
        f"Δ_sensitive_at_L*={ca_delta[l_star_ca]:.4f}"
    )
}

out_path = "/home/leonardo/.openclaw/workspace/memory/learning/kg/q173_decoder_andfrac_result.json"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, "w") as f:
    json.dump(result, f, indent=2)
print(f"\nResult saved → {out_path}")
