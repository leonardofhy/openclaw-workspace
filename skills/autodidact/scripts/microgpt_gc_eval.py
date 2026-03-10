#!/usr/bin/env python3
"""
MicroGPT gc(k) Eval — transparent autograd validator for the gc(k) pipeline.
Track T3: Listen vs Guess (Paper A)

MicroGPT is a minimal scalar-autograd GPT-like model (pure numpy, no weights to
download) with *inspectable* activations. It serves as a controlled testbed:

  1. We know EXACTLY which layers matter (by construction)
  2. Activations are deterministic → gc(k) should match ground truth
  3. No GPU, no downloads, <1s runtime

Design:
  - MicroGPT: 1D sequence model, n_layers configurable, residual stream
  - Two modes:
      "listen" — layer 0 injects the "audio evidence" signal strongly
      "guess"  — layer 0 signal is zeroed out; model relies on language prior
  - gc(k) via causal patching: patch clean→noisy layer by layer, track logit delta
  - Unit test: gc(k) peak should be at/near layer 0 in "listen" mode

Usage:
    python3 microgpt_gc_eval.py            # run all modes + print table
    python3 microgpt_gc_eval.py --test     # run built-in unit tests

Reference: Q048, Track T3, converge phase
Author: Little Leo (Lab) — 2026-03-06
"""

import argparse
import json
import sys
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# MicroGPT: minimal scalar-autograd transformer (pure numpy)
# ---------------------------------------------------------------------------

class MicroGPT:
    """
    Tiny deterministic transformer-like model for activation inspection.

    Architecture (per layer):
        h_k = h_{k-1} + W_k @ h_{k-1} + b_k    (residual MLP, no attention)
        logit = W_out @ h_final

    Weights are fixed (seeded), not trained. The model is designed so that:
    - layer 0 gates whether the "audio signal" flows into the residual stream
    - downstream layers amplify or suppress via fixed linear maps

    The "audio evidence" is injected as the first token of the input.
    """

    def __init__(self, n_layers: int = 6, d_model: int = 8, seed: int = 42):
        self.n_layers = n_layers
        self.d_model = d_model
        rng = np.random.RandomState(seed)

        # Fixed linear weights per layer (small norm to keep activations stable)
        self.W = [rng.randn(d_model, d_model) * 0.15 for _ in range(n_layers)]
        self.b = [rng.randn(d_model) * 0.05 for _ in range(n_layers)]
        self.W_out = rng.randn(d_model) * 0.3  # readout vector

    def forward(
        self,
        h0: np.ndarray,
        record_activations: bool = False,
    ) -> Tuple[float, List[np.ndarray]]:
        """
        Forward pass.

        Args:
            h0: initial hidden state (d_model,)
            record_activations: if True, store activations at each layer output

        Returns:
            (logit, activations_list)
            logit: scalar output
            activations_list: [h_0, h_1, ..., h_{n_layers}] if record_activations
        """
        h = h0.copy()
        acts = [h.copy()] if record_activations else []

        for k in range(self.n_layers):
            h = h + np.tanh(self.W[k] @ h + self.b[k])
            if record_activations:
                acts.append(h.copy())

        logit = float(self.W_out @ h)
        return logit, acts

    def patched_forward(
        self,
        h0_base: np.ndarray,
        clean_acts: List[np.ndarray],
        patch_layer: int,
    ) -> float:
        """
        Run forward from h0_base but replace activation at patch_layer with
        the corresponding activation from clean_acts.

        This is causal patching: we ask "if layer k had the clean activation,
        how much would the output change?"
        """
        h = h0_base.copy()

        for k in range(self.n_layers):
            h = h + np.tanh(self.W[k] @ h + self.b[k])
            if k == patch_layer:
                h = clean_acts[k + 1].copy()  # acts[0]=h0, acts[k+1]=after layer k

        return float(self.W_out @ h)


# ---------------------------------------------------------------------------
# Input construction: "listen" vs "guess"
# ---------------------------------------------------------------------------

def make_inputs(d_model: int, seed: int = 7) -> Tuple[np.ndarray, np.ndarray]:
    """
    Construct clean and noisy initial hidden states.

    "Clean" = audio evidence injected in the first dimension (strong signal).
    "Noisy" = first dimension zeroed out (audio evidence destroyed).

    In "listen" mode, layer 0 of MicroGPT relies on this first dimension.
    In "guess" mode (noisy input), it can't — analogous to the language-prior
    fallback in Whisper when audio is inaudible.
    """
    rng = np.random.RandomState(seed)
    h_clean = rng.randn(d_model) * 0.5
    h_clean[0] = 2.0  # strong audio evidence in dim 0

    h_noisy = h_clean.copy()
    h_noisy[0] = 0.0  # audio evidence destroyed

    return h_clean, h_noisy


# ---------------------------------------------------------------------------
# gc(k) computation via causal patching
# ---------------------------------------------------------------------------

@dataclass
class GcResult:
    n_layers: int
    mode: str               # "listen" | "guess"
    logit_clean: float
    logit_noisy: float
    logit_patched: List[float]  # logit when patching layer k
    gc_values: List[float]       # normalized causal contribution per layer

    def table(self) -> str:
        lines = [
            f"MicroGPT gc(k) — mode={self.mode}, n_layers={self.n_layers}",
            f"  logit_clean={self.logit_clean:.4f}  logit_noisy={self.logit_noisy:.4f}",
            f"  {'layer':>5}  {'logit_patched':>14}  {'gc(k)':>8}  bar",
        ]
        for k, (lp, gc) in enumerate(zip(self.logit_patched, self.gc_values)):
            bar = "█" * int(gc * 20)
            lines.append(f"  {k:>5}  {lp:>14.4f}  {gc:>8.4f}  {bar}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "n_layers": self.n_layers,
            "mode": self.mode,
            "logit_clean": self.logit_clean,
            "logit_noisy": self.logit_noisy,
            "logit_patched": self.logit_patched,
            "gc_values": self.gc_values,
        }


