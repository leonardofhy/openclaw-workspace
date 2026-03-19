"""
whisper_hook_demo.py
====================
Starter script for mechanistic interpretability on Whisper encoder.
MacBook-feasible (Whisper-base, ~400MB RAM, CPU-only).

Experiment sequence (ordered by difficulty):
  1. Load Whisper-base, register hooks on all encoder layers
  2. Run forward on a sample audio (synthetic sine wave if no file provided)
  3. Extract activations from all 12 layers
  4. Plot CKA (Centered Kernel Alignment) heatmap across layers
  5. Print layer 6 activation stats (the "transition zone" from AudioSAE)

Usage:
  python whisper_hook_demo.py [--audio path/to/audio.wav] [--no-plot]

Requirements:
  pip install openai-whisper torch numpy matplotlib

References:
  - AudioSAE: layer 6-7 = speech/acoustic transition zone
  - Beyond Transcription: saturation layer (where encoder "commits")
  - cheat sheet: skills/autodidact/references/transformerlens-pyvene-cheatsheet.md
"""

import argparse
import sys
import numpy as np

# ─────────────────────────────────────────────
# Args
# ─────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(description="Whisper encoder activation explorer")
    parser.add_argument("--audio", type=str, default=None,
                        help="Path to audio file (WAV/MP3). Uses synthetic sine wave if omitted.")
    parser.add_argument("--model", type=str, default="base",
                        choices=["tiny", "base", "small"],
                        help="Whisper model size (default: base)")
    parser.add_argument("--no-plot", action="store_true",
                        help="Skip matplotlib plots (useful in headless environments)")
    parser.add_argument("--layer-inspect", type=int, default=6,
                        help="Layer to inspect in detail (default: 6, the transition zone)")
    return parser.parse_args()


# ─────────────────────────────────────────────
# Check dependencies
# ─────────────────────────────────────────────
def check_deps():
    missing = []
    for pkg, import_name in [("whisper", "whisper"), ("torch", "torch"),
                              ("numpy", "numpy")]:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[ERROR] Missing packages: {', '.join(missing)}")
        print(f"  Install: pip install {' '.join(missing)}")
        sys.exit(1)


# ─────────────────────────────────────────────
# Synthetic audio (sine wave at 440 Hz, 3 sec)
# ─────────────────────────────────────────────
def make_synthetic_audio(sample_rate: int = 16000, duration: float = 3.0) -> np.ndarray:
    """Generate a simple sine wave. No file needed."""
    t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
    # Mix 440 Hz + 880 Hz for slight complexity
    audio = 0.5 * np.sin(2 * np.pi * 440 * t) + 0.3 * np.sin(2 * np.pi * 880 * t)
    return audio


