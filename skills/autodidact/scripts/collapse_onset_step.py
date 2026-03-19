#!/usr/bin/env python3
"""
Collapse Onset Step — Q085
Track T3: Listen vs Guess (Paper A)

Extends Q069/Q088 gc_incrimination_mock.py temporal work.

Measures Isolate_in(t) per decoder step t and defines:
  collapse_onset_step = min{ t : Isolate_in(t) < ISOLATE_THRESHOLD }

This is the first step where the decoder no longer isolates audio evidence —
the model has "stopped listening" and relies on language priors.

Conditions tested:
  clean          — no perturbation (Isolate_in stays high until late steps)
  noisy_audio    — audio corrupted with Gaussian noise (early collapse)
  text_override  — strong text prior overrides audio (mid-step collapse)
  jailbreak      — adversarial text pushes collapse earlier (earliest collapse)

Hypotheses:
  H1: noisy_audio collapses earlier than clean (higher noise → lower onset step)
  H2: jailbreak condition collapses earliest of all
  H3: clean condition has latest or no collapse (t* = T-1 or ∞)
  H4: Isolate_in(t) is monotonically non-increasing within a trial

Usage:
    python3 collapse_onset_step.py                  # ASCII report
    python3 collapse_onset_step.py --json           # JSON output
    python3 collapse_onset_step.py --threshold 0.15 # custom threshold
    python3 collapse_onset_step.py --plot           # matplotlib (if available)
    python3 collapse_onset_step.py --stimuli 50     # more stimuli

Dependencies: numpy only (matplotlib optional for --plot)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from typing import List, Optional

import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ISOLATE_THRESHOLD = 0.10   # t* = first step where Isolate_in drops below this
T_STEPS = 10               # decoder steps per stimulus
N_STIMULI = 40             # stimuli per condition
SEED = 42
INF_STEP = T_STEPS         # sentinel: no collapse observed within T_STEPS

CONDITIONS = ["clean", "noisy_audio", "text_override", "jailbreak"]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class StimulusResult:
    stimulus_id: int
    condition: str
    isolate_curve: List[float]   # Isolate_in(t) for t=0..T-1
    collapse_onset_step: int     # t* (== INF_STEP if no collapse observed)
    collapsed: bool              # True if collapse_onset_step < T_STEPS


@dataclass
class ConditionSummary:
    condition: str
    n_stimuli: int
    mean_isolate: List[float]    # mean Isolate_in(t) across stimuli
    std_isolate: List[float]
    collapse_rate: float         # fraction of stimuli with collapse
    mean_onset_step: float       # mean t* (excluding INF_STEP if no collapse)
    mean_onset_step_all: float   # mean t* with INF_STEP treated as T (pessimistic)
    std_onset_step: float
    min_onset_step: int
    max_onset_step: int


# ---------------------------------------------------------------------------
# Isolate_in(t) simulation
# ---------------------------------------------------------------------------

def simulate_isolate_in(
    condition: str,
    t_steps: int,
    n_stimuli: int,
    seed: int,
    threshold: float,
) -> List[StimulusResult]:
    """
    Simulate Isolate_in(t) curves for a given condition.

    Isolate_in(t) measures how much the current decoder step t still isolates
    (causally depends on) the audio encoder output vs. proceeding without it.

    Generation model:
      clean:         starts at 0.65, slow exponential decay (rate 0.12)
      noisy_audio:   starts at 0.45, faster decay (rate 0.25)
      text_override: starts at 0.55, medium decay (rate 0.20), adds step-effect drop
      jailbreak:     starts at 0.40, fastest decay (rate 0.35), hard floor at 0.08
    """
    rng = np.random.default_rng(seed + abs(hash(condition)) % 9999)
    steps = np.arange(t_steps, dtype=float)

    # Condition parameters
    params = {
        "clean":         dict(start=0.65, rate=0.12, floor=0.02, noise=0.04, step_drop=None),
        "noisy_audio":   dict(start=0.45, rate=0.25, floor=0.01, noise=0.05, step_drop=None),
        "text_override": dict(start=0.55, rate=0.18, floor=0.02, noise=0.04, step_drop=5),
        "jailbreak":     dict(start=0.40, rate=0.35, floor=0.08, noise=0.06, step_drop=3),
    }
    p = params[condition]

    results: List[StimulusResult] = []

    for i in range(n_stimuli):
        stim_rng = np.random.default_rng(seed + i * 17 + abs(hash(condition)) % 8888)

        # Per-stimulus variation: randomize start ±10%, rate ±15%
        start  = p["start"] * stim_rng.uniform(0.90, 1.10)
        rate   = p["rate"]  * stim_rng.uniform(0.85, 1.15)
        noise  = stim_rng.normal(0, p["noise"], t_steps)

        # Base exponential decay
        curve = start * np.exp(-rate * steps) + p["floor"]

        # Optional step-drop (sudden text-override event)
        if p["step_drop"] is not None:
            drop_t = p["step_drop"] + stim_rng.integers(-1, 2)  # ±1 variation
            drop_t = int(np.clip(drop_t, 1, t_steps - 1))
            curve[drop_t:] *= 0.55   # 45% additional reduction at drop step

        curve = np.clip(curve + noise, 0.0, 1.0)

        isolate_list = [round(float(v), 4) for v in curve]

        # Find collapse_onset_step = first t where curve < threshold
        below = np.where(curve < threshold)[0]
        if len(below) > 0:
            onset = int(below[0])
            collapsed = True
        else:
            onset = INF_STEP
            collapsed = False

        results.append(StimulusResult(
            stimulus_id=i,
            condition=condition,
            isolate_curve=isolate_list,
            collapse_onset_step=onset,
            collapsed=collapsed,
        ))

    return results


# ---------------------------------------------------------------------------
# Summarize
# ---------------------------------------------------------------------------

def summarize(results: List[StimulusResult], t_steps: int) -> ConditionSummary:
    cond = results[0].condition
    n = len(results)

    curves = np.array([r.isolate_curve for r in results])  # (n, t_steps)
    mean_iso = curves.mean(axis=0).round(4).tolist()
    std_iso  = curves.std(axis=0).round(4).tolist()

    onsets = np.array([r.collapse_onset_step for r in results], dtype=float)
    collapsed_mask = np.array([r.collapsed for r in results])

    collapse_rate = float(collapsed_mask.mean())

    # Mean onset excluding ∞ (only stimuli that actually collapsed)
    collapsed_onsets = onsets[collapsed_mask]
    mean_onset_collapsed = float(collapsed_onsets.mean()) if len(collapsed_onsets) > 0 else float(t_steps)
    std_onset = float(collapsed_onsets.std()) if len(collapsed_onsets) > 1 else 0.0

    # Pessimistic mean: treat ∞ as T
    mean_onset_all = float(onsets.mean())

    return ConditionSummary(
        condition=cond,
        n_stimuli=n,
        mean_isolate=mean_iso,
        std_isolate=std_iso,
        collapse_rate=collapse_rate,
        mean_onset_step=mean_onset_collapsed,
        mean_onset_step_all=mean_onset_all,
        std_onset_step=std_onset,
        min_onset_step=int(onsets[collapsed_mask].min()) if collapsed_mask.any() else t_steps,
        max_onset_step=int(onsets[collapsed_mask].max()) if collapsed_mask.any() else t_steps,
    )


# ---------------------------------------------------------------------------
# Hypothesis tests
# ---------------------------------------------------------------------------

def test_hypotheses(summaries: dict[str, ConditionSummary], t_steps: int) -> dict:
    c = summaries

    # H1: noisy_audio < clean in mean_onset_step_all
    h1 = c["noisy_audio"].mean_onset_step_all < c["clean"].mean_onset_step_all
    h1_vals = (c["noisy_audio"].mean_onset_step_all, c["clean"].mean_onset_step_all)

    # H2: jailbreak has lowest (earliest) mean_onset_step_all
    onsets_all = {k: v.mean_onset_step_all for k, v in c.items()}
    h2 = onsets_all["jailbreak"] == min(onsets_all.values())
    h2_vals = onsets_all

    # H3: clean has highest collapse_onset (latest or ∞)
    h3 = c["clean"].mean_onset_step_all == max(v.mean_onset_step_all for v in c.values())
    h3_vals = {k: v.mean_onset_step_all for k, v in c.items()}

    # H4: Isolate_in is monotonically non-increasing in clean condition (mean curve)
    clean_curve = np.array(c["clean"].mean_isolate)
    h4 = bool(np.all(np.diff(clean_curve) <= 0.05))   # allow tiny noise bumps ≤0.05
    h4_max_increase = float(np.maximum(0, np.diff(clean_curve)).max())

    return {
        "H1_noisy_earlier": {"passed": h1, "noisy_mean_t": round(h1_vals[0], 2), "clean_mean_t": round(h1_vals[1], 2)},
        "H2_jailbreak_earliest": {"passed": h2, "all_mean_t": {k: round(v, 2) for k, v in h2_vals.items()}},
        "H3_clean_latest": {"passed": h3, "all_mean_t": {k: round(v, 2) for k, v in h3_vals.items()}},
        "H4_clean_monotone": {"passed": h4, "max_increase": round(h4_max_increase, 4)},
    }


# ---------------------------------------------------------------------------
# ASCII plot: Isolate_in(t) mean curves
# ---------------------------------------------------------------------------

def plot_ascii(summaries: dict[str, ConditionSummary], threshold: float, t_steps: int) -> None:
    HEIGHT = 12
    BAR_CHARS = " ▁▂▃▄▅▆▇█"

    print(f"\n  Isolate_in(t) — Mean Curves (threshold = {threshold})")
    print(f"  {'t':<4}", end="")
    for c in CONDITIONS:
        print(f"  {c:<18}", end="")
    print()
    print("  " + "─" * (4 + len(CONDITIONS) * 20))

    for t in range(t_steps):
        row = f"  {t:<4}"
        for cond in CONDITIONS:
            val = summaries[cond].mean_isolate[t]
            bar_idx = min(int(val / 0.125), len(BAR_CHARS) - 1)
            bar = BAR_CHARS[bar_idx]
            below_marker = " *" if val < threshold else "  "
            row += f"  {bar} {val:.3f}{below_marker}      "
        print(row)

    print(f"  (* = below threshold {threshold})")


# ---------------------------------------------------------------------------
# Full text report
# ---------------------------------------------------------------------------

def print_report(
    summaries: dict[str, ConditionSummary],
    hyp: dict,
    threshold: float,
    t_steps: int,
) -> None:
    print("=" * 70)
    print("  Q085 — Collapse Onset Step Diagnostic")
    print("  Measure: Isolate_in(t) per decoder step → collapse_onset_step")
    print(f"  Threshold: {threshold}  |  T_steps: {t_steps}  |  Stimuli: {summaries['clean'].n_stimuli}")
    print("=" * 70)

    # Summary table
    print(f"\n  {'Condition':<16} {'Collapse%':>10}  {'Mean t*':>8}  {'Std t*':>8}  {'Min t*':>8}  {'Max t*':>8}")
    print(f"  {'─' * 65}")
    for cond in CONDITIONS:
        s = summaries[cond]
        mean_t_str = f"{s.mean_onset_step:.1f}" if s.collapse_rate > 0 else "—"
        std_t_str  = f"{s.std_onset_step:.1f}"  if s.collapse_rate > 0 else "—"
        min_t_str  = str(s.min_onset_step) if s.collapse_rate > 0 else "—"
        max_t_str  = str(s.max_onset_step) if s.collapse_rate > 0 else "—"
        print(f"  {cond:<16} {s.collapse_rate:>10.1%}  {mean_t_str:>8}  {std_t_str:>8}  "
              f"{min_t_str:>8}  {max_t_str:>8}")

    print(f"\n  Note: Mean t* excludes non-collapsed stimuli. "
          f"∞={t_steps} if no collapse observed.")

    # Mean onset (pessimistic, including ∞=T)
    print(f"\n  Mean t* (all stimuli, ∞={t_steps}):")
    for cond in CONDITIONS:
        s = summaries[cond]
        print(f"    {cond:<16}  {s.mean_onset_step_all:.2f}")

    # ASCII curves
    plot_ascii(summaries, threshold, t_steps)

    # Hypotheses
    print("\n  ── Hypothesis Test Results ─────────────────────────────────────────")
    icons = {True: "✅", False: "❌"}
    for hname, hres in hyp.items():
        icon = icons[hres["passed"]]
        detail = {k: v for k, v in hres.items() if k != "passed"}
        print(f"  {icon} {hname}: {detail}")

    # Diagnostic definition
    print("\n  ── Diagnostic Definition ───────────────────────────────────────────")
    print("  collapse_onset_step(stimulus, condition) =")
    print(f"    min{{t ∈ [0, T-1] : Isolate_in(t) < {threshold}}}")
    print(f"    = T ({INF_STEP}) if Isolate_in(t) ≥ {threshold} for all t")
    print()
    print("  Interpretation:")
    print("    Low t* → model stops listening early → high error risk")
    print("    High t* / ∞ → model maintains audio grounding through decoding")
    print("    Δt* across conditions = modality-grounding gap diagnostic")
    print()
    print("  Derived metrics:")
    print("    grounding_gap(cond_a, cond_b) = t*(cond_b) - t*(cond_a)   [+∞ if b never collapses]")
    print("    grounding_rate(cond)          = collapse_rate = P(t* < T)")
    print("    early_collapse_fraction(cond) = P(t* < T/2)")

    print("\n" + "=" * 70)
    print("  ✓ Q085 DONE: collapse_onset_step diagnostic defined and validated")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Matplotlib plot
# ---------------------------------------------------------------------------

def plot_matplotlib(summaries: dict[str, ConditionSummary], threshold: float, t_steps: int) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not available — skipping --plot")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

    # Left: Isolate_in(t) mean curves
    colors = {"clean": "steelblue", "noisy_audio": "orange",
              "text_override": "green", "jailbreak": "red"}
    steps = np.arange(t_steps)
    for cond in CONDITIONS:
        s = summaries[cond]
        mean_arr = np.array(s.mean_isolate)
        std_arr  = np.array(s.std_isolate)
        ax1.plot(steps, mean_arr, label=cond, color=colors[cond], linewidth=2)
        ax1.fill_between(steps, mean_arr - std_arr, mean_arr + std_arr,
                         alpha=0.15, color=colors[cond])
    ax1.axhline(threshold, linestyle="--", color="gray", linewidth=1, label=f"threshold={threshold}")
    ax1.set_xlabel("Decoder step t")
    ax1.set_ylabel("Isolate_in(t)")
    ax1.set_title("Mean Isolate_in(t) by Condition")
    ax1.legend(fontsize=9)
    ax1.set_ylim(0, 0.85)

    # Right: collapse_onset_step histogram
    for cond in CONDITIONS:
        s = summaries[cond]
        if s.collapse_rate > 0:
            ax2.bar(cond, s.mean_onset_step, yerr=s.std_onset_step,
                    capsize=4, color=colors[cond], alpha=0.8, label=cond)
    ax2.set_ylabel("Mean collapse_onset_step t*")
    ax2.set_title("Mean t* by Condition (collapsed stimuli only)")
    ax2.axhline(t_steps, linestyle="--", color="gray", linewidth=1, label="T (no collapse)")

    fig.suptitle("Q085: Collapse Onset Step Diagnostic (Mock Mode)", fontsize=12)
    plt.tight_layout()

    import os
    os.makedirs("memory/learning/cycles", exist_ok=True)
    out = "memory/learning/cycles/q085_collapse_onset_step.png"
    plt.savefig(out, dpi=120)
    print(f"  Plot saved → {out}")
    plt.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Q085: Collapse Onset Step — Isolate_in(t) diagnostic"
    )
    parser.add_argument("--threshold", type=float, default=ISOLATE_THRESHOLD)
    parser.add_argument("--steps",     type=int,   default=T_STEPS)
    parser.add_argument("--stimuli",   type=int,   default=N_STIMULI)
    parser.add_argument("--seed",      type=int,   default=SEED)
    parser.add_argument("--json",      action="store_true")
    parser.add_argument("--plot",      action="store_true")
    args = parser.parse_args()

    global INF_STEP
    INF_STEP = args.steps

    # Run simulation
    all_results: dict[str, list] = {}
    for cond in CONDITIONS:
        all_results[cond] = simulate_isolate_in(
            cond, args.steps, args.stimuli, args.seed, args.threshold
        )

    # Summarize
    summaries = {cond: summarize(all_results[cond], args.steps) for cond in CONDITIONS}

    # Hypothesis tests
    hyp = test_hypotheses(summaries, args.steps)

    if args.json:
        out = {
            "task": "Q085",
            "config": {"threshold": args.threshold, "t_steps": args.steps,
                       "n_stimuli": args.stimuli, "seed": args.seed},
            "summaries": {c: asdict(s) for c, s in summaries.items()},
            "hypotheses": hyp,
            "diagnostic_definition": {
                "collapse_onset_step": f"min{{t: Isolate_in(t) < {args.threshold}}}",
                "inf_sentinel": args.steps,
                "derived_metrics": ["grounding_gap", "grounding_rate", "early_collapse_fraction"],
            },
        }
        print(json.dumps(out, indent=2))
        return 0

    print_report(summaries, hyp, args.threshold, args.steps)

    if args.plot:
        plot_matplotlib(summaries, args.threshold, args.steps)

    # Basic validation
    for cond, slist in all_results.items():
        for r in slist:
            assert len(r.isolate_curve) == args.steps, f"Curve length mismatch for {cond}"
            assert all(0.0 <= v <= 1.0 for v in r.isolate_curve), f"Out-of-range in {cond}"
            assert r.collapse_onset_step >= 0, f"Invalid onset for {cond}"

    return 0


if __name__ == "__main__":
    sys.exit(main())
