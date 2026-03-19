#!/usr/bin/env python3
"""
gc-Incrimination Mock — Q088 + Q069
Track T3: Listen vs Guess (Paper A §5.4 Extension)

Tasks:
  Q069: Temporal Directed Isolate — add time axis to directed_isolate_mock.py
  Q088: gc-Incrimination — find t* where gc(k) drops below threshold; label as
        error-onset step; mock error scenario for feature-level blame attribution.

Core idea:
  In a multi-step decoding process, the gc(k) signal should remain high as long
  as the model is "listening" to the audio. When it drops below a threshold τ,
  we declare t* = error-onset step: the decoder stopped using audio evidence
  and started relying on priors/text, causing (or predicting) the transcription error.

  Formally:
    t* = min{ t : gc(k_peak, t) < τ }

  Feature-level incrimination (gc-incrimination):
    For each SAE feature f at layer k*, compute:
      blame(f, t*) = gc(k*, t*) measured with f ablated - gc(k*, t*) full
    A feature is "incriminated" if blame(f, t*) < -δ  (ablation reduces gc → feature was essential)
    An "exonerating" feature has blame(f, t*) > +δ (ablation increases gc → feature was suppressing)

Temporal extension (Q069):
  We simulate 5 decoding steps per stimulus. At each step t:
    - Compute Isolate_in(t): encoder→connector causal flow
    - Compute Isolate_out(t): connector→decoder causal flow
    - Compute gc(k_peak, t): total audio causal grounding at peak gc layer
  This produces a trajectory [gc(k_peak, 0), ..., gc(k_peak, T-1)] per stimulus.

Error scenario:
  "error_token" condition: at step t=3, audio representation is corrupted
  (noise injection). gc(k) drops. t* is detected. Feature-level blame computed.

CPU-feasible: all mock tensors, no model download.

Usage:
    python3 gc_incrimination_mock.py                  # print full report
    python3 gc_incrimination_mock.py --json           # JSON output
    python3 gc_incrimination_mock.py --scenario all   # run all scenarios
    python3 gc_incrimination_mock.py --tau 0.4        # custom threshold

Dependencies: numpy only
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from typing import Optional

import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

N_STIMULI = 20
T_STEPS = 5           # decoding timesteps (Q069: time axis)
N_LAYERS = 6          # simplified Whisper-like encoder depth
PEAK_GC_LAYER = 2     # layer with max gc(k) in clean condition
N_SAE_FEATURES = 32   # mock SAE feature dimension
SEED_BASE = 42
GC_THRESHOLD_TAU = 0.45  # t* declared when gc < tau
BLAME_DELTA = 0.03    # min |blame| to flag a feature

SCENARIOS = ["clean", "error_token", "gradual_drift", "sudden_collapse"]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TemporalGCProfile:
    """gc(k, t) trajectory for a single stimulus."""
    stimulus_id: int
    scenario: str
    # shape: (T_STEPS,) — gc at PEAK_GC_LAYER over decoding steps
    gc_trajectory: np.ndarray
    # shape: (T_STEPS,) — Isolate_in trajectory
    isolate_in_trajectory: np.ndarray
    # shape: (T_STEPS,) — Isolate_out trajectory
    isolate_out_trajectory: np.ndarray
    # Error onset
    t_star: Optional[int]           # first t where gc < tau; None if never drops
    collapse_detected: bool


@dataclass
class FeatureIncrimination:
    """Feature-level blame for a single stimulus at t*."""
    stimulus_id: int
    t_star: int
    # shape: (N_SAE_FEATURES,) — blame score per feature
    blame_scores: np.ndarray
    incriminated: list[int]         # feature indices with blame < -BLAME_DELTA
    exonerating: list[int]          # feature indices with blame > +BLAME_DELTA
    top_incriminated: list[int]     # top 3 by |blame|
    top_blame_values: list[float]


@dataclass
class ScenarioResult:
    """Aggregated result for one error scenario."""
    scenario: str
    n_stimuli: int
    # Temporal stats
    mean_gc_per_step: list[float]       # shape (T_STEPS,)
    mean_isolate_in_per_step: list[float]
    mean_isolate_out_per_step: list[float]
    # Error detection
    n_collapse_detected: int
    mean_t_star: Optional[float]
    t_star_distribution: dict[str, int]  # step → count
    # Feature-level incrimination
    incriminated_features: list[int]    # features incriminated in ≥50% of collapsing stimuli
    top_blame_features: list[dict]      # top 5 features by mean |blame|


# ---------------------------------------------------------------------------
# Mock activation generator (temporal)
# ---------------------------------------------------------------------------

def mock_temporal_activations(
    scenario: str,
    stimulus_id: int,
    t: int,
    n_features: int = N_SAE_FEATURES,
    hidden_dim: int = 64,
    seed: int = SEED_BASE,
) -> dict[str, np.ndarray]:
    """
    Generate mock activations at decoder timestep t for one stimulus.

    Scenarios:
      clean:           audio signal stable across all t; gc stays high
      error_token:     at t=3, audio noise injected → gc drops sharply
      gradual_drift:   gc decays linearly from t=1 onward
      sudden_collapse: gc drops to near-zero at t=2 (catastrophic error)

    Returns dict with keys: "encoder", "connector", "decoder", "sae_features"
      encoder, connector, decoder: shape (hidden_dim,) — single-stimulus vectors
      sae_features: shape (n_features,) — SAE feature activations at PEAK_GC_LAYER

    Real implementation:
      Use activation hooks on Whisper encoder layers.
      Run gc_eval.py::run_with_hook() at each decoding step.
    """
    rng = np.random.default_rng(seed + stimulus_id * 100 + t)

    # Base audio signal (strong, high-gc)
    audio_base = rng.standard_normal(hidden_dim) * 0.8

    # Audio retention factor at this timestep (scenario-dependent)
    if scenario == "clean":
        retention = 0.9   # stable throughout
    elif scenario == "error_token":
        retention = 0.9 if t < 3 else 0.15   # collapse at t=3
    elif scenario == "gradual_drift":
        retention = max(0.05, 0.9 - t * 0.18)  # linear decay
    elif scenario == "sudden_collapse":
        retention = 0.9 if t < 2 else 0.05   # collapse at t=2
    else:
        retention = 0.7

    # Encoder: reflects audio quality
    encoder = audio_base * retention + rng.standard_normal(hidden_dim) * (1 - retention) * 0.5

    # Connector: bridge (partially follows encoder)
    connector_blend = retention * 0.85
    connector = encoder * connector_blend + rng.standard_normal(hidden_dim) * 0.15

    # Decoder: downstream usage
    decoder_blend = retention * 0.75
    decoder = connector * decoder_blend + rng.standard_normal(hidden_dim) * 0.2

    # SAE features at peak gc layer: some features track audio, others don't
    # "audio-tracking" features (indices 0-9): high activation when retention is high
    # "text-biased" features (indices 10-19): inversely correlated with retention
    # "neutral" features (indices 20-31): stable
    sae_features = np.zeros(n_features)
    audio_tracking = rng.standard_normal(10) * retention * 2.0
    text_biased = rng.standard_normal(10) * (1 - retention) * 1.5
    neutral = rng.standard_normal(n_features - 20) * 0.5
    sae_features[:10] = audio_tracking
    sae_features[10:20] = text_biased
    sae_features[20:] = neutral

    return {
        "encoder": encoder,
        "connector": connector,
        "decoder": decoder,
        "sae_features": sae_features,
    }


# ---------------------------------------------------------------------------
# gc(k, t) computation
# ---------------------------------------------------------------------------

def _cos_sim(a: np.ndarray, b: np.ndarray, eps: float = 1e-8) -> float:
    """Cosine similarity between two 1D vectors."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + eps))