# ─────────────────────────────────────────────
# CKA (Linear) — measures layer similarity
# ─────────────────────────────────────────────
def linear_cka(X: np.ndarray, Y: np.ndarray) -> float:
    """
    Compute linear CKA between two activation matrices.
    X, Y: shape [n_samples, d_features]
    Returns: scalar in [0, 1] (1 = identical representations)

    Reference: Kornblith et al. 2019 "Similarity of Neural Network Representations Revisited"
    """
    # Center columns
    X = X - X.mean(axis=0)
    Y = Y - Y.mean(axis=0)
    # Compute HSIC (Hilbert-Schmidt Independence Criterion)
    XtX = X.T @ X
    YtY = Y.T @ Y
    XtY = X.T @ Y
    hsic_xy = np.linalg.norm(XtY, "fro") ** 2
    hsic_xx = np.linalg.norm(XtX, "fro") ** 2
    hsic_yy = np.linalg.norm(YtY, "fro") ** 2
    if hsic_xx == 0 or hsic_yy == 0:
        return 0.0
    return hsic_xy / np.sqrt(hsic_xx * hsic_yy)


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def main():
    args = parse_args()
    check_deps()

    import torch
    import whisper

    print(f"\n{'='*60}")
    print(f"  Whisper Encoder Hook Demo — {args.model.upper()} model")
    print(f"{'='*60}")

    # ── 1. Load model ──
    print(f"\n[1] Loading Whisper-{args.model}...")
    model = whisper.load_model(args.model)
    encoder = model.encoder
    encoder.eval()
    n_layers = len(encoder.blocks)
    print(f"    Encoder: {n_layers} layers, d_model={encoder.blocks[0].attn.query.in_features}")

    # ── 2. Register hooks ──
    activation_cache: dict[int, np.ndarray] = {}

    def make_hook(layer_idx: int):
        def hook(module, input, output):
            # output is the tensor after this transformer block
            # shape: [batch, time_frames, d_model]
            activation_cache[layer_idx] = output.detach().cpu().numpy()
        return hook

    hooks = []
    for i, block in enumerate(encoder.blocks):
        h = block.register_forward_hook(make_hook(i))
        hooks.append(h)

    print(f"    Registered hooks on {n_layers} encoder layers.")

    # ── 3. Load / generate audio ──
    if args.audio:
        print(f"\n[2] Loading audio from: {args.audio}")
        audio = whisper.load_audio(args.audio)
    else:
        print(f"\n[2] No audio file provided — using synthetic 440 Hz sine wave (3 sec)")
        audio = make_synthetic_audio()

    audio = whisper.pad_or_trim(audio)  # standardize to 30s
    mel = whisper.log_mel_spectrogram(audio).unsqueeze(0)  # [1, 80, 3000]

    # ── 4. Forward pass ──
    print(f"\n[3] Running encoder forward pass...")
    with torch.no_grad():
        _ = encoder(mel)

    print(f"    Cached activations from {len(activation_cache)} layers.")
    for h in hooks:
        h.remove()  # clean up

    # ── 5. Layer stats ──
    print(f"\n[4] Layer activation statistics:")
    print(f"    {'Layer':>6}  {'Mean':>10}  {'Std':>10}  {'Norm':>12}")
    print(f"    {'-'*46}")
    norms = []
    for i in range(n_layers):
        acts = activation_cache[i]  # [1, T, d_model]
        acts_flat = acts[0]  # [T, d_model]
        mean_val = float(acts_flat.mean())
        std_val = float(acts_flat.std())
        norm_val = float(np.linalg.norm(acts_flat, "fro"))
        norms.append(norm_val)
        marker = "  ← TRANSITION ZONE (AudioSAE)" if i in (5, 6) else ""
        print(f"    Layer {i:>2}:  {mean_val:>10.4f}  {std_val:>10.4f}  {norm_val:>12.2f}{marker}")

    # ── 6. CKA heatmap ──
    if not args.no_plot:
        try:
            import matplotlib
            matplotlib.use("Agg")  # headless safe
            import matplotlib.pyplot as plt

            print(f"\n[5] Computing CKA similarity matrix across {n_layers} layers...")
            # Flatten activations for CKA: [T*1, d_model]
            flat = {i: activation_cache[i][0] for i in range(n_layers)}  # [T, d_model]

            cka_matrix = np.zeros((n_layers, n_layers))
            for i in range(n_layers):
                for j in range(n_layers):
                    cka_matrix[i, j] = linear_cka(flat[i], flat[j])

            fig, axes = plt.subplots(1, 2, figsize=(14, 5))

            # CKA heatmap
            ax = axes[0]
            im = ax.imshow(cka_matrix, vmin=0, vmax=1, cmap="viridis")
            ax.set_title("CKA Similarity (Whisper Encoder Layers)", fontsize=13)
            ax.set_xlabel("Layer")
            ax.set_ylabel("Layer")
            ax.set_xticks(range(n_layers))
            ax.set_yticks(range(n_layers))
            plt.colorbar(im, ax=ax)

            # Norm per layer (proxy for "information load")
            ax2 = axes[1]
            ax2.plot(range(n_layers), norms, "o-", color="steelblue", linewidth=2)
            ax2.axvline(x=5.5, color="red", linestyle="--", alpha=0.6, label="AudioSAE transition (6-7)")
            ax2.set_xlabel("Layer")
            ax2.set_ylabel("Frobenius Norm")
            ax2.set_title("Activation Norm per Layer\n(proxy for representational 'richness')", fontsize=12)
            ax2.legend()
            ax2.set_xticks(range(n_layers))
            ax2.grid(alpha=0.3)

            out_path = "/tmp/whisper_hook_demo.png"
            plt.tight_layout()
            plt.savefig(out_path, dpi=150)
            print(f"    Saved CKA + norm plot → {out_path}")
        except Exception as e:
            print(f"    [WARN] Could not generate plots: {e}")

    # ── 7. Layer inspect ──
    li = args.layer_inspect
    if li < n_layers:
        acts = activation_cache[li][0]  # [T, d_model]
        print(f"\n[6] Layer {li} deep inspect (d_model={acts.shape[1]}, T={acts.shape[0]}):")
        # Top 5 most active dimensions
        dim_norms = np.linalg.norm(acts, axis=0)  # [d_model]
        top_dims = np.argsort(dim_norms)[::-1][:5]
        print(f"    Top-5 most active dimensions:")
        for rank, dim in enumerate(top_dims):
            print(f"      #{rank+1}: dim {dim:>4} — norm={dim_norms[dim]:.3f}")
        print(f"\n    (These dimensions are candidates for probing/SAE analysis)")

    # ── Summary ──
    print(f"\n{'='*60}")
    print("  ✅ Demo complete!")
    print()
    print("  What to try next:")
    print("    1. Run on real speech: --audio path/to/speech.wav")
    print("    2. Probe layer 6 for phonemes (label your audio frames)")
    print("    3. Add pyvene patching: patch clean layer 6 → corrupted audio → measure WER")
    print("    4. Try AudioSAE code: https://github.com/audiosae/audiosae_demo")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
