#!/usr/bin/env python3
"""
Q121 — persona_emotion_and_or.py
Persona × emotion neurons × AND/OR gate: dual-signal features.
Mock: combine persona_gc + emotion patterns. 3 personas × 50 features.
"""
import argparse
import json
import sys
import numpy as np
from dataclasses import dataclass, asdict
from typing import List, Dict


PERSONAS = ["neutral", "assistant", "anti_ground"]

@dataclass
class PersonaEmotionResult:
    persona: str
    emotion_and_frac: float
    emotion_or_frac: float
    nonemot_and_frac: float
    nonemot_or_frac: float
    dual_signal_frac: float  # features showing both emotion AND persona shift
    gc_peak_shift: float     # relative to neutral


def parse_args():
    p = argparse.ArgumentParser(description="Q121: Persona × emotion neurons × AND/OR gate")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-features", type=int, default=50)
    p.add_argument("--n-stimuli", type=int, default=60)
    p.add_argument("--json", action="store_true")
    return p.parse_args()


def classify_gate(clean, noisy, patched, thresh=0.3):
    if clean < thresh and noisy < thresh:
        return "silent"
    if noisy >= thresh * 0.8:
        return "or"
    if noisy < thresh * 0.5 and patched >= thresh * 0.8:
        return "and"
    return "passthrough"


def generate_persona_emotion_activations(rng, n_features, n_stimuli, persona, is_emotion):
    """
    Activations depend on both persona and emotion status.
    - assistant persona: boosts text-context signal → more AND-gate behavior
    - anti_ground: boosts audio signal → more OR-gate behavior
    - emotion features: already AND-gate biased (both signals needed)
    """
    # Persona modulates context signal strength
    if persona == "neutral":
        ctx_weight = 0.5
        aud_weight = 0.5
        gc_shift   = 0.0
    elif persona == "assistant":
        ctx_weight = 0.7
        aud_weight = 0.3
        gc_shift   = +1.5
    else:  # anti_ground
        ctx_weight = 0.3
        aud_weight = 0.7
        gc_shift   = -1.5

    clean   = np.zeros((n_features, n_stimuli))
    noisy   = np.zeros((n_features, n_stimuli))
    patched = np.zeros((n_features, n_stimuli))

    for f in range(n_features):
        base = rng.uniform(0.5, 0.85, size=n_stimuli)
        clean[f] = base + rng.standard_normal(n_stimuli) * 0.04

        # Gate type probability: emotion + persona interaction
        if is_emotion:
            p_and = 0.55 + ctx_weight * 0.3
        else:
            p_and = 0.2  + ctx_weight * 0.1

        p_or  = 1.0 - p_and

        for s in range(n_stimuli):
            if rng.random() < p_and:
                noisy[f, s]   = base[s] * rng.uniform(0.05, 0.25)
                patched[f, s] = base[s] * rng.uniform(0.80, 1.00)
            else:
                noisy[f, s]   = base[s] * rng.uniform(0.70, 0.95)
                patched[f, s] = base[s] * rng.uniform(0.80, 1.00)

        noisy[f]   += rng.standard_normal(n_stimuli) * 0.04
        patched[f] += rng.standard_normal(n_stimuli) * 0.04

    return clean, noisy, patched, gc_shift


def compute_gate_dist(clean, noisy, patched, thresh=0.3):
    n_f, n_s = clean.shape
    counts = {"and": 0, "or": 0, "passthrough": 0, "silent": 0}
    feature_gates = []
    for f in range(n_f):
        per_s = {}
        for g in counts:
            per_s[g] = 0
        for s in range(n_s):
            g = classify_gate(clean[f, s], noisy[f, s], patched[f, s], thresh)
            per_s[g] += 1
        majority = max(per_s, key=per_s.get)
        feature_gates.append(majority)
        counts[majority] += 1
    total = n_f
    return {k: v / total for k, v in counts.items()}, feature_gates


def run_experiment(args):
    rng = np.random.default_rng(args.seed)
    n_emo = args.n_features
    n_non = args.n_features

    print("Q121: Persona × Emotion Neurons × AND/OR Gate")
    print(f"  Features/group: {args.n_features}, Stimuli: {args.n_stimuli}, Seed: {args.seed}")
    print()

    results: List[PersonaEmotionResult] = []
    neutral_and_emo = None

    for persona in PERSONAS:
        cl_e, no_e, pa_e, gc_shift = generate_persona_emotion_activations(
            rng, n_emo, args.n_stimuli, persona, is_emotion=True)
        cl_ne, no_ne, pa_ne, _ = generate_persona_emotion_activations(
            rng, n_non, args.n_stimuli, persona, is_emotion=False)

        dist_e,  g_e  = compute_gate_dist(cl_e, no_e, pa_e)
        dist_ne, g_ne = compute_gate_dist(cl_ne, no_ne, pa_ne)

        # Dual-signal: features that switch gate type under this persona vs neutral
        # Proxy: fraction of emotion features that are AND-gate
        dual_frac = dist_e["and"] * dist_e["or"]  # both types present

        res = PersonaEmotionResult(
            persona=persona,
            emotion_and_frac=dist_e["and"],
            emotion_or_frac=dist_e["or"],
            nonemot_and_frac=dist_ne["and"],
            nonemot_or_frac=dist_ne["or"],
            dual_signal_frac=dual_frac,
            gc_peak_shift=gc_shift,
        )
        results.append(res)
        if persona == "neutral":
            neutral_and_emo = dist_e["and"]

    print(f"{'Persona':<14} {'EmoAND%':>8} {'EmoOR%':>8} {'NonAND%':>8} {'NonOR%':>8} "
          f"{'Dual%':>8} {'gcShift':>8}")
    print("-" * 68)
    for r in results:
        print(f"{r.persona:<14} {r.emotion_and_frac*100:>8.1f} {r.emotion_or_frac*100:>8.1f} "
              f"{r.nonemot_and_frac*100:>8.1f} {r.nonemot_or_frac*100:>8.1f} "
              f"{r.dual_signal_frac*100:>8.1f} {r.gc_peak_shift:>8.1f}")

    print()
    asst = next(r for r in results if r.persona == "assistant")
    anti = next(r for r in results if r.persona == "anti_ground")

    h1_pass = asst.emotion_and_frac > (neutral_and_emo or 0)
    print(f"H1: Assistant persona increases emotion AND-gate fraction")
    print(f"    assistant={asst.emotion_and_frac:.3f} > neutral={neutral_and_emo:.3f} "
          f"→ {'PASS' if h1_pass else 'FAIL'}")

    h2_pass = anti.emotion_and_frac < (neutral_and_emo or 1)
    print(f"H2: Anti-ground persona decreases emotion AND-gate fraction")
    print(f"    anti_ground={anti.emotion_and_frac:.3f} < neutral={neutral_and_emo:.3f} "
          f"→ {'PASS' if h2_pass else 'FAIL'}")

    h3_pass = all(r.emotion_and_frac > r.nonemot_and_frac for r in results)
    print(f"H3: Emotion features are more AND-gate than non-emotion in all personas")
    print(f"    All personas: {h3_pass} → {'PASS' if h3_pass else 'FAIL'}")

    if args.json:
        output = {
            "experiment": "Q121",
            "results": [asdict(r) for r in results],
            "h1": h1_pass, "h2": h2_pass, "h3": h3_pass,
        }
        print(json.dumps(output, indent=2))

    return results


def main():
    args = parse_args()
    run_experiment(args)
    print("\nQ121 complete.")
    sys.exit(0)


if __name__ == "__main__":
    main()
