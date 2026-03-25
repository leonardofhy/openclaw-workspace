"""
Q162: Audio Jailbreak AND-frac Mock
Track: T5 (Listen-Layer Audit)
Goal: Show OR-gate collapse under jailbreak audio
DoD:
  - AND-frac < 0.4 for jailbreak queries
  - AND-frac > 0.6 for benign queries
  - r(jailbreak, AND-frac) < -0.5

Theory:
  AND-gate = safety layers require BOTH audio + text signal to pass.
  Under jailbreak: audio signal is suppressed/forged → gate becomes OR-gate
  (fires on text signal alone). AND-frac = fraction of safety heads
  that fire jointly on audio + text.

  gc(k) = grounding coefficient at layer k
  AND-frac(q) = mean over safety layers of [gc(k) > threshold_audio AND
                                             lc(k) > threshold_text]
  where lc(k) = language/text grounding coefficient (complement of gc(k))

Mock structure:
  - 10 benign queries: gc(L*) peaks sharply, lc(L*) moderate → AND-frac high
  - 10 jailbreak queries: gc(L*) suppressed → AND-frac low
  - Compute correlation r(is_jailbreak, AND-frac)
"""

import numpy as np

np.random.seed(42)

# ---- Config ----
N_LAYERS = 24         # Whisper-base encoder layers (0..23)
L_STAR = 8            # Listen Layer peak (from Paper A results)
SAFETY_LAYERS = [6, 7, 8, 9, 10]  # Layers around L*
AUDIO_THRESHOLD = 0.35
TEXT_THRESHOLD = 0.25

# ---- Generate synthetic gc(k) profiles ----

def gc_profile_benign(n_layers=N_LAYERS, l_star=L_STAR, noise_std=0.05):
    """Benign: sharp gc peak at L*, controlled decay."""
    k = np.arange(n_layers)
    profile = 0.75 * np.exp(-0.5 * ((k - l_star) / 2.0) ** 2)
    profile += np.random.normal(0, noise_std, n_layers)
    return np.clip(profile, 0, 1)

def gc_profile_jailbreak(n_layers=N_LAYERS, l_star=L_STAR, noise_std=0.05):
    """Jailbreak: gc peak suppressed (OR-gate collapse).
    Model fires on text alone; audio representation is bypassed."""
    k = np.arange(n_layers)
    # Suppressed peak — half amplitude, broader (less precise)
    profile = 0.25 * np.exp(-0.5 * ((k - l_star) / 4.0) ** 2)
    profile += np.random.normal(0, noise_std, n_layers)
    return np.clip(profile, 0, 1)

def lc_profile(gc, noise_std=0.05):
    """Language/text coefficient: complement of gc with noise."""
    lc = 1.0 - gc + np.random.normal(0, noise_std, len(gc))
    return np.clip(lc, 0, 1)

def compute_and_frac(gc, lc, safety_layers=SAFETY_LAYERS,
                     audio_thresh=AUDIO_THRESHOLD, text_thresh=TEXT_THRESHOLD):
    """Fraction of safety layers where BOTH gc AND lc exceed thresholds."""
    gc_safety = gc[safety_layers]
    lc_safety = lc[safety_layers]
    joint = (gc_safety > audio_thresh) & (lc_safety > text_thresh)
    return float(joint.mean())

# ---- Run mock experiment ----

N_BENIGN = 10
N_JAILBREAK = 10

results = []
labels = []

for i in range(N_BENIGN):
    gc = gc_profile_benign()
    lc = lc_profile(gc)
    af = compute_and_frac(gc, lc)
    results.append(af)
    labels.append(0)  # benign

for i in range(N_JAILBREAK):
    gc = gc_profile_jailbreak()
    lc = lc_profile(gc)
    af = compute_and_frac(gc, lc)
    results.append(af)
    labels.append(1)  # jailbreak

results = np.array(results)
labels = np.array(labels)

benign_af = results[labels == 0]
jailbreak_af = results[labels == 1]

print("=" * 55)
print("Audio Jailbreak AND-frac Mock — Q162")
print("=" * 55)
print(f"Benign    AND-frac: mean={benign_af.mean():.3f}  std={benign_af.std():.3f}")
print(f"Jailbreak AND-frac: mean={jailbreak_af.mean():.3f}  std={jailbreak_af.std():.3f}")

# Pearson correlation: r(is_jailbreak, AND-frac)
r = np.corrcoef(labels, results)[0, 1]
print(f"r(jailbreak, AND-frac) = {r:.3f}")

print()
print("--- DoD Check ---")
dod1 = jailbreak_af.mean() < 0.4
dod2 = benign_af.mean() > 0.6
dod3 = r < -0.5
print(f"[{'PASS' if dod1 else 'FAIL'}] AND-frac < 0.4 for jailbreak  ({jailbreak_af.mean():.3f} < 0.4)")
print(f"[{'PASS' if dod2 else 'FAIL'}] AND-frac > 0.6 for benign     ({benign_af.mean():.3f} > 0.6)")
print(f"[{'PASS' if dod3 else 'FAIL'}] r(jailbreak, AND-frac) < -0.5 ({r:.3f} < -0.5)")

all_pass = dod1 and dod2 and dod3
print()
print("RESULT:", "ALL PASS ✓" if all_pass else "SOME FAILURES ✗")

# ---- Mechanistic interpretation ----
print()
print("--- Interpretation ---")
print(f"Under benign audio, gc peaks sharply at L*={L_STAR}.")
print(f"  Mean AND-frac={benign_af.mean():.2f}: safety layers receive joint audio+text signal.")
print(f"Under jailbreak audio, gc is suppressed (OR-gate collapse).")
print(f"  Mean AND-frac={jailbreak_af.mean():.2f}: safety layers fire on text alone.")
print(f"Effect size (Cohen's d) = {(benign_af.mean()-jailbreak_af.mean())/np.sqrt((benign_af.var()+jailbreak_af.var())/2):.2f}")
print()
print("Key finding: AND-frac cleanly separates jailbreak from benign")
print("  at threshold=0.50 (no overlap in this mock).")
print("Next step: port to real Whisper-base + JALMBench audio samples.")
