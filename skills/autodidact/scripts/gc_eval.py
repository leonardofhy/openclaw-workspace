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
import math
import sys
from dataclasses import dataclass, field
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Anti-confound checker (10 automated test gate assertions)
# ---------------------------------------------------------------------------
# These checks guard against common confounds in gc(k) causal patching:
# bad baselines, degenerate curves, numerical artifacts, and eval-env issues.
# Reference: T5 anti-confound checklist (Q037) + MATS proposal controls.
#
# Usage:
#   result = generate_mock_gc_curve(mode="listen")
#   report = AntiConfoundChecker().run(result)
#   report.assert_pass()   # raises RuntimeError on any FAIL
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


@dataclass
class AntiConfoundReport:
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def n_failed(self) -> int:
        return sum(1 for c in self.checks if not c.passed)

    def assert_pass(self) -> None:
        if not self.passed:
            failed = [c for c in self.checks if not c.passed]
            lines = "\n".join(f"  FAIL [{c.name}]: {c.detail}" for c in failed)
            raise RuntimeError(
                f"Anti-confound gate: {self.n_failed}/{len(self.checks)} checks FAILED:\n{lines}"
            )

    def print_report(self) -> None:
        print("\n=== Anti-Confound Checklist ===")
        for c in self.checks:
            tag = "✅ PASS" if c.passed else "❌ FAIL"
            print(f"  {tag}  [{c.name}] {c.detail}")
        overall = "ALL PASS" if self.passed else f"{self.n_failed} FAILED"
        print(f"\nResult: {overall} ({len(self.checks)} checks)\n")


