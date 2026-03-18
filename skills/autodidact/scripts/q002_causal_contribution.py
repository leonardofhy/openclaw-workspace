#!/usr/bin/env python3
"""
q002_causal_contribution.py
============================
Q002 -- Layer-wise Causal Contribution Test on Whisper-base

Tests the 'Triple Convergence' hypothesis: which encoder layers causally
contribute most to transcription?

Method: Activation Patching (Zero / Noise / Mean Ablation)
  For each encoder layer L:
    1. Run Whisper on test utterances -> baseline transcription
    2. Hook layer L output, replace activations with zeros / noise / mean
    3. Run Whisper with ablated layer -> degraded transcription
    4. Measure WER(ablated, baseline)
    5. Layer with highest WER increase = most causally important

Usage:
  python q002_causal_contribution.py [--model base] [--audio-dir /tmp] [--no-plot]

Background (Gap #1 -- Causal, Triple Convergence):
  Q001 showed weak linearity at layer 5 (cos_sim=0.155) -- representational.
  Q002 probes causality: removing a layer's contribution and observing which
  layer's removal degrades transcription the most.
"""

import argparse
import json
import os
import string
import subprocess
import sys

import numpy as np

# Test sentences
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
        description="Q002 -- Layer-wise Causal Contribution (Activation Patching)"
    )
    parser.add_argument(
        "--model", type=str, default="base",
        choices=["tiny", "base", "small"],
        help="Whisper model size (default: base)"
    )
    parser.add_argument(
        "--audio-dir", type=str, default="/tmp",
        help="Directory to write TTS WAV files (default: /tmp)"
    )
    parser.add_argument(
        "--no-plot", action="store_true",
        help="Skip ASCII plot"
    )
    parser.add_argument(
        "--output", type=str,
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "q002_results.json"),
        help="Path to write JSON results"
    )
    return parser.parse_args()


def check_deps():
    missing = []
    for pkg in ["whisper", "torch", "numpy"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[ERROR] Missing packages: {', '.join(missing)}")
        print(f"  Install: pip install {' '.join(missing)}")
        sys.exit(1)


def generate_tts(sentence: str, path: str) -> bool:
    """Generate 16-bit PCM WAV at 16 kHz via macOS say."""
    cmd = ["say", "-o", path, "--data-format=LEI16@16000", sentence]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30)
    except FileNotFoundError:
        print("  [ERROR] 'say' command not found -- macOS required")
        return False
    if result.returncode != 0:
        print(f"  [WARN] say failed: {result.stderr.decode().strip()}")
        return False
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        print(f"  [WARN] Empty or missing WAV: {path}")
        return False
    return True


def normalize_text(text: str) -> list:
    """Lowercase, strip punctuation, split into words."""
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    return text.split()


def edit_distance(a: list, b: list) -> int:
    """Levenshtein distance between two word lists."""
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


def word_error_rate(hypothesis: str, reference: str) -> float:
    """WER = edit_distance(hyp, ref) / max(len(ref), 1), capped at 1.0."""
    ref_words = normalize_text(reference)
    hyp_words = normalize_text(hypothesis)
    if not ref_words:
        return 1.0 if hyp_words else 0.0
    if not hyp_words:
        return 1.0
    return min(edit_distance(hyp_words, ref_words) / len(ref_words), 1.0)


def run_transcribe(model, audio_path: str) -> str:
    """Run model.transcribe, return stripped text or empty string."""
    try:
        result = model.transcribe(audio_path, language="en", fp16=False)
        return (result.get("text") or "").strip()
    except Exception as e:
        print(f"  [WARN] transcribe failed: {e}")
        return ""


def run_ablated_transcribe(model, audio_path: str, layer_idx: int, ablation_type: str) -> str:
    """
    Transcribe audio_path while ablating encoder.blocks[layer_idx].
    ablation_type: 'zero' | 'noise' | 'mean'
    """
    import torch

    def make_hook(atype):
        def hook(module, input, output):
            x = output[0] if isinstance(output, tuple) else output
            if atype == "zero":
                patched = torch.zeros_like(x)
            elif atype == "noise":
                mu = x.mean().item()
                sigma = max(x.std().item(), 1e-8)
                patched = torch.randn_like(x) * sigma + mu
            elif atype == "mean":
                patched = x.mean(dim=1, keepdim=True).expand_as(x).clone()
            else:
                patched = x
            if isinstance(output, tuple):
                return (patched,) + output[1:]
            return patched
        return hook

    block = model.encoder.blocks[layer_idx]
    handle = block.register_forward_hook(make_hook(ablation_type))
    try:
        text = run_transcribe(model, audio_path)
    finally:
        handle.remove()
    return text


