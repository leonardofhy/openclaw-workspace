"""
whisper_logit_lens.py
=====================
Logit-Lens projection for Whisper encoder.

Tests the "Triple Convergence Hypothesis":
  > Layers ~50% depth (base=3, large=6-7) are where Whisper's encoder
  > "crystallizes" from acoustic to semantic representations.
  > (AudioSAE transition zone, Beyond Transcription saturation layer,
  >  AudioLens critical layer all point to the same phenomenon.)

Method:
  1. Extract activations from each encoder layer
  2. Project through Whisper's ln_post + decoder embedding matrix (transposed)
  3. Decode top-k tokens at each layer → proxy for "semantic readiness"
  4. Compute Layer Information Score (LIS) = how much the layer's projection
     agrees with the final encoder output (CKA + cosine similarity)
  5. Find the "saturation layer" — first layer where LIS > threshold

This directly replicates the core metric in:
  - AudioLens (Layer-wise Information Score via vocab projection)
  - Beyond Transcription (Encoder Lens / saturation layer)

MacBook-feasible: Whisper-base, CPU-only, ~2GB RAM, ~30 sec.

Usage:
  python whisper_logit_lens.py [--audio path/to/audio.wav] [--no-plot] [--model base]

Requirements:
  pip install openai-whisper torch numpy matplotlib

References:
  - AudioLens (Ho et al., NTU, ASRU 2025): arXiv:2506.05140
  - Beyond Transcription (Glazer et al., 2025): arXiv:2508.15882
  - AudioSAE (Aparin et al., EACL 2026): arXiv:2602.05027
"""

import argparse
import sys
import numpy as np


# ─────────────────────────────────────────────
# Args
# ─────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(description="Whisper Logit-Lens — Triple Convergence Test")
    parser.add_argument("--audio", type=str, default=None,
                        help="Path to audio file (WAV/MP3). Uses synthetic sine wave if omitted.")
    parser.add_argument("--model", type=str, default="base",
                        choices=["tiny", "base", "small"],
                        help="Whisper model size (default: base)")
    parser.add_argument("--no-plot", action="store_true",
                        help="Skip matplotlib plots")
    parser.add_argument("--topk", type=int, default=5,
                        help="Top-k tokens to show per layer (default: 5)")
    parser.add_argument("--lis-threshold", type=float, default=0.8,
                        help="LIS threshold to declare saturation (default: 0.8)")
    parser.add_argument("--time-frame", type=int, default=0,
                        help="Which time frame to inspect (default: 0 = first)")
    return parser.parse_args()


# ─────────────────────────────────────────────
# Synthetic audio (sine wave at 440 Hz, 3 sec)
# ─────────────────────────────────────────────
def make_synthetic_audio(sample_rate: int = 16000, duration: float = 3.0) -> np.ndarray:
    """Generate a simple sine wave. No file needed."""
    t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
    audio = 0.5 * np.sin(2 * np.pi * 440 * t) + 0.3 * np.sin(2 * np.pi * 880 * t)
    return audio


