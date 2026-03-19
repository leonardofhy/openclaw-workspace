#!/usr/bin/env python3
"""Experiment Design Assistant — gap-aware next-experiment recommender.

Loads all experiment results + knowledge graph gaps, identifies strategic
priorities, and ranks top 10 recommendations by impact × feasibility / risk.

Usage:
    python3 skills/autodidact/tools/experiment_designer.py
    python3 skills/autodidact/tools/experiment_designer.py --track T3
    python3 skills/autodidact/tools/experiment_designer.py --budget cpu
    python3 skills/autodidact/tools/experiment_designer.py --track T3 --budget cpu --top 5
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "shared"))
from jsonl_store import find_workspace

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

WS = find_workspace()
KG_PATH = WS / "memory" / "learning" / "knowledge-graph.md"
QUEUE_PATH = WS / "memory" / "learning" / "state" / "queue.json"
CSV_DIR = WS / "memory" / "learning"


@dataclass
class Gap:
    id: int
    title: str
    status: str  # OPEN, PARTIAL, HOLD, CLOSED
    track: str
    paper: str  # Paper A, Paper B, or both
    description: str
    experiments: list[str] = field(default_factory=list)  # experiment IDs
    phase_transition: bool = False  # unlocks major paper section


@dataclass
class Suggestion:
    gap_id: int
    gap_title: str
    experiment_name: str
    design: str
    stimuli: str
    metric: str
    expected_outcome: str
    compute: str  # cpu or gpu
    est_time: str
    risk: str  # low, medium, high
    risk_score: float  # 1=low, 2=med, 3=high
    impact: float  # 1-10
    feasibility: float  # 1-10
    paper_section: str
    cross_gaps: list[int] = field(default_factory=list)
    track: str = ""

    @property
    def score(self) -> float:
        return self.impact * self.feasibility / max(self.risk_score, 0.5)


# ---------------------------------------------------------------------------
# Knowledge base — gaps and their experimental status
# ---------------------------------------------------------------------------

def build_gap_registry() -> list[Gap]:
    """Hardcoded gap registry derived from knowledge-graph.md."""
    return [
        Gap(11, "gc at neuron level (class-specific neuron grounding)",
            "PARTIAL", "T3", "A+B",
            "Kawamura/Zhao find class-specific neurons but never ask audio-vs-text pathway",
            ["Q118", "Q121"], phase_transition=False),
        Gap(12, "Temporally-resolved SAE for audio",
            "PARTIAL", "T2", "B",
            "Nobody has frame-level temporal SAE for audio; Mariotte loses time via mean-pool",
            ["Q094b", "Q125"], phase_transition=True),
        Gap(13, "EmoOmni Thinker-Talker bottleneck",
            "OPEN", "T3", "A",
            "No DAS at Thinker-Talker interface in EmoOmni architecture",
            [], phase_transition=False),
        Gap(14, "Modality Collapse formal theory",
            "OPEN", "T3", "A",
            "Formal theory explaining why audio info is encoded but decoder cannot use it",
            [], phase_transition=True),
        Gap(15, "Cascade Equivalence metric",
            "PARTIAL", "T3", "A",
            "LEACE erasure confirms speech LLMs are implicit ASR cascades except Qwen2-Audio",
            ["Q113"], phase_transition=False),
        Gap(16, "ALME causal layer patching",
            "OPEN", "T3", "A",
            "No causal layer patching on ALME 57K conflict stimuli",
            [], phase_transition=True),
        Gap(18, "Phonological vector geometry through connector",
            "PARTIAL", "T3", "A",
            "Does linear phonological structure survive through connector into speech LLMs?",
            ["Q109"], phase_transition=True),
        Gap(19, "Standardized audio SAE training pipeline",
            "OPEN", "T2", "B",
            "SAELens has zero audio SAEs; all papers use custom one-off code",
            [], phase_transition=False),
        Gap(20, "Emotion-modulated safety",
            "HOLD", "T5", "—",
            "Speaker emotion overrides LALM safety alignment non-monotonically",
            ["Q118", "Q121"], phase_transition=False),
        Gap(21, "Codec causal patching in LALMs",
            "PARTIAL", "T3", "A+B",
            "No causal patching of per-layer RVQ token streams in LALM inference",
            ["Q124", "Q126"], phase_transition=True),
        Gap(23, "Audio-RAVEL disentanglement",
            "PARTIAL", "T2", "B",
            "RAVEL Cause+Isolate for audio attributes; AudioSAEBench Cat 0",
            ["Q095", "Q105", "Q107", "Q109"], phase_transition=True),
        Gap(24, "SAE jailbreak feature attribution",
            "PARTIAL", "T5", "B",
            "Which AudioSAE features are noise-sensitive in jailbreak attacks?",
            ["Q094", "Q128"], phase_transition=False),
        Gap(26, "Speech LLM causal subspaces (DAS)",
            "PARTIAL", "T3", "A",
            "No DAS study for pre-trained speech LLMs; Maghsoudi only did brain-to-speech",
            ["Q001", "Q002"], phase_transition=True),
        Gap(27, "Audio absent from MMFM MI surveys",
            "OPEN", "T3", "A",
            "Structural gap; closed by publishing Paper A",
            [], phase_transition=False),
    ]


def load_experiment_results() -> dict[str, dict]:
    """Load latest CSV results into a dict keyed by experiment ID."""
    results = {}
    csv_files = sorted(CSV_DIR.glob("all-results-*.csv"), reverse=True)
    if not csv_files:
        return results
    with open(csv_files[0], newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            results[row["id"]] = row
    return results


def load_queue() -> list[dict]:
    """Load current queue tasks."""
    if not QUEUE_PATH.exists():
        return []
    with open(QUEUE_PATH) as f:
        data = json.load(f)
    return data.get("tasks", [])


# ---------------------------------------------------------------------------
# Suggestion generation
# ---------------------------------------------------------------------------

def generate_suggestions(gaps: list[Gap], results: dict, queue: list[dict]) -> list[Suggestion]:
    """Generate experiment suggestions based on gap analysis."""
    suggestions: list[Suggestion] = []
    queued_ids = {t["id"] for t in queue}

    # --- Priority 1: Gaps with NO experiments (highest priority) ---

    # Gap #14 — Modality Collapse formal theory
    suggestions.append(Suggestion(
        gap_id=14,
        gap_title="Modality Collapse formal theory",
        experiment_name="Connector Subspace Transfer Test",
        design="Train DAS rotation R at Whisper encoder layer for voicing variable; "
               "apply as FIXED rotation at LLM layer 0 (no retraining). "
               "Compare IIA_transfer vs gc(encoder).",
        stimuli="Choi et al. minimal pairs (voicing contrasts, ~200 pairs)",
        metric="IIA_transfer at LLM layer 0 vs gc(encoder); ratio = subspace preservation",
        expected_outcome="IIA_transfer << gc(encoder) → connector adds rotation; "
                         "both ≈ 0 → connector bottleneck (Modality Collapse confirmed)",
        compute="cpu",
        est_time="~30 min on MacBook (Whisper-small, 6 layers)",
        risk="medium",
        risk_score=2.0,
        impact=9.5,
        feasibility=8.0,
        paper_section="Paper A §3 (methodology) + Figure 2",
        cross_gaps=[18, 26],
        track="T3",
    ))

    # Gap #16 — ALME causal layer patching
    suggestions.append(Suggestion(
        gap_id=16,
        gap_title="ALME causal layer patching",
        experiment_name="DAS-gc(k) Sweep on ALME Conflict Stimuli",
        design="Run DAS at each Qwen2-Audio decoder layer using ALME audio-text "
               "conflict pairs. Measure IIA per layer → gc(k) curve.",
        stimuli="ALME dataset (57K audio-text conflict pairs, off-the-shelf)",
        metric="gc(k) = DAS-IIA per layer; peak layer L* = Listen Layer",
        expected_outcome="Clear gc(k) peak at mid-layers (~L6-7 for Whisper-scale); "
                         "validates Listen Layer Hypothesis with real conflict stimuli",
        compute="gpu",
        est_time="~4h on NDIF (Qwen2-Audio-7B remote)",
        risk="medium",
        risk_score=2.0,
        impact=10.0,
        feasibility=5.0,
        paper_section="Paper A §5 (main result), Figure 3",
        cross_gaps=[26],
        track="T3",
    ))

    # Gap #13 — EmoOmni Thinker-Talker
    suggestions.append(Suggestion(
        gap_id=13,
        gap_title="EmoOmni Thinker-Talker bottleneck",
        experiment_name="DAS at Thinker-Talker Interface",
        design="Apply DAS at the Thinker→Talker boundary in EmoOmni. "
               "Test whether phonological subspace transfers across the interface.",
        stimuli="Emotion-labeled speech with phonological minimal pairs",
        metric="IIA at Thinker output vs Talker input; delta = interface loss",
        expected_outcome="Information bottleneck at Thinker-Talker boundary; "
                         "emotion features survive but phonological features degrade",
        compute="gpu",
        est_time="~6h (requires EmoOmni weights + NDIF)",
        risk="high",
        risk_score=3.0,
        impact=6.0,
        feasibility=3.0,
        paper_section="Paper A §6 (cross-architecture generalization)",
        cross_gaps=[],
        track="T3",
    ))

    # Gap #19 — SAELens audio pipeline
    suggestions.append(Suggestion(
        gap_id=19,
        gap_title="Standardized audio SAE training pipeline",
        experiment_name="SAELens Audio Training Wrapper",
        design="Implement SAELens-compatible data loader for Whisper/HuBERT activations. "
               "Train TopK SAE (8x expansion) on LibriSpeech via SAELens API. "
               "Upload trained SAEs with 'saelens' tag to HuggingFace.",
        stimuli="LibriSpeech clean-100 (encoder activations at layers 1-12)",
        metric="Reconstruction loss; feature stability across seeds; downstream phoneme acc",
        expected_outcome="Reproducible audio SAE training in <50 lines; "
                         "community adoption via pip install + HF upload",
        compute="cpu",
        est_time="~2 days engineering",
        risk="low",
        risk_score=1.0,
        impact=7.0,
        feasibility=7.0,
        paper_section="Paper B §3 (benchmark infrastructure)",
        cross_gaps=[23],
        track="T2",
    ))

    # --- Priority 2: Gaps with weak results (needs better experiment) ---

    # Q117 retry — GSAE Graph Density (r=-0.043)
    suggestions.append(Suggestion(
        gap_id=12,  # connects to T-SAE / structural gaps
        gap_title="GSAE topology → gc correlation (Q117 retry)",
        experiment_name="GSAE Edge-Level Density Metric",
        design="Replace global graph density with edge-level or community-level metrics. "
               "Test GSAE degree distribution (not just density) against AND-gate fraction. "
               "Use Louvain community detection on GSAE graph; correlate community count "
               "with cascade_degree.",
        stimuli="Same mock GSAE graphs as Q117 + expanded topology variants",
        metric="Spearman correlation of community_count vs AND%; edge_betweenness vs gc",
        expected_outcome="Edge-level metrics should capture structural gc signal "
                         "that global density missed (r > 0.5)",
        compute="cpu",
        est_time="~2h (numpy + networkx)",
        risk="medium",
        risk_score=2.0,
        impact=5.0,
        feasibility=8.0,
        paper_section="Paper B §4 (topology analysis)",
        cross_gaps=[],
        track="T2",
    ))

    # Q123 reframe — FAD-RAVEL (r=-0.70 wrong direction)
    suggestions.append(Suggestion(
        gap_id=23,
        gap_title="FAD-RAVEL negative result reframe",
        experiment_name="FAD Polysemanticity as Paper B Caveat",
        design="Reanalyze Q123 r=-0.70 as meaningful negative result: FAD-biased "
               "features are polysemantic (high Cause but low Isolate). Design follow-up "
               "that uses MDAS (multi-task DAS) instead of single-attribute Isolate to "
               "properly handle polysemantic features.",
        stimuli="Q123 data + MDAS multi-attribute rotation training",
        metric="MDAS Isolate score for FAD-biased features; compare with single-DAS Isolate",
        expected_outcome="MDAS Isolate >> single-DAS Isolate for FAD features, confirming "
                         "polysemanticity is the confound (not method failure)",
        compute="cpu",
        est_time="~3h (mock MDAS + reanalysis)",
        risk="low",
        risk_score=1.0,
        impact=6.0,
        feasibility=8.0,
        paper_section="Paper B §4 (encoder selection caveat)",
        cross_gaps=[],
        track="T2",
    ))

    # Q092b weak — Schelling × AND/OR (r=0.330)
    suggestions.append(Suggestion(
        gap_id=15,
        gap_title="Schelling stability → grounding (strengthen Q092b)",
        experiment_name="Schelling Focal Point × Cascade Degree",
        design="Extend Q092b by using cascade_degree (Q113) instead of raw AND%. "
               "Test whether Schelling-stable coalitions correlate with cascade_degree "
               "rather than AND% directly. Add iterated best-response dynamics.",
        stimuli="Same mock as Q092b + cascade_degree from Q113 + iterated dynamics",
        metric="Spearman r(Schelling_stability, cascade_degree); Nash equilibrium count",
        expected_outcome="cascade_degree should be a better predictor than raw AND% "
                         "(r > 0.5 vs current 0.330)",
        compute="cpu",
        est_time="~1.5h (numpy)",
        risk="low",
        risk_score=1.5,
        impact=4.0,
        feasibility=9.0,
        paper_section="Paper A §5.5 (game-theoretic validation)",
        cross_gaps=[],
        track="T3",
    ))

    # --- Priority 3: Phase-transition unlocking experiments ---

    # Gap #18 full → real model
    suggestions.append(Suggestion(
        gap_id=18,
        gap_title="Phonological geometry through connector (full close)",
        experiment_name="Real-Model DAS Encoder→Connector→LLM Transfer",
        design="Phase 1 of Paper A: train DAS on Whisper-small encoder layers for "
               "voicing variable using pyvene. Then test subspace transfer through "
               "connector to LLM layer 0 using NNsight hooks. Full gc(k) curve.",
        stimuli="Choi et al. minimal pairs (~200 voicing contrasts) + TTS augmentation",
        metric="gc(k) curve across encoder + LLM layers; IIA_transfer ratio",
        expected_outcome="gc peak at encoder L5-7; IIA_transfer > 0.3 at LLM L0 "
                         "(geometry partially survives connector)",
        compute="cpu",
        est_time="~2h on MacBook (Whisper-small via pyvene)",
        risk="medium",
        risk_score=2.0,
        impact=9.0,
        feasibility=7.0,
        paper_section="Paper A Figure 2 + §4.1",
        cross_gaps=[14, 26],
        track="T3",
    ))

    # Gap #23 full → real Audio-RAVEL
    suggestions.append(Suggestion(
        gap_id=23,
        gap_title="Audio-RAVEL on real Whisper (full close)",
        experiment_name="Audio-RAVEL with Real Minimal Pairs",
        design="Apply RAVEL Cause+Isolate framework to Whisper encoder using real "
               "phonological minimal pair audio. Train MDAS for voicing + manner + "
               "place + speaker simultaneously. Compare SAE vs DAS vs PCA baselines.",
        stimuli="Choi et al. phonological minimal pairs + TTS speaker augmentation "
                "(4 attributes × ~200 pairs each)",
        metric="Cause(F,A) + Isolate(F,A) per attribute; RAVEL harmonic mean; "
               "SAE vs MDAS comparison",
        expected_outcome="MDAS best on Isolate; SAE good on Cause but leaks on Isolate "
                         "(confirming text polysemanticity finding from Q123)",
        compute="cpu",
        est_time="~4h (pyvene DAS + Whisper-small)",
        risk="medium",
        risk_score=2.0,
        impact=9.0,
        feasibility=6.0,
        paper_section="Paper B §4 Category 0 (flagship contribution)",
        cross_gaps=[18],
        track="T2",
    ))

    # Gap #21 full → real causal patching
    suggestions.append(Suggestion(
        gap_id=21,
        gap_title="Codec RVQ causal patching in LALM (full close)",
        experiment_name="RVQ-Selective Causal Patching in Qwen2-Audio",
        design="Corrupt individual RVQ layers (1-8) of codec tokens during LALM "
               "inference. Measure output degradation per RVQ layer. Validate that "
               "Layer 1 (semantic) corruption → meaning change; Layers 2+ (acoustic) "
               "corruption → style change only.",
        stimuli="SpeechTokenizer-encoded utterances with known content + speaker labels",
        metric="WER delta (semantic) + speaker ID delta (acoustic) per RVQ layer; "
               "gc(RVQ_k) = DAS-IIA per codec layer",
        expected_outcome="RVQ-1 corruption → high WER delta, low speaker delta; "
                         "RVQ-4+ → low WER delta, high speaker delta (clean dissociation)",
        compute="gpu",
        est_time="~4h on NDIF (Qwen2-Audio-7B)",
        risk="medium",
        risk_score=2.0,
        impact=8.0,
        feasibility=5.0,
        paper_section="Paper A §5.3 + Paper B Cat 1",
        cross_gaps=[],
        track="T3",
    ))

    # Gap #24 full → real SAE jailbreak
    suggestions.append(Suggestion(
        gap_id=24,
        gap_title="SAE jailbreak feature attribution (full close)",
        experiment_name="AudioSAE Decomposition of SPIRIT Noise-Sensitive Neurons",
        design="Apply AudioSAE to Qwen2-Audio; decompose SPIRIT's noise-sensitive "
               "neurons into monosemantic features. Test whether jailbreak corrupts "
               "gc≈1 (audio-grounded) or gc≈0 (text-predicted) features.",
        stimuli="SPIRIT AdvBench 246 adversarial audio samples + clean counterparts",
        metric="Feature-level gc for noise-sensitive neurons; attack success rate "
               "after SAE-guided surgical patching",
        expected_outcome="Jailbreak primarily corrupts gc≈0 (text-predicted) features; "
                         "SAE-guided patching = more surgical than SPIRIT's blind approach",
        compute="gpu",
        est_time="~6h (AudioSAE + Qwen2-Audio via NDIF)",
        risk="high",
        risk_score=2.5,
        impact=7.5,
        feasibility=4.0,
        paper_section="Paper B §4 Cat 4 (safety) + SPIRIT comparison",
        cross_gaps=[20],
        track="T5",
    ))

    # Gap #26 — DAS on real speech LLM (core Paper A experiment)
    suggestions.append(Suggestion(
        gap_id=26,
        gap_title="Speech LLM causal subspaces via DAS",
        experiment_name="Full gc(k) Sweep on Whisper-small (Paper A Phase 1)",
        design="Train DAS rotation at each of Whisper-small's 12 encoder layers + "
               "4 decoder layers for voicing variable. Produce gc(k) curve. "
               "Test decomposability ablation at L* (voicing ⊥ phoneme-identity).",
        stimuli="Choi et al. voicing minimal pairs (~250 base/source pairs)",
        metric="gc(k) = DAS-IIA per layer; decomposability = cos(R_voicing, R_phoneme)",
        expected_outcome="gc peak at encoder L5-7 (consistent with Q001 cos_sim peak); "
                         "decomposability near 0 (abstract phonological encoding)",
        compute="cpu",
        est_time="~30 min per layer, ~6h total on MacBook",
        risk="low",
        risk_score=1.5,
        impact=10.0,
        feasibility=7.0,
        paper_section="Paper A §5 (main result), Figure 1",
        cross_gaps=[14, 18],
        track="T3",
    ))

    # --- Cross-gap experiment: one experiment validates multiple gaps ---
    suggestions.append(Suggestion(
        gap_id=11,
        gap_title="Cross-gap: neuron grounding + emotion + safety",
        experiment_name="AAPE-gc Neuron Taxonomy (Kawamura × Zhao × SPIRIT)",
        design="Apply AAPE (Kawamura) to find class-specific neurons in Qwen2-Audio. "
               "Compute gc per neuron (audio vs text activation source). Cross-reference "
               "with Zhao ESN emotions + SPIRIT noise-sensitivity. Single experiment "
               "closes 3 gaps.",
        stimuli="VoxCeleb1 (gender/speaker) + IEMOCAP (emotion) + AdvBench (safety)",
        metric="gc(neuron) distribution; ESN overlap with noise-sensitive neurons; "
               "emotion-neuron gc (expect ≈0 per Q118)",
        expected_outcome="Emotion neurons gc≈0 (text-predicted), speaker neurons gc≈1 "
                         "(audio-grounded), safety neurons mixed → taxonomy complete",
        compute="gpu",
        est_time="~8h on NDIF",
        risk="high",
        risk_score=2.5,
        impact=8.0,
        feasibility=4.0,
        paper_section="Paper A §6 + Paper B Cat 5 (cross-modal attribution)",
        cross_gaps=[20, 24],
        track="T3",
    ))

    return suggestions


# ---------------------------------------------------------------------------
# Filtering and ranking
# ---------------------------------------------------------------------------

def filter_suggestions(
    suggestions: list[Suggestion],
    track: Optional[str] = None,
    budget: Optional[str] = None,
) -> list[Suggestion]:
    """Filter by track and/or compute budget."""
    filtered = suggestions
    if track:
        filtered = [s for s in filtered if s.track == track]
    if budget:
        filtered = [s for s in filtered if s.compute == budget]
    return filtered


def rank_suggestions(suggestions: list[Suggestion]) -> list[Suggestion]:
    """Rank by score = impact × feasibility / risk."""
    return sorted(suggestions, key=lambda s: s.score, reverse=True)


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_suggestions(suggestions: list[Suggestion], top_n: int = 10) -> None:
    """Pretty-print ranked suggestions."""
    print("=" * 78)
    print("  EXPERIMENT DESIGN ASSISTANT — Gap-Aware Recommendations")
    print("=" * 78)
    print()

    for i, s in enumerate(suggestions[:top_n], 1):
        cross = f" + Gaps {s.cross_gaps}" if s.cross_gaps else ""
        print(f"{'─' * 78}")
        print(f"  #{i}  Gap #{s.gap_id}: {s.gap_title}")
        print(f"{'─' * 78}")
        print(f"  Experiment : {s.experiment_name}")
        print(f"  Track      : {s.track}")
        print(f"  Score      : {s.score:.1f}  "
              f"(impact={s.impact}, feasibility={s.feasibility}, "
              f"risk={s.risk} [{s.risk_score}])")
        print(f"  Cross-gaps : {cross or 'none'}")
        print(f"  Paper      : {s.paper_section}")
        print()
        print(f"  Design:")
        for line in _wrap(s.design, 68):
            print(f"    {line}")
        print(f"  Stimuli    : {s.stimuli}")
        print(f"  Metric     : {s.metric}")
        print(f"  Expected   : {s.expected_outcome}")
        print(f"  Compute    : {s.compute.upper()} — {s.est_time}")
        print()

    # Summary stats
    print("=" * 78)
    print("  SUMMARY")
    print("=" * 78)
    shown = suggestions[:top_n]
    cpu_count = sum(1 for s in shown if s.compute == "cpu")
    gpu_count = sum(1 for s in shown if s.compute == "gpu")
    unique_gaps = len({s.gap_id for s in shown})
    cross_count = sum(1 for s in shown if s.cross_gaps)
    avg_score = sum(s.score for s in shown) / len(shown) if shown else 0
    print(f"  Showing {len(shown)}/{len(suggestions)} suggestions")
    print(f"  Unique gaps covered  : {unique_gaps}")
    print(f"  Cross-gap experiments: {cross_count}")
    print(f"  CPU / GPU split      : {cpu_count} / {gpu_count}")
    print(f"  Avg score            : {avg_score:.1f}")
    print(f"  Top score            : {shown[0].score:.1f}" if shown else "")
    print()


def _wrap(text: str, width: int) -> list[str]:
    """Simple word-wrap."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for w in words:
        if len(current) + len(w) + 1 > width:
            lines.append(current)
            current = w
        else:
            current = f"{current} {w}" if current else w
    if current:
        lines.append(current)
    return lines


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Experiment Design Assistant — gap-aware recommendations"
    )
    parser.add_argument(
        "--track", choices=["T1", "T2", "T3", "T4", "T5"],
        help="Filter by research track"
    )
    parser.add_argument(
        "--budget", choices=["cpu", "gpu"],
        help="Filter by compute requirement"
    )
    parser.add_argument(
        "--top", type=int, default=10,
        help="Number of recommendations to show (default: 10)"
    )
    args = parser.parse_args()

    # Load data
    results = load_experiment_results()
    queue = load_queue()
    gaps = build_gap_registry()

    # Generate, filter, rank
    suggestions = generate_suggestions(gaps, results, queue)
    suggestions = filter_suggestions(suggestions, track=args.track, budget=args.budget)
    suggestions = rank_suggestions(suggestions)

    if not suggestions:
        print(f"No suggestions match filters (track={args.track}, budget={args.budget})")
        sys.exit(0)

    print_suggestions(suggestions, top_n=args.top)


if __name__ == "__main__":
    main()
