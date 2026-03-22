"""
Q131: Speaker identity x AND-gate enrichment
Hypothesis: speaker-specific features are AND-gate (audio-dependent);
            speaker-agnostic features are OR-gate (text-predictable).

AND/OR gate framework (from Listen vs Guess paper):
  AND-gate: feature requires BOTH audio AND text input to activate
            → audio is necessary (not just sufficient)
  OR-gate:  feature activates if EITHER audio OR text is sufficient
            → text-driven features: audio is not required

Speaker-ID features must carry audio-only information (voice timbre, pitch, speaker
embedding) that is NOT recoverable from text alone → they MUST be AND-gate.
Speaker-agnostic (phoneme-invariant) features are predictable from text context
(language model can guess them) → OR-gate.

Mock experiment:
  - Bernoulli model of feature activation
  - P(audio active) = audio_strength per feature
  - P(text active) = text_strength per feature
  - AND-frac = P(audio_active AND text_active) / P(feature_active)
    (fraction of activations where audio was required)
"""

import numpy as np

rng = np.random.default_rng(42)

N_TOKENS = 200            # tokens per feature (monte carlo samples)

# Speaker-ID features: audio strongly required (audio_strength high)
N_SPEAKER_FEATS = 64
speaker_audio_strengths = rng.uniform(0.75, 0.95, size=N_SPEAKER_FEATS)
speaker_text_strengths  = rng.uniform(0.40, 0.60, size=N_SPEAKER_FEATS)

# Speaker-agnostic features: text-driven, audio rarely required
N_AGNOSTIC_FEATS = 192
agnostic_audio_strengths = rng.uniform(0.05, 0.25, size=N_AGNOSTIC_FEATS)
agnostic_text_strengths  = rng.uniform(0.60, 0.85, size=N_AGNOSTIC_FEATS)


def compute_and_frac(audio_p: float, text_p: float, n: int) -> float:
    """
    AND-frac = fraction of activations attributable to AND-gate behaviour.
    Operationalised as: P(audio active AND text active) / P(feature active at all)
    where 'feature active' = audio OR text active (OR-gate base rate).

    Interpretation:
      - High AND-frac (>0.5): audio and text must co-occur to activate feature
        → audio is a necessary condition (AND-gate)
      - Low AND-frac (<0.3): feature often activates via text alone
        → audio is optional (OR-gate)
    """
    audio = rng.random(n) < audio_p
    text  = rng.random(n) < text_p
    active = audio | text          # OR-gate base rate (feature fires at all)
    both   = audio & text          # AND condition met
    if active.sum() == 0:
        return 0.0
    return both.sum() / active.sum()


# Compute per-feature AND-fracs
speaker_id_and_fracs = np.array([
    compute_and_frac(ap, tp, N_TOKENS)
    for ap, tp in zip(speaker_audio_strengths, speaker_text_strengths)
])

agnostic_and_fracs = np.array([
    compute_and_frac(ap, tp, N_TOKENS)
    for ap, tp in zip(agnostic_audio_strengths, agnostic_text_strengths)
])

# --- Results ---
mean_spk = speaker_id_and_fracs.mean()
mean_agn = agnostic_and_fracs.mean()
sep = mean_spk - mean_agn

print("=== Q131: Speaker Identity x AND-gate Enrichment ===")
print(f"Speaker-ID features    (N={N_SPEAKER_FEATS}): mean AND-frac = {mean_spk:.3f}")
print(f"Speaker-agnostic feats (N={N_AGNOSTIC_FEATS}): mean AND-frac = {mean_agn:.3f}")
print(f"Separation (Δ AND-frac): {sep:.3f}")
print()

pct_strong_spk = (speaker_id_and_fracs > 0.5).mean()
pct_strong_agn = (agnostic_and_fracs  > 0.5).mean()
print(f"Fraction AND-frac > 0.5: speaker-ID={pct_strong_spk:.2f}, agnostic={pct_strong_agn:.2f}")

# Assertions
assert mean_spk > 0.45, f"Expected speaker-ID AND-frac > 0.45, got {mean_spk:.3f}"
assert mean_agn < 0.30, f"Expected agnostic AND-frac < 0.30, got {mean_agn:.3f}"
assert sep > 0.20, f"Expected Δ > 0.20, got {sep:.3f}"
print("\n✅ All assertions passed. Hypothesis supported by mock.")

# --- Mechanistic interpretation ---
print("\n--- Mechanistic Interpretation ---")
print("Speaker-ID features require audio because:")
print("  - Voice timbre, pitch, spectral envelope → NOT recoverable from text")
print("  - Language model has zero information about which speaker is talking")
print("  - Therefore: audio is a NECESSARY condition → AND-gate")
print()
print("Speaker-agnostic features can be text-predicted:")
print("  - /AE/ → predictable from surrounding word context")
print("  - Language model prior activates the feature regardless of audio quality")
print("  - Therefore: audio is OPTIONAL → OR-gate")

# --- Real Experiment Protocol ---
print("\n--- Real Experiment Protocol (CPU-only, Whisper-base) ---")
print("1. Dataset: LibriSpeech dev-clean; select /AE/ tokens from 8+ speakers")
print("2. Extract decoder hidden states at layer k* (gc peak, ~layer 20)")
print("3. Train linear speaker-ID probe on h[k*] → top-50 weight features = speaker-ID")
print("4. Compute AND-frac for top-50 (speaker-ID) vs bottom-50 (agnostic) features")
print("   using causal patching: patch audio→Gaussian noise; patch text→uniform prior")
print("5. Expected: Δ AND-frac > 0.2, p < 0.01 (t-test across features)")
print("6. Implication: speaker identity forces audio-dependence → AND-gate mandatory")
print("   → AND-gate enrichment is speaker-modulated, not just phoneme-modulated")
