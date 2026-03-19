#!/usr/bin/env python3
"""
unified_results_dashboard.py
==============================
Unified evaluation dashboard for ALL OpenClaw/Autodidact experiments.
Summarises Q001-Q128 results as of 2026-03-18.

Outputs:
  1. Formatted ASCII table to stdout
  2. Aggregate statistics (pass/blocked, avg correlation, best/worst)
  3. CSV at memory/learning/all-results-2026-03-18.csv

Standalone — requires only numpy (no torch / transformers).

Usage:
    python unified_results_dashboard.py [--csv PATH]
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Master results registry
# ---------------------------------------------------------------------------

RESULTS: dict[str, dict] = {
    # ── Real-model experiments ──────────────────────────────────────────
    "Q001": {
        "name": "Voicing Geometry",
        "script": "q001_voicing_geometry.py",
        "mode": "real",
        "status": "pass",
        "metric": "peak cos_sim=0.155 (L5)",
        "correlation": None,  # representational, no r value
    },
    "Q002": {
        "name": "Causal Contribution",
        "script": "q002_causal_contribution.py",
        "mode": "real",
        "status": "pass",
        "metric": "WER ablation peak identifies causal layer",
        "correlation": None,
    },

    # ── Batch 1  Q091-Q107 (2026-03-18, 8 experiments, all pass) ──────
    "Q091": {
        "name": "AND/OR gc Patching",
        "script": "and_or_gc_patching_mock.py",
        "mode": "mock",
        "status": "pass",
        "metric": "AND%×gc(k) r=0.984; peak L3 confirmed",
        "correlation": 0.9836,
    },
    "Q092": {
        "name": "Persona gc Benchmark",
        "script": "persona_gc_benchmark.py",
        "mode": "mock",
        "status": "pass",
        "metric": "anti_ground shift=2 layers; H2,H3 ✓",
        "correlation": None,
    },
    "Q093": {
        "name": "gc Incrimination",
        "script": "gc_incrimination_mock.py",
        "mode": "mock",
        "status": "pass",
        "metric": "collapse rate 0-55%; t* detection OK",
        "correlation": None,
    },
    "Q094": {
        "name": "SAE Incrimination Patrol",
        "script": "sae_incrimination_patrol.py",
        "mode": "mock",
        "status": "pass",
        "metric": "suppress=96%, override=77%, FPR=3.3%",
        "correlation": None,
    },
    "Q095": {
        "name": "MicroGPT RAVEL",
        "script": "microgpt_ravel.py",
        "mode": "mock",
        "status": "pass",
        "metric": "acc=1.00; RAVEL 5/6 pass (83%)",
        "correlation": None,
    },
    "Q096": {
        "name": "FAD Bias × AND/OR Gate",
        "script": "fad_and_or_gate.py",
        "mode": "mock",
        "status": "pass",
        "metric": "r(text_pred, AND%)=-0.960",
        "correlation": -0.960,
    },
    "Q105": {
        "name": "RAVEL MDAS × AND/OR Gate",
        "script": "ravel_mdas_and_or.py",
        "mode": "mock",
        "status": "pass",
        "metric": "r(MDAS,AND)=0.877; cls acc=74%",
        "correlation": 0.877,
    },
    "Q106": {
        "name": "SAE Incrimination ENV Taxonomy",
        "script": "sae_incrimination_env_taxonomy.py",
        "mode": "mock",
        "status": "pass",
        "metric": "ENV-1 hub offender=100%; ENV-3=0%",
        "correlation": None,
    },
    "Q107": {
        "name": "RAVEL Isolate gc Proxy",
        "script": "ravel_isolate_gc_proxy.py",
        "mode": "mock",
        "status": "pass",
        "metric": "Pearson r=0.904; compute save=67%",
        "correlation": 0.904,
    },
    # Persona AND/OR Gate (Q091 batch partner)
    "Q091b": {
        "name": "Persona × AND/OR Gate",
        "script": "persona_and_or_gate.py",
        "mode": "mock",
        "status": "pass",
        "metric": "asst AND%=20 vs neutral=45.3 (H1 ✓)",
        "correlation": None,
    },
    "Q092b": {
        "name": "Schelling × AND/OR Gate",
        "script": "schelling_and_or_gate.py",
        "mode": "mock",
        "status": "pass",
        "metric": "stable AND%=71 vs unstable=39; r=0.330",
        "correlation": 0.330,
    },
    "Q093b": {
        "name": "Collapse Onset × AND/OR",
        "script": "collapse_onset_and_or.py",
        "mode": "mock",
        "status": "pass",
        "metric": "AND t*=5.0; OR t*=4.35",
        "correlation": None,
    },
    "Q094b": {
        "name": "T-SAE gc Incrimination",
        "script": "tsae_gc_incrimination.py",
        "mode": "mock",
        "status": "pass",
        "metric": "10 features; top max_score=0.099",
        "correlation": None,
    },

    # ── Batch 2  Q109-Q128 (2026-03-18, 12 pass + 2 blocked) ─────────
    "Q109": {
        "name": "Phoneme MDAS",
        "script": "phoneme_mdas.py",
        "mode": "mock",
        "status": "pass",
        "metric": "phoneme disentangle gap=0.135",
        "correlation": None,
    },
    "Q113": {
        "name": "Cascade Degree",
        "script": "cascade_degree.py",
        "mode": "mock",
        "status": "pass",
        "metric": "cascade_degree=1-AND%; mean=0.901",
        "correlation": None,
    },
    "Q116": {
        "name": "Backdoor Cascade Induction",
        "script": "backdoor_cascade.py",
        "mode": "mock",
        "status": "pass",
        "metric": "t* shift=-3 (leftward); detector OK",
        "correlation": None,
    },
    "Q117": {
        "name": "GSAE Graph Density",
        "script": "cascade_gsae_density.py",
        "mode": "mock",
        "status": "blocked",
        "metric": "r=-0.043 (weak); needs refinement",
        "correlation": -0.0427,
    },
    "Q118": {
        "name": "Emotion × AND/OR Gates",
        "script": "emotion_and_or_gate.py",
        "mode": "mock",
        "status": "pass",
        "metric": "emotion AND%=0 vs non-emo=44",
        "correlation": None,
    },
    "Q120": {
        "name": "ENV × GSAE Topology",
        "script": "env_gsae_topology.py",
        "mode": "mock",
        "status": "pass",
        "metric": "ENV-3 sparsity=1.5× baseline",
        "correlation": None,
    },
    "Q121": {
        "name": "Persona × Emotion × AND/OR",
        "script": "persona_emotion_and_or.py",
        "mode": "mock",
        "status": "pass",
        "metric": "3 personas × emotion dual-signal ✓",
        "correlation": None,
    },
    "Q122": {
        "name": "Incrimination Jacobian SVD",
        "script": "incrimination_jacobian.py",
        "mode": "mock",
        "status": "pass",
        "metric": "top SVD → 10 features ≥2 blames",
        "correlation": None,
    },
    "Q123": {
        "name": "FAD-RAVEL Cause/Isolate",
        "script": "fad_ravel_cause_isolate.py",
        "mode": "mock",
        "status": "blocked",
        "metric": "r=-0.70 (direction wrong)",
        "correlation": -0.70,
    },
    "Q124": {
        "name": "Codec Probe RVQ × AND/OR",
        "script": "codec_probe_and_or.py",
        "mode": "mock",
        "status": "pass",
        "metric": "RVQ-1 semantic OR-gate r=-0.90",
        "correlation": -0.90,
    },
    "Q125": {
        "name": "Schelling × T-SAE Stability",
        "script": "schelling_tsae.py",
        "mode": "mock",
        "status": "pass",
        "metric": "mean Spearman=0.639; IIA stable",
        "correlation": 0.639,
    },
    "Q126": {
        "name": "ENV × Codec RVQ",
        "script": "env_codec_rvq.py",
        "mode": "mock",
        "status": "pass",
        "metric": "ENV-1 hub RVQ-1=60%; isolated=0%",
        "correlation": None,
    },
    "Q127": {
        "name": "Power Steering × AND/OR",
        "script": "power_steering_and_or.py",
        "mode": "mock",
        "status": "pass",
        "metric": "Jacobian SVD × AND r=0.627",
        "correlation": 0.627,
    },
    "Q128": {
        "name": "Jailbreak Isolate × ENV-3",
        "script": "jailbreak_isolate_env.py",
        "mode": "mock",
        "status": "pass",
        "metric": "ENV-3 pruning r=0.888; t* restored",
        "correlation": 0.888,
    },
}


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _trunc(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def print_table(results: dict[str, dict]) -> None:
    """Print a formatted ASCII summary table."""
    hdr = f"{'ID':<6} {'Name':<30} {'Mode':<5} {'Status':<8} {'Key Metric':<42} {'r':>7}"
    sep = "-" * len(hdr)
    print(sep)
    print(hdr)
    print(sep)
    for qid, r in results.items():
        corr = f"{r['correlation']:+.3f}" if r["correlation"] is not None else "   —"
        status_str = r["status"].upper()
        print(
            f"{qid:<6} {_trunc(r['name'], 30):<30} {r['mode']:<5} "
            f"{status_str:<8} {_trunc(r['metric'], 42):<42} {corr:>7}"
        )
    print(sep)


def print_aggregate(results: dict[str, dict]) -> None:
    """Print aggregate statistics."""
    total = len(results)
    n_pass = sum(1 for r in results.values() if r["status"] == "pass")
    n_blocked = sum(1 for r in results.values() if r["status"] == "blocked")
    correlations = [
        r["correlation"]
        for r in results.values()
        if r["correlation"] is not None
    ]
    abs_corr = [abs(c) for c in correlations]

    print("\n=== AGGREGATE STATISTICS ===")
    print(f"Total experiments : {total}")
    print(f"Pass              : {n_pass}")
    print(f"Blocked           : {n_blocked}")
    print(f"Pass rate         : {n_pass / total * 100:.1f}%")

    if correlations:
        arr = np.array(correlations)
        abs_arr = np.array(abs_corr)
        print(f"\nCorrelations reported : {len(correlations)}")
        print(f"Mean |r|             : {abs_arr.mean():.3f}")
        print(f"Median |r|           : {np.median(abs_arr):.3f}")
        print(f"Max |r|              : {abs_arr.max():.3f}")
        print(f"Min |r|              : {abs_arr.min():.3f}")

        # strongest / weakest
        sorted_ids = sorted(
            [(qid, r) for qid, r in results.items() if r["correlation"] is not None],
            key=lambda x: abs(x[1]["correlation"]),
            reverse=True,
        )
        print("\nStrongest results (by |r|):")
        for qid, r in sorted_ids[:3]:
            print(f"  {qid} {r['name']:<30} r={r['correlation']:+.3f}")
        print("Weakest results (by |r|):")
        for qid, r in sorted_ids[-3:]:
            print(f"  {qid} {r['name']:<30} r={r['correlation']:+.3f}")
    else:
        print("(no correlation values to summarize)")


def write_csv(results: dict[str, dict], path: str) -> None:
    """Write results to CSV."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "name", "script", "mode", "status", "metric", "correlation"])
        for qid, r in results.items():
            writer.writerow([
                qid,
                r["name"],
                r["script"],
                r["mode"],
                r["status"],
                r["metric"],
                r["correlation"] if r["correlation"] is not None else "",
            ])
    print(f"\nCSV written to {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Unified experiment results dashboard")
    parser.add_argument(
        "--csv",
        default=os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "memory", "learning", "all-results-2026-03-18.csv",
        ),
        help="Output CSV path",
    )
    args = parser.parse_args()

    csv_path = os.path.normpath(args.csv)

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     OpenClaw / Autodidact — Unified Results Dashboard      ║")
    print("║                      2026-03-18                            ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")

    print_table(RESULTS)
    print_aggregate(RESULTS)
    write_csv(RESULTS, csv_path)


if __name__ == "__main__":
    main()
