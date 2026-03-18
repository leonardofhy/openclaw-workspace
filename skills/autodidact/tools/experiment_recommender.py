#!/usr/bin/env python3
"""Experiment Recommender — score and rank next highest-value experiments.

Reads current state (completed experiments, blocked tasks, knowledge gaps,
research tracks) and recommends the top-N highest-value next experiments
using a multi-factor scoring algorithm.

Scoring dimensions (each 0–1, weighted):
  novelty       (0.20) — tests something no existing experiment covers
  feasibility   (0.25) — CPU-only > GPU-required > needs external data
  impact        (0.25) — directly supports Paper A claims
  convergence   (0.15) — connects multiple existing results
  gap_coverage  (0.15) — addresses an open gap in knowledge-graph.md

Usage:
    python3 experiment_recommender.py              # ranked ASCII table
    python3 experiment_recommender.py --json       # JSON output
    python3 experiment_recommender.py --add 3      # add top 3 to queue.json
    python3 experiment_recommender.py --top 5      # show top 5 (default 10)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "shared"))
from jsonl_store import find_workspace

WS = find_workspace()
LEARNING = WS / "memory" / "learning"

TZ = timezone(timedelta(hours=8))

# ---------------------------------------------------------------------------
# Weights
# ---------------------------------------------------------------------------

WEIGHTS = {
    "novelty": 0.20,
    "feasibility": 0.25,
    "impact": 0.25,
    "convergence": 0.15,
    "gap_coverage": 0.15,
}

# ---------------------------------------------------------------------------
# Load current state
# ---------------------------------------------------------------------------


def load_completed_experiments() -> dict[str, dict]:
    """Import RESULTS from unified_results_dashboard.py by parsing the dict."""
    dashboard = WS / "skills" / "autodidact" / "scripts" / "unified_results_dashboard.py"
    if not dashboard.exists():
        return {}
    code = dashboard.read_text()
    # Extract just the RESULTS dict assignment (up to first function def)
    cut = code.find("\ndef ")
    if cut > 0:
        code = code[:cut]
    ns: dict = {}
    try:
        compiled = compile(code, str(dashboard), "exec")
        eval_ns = {"__builtins__": __builtins__}
        # numpy may not be available; stub it
        try:
            import numpy
            eval_ns["np"] = numpy
        except ImportError:
            pass
        exec(compiled, eval_ns)  # noqa: S102
        return eval_ns.get("RESULTS", {})
    except Exception:
        return {}


def load_queue() -> dict:
    qpath = LEARNING / "state" / "queue.json"
    try:
        return json.loads(qpath.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"tasks": []}


def load_knowledge_gaps() -> list[dict]:
    """Extract Gap #N entries from knowledge-graph.md."""
    kg_path = LEARNING / "knowledge-graph.md"
    if not kg_path.exists():
        return []
    text = kg_path.read_text()
    gaps: list[dict] = []
    for m in re.finditer(r"Gap #(\d+)[^:]*:?\s*(.+?)(?=\n\n|\nGap #|\n###|\Z)", text, re.DOTALL):
        gap_num = int(m.group(1))
        desc = m.group(2).strip().split("\n")[0][:200]
        status = "open"
        if "PARTIALLY ADDRESSED" in m.group(0):
            status = "partial"
        elif "CLOSED" in m.group(0) or "✅" in m.group(0):
            status = "closed"
        gaps.append({"id": gap_num, "description": desc, "status": status})
    # Deduplicate by gap id (keep first)
    seen: set[int] = set()
    unique: list[dict] = []
    for g in gaps:
        if g["id"] not in seen:
            seen.add(g["id"])
            unique.append(g)
    return unique


def load_tracks() -> list[str]:
    """Extract track names from goals.md."""
    goals = LEARNING / "goals.md"
    if not goals.exists():
        return []
    text = goals.read_text()
    tracks: list[str] = []
    for m in re.finditer(r"###\s+Track\s+(\d+)[：:]\s*(.+)", text):
        tracks.append(f"T{m.group(1)}: {m.group(2).strip()}")
    return tracks


# ---------------------------------------------------------------------------
# Candidate experiments
# ---------------------------------------------------------------------------

