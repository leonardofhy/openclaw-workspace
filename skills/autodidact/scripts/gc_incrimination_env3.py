#!/usr/bin/env python3
"""
gc-Incrimination + ENV-3 Phoneme-Conflict Motive Diagnostic — Q101
Track T3: Listen vs Guess (Paper A §5.4 Extension)

Extends gc_incrimination_mock.py with the ENV motive taxonomy from Q100.

ENV Taxonomy (gc(k) as behavioral motive signal):
  ENV-1  LISTEN   gc(k) ≥ τ_high consistently → model attends to audio evidence
  ENV-2  GUESS    gc(k) < τ_low consistently  → model ignores audio, relies on prior
  ENV-3  CONFLICT gc(k) oscillates between τ_low and τ_high across decoding steps
                  → audio and language prior are in active competition (phoneme conflict)
                  → t* captures the moment the language prior "wins" the conflict

ENV-3 Diagnostic:
  A stimulus is ENV-3 (phoneme-conflict) if:
    1. gc trajectory has high variance (std > σ_thresh)
    2. gc crosses τ boundary at least once (oscillation)
    3. Feature blame at conflict onset (t_conflict) shows mixed incrimination:
       some features support audio (negative blame), others support prior (positive blame)

This reflects the underlying mechanistic story:
  - In ENV-1: AND-gate audio features dominate → gc stays high
  - In ENV-2: OR-gate text features dominate → gc stays low
  - In ENV-3: audio vs text features are COMPETING → gc oscillates around τ
    The "winner" at each step is determined by feature dominance at that step.

Usage:
    python3 gc_incrimination_env3.py              # print full ENV-3 report
    python3 gc_incrimination_env3.py --json       # JSON output
    python3 gc_incrimination_env3.py --stimuli 50 # more stimuli
    python3 gc_incrimination_env3.py --sigma 0.05 # custom oscillation threshold

Dependencies: numpy only
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Optional

import numpy as np

# Re-use core machinery from gc_incrimination_mock.py
import importlib.util, os
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_mock_spec = importlib.util.spec_from_file_location(
    "gc_incrimination_mock",
    os.path.join(_SCRIPT_DIR, "gc_incrimination_mock.py"),
)
_mock = importlib.util.module_from_spec(_mock_spec)  # type: ignore
sys.modules["gc_incrimination_mock"] = _mock
_mock_spec.loader.exec_module(_mock)  # type: ignore

# Pull constants and functions from the mock module
N_STIMULI = _mock.N_STIMULI
T_STEPS = _mock.T_STEPS
N_SAE_FEATURES = _mock.N_SAE_FEATURES
GC_THRESHOLD_TAU = _mock.GC_THRESHOLD_TAU
SEED_BASE = _mock.SEED_BASE
build_temporal_profile = _mock.build_temporal_profile
compute_feature_incrimination = _mock.compute_feature_incrimination
mock_temporal_activations = _mock.mock_temporal_activations
compute_gc_at_t = _mock.compute_gc_at_t

# ENV-3 parameters
TAU_HIGH = 0.65      # above = clearly listening
TAU_LOW  = 0.45      # below = clearly guessing (mock calibrated; set empirically on real data)
SIGMA_THRESH = 0.08  # gc std across steps needed to flag ENV-3 oscillation


# ---------------------------------------------------------------------------
# ENV classification
# ---------------------------------------------------------------------------

ENV_LABELS = {1: "LISTEN", 2: "GUESS", 3: "CONFLICT"}


def classify_env(gc_trajectory: np.ndarray, sigma_thresh: float = SIGMA_THRESH) -> int:
    """
    Classify a stimulus's gc(k,t) trajectory into ENV-1, ENV-2, or ENV-3.

    Rules (in priority order):
      ENV-3: high variance (std > σ_thresh) AND trajectory crosses τ boundary
      ENV-1: mean gc ≥ τ_high  (stably listening)
      ENV-2: mean gc < τ_high  (stably guessing)

    Returns 1, 2, or 3.
    """
    mean_gc = float(np.mean(gc_trajectory))
    std_gc = float(np.std(gc_trajectory))
    crosses_boundary = bool(
        np.any(gc_trajectory >= TAU_HIGH) and np.any(gc_trajectory <= TAU_LOW)
    )

    if std_gc > sigma_thresh and crosses_boundary:
        return 3  # ENV-3: phoneme conflict
    elif mean_gc >= TAU_HIGH:
        return 1  # ENV-1: listening
    else:
        return 2  # ENV-2: guessing


# ---------------------------------------------------------------------------
# Phoneme-conflict scenario generator
# ---------------------------------------------------------------------------

def mock_env3_activations(
    stimulus_id: int,
    t: int,
    seed: int = SEED_BASE,
    conflict_peak_step: int = 2,
) -> dict[str, np.ndarray]:
    """
    Generate activations for an ENV-3 phoneme-conflict stimulus.

    The model receives an audio token whose phoneme is ambiguous between
    /p/ (audio evidence) and /b/ (language prior prediction). At each
    decoding step, the dominance alternates, creating a gc(k,t) oscillation.

    Mechanistic story:
      - Steps 0-1: audio features (f0-f4, AND-gate) briefly win → gc high
      - Step 2 (peak conflict): both sides activate simultaneously → gc in τ zone
      - Steps 3-4: language prior (text features f10-f14) wins → gc drops
      - The OR-gate features (f10-f14) are incriminated at t_conflict = step 2
    """
    rng = np.random.default_rng(seed + stimulus_id * 100 + t + 9999)
    hidden_dim = 64

    # Audio evidence for /p/ phoneme (strong early, weak late)
    audio_p = rng.standard_normal(hidden_dim) * 0.8
    # Language prior for /b/ phoneme (weak early, strong late)
    text_b = rng.standard_normal(hidden_dim) * 0.8

    # Conflict dynamics: audio fades, text rises
    audio_weight = max(0.1, 0.85 - t * 0.18)
    text_weight = min(0.85, 0.2 + t * 0.18)

    # At peak conflict step, both are near equal
    if t == conflict_peak_step:
        audio_weight = 0.50
        text_weight = 0.45

    encoder = audio_p * audio_weight + rng.standard_normal(hidden_dim) * 0.1

    # At high text_weight, decoder follows text_b (different direction from encoder)
    # This produces low cosine-sim (gc) when text prior dominates
    decoder = (audio_p * audio_weight * (1.0 - text_weight) +
               text_b * text_weight +
               rng.standard_normal(hidden_dim) * 0.05)
    connector = (encoder * 0.6 + rng.standard_normal(hidden_dim) * 0.1)

    # SAE features: audio-tracking (0-4), text-biased (10-14) are conflict-relevant
    sae_features = np.zeros(N_SAE_FEATURES)
    sae_features[:5] = rng.standard_normal(5) * audio_weight * 2.0   # audio side
    sae_features[5:10] = rng.standard_normal(5) * 0.3                # weak audio
    sae_features[10:15] = rng.standard_normal(5) * text_weight * 1.8 # text side
    sae_features[15:20] = rng.standard_normal(5) * 0.3               # weak text
    sae_features[20:] = rng.standard_normal(N_SAE_FEATURES - 20) * 0.2

    return {
        "encoder": encoder,
        "connector": connector,
        "decoder": decoder,
        "sae_features": sae_features,
    }


# ---------------------------------------------------------------------------
# ENV-3 motive diagnostic
# ---------------------------------------------------------------------------

@dataclass
class ENV3Diagnostic:
    """Full ENV-3 phoneme-conflict diagnosis for one stimulus."""
    stimulus_id: int
    gc_trajectory: list[float]       # gc at each step
    env_class: int                   # 1, 2, or 3
    std_gc: float                    # oscillation strength
    crosses_boundary: bool
    t_conflict: Optional[int]        # step with gc closest to τ boundary midpoint
    audio_features_at_conflict: list[int]   # features supporting audio at t_conflict
    text_features_at_conflict: list[int]    # features supporting prior at t_conflict
    conflict_ratio: float            # |text_features| / (|audio_features| + |text_features|)
    verdict: str                     # "audio_wins" | "prior_wins" | "unresolved"


def run_env3_diagnostic(
    stimulus_id: int,
    seed: int = SEED_BASE,
    sigma_thresh: float = SIGMA_THRESH,
) -> ENV3Diagnostic:
    """Run ENV-3 diagnostic on a phoneme-conflict stimulus."""
    # Generate gc trajectory using conflict activations
    gc_traj = np.zeros(T_STEPS)
    for t in range(T_STEPS):
        acts = mock_env3_activations(stimulus_id, t, seed=seed)
        gc_traj[t] = compute_gc_at_t(acts)

    env_class = classify_env(gc_traj, sigma_thresh=sigma_thresh)
    std_gc = float(np.std(gc_traj))
    crosses_boundary = bool(
        np.any(gc_traj >= TAU_HIGH) and np.any(gc_traj <= TAU_LOW)
    )

    # Find conflict onset: step with gc closest to midpoint of τ band
    tau_mid = (TAU_HIGH + TAU_LOW) / 2.0
    t_conflict = int(np.argmin(np.abs(gc_traj - tau_mid)))

    # Feature analysis at conflict step
    acts = mock_env3_activations(stimulus_id, t_conflict, seed=seed)
    feats = acts["sae_features"]

    # Features supporting audio: high positive activation AND audio-tracking type
    # Features supporting prior: high positive activation AND text-biased type
    audio_feat_threshold = 0.6
    text_feat_threshold = 0.5

    audio_feats = [i for i in range(5) if feats[i] > audio_feat_threshold]
    text_feats = [i for i in range(10, 15) if feats[i] > text_feat_threshold]

    n_audio = len(audio_feats)
    n_text = len(text_feats)
    conflict_ratio = n_text / (n_audio + n_text + 1e-8)  # avoid div-by-zero

    # Verdict: what resolves the conflict?
    final_gc = float(gc_traj[-1])
    if final_gc >= TAU_HIGH:
        verdict = "audio_wins"
    elif final_gc <= TAU_LOW:
        verdict = "prior_wins"
    else:
        verdict = "unresolved"

    return ENV3Diagnostic(
        stimulus_id=stimulus_id,
        gc_trajectory=[round(float(v), 4) for v in gc_traj],
        env_class=env_class,
        std_gc=round(std_gc, 4),
        crosses_boundary=crosses_boundary,
        t_conflict=t_conflict,
        audio_features_at_conflict=audio_feats,
        text_features_at_conflict=text_feats,
        conflict_ratio=round(conflict_ratio, 3),
        verdict=verdict,
    )


# ---------------------------------------------------------------------------
# Batch analysis across all ENV classes
# ---------------------------------------------------------------------------

@dataclass
class ENVBatchResult:
    """Aggregate ENV classification over N stimuli."""
    n_stimuli: int
    env_counts: dict[str, int]       # "ENV-1" → count
    env_rates: dict[str, float]      # "ENV-1" → rate
    env3_conflict_ratios: list[float]
    env3_verdicts: dict[str, int]    # "audio_wins" / "prior_wins" / "unresolved"
    mean_gc_by_env: dict[str, list[float]]   # ENV label → mean gc trajectory
    env3_diagnostics: list[ENV3Diagnostic]


def run_batch_analysis(
    n_stimuli: int = N_STIMULI,
    seed: int = SEED_BASE,
    sigma_thresh: float = SIGMA_THRESH,
) -> ENVBatchResult:
    """
    Classify N stimuli from all scenarios into ENV-1/2/3.

    Mix:
      - 1/3 from "clean" scenario (expect ENV-1)
      - 1/3 from "gradual_drift" scenario (expect ENV-2)
      - 1/3 from ENV-3 conflict scenario (expect ENV-3)
    """
    per_type = n_stimuli // 3
    env_counts = {f"ENV-{i}": 0 for i in range(1, 4)}
    mean_gc_accum: dict[str, list[list[float]]] = {f"ENV-{i}": [] for i in range(1, 4)}
    env3_conflicts: list[float] = []
    env3_verdicts: dict[str, int] = {"audio_wins": 0, "prior_wins": 0, "unresolved": 0}
    env3_diags: list[ENV3Diagnostic] = []

    # Classify clean stimuli (expected: ENV-1)
    for i in range(per_type):
        profile = build_temporal_profile("clean", i, seed=seed)
        env_class = classify_env(profile.gc_trajectory, sigma_thresh=sigma_thresh)
        label = f"ENV-{env_class}"
        env_counts[label] += 1
        mean_gc_accum[label].append(list(profile.gc_trajectory))

    # Classify gradual_drift stimuli (expected: ENV-2)
    for i in range(per_type):
        profile = build_temporal_profile("gradual_drift", i, seed=seed)
        env_class = classify_env(profile.gc_trajectory, sigma_thresh=sigma_thresh)
        label = f"ENV-{env_class}"
        env_counts[label] += 1
        mean_gc_accum[label].append(list(profile.gc_trajectory))

    # Classify ENV-3 conflict stimuli (expected: ENV-3)
    for i in range(per_type):
        diag = run_env3_diagnostic(i, seed=seed, sigma_thresh=sigma_thresh)
        env_class = diag.env_class
        label = f"ENV-{env_class}"
        env_counts[label] += 1

        # Reconstruct trajectory for mean
        mean_gc_accum[label].append(diag.gc_trajectory)

        if env_class == 3:
            env3_conflicts.append(diag.conflict_ratio)
            env3_verdicts[diag.verdict] += 1
            env3_diags.append(diag)

    n_total = 3 * per_type
    env_rates = {k: round(v / n_total, 3) for k, v in env_counts.items()}

    # Mean gc trajectory per ENV class
    mean_gc_by_env: dict[str, list[float]] = {}
    for label, trajs in mean_gc_accum.items():
        if trajs:
            mat = np.array(trajs)
            mean_gc_by_env[label] = [round(float(v), 4) for v in mat.mean(axis=0)]
        else:
            mean_gc_by_env[label] = [0.0] * T_STEPS

    return ENVBatchResult(
        n_stimuli=n_total,
        env_counts=env_counts,
        env_rates=env_rates,
        env3_conflict_ratios=env3_conflicts,
        env3_verdicts=env3_verdicts,
        mean_gc_by_env=mean_gc_by_env,
        env3_diagnostics=env3_diags,
    )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_env3_report(result: ENVBatchResult) -> None:
    sep = "=" * 82

    print(f"\n{sep}")
    print("  gc-Incrimination × ENV-3  — Phoneme-Conflict Motive Diagnostic  (Q101)")
    print("  Track T3: Listen vs Guess  |  Motive taxonomy from Q100 (ENV-1/2/3)")
    print(sep)
    print(f"  Thresholds: τ_high={TAU_HIGH}, τ_low={TAU_LOW}, σ_thresh={SIGMA_THRESH}")
    print(f"  N stimuli = {result.n_stimuli} (1/3 clean, 1/3 drift, 1/3 conflict)")
    print()

    # ENV classification summary
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │ ENV Classification Summary                              │")
    print("  ├───────────┬───────────────┬────────────┬───────────────┤")
    print("  │ Class     │ Label         │ Count      │ Rate          │")
    print("  ├───────────┼───────────────┼────────────┼───────────────┤")
    for env_id, label in ENV_LABELS.items():
        key = f"ENV-{env_id}"
        cnt = result.env_counts[key]
        rate = result.env_rates[key]
        bar = "█" * int(rate * 20)
        print(f"  │ ENV-{env_id}     │ {label:<13} │ {cnt:<10} │ {rate:>5.1%}  {bar:<10} │")
    print("  └───────────┴───────────────┴────────────┴───────────────┘")

    # Mean gc trajectory per class
    print(f"\n  Mean gc(k_peak, t) trajectory by ENV class:")
    steps_hdr = "  ".join([f"t={t}" for t in range(T_STEPS)])
    print(f"  {'Class':<10}: {steps_hdr}")
    print(f"  {'─' * 60}")
    for env_id, label in ENV_LABELS.items():
        key = f"ENV-{env_id}"
        trajs = result.mean_gc_by_env.get(key, [])
        gc_str = "  ".join([f"{v:.3f}" for v in trajs]) if trajs else "N/A"
        print(f"  {key:<10}: {gc_str}  ← {label}")

    # ENV-3 specific analysis
    print(f"\n  {'─' * 78}")
    print(f"  ENV-3 Conflict Analysis (phoneme conflict stimuli only):")
    print(f"  {'─' * 78}")

    n_env3 = len(result.env3_diagnostics)
    if n_env3 == 0:
        print("  No ENV-3 stimuli detected (try increasing n_stimuli or reducing σ_thresh)")
    else:
        # Conflict ratio distribution
        ratios = result.env3_conflict_ratios
        print(f"  Detected {n_env3} ENV-3 stimuli from conflict scenario")
        print(f"  Conflict ratio (text features / total active features):")
        print(f"    mean={np.mean(ratios):.3f}  std={np.std(ratios):.3f}  "
              f"min={min(ratios):.3f}  max={max(ratios):.3f}")
        print(f"\n  Verdict distribution (who wins the phoneme conflict):")
        for verdict, cnt in result.env3_verdicts.items():
            pct = cnt / n_env3 if n_env3 else 0
            bar = "█" * int(pct * 20)
            print(f"    {verdict:<12}: {cnt:>3} ({pct:.0%})  {bar}")

        # Example ENV-3 stimulus (most conflicted)
        if result.env3_diagnostics:
            ex = max(result.env3_diagnostics, key=lambda d: d.std_gc)
            print(f"\n  Example ENV-3 stimulus (stimulus_id={ex.stimulus_id}, "
                  f"std={ex.std_gc:.3f}):")
            gc_str = " → ".join([f"{v:.3f}" for v in ex.gc_trajectory])
            print(f"    gc trajectory: {gc_str}")
            print(f"    t_conflict = {ex.t_conflict}  |  verdict = {ex.verdict}")
            print(f"    Audio features at t_conflict: {ex.audio_features_at_conflict}")
            print(f"    Text features at t_conflict:  {ex.text_features_at_conflict}")
            print(f"    Conflict ratio: {ex.conflict_ratio:.3f}")

    # Interpretation for Paper A
    print(f"\n  {'─' * 78}")
    print(f"  Mechanistic Interpretation (Paper A §5.4 ENV-3 contribution):")
    print(f"  {'─' * 78}")
    print(f"  • ENV-1 (LISTEN): AND-gate audio features dominate → gc stable above τ_high")
    print(f"    → Model can be trusted to follow audio; errors = noise/acoustic, not motive")
    print(f"  • ENV-2 (GUESS): OR-gate text features dominate → gc stable below τ_low")
    print(f"    → Model ignores audio regardless; prior alone determines output")
    print(f"  • ENV-3 (CONFLICT): Mixed AND/OR gate activation → gc oscillates near τ")
    print(f"    → Audio and prior actively compete; incrimination reveals which features tip it")
    print(f"    → t_conflict = the mechanistic decision point for phoneme selection")
    print(f"    → Feature blame at t_conflict identifies the 'swing features'")
    print(f"\n  Implications:")
    print(f"    1. gc(k,t) is not just an error detector — it is a motive signal")
    print(f"    2. ENV-3 stimuli are the most informative for interpretability")
    print(f"    3. Incrimination at t_conflict is the right intervention target")
    print(f"    4. Safety-trained models may show ENV-3 more often (competing training signals)")
    print(f"\n  Next steps → Q090 (Audio Incrimination Graph) or Q095 (OBLITERATUS x gc(k))")
    print(sep)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="gc-Incrimination × ENV-3 Phoneme-Conflict Motive Diagnostic (Q101)"
    )
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--stimuli", type=int, default=N_STIMULI,
                        help=f"Stimuli per scenario type (total 3x, default {N_STIMULI})")
    parser.add_argument("--sigma", type=float, default=SIGMA_THRESH,
                        help=f"gc std threshold for ENV-3 detection (default {SIGMA_THRESH})")
    parser.add_argument("--seed", type=int, default=SEED_BASE)
    args = parser.parse_args()

    result = run_batch_analysis(n_stimuli=args.stimuli, seed=args.seed, sigma_thresh=args.sigma)

    if args.json:
        out = {
            "n_stimuli": result.n_stimuli,
            "env_counts": result.env_counts,
            "env_rates": result.env_rates,
            "env3_conflict_ratios": result.env3_conflict_ratios,
            "env3_verdicts": result.env3_verdicts,
            "mean_gc_by_env": result.mean_gc_by_env,
            "env3_diagnostics": [
                {
                    "stimulus_id": d.stimulus_id,
                    "gc_trajectory": d.gc_trajectory,
                    "env_class": d.env_class,
                    "std_gc": d.std_gc,
                    "crosses_boundary": d.crosses_boundary,
                    "t_conflict": d.t_conflict,
                    "audio_features_at_conflict": d.audio_features_at_conflict,
                    "text_features_at_conflict": d.text_features_at_conflict,
                    "conflict_ratio": d.conflict_ratio,
                    "verdict": d.verdict,
                }
                for d in result.env3_diagnostics
            ],
        }
        print(json.dumps(out, indent=2))
    else:
        print_env3_report(result)

    # Sanity checks
    total = sum(result.env_counts.values())
    assert total == result.n_stimuli, f"Counts don't add up: {total} != {result.n_stimuli}"
    for label, trajs in result.mean_gc_by_env.items():
        for v in trajs:
            assert 0.0 <= v <= 1.0, f"gc out of [0,1] for {label}: {v}"

    return 0


if __name__ == "__main__":
    sys.exit(main())
