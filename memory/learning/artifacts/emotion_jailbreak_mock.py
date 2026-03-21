"""
emotion_jailbreak_mock.py — Q138

Hypothesis: Jailbreak attacks on audio LLMs suppress emotion AND-gates.
Clean audio → emotion SAE features are AND-gated (need audio + context).
Jailbreak audio → emotion AND-frac collapses below 0.4 (OR-gate shift).
Combines Q118 (emotion neuron gating) + Q128 (AND-frac confidence) + ENV-3
(isolated emotion feature pruning as jailbreak signature).

Background:
  - Emotion features in Whisper/audio-LLMs are AND-gate: they require BOTH
    acoustic cues (prosody, pitch, energy envelope) AND semantic context cues.
  - Jailbreaks work by injecting adversarial audio that disrupts acoustic
    signal integrity → emotion features lose audio grounding → shift to OR-gate
    (text/context driven only).
  - ENV-3 signature: ENV-3 features are "isolated" (sparse, specific). Under
    jailbreak, ENV-3 emotion features get pruned from the active set.
  - Combined metric: low emotion AND-frac + ENV-3 emotion cluster shrinkage
    → reliable jailbreak detection signal.

Mock design:
  - 3 conditions: clean, audio-jailbreak (FGSM-style), text-jailbreak (prompt injection)
  - F=50 SAE features: 12 emotion (ENV-3, idx 0..11), 8 emotion (ENV-1 hub, idx 12..19),
    30 non-emotion
  - Clean: emotion AND-gate dominant (>0.70 for ENV-3, >0.60 for ENV-1)
  - Audio jailbreak: ENV-3 emotion features collapse (AND-frac < 0.35) — acoustic
    signal corrupted → audio no longer sufficient partner for AND-gate
  - Text jailbreak: moderate collapse (AND-frac ~ 0.45-0.50) — less impact on
    acoustic processing, more on semantic routing
  - ENV-3 cluster size: number of ENV-3 emotion features with activation > threshold;
    drops under audio jailbreak (ENV-3 pruning signature)

GCBench thresholds:
  - emotion_and_frac_clean > 0.70
  - emotion_and_frac_audio_jailbreak < 0.40
  - emotion_and_frac_text_jailbreak in [0.40, 0.60]  (partial collapse)
  - env3_cluster_size_clean > 8
  - env3_cluster_size_audio_jailbreak < 5
  - detector_auroc_audio > 0.85
  - non_emotion_gate_delta < 0.10   (non-emotion features stable)
"""

import numpy as np
import json
from typing import Dict, List, Tuple

# ── Config ──────────────────────────────────────────────────────────────────
N_ENV3_EMOTION  = 12   # idx 0..11: ENV-3 isolated emotion features
N_ENV1_EMOTION  = 8    # idx 12..19: ENV-1 hub emotion features
N_NON_EMOTION   = 30   # idx 20..49
N_FEATURES      = N_ENV3_EMOTION + N_ENV1_EMOTION + N_NON_EMOTION  # 50
N_SAMPLES       = 60   # clips per condition

CONDITIONS = {
    "clean": {
        "jailbreak": False,
        "audio_disruption": 0.0,   # 0 = pristine, 1 = fully corrupted
        "text_disruption":  0.0,
    },
    "audio_jailbreak": {
        "jailbreak": True,
        "audio_disruption": 0.85,  # FGSM-style — acoustic signal corrupted
        "text_disruption":  0.10,
    },
    "text_jailbreak": {
        "jailbreak": True,
        "audio_disruption": 0.20,  # prompt injection — audio mostly intact
        "text_disruption":  0.75,
    },
}

ENV3_ACTIVATION_THRESHOLD = 0.5  # for ENV-3 cluster size count


def make_rng(condition: str, sample: int, feature: int) -> np.random.Generator:
    seed = hash((condition, sample, feature)) % (2**31)
    return np.random.default_rng(seed)


