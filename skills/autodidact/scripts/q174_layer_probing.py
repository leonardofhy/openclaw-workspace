#!/usr/bin/env python3
"""
Q174: Layer-wise Phoneme/Word Probing at Listen Layer
Track T3 — Listen vs Guess (Paper A)

Hypothesis: Linear probe accuracy at each encoder layer k reveals *when*
Whisper transitions from sub-phonemic features → phoneme identity → word-level
semantics. This transition should co-locate with the AND-frac "listen layer" L*.

Method:
1. Feed audio through Whisper encoder; collect hidden states at each layer.
2. Align phoneme/word labels to frame positions via forced alignment (or CTC proxy).
3. Train logistic regression probe at each layer; record probe accuracy.
4. Compare probe accuracy profile to AND-frac gc(k) curve.

Data: L2-ARCTIC (accented English) — tests if Listen Layer is accent-robust.
Fallback: synthetic 40-class classification task mimicking encoder geometry.

CPU-only, Tier 0 (build scaffold + synthetic baseline). Real model path: Tier 1.

Usage:
    python3 q174_layer_probing.py --mock              # synthetic data only
    python3 q174_layer_probing.py --model whisper-base --audio-dir /path/to/l2arctic
    python3 q174_layer_probing.py --mock --plot

Definition of Done (Q174):
    - Probe accuracy curve plotted across layers 0→L*
    - Profile shape compared to AND-frac gc(k) transition
    - Transition layer identified and logged
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ENCODER_LAYERS_BY_MODEL = {
    "whisper-tiny": 4,
    "whisper-base": 6,
    "whisper-small": 12,
    "whisper-medium": 24,
    "whisper-large-v3": 32,
}

# Known AND-frac Listen Layer (L*) from prior experiments (Q001, Q002)
# L* is the layer where AND-frac transitions from near-0 to near-1 (audio evidence kicks in)
KNOWN_LISTEN_LAYER = {
    "whisper-tiny": 2,
    "whisper-base": 3,
}

# Number of phoneme classes (English reduced set: 40 IPA classes)
N_PHONEME_CLASSES = 40
N_WORD_CLASSES = 200  # frequent words in L2-ARCTIC vocab


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class ProbeResult:
    layer: int
    phoneme_acc: float      # linear probe accuracy for phoneme classification
    word_acc: float         # linear probe accuracy for word classification
    n_samples: int
    n_phoneme_classes: int
    n_word_classes: int


@dataclass
class LayerProbeReport:
    model_name: str
    n_encoder_layers: int
    results: list[ProbeResult] = field(default_factory=list)
    listen_layer_probe: Optional[int] = None    # layer where phoneme acc peaks
    listen_layer_gc: Optional[int] = None       # known L* from gc(k) / AND-frac
    profile_aligned: Optional[bool] = None      # do they agree?
    notes: str = ""


# ---------------------------------------------------------------------------
# Synthetic data generator (Tier 0 / CPU mock)
# ---------------------------------------------------------------------------

def generate_synthetic_data(
    n_layers: int,
    n_samples: int = 500,
    hidden_dim: int = 512,
    n_phoneme_classes: int = N_PHONEME_CLASSES,
    n_word_classes: int = N_WORD_CLASSES,
    listen_layer: int = 3,
    rng_seed: int = 42,
) -> dict:
    """
    Generate synthetic encoder activations that simulate the Listen Layer hypothesis:
    - Early layers (< listen_layer): activations are noisy; probe accuracy low
    - At listen_layer: rapid accuracy jump (phoneme structure emerges)
    - Late layers: word-level accuracy rises as attention integrates context

    Returns dict of {layer_idx: {"activations": ndarray, "phoneme_labels": ndarray, "word_labels": ndarray}}
    """
    rng = np.random.default_rng(rng_seed)
    data = {}

    for layer in range(n_layers):
        # Signal-to-noise ratio increases with layer (listen layer = inflection point)
        # Use logistic growth centered at listen_layer
        snr_phoneme = 1.0 / (1.0 + np.exp(-(layer - listen_layer) * 1.5))
        snr_word = 1.0 / (1.0 + np.exp(-(layer - listen_layer - 1) * 1.5))

        # Base noise activations
        noise = rng.standard_normal((n_samples, hidden_dim)).astype(np.float32)

        # Class prototypes
        phoneme_labels = rng.integers(0, n_phoneme_classes, n_samples)
        word_labels = rng.integers(0, n_word_classes, n_samples)

        # Embed class signal into activations
        phoneme_signal = np.zeros((n_samples, hidden_dim), dtype=np.float32)
        word_signal = np.zeros((n_samples, hidden_dim), dtype=np.float32)

        phoneme_proto = rng.standard_normal((n_phoneme_classes, hidden_dim)).astype(np.float32) * 2
        word_proto = rng.standard_normal((n_word_classes, hidden_dim)).astype(np.float32) * 2

        phoneme_signal = phoneme_proto[phoneme_labels]
        word_signal = word_proto[word_labels]

        activations = (
            snr_phoneme * phoneme_signal
            + snr_word * word_signal
            + (1.0 - max(snr_phoneme, snr_word)) * noise
        )

        data[layer] = {
            "activations": activations,
            "phoneme_labels": phoneme_labels,
            "word_labels": word_labels,
        }

    return data


# ---------------------------------------------------------------------------
# Linear Probe
# ---------------------------------------------------------------------------

def train_linear_probe(
    X: np.ndarray,
    y: np.ndarray,
    test_frac: float = 0.2,
    rng_seed: int = 42,
    max_iter: int = 200,
) -> float:
    """
    Train logistic regression probe on X→y.
    Returns held-out accuracy.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    # Use stratify only if all classes have >= 2 members
    unique, counts = np.unique(y, return_counts=True)
    can_stratify = bool(np.all(counts >= 2) and len(unique) < 200)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_frac, random_state=rng_seed, stratify=y if can_stratify else None
    )

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    clf = LogisticRegression(
        max_iter=max_iter,
        C=0.1,
        solver="saga",
        n_jobs=-1,
        random_state=rng_seed,
    )
    clf.fit(X_train, y_train)
    return float(clf.score(X_test, y_test))


