"""
attn_entropy_gate_mock.py
=========================
Q150: Attention entropy × AND-gate — identify commitment heads.

Hypothesis: "Commitment heads" are attention heads that:
  (1) have LOW entropy (attend sharply to specific positions)
  (2) correlate with high AND-frac at gc(k) peak

These heads are evidence that Whisper is LISTENING (audio-grounded),
not just guessing from language priors.

Mock setup:
  - N_HEADS = 12 (Whisper-base encoder, last layer)
  - T = 50 audio frames
  - For each of K audio samples, generate mock:
      * per-head entropy: H(head) = -sum(p * log(p)) over attended positions
      * AND-frac at gc_peak for that sample
  - Compute Pearson r(H, AND-frac) per head
  - Commitment heads = r < -0.6 (low entropy → high AND-frac)

Expected: top-3 commitment heads with r < -0.6.
"""

import numpy as np

def pearsonr(x, y):
    """Pure numpy Pearson correlation."""
    x, y = np.array(x), np.array(y)
    xm, ym = x - x.mean(), y - y.mean()
    r = np.dot(xm, ym) / (np.sqrt(np.dot(xm, xm)) * np.sqrt(np.dot(ym, ym)) + 1e-12)
    # approximate p-value via t-distribution
    n = len(x)
    t = r * np.sqrt((n - 2) / (1 - r**2 + 1e-12))
    # very rough p-value (two-tailed) — just for display
    p = 2 * np.exp(-0.717 * abs(t) - 0.416 * t**2)  # Abramowitz approximation
    return float(r), float(np.clip(p, 1e-12, 1.0))

np.random.seed(42)

N_HEADS = 12
N_SAMPLES = 80
T = 50  # attention positions

# --- Generate mock data ---
# Each head has a "true" commitment level C in [0, 1]
# C = 1 → very commitment (low entropy, high AND-frac)
# C = 0 → language-prior head (high entropy, low AND-frac)

np.random.seed(42)
# True commitment scores per head (some committed, most not)
true_commitment = np.array([
    0.85, 0.78, 0.12, 0.09, 0.72, 0.15,
    0.08, 0.81, 0.11, 0.14, 0.10, 0.77
])

entropies = np.zeros((N_SAMPLES, N_HEADS))
and_fracs = np.zeros((N_SAMPLES, N_HEADS))

# Key insight: each sample has a "grounding_signal" strength
# When grounding is strong → high-C heads show LOW entropy AND HIGH AND-frac
# (anti-correlation between entropy and AND-frac, but only for high-C heads)
grounding_signal = np.random.uniform(0.2, 1.0, N_SAMPLES)  # audio quality per sample

max_entropy = np.log(T)  # ~3.91 for T=50

for s in range(N_SAMPLES):
    g = grounding_signal[s]
    for h in range(N_HEADS):
        C = true_commitment[h]
        
        # Entropy: high-C head → entropy DECREASES with grounding signal
        # Low-C head → entropy unaffected by grounding (language prior head)
        base_entropy = max_entropy * (1.0 - 0.55 * C)  # committed heads are sharper on average
        grounding_effect = -C * 1.2 * (g - 0.6)        # grounding pulls entropy down for high-C
        noise_e = np.random.normal(0, 0.12)
        entropies[s, h] = np.clip(base_entropy + grounding_effect + noise_e, 0.3, max_entropy)
        
        # AND-frac: high-C head → AND-frac INCREASES with grounding signal
        base_and = 0.25 + 0.45 * C
        grounding_and = C * 0.35 * (g - 0.6)            # grounding boosts AND-frac for high-C
        noise_a = np.random.normal(0, 0.06)
        and_fracs[s, h] = np.clip(base_and + grounding_and + noise_a, 0.0, 1.0)

# --- Compute per-head Pearson r(entropy, AND-frac) ---
correlations = []
p_values = []
for h in range(N_HEADS):
    r, p = pearsonr(entropies[:, h], and_fracs[:, h])
    correlations.append(r)
    p_values.append(p)

correlations = np.array(correlations)
p_values = np.array(p_values)

# --- Identify commitment heads (r < -0.6) ---
commitment_mask = correlations < -0.6
commitment_heads = np.where(commitment_mask)[0]
# Sort by most negative r (strongest commitment signal)
commitment_heads_sorted = commitment_heads[np.argsort(correlations[commitment_heads])]

print("=" * 60)
print("Attention Entropy × AND-Gate Commitment Head Analysis")
print("=" * 60)
print(f"\nModel: Whisper-base encoder (mock), last layer")
print(f"Heads: {N_HEADS}, Samples: {N_SAMPLES}, Positions: {T}")
print()
print(f"{'Head':>5} | {'r(H, AND-frac)':>15} | {'p-value':>10} | {'Committed?':>10}")
print("-" * 50)
for h in range(N_HEADS):
    flag = "✓ YES" if correlations[h] < -0.6 else "  no"
    print(f"  H{h:02d} | {correlations[h]:>15.4f} | {p_values[h]:>10.4e} | {flag:>10}")

print()
print(f"Commitment heads (r < -0.6): {[f'H{h:02d}' for h in commitment_heads_sorted]}")
print()

if len(commitment_heads_sorted) >= 3:
    top3 = commitment_heads_sorted[:3]
    print("Top-3 commitment heads:")
    for rank, h in enumerate(top3, 1):
        print(f"  #{rank}: H{h:02d} | r = {correlations[h]:.4f} | p = {p_values[h]:.2e} "
              f"| avg_entropy = {entropies[:, h].mean():.3f} nats "
              f"| avg_AND-frac = {and_fracs[:, h].mean():.3f}")

print()
print("Interpretation:")
print("  Commitment heads attend sharply (low entropy) AND correlate")
print("  with high AND-frac at gc(k) peak → they are forcing audio-")
print("  grounded decisions, not falling back to language priors.")
print()

# --- Cross-head AND-frac agreement among commitment heads ---
if len(commitment_heads_sorted) >= 2:
    top_and = and_fracs[:, commitment_heads_sorted[:3]].mean(axis=1)
    other_heads = [h for h in range(N_HEADS) if h not in commitment_heads_sorted[:3]]
    other_and = and_fracs[:, other_heads].mean(axis=1)
    
    r_cross, p_cross = pearsonr(top_and, other_and)
    print(f"Cross-head AND-frac agreement (top-3 vs rest): r = {r_cross:.4f}, p = {p_cross:.2e}")
    print(f"  → Top-3 commitment heads are {'correlated with' if r_cross > 0.4 else 'somewhat independent from'}")
    print(f"     general AND-frac signal (suggests {'shared' if r_cross > 0.4 else 'specialized'} mechanism)")

print()

# --- Verification ---
print("=" * 60)
print("VERIFICATION")
print("=" * 60)
n_commitment = (correlations < -0.6).sum()
strongest_r = correlations.min()
print(f"  Commitment heads found: {n_commitment}")
print(f"  Strongest r: {strongest_r:.4f}")
print(f"  DoD 1 — ≥3 commitment heads: {'PASS ✓' if n_commitment >= 3 else 'FAIL ✗'}")
print(f"  DoD 2 — min r < -0.6: {'PASS ✓' if strongest_r < -0.6 else 'FAIL ✗'}")
all_pass = n_commitment >= 3 and strongest_r < -0.6
print(f"\n  Q150 STATUS: {'PASS ✓' if all_pass else 'FAIL ✗'}")
print()
print("Next: Q151 (Isolate(k) × beam diversity) or Q157 (AND-gate steerability mock)")
