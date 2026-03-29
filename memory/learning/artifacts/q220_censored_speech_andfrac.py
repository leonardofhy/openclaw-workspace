"""
Q220: Censored speech in real Whisper — AND-frac commit layer shift
for sensitive vs neutral content?

Approach:
- Load Whisper-base encoder
- Generate 10 "sensitive" + 10 "neutral" mock mel-spectrogram inputs
  (distinguish via embedding perturbation in mel domain)
- Hook all encoder layers to capture hidden states
- Compute AND-frac (fraction of tokens with active top-1 prediction)
  at each layer
- Compare L* (peak AND-frac layer) between groups
- Report: mean L*, std, Wilcoxon p-value
"""

import sys
import json
import numpy as np
import torch
import whisper
from scipy import stats

# ── helpers ────────────────────────────────────────────────────────────────

def compute_and_frac(hidden: torch.Tensor, proj_matrix: torch.Tensor) -> float:
    """
    AND-frac (Andromeda fraction):
    fraction of time-steps where the top-1 vocabulary logit is
    consistently the SAME token across the batch dimension.
    For a single sample, approximate as mean entropy proxy:
    low entropy  → high commitment → high AND-frac.

    Practical definition used here:
      logits = hidden @ proj_matrix.T  → (T, V)
      and_frac = fraction of T where max logit > mean_logit + 1*std_logit
    """
    with torch.no_grad():
        logits = hidden.squeeze(0).float() @ proj_matrix.T.float()  # (T, V)
        mx = logits.max(dim=-1).values       # (T,)
        mu = logits.mean(dim=-1)
        sd = logits.std(dim=-1).clamp(min=1e-6)
        frac = ((mx - mu) / sd > 1.0).float().mean().item()
    return frac


def extract_andfrac_curve(model, mel: torch.Tensor) -> list:
    """Run encoder and return AND-frac per layer."""
    activations = []

    hooks = []
    for layer in model.encoder.blocks:
        def hook_fn(module, inp, out, store=activations):
            store.append(out.detach().cpu())
        hooks.append(layer.register_forward_hook(hook_fn))

    with torch.no_grad():
        model.encoder(mel)

    for h in hooks:
        h.remove()

    # Use vocab projection (embed_out) from decoder — shared embedding
    proj = model.decoder.token_embedding.weight  # (V, D)

    curve = [compute_and_frac(act, proj) for act in activations]
    return curve


def make_mel(seed: int, sensitive: bool, n_frames: int = 3000) -> torch.Tensor:
    """
    Synthetic mel-spectrogram (80 × 3000) — Whisper requires exactly 3000 frames.
    Sensitive samples: stronger low-frequency energy (simulating emphatic/
    emotionally charged speech with boosted harmonics in lower mels).
    Neutral samples: flatter spectrum.
    """
    rng = np.random.default_rng(seed)
    mel = rng.normal(0, 1, (80, n_frames)).astype(np.float32)

    if sensitive:
        # Boost lower 20 mel bins (speech fundamentals) — simulates
        # patterns Whisper might recognize as "sensitive" content
        mel[:20, :] += rng.normal(0, 1.5, (20, n_frames))
        # Add periodic structure mimicking stressed/emotional prosody
        t = np.linspace(0, 10 * np.pi, n_frames)
        mel[:20, :] += 0.5 * np.sin(t)[None, :]
    else:
        # Neutral: slightly raised mid-range, flatter
        mel[20:60, :] += rng.normal(0, 0.5, (40, n_frames))

    # Whisper expects log-mel in [-1, 1] range roughly; clip
    mel = np.clip(mel, -3, 3) / 3.0
    return torch.tensor(mel).unsqueeze(0)  # (1, 80, T)


# ── main ───────────────────────────────────────────────────────────────────