# ---------------------------------------------------------------------------
# Real Whisper encoder extraction (Tier 1 — real model)
# ---------------------------------------------------------------------------

def extract_whisper_activations(
    model_name: str,
    audio_paths: list[Path],
    n_frames_per_file: int = 50,
) -> dict:
    """
    Extract encoder hidden states from Whisper for each layer.
    Returns same format as generate_synthetic_data.

    NOTE: This requires openai-whisper + torch + audio files.
    Tier 1 — CPU-only, Whisper-base runs in ~3s per file on CPU.
    """
    import torch
    import whisper

    print(f"[INFO] Loading {model_name}...")
    model = whisper.load_model(model_name.replace("whisper-", ""))
    encoder = model.encoder
    n_layers = len(encoder.blocks)

    all_activations = {layer: [] for layer in range(n_layers)}
    dummy_phoneme_labels = []
    dummy_word_labels = []

    hooks = []
    layer_cache = {}

    def make_hook(layer_idx):
        def hook(module, input, output):
            # output shape: (batch, seq_len, hidden_dim)
            # take mean over seq_len for each sample
            layer_cache[layer_idx] = output.detach().cpu().numpy()
        return hook

    for layer_idx, block in enumerate(encoder.blocks):
        h = block.register_forward_hook(make_hook(layer_idx))
        hooks.append(h)

    model.eval()
    with torch.no_grad():
        for audio_path in audio_paths[:50]:  # cap at 50 files for CPU budget
            try:
                audio = whisper.load_audio(str(audio_path))
                audio = whisper.pad_or_trim(audio)
                mel = whisper.log_mel_spectrogram(audio).unsqueeze(0)
                _ = encoder(mel)

                for layer_idx in range(n_layers):
                    acts = layer_cache[layer_idx][0]  # (seq_len, hidden_dim)
                    # sample n_frames_per_file frames
                    idxs = np.linspace(0, len(acts) - 1, n_frames_per_file, dtype=int)
                    all_activations[layer_idx].append(acts[idxs])

                # dummy labels (would be replaced by forced alignment in full experiment)
                dummy_phoneme_labels.extend([0] * n_frames_per_file)
                dummy_word_labels.extend([0] * n_frames_per_file)

            except Exception as e:
                print(f"[WARN] Skipped {audio_path}: {e}")

    for h in hooks:
        h.remove()

    data = {}
    phoneme_labels = np.array(dummy_phoneme_labels)
    word_labels = np.array(dummy_word_labels)

    for layer_idx in range(n_layers):
        if all_activations[layer_idx]:
            acts = np.concatenate(all_activations[layer_idx], axis=0)
            data[layer_idx] = {
                "activations": acts,
                "phoneme_labels": phoneme_labels[: len(acts)],
                "word_labels": word_labels[: len(acts)],
            }

    return data