# ─────────────────────────────────────────────
# Layer Information Score (cosine similarity to final layer)
# ─────────────────────────────────────────────
def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two 1-D or 2-D arrays (mean over rows if 2-D)."""
    if a.ndim == 2:
        # Mean cosine similarity across time frames
        sims = []
        for i in range(min(a.shape[0], b.shape[0])):
            na, nb = np.linalg.norm(a[i]), np.linalg.norm(b[i])
            if na == 0 or nb == 0:
                sims.append(0.0)
            else:
                sims.append(float(np.dot(a[i], b[i]) / (na * nb)))
        return float(np.mean(sims))
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def layer_information_score(
    layer_logits: np.ndarray,   # [T, vocab_size]
    final_logits: np.ndarray,   # [T, vocab_size]
) -> float:
    """
    Layer Information Score (LIS) — how much does layer L's projection
    agree with the final (deepest) layer's projection?

    Method: cosine similarity of softmax(logits) distributions averaged over T.
    Range: [0, 1]; 1 = identical distribution to final layer.
    
    This mirrors AudioLens's "Layer-wise Information Score".
    """
    # Softmax (numerically stable)
    def softmax(x):
        x = x - x.max(axis=-1, keepdims=True)
        e = np.exp(x)
        return e / e.sum(axis=-1, keepdims=True)

    p_layer = softmax(layer_logits)   # [T, V]
    p_final = softmax(final_logits)   # [T, V]
    return cosine_similarity(p_layer, p_final)


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def main():
    args = parse_args()

    # Check deps
    missing = []
    for pkg in ["whisper", "torch", "numpy"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[ERROR] Missing packages: {', '.join(missing)}")
        sys.exit(1)

    import torch
    import whisper
    import whisper.tokenizer

    print(f"\n{'='*65}")
    print(f"  Whisper Logit-Lens — Triple Convergence Test")
    print(f"  Model: Whisper-{args.model}")
    print(f"{'='*65}")

    # ── 1. Load model ──
    print(f"\n[1] Loading Whisper-{args.model}...")
    model = whisper.load_model(args.model)
    encoder = model.encoder
    encoder.eval()

    n_layers = len(encoder.blocks)
    d_model = encoder.blocks[0].attn.query.in_features
    print(f"    Encoder: {n_layers} layers, d_model={d_model}")

    # The "unembed" matrix: decoder's token_embedding (shape: [vocab, d_model])
    # We'll project encoder hidden states → logits using this matrix.
    # Note: Whisper uses tied embeddings: decoder.token_embedding.weight
    # For encoder, we also need ln_post (layer norm before decoder cross-attn).
    token_embed = model.decoder.token_embedding.weight.detach().cpu().numpy()  # [vocab, d_model]
    vocab_size = token_embed.shape[0]
    print(f"    Decoder embedding: vocab_size={vocab_size}, d_model={d_model}")

    # ln_post params (Whisper encoder has ln_post before projection)
    ln_post_weight = encoder.ln_post.weight.detach().cpu().numpy()  # [d_model]
    ln_post_bias = encoder.ln_post.bias.detach().cpu().numpy()      # [d_model]

    def apply_ln_and_project(hidden: np.ndarray) -> np.ndarray:
        """
        Apply encoder's ln_post and project to vocabulary space.
        hidden: [T, d_model] → returns [T, vocab_size]

        This is the core logit-lens operation: treat each layer's
        hidden state as if it were the final encoder output.
        """
        # LayerNorm: (x - mean) / std * weight + bias
        mean = hidden.mean(axis=-1, keepdims=True)
        std = hidden.std(axis=-1, keepdims=True) + 1e-5
        normed = (hidden - mean) / std * ln_post_weight + ln_post_bias
        # Linear projection: [T, d_model] @ [d_model, vocab] = [T, vocab]
        logits = normed @ token_embed.T
        return logits

    # ── 2. Register hooks ──
    activation_cache: dict[int, np.ndarray] = {}

    def make_hook(layer_idx: int):
        def hook(module, input, output):
            activation_cache[layer_idx] = output.detach().cpu().numpy()
        return hook

    hooks = []
    for i, block in enumerate(encoder.blocks):
        h = block.register_forward_hook(make_hook(i))
        hooks.append(h)

    # ── 3. Load / generate audio ──
    if args.audio:
        print(f"\n[2] Loading audio from: {args.audio}")
        audio = whisper.load_audio(args.audio)
    else:
        print(f"\n[2] No audio file — using synthetic 440+880 Hz sine wave (3 sec)")
        audio = make_synthetic_audio()

    audio = whisper.pad_or_trim(audio)
    mel = whisper.log_mel_spectrogram(audio).unsqueeze(0)  # [1, 80, 3000]

    # ── 4. Forward pass ──
    print(f"\n[3] Running encoder forward pass...")
    with torch.no_grad():
        final_encoder_out = encoder(mel)  # [1, T, d_model]

    final_hidden = final_encoder_out[0].cpu().numpy()  # [T, d_model]
    print(f"    Encoder output shape: {final_hidden.shape}")

    for h in hooks:
        h.remove()

    # ── 5. Project all layers through logit lens ──
    print(f"\n[4] Logit-Lens projection for all {n_layers} layers...")
    print(f"    {'Layer':>6}  {'LIS':>8}  {'Top-1 token':>25}  {'Token norm':>12}")
    print(f"    {'-'*60}")

    # Final layer logits (reference)
    final_logits = apply_ln_and_project(final_hidden)  # [T, V]

    lis_scores = []
    layer_top_tokens = []

    # Load tokenizer for decoding
    tokenizer = whisper.tokenizer.get_tokenizer(multilingual=False)

    t_frame = min(args.time_frame, final_hidden.shape[0] - 1)

    for layer_idx in range(n_layers):
        hidden = activation_cache[layer_idx][0]  # [T, d_model]
        logits = apply_ln_and_project(hidden)     # [T, V]

        # LIS: similarity to final layer logits
        lis = layer_information_score(logits, final_logits)
        lis_scores.append(lis)

        # Top-k tokens at the specified time frame
        frame_logits = logits[t_frame]  # [V]
        topk_ids = np.argsort(frame_logits)[::-1][:args.topk]
        topk_tokens = []
        for tid in topk_ids:
            try:
                tok = tokenizer.decode([int(tid)])
                topk_tokens.append(tok.strip() or f"<{tid}>")
            except Exception:
                topk_tokens.append(f"<{tid}>")
        layer_top_tokens.append(topk_tokens)

        top1 = topk_tokens[0] if topk_tokens else "?"
        marker = ""
        if lis >= args.lis_threshold and (layer_idx == 0 or lis_scores[-2] < args.lis_threshold):
            marker = "  ← SATURATION LAYER ⭐"

        # Norm of the projection for the time frame
        proj_norm = float(np.linalg.norm(frame_logits))

        print(f"    Layer {layer_idx:>2}:  {lis:>8.4f}  {repr(top1):>25}  {proj_norm:>12.2f}{marker}")

    # ── 6. Saturation analysis ──
    saturation_layer = None
    for i, lis in enumerate(lis_scores):
        if lis >= args.lis_threshold:
            saturation_layer = i
            break

    print(f"\n[5] Triple Convergence Analysis:")
    print(f"    LIS threshold: {args.lis_threshold}")
    if saturation_layer is not None:
        pct = saturation_layer / (n_layers - 1) * 100
        print(f"    Saturation layer: {saturation_layer} ({pct:.0f}% depth) ← semantic crystallization point")
        print(f"    Prediction check: 50% depth = layer {n_layers // 2}")
        if saturation_layer == n_layers // 2:
            print(f"    ✅ CONFIRMED: Saturation at ~50% depth (consistent with Triple Convergence)")
        elif abs(saturation_layer - n_layers // 2) <= 1:
            print(f"    ✅ CLOSE MATCH: ±1 layer from 50% prediction")
        else:
            print(f"    ⚠️  OFF: Saturation at {pct:.0f}% depth, expected ~50%")
    else:
        print(f"    ⚠️  No saturation found below LIS={args.lis_threshold} — try lowering --lis-threshold")

    # ── 7. Token evolution ──
    print(f"\n[6] Token evolution at frame {t_frame} (logit-lens decode per layer):")
    for i in range(n_layers):
        tokens_str = " | ".join(repr(t) for t in layer_top_tokens[i])
        print(f"    Layer {i:>2}: {tokens_str}")
    print()
    print("    (Early layers → noise/incoherent tokens; later layers → structured output)")
    print("    (Transition point = where tokens become coherent = saturation layer)")

    # ── 8. Plot ──
    if not args.no_plot:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            fig, axes = plt.subplots(1, 2, figsize=(14, 5))
            fig.suptitle("Whisper Logit-Lens — Triple Convergence Test", fontsize=14)

            # LIS curve
            ax = axes[0]
            ax.plot(range(n_layers), lis_scores, "o-", color="steelblue", linewidth=2.5)
            ax.axhline(y=args.lis_threshold, color="orange", linestyle="--",
                       label=f"Saturation threshold ({args.lis_threshold})")
            if saturation_layer is not None:
                ax.axvline(x=saturation_layer, color="red", linestyle="-.",
                           label=f"Saturation layer {saturation_layer}")
            ax.axvline(x=n_layers / 2 - 0.5, color="green", linestyle=":",
                       alpha=0.7, label=f"50% depth (layer {n_layers // 2})")
            ax.set_xlabel("Layer")
            ax.set_ylabel("Layer Information Score (LIS)")
            ax.set_title("LIS per Layer\n(1 = identical to final encoder output)")
            ax.set_xticks(range(n_layers))
            ax.legend()
            ax.grid(alpha=0.3)
            ax.set_ylim(-0.05, 1.05)

            # Top-1 token annotation (qualitative)
            ax2 = axes[1]
            # Show LIS as bars with token labels
            colors = ["#e74c3c" if lis < args.lis_threshold else "#27ae60"
                      for lis in lis_scores]
            bars = ax2.bar(range(n_layers), lis_scores, color=colors, alpha=0.8)
            ax2.set_xlabel("Layer")
            ax2.set_ylabel("LIS")
            ax2.set_title(f"LIS per Layer with Top-1 Token\n(frame={t_frame}, red=pre-saturation, green=post)")
            ax2.set_xticks(range(n_layers))
            ax2.grid(alpha=0.3, axis="y")

            # Annotate each bar with top-1 token
            for i, (bar, tokens) in enumerate(zip(bars, layer_top_tokens)):
                top1 = tokens[0][:6] if tokens else "?"
                ax2.text(bar.get_x() + bar.get_width() / 2,
                         bar.get_height() + 0.02,
                         top1,
                         ha="center", va="bottom", fontsize=7, rotation=45)

            plt.tight_layout()
            out_path = "/tmp/whisper_logit_lens.png"
            plt.savefig(out_path, dpi=150)
            print(f"\n[7] Plot saved → {out_path}")

        except Exception as e:
            print(f"\n[7] [WARN] Could not generate plots: {e}")

    # ── Summary ──
    print(f"\n{'='*65}")
    print(f"  ✅ Logit-Lens demo complete!")
    print()
    print(f"  Triple Convergence Hypothesis:")
    print(f"    AudioSAE  → layer 6-7 transition (large; =3 for base)")
    print(f"    AudioLens → critical layer (weighted avg, correlates with accuracy)")
    print(f"    Beyond Transcription → saturation layer (where encoder commits)")
    print()
    if saturation_layer is not None:
        print(f"  This script found:  saturation layer = {saturation_layer}")
    print()
    print(f"  Next steps:")
    print(f"    1. Try with real speech: --audio speech.wav")
    print(f"    2. Compare LIS with/without speech (vs silence/noise)")
    print(f"    3. Extend: patch activations at saturation layer → measure WER change")
    print(f"    4. → This is the 'Causal AudioLens' experiment!")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
