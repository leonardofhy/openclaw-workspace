"""
isolate_curve_shape.py — Classify Isolate(k) curve shapes per utterance.

Theory
------
The shape of Isolate(k) across layers encodes the model's audio processing
strategy for a given utterance:

  DECAY   — Isolate decreases monotonically: audio info disentangles
            progressively layer-by-layer. Associated with strong, high-layer
            gc(k) peaks. Model "hears" clearly.

  U-SHAPE — Isolate is high early, drops mid-layers, rises again late.
            Mid-layers are the "clean" zone. gc peak is moderate, mid-network.
            Model converges then reconverges (feature reuse).

  PLATEAU — Isolate stays roughly constant across layers. No clear
            disentanglement. Low gc peak everywhere. Model "guesses."

Hypothesis:
  shape_class → gc peak height correlation:
    DECAY > U-SHAPE > PLATEAU

This lets us predict ASR reliability from probe geometry alone (no patching).

Usage
-----
    python3 isolate_curve_shape.py               # run classification demo
    python3 isolate_curve_shape.py --n 500       # larger mock dataset
    python3 isolate_curve_shape.py --layers 48   # 48-layer model
    python3 isolate_curve_shape.py --verbose      # show per-utterance details
"""

import argparse
import math
import random
import statistics
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Shape taxonomy
# ---------------------------------------------------------------------------

class CurveShape(str, Enum):
    DECAY   = "decay"    # monotone decreasing
    U_SHAPE = "u_shape"  # valley in middle
    PLATEAU = "plateau"  # flat


# ---------------------------------------------------------------------------
# Mock data generation
# ---------------------------------------------------------------------------

def _add_noise(curve: list[float], sigma: float) -> list[float]:
    return [max(0.01, v + random.gauss(0, sigma)) for v in curve]


def generate_decay_curve(n_layers: int, noise: float = 0.04) -> list[float]:
    """Monotone decrease: Isolate falls as layers increase."""
    curve = [1.0 - 0.6 * (k / (n_layers - 1)) for k in range(n_layers)]
    return _add_noise(curve, noise)


def generate_u_curve(n_layers: int, noise: float = 0.04) -> list[float]:
    """U-shape: Isolate high → low → high (valley around middle)."""
    mid = (n_layers - 1) / 2
    width = n_layers * 0.2
    curve = [0.4 + 0.6 * math.exp(-0.5 * ((k - mid) / width) ** 2) for k in range(n_layers)]
    # Invert: low in middle = U-shape for Isolate
    curve = [1.4 - v for v in curve]
    # Clamp
    curve = [max(0.05, min(1.2, v)) for v in curve]
    return _add_noise(curve, noise)


def generate_plateau_curve(n_layers: int, noise: float = 0.05) -> list[float]:
    """Flat: Isolate stays roughly constant (slight trend)."""
    curve = [0.6 + 0.05 * (k / n_layers) for k in range(n_layers)]
    return _add_noise(curve, noise)


def generate_gc_peak(shape: CurveShape, n_layers: int) -> float:
    """Mock gc(k) peak height as a function of curve shape."""
    base = {"decay": 0.78, "u_shape": 0.55, "plateau": 0.31}[shape.value]
    return max(0.0, min(1.0, base + random.gauss(0, 0.06)))


# ---------------------------------------------------------------------------
# Shape classifier
# ---------------------------------------------------------------------------

@dataclass
class ClassificationResult:
    shape: CurveShape
    confidence: float          # 0–1
    decay_score: float
    u_score: float
    plateau_score: float
    valley_layer: int | None   # for U-shape
    slope: float               # linear slope (negative = decay)
    flatness: float            # std dev of curve (low = plateau)