def compute_gc_at_t(acts: dict[str, np.ndarray]) -> float:
    """
    Compute gc(k_peak, t) at a single timestep.

    gc(k) operationalized as cosine similarity between encoder and decoder activations.
    High gc = strong causal flow of audio info from encoder to decoder output.
    Normalized to [0, 1].
    """
    raw = _cos_sim(acts["encoder"], acts["decoder"])
    return float(np.clip((raw + 1.0) / 2.0, 0.0, 1.0))


def compute_isolate_in_at_t(acts: dict[str, np.ndarray]) -> float:
    raw = _cos_sim(acts["encoder"], acts["connector"])
    return float(np.clip((raw + 1.0) / 2.0, 0.0, 1.0))


def compute_isolate_out_at_t(acts: dict[str, np.ndarray]) -> float:
    raw = _cos_sim(acts["connector"], acts["decoder"])
    return float(np.clip((raw + 1.0) / 2.0, 0.0, 1.0))


# ---------------------------------------------------------------------------
# Temporal profile
# ---------------------------------------------------------------------------

def build_temporal_profile(
    scenario: str,
    stimulus_id: int,
    tau: float = GC_THRESHOLD_TAU,
    seed: int = SEED_BASE,
) -> TemporalGCProfile:
    """Compute gc(k, t), Isolate_in(t), Isolate_out(t) for all timesteps."""
    gc_traj = np.zeros(T_STEPS)
    iso_in_traj = np.zeros(T_STEPS)
    iso_out_traj = np.zeros(T_STEPS)

    for t in range(T_STEPS):
        acts = mock_temporal_activations(scenario, stimulus_id, t, seed=seed)
        gc_traj[t] = compute_gc_at_t(acts)
        iso_in_traj[t] = compute_isolate_in_at_t(acts)
        iso_out_traj[t] = compute_isolate_out_at_t(acts)

    # Detect t* = first step where gc < tau
    below = np.where(gc_traj < tau)[0]
    t_star = int(below[0]) if len(below) > 0 else None
    collapse_detected = t_star is not None

    return TemporalGCProfile(
        stimulus_id=stimulus_id,
        scenario=scenario,
        gc_trajectory=gc_traj,
        isolate_in_trajectory=iso_in_traj,
        isolate_out_trajectory=iso_out_traj,
        t_star=t_star,
        collapse_detected=collapse_detected,
    )


