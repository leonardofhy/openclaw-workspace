"""
Q127: Stressed syllable x AND/OR gate

Hypothesis: Prosodic emphasis (stressed syllables) requires audio-committed processing
→ AND-gate dominant. Unstressed syllables are text-predictable → OR-gate dominant.

Mechanism: In Whisper cross-attention, stressed syllables carry unique acoustic contours
(F0, duration, intensity) that cannot be predicted from text context alone. These must
flow through the AND gate (both audio + text paths active). Unstressed syllables in
predictable positions (function words, reduced vowels) have sufficient text-prior to
allow OR-gate (either path sufficient).

Mock: Simulate AND-gate fraction (and_frac) for stressed vs unstressed tokens.
Expected: stressed_and_frac >> unstressed_and_frac

Metric: and_frac(t) = fraction of features at step t where gate = AND
(i.e., audio-path activation × text-path activation / total active features)
"""

import numpy as np

np.random.seed(127)

# ─── Parameters ───────────────────────────────────────────────────────────────
N_TOKENS = 200          # total tokens simulated
N_FEATURES = 256        # number of attention features per token
STRESSED_FRAC = 0.30    # ~30% of syllables are stressed (English average)
THRESHOLD = 0.35        # activation threshold for AND/OR classification

# ─── Simulate token types ─────────────────────────────────────────────────────
is_stressed = np.random.binomial(1, STRESSED_FRAC, N_TOKENS).astype(bool)
n_stressed   = is_stressed.sum()
n_unstressed = (~is_stressed).sum()

# ─── Simulate feature activations ─────────────────────────────────────────────
# Each feature has an audio path activation and a text path activation.
# AND-gate: both audio_act > threshold AND text_act > threshold
# OR-gate:  at least one > threshold but NOT both (text-predictable or audio-only)

def simulate_and_frac(n_tokens, audio_mu, audio_sigma, text_mu, text_sigma, n_features, threshold):
    """
    For each token, sample audio + text activations per feature.
    Compute and_frac = fraction of features that are AND-gated.
    """
    and_fracs = []
    for _ in range(n_tokens):
        audio_act = np.random.normal(audio_mu, audio_sigma, n_features).clip(0, 1)
        text_act  = np.random.normal(text_mu,  text_sigma,  n_features).clip(0, 1)

        is_and = (audio_act > threshold) & (text_act > threshold)
        is_active = (audio_act > threshold) | (text_act > threshold)

        and_frac = is_and.sum() / max(is_active.sum(), 1)
        and_fracs.append(and_frac)
    return np.array(and_fracs)

# ─── Stressed: high audio activation (unique acoustic signature)
# Text activation also moderate (the word is still predictable to some degree)
stressed_and_fracs = simulate_and_frac(
    n_stressed,
    audio_mu=0.65, audio_sigma=0.12,   # strong audio signal
    text_mu=0.50,  text_sigma=0.15,    # moderate text prior
    n_features=N_FEATURES,
    threshold=THRESHOLD,
)

# ─── Unstressed: low audio activation (reduced vowel, coarticulation)
# High text activation (function words, predictable phonemes)
unstressed_and_fracs = simulate_and_frac(
    n_unstressed,
    audio_mu=0.38, audio_sigma=0.12,   # weak audio signal (reduced vowel)
    text_mu=0.65,  text_sigma=0.12,    # strong text prior
    n_features=N_FEATURES,
    threshold=THRESHOLD,
)

# ─── Results ──────────────────────────────────────────────────────────────────
stressed_mean   = stressed_and_fracs.mean()
stressed_std    = stressed_and_fracs.std()
unstressed_mean = unstressed_and_fracs.mean()
unstressed_std  = unstressed_and_fracs.std()
delta           = stressed_mean - unstressed_mean
ratio           = stressed_mean / unstressed_mean if unstressed_mean > 0 else float("inf")

print("=" * 56)
print("Q127: Stressed Syllable × AND/OR Gate — Mock Results")
print("=" * 56)
print(f"  Tokens simulated : {N_TOKENS} ({n_stressed} stressed, {n_unstressed} unstressed)")
print(f"  Features/token   : {N_FEATURES}")
print(f"  Threshold        : {THRESHOLD}")
print()
print(f"  AND-frac (stressed)   : {stressed_mean:.3f} ± {stressed_std:.3f}")
print(f"  AND-frac (unstressed) : {unstressed_mean:.3f} ± {unstressed_std:.3f}")
print(f"  Δ (stressed - unstressed): {delta:+.3f}")
print(f"  Ratio (stressed/unstressed): {ratio:.2f}×")
print()

# ─── Hypothesis test (Welch's t-test proxy via z-score) ─────────────────────
pooled_se = np.sqrt(stressed_std**2 / n_stressed + unstressed_std**2 / n_unstressed)
z = delta / pooled_se if pooled_se > 0 else 0.0

print(f"  Z-score (stressed > unstressed): {z:.2f}")
if z > 3.0:
    verdict = "STRONG SUPPORT ✅ (z > 3)"
elif z > 2.0:
    verdict = "MODERATE SUPPORT ✅ (z > 2)"
elif z > 1.0:
    verdict = "WEAK SUPPORT ⚠️  (z > 1)"
else:
    verdict = "NOT SUPPORTED ❌"

print(f"  Verdict: {verdict}")
print()
print("─" * 56)
print("Interpretation:")
print(f"  Stressed syllables AND-frac = {stressed_mean:.3f}: both audio+text")
print(f"  paths active → model must commit to acoustic detail.")
print(f"  Unstressed AND-frac = {unstressed_mean:.3f}: dominated by OR-gate")
print(f"  (text prior sufficient; audio path deprioritized).")
print()
print("Prediction for real Whisper cross-attention:")
print(f"  Expect Δ ≈ {delta:.2f}–{delta*1.2:.2f} in actual head activations.")
print(f"  Testable: extract attention × value norms per token,")
print(f"  split by forced-aligner stress labels (e.g. CMU-Pronouncing).")
print("=" * 56)