@dataclass
class Candidate:
    name: str
    description: str
    tier: int  # 0=mock/CPU, 1=CPU+real-model, 2=GPU/external
    builds_on: list[str] = field(default_factory=list)   # Q-IDs
    paper_section: str = ""
    gaps_addressed: list[int] = field(default_factory=list)
    tracks: list[str] = field(default_factory=list)
    feasibility_class: str = "cpu"  # cpu | gpu | external
    # Scores (filled by scoring)
    scores: dict[str, float] = field(default_factory=dict)
    total: float = 0.0


def generate_candidates(completed: dict[str, dict], gaps: list[dict], queue: dict) -> list[Candidate]:
    """Generate candidate experiments based on current state analysis."""

    completed_ids = set(completed.keys())
    open_gaps = {g["id"] for g in gaps if g["status"] != "closed"}
    blocked_ids = {t["id"] for t in queue.get("tasks", []) if t.get("status") == "blocked"}

    candidates: list[Candidate] = []

    # --- 1. Cross-model validation: same experiment on Whisper-small ---
    candidates.append(Candidate(
        name="Cross-Model AND/OR gc Patching (Whisper-small)",
        description="Replicate Q091 AND/OR gc patching on Whisper-small (real model) "
                    "to validate that the r=0.984 mock correlation holds on a real encoder.",
        tier=1,
        builds_on=["Q091"],
        paper_section="Paper A §4 (Validation)",
        gaps_addressed=[g for g in [18] if g in open_gaps],
        tracks=["T3"],
        feasibility_class="cpu",
    ))

    # --- 2. Ablation: remove AND-gate constraint ---
    candidates.append(Candidate(
        name="AND-Gate Ablation Study",
        description="Test gc framework WITHOUT the AND-gate constraint — replace AND/OR "
                    "classification with continuous activation magnitude. Does gc(k) "
                    "still predict grounding? Ablation of core theoretical assumption.",
        tier=0,
        builds_on=["Q091", "Q096", "Q113"],
        paper_section="Paper A §5 (Ablation)",
        gaps_addressed=[],
        tracks=["T3"],
        feasibility_class="cpu",
    ))

    # --- 3. Failure mode analysis ---
    candidates.append(Candidate(
        name="gc Framework Failure Mode Analysis",
        description="Systematically test when gc framework breaks: adversarial inputs, "
                    "OOD audio, multilingual stimuli, codec artifacts. Identify boundary "
                    "conditions for Paper A's claims.",
        tier=0,
        builds_on=["Q091", "Q093", "Q116"],
        paper_section="Paper A §6 (Limitations)",
        gaps_addressed=[],
        tracks=["T3"],
        feasibility_class="cpu",
    ))

    # --- 4. Statistical significance on mock results ---
    candidates.append(Candidate(
        name="Bootstrap Confidence Intervals for Mock Correlations",
        description="Run bootstrap resampling on all mock experiments with r-values "
                    "(Q091, Q096, Q105, Q107, Q124, Q128) to compute 95% CIs. "
                    "Report which correlations are robust vs fragile.",
        tier=0,
        builds_on=["Q091", "Q096", "Q105", "Q107", "Q124", "Q128"],
        paper_section="Paper A §4 (Statistical robustness)",
        gaps_addressed=[],
        tracks=["T3"],
        feasibility_class="cpu",
    ))

    # --- 5. Real Whisper encoder lens + CKA triple convergence ---
    candidates.append(Candidate(
        name="Triple Convergence Causal Test (Whisper-small)",
        description="Run encoder-lens + CKA + denoising patching on Whisper-small with "
                    "real speech minimal pairs. Test if all three metrics converge at "
                    "the same layer (~50% depth).",
        tier=1,
        builds_on=["Q001", "Q002"],
        paper_section="Paper A §3 (Experiment 1)",
        gaps_addressed=[g for g in [18] if g in open_gaps],
        tracks=["T3", "T1"],
        feasibility_class="cpu",
    ))

    # --- 6. RAVEL on real Whisper-small (Audio-RAVEL) ---
    candidates.append(Candidate(
        name="Audio-RAVEL on Whisper-small",
        description="Port RAVEL Cause/Isolate metrics to real Whisper-small encoder. "
                    "Test phoneme/speaker disentanglement with interchange interventions "
                    "on LibriSpeech minimal pairs.",
        tier=1,
        builds_on=["Q095", "Q105", "Q107"],
        paper_section="Paper B §3 (AudioSAEBench Cat 0)",
        gaps_addressed=[g for g in [23] if g in open_gaps],
        tracks=["T2", "T3"],
        feasibility_class="cpu",
    ))

    # --- 7. Phonological geometry through connector ---
    candidates.append(Candidate(
        name="Phonological Geometry Connector Test",
        description="Test if Choi et al.'s phonological vector arithmetic survives "
                    "through the audio-LLM connector. Extract voicing vectors from "
                    "Whisper encoder, project via connector, test linearity in LLM space.",
        tier=2,
        builds_on=["Q001", "Q109"],
        paper_section="Paper A §3.2 (Connector analysis)",
        gaps_addressed=[g for g in [18] if g in open_gaps],
        tracks=["T3"],
        feasibility_class="gpu",
    ))

    # --- 8. GSAE density refinement (unblock Q117) ---
    if "Q117" in blocked_ids or "Q117" in completed_ids:
        candidates.append(Candidate(
            name="GSAE Density Metric Refinement",
            description="Redesign GSAE graph density metric to fix weak correlation "
                        "(r=-0.043). Try normalized Laplacian spectral gap, weighted "
                        "edge density, or community-detection-based metrics.",
            tier=0,
            builds_on=["Q117", "Q113", "Q120"],
            paper_section="Paper A §4 (GCBench metric #9)",
            gaps_addressed=[],
            tracks=["T3"],
            feasibility_class="cpu",
        ))

    # --- 9. FAD-RAVEL proxy fix (unblock Q123) ---
    if "Q123" in blocked_ids or "Q123" in completed_ids:
        candidates.append(Candidate(
            name="FAD-RAVEL Proxy Redesign",
            description="Fix Q123's wrong-direction correlation (r=-0.70). Replace "
                        "FAD bias proxy with direct text-predictability score from "
                        "language model perplexity. Rerun Cause/Isolate.",
            tier=0,
            builds_on=["Q123", "Q096", "Q109"],
            paper_section="Paper A §4 (FAD entanglement)",
            gaps_addressed=[],
            tracks=["T3"],
            feasibility_class="cpu",
        ))

    # --- 10. Jailbreak SAE feature attribution ---
    candidates.append(Candidate(
        name="SAE-Guided Jailbreak Feature Attribution",
        description="Decompose SPIRIT's noise-sensitive neurons into SAE features. "
                    "Test which features carry adversarial signal: audio-grounded (gc~1) "
                    "or text-predicted (gc~0)? Mock first, then real with AudioSAE.",
        tier=0,
        builds_on=["Q128", "Q094", "Q106"],
        paper_section="Paper C (Safety) + Paper B Cat4",
        gaps_addressed=[g for g in [24] if g in open_gaps],
        tracks=["T5", "T2"],
        feasibility_class="cpu",
    ))

    # --- 11. Temporal SAE for audio (T-SAE transfer) ---
    candidates.append(Candidate(
        name="Audio T-SAE Temporal Coherence Pilot",
        description="Train T-SAE on Whisper-small layer 3-5 activations (LibriSpeech). "
                    "Test if high-level features segment at phoneme boundaries. Compare "
                    "TCS(F) metric against standard SAE baseline.",
        tier=1,
        builds_on=["Q094b", "Q125"],
        paper_section="Paper B §3 (AudioSAEBench novel metric)",
        gaps_addressed=[g for g in [12] if g in open_gaps],
        tracks=["T2"],
        feasibility_class="cpu",
    ))

    # --- 12. Emotion x grounding coefficient ---
    candidates.append(Candidate(
        name="ESN Grounding Coefficient (Emotion Neurons x gc)",
        description="Apply gc metric to Zhao et al.'s emotion-sensitive neurons. "
                    "For each ESN cluster, patch audio vs text to measure whether "
                    "emotion neurons are audio-grounded or text-predicted.",
        tier=2,
        builds_on=["Q118", "Q121"],
        paper_section="Paper A §5 (Extension to emotion)",
        gaps_addressed=[g for g in [11, 13] if g in open_gaps],
        tracks=["T3", "T5"],
        feasibility_class="gpu",
    ))

    # --- 13. Cascade degree multi-model comparison ---
    candidates.append(Candidate(
        name="Cascade Degree Across Model Sizes",
        description="Run cascade_degree = 1-AND% on Whisper-tiny, base, small, medium. "
                    "Test if cascade onset layer scales with model depth (~50% for all).",
        tier=1,
        builds_on=["Q113", "Q091"],
        paper_section="Paper A §4 (Scaling)",
        gaps_addressed=[],
        tracks=["T3"],
        feasibility_class="cpu",
    ))

    # --- 14. Real ALME conflict patching (GPU) ---
    candidates.append(Candidate(
        name="ALME Conflict Patching on Qwen2-Audio",
        description="Run denoising activation patching on Qwen2-Audio with ALME 57K "
                    "conflict stimuli. Localize the Listen Layer. THE core experiment "
                    "of Paper A — requires GPU access.",
        tier=2,
        builds_on=["Q001", "Q002", "Q091"],
        paper_section="Paper A §3 (Core experiment)",
        gaps_addressed=[g for g in [16] if g in open_gaps],
        tracks=["T3"],
        feasibility_class="gpu",
    ))

    # --- 15. Codec RVQ causal patching (real model) ---
    candidates.append(Candidate(
        name="Real Codec RVQ Layer Patching",
        description="Causally patch individual RVQ layers in LALM inference to test "
                    "Q124's prediction (RVQ-1=semantic/OR, RVQ-2+=acoustic/AND). "
                    "Requires GPU for full LALM.",
        tier=2,
        builds_on=["Q124", "Q126"],
        paper_section="Paper A §3.3 (Codec analysis)",
        gaps_addressed=[g for g in [21] if g in open_gaps],
        tracks=["T3", "T1"],
        feasibility_class="gpu",
    ))

    # --- 16. Multi-attribute RAVEL matrix ---
    candidates.append(Candidate(
        name="RAVEL Multi-Attribute Disentanglement Matrix",
        description="Extend Q095 MicroGPT RAVEL to full attribute matrix: "
                    "phoneme x speaker x emotion x accent. Build the complete "
                    "Cause/Isolate heatmap for AudioSAEBench.",
        tier=0,
        builds_on=["Q095", "Q105", "Q118"],
        paper_section="Paper B §3 (Cat 0 full matrix)",
        gaps_addressed=[g for g in [23] if g in open_gaps],
        tracks=["T2"],
        feasibility_class="cpu",
    ))

    # --- 17. Power steering dose-response curve ---
    candidates.append(Candidate(
        name="Steering Dose-Response Curve (gc x alpha)",
        description="Systematically vary steering gain alpha for features at different gc "
                    "levels. Test prediction: high-gc features need less alpha to steer "
                    "audio behavior; low-gc features are unsteerable for audio.",
        tier=0,
        builds_on=["Q127", "Q091"],
        paper_section="Paper B §3 (Cat 4 controllability)",
        gaps_addressed=[],
        tracks=["T2", "T3"],
        feasibility_class="cpu",
    ))

    # --- 18. Modality collapse detection benchmark ---
    candidates.append(Candidate(
        name="Modality Collapse Detection Benchmark",
        description="Build standardized test for detecting when LALMs fall back from "
                    "listening to guessing. Combine gc(k) + cascade_degree + t* onset "
                    "into a single collapse score. Validate on known failure modes.",
        tier=0,
        builds_on=["Q093", "Q113", "Q093b"],
        paper_section="Paper A §5 (Practical application)",
        gaps_addressed=[g for g in [14, 15] if g in open_gaps],
        tracks=["T3"],
        feasibility_class="cpu",
    ))

    # --- 19. Accent/language gc variation ---
    candidates.append(Candidate(
        name="Cross-Lingual gc Variation Study",
        description="Test gc framework on non-English stimuli (Mandarin, Japanese). "
                    "Do tonal languages show different gc profiles? Uses synthetic "
                    "mock data with language-specific phonological structure.",
        tier=0,
        builds_on=["Q091", "Q109"],
        paper_section="Paper A §5 (Generalization)",
        gaps_addressed=[],
        tracks=["T3", "T1"],
        feasibility_class="cpu",
    ))

    # --- 20. Incrimination to circuit graph automation ---
    candidates.append(Candidate(
        name="Automated Circuit Graph from Incrimination",
        description="Use Q094+Q122 incrimination data to automatically construct "
                    "a circuit graph (nodes=SAE features, edges=blame links). "
                    "Test if graph structure predicts gc(k) values.",
        tier=0,
        builds_on=["Q094", "Q122", "Q127"],
        paper_section="Paper A §4 (Circuit discovery)",
        gaps_addressed=[],
        tracks=["T3", "T2"],
        feasibility_class="cpu",
    ))

    return candidates