# ---------------------------------------------------------------------------
# Feature incrimination
# ---------------------------------------------------------------------------

def compute_feature_incrimination(
    scenario: str,
    stimulus_id: int,
    t_star: int,
    seed: int = SEED_BASE,
    blame_delta: float = BLAME_DELTA,
) -> FeatureIncrimination:
    """
    Compute feature-level blame at t*.

    Protocol (mock):
      1. Get full gc(k*, t*) baseline
      2. For each SAE feature f: ablate f (zero out), recompute gc
      3. blame(f, t*) = gc_ablated - gc_baseline
         < -δ → incriminated (feature was supporting gc; removing it hurts)
         > +δ → exonerating (feature was suppressing gc; removing it helps)

    Real implementation:
      Use activation patching: zero out feature f in SAE output at layer k*,
      measure how gc(k*, t*) changes. Features with large negative blame are
      causally responsible for the error-onset.
    """
    acts_full = mock_temporal_activations(scenario, stimulus_id, t_star, seed=seed)
    gc_baseline = compute_gc_at_t(acts_full)

    blame_scores = np.zeros(N_SAE_FEATURES)

    for f_idx in range(N_SAE_FEATURES):
        # Mock ablation: zero out feature f in SAE
        # In real implementation: patch acts["encoder"] to remove SAE feature f's contribution
        acts_ablated = mock_temporal_activations(scenario, stimulus_id, t_star, seed=seed)

        # Simulate ablation effect: features 0-9 (audio-tracking) hurt gc when ablated
        # features 10-19 (text-biased) help gc when ablated
        sae_f_val = acts_full["sae_features"][f_idx]
        if f_idx < 10:  # audio-tracking feature
            ablation_effect = -abs(sae_f_val) * 0.12  # blame: ablating hurts gc
        elif f_idx < 20:  # text-biased feature
            ablation_effect = abs(sae_f_val) * 0.08   # blame: ablating helps gc
        else:             # neutral
            ablation_effect = sae_f_val * 0.01  # tiny effect

        # Add small noise to simulate sampling variance
        rng = np.random.default_rng(seed + f_idx + stimulus_id)
        noise = rng.standard_normal() * 0.005
        blame_scores[f_idx] = ablation_effect + noise

    incriminated = [i for i in range(N_SAE_FEATURES) if blame_scores[i] < -blame_delta]
    exonerating = [i for i in range(N_SAE_FEATURES) if blame_scores[i] > blame_delta]

    # Top 3 incriminated by |blame|
    sorted_by_blame = sorted(incriminated, key=lambda i: blame_scores[i])[:3]
    top_blame_values = [round(float(blame_scores[i]), 4) for i in sorted_by_blame]

    return FeatureIncrimination(
        stimulus_id=stimulus_id,
        t_star=t_star,
        blame_scores=blame_scores,
        incriminated=incriminated,
        exonerating=exonerating,
        top_incriminated=sorted_by_blame,
        top_blame_values=top_blame_values,
    )


