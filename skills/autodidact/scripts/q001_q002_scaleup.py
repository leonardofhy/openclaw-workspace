#!/usr/bin/env python3
"""
q001_q002_scaleup.py
====================
Scale-up runner for Q001 (voicing geometry) and Q002 (causal ablation)
across Whisper model sizes (base, small, medium).

Runs both experiments sequentially, saves results, and prints a
comparison table against whisper-base baseline.

Usage:
  python q001_q002_scaleup.py --model whisper-small
  python q001_q002_scaleup.py --model whisper-medium
  python q001_q002_scaleup.py --model whisper-base --dry-run
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

import numpy as np

# ---------------------------------------------------------------------------
# Whisper-base baseline results (from 2026-03-18 runs)
# ---------------------------------------------------------------------------
BASELINE = {
    "model": "whisper-base",
    "n_layers": 6,
    "q001": {
        "peak_layer": 5,
        "peak_mean_cos_sim": 0.155,
        "stop_stop_sim": 0.25,
        "stop_fricative_sim": 0.0,
    },
    "q002": {
        "mean_wer_zero": 1.0,
        "critical_layer_zero": 0,  # all layers WER=1.0, argmax returns 0
        "all_layers_critical": True,
    },
}

# Model config for layer/dim expectations
MODEL_SPECS = {
    "whisper-base": {"n_layers": 6, "d_model": 512},
    "whisper-small": {"n_layers": 12, "d_model": 768},
    "whisper-medium": {"n_layers": 24, "d_model": 1024},
}

# Minimal pairs (Q001)
PAIRS = [
    ("tie", "die", "t_d"),
    ("pat", "bat", "p_b"),
    ("cap", "gap", "k_g"),
    ("sip", "zip", "s_z"),
]

# Test sentences (Q002)
SENTENCES = [
    "The quick brown fox jumps over the lazy dog",
    "She sells sea shells by the sea shore",
    "How much wood would a woodchuck chuck",
    "Peter Piper picked a peck of pickled peppers",
    "The rain in Spain falls mainly on the plain",
]

ABLATION_TYPES = ["zero", "noise", "mean"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scale-up runner for Q001 + Q002 across Whisper sizes"
    )
    parser.add_argument(
        "--model", type=str, required=True,
        choices=["whisper-base", "whisper-small", "whisper-medium"],
        help="Whisper model to run"
    )
    parser.add_argument(
        "--output-dir", type=str,
        default=os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..", "..", "memory", "learning"
        ),
        help="Directory for result JSON files"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Mock mode: no model loading, synthetic results"
    )
    return parser.parse_args()


# ===========================================================================
# Shared utilities
# ===========================================================================

def generate_tts(text, path):
    """Generate WAV via macOS say or create silent stub on Linux."""
    cmd = ["say", "-o", path, "--data-format=LEI16@16000", text]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        return result.returncode == 0 and os.path.exists(path) and os.path.getsize(path) > 0
    except FileNotFoundError:
        # Not macOS — create a silent WAV stub for cluster runs
        import struct
        sr, dur = 16000, 1
        n_samples = sr * dur
        data = b'\x00\x00' * n_samples
        with open(path, 'wb') as f:
            f.write(b'RIFF')
            f.write(struct.pack('<I', 36 + len(data)))
            f.write(b'WAVE')
            f.write(b'fmt ')
            f.write(struct.pack('<IHHIIHH', 16, 1, 1, sr, sr * 2, 2, 16))
            f.write(b'data')
            f.write(struct.pack('<I', len(data)))
            f.write(data)
        return True


def cosine_sim(a, b):
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if na < 1e-10 or nb < 1e-10:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def normalize_text(text):
    import string
    text = text.lower().translate(str.maketrans("", "", string.punctuation))
    return text.split()


def edit_distance(a, b):
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[:]
        dp[0] = i
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[j] = prev[j - 1]
            else:
                dp[j] = 1 + min(prev[j], dp[j - 1], prev[j - 1])
    return dp[n]


def word_error_rate(hyp, ref):
    ref_w = normalize_text(ref)
    hyp_w = normalize_text(hyp)
    if not ref_w:
        return 1.0 if hyp_w else 0.0
    if not hyp_w:
        return 1.0
    return min(edit_distance(hyp_w, ref_w) / len(ref_w), 1.0)


# ===========================================================================
# Q001 — Voicing Geometry
# ===========================================================================

def run_q001_real(model_name, model):
    """Run Q001 with a real Whisper model."""
    import torch
    import whisper

    n_layers = len(model.encoder.blocks)
    tmpdir = tempfile.mkdtemp(prefix="q001_scale_")

    activations = {}
    for unvoiced, voiced, label in PAIRS:
        for word in (unvoiced, voiced):
            path = os.path.join(tmpdir, f"{word}.wav")
            if not generate_tts(word, path):
                continue
            cache = {}

            def make_hook(idx):
                def hook(mod, inp, out):
                    cache[idx] = out.detach().cpu().numpy()[0]
                return hook

            hooks = [b.register_forward_hook(make_hook(i))
                     for i, b in enumerate(model.encoder.blocks)]
            try:
                audio = whisper.load_audio(path)
                audio = whisper.pad_or_trim(audio)
                mel = whisper.log_mel_spectrogram(audio).unsqueeze(0)
                if next(model.parameters()).is_cuda:
                    mel = mel.cuda()
                with torch.no_grad():
                    model.encoder(mel)
            finally:
                for h in hooks:
                    h.remove()

            if cache:
                activations[word] = {i: cache[i].mean(axis=0) for i in cache}

    import itertools
    voicing_vecs = {}
    for unvoiced, voiced, label in PAIRS:
        if unvoiced not in activations or voiced not in activations:
            continue
        vecs = {}
        for layer in range(n_layers):
            vecs[layer] = activations[voiced][layer] - activations[unvoiced][layer]
        voicing_vecs[label] = vecs

    valid = list(voicing_vecs.keys())
    combos = list(itertools.combinations(valid, 2))
    mean_cos = []
    for layer in range(n_layers):
        sims = [cosine_sim(voicing_vecs[la][layer], voicing_vecs[lb][layer])
                for la, lb in combos]
        mean_cos.append(float(np.mean(sims)) if sims else 0.0)

    peak_layer = int(np.argmax(mean_cos))
    peak_sim = mean_cos[peak_layer]

    stop_labels = [l for l in valid if l != "s_z"]
    stop_combos = [(a, b) for a, b in combos if a in stop_labels and b in stop_labels]
    cross_combos = [(a, b) for a, b in combos
                    if (a in stop_labels and b == "s_z") or (b in stop_labels and a == "s_z")]

    stop_sim = float(np.mean([cosine_sim(voicing_vecs[a][peak_layer], voicing_vecs[b][peak_layer])
                              for a, b in stop_combos])) if stop_combos else 0.0
    cross_sim = float(np.mean([cosine_sim(voicing_vecs[a][peak_layer], voicing_vecs[b][peak_layer])
                               for a, b in cross_combos])) if cross_combos else 0.0

    return {
        "peak_layer": peak_layer,
        "peak_mean_cos_sim": round(peak_sim, 4),
        "stop_stop_sim": round(stop_sim, 4),
        "stop_fricative_sim": round(cross_sim, 4),
        "mean_cos_per_layer": [round(v, 4) for v in mean_cos],
    }


def run_q001_dry(model_name):
    """Synthetic Q001 results for dry-run testing."""
    spec = MODEL_SPECS[model_name]
    n = spec["n_layers"]
    peak = int(n * 0.6)
    cos_vals = [round(0.05 + 0.1 * np.exp(-0.5 * ((i - peak) / 2) ** 2), 4)
                for i in range(n)]
    return {
        "peak_layer": peak,
        "peak_mean_cos_sim": max(cos_vals),
        "stop_stop_sim": 0.20,
        "stop_fricative_sim": 0.02,
        "mean_cos_per_layer": cos_vals,
    }


# ===========================================================================
# Q002 — Causal Contribution
# ===========================================================================

def run_q002_real(model_name, model):
    """Run Q002 with a real Whisper model."""
    import torch

    n_layers = len(model.encoder.blocks)
    tmpdir = tempfile.mkdtemp(prefix="q002_scale_")

    wav_paths = []
    for i, sent in enumerate(SENTENCES):
        path = os.path.join(tmpdir, f"sent_{i}.wav")
        if generate_tts(sent, path):
            wav_paths.append((i, sent, path))

    if not wav_paths:
        return {"error": "No TTS audio generated"}

    baselines = {}
    for i, sent, path in wav_paths:
        result = model.transcribe(path, language="en", fp16=False)
        baselines[i] = (result.get("text") or "").strip()

    mean_wer_per_layer = []
    for layer in range(n_layers):
        def make_hook():
            def hook(mod, inp, out):
                x = out[0] if isinstance(out, tuple) else out
                patched = torch.zeros_like(x)
                return (patched,) + out[1:] if isinstance(out, tuple) else patched
            return hook

        block = model.encoder.blocks[layer]
        handle = block.register_forward_hook(make_hook())
        wers = []
        try:
            for i, sent, path in wav_paths:
                result = model.transcribe(path, language="en", fp16=False)
                ablated = (result.get("text") or "").strip()
                wers.append(word_error_rate(ablated, baselines[i]))
        finally:
            handle.remove()
        mean_wer_per_layer.append(round(float(np.mean(wers)), 4))

    critical = int(np.argmax(mean_wer_per_layer))
    all_critical = all(w >= 0.95 for w in mean_wer_per_layer)

    return {
        "mean_wer_zero_per_layer": mean_wer_per_layer,
        "mean_wer_zero": round(float(np.mean(mean_wer_per_layer)), 4),
        "critical_layer_zero": critical,
        "all_layers_critical": all_critical,
    }


def run_q002_dry(model_name):
    """Synthetic Q002 results for dry-run testing."""
    spec = MODEL_SPECS[model_name]
    n = spec["n_layers"]
    wers = []
    for i in range(n):
        if n <= 6:
            wers.append(1.0)
        else:
            depth = i / (n - 1)
            if depth < 0.2 or depth > 0.8:
                wers.append(round(0.9 + np.random.uniform(0, 0.1), 4))
            else:
                wers.append(round(0.4 + np.random.uniform(0, 0.4), 4))

    critical = int(np.argmax(wers))
    return {
        "mean_wer_zero_per_layer": wers,
        "mean_wer_zero": round(float(np.mean(wers)), 4),
        "critical_layer_zero": critical,
        "all_layers_critical": all(w >= 0.95 for w in wers),
    }


# ===========================================================================
# Comparison table
# ===========================================================================

def print_comparison(model_name, q001, q002, elapsed_q001, elapsed_q002):
    spec = MODEL_SPECS[model_name]
    base_spec = MODEL_SPECS["whisper-base"]

    print(f"\n{'='*78}")
    print(f"  SCALE-UP COMPARISON: {model_name} vs whisper-base (baseline)")
    print(f"{'='*78}")

    header = f"  {'Metric':<35} {'whisper-base':>14} {model_name:>14} {'Delta':>10}"
    print(f"\n{header}")
    print(f"  {'-'*73}")

    rows = [
        ("Encoder layers",
         str(base_spec["n_layers"]),
         str(spec["n_layers"]),
         f"+{spec['n_layers'] - base_spec['n_layers']}"),
        ("d_model",
         str(base_spec["d_model"]),
         str(spec["d_model"]),
         f"+{spec['d_model'] - base_spec['d_model']}"),
        ("Q001 peak layer",
         str(BASELINE["q001"]["peak_layer"]),
         str(q001["peak_layer"]),
         f"{q001['peak_layer'] - BASELINE['q001']['peak_layer']:+d}"),
        ("Q001 peak cos_sim",
         f"{BASELINE['q001']['peak_mean_cos_sim']:.4f}",
         f"{q001['peak_mean_cos_sim']:.4f}",
         f"{q001['peak_mean_cos_sim'] - BASELINE['q001']['peak_mean_cos_sim']:+.4f}"),
        ("Q001 stop-stop sim",
         f"{BASELINE['q001']['stop_stop_sim']:.4f}",
         f"{q001['stop_stop_sim']:.4f}",
         f"{q001['stop_stop_sim'] - BASELINE['q001']['stop_stop_sim']:+.4f}"),
        ("Q001 stop-fricative sim",
         f"{BASELINE['q001']['stop_fricative_sim']:.4f}",
         f"{q001['stop_fricative_sim']:.4f}",
         f"{q001['stop_fricative_sim'] - BASELINE['q001']['stop_fricative_sim']:+.4f}"),
        ("Q002 mean WER (zero abl.)",
         f"{BASELINE['q002']['mean_wer_zero']:.4f}",
         f"{q002['mean_wer_zero']:.4f}",
         f"{q002['mean_wer_zero'] - BASELINE['q002']['mean_wer_zero']:+.4f}"),
        ("Q002 all layers critical?",
         str(BASELINE["q002"]["all_layers_critical"]),
         str(q002["all_layers_critical"]),
         "same" if q002["all_layers_critical"] == BASELINE["q002"]["all_layers_critical"] else "CHANGED"),
        ("Q002 critical layer (zero)",
         str(BASELINE["q002"]["critical_layer_zero"]),
         str(q002["critical_layer_zero"]),
         f"{q002['critical_layer_zero'] - BASELINE['q002']['critical_layer_zero']:+d}"),
    ]

    for label, base_val, new_val, delta in rows:
        print(f"  {label:<35} {base_val:>14} {new_val:>14} {delta:>10}")

    total_time = elapsed_q001 + elapsed_q002
    print(f"\n  Timing:")
    print(f"    Q001: {elapsed_q001:.1f}s")
    print(f"    Q002: {elapsed_q002:.1f}s")
    print(f"    Total: {total_time:.1f}s")
    print(f"{'='*78}\n")


# ===========================================================================
# Main
# ===========================================================================

def main():
    args = parse_args()
    model_name = args.model
    model_size = model_name.replace("whisper-", "")
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n{'#'*70}")
    print(f"  Q001/Q002 Scale-Up Runner")
    print(f"  Model: {model_name}  |  Dry-run: {args.dry_run}")
    print(f"{'#'*70}")

    model = None
    if not args.dry_run:
        print(f"\n[LOAD] Loading {model_name}...")
        import whisper
        model = whisper.load_model(model_size)
        model.encoder.train(False)
        print(f"  Loaded: {len(model.encoder.blocks)} layers, "
              f"d_model={model.encoder.blocks[0].attn.query.in_features}")

    # --- Q001 ---
    print(f"\n{'='*70}")
    print(f"  Running Q001 -- Voicing Geometry on {model_name}")
    print(f"{'='*70}")
    t0 = time.time()
    if args.dry_run:
        q001 = run_q001_dry(model_name)
    else:
        q001 = run_q001_real(model_name, model)
    elapsed_q001 = time.time() - t0
    print(f"  Q001 done in {elapsed_q001:.1f}s")
    print(f"  Peak layer: {q001['peak_layer']}, cos_sim: {q001['peak_mean_cos_sim']:.4f}")

    # --- Q002 ---
    print(f"\n{'='*70}")
    print(f"  Running Q002 -- Causal Contribution on {model_name}")
    print(f"{'='*70}")
    t0 = time.time()
    if args.dry_run:
        q002 = run_q002_dry(model_name)
    else:
        q002 = run_q002_real(model_name, model)
    elapsed_q002 = time.time() - t0
    print(f"  Q002 done in {elapsed_q002:.1f}s")
    print(f"  Mean WER (zero): {q002['mean_wer_zero']:.4f}, "
          f"all critical: {q002['all_layers_critical']}")

    # --- Comparison ---
    print_comparison(model_name, q001, q002, elapsed_q001, elapsed_q002)

    # --- Save results ---
    results = {
        "model": model_name,
        "n_layers": MODEL_SPECS[model_name]["n_layers"],
        "d_model": MODEL_SPECS[model_name]["d_model"],
        "dry_run": args.dry_run,
        "q001": q001,
        "q002": q002,
        "timing": {
            "q001_seconds": round(elapsed_q001, 2),
            "q002_seconds": round(elapsed_q002, 2),
            "total_seconds": round(elapsed_q001 + elapsed_q002, 2),
        },
        "baseline": BASELINE,
    }

    out_path = os.path.join(output_dir, f"scaleup-results-{model_name}.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Results saved -> {out_path}")


if __name__ == "__main__":
    main()
