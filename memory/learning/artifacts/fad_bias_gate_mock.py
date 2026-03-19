"""
Q096: FAD bias × AND/OR gate
Hypothesis: Text-predictable phonemes (low audio-dependence) → OR-gates.
            Audio-dependent phonemes (can't be guessed from context) → AND-gates.

FAD = Frequency/Acoustic/Distributional bias in ASR:
  - Text-predictable phonemes: e.g., "the", common function words, predictable suffixes
    → LM can guess even with degraded audio → OR-gate sufficient
  - Audio-dependent phonemes: e.g., minimal pairs, rare words, phonemically ambiguous
    → Must attend to actual audio → AND-gate needed

Mechanistic test: AND-gate fraction should INVERSELY correlate with text-predictability score.

Mock design:
  - 20 synthetic SAE features, each labeled with (phoneme_type, text_pred_score, gate_type)
  - text_pred_score in [0,1]: 1 = fully text-predictable, 0 = audio-dependent
  - gate_type: inferred from AND-fraction threshold (AND_frac > 0.6 → AND-gate)
  - Metric: Pearson r between text_pred_score and AND_frac should be < -0.7
"""

import random
import math

random.seed(42)

# ─── Mock data ───────────────────────────────────────────────────────────────
# Each feature: (feature_id, phoneme_type, text_pred_score, true_gate)
FEATURE_SPECS = [
    # High text-predictability → OR-gates
    ("F01", "schwa_function_word",   0.95, "OR"),
    ("F02", "word_final_s",          0.90, "OR"),
    ("F03", "common_stop_th",        0.85, "OR"),
    ("F04", "article_the",           0.92, "OR"),
    ("F05", "plural_suffix",         0.88, "OR"),
    ("F06", "common_vowel_e",        0.80, "OR"),
    ("F07", "function_word_to",      0.87, "OR"),
    ("F08", "high_freq_fricative",   0.75, "OR"),
    ("F09", "word_initial_w",        0.72, "OR"),
    ("F10", "predictable_nasal",     0.78, "OR"),
    # Low text-predictability → AND-gates
    ("F11", "minimal_pair_bid_bad",  0.15, "AND"),
    ("F12", "rare_phoneme_zh",       0.08, "AND"),
    ("F13", "vowel_minimal_pair",    0.12, "AND"),
    ("F14", "content_word_onset",    0.20, "AND"),
    ("F15", "fricative_voicing",     0.18, "AND"),
    ("F16", "stop_manner_dist",      0.10, "AND"),
    ("F17", "unexpected_stress",     0.05, "AND"),
    ("F18", "phoneme_in_noise",      0.10, "AND"),
    ("F19", "borrowing_phoneme",     0.22, "AND"),
    ("F20", "accent_variant",        0.25, "AND"),
]

def simulate_and_fraction(text_pred: float, true_gate: str, noise: float = 0.08) -> float:
    """
    Simulate AND-gate fraction based on text-predictability.
    AND-fraction ≈ (1 - text_pred) with noise + gate-type bias.
    OR-gates tend to have low AND-fraction even if text_pred is moderate.
    """
    base = 1.0 - text_pred
    if true_gate == "OR":
        base *= 0.6   # OR-gates suppress AND-fraction further
    else:
        base = 0.5 + base * 0.5  # AND-gates boost fraction
    jitter = random.gauss(0, noise)
    return max(0.0, min(1.0, base + jitter))

# ─── Run simulation ───────────────────────────────────────────────────────────
results = []
print("="*70)
print("Q096: FAD Bias × AND/OR Gate Mock Experiment")
print("="*70)
print(f"\n{'Feature':<6} {'Phoneme Type':<30} {'TextPred':>9} {'AND_frac':>9} {'Inferred':>9} {'True':>6}")
print("-"*70)

for fid, ptype, tp_score, true_gate in FEATURE_SPECS:
    and_frac = simulate_and_fraction(tp_score, true_gate)
    inferred = "AND" if and_frac > 0.55 else "OR"
    correct = "✓" if inferred == true_gate else "✗"
    results.append((fid, tp_score, and_frac, inferred, true_gate))
    print(f"{fid:<6} {ptype:<30} {tp_score:>9.2f} {and_frac:>9.3f} {inferred:>9} {correct:>6}")

