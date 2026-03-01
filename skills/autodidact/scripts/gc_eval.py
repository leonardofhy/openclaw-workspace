#!/usr/bin/env python3
"""
gc(k) Evaluation Harness — graded causality curve per layer
Track T3: Listen vs Guess (Paper A)

gc(k) measures the causal contribution of audio evidence (vs language prior)
at each Whisper encoder/decoder layer k. Method: activation patching.

Usage (mock mode):
    python3 gc_eval.py --mock
    python3 gc_eval.py --mock --plot

Usage (real model, Tier 1+):
    python3 gc_eval.py \
        --model-name openai/whisper-tiny \
        --audio-clean path/to/clean.wav \
        --audio-noisy path/to/noisy.wav \
        --layer-range 0 5

gc(k) Definition (causal patching):
    Clean run → record all layer activations
    Noisy baseline run → get corrupted activations
    For each layer k:
        Patch layer k of noisy run with clean activations → measure ΔP(correct token)
    gc(k) = ΔP(correct token) / max_ΔP  (normalized, range [0,1])

High gc(k) at layer k → audio evidence causally important at that layer.
Low gc(k) throughout → model "guessing" from language prior.
"""

import argparse
import json
import sys
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Mock data generator (Tier 0 — no model needed)
# ---------------------------------------------------------------------------

def generate_mock_gc_curve(
    n_encoder_layers: int = 6,
    n_decoder_layers: int = 6,
    seed: int = 42,
    mode: str = "listen",  # "listen" | "guess"
) -> dict:
    """
    Generate a plausible mock gc(k) curve.

    In "listen" mode: gc(k) rises then stays high (audio used throughout).
    In "guess" mode: gc(k) drops off fast (model falls back to language prior).
    """
    rng = np.random.default_rng(seed)
    total = n_encoder_layers + n_decoder_layers
    layers = list(range(total))

    if mode == "listen":
        # Rises through encoder, stays elevated in decoder
        encoder_vals = np.linspace(0.2, 0.85, n_encoder_layers) + rng.normal(0, 0.04, n_encoder_layers)
        decoder_vals = np.linspace(0.85, 0.7, n_decoder_layers) + rng.normal(0, 0.06, n_decoder_layers)
    else:
        # Peaks mid-encoder, collapses in decoder
        encoder_vals = np.linspace(0.1, 0.6, n_encoder_layers) + rng.normal(0, 0.05, n_encoder_layers)
        decoder_vals = np.linspace(0.4, 0.05, n_decoder_layers) + rng.normal(0, 0.04, n_decoder_layers)

    values = np.concatenate([encoder_vals, decoder_vals])
    values = np.clip(values, 0.0, 1.0)

    return {
        "layers": layers,
        "gc_values": values.tolist(),
        "n_encoder_layers": n_encoder_layers,
        "n_decoder_layers": n_decoder_layers,
        "mode": mode,
        "method": "mock_causal_patch",
    }


# ---------------------------------------------------------------------------
# Real model harness (Tier 1 — requires transformers + torch)
# ---------------------------------------------------------------------------

def compute_gc_curve_real(
    model_name: str,
    audio_clean: str,
    audio_noisy: str,
    layer_range: tuple[int, int],
    target_token: Optional[str] = None,
) -> dict:
    """
    Compute gc(k) via causal patching on a real Whisper model.
    
    Requires: transformers, torch, librosa (Tier 1 — CPU, <5 min for small models).
    """
    try:
        import torch
        from transformers import WhisperForConditionalGeneration, WhisperProcessor
        import librosa
    except ImportError as e:
        raise RuntimeError(
            f"Missing dependency: {e}. Run: pip install transformers torch librosa"
        ) from e

    print(f"[gc_eval] Loading model: {model_name}", file=sys.stderr)
    processor = WhisperProcessor.from_pretrained(model_name)
    model = WhisperForConditionalGeneration.from_pretrained(model_name)
    model.eval()

    def load_audio(path: str) -> torch.Tensor:
        waveform, _ = librosa.load(path, sr=16000, mono=True)
        inputs = processor(waveform, sampling_rate=16000, return_tensors="pt")
        return inputs.input_features

    feat_clean = load_audio(audio_clean)
    feat_noisy = load_audio(audio_noisy)

    # --- Record clean activations ---
    enc_clean_acts: dict[int, torch.Tensor] = {}

    def make_hook(layer_idx: int, store: dict):
        def hook(module, inp, out):
            store[layer_idx] = out[0].detach().clone()
        return hook

    n_enc = model.config.encoder_layers

    handles = []
    for i in range(n_enc):
        h = model.model.encoder.layers[i].register_forward_hook(
            make_hook(i, enc_clean_acts)
        )
        handles.append(h)

    with torch.no_grad():
        clean_out = model.generate(feat_clean, return_dict_in_generate=True, output_scores=True)

    for h in handles:
        h.remove()

    # Get clean token probability for target
    # Default: take the first generated token as target
    clean_tokens = clean_out.sequences[0]
    target_id = int(clean_tokens[1])  # first real token after BOS

    def get_logp_target(features: torch.Tensor, patch_layer: Optional[int] = None,
                        patch_act: Optional[torch.Tensor] = None) -> float:
        """Run forward pass, optionally patching one encoder layer."""
        patch_store: dict[int, torch.Tensor] = {}

        def patch_hook(module, inp, out):
            if patch_layer is not None:
                return (patch_act,) + out[1:]
            return out

        hh = None
        if patch_layer is not None:
            hh = model.model.encoder.layers[patch_layer].register_forward_hook(patch_hook)

        with torch.no_grad():
            logits = model(input_features=features, decoder_input_ids=clean_tokens[:1].unsqueeze(0)).logits
            lp = float(torch.log_softmax(logits[0, 0], dim=-1)[target_id])

        if hh is not None:
            hh.remove()

        return lp

    baseline_clean_lp = get_logp_target(feat_clean)
    baseline_noisy_lp = get_logp_target(feat_noisy)
    delta_baseline = baseline_clean_lp - baseline_noisy_lp

    layer_start, layer_end = layer_range
    layer_end = min(layer_end, n_enc)
    layers = list(range(layer_start, layer_end))
    gc_values = []

    for k in layers:
        patched_lp = get_logp_target(feat_noisy, patch_layer=k, patch_act=enc_clean_acts[k])
        delta_k = patched_lp - baseline_noisy_lp
        gc_k = delta_k / (abs(delta_baseline) + 1e-8)
        gc_values.append(float(np.clip(gc_k, 0.0, 1.0)))
        print(f"[gc_eval] layer {k}: gc={gc_k:.4f}", file=sys.stderr)

    return {
        "layers": layers,
        "gc_values": gc_values,
        "n_encoder_layers": n_enc,
        "n_decoder_layers": model.config.decoder_layers,
        "target_token_id": target_id,
        "method": "causal_patch",
        "model": model_name,
    }