# ---------------------------------------------------------------------------
# Probe runner
# ---------------------------------------------------------------------------

def run_probes(
    data: dict,
    n_layers: int,
    model_name: str = "whisper-base",
    verbose: bool = True,
) -> LayerProbeReport:
    """Run linear probes at each layer and return a LayerProbeReport."""
    report = LayerProbeReport(
        model_name=model_name,
        n_encoder_layers=n_layers,
        listen_layer_gc=KNOWN_LISTEN_LAYER.get(model_name),
    )

    phoneme_accs = []
    for layer in range(n_layers):
        if layer not in data:
            continue
        d = data[layer]
        X = d["activations"]
        y_phoneme = d["phoneme_labels"]
        y_word = d["word_labels"]

        p_acc = train_linear_probe(X, y_phoneme)
        w_acc = train_linear_probe(X, y_word)
        phoneme_accs.append(p_acc)

        result = ProbeResult(
            layer=layer,
            phoneme_acc=p_acc,
            word_acc=w_acc,
            n_samples=len(X),
            n_phoneme_classes=len(np.unique(y_phoneme)),
            n_word_classes=len(np.unique(y_word)),
        )
        report.results.append(result)

        if verbose:
            print(f"  Layer {layer:2d}: phoneme_acc={p_acc:.3f}  word_acc={w_acc:.3f}")

    # Find listen layer = layer of max phoneme accuracy increase (inflection)
    if len(phoneme_accs) >= 2:
        diffs = np.diff(phoneme_accs)
        report.listen_layer_probe = int(np.argmax(diffs))

    # Alignment check
    if report.listen_layer_probe is not None and report.listen_layer_gc is not None:
        delta = abs(report.listen_layer_probe - report.listen_layer_gc)
        report.profile_aligned = delta <= 1  # within 1 layer = aligned
        if delta == 0:
            report.notes = f"✅ Perfect alignment: probe L*={report.listen_layer_probe} matches gc(k) L*={report.listen_layer_gc}"
        elif delta == 1:
            report.notes = f"✅ Near-aligned: probe L*={report.listen_layer_probe}, gc(k) L*={report.listen_layer_gc} (Δ=1)"
        else:
            report.notes = f"⚠️ Misaligned: probe L*={report.listen_layer_probe}, gc(k) L*={report.listen_layer_gc} (Δ={delta})"
    else:
        report.notes = "No known L* for alignment comparison."

    return report


# ---------------------------------------------------------------------------
# ASCII plot
# ---------------------------------------------------------------------------

def ascii_plot(report: LayerProbeReport):
    """Simple ASCII bar chart of probe accuracy by layer."""
    print("\n── Layer-wise Probing Profile ──────────────────────────────")
    print(f"  Model: {report.model_name}   L*(gc)={report.listen_layer_gc}")
    print(f"{'Layer':>6}  {'Phoneme Acc':>12}  {'Word Acc':>10}  {'Bar'}")
    print("  " + "-" * 60)

    for r in report.results:
        bar_len = int(r.phoneme_acc * 30)
        bar = "█" * bar_len + "░" * (30 - bar_len)
        marker = " ← L*(probe)" if r.layer == report.listen_layer_probe else ""
        marker_gc = " ← L*(gc)" if r.layer == report.listen_layer_gc else ""
        print(f"  {r.layer:>4}   {r.phoneme_acc:>10.3f}   {r.word_acc:>8.3f}  {bar}{marker}{marker_gc}")

    print()
    print(f"  {report.notes}")
    print()


# ---------------------------------------------------------------------------
# Optional matplotlib plot
# ---------------------------------------------------------------------------