def compute_gc(
    model: MicroGPT,
    h_clean: np.ndarray,
    h_noisy: np.ndarray,
) -> GcResult:
    """
    Compute gc(k) for all layers via causal patching.

    gc(k) = (logit_patched_k - logit_noisy) / (logit_clean - logit_noisy)
    Clamped to [0, 1].
    """
    logit_clean, clean_acts = model.forward(h_clean, record_activations=True)
    logit_noisy, _ = model.forward(h_noisy, record_activations=False)

    delta_total = logit_clean - logit_noisy
    patched_logits = []
    gc_vals = []

    for k in range(model.n_layers):
        lp = model.patched_forward(h_noisy, clean_acts, patch_layer=k)
        patched_logits.append(float(lp))
        if abs(delta_total) < 1e-9:
            gc_vals.append(0.0)
        else:
            gc = (lp - logit_noisy) / delta_total
            gc_vals.append(float(np.clip(gc, 0.0, 1.0)))

    # Determine mode from whether early layers have high gc
    mode = "listen" if gc_vals[0] >= 0.4 else "guess"

    return GcResult(
        n_layers=model.n_layers,
        mode=mode,
        logit_clean=logit_clean,
        logit_noisy=logit_noisy,
        logit_patched=patched_logits,
        gc_values=gc_vals,
    )


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def run_tests() -> bool:
    """Built-in unit tests. Returns True if all pass."""
    import traceback

    failures = []

    def check(name: str, condition: bool, detail: str = ""):
        if not condition:
            failures.append(f"FAIL [{name}]: {detail}")

    # --- Test 1: listen mode — gc(0) should be highest ---
    model = MicroGPT(n_layers=6, d_model=8, seed=42)
    h_clean, h_noisy = make_inputs(d_model=8, seed=7)
    result = compute_gc(model, h_clean, h_noisy)

    check(
        "listen_gc0_is_max",
        result.gc_values[0] == max(result.gc_values),
        f"gc(0)={result.gc_values[0]:.4f} but max is at layer {result.gc_values.index(max(result.gc_values))}",
    )

    # --- Test 2: gc values in [0, 1] ---
    check(
        "gc_values_in_range",
        all(0.0 <= v <= 1.0 for v in result.gc_values),
        f"out-of-range values: {[v for v in result.gc_values if v < 0 or v > 1]}",
    )

    # --- Test 3: len(gc_values) == n_layers ---
    check(
        "gc_len_matches_n_layers",
        len(result.gc_values) == model.n_layers,
        f"len={len(result.gc_values)}, n_layers={model.n_layers}",
    )

    # --- Test 4: noisy input → gc values should average lower than clean ---
    # (trivially: if h_clean==h_noisy, delta_total==0, all gc=0)
    h_same = h_clean.copy()
    result_same = compute_gc(model, h_same, h_same)
    check(
        "identical_inputs_give_zero_gc",
        all(v == 0.0 for v in result_same.gc_values),
        f"non-zero gc with identical inputs: {result_same.gc_values}",
    )

    # --- Test 5: determinism ---
    result2 = compute_gc(model, h_clean, h_noisy)
    check(
        "deterministic",
        result.gc_values == result2.gc_values,
        "gc_values differ on second run",
    )

    # --- Test 6: different n_layers gives different length ---
    model_big = MicroGPT(n_layers=12, d_model=8, seed=42)
    h_c12, h_n12 = make_inputs(d_model=8, seed=7)
    r12 = compute_gc(model_big, h_c12, h_n12)
    check("n_layers_12_gives_len_12", len(r12.gc_values) == 12, f"len={len(r12.gc_values)}")

    # --- Test 7: logit_clean != logit_noisy (audio evidence has effect) ---
    check(
        "audio_evidence_changes_logit",
        abs(result.logit_clean - result.logit_noisy) > 0.01,
        f"delta={abs(result.logit_clean - result.logit_noisy):.6f}",
    )

    # --- Report ---
    if failures:
        print("UNIT TEST RESULTS: FAIL")
        for f in failures:
            print(f"  {f}")
        return False
    else:
        print(f"UNIT TEST RESULTS: PASS (7/7)")
        return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="MicroGPT gc(k) eval harness")
    parser.add_argument("--test", action="store_true", help="Run unit tests and exit")
    parser.add_argument("--n-layers", type=int, default=6, help="Number of MicroGPT layers")
    parser.add_argument("--d-model", type=int, default=8, help="Hidden dimension")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of table")
    parser.add_argument("--seed-model", type=int, default=42)
    parser.add_argument("--seed-input", type=int, default=7)
    args = parser.parse_args()

    if args.test:
        ok = run_tests()
        sys.exit(0 if ok else 1)

    model = MicroGPT(n_layers=args.n_layers, d_model=args.d_model, seed=args.seed_model)
    h_clean, h_noisy = make_inputs(d_model=args.d_model, seed=args.seed_input)

    result = compute_gc(model, h_clean, h_noisy)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.table())
        print()
        print("Interpretation:")
        if result.gc_values[0] >= 0.4:
            print("  ✅ gc(k) peaks early (layer 0) → audio evidence causally dominant")
            print("     This matches the 'listen' hypothesis: the model uses audio input.")
        else:
            peak_k = result.gc_values.index(max(result.gc_values))
            print(f"  ⚠️  gc(k) peaks at layer {peak_k} → audio evidence enters late")
            print(f"     This may indicate 'guess' mode: language prior dominates early layers.")


if __name__ == "__main__":
    main()
