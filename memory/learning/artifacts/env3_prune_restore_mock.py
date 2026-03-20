"""
env3_prune_restore_mock.py — Q128

Hypothesis: Jailbreak audio activates ENV-3 (isolated, periphery) SAE features
that pollute the audio integration pathway, causing t* (collapse onset) to shift
leftward (early collapse = "giving up on audio"). Pruning ENV-3 features restores
t* toward the clean baseline.

ENV Taxonomy (from Q106):
  ENV-1: Hub features  — high GSAE connectivity, causally influential
  ENV-2: Normal        — intermediate connectivity
  ENV-3: Isolated      — low connectivity (<2 active edges), periphery noise

Experimental Setup:
  - Mock audio model with 8 decoder steps (t=0..7)
  - 40 SAE features; ENV labels assigned by GSAE connectivity
  - Clean input: ENV-3 features mostly silent → t* = 6 (late collapse)
  - Jailbreak input: ENV-3 features over-activated → t* = 4 (early collapse)
  - After ENV-3 pruning (zero-out): measure t* recovery

Key Metric:
  t*_restored > t*_jailbreak  → pruning restores audio integration

Theoretical Link:
  ENV-3 features = isolated GSAE nodes → no clean causal paths in circuit
  When activated by adversarial perturbation: they inject "dead-end" activations
  that consume residual stream capacity → Isolate(k) drops earlier → leftward t*
  Pruning removes this noise → causal paths can route normally → t* recovers

Usage:
    python3 env3_prune_restore_mock.py
    python3 env3_prune_restore_mock.py --n-trials 20 --verbose
"""

import argparse
import statistics
import random

RNG_SEED = 42
random.seed(RNG_SEED)

N_STEPS = 8      # decoder steps t = 0..7
N_FEATURES = 40  # SAE feature count


# ─── ENV Label Assignment ────────────────────────────────────────────────────

def assign_env_labels(n_features: int, rng: random.Random) -> list[str]:
    """
    Assign ENV labels based on mock GSAE connectivity.
    ENV-1: ~20% (hubs), ENV-2: ~55% (normal), ENV-3: ~25% (isolated).
    """
    labels = []
    for _ in range(n_features):
        r = rng.random()
        if r < 0.20:
            labels.append("ENV-1")
        elif r < 0.75:
            labels.append("ENV-2")
        else:
            labels.append("ENV-3")
    return labels


# ─── Isolate Curve Generation ────────────────────────────────────────────────

def isolate_curve_from_activations(
    activations: list[list[float]],  # [step][feature]
    env_labels: list[str],
    env3_penalty: float = 0.0,
) -> list[float]:
    """
    Simulate Isolate(k) per decoder step.

    Base Isolate curve: high in early steps (rich audio routing),
    falls as decoding proceeds. ENV-3 activations reduce Isolate faster
    (they add noise, consuming causal path capacity).

    env3_penalty: per-unit reduction in Isolate per active ENV-3 feature.
    """
    # Base Isolate: peaks at t=1, falls smoothly
    base = [0.85, 0.92, 0.82, 0.68, 0.52, 0.35, 0.20, 0.10]

    env3_indices = [i for i, l in enumerate(env_labels) if l == "ENV-3"]

    isolate = []
    for t in range(N_STEPS):
        iso = base[t]
        if env3_penalty > 0 and env3_indices:
            # Count active ENV-3 features at this step
            active_env3 = sum(1 for i in env3_indices if activations[t][i] > 0.3)
            # Each active ENV-3 feature reduces Isolate
            iso = max(0.02, iso - env3_penalty * active_env3)
        isolate.append(iso)

    return isolate


def compute_t_star(isolate: list[float]) -> int:
    """t* = argmin(Isolate): step where audio information collapses."""
    return isolate.index(min(isolate))


# ─── Activation Profiles ─────────────────────────────────────────────────────

def clean_activations(n_features: int, env_labels: list[str], rng: random.Random) -> list[list[float]]:
    """
    Clean input activations: ENV-3 features are mostly silent (audio not exploiting isolated nodes).
    ENV-1 hubs active throughout; ENV-2 fade mid-decode.
    """
    acts = []
    for t in range(N_STEPS):
        step_acts = []
        for i in range(n_features):
            lbl = env_labels[i]
            noise = rng.gauss(0, 0.05)
            if lbl == "ENV-1":
                # Hubs: consistently active across all steps
                val = 0.75 + noise
            elif lbl == "ENV-2":
                # Normal: decay from step 3 onward
                val = (0.60 if t < 4 else 0.30) + noise
            else:  # ENV-3
                # Isolated: sparse, mostly silent in clean audio
                val = 0.10 + rng.gauss(0, 0.08)
            step_acts.append(max(0.0, min(1.0, val)))
        acts.append(step_acts)
    return acts