# ---------------------------------------------------------------------------
# Scenario runner
# ---------------------------------------------------------------------------

def run_scenario(
    scenario: str,
    n_stimuli: int = N_STIMULI,
    tau: float = GC_THRESHOLD_TAU,
    seed: int = SEED_BASE,
) -> ScenarioResult:
    """Run full temporal gc + incrimination analysis for a scenario."""
    profiles: list[TemporalGCProfile] = []
    incriminations: list[FeatureIncrimination] = []

    gc_matrix = np.zeros((n_stimuli, T_STEPS))
    iso_in_matrix = np.zeros((n_stimuli, T_STEPS))
    iso_out_matrix = np.zeros((n_stimuli, T_STEPS))

    for i in range(n_stimuli):
        prof = build_temporal_profile(scenario, i, tau=tau, seed=seed)
        profiles.append(prof)
        gc_matrix[i] = prof.gc_trajectory
        iso_in_matrix[i] = prof.isolate_in_trajectory
        iso_out_matrix[i] = prof.isolate_out_trajectory

        if prof.collapse_detected and prof.t_star is not None:
            incr = compute_feature_incrimination(scenario, i, prof.t_star, seed=seed)
            incriminations.append(incr)

    # Aggregate temporal means
    mean_gc = [round(float(gc_matrix[:, t].mean()), 4) for t in range(T_STEPS)]
    mean_iso_in = [round(float(iso_in_matrix[:, t].mean()), 4) for t in range(T_STEPS)]
    mean_iso_out = [round(float(iso_out_matrix[:, t].mean()), 4) for t in range(T_STEPS)]

    # Collapse stats
    n_collapse = sum(1 for p in profiles if p.collapse_detected)
    t_stars = [p.t_star for p in profiles if p.t_star is not None]
    mean_t_star = round(float(np.mean(t_stars)), 2) if t_stars else None
    t_star_dist: dict[str, int] = {}
    for t in t_stars:
        k = f"t={t}"
        t_star_dist[k] = t_star_dist.get(k, 0) + 1

    # Feature-level: which features are incriminated in ≥50% of collapsing stimuli?
    if incriminations:
        from collections import Counter
        incr_counter: Counter[int] = Counter()
        blame_accum = np.zeros(N_SAE_FEATURES)
        for incr in incriminations:
            for f in incr.incriminated:
                incr_counter[f] += 1
            blame_accum += incr.blame_scores
        thresh = len(incriminations) * 0.5
        consensus_incr = [f for f, cnt in incr_counter.items() if cnt >= thresh]
        mean_blame = blame_accum / len(incriminations)
        sorted_feats = sorted(range(N_SAE_FEATURES), key=lambda f: mean_blame[f])[:5]
        top_blame_feats = [
            {"feature_id": f, "mean_blame": round(float(mean_blame[f]), 4),
             "type": "audio-tracking" if f < 10 else ("text-biased" if f < 20 else "neutral")}
            for f in sorted_feats
        ]
    else:
        consensus_incr = []
        top_blame_feats = []

    return ScenarioResult(
        scenario=scenario,
        n_stimuli=n_stimuli,
        mean_gc_per_step=mean_gc,
        mean_isolate_in_per_step=mean_iso_in,
        mean_isolate_out_per_step=mean_iso_out,
        n_collapse_detected=n_collapse,
        mean_t_star=mean_t_star,
        t_star_distribution=t_star_dist,
        incriminated_features=sorted(consensus_incr),
        top_blame_features=top_blame_feats,
    )