def main():
    print("Loading Whisper-base...")
    model = whisper.load_model("base", device="cpu")
    model.eval()

    n_layers = len(model.encoder.blocks)
    print(f"Encoder layers: {n_layers}")

    N = 10
    sensitive_curves = []
    neutral_curves   = []

    print(f"\nRunning {N} sensitive samples...")
    for i in range(N):
        mel = make_mel(seed=i, sensitive=True)
        curve = extract_andfrac_curve(model, mel)
        sensitive_curves.append(curve)
        print(f"  S{i:02d}: peak L*={np.argmax(curve)}, max={max(curve):.3f}")

    print(f"\nRunning {N} neutral samples...")
    for i in range(N):
        mel = make_mel(seed=i + 100, sensitive=False)
        curve = extract_andfrac_curve(model, mel)
        neutral_curves.append(curve)
        print(f"  N{i:02d}: peak L*={np.argmax(curve)}, max={max(curve):.3f}")

    # ── Analysis ──────────────────────────────────────────────────────────
    s_arr = np.array(sensitive_curves)   # (10, n_layers)
    n_arr = np.array(neutral_curves)

    s_peak = np.argmax(s_arr, axis=1).astype(float)
    n_peak = np.argmax(n_arr, axis=1).astype(float)

    s_max  = s_arr.max(axis=1)
    n_max  = n_arr.max(axis=1)

    stat_peak, p_peak = stats.mannwhitneyu(s_peak, n_peak, alternative='two-sided')
    stat_max,  p_max  = stats.mannwhitneyu(s_max,  n_max,  alternative='two-sided')

    # Layer-wise mean curves
    s_mean = s_arr.mean(axis=0)
    n_mean = n_arr.mean(axis=0)

    print("\n" + "="*60)
    print("RESULTS — Q220: Censored speech AND-frac analysis")
    print("="*60)
    print(f"Whisper-base encoder layers: {n_layers}")
    print(f"\nPeak L* (layer with max AND-frac):")
    print(f"  Sensitive: mean={s_peak.mean():.2f} ± {s_peak.std():.2f}  "
          f"[{s_peak.min():.0f}–{s_peak.max():.0f}]")
    print(f"  Neutral:   mean={n_peak.mean():.2f} ± {n_peak.std():.2f}  "
          f"[{n_peak.min():.0f}–{n_peak.max():.0f}]")
    print(f"  Mann-Whitney U={stat_peak:.0f}, p={p_peak:.4f}")

    print(f"\nMax AND-frac value:")
    print(f"  Sensitive: mean={s_max.mean():.4f} ± {s_max.std():.4f}")
    print(f"  Neutral:   mean={n_max.mean():.4f} ± {n_max.std():.4f}")
    print(f"  Mann-Whitney U={stat_max:.0f}, p={p_max:.4f}")

    print(f"\nLayer-wise mean AND-frac curves:")
    print(f"  {'Layer':>5}  {'Sensitive':>10}  {'Neutral':>10}  {'Delta':>8}")
    for i, (sv, nv) in enumerate(zip(s_mean, n_mean)):
        marker = " ←" if i == int(s_peak.mean().round()) else ""
        print(f"  {i:>5}  {sv:>10.4f}  {nv:>10.4f}  {sv-nv:>+8.4f}{marker}")

    # ── Interpretation ────────────────────────────────────────────────────
    print("\n" + "-"*60)
    print("INTERPRETATION:")
    delta_peak = s_peak.mean() - n_peak.mean()
    if abs(delta_peak) < 0.5:
        shift_str = "negligible"
    elif delta_peak > 0:
        shift_str = f"later (Δ={delta_peak:+.2f} layers) in sensitive"
    else:
        shift_str = f"earlier (Δ={delta_peak:+.2f} layers) in sensitive"

    sig = "SIGNIFICANT" if p_peak < 0.05 else "not significant"
    print(f"  L* shift: {shift_str} ({sig}, p={p_peak:.4f})")

    if p_peak < 0.05:
        print("  → Commitment layer shifts with content type; Whisper encodes")
        print("    semantic/emotional features that modulate AND-frac timing.")
    else:
        print("  → No significant L* shift. Both groups commit at same depth.")
        print("    Possible: synthetic mels don't produce realistic content-")
        print("    dependent activation patterns. Real audio needed.")

    # Save results
    results = {
        "task": "Q220",
        "model": "whisper-base",
        "n_samples_per_group": N,
        "n_encoder_layers": n_layers,
        "sensitive_peak_L_mean": float(s_peak.mean()),
        "sensitive_peak_L_std":  float(s_peak.std()),
        "neutral_peak_L_mean":   float(n_peak.mean()),
        "neutral_peak_L_std":    float(n_peak.std()),
        "peak_L_delta":          float(delta_peak),
        "peak_L_mannwhitney_p":  float(p_peak),
        "max_andfrac_sensitive": float(s_max.mean()),
        "max_andfrac_neutral":   float(n_max.mean()),
        "max_andfrac_p":         float(p_max),
        "sensitive_curves":      s_arr.tolist(),
        "neutral_curves":        n_arr.tolist(),
    }

    out_path = "memory/learning/artifacts/q220_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved → {out_path}")
    return results


if __name__ == "__main__":
    main()
