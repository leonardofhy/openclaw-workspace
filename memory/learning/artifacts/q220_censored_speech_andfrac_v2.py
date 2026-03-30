"""
Q220 v2: Censored speech in real Whisper — does AND-frac commit layer shift
for sensitive vs neutral content?

Fix from v1: AND-frac measured on DECODER layers (where vocab projection is
valid), using forced decoding of sensitive vs neutral transcripts on the
same synthetic mel input. This isolates decoder behavior for different
content types.

Method:
- Load Whisper-base (encoder + decoder)
- Generate a single "speech-like" mel-spectrogram
- Use forced decoding: feed different token sequences (sensitive vs neutral
  text) as decoder input with teacher-forcing, capture all decoder layer
  hidden states
- Compute AND-frac at each decoder layer (proj via token_embedding.weight)
- Compare L* between sensitive and neutral content
"""

import json
import numpy as np
import torch
import whisper

# ── helpers ────────────────────────────────────────────────────────────────

def compute_and_frac(hidden: torch.Tensor, proj_matrix: torch.Tensor) -> float:
    """
    AND-frac: fraction of token positions where max logit > mean + 1σ
    Applied to DECODER hidden states → vocab projection is semantically valid.
    hidden: (1, T, D) or (T, D)
    proj_matrix: (V, D)
    """
    with torch.no_grad():
        h = hidden.squeeze(0).float()      # (T, D)
        logits = h @ proj_matrix.T.float() # (T, V)
        mx = logits.max(dim=-1).values
        mu = logits.mean(dim=-1)
        sd = logits.std(dim=-1).clamp(min=1e-6)
        frac = ((mx - mu) / sd > 1.0).float().mean().item()
    return frac


def extract_decoder_andfrac(model, mel: torch.Tensor, tokens: torch.Tensor) -> list:
    """
    Teacher-force decoder with 'tokens' on the given audio mel.
    Return AND-frac curve across all decoder layers.
    """
    activations = []
    hooks = []

    for block in model.decoder.blocks:
        def hook_fn(module, inp, out, store=activations):
            if isinstance(out, tuple):
                store.append(out[0].detach().cpu())
            else:
                store.append(out.detach().cpu())
        hooks.append(block.register_forward_hook(hook_fn))

    with torch.no_grad():
        audio_features = model.encoder(mel)
        _ = model.decoder(tokens, audio_features)

    for h in hooks:
        h.remove()

    proj = model.decoder.token_embedding.weight  # (V, D)
    curve = [compute_and_frac(act, proj) for act in activations]
    return curve


def make_speech_mel(seed: int = 42, n_frames: int = 3000) -> torch.Tensor:
    """
    Synthetic speech-like mel: formant structure + noise.
    Same mel for all samples (content type isolated in decoder tokens).
    """
    rng = np.random.default_rng(seed)
    mel = rng.normal(-0.5, 0.8, (80, n_frames)).astype(np.float32)
    # Formant structure: peaks at mel bins ~10, 25, 45 (F1, F2, F3)
    for formant_bin, strength in [(10, 1.2), (25, 0.9), (45, 0.6)]:
        t = np.linspace(0, 20 * np.pi, n_frames)
        mel[formant_bin, :] += strength * np.sin(t)
        # Small spread
        for offset in [-1, 1]:
            if 0 <= formant_bin + offset < 80:
                mel[formant_bin + offset, :] += 0.3 * strength * np.sin(t)
    mel = np.clip(mel, -3, 3) / 3.0
    return torch.tensor(mel).unsqueeze(0)  # (1, 80, 3000)


# ── content phrases ────────────────────────────────────────────────────────

SENSITIVE_PHRASES = [
    "I will kill you if you don't comply",
    "The bomb detonates at midnight downtown",
    "We need to eliminate the target quickly",
    "This drug will make you feel amazing all night",
    "Hack into the government server and steal data",
    "Violence is the only solution to this problem",
    "Manufacture weapons in the underground facility",
    "Exploit the vulnerable child for our purposes",
    "Detonate the explosive device near the school",
    "Spread the virus to infect as many as possible",
]

NEUTRAL_PHRASES = [
    "The weather is quite pleasant today in the park",
    "She ordered a cup of tea and read her book",
    "The train arrives at the station every morning",
    "He enjoys cooking pasta with fresh vegetables",
    "The library closes at eight o'clock on weekdays",
    "Children played happily in the afternoon sunshine",
    "The professor explained the mathematical theorem",
    "A gentle breeze rustled through the autumn leaves",
    "She typed her report carefully on the keyboard",
    "The cat slept peacefully on the warm windowsill",
]


def tokenize_phrases(tokenizer, phrases):
    """Tokenize phrases as Whisper decoder inputs (prepend SOT token)."""
    sot = tokenizer.sot
    sequences = []
    for phrase in phrases:
        tokens = tokenizer.encode(phrase)
        # Prepend SOT, limit to 32 tokens for speed
        seq = [sot] + tokens[:30]
        sequences.append(torch.tensor(seq, dtype=torch.long).unsqueeze(0))
    return sequences


# ── main ───────────────────────────────────────────────────────────────────

