#!/usr/bin/env python3
"""
Q038 — MicroGPT × Phonological DAS suite (fully inspectable phoneme circuits)

Implements a tiny deterministic transformer-like model and a DAS-style activation
patching protocol over a 6-phoneme toy task:
  phonemes = [p, b, t, d, k, g]

Target factor: voicing (0=voiceless, 1=voiced)
Pairs: (p,b), (t,d), (k,g)

Outputs:
  - IIA: interchange intervention accuracy (did patch induce expected voiced/voiceless flip?)
  - Cause: average causal effect size of patching on voicing logit
  - Isolate: specificity score (target factor changes while place-of-articulation stays stable)
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np


PHONEMES = ["p", "b", "t", "d", "k", "g"]
VOICING = {"p": 0, "b": 1, "t": 0, "d": 1, "k": 0, "g": 1}
PLACE = {"p": "labial", "b": "labial", "t": "alveolar", "d": "alveolar", "k": "velar", "g": "velar"}
PAIRS = [("p", "b"), ("t", "d"), ("k", "g")]


class TinyPhonDASModel:
    """Deterministic, inspectable residual stack with layer-wise activations."""

    def __init__(self, n_layers: int = 5, d_model: int = 4, seed: int = 42):
        self.n_layers = n_layers
        self.d_model = d_model
        rng = np.random.RandomState(seed)

        # Embed dims: [voicing, place_1, place_2, bias]
        self.emb = {
            "p": np.array([-1.0, 1.0, 0.0, 1.0]),
            "b": np.array([+1.0, 1.0, 0.0, 1.0]),
            "t": np.array([-1.0, 0.0, 1.0, 1.0]),
            "d": np.array([+1.0, 0.0, 1.0, 1.0]),
            "k": np.array([-1.0, -1.0, -1.0, 1.0]),
            "g": np.array([+1.0, -1.0, -1.0, 1.0]),
        }

        self.W = [rng.randn(d_model, d_model) * 0.08 for _ in range(n_layers)]
        self.b = [rng.randn(d_model) * 0.03 for _ in range(n_layers)]

        # Encourage voicing readout to be dominated by dim 0.
        self.w_voice = np.array([1.4, 0.08, -0.05, 0.02])
        self.w_place = np.array([0.02, 0.85, 0.85, 0.01])

    def forward(self, phoneme: str, record: bool = False) -> Tuple[np.ndarray, List[np.ndarray]]:
        h = self.emb[phoneme].copy()
        acts = [h.copy()] if record else []
        for k in range(self.n_layers):
            h = h + np.tanh(self.W[k] @ h + self.b[k])
            if k == 1:
                # Layer 1 carries strongest voicing feature (designed causal site).
                h[0] *= 1.35
            if record:
                acts.append(h.copy())
        logits = np.array([self.w_voice @ h, self.w_place @ h])
        return logits, acts

    def patched_logits(self, base_ph: str, src_acts: List[np.ndarray], patch_layer: int) -> np.ndarray:
        h = self.emb[base_ph].copy()
        for k in range(self.n_layers):
            h = h + np.tanh(self.W[k] @ h + self.b[k])
            if k == 1:
                h[0] *= 1.35
            if k == patch_layer:
                h = src_acts[k + 1].copy()
        return np.array([self.w_voice @ h, self.w_place @ h])


@dataclass
class LayerScore:
    layer: int
    iia: float
    cause: float
    isolate: float



def run_suite(model: TinyPhonDASModel) -> Dict:
    rows: List[LayerScore] = []

    for layer in range(model.n_layers):
        iia_hits = 0
        iia_total = 0
        cause_vals: List[float] = []
        isolate_vals: List[float] = []

        for a, b in PAIRS:
            for base, src in [(a, b), (b, a)]:
                base_logits, _ = model.forward(base, record=False)
                src_logits, src_acts = model.forward(src, record=True)
                patched = model.patched_logits(base, src_acts, patch_layer=layer)

                base_voice = 1 if base_logits[0] > 0 else 0
                src_voice = 1 if src_logits[0] > 0 else 0
                patched_voice = 1 if patched[0] > 0 else 0

                # IIA: did intervention move prediction to source factor value?
                iia_hits += int(patched_voice == src_voice)
                iia_total += 1

                # Cause: normalized movement of voicing logit toward source.
                denom = abs(src_logits[0] - base_logits[0]) + 1e-9
                toward_src = 1.0 - abs(src_logits[0] - patched[0]) / denom
                cause_vals.append(float(np.clip(toward_src, 0.0, 1.0)))

                # Isolate: place logit should remain stable while voicing changes.
                place_shift = abs(patched[1] - base_logits[1])
                voice_shift = abs(patched[0] - base_logits[0]) + 1e-9
                isolate = float(np.clip(1.0 - (place_shift / voice_shift), 0.0, 1.0))
                isolate_vals.append(isolate)

        rows.append(
            LayerScore(
                layer=layer,
                iia=iia_hits / max(iia_total, 1),
                cause=float(np.mean(cause_vals)) if cause_vals else 0.0,
                isolate=float(np.mean(isolate_vals)) if isolate_vals else 0.0,
            )
        )

    best = max(rows, key=lambda r: (r.cause + r.iia + r.isolate))
    return {
        "task": "Q038",
        "phonemes": PHONEMES,
        "pairs": PAIRS,
        "metrics": [r.__dict__ for r in rows],
        "best_layer": best.layer,
    }


def print_table(result: Dict) -> None:
    print("MicroGPT × Phonological DAS (Q038)")
    print("6-phoneme task: p/b, t/d, k/g")
    print(f"Best layer: {result['best_layer']}")
    print(f"{'layer':>5}  {'IIA':>6}  {'Cause':>6}  {'Isolate':>8}")
    for r in result["metrics"]:
        print(f"{r['layer']:>5}  {r['iia']:.3f}  {r['cause']:.3f}  {r['isolate']:.3f}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--json", action="store_true")
    p.add_argument("--n-layers", type=int, default=5)
    p.add_argument("--d-model", type=int, default=4)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    model = TinyPhonDASModel(n_layers=args.n_layers, d_model=args.d_model, seed=args.seed)
    result = run_suite(model)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_table(result)


if __name__ == "__main__":
    main()