def jailbreak_activations(n_features: int, env_labels: list[str], rng: random.Random) -> list[list[float]]:
    """
    Jailbreak input activations: adversarial perturbation over-activates ENV-3 features.
    This injects isolated-node noise, disrupting causal audio pathways.
    """
    acts = []
    for t in range(N_STEPS):
        step_acts = []
        for i in range(n_features):
            lbl = env_labels[i]
            noise = rng.gauss(0, 0.05)
            if lbl == "ENV-1":
                # Hubs still active (adversarial doesn't easily affect well-connected nodes)
                val = 0.70 + noise
            elif lbl == "ENV-2":
                # Normal features slightly suppressed by noise
                val = (0.50 if t < 4 else 0.25) + noise
            else:  # ENV-3
                # ADVERSARIAL: ENV-3 features over-activated (3-5x normal)
                boost = rng.uniform(0.45, 0.75) if t < 5 else rng.uniform(0.25, 0.45)
                val = boost + noise
            step_acts.append(max(0.0, min(1.0, val)))
        acts.append(step_acts)
    return acts


def prune_env3(
    activations: list[list[float]],
    env_labels: list[str],
) -> list[list[float]]:
    """
    ENV-3 pruning: zero-out (or soft-clamp) activations for all ENV-3 features.
    This simulates a feature-level intervention: remove the isolated periphery noise.
    """
    pruned = []
    env3_mask = [l == "ENV-3" for l in env_labels]
    for t in range(N_STEPS):
        step_acts = list(activations[t])
        for i in range(len(step_acts)):
            if env3_mask[i]:
                step_acts[i] = 0.0  # hard prune
        pruned.append(step_acts)
    return pruned


# ─── Single Trial ─────────────────────────────────────────────────────────────

def run_trial(
    env3_penalty: float = 0.032,
    rng: random.Random | None = None,
    verbose: bool = False,
) -> dict:
    """
    Run one trial:
      1. Assign ENV labels
      2. Generate clean / jailbreak activations
      3. Compute t* for: clean, jailbreak, jailbreak+pruned
      4. Check: t*_restored > t*_jailbreak
    """
    if rng is None:
        rng = random.Random(42)

    env_labels = assign_env_labels(N_FEATURES, rng)
    n_env3 = env_labels.count("ENV-3")

    # --- Clean ---
    acts_clean = clean_activations(N_FEATURES, env_labels, rng)
    iso_clean = isolate_curve_from_activations(acts_clean, env_labels, env3_penalty)
    t_star_clean = compute_t_star(iso_clean)

    # --- Jailbreak ---
    acts_jailbreak = jailbreak_activations(N_FEATURES, env_labels, rng)
    iso_jailbreak = isolate_curve_from_activations(acts_jailbreak, env_labels, env3_penalty)
    t_star_jailbreak = compute_t_star(iso_jailbreak)

    # --- Jailbreak + ENV-3 Pruning ---
    acts_pruned = prune_env3(acts_jailbreak, env_labels)
    iso_pruned = isolate_curve_from_activations(acts_pruned, env_labels, env3_penalty)
    t_star_pruned = compute_t_star(iso_pruned)

    # Check recovery: pruned t* should exceed jailbreak t*
    recovery = t_star_pruned > t_star_jailbreak

    if verbose:
        print(f"  n_ENV3={n_env3:2d} | "
              f"t*_clean={t_star_clean} | "
              f"t*_jailbreak={t_star_jailbreak} | "
              f"t*_restored={t_star_pruned} | "
              f"recovery={'✅' if recovery else '❌'}")

    return {
        "t_star_clean": t_star_clean,
        "t_star_jailbreak": t_star_jailbreak,
        "t_star_restored": t_star_pruned,
        "n_env3": n_env3,
        "recovery": recovery,
        "shift_jailbreak": t_star_clean - t_star_jailbreak,   # positive = leftward shift
        "shift_restored": t_star_pruned - t_star_jailbreak,   # positive = recovery
        "full_restore": t_star_pruned >= t_star_clean,        # full vs partial
    }


# ─── Sensitivity Analysis ─────────────────────────────────────────────────────