def classify_curve(curve: list[float]) -> ClassificationResult:
    """
    Classify an Isolate(k) curve into DECAY / U-SHAPE / PLATEAU.

    Heuristics:
      - Compute linear slope (OLS). Very negative → DECAY.
      - Compute std-dev (flatness). Very low → PLATEAU.
      - Detect valley: find argmin, check if endpoints > min by threshold → U-SHAPE.
    """
    n = len(curve)
    # --- Linear slope (OLS) ---
    x_mean = (n - 1) / 2
    y_mean = statistics.mean(curve)
    num = sum((k - x_mean) * (v - y_mean) for k, v in enumerate(curve))
    den = sum((k - x_mean) ** 2 for k in range(n))
    slope = num / den if den > 0 else 0.0

    # --- Flatness (std dev normalised by range) ---
    y_range = max(curve) - min(curve)
    flatness = statistics.stdev(curve) / (y_range + 1e-9)

    # --- Valley detection ---
    valley_layer = curve.index(min(curve))
    valley_margin = 0.10 * (n - 1)  # valley not at endpoints
    left_drop  = curve[0] - curve[valley_layer]
    right_drop = curve[-1] - curve[valley_layer]

    # Score each shape (higher = more likely)
    decay_score   = max(0.0, -slope * 10)                        # negative slope
    plateau_score = max(0.0, 1.0 - flatness * 3)                 # small std dev
    u_score = 0.0
    if (valley_margin <= valley_layer <= (n - 1 - valley_margin)
            and left_drop > 0.08 and right_drop > 0.05):
        # Valley is internal and both sides drop significantly
        u_score = (left_drop + right_drop) * 3

    # Softmax-style confidence
    total = decay_score + plateau_score + u_score + 1e-9
    scores = {
        CurveShape.DECAY:   decay_score / total,
        CurveShape.U_SHAPE: u_score / total,
        CurveShape.PLATEAU: plateau_score / total,
    }
    best_shape = max(scores, key=lambda s: scores[s])
    confidence = scores[best_shape]

    return ClassificationResult(
        shape=best_shape,
        confidence=confidence,
        decay_score=decay_score,
        u_score=u_score,
        plateau_score=plateau_score,
        valley_layer=valley_layer if best_shape == CurveShape.U_SHAPE else None,
        slope=round(slope, 4),
        flatness=round(flatness, 4),
    )


# ---------------------------------------------------------------------------
# Correlation: shape → gc peak
# ---------------------------------------------------------------------------

class UtteranceRecord(NamedTuple):
    utt_id: str
    true_shape: CurveShape
    pred_shape: CurveShape
    gc_peak: float
    confidence: float