# ---------------------------------------------------------------------------
# Output + plotting
# ---------------------------------------------------------------------------

def print_curve(result: dict) -> None:
    n_enc = result["n_encoder_layers"]
    print("\n=== gc(k) Curve ===")
    print(f"{'Layer':>6}  {'Type':>8}  {'gc(k)':>8}  {'Bar'}")
    print("-" * 50)
    for i, (layer, val) in enumerate(zip(result["layers"], result["gc_values"])):
        layer_type = "enc" if layer < n_enc else "dec"
        bar = "█" * int(val * 30) + "░" * (30 - int(val * 30))
        print(f"{layer:>6}  {layer_type:>8}  {val:>8.3f}  {bar}")
    print()
    gc = np.array(result["gc_values"])
    print(f"Mean gc (encoder): {gc[:n_enc].mean():.3f}")
    print(f"Mean gc (decoder): {gc[n_enc:].mean():.3f}")
    print(f"Peak layer: {result['layers'][int(np.argmax(gc))]}")
    print()


def plot_curve(result: dict) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("[gc_eval] matplotlib not available; skipping plot.", file=sys.stderr)
        return

    n_enc = result["n_encoder_layers"]
    layers = result["layers"]
    vals = result["gc_values"]

    fig, ax = plt.subplots(figsize=(10, 4))
    enc_layers = [l for l in layers if l < n_enc]
    dec_layers = [l for l in layers if l >= n_enc]
    enc_vals = vals[: len(enc_layers)]
    dec_vals = vals[len(enc_layers):]

    ax.plot(enc_layers, enc_vals, "b-o", label="Encoder layers", linewidth=2)
    ax.plot(dec_layers, dec_vals, "r-s", label="Decoder layers", linewidth=2)
    ax.axvline(x=n_enc - 0.5, color="gray", linestyle="--", alpha=0.5, label="Enc/Dec boundary")
    ax.axhline(y=0.5, color="green", linestyle=":", alpha=0.5, label="gc=0.5 (balanced)")
    ax.set_xlabel("Layer k")
    ax.set_ylabel("gc(k) — causal contribution of audio")
    ax.set_title(f"gc(k) Curve [{result.get('mode', result.get('model', 'real'))}]")
    ax.legend()
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)

    out_path = "/tmp/gc_curve.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    print(f"[gc_eval] Plot saved: {out_path}", file=sys.stderr)
    plt.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="gc(k) eval harness")
    parser.add_argument("--mock", action="store_true", help="Use mock data (no model needed)")
    parser.add_argument("--mock-mode", choices=["listen", "guess"], default="listen")
    parser.add_argument("--model-name", default="openai/whisper-tiny")
    parser.add_argument("--audio-clean", help="Path to clean audio .wav")
    parser.add_argument("--audio-noisy", help="Path to noisy/corrupted audio .wav")
    parser.add_argument("--layer-range", nargs=2, type=int, default=[0, 6], metavar=("START", "END"))
    parser.add_argument("--plot", action="store_true", help="Save curve plot to /tmp/gc_curve.png")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    if args.mock:
        result = generate_mock_gc_curve(mode=args.mock_mode)
    else:
        if not args.audio_clean or not args.audio_noisy:
            parser.error("--audio-clean and --audio-noisy required without --mock")
        result = compute_gc_curve_real(
            model_name=args.model_name,
            audio_clean=args.audio_clean,
            audio_noisy=args.audio_noisy,
            layer_range=tuple(args.layer_range),
        )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_curve(result)

    if args.plot:
        plot_curve(result)


if __name__ == "__main__":
    main()