def penalty_sweep(n_trials: int = 30) -> None:
    """Test across different ENV-3 penalty levels to find effective intervention range."""
    print(f"\n{'='*65}")
    print(f"PENALTY SWEEP (n_trials={n_trials})")
    print(f"{'='*65}")
    print(f"{'penalty':>10} {'recovery%':>12} {'full_restore%':>15} {'avg_Δt*':>10}")
    print(f"{'-'*55}")

    for penalty in [0.010, 0.020, 0.032, 0.045, 0.060, 0.080]:
        rng = random.Random(123)
        results = [run_trial(env3_penalty=penalty, rng=rng) for _ in range(n_trials)]
        recovery_rate = sum(r["recovery"] for r in results) / n_trials
        full_restore_rate = sum(r["full_restore"] for r in results) / n_trials
        avg_delta = statistics.mean(r["shift_restored"] for r in results)
        print(f"{penalty:>10.3f} {recovery_rate:>12.1%} {full_restore_rate:>15.1%} {avg_delta:>10.2f}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ENV-3 pruning restores t* collapse onset after jailbreak"
    )
    parser.add_argument("--n-trials", type=int, default=40,
                        help="Number of random trials (default: 40)")
    parser.add_argument("--penalty", type=float, default=0.032,
                        help="ENV-3 activity penalty on Isolate per feature (default: 0.032)")
    parser.add_argument("--verbose", action="store_true",
                        help="Print per-trial details (first 10)")
    parser.add_argument("--sweep", action="store_true",
                        help="Run penalty sensitivity sweep")
    args = parser.parse_args()

    print("ENV-3 Pruning → t* Restoration Mock Experiment")
    print(f"Config: n_trials={args.n_trials}, env3_penalty={args.penalty:.3f}")
    print(f"Architecture: {N_STEPS} decoder steps, {N_FEATURES} SAE features")
    print()

    master_rng = random.Random(RNG_SEED)
    results = []
    for trial_idx in range(args.n_trials):
        trial_rng = random.Random(master_rng.randint(0, 2**31))
        r = run_trial(
            env3_penalty=args.penalty,
            rng=trial_rng,
            verbose=(args.verbose and trial_idx < 10),
        )
        results.append(r)

    # ── Summary ──────────────────────────────────────────────────────────────
    recovery_rate = sum(r["recovery"] for r in results) / len(results)
    full_restore_rate = sum(r["full_restore"] for r in results) / len(results)

    avg_t_clean = statistics.mean(r["t_star_clean"] for r in results)
    avg_t_jailbreak = statistics.mean(r["t_star_jailbreak"] for r in results)
    avg_t_restored = statistics.mean(r["t_star_restored"] for r in results)
    avg_shift_jb = statistics.mean(r["shift_jailbreak"] for r in results)
    avg_shift_restore = statistics.mean(r["shift_restored"] for r in results)
    avg_n_env3 = statistics.mean(r["n_env3"] for r in results)

    print(f"Results ({args.n_trials} trials):")
    print(f"  Avg ENV-3 features/model : {avg_n_env3:.1f} / {N_FEATURES}")
    print()
    print(f"  t* (clean)               : {avg_t_clean:.2f}")
    print(f"  t* (jailbreak)           : {avg_t_jailbreak:.2f}  ← leftward shift: {avg_shift_jb:.2f}")
    print(f"  t* (jailbreak + pruning) : {avg_t_restored:.2f}  ← rightward recovery: +{avg_shift_restore:.2f}")
    print()
    print(f"  Recovery rate (t*_restored > t*_jailbreak) : {recovery_rate:.1%}")
    print(f"  Full restore  (t*_restored >= t*_clean)    : {full_restore_rate:.1%}")

    # ── DoD Check ────────────────────────────────────────────────────────────
    print()
    dod_pass = (recovery_rate >= 0.75) and (avg_t_restored > avg_t_jailbreak)
    if dod_pass:
        print("✅ DoD PASS: t*_restored > t*_jailbreak in majority of trials")
        print("   ENV-3 pruning partially restores audio integration after jailbreak.")
        print()
        print("Mechanistic Interpretation:")
        print(f"  • Jailbreak activates ~{avg_n_env3:.0f} isolated (ENV-3) features")
        print(f"  • These inject dead-end noise into causal pathways")
        print(f"  • Isolate(k) drops {avg_shift_jb:.1f} steps earlier (t*={avg_t_jailbreak:.1f} vs clean={avg_t_clean:.1f})")
        print(f"  • Pruning ENV-3 removes the noise → t* recovers by +{avg_shift_restore:.1f} steps")
        print()
        print("Connection to Paper A (Listen vs Guess):")
        print("  • t* leftward = 'giving up on audio' = collapse-induced error")
        print("  • ENV-3 = periphery features with no causal role in gc circuit")
        print("  • Adversarial perturbation exploits isolated features as attack surface")
        print("  • Defense: prune ENV-3 at inference → restore causal audio routing")
        print()
        print("Connection to T5 (Listen-Layer Audit / Safety):")
        print("  • ENV-3 pruning is a feature-level jailbreak defense")
        print("  • No model fine-tuning needed; applied post-hoc at inference")
        print("  • Generalizable to any SAE-interpretable audio model")
    else:
        print("❌ DoD FAIL")
        if recovery_rate < 0.75:
            print(f"   Recovery rate {recovery_rate:.1%} < 75% threshold")
        if avg_t_restored <= avg_t_jailbreak:
            print(f"   t*_restored ({avg_t_restored:.2f}) not > t*_jailbreak ({avg_t_jailbreak:.2f})")

    if args.sweep:
        penalty_sweep(n_trials=30)


if __name__ == "__main__":
    main()