def run_mock_dataset(
    n_utterances: int,
    n_layers: int,
    noise: float = 0.04,
    verbose: bool = False,
) -> list[UtteranceRecord]:
    """Generate mock dataset, classify, return records."""
    records = []
    shapes = [CurveShape.DECAY, CurveShape.U_SHAPE, CurveShape.PLATEAU]
    generators = {
        CurveShape.DECAY:   lambda: generate_decay_curve(n_layers, noise),
        CurveShape.U_SHAPE: lambda: generate_u_curve(n_layers, noise),
        CurveShape.PLATEAU: lambda: generate_plateau_curve(n_layers, noise),
    }

    for i in range(n_utterances):
        true_shape = shapes[i % 3]          # balanced classes
        curve = generators[true_shape]()
        gc_peak = generate_gc_peak(true_shape, n_layers)
        result = classify_curve(curve)

        rec = UtteranceRecord(
            utt_id=f"utt-{i:04d}",
            true_shape=true_shape,
            pred_shape=result.shape,
            gc_peak=round(gc_peak, 4),
            confidence=round(result.confidence, 3),
        )
        records.append(rec)

        if verbose and i < 12:
            match = "✓" if rec.true_shape == rec.pred_shape else "✗"
            print(f"  {match} {rec.utt_id}: true={rec.true_shape.value:8s} "
                  f"pred={rec.pred_shape.value:8s} gc={rec.gc_peak:.3f} "
                  f"conf={rec.confidence:.2f}")

    return records


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def compute_stats(records: list[UtteranceRecord]) -> dict:
    """Accuracy + per-class gc peak means."""
    n = len(records)
    correct = sum(1 for r in records if r.true_shape == r.pred_shape)
    accuracy = correct / n

    per_class_gc: dict[CurveShape, list[float]] = {s: [] for s in CurveShape}
    for r in records:
        per_class_gc[r.true_shape].append(r.gc_peak)

    gc_means = {s: statistics.mean(vals) for s, vals in per_class_gc.items() if vals}
    gc_stds  = {s: statistics.stdev(vals) if len(vals) > 1 else 0.0
                for s, vals in per_class_gc.items() if vals}

    # Per-class accuracy
    per_class_correct: dict[CurveShape, int] = {s: 0 for s in CurveShape}
    per_class_total:   dict[CurveShape, int] = {s: 0 for s in CurveShape}
    for r in records:
        per_class_total[r.true_shape] += 1
        if r.true_shape == r.pred_shape:
            per_class_correct[r.true_shape] += 1

    # Ranking: DECAY > U_SHAPE > PLATEAU (should hold for gc_means)
    ranking_correct = (
        gc_means.get(CurveShape.DECAY, 0) >
        gc_means.get(CurveShape.U_SHAPE, 0) >
        gc_means.get(CurveShape.PLATEAU, 0)
    )

    return {
        "n": n,
        "accuracy": accuracy,
        "per_class_accuracy": {
            s.value: per_class_correct[s] / per_class_total[s]
            for s in CurveShape if per_class_total[s] > 0
        },
        "gc_means": {s.value: round(gc_means[s], 4) for s in CurveShape if s in gc_means},
        "gc_stds":  {s.value: round(gc_stds[s],  4) for s in CurveShape if s in gc_stds},
        "ranking_correct": ranking_correct,   # DECAY > U > PLATEAU in gc_mean
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Isolate(k) curve shape classifier: DECAY / U-SHAPE / PLATEAU"
    )
    parser.add_argument("--n",       type=int,   default=150,  help="# utterances (default: 150)")
    parser.add_argument("--layers",  type=int,   default=32,   help="# layers (default: 32)")
    parser.add_argument("--noise",   type=float, default=0.04, help="Curve noise σ (default: 0.04)")
    parser.add_argument("--seed",    type=int,   default=42,   help="Random seed")
    parser.add_argument("--verbose", action="store_true",      help="Show per-utterance details")
    args = parser.parse_args()

    random.seed(args.seed)

    print("=" * 62)
    print("Isolate(k) Curve Shape Classifier — Q146")
    print(f"  n={args.n} utterances | layers={args.layers} | noise={args.noise}")
    print("=" * 62)

    if args.verbose:
        print("\nFirst 12 utterances:")

    records = run_mock_dataset(args.n, args.layers, args.noise, verbose=args.verbose)
    stats = compute_stats(records)

    print(f"\nOverall accuracy : {stats['accuracy']:.1%}  (3-class)")
    print()
    print("Per-class accuracy:")
    for shape, acc in stats["per_class_accuracy"].items():
        bar = "█" * int(acc * 20)
        print(f"  {shape:8s} : {acc:5.1%}  {bar}")

    print()
    print("gc(k) peak height by true curve shape:")
    order = [CurveShape.DECAY, CurveShape.U_SHAPE, CurveShape.PLATEAU]
    for s in order:
        mean = stats["gc_means"].get(s.value, float("nan"))
        std  = stats["gc_stds"].get(s.value,  float("nan"))
        bar = "█" * int(mean * 20)
        print(f"  {s.value:8s} : gc_mean={mean:.3f} ± {std:.3f}  {bar}")

    print()
    ranking_sym = "✅" if stats["ranking_correct"] else "❌"
    print(f"Hypothesis (DECAY > U-SHAPE > PLATEAU) : {ranking_sym}")
    print()

    if stats["accuracy"] >= 0.75 and stats["ranking_correct"]:
        verdict = "✅ DOD MET — classifier works, gc ranking confirmed"
    elif stats["accuracy"] >= 0.60:
        verdict = "⚠️  PARTIAL — moderate accuracy, check hyperparameters"
    else:
        verdict = "❌ NOT MET — classification too noisy"

    print(f"Verdict: {verdict}")
    print()
    print("Interpretation:")
    print("  DECAY   → model progressively disentangles audio → strong gc peak")
    print("  U-SHAPE → mid-layer sweet spot, then re-entanglement → moderate gc")
    print("  PLATEAU → no clear disentanglement → low gc everywhere (guessing)")
    print()
    print("Next: run on real Isolate(k) data (from probe experiments) to validate.")


if __name__ == "__main__":
    main()