# ---------------------------------------------------------------------------
# Scoring algorithm
# ---------------------------------------------------------------------------

def score_candidates(
    candidates: list[Candidate],
    completed: dict[str, dict],
    gaps: list[dict],
    queue: dict,
) -> list[Candidate]:
    """Score each candidate on 5 dimensions and compute weighted total."""

    completed_names = {r["name"].lower() for r in completed.values()}
    completed_ids = set(completed.keys())
    open_gap_ids = {g["id"] for g in gaps if g["status"] != "closed"}
    partial_gap_ids = {g["id"] for g in gaps if g["status"] == "partial"}

    # Experiments with high correlations (strong results to build on)
    strong_results = {
        qid for qid, r in completed.items()
        if r.get("correlation") is not None and abs(r["correlation"]) > 0.8
    }

    for c in candidates:
        # --- Novelty (0-1): does it test something new? ---
        name_words = set(c.name.lower().split())
        overlap = sum(1 for n in completed_names if len(name_words & set(n.split())) >= 3)
        c.scores["novelty"] = max(0.0, 1.0 - overlap * 0.3)

        # --- Feasibility (0-1): cpu=1.0, gpu=0.5, external=0.3 ---
        feas_map = {"cpu": 1.0, "gpu": 0.5, "external": 0.3}
        tier_penalty = c.tier * 0.1  # tier 0=0, tier 1=0.1, tier 2=0.2
        c.scores["feasibility"] = max(0.0, feas_map.get(c.feasibility_class, 0.3) - tier_penalty)

        # --- Impact (0-1): supports Paper A directly? ---
        paper_a = 1.0 if "Paper A" in c.paper_section else 0.0
        paper_b = 0.6 if "Paper B" in c.paper_section else 0.0
        paper_c = 0.4 if "Paper C" in c.paper_section else 0.0
        t3_bonus = 0.2 if "T3" in c.tracks else 0.0
        c.scores["impact"] = min(1.0, max(paper_a, paper_b, paper_c) + t3_bonus)

        # --- Convergence (0-1): connects multiple strong results ---
        strong_links = sum(1 for qid in c.builds_on if qid in strong_results)
        total_links = len(c.builds_on)
        c.scores["convergence"] = min(1.0, (strong_links * 0.3) + (total_links * 0.1))

        # --- Gap coverage (0-1): addresses open/partial gaps ---
        open_covered = sum(1 for g in c.gaps_addressed if g in open_gap_ids)
        partial_covered = sum(1 for g in c.gaps_addressed if g in partial_gap_ids)
        c.scores["gap_coverage"] = min(1.0, open_covered * 0.5 + partial_covered * 0.3)

        # Weighted total
        c.total = sum(WEIGHTS[k] * c.scores[k] for k in WEIGHTS)

    # Sort descending by total score
    candidates.sort(key=lambda c: c.total, reverse=True)
    return candidates


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def _trunc(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def print_table(candidates: list[Candidate], top_n: int = 10) -> None:
    """Print ranked ASCII table."""
    shown = candidates[:top_n]
    hdr = (
        f"{'#':>2}  {'Name':<44} {'Tier':>4}  "
        f"{'Nov':>5} {'Feas':>5} {'Imp':>5} {'Conv':>5} {'Gap':>5}  {'TOTAL':>6}"
    )
    sep = "-" * len(hdr)
    print(f"\nExperiment Recommender -- Top {len(shown)} Candidates")
    print(f"   Weights: novelty={WEIGHTS['novelty']}, feasibility={WEIGHTS['feasibility']}, "
          f"impact={WEIGHTS['impact']}, convergence={WEIGHTS['convergence']}, "
          f"gap_coverage={WEIGHTS['gap_coverage']}")
    print(sep)
    print(hdr)
    print(sep)
    for i, c in enumerate(shown, 1):
        s = c.scores
        print(
            f"{i:>2}  {_trunc(c.name, 44):<44} T{c.tier:>3}  "
            f"{s.get('novelty', 0):>5.2f} {s.get('feasibility', 0):>5.2f} "
            f"{s.get('impact', 0):>5.2f} {s.get('convergence', 0):>5.2f} "
            f"{s.get('gap_coverage', 0):>5.2f}  {c.total:>6.3f}"
        )
    print(sep)

    # Detail section
    print(f"\nDetails")
    print(sep)
    for i, c in enumerate(shown, 1):
        builds = ", ".join(c.builds_on) if c.builds_on else "--"
        gaps_str = ", ".join(f"#{g}" for g in c.gaps_addressed) if c.gaps_addressed else "--"
        tracks_str = ", ".join(c.tracks) if c.tracks else "--"
        print(f"\n  {i}. {c.name} (Tier {c.tier}, score={c.total:.3f})")
        print(f"     {c.description}")
        print(f"     Builds on: {builds}")
        print(f"     Paper section: {c.paper_section}")
        print(f"     Gaps addressed: {gaps_str}")
        print(f"     Tracks: {tracks_str}")
    print()


def to_json(candidates: list[Candidate], top_n: int = 10) -> str:
    """Return JSON array of top candidates."""
    shown = candidates[:top_n]
    out = []
    for i, c in enumerate(shown, 1):
        out.append({
            "rank": i,
            "name": c.name,
            "description": c.description,
            "tier": c.tier,
            "feasibility_class": c.feasibility_class,
            "builds_on": c.builds_on,
            "paper_section": c.paper_section,
            "gaps_addressed": c.gaps_addressed,
            "tracks": c.tracks,
            "scores": c.scores,
            "total": round(c.total, 4),
        })
    return json.dumps(out, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Add to queue
# ---------------------------------------------------------------------------

def add_to_queue(candidates: list[Candidate], n: int) -> int:
    """Add top N candidates to queue.json. Returns count added."""
    qpath = LEARNING / "state" / "queue.json"
    try:
        data = json.loads(qpath.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"version": 1, "max_tasks": 25, "tasks": []}

    tasks = data.get("tasks", [])
    max_tasks = data.get("max_tasks", 25)

    # Find next Q-ID
    max_num = 0
    for t in tasks:
        tid = t.get("id", "")
        if tid.startswith("Q") and tid[1:].isdigit():
            max_num = max(max_num, int(tid[1:]))

    existing_titles = {t.get("title", "").lower() for t in tasks}

    added = 0
    now = datetime.now(TZ).strftime("%Y-%m-%d")

    for c in candidates[:n]:
        if len(tasks) >= max_tasks:
            print(f"  Queue full ({max_tasks} tasks). Cannot add more.")
            break
        # Skip if similar title already in queue
        if c.name.lower() in existing_titles:
            print(f"  Skipping '{c.name}' -- similar task already in queue")
            continue
        max_num += 1
        qid = f"Q{max_num:03d}"
        track = c.tracks[0] if c.tracks else "T3"
        task = {
            "id": qid,
            "type": "experiment",
            "track": track,
            "title": c.name,
            "status": "ready",
            "priority": max(1, 3 - c.tier),  # tier 0->3, tier 1->2, tier 2->1
            "blocked_by": None if c.feasibility_class == "cpu" else f"Requires {c.feasibility_class.upper()} access",
            "definition_of_done": c.description[:200],
            "created": now,
            "due": None,
        }
        if c.feasibility_class != "cpu":
            task["status"] = "blocked"
        tasks.append(task)
        added += 1
        print(f"  Added {qid}: {c.name} (Tier {c.tier}, {c.feasibility_class})")

    data["tasks"] = tasks
    data["last_updated"] = datetime.now(TZ).isoformat()

    # Atomic write
    tmp = str(qpath) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, str(qpath))

    return added


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recommend next highest-value experiments based on current research state."
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--add", type=int, metavar="N", help="Add top N to queue.json")
    parser.add_argument("--top", type=int, default=10, help="Number of candidates to show (default: 10)")
    args = parser.parse_args()

    # Load state
    completed = load_completed_experiments()
    queue = load_queue()
    gaps = load_knowledge_gaps()
    tracks = load_tracks()

    # Generate and score
    candidates = generate_candidates(completed, gaps, queue)
    candidates = score_candidates(candidates, completed, gaps, queue)

    # Output
    if args.json:
        print(to_json(candidates, args.top))
    else:
        print_table(candidates, args.top)

        # Summary stats
        print(f"State summary:")
        print(f"   Completed experiments: {len(completed)} ({sum(1 for r in completed.values() if r['mode'] == 'real')} real)")
        print(f"   Blocked tasks: {sum(1 for t in queue.get('tasks', []) if t.get('status') == 'blocked')}")
        print(f"   Open knowledge gaps: {sum(1 for g in gaps if g['status'] != 'closed')}")
        print(f"   Research tracks: {len(tracks)}")
        print()

    if args.add:
        print(f"\nAdding top {args.add} to queue.json...")
        n = add_to_queue(candidates, args.add)
        print(f"   Added {n} experiments to queue.")


if __name__ == "__main__":
    main()