# ---------------------------------------------------------------------------
# Report printer
# ---------------------------------------------------------------------------

def print_report(results: dict[str, ScenarioResult], tau: float) -> None:
    sep = "=" * 82

    print(f"\n{sep}")
    print("  gc-Incrimination Mock — Q088 + Q069 (Temporal Directed Isolate)")
    print("  Track T3: Listen vs Guess | t* = error-onset step detection")
    print(sep)
    print(f"  τ (gc threshold for t*) = {tau}  |  T = {T_STEPS} steps  |  "
          f"Layers = {N_LAYERS}  |  k_peak = {PEAK_GC_LAYER}")
    print(f"  N stimuli = {N_STIMULI}  |  SAE features = {N_SAE_FEATURES}")
    print(f"  NOTE: Mock mode — replace mock_temporal_activations() with real hooks")

    steps_header = "  ".join([f"t={t}" for t in range(T_STEPS)])
    for scenario, res in results.items():
        print(f"\n  {'─' * 78}")
        print(f"  Scenario: [{scenario.upper()}]")
        print(f"  {'─' * 78}")

        # Temporal gc trajectory
        gc_str = "  ".join([f"{v:.3f}" for v in res.mean_gc_per_step])
        in_str = "  ".join([f"{v:.3f}" for v in res.mean_isolate_in_per_step])
        out_str = "  ".join([f"{v:.3f}" for v in res.mean_isolate_out_per_step])

        print(f"  {'Step':>12}:  {steps_header}")
        print(f"  {'gc(k_peak,t)':>12}:  {gc_str}")
        print(f"  {'Isolate-IN':>12}:  {in_str}")
        print(f"  {'Isolate-OUT':>12}:  {out_str}")

        # Collapse detection
        collapse_rate = res.n_collapse_detected / res.n_stimuli
        print(f"\n  Collapse detection (gc < τ={tau}):")
        print(f"    {res.n_collapse_detected}/{res.n_stimuli} stimuli collapsed "
              f"({collapse_rate:.0%})")
        if res.mean_t_star is not None:
            print(f"    Mean t* = {res.mean_t_star:.1f}  |  "
                  f"Distribution: {res.t_star_distribution}")
        else:
            print(f"    No collapses detected")

        # Feature incrimination
        if res.top_blame_features:
            print(f"\n  Feature Incrimination (consensus ≥50% collapsing stimuli):")
            print(f"    Incriminated features: {res.incriminated_features}")
            print(f"    Top 5 features by mean blame:")
            for fb in res.top_blame_features:
                bar = "█" * int(abs(fb["mean_blame"]) * 100)
                print(f"      f{fb['feature_id']:02d} [{fb['type']:>14}]  "
                      f"blame={fb['mean_blame']:+.4f}  {bar}")
        else:
            print(f"\n  Feature Incrimination: no collapses to analyze")

    print(f"\n{sep}")
    print("  Summary: t* detection + feature blame")
    print(f"  {'─' * 78}")
    print(f"  {'Scenario':<22} {'CollapseRate':>13} {'Mean-t*':>9} {'TopIncrim':>12}")
    print(f"  {'─' * 60}")
    for scenario, res in results.items():
        rate = f"{res.n_collapse_detected}/{res.n_stimuli}"
        t_star_str = f"{res.mean_t_star:.1f}" if res.mean_t_star is not None else "N/A"
        top_f = str(res.incriminated_features[:3]) if res.incriminated_features else "none"
        print(f"  {scenario:<22} {rate:>13} {t_star_str:>9} {top_f:>12}")

    print(f"\n  Interpretation:")
    print(f"    • clean: gc stays high → t* never triggered (model always listening)")
    print(f"    • error_token: t*=3 → error-onset at step 3; features 0-9 incriminated")
    print(f"    • gradual_drift: t* earlier → model drifts from audio, blame spreads")
    print(f"    • sudden_collapse: t*=2 → catastrophic failure; most features implicated")
    print(f"\n  Next steps (Q069/Q088 → real data):")
    print(f"    1. Replace mock_temporal_activations() with WhisperHookedEncoder hooks")
    print(f"    2. Use gc_eval.py::run_with_hook() per decoding step")
    print(f"    3. Apply SAE decomposition at k_peak = {PEAK_GC_LAYER}")
    print(f"    4. Compare t* with human error annotations in LibriSpeech error set")
    print(sep)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="gc-Incrimination Mock (Q088+Q069) — Temporal gc(k,t) + error-onset detection"
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--scenario", default="all",
                        choices=["all"] + SCENARIOS, help="Which scenario to run")
    parser.add_argument("--tau", type=float, default=GC_THRESHOLD_TAU,
                        help=f"gc threshold for t* detection (default {GC_THRESHOLD_TAU})")
    parser.add_argument("--stimuli", type=int, default=N_STIMULI, help="Stimuli per scenario")
    parser.add_argument("--seed", type=int, default=SEED_BASE, help="Random seed")
    args = parser.parse_args()

    scenarios_to_run = SCENARIOS if args.scenario == "all" else [args.scenario]
    results: dict[str, ScenarioResult] = {}

    for sc in scenarios_to_run:
        results[sc] = run_scenario(sc, n_stimuli=args.stimuli, tau=args.tau, seed=args.seed)

    if args.json:
        out = {}
        for sc, res in results.items():
            out[sc] = {
                "scenario": res.scenario,
                "mean_gc_per_step": res.mean_gc_per_step,
                "mean_isolate_in_per_step": res.mean_isolate_in_per_step,
                "mean_isolate_out_per_step": res.mean_isolate_out_per_step,
                "n_collapse_detected": res.n_collapse_detected,
                "n_stimuli": res.n_stimuli,
                "collapse_rate": round(res.n_collapse_detected / res.n_stimuli, 3),
                "mean_t_star": res.mean_t_star,
                "t_star_distribution": res.t_star_distribution,
                "incriminated_features": res.incriminated_features,
                "top_blame_features": res.top_blame_features,
            }
        print(json.dumps(out, indent=2))
    else:
        print_report(results, tau=args.tau)

    # Sanity checks
    for sc, res in results.items():
        assert len(res.mean_gc_per_step) == T_STEPS, f"gc trajectory length mismatch for {sc}"
        for v in res.mean_gc_per_step + res.mean_isolate_in_per_step + res.mean_isolate_out_per_step:
            assert 0.0 <= v <= 1.0, f"Score out of [0,1] in scenario {sc}: {v}"
        if res.mean_t_star is not None:
            assert 0 <= res.mean_t_star < T_STEPS, f"t* out of range for {sc}"

    return 0


if __name__ == "__main__":
    sys.exit(main())