def matplotlib_plot(report: LayerProbeReport, outpath: Optional[str] = None):
    import matplotlib.pyplot as plt

    layers = [r.layer for r in report.results]
    phoneme_accs = [r.phoneme_acc for r in report.results]
    word_accs = [r.word_acc for r in report.results]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(layers, phoneme_accs, "o-", label="Phoneme probe acc", color="steelblue")
    ax.plot(layers, word_accs, "s--", label="Word probe acc", color="coral")

    if report.listen_layer_probe is not None:
        ax.axvline(report.listen_layer_probe, color="steelblue", linestyle=":", alpha=0.7, label=f"L*(probe)={report.listen_layer_probe}")
    if report.listen_layer_gc is not None:
        ax.axvline(report.listen_layer_gc, color="red", linestyle="-", alpha=0.5, label=f"L*(gc)={report.listen_layer_gc}")

    # chance lines
    ax.axhline(1.0 / N_PHONEME_CLASSES, color="gray", linestyle=":", alpha=0.5, label=f"Chance (phoneme, 1/{N_PHONEME_CLASSES})")
    ax.axhline(1.0 / N_WORD_CLASSES, color="gray", linestyle="--", alpha=0.3, label=f"Chance (word, 1/{N_WORD_CLASSES})")

    ax.set_xlabel("Encoder Layer")
    ax.set_ylabel("Linear Probe Accuracy")
    ax.set_title(f"Q174 — Layer-wise Probing ({report.model_name})\n{report.notes}")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    if outpath:
        plt.tight_layout()
        plt.savefig(outpath, dpi=150)
        print(f"[INFO] Saved plot to {outpath}")
    else:
        plt.tight_layout()
        plt.show()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Q174: Layer-wise Phoneme/Word Probing at Listen Layer")
    parser.add_argument("--mock", action="store_true", help="Use synthetic data (no GPU/audio required)")
    parser.add_argument("--model", default="whisper-base", help="Whisper model name (e.g. whisper-base)")
    parser.add_argument("--audio-dir", type=Path, default=None, help="Path to L2-ARCTIC audio files (.wav)")
    parser.add_argument("--n-samples", type=int, default=500, help="Synthetic samples per layer")
    parser.add_argument("--plot", action="store_true", help="Show matplotlib plot (requires display)")
    parser.add_argument("--out-json", type=Path, default=None, help="Save report JSON to path")
    args = parser.parse_args()

    model_name = args.model
    n_layers = ENCODER_LAYERS_BY_MODEL.get(model_name, 6)

    print(f"[Q174] Layer-wise Phoneme/Word Probing — {model_name} ({n_layers} encoder layers)")
    print(f"       Mode: {'mock (synthetic)' if args.mock else 'real (Tier 1)'}")
    print()

    if args.mock:
        listen_layer = KNOWN_LISTEN_LAYER.get(model_name, n_layers // 2)
        data = generate_synthetic_data(
            n_layers=n_layers,
            n_samples=args.n_samples,
            hidden_dim=512,
            listen_layer=listen_layer,
        )
        print(f"[INFO] Synthetic data generated: {args.n_samples} samples × {n_layers} layers")
    else:
        if args.audio_dir is None or not args.audio_dir.exists():
            print("[ERROR] --audio-dir must point to a directory with .wav files for real mode.")
            print("        Use --mock for synthetic baseline.")
            sys.exit(1)

        audio_paths = list(args.audio_dir.glob("**/*.wav"))
        if not audio_paths:
            print(f"[ERROR] No .wav files found in {args.audio_dir}")
            sys.exit(1)

        print(f"[INFO] Found {len(audio_paths)} .wav files in {args.audio_dir}")
        data = extract_whisper_activations(model_name, audio_paths)

    print("[INFO] Running linear probes...")
    report = run_probes(data, n_layers=n_layers, model_name=model_name, verbose=True)

    ascii_plot(report)

    # Summary
    print("── Summary ─────────────────────────────────────────────────")
    print(f"  Model:              {report.model_name}")
    print(f"  Encoder layers:     {report.n_encoder_layers}")
    print(f"  Listen Layer (probe inflection): {report.listen_layer_probe}")
    print(f"  Listen Layer (gc(k) / AND-frac): {report.listen_layer_gc}")
    print(f"  Profile aligned:    {report.profile_aligned}")
    print(f"  Verdict:            {report.notes}")
    print()

    # Save JSON
    if args.out_json:
        out = {
            "model": report.model_name,
            "n_encoder_layers": report.n_encoder_layers,
            "listen_layer_probe": report.listen_layer_probe,
            "listen_layer_gc": report.listen_layer_gc,
            "profile_aligned": report.profile_aligned,
            "notes": report.notes,
            "results": [
                {
                    "layer": r.layer,
                    "phoneme_acc": round(r.phoneme_acc, 4),
                    "word_acc": round(r.word_acc, 4),
                    "n_samples": r.n_samples,
                }
                for r in report.results
            ],
        }
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(out, indent=2))
        print(f"[INFO] Report saved to {args.out_json}")

    if args.plot:
        try:
            matplotlib_plot(report)
        except Exception as e:
            print(f"[WARN] Matplotlib plot failed: {e}")

    return report


if __name__ == "__main__":
    main()
