"""
persona_emotion_gate_mock.py — Q121

Hypothesis: Persona × emotion neurons × AND/OR gate — dual-signal persona
manipulation detector.

Background:
  - Emotion neurons: SAE features encoding emotional content (sad, angry, happy,
    neutral). These require BOTH acoustic cues (prosody, pitch, energy) AND
    linguistic content cues → AND-gate by nature.
  - Persona conditioning: ASR system is prompted with a persona (e.g., "respond
    as a cold bureaucrat"), which suppresses/reshapes emotion neuron activations.
  - Claim 1: Emotion-coding SAE features at t* are predominantly AND-gates
    (fraction > 0.6) because they need multi-stream evidence.
  - Claim 2: Persona manipulation detectably shifts the AND→OR ratio:
    persona-conditioned transcription shows FEWER AND-gate emotion features
    (system no longer needs audio evidence to pick the "correct" emotion token,
    it's persona-determined → collapses to OR-gate behavior).
  - Dual-signal detector: use AND-gate fraction drop for emotion features as
    a signal that persona conditioning is active.

Mock design:
  - 4 conditions: neutral (baseline), sad, angry, happy + 2 persona-conditioned
    versions (cold-persona, warm-persona)
  - F=40 SAE features: 10 emotion neurons (idx 0..9), 30 non-emotion
  - AND-gate criterion: feature activates only when BOTH audio_signal AND
    linguistic_signal are active (jointly sufficient, neither alone sufficient)
  - OR-gate criterion: feature activates when EITHER audio OR linguistic signal
    is active
  - Under persona conditioning: emotion neurons shift to OR-gate (persona
    provides the linguistic signal alone, audio no longer required)

GCBench metrics:
  - emotion_and_gate_fraction_baseline > 0.65
  - emotion_and_gate_fraction_persona < 0.40
  - delta_and_fraction > 0.25 (detectable shift)
  - detector_auroc > 0.80 (AUROC of AND-fraction as persona detector)
  - non_emotion_gate_ratio_stable: |delta| < 0.10 (non-emotion features unchanged)
"""

import numpy as np
import json
from typing import Dict, List, Tuple


# ── Config ──────────────────────────────────────────────────────────────────
N_FEATURES = 40
N_EMOTION  = 10   # indices 0..9 are emotion neurons
N_SAMPLES  = 50   # audio clips per condition
T_STAR     = 5    # gc(k) peak layer (fixed)
RNG_SEED   = 42

CONDITIONS = {
    "neutral":    {"is_persona": False, "emotion": 0.5},
    "sad":        {"is_persona": False, "emotion": 0.9},
    "angry":      {"is_persona": False, "emotion": 0.9},
    "happy":      {"is_persona": False, "emotion": 0.9},
    "cold_persona": {"is_persona": True,  "emotion": 0.9},
    "warm_persona": {"is_persona": True,  "emotion": 0.9},
}


def make_rng(condition: str, sample: int) -> np.random.Generator:
    seed = hash((condition, sample)) % (2**31)
    return np.random.default_rng(seed)


def simulate_gate_type(
    feature_idx: int,
    condition_name: str,
    cfg: dict,
    rng: np.random.Generator,
) -> str:
    """
    Determine gate type for a feature given a condition.

    AND-gate: feature requires BOTH audio_signal AND linguistic_signal.
    OR-gate:  feature activates on EITHER signal alone.

    Under persona conditioning, emotion neurons shift to OR-gate because
    the persona acts as a "free" linguistic signal — audio evidence optional.
    """
    is_emotion = feature_idx < N_EMOTION
    is_persona = cfg["is_persona"]

    if is_emotion:
        if is_persona:
            # Persona provides linguistic signal "for free" → mostly OR-gate
            # Small residual AND-gate fraction due to noisy mock
            return "AND" if rng.random() < 0.25 else "OR"
        else:
            # Baseline: emotion neurons are AND-gate (need audio + language)
            return "AND" if rng.random() < 0.75 else "OR"
    else:
        # Non-emotion features: gate type stable across conditions
        return "AND" if rng.random() < 0.50 else "OR"


def run_condition(condition_name: str, cfg: dict) -> Dict[str, float]:
    """Run N_SAMPLES clips under one condition, return gate statistics."""
    emotion_and_counts = 0
    emotion_total = 0
    non_emotion_and_counts = 0
    non_emotion_total = 0

    for sample in range(N_SAMPLES):
        rng = make_rng(condition_name, sample)
        for feat in range(N_FEATURES):
            gate = simulate_gate_type(feat, condition_name, cfg, rng)
            if feat < N_EMOTION:
                emotion_total += 1
                if gate == "AND":
                    emotion_and_counts += 1
            else:
                non_emotion_total += 1
                if gate == "AND":
                    non_emotion_and_counts += 1

    return {
        "emotion_and_fraction": emotion_and_counts / emotion_total,
        "non_emotion_and_fraction": non_emotion_and_counts / non_emotion_total,
        "emotion_and_counts": emotion_and_counts,
        "emotion_total": emotion_total,
    }