def main():
    args = parse_args()
    check_deps()

    import whisper

    print(f"\n{'='*70}")
    print(f"  Q002 -- Layer-wise Causal Contribution (Activation Patching)")
    print(f"  Model: Whisper-{args.model}")
    print(f"{'='*70}")

    # 1. Load model
    print(f"\n[1] Loading Whisper-{args.model}...")
    model = whisper.load_model(args.model)
    model.encoder.train(False)
    n_layers = len(model.encoder.blocks)
    d_model = model.encoder.blocks[0].attn.query.in_features
    print(f"    {n_layers} encoder layers, d_model={d_model}")

    # 2. Generate TTS audio
    print(f"\n[2] Generating TTS audio ({len(SENTENCES)} sentences)...")
    os.makedirs(args.audio_dir, exist_ok=True)
    wav_paths = []
    for i, sent in enumerate(SENTENCES):
        path = os.path.join(args.audio_dir, f"q002_sent_{i}.wav")
        ok = generate_tts(sent, path)
        label = "OK" if ok else "FAIL"
        display = sent[:55] + "..." if len(sent) > 55 else sent
        print(f"    [{label}] sent_{i}: \"{display}\"")
        if ok:
            wav_paths.append((i, sent, path))

    if not wav_paths:
        print("[ERROR] No TTS audio generated. Aborting.")
        sys.exit(1)

    # 3. Baseline transcriptions
    print(f"\n[3] Baseline transcriptions...")
    baselines = {}
    for i, sent, path in wav_paths:
        text = run_transcribe(model, path)
        baselines[i] = text
        w = word_error_rate(text, sent)
        display = text[:60] if text else "(empty)"
        print(f"    sent_{i}  WER_ref={w:.3f}  \"{display}\"")

    # 4. Ablation loop
    n_runs = n_layers * len(ABLATION_TYPES) * len(wav_paths)
    print(f"\n[4] Ablation loop...")
    print(f"    {n_layers} layers x {len(ABLATION_TYPES)} types x {len(wav_paths)} utterances = {n_runs} runs")

    layer_results = {
        layer: {atype: [] for atype in ABLATION_TYPES}
        for layer in range(n_layers)
    }

    total_combos = n_layers * len(ABLATION_TYPES)
    run_num = 0
    for layer in range(n_layers):
        for atype in ABLATION_TYPES:
            run_num += 1
            print(f"    [{run_num:>3}/{total_combos}] layer={layer} type={atype}...", end=" ", flush=True)
            wers = []
            for i, sent, path in wav_paths:
                ablated = run_ablated_transcribe(model, path, layer, atype)
                baseline = baselines[i]
                w = word_error_rate(ablated, baseline)
                layer_results[layer][atype].append({
                    "sent_idx": i,
                    "baseline": baseline,
                    "ablated": ablated,
                    "wer_vs_baseline": round(w, 4),
                    "wer_vs_reference": round(word_error_rate(ablated, sent), 4),
                })
                wers.append(w)
            print(f"mean WER={np.mean(wers):.3f}")

    # 5. Aggregate
    print(f"\n[5] Aggregating results...")
    mean_wer = {}
    for layer in range(n_layers):
        mean_wer[layer] = {}
        for atype in ABLATION_TYPES:
            wers = [r["wer_vs_baseline"] for r in layer_results[layer][atype]]
            mean_wer[layer][atype] = round(float(np.mean(wers)), 4)

    critical_layers = {}
    for atype in ABLATION_TYPES:
        wers_by_layer = [mean_wer[layer][atype] for layer in range(n_layers)]
        critical_layers[atype] = int(np.argmax(wers_by_layer))

    # 6. Print results table
    if not args.no_plot:
        bar_scale = 40

        print(f"\n{'='*70}")
        print(f"  RESULTS -- Mean WER after Ablation (vs Baseline)")
        print(f"{'='*70}")
        print(f"  {'Layer':>6}  {'WER(zero)':>10}  {'WER(noise)':>10}  {'WER(mean)':>10}")
        print(f"  {'-'*52}")
        for layer in range(n_layers):
            z = mean_wer[layer]["zero"]
            n_ = mean_wer[layer]["noise"]
            m = mean_wer[layer]["mean"]
            peaks = [atype for atype, cl in critical_layers.items() if cl == layer]
            marker = "  <- PEAK(" + ",".join(peaks) + ")" if peaks else ""
            print(f"  Layer {layer:>2}:  {z:>10.4f}  {n_:>10.4f}  {m:>10.4f}{marker}")

        print(f"\n  Critical layers (most causally important by ablation type):")
        for atype in ABLATION_TYPES:
            cl = critical_layers[atype]
            w_ = mean_wer[cl][atype]
            print(f"    {atype:<6}: layer {cl}  (mean WER vs baseline = {w_:.4f})")

        # ASCII bar chart -- zero ablation
        print(f"\n  WER(zero ablation) per layer -- bar chart:")
        for layer in range(n_layers):
            w_ = mean_wer[layer]["zero"]
            bar_len = max(1, int(w_ * bar_scale))
            bar = "#" * bar_len
            marker = " <- PEAK" if layer == critical_layers["zero"] else ""
            print(f"    Layer {layer}: [{bar:<{bar_scale}}] {w_:.3f}{marker}")

        # Sample ablation output at critical layer
        cz = critical_layers["zero"]
        print(f"\n  Sample ablations at critical layer {cz} (zero ablation):")
        print(f"  {'':3}  {'Baseline':<42}  {'Ablated'}")
        print(f"  {'-'*88}")
        for r in layer_results[cz]["zero"]:
            b = r["baseline"][:40] if r["baseline"] else "(empty)"
            a = r["ablated"][:40] if r["ablated"] else "(empty)"
            print(f"  s{r['sent_idx']}:  {b:<42}  {a}  WER={r['wer_vs_baseline']:.3f}")

    # 7. Save JSON
    output_data = {
        "experiment": "Q002_causal_contribution",
        "model": f"whisper-{args.model}",
        "n_layers": n_layers,
        "d_model": d_model,
        "ablation_types": ABLATION_TYPES,
        "sentences": SENTENCES,
        "n_sentences_used": len(wav_paths),
        "baseline_transcriptions": {str(i): baselines[i] for i in baselines},
        "mean_wer_per_layer": {str(layer): mean_wer[layer] for layer in range(n_layers)},
        "critical_layers": critical_layers,
        "per_layer_details": {
            str(layer): {atype: layer_results[layer][atype] for atype in ABLATION_TYPES}
            for layer in range(n_layers)
        },
    }

    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\n  Results written -> {args.output}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
