#!/usr/bin/env python3
"""
Synthetic Stimuli Generator for gc(k) Harness
Track T3: Listen vs Guess (Paper A)

Generates phoneme-contrastive activation pairs that mimic Whisper encoder
hidden states for "listen" vs "guess" conditions. Enables CPU testing of
the full gc(k) pipeline without real audio or a loaded model.

Phoneme contrast pairs model the key experimental condition:
    - "listen" condition: acoustic evidence is unambiguous → activations
      differ significantly between phoneme classes
    - "guess" condition: acoustics degraded/masked → activations converge
      toward language-prior-driven representations

Usage:
    from synthetic_stimuli import generate_activation_pair, StimuliConfig
    clean_acts, noisy_acts = generate_activation_pair(config)

    # Or CLI:
    python3 synthetic_stimuli.py --contrast vowel_consonant --snr-db 5
    python3 synthetic_stimuli.py --list-contrasts
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from typing import Literal

import numpy as np


# ---------------------------------------------------------------------------
# Phoneme contrast definitions
# ---------------------------------------------------------------------------

# Each contrast is defined by a mean activation vector pattern for the
# "clean" (signal-present) and "degraded" (guess-inducing) conditions.
# Dimensions are abstract (not tied to real Whisper weights) but follow
# known patterns from mechanistic interpretability:
#   - Early encoder layers: frequency/spectral features
#   - Mid encoder: phonetic class distinctions
#   - Late encoder/decoder: lexical/language-prior driven

PHONEME_CONTRASTS: dict[str, dict] = {
    "vowel_consonant": {
        "description": "Vowel vs. stop consonant (/a/ vs. /t/)",
        "clean_signal_strength": 0.85,   # high SNR: activations well-separated
        "noisy_signal_strength": 0.15,   # low SNR: converge to language prior
        "encoder_profile": "spectral_formant",  # formant-driven early layers
        "decoder_collapse_rate": 0.7,    # how fast decoder discards audio signal
    },
    "voiced_voiceless": {
        "description": "Voiced vs. voiceless stop (/b/ vs. /p/)",
        "clean_signal_strength": 0.70,
        "noisy_signal_strength": 0.25,   # voicing cue survives some noise
        "encoder_profile": "voicing_periodic",
        "decoder_collapse_rate": 0.6,
    },
    "place_of_articulation": {
        "description": "Bilabial vs. alveolar (/b/ vs. /d/)",
        "clean_signal_strength": 0.60,   # subtle acoustic cue
        "noisy_signal_strength": 0.30,   # guessing is common here
        "encoder_profile": "formant_transition",
        "decoder_collapse_rate": 0.8,    # language prior dominates quickly
    },
    "tonal_lexical": {
        "description": "Tonal disambiguation (Mandarin tone 1 vs. tone 4)",
        "clean_signal_strength": 0.75,
        "noisy_signal_strength": 0.20,
        "encoder_profile": "f0_trajectory",
        "decoder_collapse_rate": 0.75,
    },
    "noise_only": {
        "description": "Pure noise baseline (no phonemic content)",
        "clean_signal_strength": 0.90,
        "noisy_signal_strength": 0.05,   # almost pure language prior
        "encoder_profile": "flat",
        "decoder_collapse_rate": 0.95,
    },
}


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class StimuliConfig:
    """Configuration for synthetic activation pair generation."""
    n_encoder_layers: int = 6
    n_decoder_layers: int = 6
    hidden_dim: int = 64        # activation vector width (mock Whisper-tiny: 384, but 64 for speed)
    seq_len: int = 8            # sequence length (time steps)
    contrast: str = "vowel_consonant"
    snr_db: float = 10.0        # signal-to-noise ratio for "clean" condition
    noisy_snr_db: float = -5.0  # SNR for "noisy/guess" condition
    seed: int = 42
    # Derived
    extra_fields: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.contrast not in PHONEME_CONTRASTS:
            raise ValueError(
                f"Unknown contrast '{self.contrast}'. "
                f"Available: {list(PHONEME_CONTRASTS.keys())}"
            )


# ---------------------------------------------------------------------------
# Core generators
# ---------------------------------------------------------------------------

def _snr_to_noise_scale(snr_db: float, signal_scale: float = 1.0) -> float:
    """Convert SNR in dB to additive noise standard deviation."""
    snr_linear = 10 ** (snr_db / 10)
    return signal_scale / (snr_linear ** 0.5)


def _encoder_profile_weights(
    profile: str, n_layers: int, hidden_dim: int, rng: np.random.Generator
) -> np.ndarray:
    """
    Layer-wise weights controlling how strongly the phonemic signal
    is encoded across encoder layers. Shape: (n_layers, hidden_dim).

    Different profiles reflect different acoustic feature processing:
    - spectral_formant: peaks in mid layers (formant analysis)
    - voicing_periodic: peaks early (low-frequency periodicity)
    - formant_transition: distributed across all encoder layers
    - f0_trajectory: peaks late in encoder (global pitch contour)
    - flat: uniform (noise baseline)
    """
    base = rng.standard_normal((n_layers, hidden_dim)) * 0.1

    if profile == "spectral_formant":
        # Bell-shaped peaking at layer n//2
        peak = n_layers // 2
        layer_scale = np.exp(-0.5 * ((np.arange(n_layers) - peak) / 1.5) ** 2)
    elif profile == "voicing_periodic":
        # Decaying: strongest in early layers
        layer_scale = np.exp(-np.arange(n_layers) * 0.4)
    elif profile == "formant_transition":
        # Roughly uniform, slight early bias
        layer_scale = np.ones(n_layers) * 0.8 + rng.uniform(0, 0.2, n_layers)
    elif profile == "f0_trajectory":
        # Late-peaked: F0 requires temporal integration
        layer_scale = np.linspace(0.2, 1.0, n_layers) ** 2
    else:  # flat
        layer_scale = np.ones(n_layers) * 0.3

    # Phoneme-direction: a fixed unit vector in hidden_dim space
    phoneme_dir = rng.standard_normal(hidden_dim)
    phoneme_dir /= np.linalg.norm(phoneme_dir) + 1e-8

    for k in range(n_layers):
        base[k] += layer_scale[k] * phoneme_dir

    return base, phoneme_dir  # (n_layers, hidden_dim), (hidden_dim,)


def generate_activation_pair(
    config: StimuliConfig,
) -> tuple[dict[str, list], dict[str, list]]:
    """
    Generate (clean_activations, noisy_activations) layer dictionaries.

    Each dict maps layer_index (int) → np.ndarray of shape (seq_len, hidden_dim).

    "Clean" activations have strong phonemic signal (high SNR).
    "Noisy" activations are degraded toward language-prior noise floor.

    Returns compatible format with gc_eval.py's causal patching loop.
    """
    rng = np.random.default_rng(config.seed)
    contrast_spec = PHONEME_CONTRASTS[config.contrast]

    n_enc = config.n_encoder_layers
    n_dec = config.n_decoder_layers
    H = config.hidden_dim
    T = config.seq_len

    clean_signal_str = contrast_spec["clean_signal_strength"]
    noisy_signal_str = contrast_spec["noisy_signal_strength"]
    dec_collapse = contrast_spec["decoder_collapse_rate"]
    profile = contrast_spec["encoder_profile"]

    # Build encoder profile weights
    enc_weights, phoneme_dir = _encoder_profile_weights(profile, n_enc, H, rng)

    # Language-prior "guess" vector (orthogonal to phoneme direction)
    noise_dir = rng.standard_normal(H)
    noise_dir -= noise_dir.dot(phoneme_dir) * phoneme_dir  # Gram-Schmidt
    noise_dir /= np.linalg.norm(noise_dir) + 1e-8

    clean_acts: dict[int, np.ndarray] = {}
    noisy_acts: dict[int, np.ndarray] = {}

    # --- Encoder layers ---
    for k in range(n_enc):
        layer_phoneme = enc_weights[k]  # (H,)
        noise_scale_clean = _snr_to_noise_scale(config.snr_db, clean_signal_str)
        noise_scale_noisy = _snr_to_noise_scale(config.noisy_snr_db, noisy_signal_str)

        # Clean: signal + small noise, repeated across time with slight drift
        clean_base = np.outer(np.ones(T), layer_phoneme * clean_signal_str)
        clean_base += rng.standard_normal((T, H)) * noise_scale_clean * 0.3
        # Add temporal variation
        time_drift = np.linspace(-0.1, 0.1, T)[:, None] * phoneme_dir[None, :]
        clean_acts[k] = clean_base + time_drift

        # Noisy: weakened signal + more noise, drifting toward language prior
        noisy_base = np.outer(np.ones(T), layer_phoneme * noisy_signal_str)
        noisy_base += np.outer(np.ones(T), noise_dir * (1.0 - noisy_signal_str) * 0.5)
        noisy_base += rng.standard_normal((T, H)) * noise_scale_noisy * 0.5
        noisy_acts[k] = noisy_base

    # --- Decoder layers ---
    # Decoder collapses audio signal at rate `dec_collapse` per layer
    dec_signal_clean = clean_signal_str * (1.0 - dec_collapse * 0.3)
    dec_signal_noisy = noisy_signal_str * (1.0 - dec_collapse * 0.5)

    for k in range(n_dec):
        layer_idx = n_enc + k
        decay = dec_collapse ** (k + 1)

        # Clean decoder: audio signal fades, language prior grows
        clean_dec = rng.standard_normal((T, H)) * 0.1
        clean_dec += np.outer(np.ones(T), phoneme_dir * dec_signal_clean * (1.0 - decay))
        clean_dec += np.outer(np.ones(T), noise_dir * decay * 0.5)
        clean_acts[layer_idx] = clean_dec

        # Noisy decoder: mostly language prior
        noisy_dec = rng.standard_normal((T, H)) * 0.15
        noisy_dec += np.outer(np.ones(T), phoneme_dir * dec_signal_noisy * (1.0 - decay))
        noisy_dec += np.outer(np.ones(T), noise_dir * (0.5 + decay * 0.4))
        noisy_acts[layer_idx] = noisy_dec

    # Metadata
    meta = {
        "contrast": config.contrast,
        "description": contrast_spec["description"],
        "n_encoder_layers": n_enc,
        "n_decoder_layers": n_dec,
        "hidden_dim": H,
        "seq_len": T,
        "seed": config.seed,
        "snr_db_clean": config.snr_db,
        "snr_db_noisy": config.noisy_snr_db,
    }

    return clean_acts, noisy_acts, meta


def compute_mock_gc_from_stimuli(
    clean_acts: dict[int, np.ndarray],
    noisy_acts: dict[int, np.ndarray],
    n_encoder_layers: int,
    n_decoder_layers: int,
) -> dict:
    """
    Compute a mock gc(k) curve from synthetic activation pairs.

    Simulates causal patching: at each layer k, measures how much
    patching clean activations into the noisy run shifts the "output."
    Here the output proxy = cosine similarity between the final layer
    activation and the clean reference.

    This directly feeds into gc_eval.py format.
    """
    total_layers = n_encoder_layers + n_decoder_layers
    final_layer = total_layers - 1

    # Clean reference = mean activation of final clean decoder layer
    ref_clean = clean_acts[final_layer].mean(axis=0)  # (H,)
    ref_clean_norm = ref_clean / (np.linalg.norm(ref_clean) + 1e-8)

    # Noisy baseline = cosine sim of final noisy layer to clean ref
    noisy_final = noisy_acts[final_layer].mean(axis=0)
    noisy_final_norm = noisy_final / (np.linalg.norm(noisy_final) + 1e-8)
    baseline_noisy_score = float(ref_clean_norm.dot(noisy_final_norm))
    baseline_clean_score = 1.0  # perfect match to itself

    delta_baseline = baseline_clean_score - baseline_noisy_score + 1e-8

    gc_values = []
    for k in range(total_layers):
        # Patched run: replace layer k in noisy with clean, propagate to final
        # Approximation: interpolate final layer toward clean proportionally
        # to how early/late the patched layer is (early = more influence)
        influence = 1.0 - (k / total_layers) * 0.5  # earlier layers → more influence

        # Patched final activation (simple linear interpolation heuristic)
        patched_final = (
            influence * clean_acts[k].mean(axis=0)
            + (1.0 - influence) * noisy_acts[final_layer].mean(axis=0)
        )
        patched_final_norm = patched_final / (np.linalg.norm(patched_final) + 1e-8)
        patched_score = float(ref_clean_norm.dot(patched_final_norm))

        delta_k = patched_score - baseline_noisy_score
        gc_k = float(np.clip(delta_k / delta_baseline, 0.0, 1.0))
        gc_values.append(gc_k)

    return {
        "layers": list(range(total_layers)),
        "gc_values": gc_values,
        "n_encoder_layers": n_encoder_layers,
        "n_decoder_layers": n_decoder_layers,
        "method": "synthetic_causal_patch",
    }


# ---------------------------------------------------------------------------
# gc_eval integration shim
# ---------------------------------------------------------------------------

def generate_gc_result_from_stimuli(config: StimuliConfig) -> dict:
    """
    Full pipeline: generate stimuli → compute gc(k) → return gc_eval-compatible dict.
    Drop-in replacement for gc_eval.generate_mock_gc_curve() with
    phoneme-grounded semantics.
    """
    clean_acts, noisy_acts, meta = generate_activation_pair(config)
    result = compute_mock_gc_from_stimuli(
        clean_acts, noisy_acts,
        config.n_encoder_layers, config.n_decoder_layers
    )
    result["contrast"] = config.contrast
    result["mode"] = f"synthetic_{config.contrast}"
    result["meta"] = meta
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _list_contrasts() -> None:
    print("Available phoneme contrasts:\n")
    for name, spec in PHONEME_CONTRASTS.items():
        print(f"  {name:25s}  {spec['description']}")
        print(f"    clean_signal={spec['clean_signal_strength']:.2f}  "
              f"noisy_signal={spec['noisy_signal_strength']:.2f}  "
              f"dec_collapse={spec['decoder_collapse_rate']:.2f}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Synthetic stimuli generator for gc(k) harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--contrast", default="vowel_consonant",
                        help="Phoneme contrast type (see --list-contrasts)")
    parser.add_argument("--list-contrasts", action="store_true",
                        help="Print available contrast types and exit")
    parser.add_argument("--n-encoder", type=int, default=6)
    parser.add_argument("--n-decoder", type=int, default=6)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--seq-len", type=int, default=8)
    parser.add_argument("--snr-db", type=float, default=10.0)
    parser.add_argument("--noisy-snr-db", type=float, default=-5.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--json", action="store_true", help="Output raw JSON result")
    parser.add_argument("--all-contrasts", action="store_true",
                        help="Run all contrasts and show comparison table")
    args = parser.parse_args()

    if args.list_contrasts:
        _list_contrasts()
        return

    def make_config(contrast: str) -> StimuliConfig:
        return StimuliConfig(
            contrast=contrast,
            n_encoder_layers=args.n_encoder,
            n_decoder_layers=args.n_decoder,
            hidden_dim=args.hidden_dim,
            seq_len=args.seq_len,
            snr_db=args.snr_db,
            noisy_snr_db=args.noisy_snr_db,
            seed=args.seed,
        )

    if args.all_contrasts:
        print(f"\n{'Contrast':30s} {'EncMean':>8} {'DecMean':>8} {'Peak':>6}")
        print("-" * 60)
        for contrast in PHONEME_CONTRASTS:
            cfg = make_config(contrast)
            result = generate_gc_result_from_stimuli(cfg)
            gc = np.array(result["gc_values"])
            n_enc = result["n_encoder_layers"]
            enc_mean = gc[:n_enc].mean()
            dec_mean = gc[n_enc:].mean()
            peak = result["layers"][int(np.argmax(gc))]
            print(f"  {contrast:28s} {enc_mean:>8.3f} {dec_mean:>8.3f} {peak:>6}")
        print()
        return

    cfg = make_config(args.contrast)
    result = generate_gc_result_from_stimuli(cfg)

    if args.json:
        # Remove non-serializable meta fields
        out = {k: v for k, v in result.items() if k != "meta"}
        out["meta"] = result["meta"]
        print(json.dumps(out, indent=2))
        return

    # Pretty print
    gc = np.array(result["gc_values"])
    n_enc = result["n_encoder_layers"]
    print(f"\n=== Synthetic gc(k): {args.contrast} ===")
    print(f"Description: {PHONEME_CONTRASTS[args.contrast]['description']}")
    print(f"SNR clean={args.snr_db}dB  noisy={args.noisy_snr_db}dB\n")
    print(f"{'Layer':>6}  {'Type':>8}  {'gc(k)':>8}  Bar")
    print("-" * 52)
    for layer, val in zip(result["layers"], result["gc_values"]):
        ltype = "enc" if layer < n_enc else "dec"
        bar = "█" * int(val * 30) + "░" * (30 - int(val * 30))
        print(f"{layer:>6}  {ltype:>8}  {val:>8.3f}  {bar}")
    print()
    print(f"Mean gc (encoder): {gc[:n_enc].mean():.3f}")
    print(f"Mean gc (decoder): {gc[n_enc:].mean():.3f}")
    print(f"Peak layer: {result['layers'][int(np.argmax(gc))]}")
    print()


if __name__ == "__main__":
    main()