class AntiConfoundChecker:
    """
    10-item automated anti-confound test gate for gc(k) curves.

    Instantiate with custom thresholds if defaults are too strict/loose.
    """

    def __init__(
        self,
        *,
        min_peak_gc: float = 0.3,       # AC-5: at least one layer must reach this gc
        min_gc_std: float = 0.02,        # AC-4: curve must not be suspiciously flat
        min_encoder_layers: int = 1,     # AC-7: must have at least this many encoder layers
        max_listen_guess_overlap: float = 0.15,  # AC-9: listen/guess means must differ by this
        min_baseline_delta_logp: float | None = None,  # AC-6: log-prob delta (real mode only)
        min_valid_frac: float = 0.9,     # AC-3: fraction of values that must be finite & in [0,1]
    ):
        self.min_peak_gc = min_peak_gc
        self.min_gc_std = min_gc_std
        self.min_encoder_layers = min_encoder_layers
        self.max_listen_guess_overlap = max_listen_guess_overlap
        self.min_baseline_delta_logp = min_baseline_delta_logp
        self.min_valid_frac = min_valid_frac

    # --- individual check methods ---

    def _ac01_value_range(self, gc: np.ndarray) -> CheckResult:
        """AC-01: All gc(k) values must be in [0, 1]."""
        out_of_range = np.sum((gc < 0) | (gc > 1))
        ok = int(out_of_range) == 0
        return CheckResult(
            "AC-01:value-range",
            ok,
            f"All {len(gc)} values in [0,1]" if ok
            else f"{out_of_range}/{len(gc)} values outside [0,1]",
        )

    def _ac02_no_nan_inf(self, gc: np.ndarray) -> CheckResult:
        """AC-02: No NaN or Inf values."""
        n_bad = int(np.sum(~np.isfinite(gc)))
        ok = n_bad == 0
        return CheckResult(
            "AC-02:no-nan-inf",
            ok,
            "No NaN/Inf detected" if ok else f"{n_bad} NaN/Inf values found",
        )

    def _ac03_valid_fraction(self, gc: np.ndarray) -> CheckResult:
        """AC-03: ≥90% of values are finite and within [0,1]."""
        finite = np.isfinite(gc)
        in_range = (gc >= 0) & (gc <= 1)
        valid_frac = float(np.mean(finite & in_range))
        ok = valid_frac >= self.min_valid_frac
        return CheckResult(
            "AC-03:valid-fraction",
            ok,
            f"{valid_frac:.1%} valid (threshold {self.min_valid_frac:.0%})",
        )

    def _ac04_non_constant_curve(self, gc: np.ndarray) -> CheckResult:
        """AC-04: Curve must not be suspiciously flat (std > threshold).
        A constant gc(k) curve signals a bug or degenerate baseline."""
        std = float(np.std(gc))
        ok = std >= self.min_gc_std
        return CheckResult(
            "AC-04:non-constant-curve",
            ok,
            f"std={std:.4f} ≥ {self.min_gc_std}" if ok
            else f"std={std:.4f} < {self.min_gc_std} (suspiciously flat curve)",
        )

    def _ac05_peak_reachability(self, gc: np.ndarray) -> CheckResult:
        """AC-05: At least one layer must show gc(k) > threshold.
        If every gc(k) is near zero, audio never contributes — likely a bad baseline."""
        peak = float(np.max(gc))
        ok = peak >= self.min_peak_gc
        return CheckResult(
            "AC-05:peak-reachability",
            ok,
            f"max gc={peak:.3f} ≥ {self.min_peak_gc}" if ok
            else f"max gc={peak:.3f} < {self.min_peak_gc} (audio never causally active)",
        )

    def _ac06_baseline_delta(self, result: dict) -> CheckResult:
        """AC-06: Clean-noisy log-prob delta must be non-trivial.
        If delta≈0, causal patching measures noise not signal. Skipped in mock mode."""
        if result.get("method") == "mock_causal_patch":
            return CheckResult(
                "AC-06:baseline-delta",
                True,
                "Skipped (mock mode — no real baseline delta)",
            )
        delta = result.get("baseline_delta_logp")
        if delta is None:
            return CheckResult("AC-06:baseline-delta", False, "baseline_delta_logp missing from result")
        threshold = self.min_baseline_delta_logp or 0.1
        ok = abs(delta) >= threshold
        return CheckResult(
            "AC-06:baseline-delta",
            ok,
            f"|Δlog-p|={abs(delta):.4f} ≥ {threshold}" if ok
            else f"|Δlog-p|={abs(delta):.4f} < {threshold} (baseline too close — patching measures noise)",
        )

    def _ac07_layer_coverage(self, result: dict, gc: np.ndarray) -> CheckResult:
        """AC-07: Number of encoder layers ≥ min_encoder_layers, and layer list is contiguous."""
        n_enc = result.get("n_encoder_layers", 0)
        layers = result.get("layers", [])
        # Check contiguity
        if len(layers) > 1:
            diffs = [layers[i+1] - layers[i] for i in range(len(layers)-1)]
            contiguous = all(d == 1 for d in diffs)
        else:
            contiguous = True
        ok = n_enc >= self.min_encoder_layers and len(gc) == len(layers) and contiguous
        detail_parts = []
        if n_enc < self.min_encoder_layers:
            detail_parts.append(f"n_encoder_layers={n_enc} < {self.min_encoder_layers}")
        if len(gc) != len(layers):
            detail_parts.append(f"gc length {len(gc)} ≠ layers length {len(layers)}")
        if not contiguous:
            detail_parts.append("layer indices not contiguous")
        return CheckResult(
            "AC-07:layer-coverage",
            ok,
            f"{len(layers)} layers, {n_enc} encoder, contiguous={contiguous}" if ok
            else "; ".join(detail_parts),
        )

    def _ac08_encoder_decoder_differentiation(self, result: dict, gc: np.ndarray) -> CheckResult:
        """AC-08: Encoder and decoder mean gc must differ (soft check).
        If they are identical, enc/dec boundary detection may be broken."""
        n_enc = result.get("n_encoder_layers", 0)
        if n_enc == 0 or n_enc >= len(gc):
            return CheckResult(
                "AC-08:enc-dec-differentiation",
                True,
                "Skipped (no decoder layers to compare)",
            )
        enc_mean = float(np.mean(gc[:n_enc]))
        dec_mean = float(np.mean(gc[n_enc:]))
        diff = abs(enc_mean - dec_mean)
        ok = diff > 0.02  # soft: just check they differ by > 2pp
        return CheckResult(
            "AC-08:enc-dec-differentiation",
            ok,
            f"enc_mean={enc_mean:.3f}, dec_mean={dec_mean:.3f}, |diff|={diff:.3f}" if ok
            else f"enc/dec means nearly identical ({enc_mean:.3f} vs {dec_mean:.3f}) — possible bug",
        )

    def _ac09_mode_separability(self, result: dict, gc: np.ndarray) -> CheckResult:
        """AC-09: If mode is labeled (listen/guess), the mean gc should
        match expected direction. Prevents swapped labels or inverted curves."""
        mode = result.get("mode")
        if mode not in ("listen", "guess"):
            return CheckResult(
                "AC-09:mode-separability",
                True,
                f"Skipped (mode={mode!r} — no expected direction)",
            )
        mean_gc = float(np.mean(gc))
        if mode == "listen":
            # listen → should be higher; we just check > 0.4 as sanity
            ok = mean_gc >= 0.4
            exp = "≥0.40 for 'listen' mode"
        else:
            # guess → should be lower; check < 0.55
            ok = mean_gc < 0.55
            exp = "<0.55 for 'guess' mode"
        return CheckResult(
            "AC-09:mode-separability",
            ok,
            f"mean_gc={mean_gc:.3f} {exp}" if ok
            else f"mean_gc={mean_gc:.3f} inconsistent with mode={mode!r} ({exp})",
        )

    def _ac10_no_eval_awareness_artifact(self, result: dict, gc: np.ndarray) -> CheckResult:
        """AC-10: gc(k) must not be perfectly monotone (either strictly increasing or
        strictly decreasing throughout). A perfectly monotone curve is suspiciously clean
        and may indicate the model is responding to eval structure rather than audio content.
        Real causal patching results always show some non-monotone noise."""
        if len(gc) < 4:
            return CheckResult(
                "AC-10:no-monotone-artifact",
                True,
                "Skipped (too few layers to test monotonicity)",
            )
        diffs = np.diff(gc)
        strictly_increasing = bool(np.all(diffs > 0))
        strictly_decreasing = bool(np.all(diffs < 0))
        is_perfectly_monotone = strictly_increasing or strictly_decreasing
        ok = not is_perfectly_monotone
        return CheckResult(
            "AC-10:no-monotone-artifact",
            ok,
            "Curve is non-monotone (expected for causal patching)" if ok
            else "Curve is perfectly monotone — likely synthetic artifact or bug",
        )

    # --- main entry point ---

    def run(self, result: dict) -> AntiConfoundReport:
        """Run all 10 checks on a gc(k) result dict. Returns AntiConfoundReport."""
        gc = np.array(result.get("gc_values", []), dtype=float)
        report = AntiConfoundReport()
        report.checks = [
            self._ac01_value_range(gc),
            self._ac02_no_nan_inf(gc),
            self._ac03_valid_fraction(gc),
            self._ac04_non_constant_curve(gc),
            self._ac05_peak_reachability(gc),
            self._ac06_baseline_delta(result),
            self._ac07_layer_coverage(result, gc),
            self._ac08_encoder_decoder_differentiation(result, gc),
            self._ac09_mode_separability(result, gc),
            self._ac10_no_eval_awareness_artifact(result, gc),
        ]
        return report


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
    parser.add_argument(
        "--check", action="store_true",
        help="Run anti-confound checklist (10 assertions). Exit code 1 if any FAIL.",
    )
    parser.add_argument(
        "--check-only", action="store_true",
        help="Run --check and suppress curve output (gate mode).",
    )
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

    if args.check or args.check_only:
        report = AntiConfoundChecker().run(result)
        report.print_report()
        if not report.passed:
            sys.exit(1)

    if args.check_only:
        return

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_curve(result)

    if args.plot:
        plot_curve(result)


if __name__ == "__main__":
    main()