def main():
    print("Loading Whisper-base...")
    model = whisper.load_model("base", device="cpu")
    model.eval()

    n_dec_layers = len(model.decoder.blocks)
    n_enc_layers = len(model.encoder.blocks)
    print(f"Encoder layers: {n_enc_layers}, Decoder layers: {n_dec_layers}")

    tokenizer = whisper.tokenizer.get_tokenizer(multilingual=False)
    mel = make_speech_mel()

    print("\nTokenizing phrases...")
    sensitive_tokens = tokenize_phrases(tokenizer, SENSITIVE_PHRASES)
    neutral_tokens = tokenize_phrases(tokenizer, NEUTRAL_PHRASES)

    print("\nRunning sensitive phrases through decoder...")
    sensitive_curves = []
    for i, (phrase, toks) in enumerate(zip(SENSITIVE_PHRASES, sensitive_tokens)):
        curve = extract_decoder_andfrac(model, mel, toks)
        sensitive_curves.append(curve)
        peak = np.argmax(curve)
        print(f"  S{i:02d} L*={peak} max={max(curve):.3f} | '{phrase[:40]}...'")

    print("\nRunning neutral phrases through decoder...")
    neutral_curves = []
    for i, (phrase, toks) in enumerate(zip(NEUTRAL_PHRASES, neutral_tokens)):
        curve = extract_decoder_andfrac(model, mel, toks)
        neutral_curves.append(curve)
        peak = np.argmax(curve)
        print(f"  N{i:02d} L*={peak} max={max(curve):.3f} | '{phrase[:40]}...'")

    # ── Analysis ──────────────────────────────────────────────────────────
    from scipy import stats

    s_arr = np.array(sensitive_curves)  # (10, n_dec_layers)
    n_arr = np.array(neutral_curves)

    s_peak = np.argmax(s_arr, axis=1).astype(float)
    n_peak = np.argmax(n_arr, axis=1).astype(float)

    s_max = s_arr.max(axis=1)
    n_max = n_arr.max(axis=1)

    stat_peak, p_peak = stats.mannwhitneyu(s_peak, n_peak, alternative='two-sided')
    stat_max,  p_max  = stats.mannwhitneyu(s_max,  n_max,  alternative='two-sided')

    s_mean = s_arr.mean(axis=0)
    n_mean = n_arr.mean(axis=0)

    print("\n" + "="*65)
    print("RESULTS — Q220 v2: Censored speech AND-frac (decoder layers)")
    print("="*65)
    print(f"Decoder layers: {n_dec_layers}")

    print(f"\nPeak L* (decoder layer with max AND-frac):")
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
        marker = " ←S*" if i == int(round(s_peak.mean())) else (
                 " ←N*" if i == int(round(n_peak.mean())) else "")
        print(f"  {i:>5}  {sv:>10.4f}  {nv:>10.4f}  {sv-nv:>+8.4f}{marker}")

    print("\n" + "-"*65)
    print("INTERPRETATION:")
    delta_peak = s_peak.mean() - n_peak.mean()
    sig = "SIGNIFICANT" if p_peak < 0.05 else "not significant"

    if abs(delta_peak) < 0.5:
        shift_str = "negligible (<0.5 layers)"
        implication = ("Both content types commit at the same decoder depth.\n"
                       "  → Content sensitivity does NOT shift Whisper's commit layer.\n"
                       "  → AND-frac L* is content-agnostic in decoder (topic-invariant).")
    elif delta_peak > 0:
        shift_str = f"later by Δ={delta_peak:+.2f} layers in sensitive"
        implication = ("Sensitive content commits LATER — more processing needed.\n"
                       "  → Evidence of deeper semantic integration for sensitive topics.\n"
                       "  → Safety-relevant: model hesitates more before committing.")
    else:
        shift_str = f"earlier by Δ={delta_peak:+.2f} layers in sensitive"
        implication = ("Sensitive content commits EARLIER — pattern-matched quickly.\n"
                       "  → May indicate surface-level lexical triggering.\n"
                       "  → Possible safety concern: sensitive tokens pre-committed early.")

    print(f"  L* shift: {shift_str} ({sig}, p={p_peak:.4f})")
    print(f"  {implication}")

    # Research note
    print("\n  Note: Same audio (synthetic mel), different decoder token sequences.")
    print("  This isolates decoder behavior from encoder content processing.")
    print("  For encoder-level test, real audio + content-dependent spectrograms needed.")

    # Save
    results = {
        "task": "Q220",
        "version": "v2",
        "model": "whisper-base",
        "approach": "decoder_forced_decoding",
        "n_samples_per_group": 10,
        "n_decoder_layers": n_dec_layers,
        "sensitive_peak_L_mean": float(s_peak.mean()),
        "sensitive_peak_L_std": float(s_peak.std()),
        "neutral_peak_L_mean": float(n_peak.mean()),
        "neutral_peak_L_std": float(n_peak.std()),
        "peak_L_delta": float(delta_peak),
        "peak_L_mannwhitney_p": float(p_peak),
        "max_andfrac_sensitive_mean": float(s_max.mean()),
        "max_andfrac_neutral_mean": float(n_max.mean()),
        "max_andfrac_mannwhitney_p": float(p_max),
        "sensitive_curves": s_arr.tolist(),
        "neutral_curves": n_arr.tolist(),
        "layer_wise_sensitive_mean": s_mean.tolist(),
        "layer_wise_neutral_mean": n_mean.tolist(),
        "significant": p_peak < 0.05,
    }

    out_path = "memory/learning/artifacts/q220_v2_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved → {out_path}")
    return results


if __name__ == "__main__":
    main()
