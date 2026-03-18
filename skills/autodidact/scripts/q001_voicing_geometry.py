#!/usr/bin/env python3
"""
q001_voicing_geometry.py
========================
Q001 -- Phonological Vector Geometry on Whisper-base

Steps:
  1. Generate minimal pairs via macOS TTS (say command)
  2. Load Whisper encoder, hook all layers
  3. Compute voicing_vector = mean(h(voiced)) - mean(h(unvoiced)) per layer
  4. Cross-pair cosine similarity per layer -> peak layer detection
  5. Write results to JSON, print readable summary

Usage:
  python q001_voicing_geometry.py [--model base] [--output PATH]

Background (Gap #18):
  Does linear phonological structure in S3M encoders survive?
  Voicing vectors from different consonant pairs should point in the same
  direction if phonological features are linearly organized in the encoder.

Reference: Choi et al. 2602.18899 (phonological linearity in S3M encoders)
"""

import argparse
import itertools
import json
import os
import subprocess
import sys
import tempfile

import numpy as np

# Minimal pairs: (unvoiced_word, voiced_word, pair_label)
# Voicing contrast: [t/d], [p/b], [k/g], [s/z]
PAIRS = [
    ("tie", "die", "t_d"),
    ("pat", "bat", "p_b"),
    ("cap", "gap", "k_g"),
    ("sip", "zip", "s_z"),
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Q001 -- Voicing vector geometry in Whisper encoder"
    )
    parser.add_argument(
        "--model", type=str, default="base", choices=["tiny", "base", "small"],
        help="Whisper model size (default: base)"
    )
    parser.add_argument(
        "--output", type=str,
        default=os.path.join(os.path.dirname(__file__), "q001_results.json"),
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


def generate_tts(word: str, path: str) -> bool:
    """Generate 16-bit PCM WAV at 16 kHz via macOS say. Returns True on success."""
    cmd = ["say", "-o", path, "--data-format=LEI16@16000", word]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=15)
    except FileNotFoundError:
        print("  [ERROR] 'say' command not found -- macOS required")
        return False
    if result.returncode != 0:
        print(f"  [WARN] say failed for '{word}': {result.stderr.decode().strip()}")
        return False
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        print(f"  [WARN] Empty or missing WAV for '{word}'")
        return False
    return True


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity. Returns 0.0 for zero vectors."""
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na < 1e-10 or nb < 1e-10:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def extract_mean_activations(model, audio_path: str) -> dict:
    """
    Run Whisper encoder on audio_path.
    Returns {layer_idx: mean_activation_over_time [d_model]}.
    """
    import torch
    import whisper

    cache: dict = {}

    def make_hook(layer_idx: int):
        def hook(module, input, output):
            # output shape: [batch=1, T, d_model]
            cache[layer_idx] = output.detach().cpu().numpy()[0]  # [T, d_model]
        return hook

    encoder = model.encoder
    hooks = [block.register_forward_hook(make_hook(i))
             for i, block in enumerate(encoder.blocks)]
    try:
        audio = whisper.load_audio(audio_path)
        audio = whisper.pad_or_trim(audio)
        mel = whisper.log_mel_spectrogram(audio).unsqueeze(0)
        with torch.no_grad():
            encoder(mel)
    finally:
        for h in hooks:
            h.remove()

    if not cache:
        return {}
    # Mean over time frames -> [d_model] per layer
    return {i: cache[i].mean(axis=0) for i in cache}


def _interpret_sim(sim: float) -> str:
    if sim > 0.7:
        return "strong"
    elif sim > 0.4:
        return "moderate"
    elif sim > 0.1:
        return "weak"
    elif sim > -0.1:
        return "orthogonal"
    else:
        return "anti-correlated"


def main():
    args = parse_args()
    check_deps()

    import whisper

    print(f"\n{'='*65}")
    print(f"  Q001 -- Phonological Vector Geometry (Gap #18)")
    print(f"  Model: Whisper-{args.model}")
    print(f"{'='*65}")

    # -- 1. Load model -------------------------------------------------------
    print(f"\n[1] Loading Whisper-{args.model}...")
    model = whisper.load_model(args.model)
    model.encoder.train(False)   # inference mode (equivalent to .eval())
    n_layers = len(model.encoder.blocks)
    d_model = model.encoder.blocks[0].attn.query.in_features
    print(f"    {n_layers} encoder layers, d_model={d_model}")

    # -- 2. Generate TTS audio -----------------------------------------------
    print(f"\n[2] Generating TTS audio ({len(PAIRS)} pairs, {len(PAIRS)*2} words)...")
    tmpdir = tempfile.mkdtemp(prefix="q001_")
    wav_paths: dict = {}

    for unvoiced, voiced, label in PAIRS:
        for word in (unvoiced, voiced):
            path = os.path.join(tmpdir, f"{word}.wav")
            ok = generate_tts(word, path)
            status = "OK" if ok else "FAIL"
            print(f"    [{status}] '{word}' -> {path}")
            if ok:
                wav_paths[word] = path

    # -- 3. Extract activations ----------------------------------------------
    print(f"\n[3] Extracting encoder activations...")
    activations: dict = {}  # word -> {layer: [d_model]}
    for word, path in wav_paths.items():
        print(f"    '{word}'...", end=" ", flush=True)
        acts = extract_mean_activations(model, path)
        if acts:
            activations[word] = acts
            print("done")
        else:
            print("EMPTY -- skipped")

    # -- 4. Compute voicing vectors per layer --------------------------------
    print(f"\n[4] Computing voicing vectors (voiced - unvoiced)...")
    voicing_vecs: dict = {}   # label -> {layer: [d_model]}
    voicing_norms: dict = {}  # label -> [norm per layer]

    for unvoiced, voiced, label in PAIRS:
        if unvoiced not in activations or voiced not in activations:
            print(f"    SKIP {label}: missing activations")
            continue
        vecs = {}
        norms = []
        for layer in range(n_layers):
            h_voiced   = activations[voiced][layer]
            h_unvoiced = activations[unvoiced][layer]
            vec = h_voiced - h_unvoiced
            vecs[layer] = vec
            norms.append(float(np.linalg.norm(vec)))
        voicing_vecs[label] = vecs
        voicing_norms[label] = norms
        peak = int(np.argmax(norms))
        print(f"    {label}: voicing vector norm peaks at layer {peak} ({norms[peak]:.3f})")

    valid_labels = list(voicing_vecs.keys())
    if len(valid_labels) < 2:
        print("[ERROR] Need >= 2 valid pairs for cosine similarity. Aborting.")
        sys.exit(1)

    # -- 5. Cross-pair cosine similarity per layer ---------------------------
    print(f"\n[5] Computing cross-pair cosine similarities...")
    pair_combos = list(itertools.combinations(valid_labels, 2))

    cos_per_layer: dict = {}  # layer -> {combo_key: float}
    for layer in range(n_layers):
        cos_per_layer[layer] = {}
        for la, lb in pair_combos:
            key = f"{la}_vs_{lb}"
            cos_per_layer[layer][key] = cosine_sim(
                voicing_vecs[la][layer], voicing_vecs[lb][layer]
            )

    mean_cos_per_layer = [
        float(np.mean(list(cos_per_layer[layer].values())))
        for layer in range(n_layers)
    ]
    peak_layer = int(np.argmax(mean_cos_per_layer))

    # Activation norms per layer (averaged across all words)
    activation_norms_per_layer = []
    for layer in range(n_layers):
        norms_l = [float(np.linalg.norm(activations[w][layer])) for w in activations]
        activation_norms_per_layer.append(float(np.mean(norms_l)))

    # -- 6. Print summary ----------------------------------------------------
    print(f"\n{'='*65}")
    print(f"  RESULTS -- Voicing Direction Consistency Across Pairs")
    print(f"{'='*65}")
    print(f"\n  Pairs: {', '.join(valid_labels)}")
    print(f"  Comparisons: {', '.join(f'{la}_vs_{lb}' for la, lb in pair_combos)}")
    print(f"\n  Layer-wise mean cosine similarity (voicing vector alignment):")
    print(f"  {'Layer':>6}  {'MeanCosSim':>12}  Bar (0 -> 1)")
    print(f"  {'-'*52}")
    for layer in range(n_layers):
        val = mean_cos_per_layer[layer]
        bar_len = max(0, int(val * 30))
        bar = "#" * bar_len
        marker = "  <- PEAK" if layer == peak_layer else ""
        print(f"  Layer {layer:>2}:  {val:>12.4f}  {bar}{marker}")

    print(f"\n  Peak layer: {peak_layer}  "
          f"(mean cosine sim = {mean_cos_per_layer[peak_layer]:.4f})")

    print(f"\n  Per-pair cosine similarities at peak layer {peak_layer}:")
    for la, lb in pair_combos:
        key = f"{la}_vs_{lb}"
        sim = cos_per_layer[peak_layer][key]
        print(f"    {key:<25} = {sim:+.4f}  [{_interpret_sim(sim)}]")

    # Manner-grouped interpretation
    stop_labels  = [l for l in valid_labels if l != "s_z"]
    stop_combos  = [(la, lb) for la, lb in pair_combos
                    if la in stop_labels and lb in stop_labels]
    cross_combos = [(la, lb) for la, lb in pair_combos
                    if (la in stop_labels and lb == "s_z") or
                       (lb in stop_labels and la == "s_z")]

    print(f"\n  Interpretation:")
    if stop_combos:
        stop_mean = float(np.mean([
            cos_per_layer[peak_layer][f"{la}_vs_{lb}"] for la, lb in stop_combos
        ]))
        print(f"    Stop-stop voicing consistency:    {stop_mean:+.4f}  [{_interpret_sim(stop_mean)}]")
        if stop_mean > 0.3:
            print(f"    >> Voicing direction SHARED across stops -> linear phonological structure")
        else:
            print(f"    >> Voicing direction PAIR-SPECIFIC -> limited stop generalization")

    if cross_combos:
        cross_mean = float(np.mean([
            cos_per_layer[peak_layer][f"{la}_vs_{lb}"] for la, lb in cross_combos
        ]))
        print(f"    Cross-manner (stop vs fricative): {cross_mean:+.4f}  [{_interpret_sim(cross_mean)}]")
        if cross_mean > 0.2:
            print(f"    >> Voicing generalizes ACROSS MANNER (stops + fricative share direction)")
        else:
            print(f"    >> Voicing does NOT generalize across manner of articulation")

    # -- 7. Write JSON results -----------------------------------------------
    results = {
        "experiment": "Q001_voicing_geometry",
        "model": f"whisper-{args.model}",
        "n_layers": n_layers,
        "d_model": d_model,
        "pairs": [
            {"unvoiced": u, "voiced": v, "label": l}
            for u, v, l in PAIRS if l in valid_labels
        ],
        "peak_layer": peak_layer,
        "peak_mean_cosine_sim": mean_cos_per_layer[peak_layer],
        "mean_cosine_sim_per_layer": mean_cos_per_layer,
        "activation_norms_per_layer": activation_norms_per_layer,
        "cosine_sim_matrix": {
            str(layer): cos_per_layer[layer] for layer in range(n_layers)
        },
        "voicing_vector_norms_per_layer": {
            label: voicing_norms[label] for label in valid_labels
        },
    }

    out_path = args.output
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n  Results written -> {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