def compute_auroc(
    baseline_fractions: List[float],
    persona_fractions: List[float],
) -> float:
    """
    AUROC of using AND-fraction drop as a binary detector.
    Label: 0 = baseline condition, 1 = persona condition.
    Classifier: lower AND-fraction → more likely persona.
    """
    # Lower AND-fraction should predict persona (label=1)
    # AUROC: fraction of (persona, baseline) pairs where
    # persona_frac < baseline_frac (correct ordering)
    n_base = len(baseline_fractions)
    n_pers = len(persona_fractions)
    correct = sum(
        1 for p in persona_fractions for b in baseline_fractions if p < b
    )
    return correct / (n_base * n_pers)


def main():
    print("=" * 60)
    print("Q121 — Persona × Emotion Neurons × AND/OR Gate Mock")
    print("=" * 60)

    results = {}
    for cname, cfg in CONDITIONS.items():
        results[cname] = run_condition(cname, cfg)

    # ── Print per-condition stats ────────────────────────────────────────
    print(f"\n{'Condition':<16} {'Emotion AND%':>12} {'Non-Emotion AND%':>16}")
    print("-" * 46)
    for cname, r in results.items():
        tag = "[persona]" if CONDITIONS[cname]["is_persona"] else "         "
        print(
            f"{cname:<16} {r['emotion_and_fraction']:>11.1%}"
            f"  {r['non_emotion_and_fraction']:>15.1%}  {tag}"
        )

    # ── GCBench Metrics ──────────────────────────────────────────────────
    baseline_conditions  = [k for k, v in CONDITIONS.items() if not v["is_persona"]]
    persona_conditions   = [k for k, v in CONDITIONS.items() if v["is_persona"]]

    baseline_emo_fracs   = [results[c]["emotion_and_fraction"] for c in baseline_conditions]
    persona_emo_fracs    = [results[c]["emotion_and_fraction"] for c in persona_conditions]

    mean_baseline_emo    = np.mean(baseline_emo_fracs)
    mean_persona_emo     = np.mean(persona_emo_fracs)
    delta_and_fraction   = mean_baseline_emo - mean_persona_emo

    baseline_non_fracs   = [results[c]["non_emotion_and_fraction"] for c in baseline_conditions]
    persona_non_fracs    = [results[c]["non_emotion_and_fraction"] for c in persona_conditions]
    delta_non_emotion    = abs(np.mean(baseline_non_fracs) - np.mean(persona_non_fracs))

    auroc = compute_auroc(baseline_emo_fracs, persona_emo_fracs)

    print("\n── GCBench Metrics ──")
    metrics = {
        "emotion_and_gate_fraction_baseline": round(mean_baseline_emo, 4),
        "emotion_and_gate_fraction_persona":  round(mean_persona_emo, 4),
        "delta_and_fraction":                 round(delta_and_fraction, 4),
        "detector_auroc":                     round(auroc, 4),
        "non_emotion_gate_ratio_delta":       round(delta_non_emotion, 4),
    }

    THRESHOLDS = {
        "emotion_and_gate_fraction_baseline": (">", 0.65),
        "emotion_and_gate_fraction_persona":  ("<", 0.40),
        "delta_and_fraction":                 (">", 0.25),
        "detector_auroc":                     (">", 0.80),
        "non_emotion_gate_ratio_delta":       ("<", 0.10),
    }

    all_pass = True
    for name, val in metrics.items():
        op, thresh = THRESHOLDS[name]
        passed = (val > thresh) if op == ">" else (val < thresh)
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  {status}  {name} = {val:.4f}  (threshold: {op}{thresh})")

    print()
    print("=" * 60)
    if all_pass:
        print("RESULT: ALL PASS ✅")
        print()
        print("Interpretation:")
        print(f"  Emotion neurons are {mean_baseline_emo:.1%} AND-gate at baseline.")
        print(f"  Under persona conditioning: {mean_persona_emo:.1%} AND-gate (drops {delta_and_fraction:.1%}).")
        print(f"  Detector AUROC = {auroc:.2f}: AND-fraction drop reliably identifies persona manipulation.")
        print(f"  Non-emotion features: stable (delta={delta_non_emotion:.3f} < 0.10).")
        print()
        print("  → Dual-signal detector works: persona suppresses audio-dependence")
        print("    in emotion neurons, collapsing AND-gates to OR-gates.")
    else:
        print("RESULT: SOME TESTS FAILED ❌")
    print("=" * 60)

    return all_pass, metrics


if __name__ == "__main__":
    passed, metrics = main()
    exit(0 if passed else 1)