def gate_type(feat_idx: int, cfg: dict, rng: np.random.Generator) -> str:
    """
    AND-gate: requires both audio_signal AND linguistic_signal.
    Under audio disruption: audio signal unreliable → AND collapses to OR.
    Under text disruption: linguistic routing altered → partial AND collapse.
    """
    is_env3  = feat_idx < N_ENV3_EMOTION
    is_env1  = N_ENV3_EMOTION <= feat_idx < N_ENV3_EMOTION + N_ENV1_EMOTION
    is_emotion = feat_idx < N_ENV3_EMOTION + N_ENV1_EMOTION

    audio_d = cfg["audio_disruption"]
    text_d  = cfg["text_disruption"]

    if is_emotion:
        if is_env3:
            # ENV-3 features: highly audio-dependent → very sensitive to audio disruption
            # Baseline AND-prob = 0.80
            and_prob = 0.80 * (1 - audio_d) * (1 - 0.3 * text_d)
        else:
            # ENV-1 hub: shared / less audio-specific → less sensitive
            # Baseline AND-prob = 0.65
            and_prob = 0.65 * (1 - 0.5 * audio_d) * (1 - 0.4 * text_d)
        and_prob = float(np.clip(and_prob, 0.0, 1.0))
    else:
        # Non-emotion: ~50% AND-gate, stable across conditions
        and_prob = 0.50 + 0.05 * (rng.random() - 0.5)  # small noise

    return "AND" if rng.random() < and_prob else "OR"


def env3_activation(feat_idx: int, cfg: dict, rng: np.random.Generator) -> float:
    """
    Simulate activation magnitude for ENV-3 features.
    Audio jailbreak prunes ENV-3 activations (below threshold → inactive).
    """
    if feat_idx >= N_ENV3_EMOTION:
        return 0.0  # only for ENV-3

    base_activation = 0.70 + 0.20 * rng.random()   # clean: 0.70-0.90
    suppression = cfg["audio_disruption"] * 0.75    # audio jailbreak suppresses
    return float(np.clip(base_activation - suppression, 0.0, 1.0))


def run_condition(cname: str, cfg: dict) -> Dict:
    emotion_env3_and = 0
    emotion_env3_total = 0
    emotion_env1_and = 0
    emotion_env1_total = 0
    non_emotion_and = 0
    non_emotion_total = 0

    env3_active_counts = []  # per sample: how many ENV-3 features active

    for s in range(N_SAMPLES):
        active_env3 = 0
        for f in range(N_FEATURES):
            rng = make_rng(cname, s, f)
            gate = gate_type(f, cfg, rng)

            if f < N_ENV3_EMOTION:
                act = env3_activation(f, cfg, rng)
                if act > ENV3_ACTIVATION_THRESHOLD:
                    active_env3 += 1
                emotion_env3_total += 1
                if gate == "AND":
                    emotion_env3_and += 1
            elif f < N_ENV3_EMOTION + N_ENV1_EMOTION:
                emotion_env1_total += 1
                if gate == "AND":
                    emotion_env1_and += 1
            else:
                non_emotion_total += 1
                if gate == "AND":
                    non_emotion_and += 1

        env3_active_counts.append(active_env3)

    total_emotion_and = emotion_env3_and + emotion_env1_and
    total_emotion_total = emotion_env3_total + emotion_env1_total

    return {
        "emotion_and_frac_all": total_emotion_and / total_emotion_total,
        "emotion_and_frac_env3": emotion_env3_and / emotion_env3_total,
        "emotion_and_frac_env1": emotion_env1_and / emotion_env1_total,
        "non_emotion_and_frac": non_emotion_and / non_emotion_total,
        "env3_cluster_size_mean": float(np.mean(env3_active_counts)),
        "env3_cluster_size_std": float(np.std(env3_active_counts)),
    }


def compute_auroc(clean_fracs: List[float], jailbreak_fracs: List[float]) -> float:
    """AUROC: lower AND-frac → predict jailbreak. Return fraction correct pairs."""
    n_c = len(clean_fracs)
    n_j = len(jailbreak_fracs)
    correct = sum(1 for j in jailbreak_fracs for c in clean_fracs if j < c)
    return correct / (n_c * n_j)