# ─── Correlation ─────────────────────────────────────────────────────────────
tp_scores = [r[1] for r in results]
and_fracs = [r[2] for r in results]
n = len(results)
mean_tp = sum(tp_scores) / n
mean_af = sum(and_fracs) / n
cov = sum((x - mean_tp) * (y - mean_af) for x, y in zip(tp_scores, and_fracs)) / n
std_tp = math.sqrt(sum((x - mean_tp) ** 2 for x in tp_scores) / n)
std_af = math.sqrt(sum((y - mean_af) ** 2 for y in and_fracs) / n)
pearson_r = cov / (std_tp * std_af)

# Accuracy
correct_count = sum(1 for r in results if r[3] == r[4])
accuracy = correct_count / n

print("\n" + "="*70)
print("RESULTS SUMMARY")
print("="*70)
print(f"Pearson r (text_pred vs AND_frac): {pearson_r:+.3f}")
print(f"  → Expected: r < -0.70 (inverse correlation)")
print(f"  → {'PASS ✓' if pearson_r < -0.70 else 'FAIL ✗'}")
print(f"\nGate inference accuracy: {correct_count}/{n} = {accuracy:.1%}")
print(f"  → {'PASS ✓' if accuracy >= 0.85 else 'FAIL ✗'}")

# Group stats
or_features = [r for r in results if r[4] == "OR"]
and_features = [r for r in results if r[4] == "AND"]
or_and_frac_mean = sum(r[2] for r in or_features) / len(or_features)
and_and_frac_mean = sum(r[2] for r in and_features) / len(and_features)
print(f"\nGroup means:")
print(f"  OR-gate features:  mean AND_frac = {or_and_frac_mean:.3f}")
print(f"  AND-gate features: mean AND_frac = {and_and_frac_mean:.3f}")
print(f"  Delta:             {and_and_frac_mean - or_and_frac_mean:+.3f}")

print("\n" + "="*70)
print("MECHANISTIC INTERPRETATION")
print("="*70)
print("""
Claim: Text-predictable phonemes (high FAD bias) are processed via OR-gate
features — the model need not attend to audio if the language model prior
is strong enough. Audio-dependent phonemes (low FAD bias / minimal pairs)
require AND-gate features to correctly decode.

Implication for Paper A:
  - FAD bias = fraction of phonemes decoded via OR-gates at gc peak
  - gc(k) collapse ↔ AND-gate deactivation (Q093 validated)
  - Text-heavy contexts → higher OR-gate fraction → lower gc(k) → earlier collapse
  - Mechanistic test: measure AND_frac per phoneme × LM log-prob; plot binned mean
  - Prediction: AND_frac ∝ -log P_LM(phoneme | context)

Next steps:
  - Q107: Isolate curve as gc proxy → can use this for FAD bias phoneme ranking
  - Q123: FAD bias × RAVEL Cause/Isolate (complementary test)
  - Real validation: Whisper-base, compute LM log-probs for each phoneme token
""")

# ─── All PASS/FAIL summary ────────────────────────────────────────────────────
h1 = pearson_r < -0.70
h2 = accuracy >= 0.85
h3 = and_and_frac_mean - or_and_frac_mean > 0.25
print(f"Hypotheses:")
print(f"  H1 (r < -0.70):         {'PASS ✓' if h1 else 'FAIL ✗'}  (r = {pearson_r:.3f})")
print(f"  H2 (accuracy >= 85%):   {'PASS ✓' if h2 else 'FAIL ✗'}  ({accuracy:.0%})")
print(f"  H3 (delta AND_frac > 0.25): {'PASS ✓' if h3 else 'FAIL ✗'}  (delta = {and_and_frac_mean - or_and_frac_mean:.3f})")
all_pass = h1 and h2 and h3
print(f"\nOverall: {'ALL PASS ✓' if all_pass else 'SOME FAIL ✗'}")