def main():
    print("=" * 65)
    print("Q138 — Emotion AND-gate Suppression as Jailbreak Success Metric")
    print("=" * 65)

    results = {cname: run_condition(cname, cfg) for cname, cfg in CONDITIONS.items()}

    # ── Per-condition table ──────────────────────────────────────────────
    print(f"\n{'Condition':<18} {'Emo-ALL AND%':>12} {'ENV3 AND%':>10} "
          f"{'ENV1 AND%':>10} {'ENV3 Active':>12} {'NonEmo AND%':>12}")
    print("-" * 76)
    for cname, r in results.items():
        tag = " [JB]" if CONDITIONS[cname]["jailbreak"] else "     "
        print(
            f"{cname:<18} {r['emotion_and_frac_all']:>11.1%}"
            f"  {r['emotion_and_frac_env3']:>9.1%}"
            f"  {r['emotion_and_frac_env1']:>9.1%}"
            f"  {r['env3_cluster_size_mean']:>8.1f}±{r['env3_cluster_size_std']:.1f}"
            f"  {r['non_emotion_and_frac']:>11.1%}  {tag}"
        )

    # ── Compute AUROC on per-sample bootstrap ────────────────────────────
    # Bootstrap per-sample AND-frac by treating each sample's ENV-3 fraction
    # We'll use per-feature gate probabilities as proxy via the condition means
    clean_frac  = results["clean"]["emotion_and_frac_all"]
    audio_frac  = results["audio_jailbreak"]["emotion_and_frac_all"]
    text_frac   = results["text_jailbreak"]["emotion_and_frac_all"]

    # Simulate N_SAMPLES observations from a Beta distribution centered on each mean
    rng_auroc = np.random.default_rng(99)
    def beta_samples(mean, n=N_SAMPLES, dispersion=30):
        a = mean * dispersion
        b = (1 - mean) * dispersion
        return rng_auroc.beta(a, b, size=n).tolist()

    clean_samples       = beta_samples(clean_frac)
    audio_jb_samples    = beta_samples(audio_frac)
    text_jb_samples     = beta_samples(text_frac)

    auroc_audio = compute_auroc(clean_samples, audio_jb_samples)
    auroc_text  = compute_auroc(clean_samples, text_jb_samples)

    env3_clean_size = results["clean"]["env3_cluster_size_mean"]
    env3_audio_size = results["audio_jailbreak"]["env3_cluster_size_mean"]
    text_in_range   = 0.40 <= text_frac <= 0.60

    # ── GCBench Metrics ──────────────────────────────────────────────────
    print("\n── GCBench Metrics ──")
    metrics_tests = [
        ("emotion_and_frac_clean",               clean_frac,      ">",  0.70),
        ("emotion_and_frac_audio_jailbreak",      audio_frac,      "<",  0.40),
        ("emotion_and_frac_text_jailbreak_in_range",
                                                  float(text_in_range), ">", 0.5),
        ("env3_cluster_size_clean",               env3_clean_size, ">",  8.0),
        ("env3_cluster_size_audio_jailbreak",     env3_audio_size, "<",  5.0),
        ("detector_auroc_audio",                  auroc_audio,     ">",  0.85),
        ("detector_auroc_text",                   auroc_text,      ">",  0.65),
        ("non_emotion_gate_delta",
         abs(results["clean"]["non_emotion_and_frac"]
             - results["audio_jailbreak"]["non_emotion_and_frac"]),
         "<", 0.10),
    ]

    all_pass = True
    pass_results = {}
    for name, val, op, thresh in metrics_tests:
        passed = (val > thresh) if op == ">" else (val < thresh)
        if not passed:
            all_pass = False
        status = "PASS" if passed else "FAIL"
        pass_results[name] = passed
        print(f"  {status}  {name} = {val:.4f}  (threshold: {op}{thresh})")

    print()
    print("=" * 65)
    if all_pass:
        print("RESULT: ALL PASS ✅")
        print()
        print("Interpretation:")
        print(f"  Clean: emotion AND-frac = {clean_frac:.1%}  (audio-grounded gating)")
        print(f"  Audio JB: AND-frac drops to {audio_frac:.1%}  (audio signal corrupted)")
        print(f"  Text JB: AND-frac = {text_frac:.1%}  (partial — audio still present)")
        print(f"  ENV-3 cluster: {env3_clean_size:.0f} active clean → {env3_audio_size:.0f} under audio JB")
        print(f"  AUROC (audio JB detector) = {auroc_audio:.2f}")
        print(f"  AUROC (text JB detector)  = {auroc_text:.2f}")
        print()
        print("  Key insight: Audio jailbreaks have a DISTINCT ENV-3 signature")
        print("  — both AND-frac drop AND ENV-3 cluster shrinkage. Text jailbreaks")
        print("  show partial AND collapse but ENV-3 cluster stays larger.")
        print("  → Dual-signal (AND-frac + ENV-3 size) distinguishes attack type.")
    else:
        print("RESULT: SOME TESTS FAILED ❌")
    print("=" * 65)

    output = {
        "task": "Q138",
        "all_pass": all_pass,
        "metrics": {name: val for name, val, op, thresh in metrics_tests},
        "gcbench_pass": {name: passed for name, passed in pass_results.items()},
        "condition_results": {
            c: {k: round(v, 4) for k, v in r.items()}
            for c, r in results.items()
        },
    }
    print("\nJSON output:")
    print(json.dumps(output, indent=2))
    return all_pass, output


if __name__ == "__main__":
    passed, _ = main()
    exit(0 if passed else 1)
