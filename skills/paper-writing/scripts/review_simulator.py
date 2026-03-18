#!/usr/bin/env python3
"""Paper Reviewer Simulator: simulates 3 peer reviewers for Paper A.

Generates structured review feedback with scores, strengths, weaknesses,
questions, and prioritized action items.

Usage:
    python3 skills/paper-writing/scripts/review_simulator.py
    python3 skills/paper-writing/scripts/review_simulator.py --draft docs/paper-a-draft.md
    python3 skills/paper-writing/scripts/review_simulator.py --output docs/simulated-review.md
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_DRAFT = Path("docs/paper-a-draft.md")
DEFAULT_OUTPUT = Path("docs/simulated-review.md")


@dataclass
class ReviewItem:
    text: str
    section: str = ""
    priority: str = "medium"  # high, medium, low


@dataclass
class Review:
    reviewer_name: str
    reviewer_role: str
    score: int
    summary: str
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    suggestions: list[ReviewItem] = field(default_factory=list)


@dataclass
class PaperStats:
    word_count: int = 0
    section_counts: dict[str, int] = field(default_factory=dict)
    todo_count: int = 0
    todo_locations: list[str] = field(default_factory=list)
    cite_placeholders: int = 0
    tables_count: int = 0
    figures_count: int = 0
    equations_count: int = 0
    real_experiments: int = 0
    mock_experiments: int = 0
    claims_count: int = 0
    sections: list[str] = field(default_factory=list)
    has_conclusion_content: bool = False
    notation_variants: dict[str, list[str]] = field(default_factory=dict)


def analyze_paper(text: str) -> PaperStats:
    """Extract structural statistics from the paper draft."""
    stats = PaperStats()
    stats.word_count = len(text.split())

    # Section word counts
    current_section = "preamble"
    section_text: dict[str, list[str]] = {}
    for line in text.splitlines():
        if line.startswith("# ") or line.startswith("## "):
            current_section = line.lstrip("#").strip()
            stats.sections.append(current_section)
        section_text.setdefault(current_section, []).append(line)
    stats.section_counts = {
        s: len(" ".join(lines).split()) for s, lines in section_text.items()
    }

    # TODOs
    for i, line in enumerate(text.splitlines(), 1):
        if "[TODO" in line:
            stats.todo_count += 1
            stats.todo_locations.append(f"Line {i}: {line.strip()[:80]}")

    # CITE placeholders
    stats.cite_placeholders = len(re.findall(r"\[CITE:", text))

    # Tables, figures, equations
    stats.tables_count = text.count("| Layer") + text.count("| Model") + text.count("| Codec") + text.count("| Condition") + text.count("| Degradation") + text.count("| Component") + text.count("| Prediction") + text.count("| Metric")
    stats.figures_count = len(re.findall(r"(?i)figure\s+\d+", text))
    stats.equations_count = len(re.findall(r"\$\$.*?\$\$", text, re.DOTALL))

    # Experiments
    stats.real_experiments = len(re.findall(r"\(Real\)", text))
    stats.mock_experiments = len(re.findall(r"\(Mock\)", text))

    # Claims
    stats.claims_count = len(re.findall(r"\*\*Claim \d+", text))

    # Conclusion completeness
    conclusion_section = section_text.get("§6 Conclusion", [])
    stats.has_conclusion_content = any(
        line.strip() and not line.startswith("[TODO") and not line.startswith("##")
        for line in conclusion_section
    )

    # Notation variants for gc
    gc_variants = set(re.findall(r"gc(?:\([^)]*\))?", text))
    stats.notation_variants["gc"] = sorted(gc_variants)

    return stats


def review_methodology(text: str, stats: PaperStats) -> Review:
    """Reviewer 1: Methodology Critic."""
    r = Review(
        reviewer_name="Reviewer 1",
        reviewer_role="Methodology Critic",
        score=5,
        summary=(
            "The paper proposes gc(k), a causal grounding coefficient for ALMs, "
            "embedded in a five-dimensional Listening Geometry framework. "
            "The theoretical contribution is clear, but the empirical validation "
            "is critically weak: only 2 real experiments on the smallest model scale, "
            "with the remaining 27 experiments using a mock framework."
        ),
    )

    # --- Strengths ---
    r.strengths = [
        "gc(k) is well-defined mathematically via DAS-IIA, with clear connection to causal abstraction theory (§3.1). The formalization is rigorous.",
        "The AND/OR gate framework (§3.2) provides a principled mechanistic decomposition of multimodal feature dependence, going beyond layer-level analysis.",
        "Pre-registered predictions (§4.8) are commendable and show intellectual honesty — few interpretability papers make falsifiable predictions about concurrent work.",
        "Honest reporting of blocked experiments Q117 and Q123 (§4.9) builds credibility.",
    ]

    # --- Weaknesses ---
    weaknesses = []

    # Mock vs real gap
    real = stats.real_experiments
    mock = stats.mock_experiments
    weaknesses.append(
        f"**Critical: Mock/Real experiment gap.** {mock} of {real + mock} experiments "
        f"use a mock framework (§4.3–4.7). Mock experiments validate internal consistency "
        f"of the formalism but cannot demonstrate that gc(k) captures real neural network "
        f"behavior. The two real experiments (Q001, Q002) use only Whisper-base (74M params). "
        f"This is acknowledged in §5.5 but not sufficiently mitigated — the paper reads as "
        f"a theoretical proposal masquerading as an empirical contribution."
    )

    # Baselines
    weaknesses.append(
        "**Baselines are insufficient.** The paper compares gc(k) conceptually to AudioLens "
        "and Beyond Transcription (§5.1) but never runs these methods on the same data for "
        "direct quantitative comparison. Without head-to-head baselines, the claim that gc(k) "
        "'subsumes and extends' prior metrics (§5.1) is unsupported."
    )

    # Statistical significance
    weaknesses.append(
        "**Statistical claims require scrutiny.** The r=0.98 correlation between AND% and gc(k) "
        "(§4.3) is from mock data where both quantities are generated by the same framework — "
        "this is a consistency check, not an empirical finding. The 96% suppression detection "
        "rate (§4.6) and other metrics from mock experiments should not be cited as validation "
        "of the framework's predictive power."
    )

    # Ablation studies
    weaknesses.append(
        "**Ablations are missing.** How sensitive is gc(k) to: (a) number of minimal pairs, "
        "(b) DAS rotation training set size, (c) choice of phonological contrast, "
        "(d) subspace dimensionality m? None of these ablations appear in the paper."
    )

    # TODO density
    if stats.todo_count > 10:
        weaknesses.append(
            f"**Paper is incomplete.** {stats.todo_count} [TODO] markers remain in the text, "
            f"including missing data in core results tables (§4.1, §4.2). Several key results "
            f"(real gc(k) sweep, RAVEL on real SAE features, Qwen2-Audio experiments) are "
            f"listed as 'awaiting GPU access.' This paper is not ready for review."
        )

    r.weaknesses = weaknesses

    # --- Questions ---
    r.questions = [
        "Why was Whisper-base chosen for the real experiments instead of Whisper-small, which is "
        "the stated 'primary analysis target' (§3.4.1)? Was this purely a compute constraint?",
        "The Q001 result shows weak voicing alignment (cos_sim = +0.25 for stop-stop at layer 5). "
        "Is this strong enough to support the claim that 'linearly structured phonological "
        "representations can serve as intervention targets'? What is the expected cos_sim for "
        "a reliable DAS intervention?",
        "How does gc(k) behave when the audio is completely uninformative (e.g., silence or "
        "white noise)? Is gc(k) = 0 at all layers in this case, or does it depend on text context?",
        "The mock framework is described only indirectly. Can you provide a concise formal "
        "specification of what the mock model computes? Without this, it is impossible to "
        "assess whether mock results generalize.",
        "In Q002, every single-layer ablation produces WER ≈ 1.0. Does this mean gc(k) will "
        "be uniformly high across all layers (since every layer is necessary), which would "
        "make the 'listen layer' concept vacuous for Whisper?",
    ]

    # --- Suggestions ---
    r.suggestions = [
        ReviewItem(
            "Run gc(k) sweep on Whisper-small with at least 500 minimal pairs and report "
            "the full curve with bootstrap CIs. This single experiment would transform the paper.",
            section="§4.3",
            priority="high",
        ),
        ReviewItem(
            "Add a baseline comparison: run AudioLens information score on the same stimuli "
            "and show where gc(k) and AudioLens agree/disagree. This would substantiate "
            "the 'causal upgrade' claim.",
            section="§5.1",
            priority="high",
        ),
        ReviewItem(
            "Provide an explicit formal definition of the mock framework in §3 or an appendix. "
            "Currently the reader must infer what mock experiments actually compute.",
            section="§3.3",
            priority="high",
        ),
        ReviewItem(
            "Report sensitivity of gc(k) to DAS subspace dimensionality m. Even a small "
            "sweep (m ∈ {1, 2, 4, 8, 16}) on Whisper-base would help.",
            section="§3.1",
            priority="medium",
        ),
        ReviewItem(
            "The H4 failure (§4.5, variance ratio = 0.073) deserves more discussion. "
            "If persona effects are small relative to within-condition variability, "
            "the safety implications (§5.3) are overstated.",
            section="§4.5 / §5.3",
            priority="medium",
        ),
    ]

    return r


def review_novelty(text: str, stats: PaperStats) -> Review:
    """Reviewer 2: Novelty Assessor."""
    r = Review(
        reviewer_name="Reviewer 2",
        reviewer_role="Novelty Assessor",
        score=6,
        summary=(
            "The paper introduces a principled causal framework (gc(k) + Listening Geometry) "
            "for understanding audio grounding in ALMs. The framing is novel and the theoretical "
            "connections are well-drawn. However, the core contribution — applying DAS to "
            "audio-language models — is a straightforward extension of existing text-domain "
            "methods (Geiger et al., 2021/2023; RAVEL) to a new modality. The AND/OR gate "
            "framework adds conceptual value but its empirical validation is entirely synthetic."
        ),
    )

    r.strengths = [
        "The gc(k) metric fills a genuine gap: no prior work provides causal, layer-wise "
        "audio grounding quantification for ALMs. The related work (§2) convincingly argues "
        "this gap exists across four independent research threads.",
        "The five-dimensional Listening Geometry and four-profile taxonomy (strong/shallow/"
        "fragile listener, sophisticated guesser) is a creative framing that could become "
        "a standard vocabulary for the field if validated.",
        "The cross-paper predictions (§5.4) for MPAR² and Modality Collapse are specific, "
        "falsifiable, and demonstrate the framework's generative power beyond the immediate "
        "experiments.",
        "Connecting AND/OR gates to safety implications (§5.3) — particularly the insight "
        "that jailbreaks operate by inducing gc suppression — is novel and practically relevant.",
        "The paper honestly positions itself relative to the closest methodological analog "
        "(FCCT for vision-LLMs, §2.2), making clear what is borrowed vs. new.",
    ]

    r.weaknesses = [
        "**Incremental methodology.** gc(k) = IIA_audio / (IIA_audio + IIA_text) is a "
        "straightforward ratio of DAS-IIA scores. The theoretical contribution is applying "
        "an existing causal framework (DAS/IIT) to a new domain (audio). This is valuable "
        "engineering but modest in terms of methodological novelty.",
        "**AND/OR gate results may be trivial.** The mock finding that 'all features at gc "
        "peak are AND-gates' (§4.4) is almost tautological: by definition, the layer with "
        "highest audio dependence should have features that require audio. The interesting "
        "question is what happens at *non-peak* layers, and this is unexplored.",
        "**Five dimensions, three validated.** The Listening Geometry claims five dimensions "
        "but defers two (CS, t*) to Paper B (§5.5). A framework paper that validates only "
        "60% of its proposed dimensions will face skepticism about the unvalidated parts.",
        "**No comparison to simpler alternatives.** Would a simple linear probe for 'audio "
        "content present' at each layer produce similar layer-wise profiles to gc(k)? "
        "Without ablating the complexity of DAS, it is unclear whether the full causal "
        "machinery is necessary to achieve the paper's stated goals.",
    ]

    r.questions = [
        "How does gc(k) differ from simply computing mutual information between layer-k "
        "representations and the audio input? What does the causal (interventional) "
        "perspective buy that an observational metric would not?",
        "The paper claims gc(k) provides both sufficiency and necessity evidence (Contribution 1). "
        "Can you clarify exactly which experiments test sufficiency vs. necessity? "
        "The DAS intervention appears to test only sufficiency (patching in source activations).",
        "Is the Listening Geometry truly five-dimensional, or are the dimensions highly "
        "correlated? The r=0.98 between α_AND and gc suggests they may be near-redundant.",
        "What would change in the framework if AND-gates were a continuum rather than a "
        "binary classification? The δ threshold makes the classification discrete — is "
        "there a continuous version?",
    ]

    r.suggestions = [
        ReviewItem(
            "Add a 'simple baseline' comparison: linear probe accuracy for audio content "
            "at each layer vs. gc(k). If they correlate highly, discuss what gc(k) adds "
            "beyond probing; if they diverge, highlight the cases.",
            section="§4 / §5.1",
            priority="high",
        ),
        ReviewItem(
            "Consider splitting the AND/OR gate results to show non-peak layers in detail. "
            "The transition zone (layers adjacent to k*) is where the interesting biology "
            "of multimodal integration happens.",
            section="§4.4",
            priority="medium",
        ),
        ReviewItem(
            "Either validate all five Listening Geometry dimensions in this paper, or "
            "rename the framework to reflect what is actually validated (e.g., 'Grounding "
            "Geometry' with three dimensions). Claiming five dimensions while delivering "
            "three invites rejection.",
            section="§3 / §5.5",
            priority="high",
        ),
        ReviewItem(
            "Strengthen the novelty narrative by emphasizing what is *surprising* in the "
            "results. The Q002 finding (every layer ablation → WER ≈ 1.0) is genuinely "
            "surprising and distinguishes audio from text models. Lead with this.",
            section="§4.2 / §1",
            priority="medium",
        ),
    ]

    return r


def review_clarity(text: str, stats: PaperStats) -> Review:
    """Reviewer 3: Clarity/Presentation."""
    r = Review(
        reviewer_name="Reviewer 3",
        reviewer_role="Clarity & Presentation",
        score=5,
        summary=(
            "The paper is ambitious in scope and well-structured at the outline level. "
            "However, the draft is clearly incomplete — numerous TODOs, missing data tables, "
            "and a placeholder conclusion undermine readability. The writing quality in "
            "completed sections is generally strong, but notation inconsistencies and an "
            "imbalanced section structure detract from clarity."
        ),
    )

    # Notation analysis
    gc_forms = stats.notation_variants.get("gc", [])

    r.strengths = [
        "The related work (§2) is comprehensive and well-organized into four clear threads, "
        "each ending with a 'Gap' statement that motivates the contribution. This is "
        "excellent scholarly writing.",
        "The progression from gc(k) definition (§3.1) to AND/OR gates (§3.2) to experimental "
        "protocol (§3.3) follows a logical build-up that a reader can follow.",
        "The abstract is dense but complete — it covers all five dimensions, key results, "
        "and applications in a single paragraph. At ~250 words it is appropriate for a "
        "top venue.",
        "Tables are used effectively for presenting results (when data is present). The "
        "intervention procedure (§3.3.2) is described step-by-step with admirable precision.",
    ]

    weaknesses = []

    # TODOs
    weaknesses.append(
        f"**{stats.todo_count} TODO markers remain.** These appear in critical locations "
        f"including results tables (§4.1, §4.2), threshold values (§3.2.1), dataset sizes "
        f"(§3.3.1, §3.4.2), and the entire conclusion (§6). The paper cannot be evaluated "
        f"in this state."
    )

    # Notation
    weaknesses.append(
        f"**Notation inconsistency for gc.** The following forms appear: {', '.join(gc_forms)}. "
        f"The paper uses gc, gc(k), gc(k*), gc(L), and related notation without a consistent "
        f"typographic convention. Suggestion: always use $gc(k)$ with italic 'gc' and "
        f"reserve gc without argument only when referring to the metric generically."
    )

    # Section balance
    method_words = sum(
        v for k, v in stats.section_counts.items()
        if "Method" in k or "3." in k or k.startswith("§3")
    )
    results_words = sum(
        v for k, v in stats.section_counts.items()
        if "Result" in k or "4." in k or k.startswith("§4")
    )
    discussion_words = sum(
        v for k, v in stats.section_counts.items()
        if "Discuss" in k or "5." in k or k.startswith("§5")
    )

    weaknesses.append(
        f"**Section imbalance.** Estimated word counts: Related Work §2 is very long "
        f"relative to Results §4. The related work exhaustively catalogs prior work but "
        f"could be tightened by 30–40% without losing essential context. Results §4 "
        f"is sparse due to missing data — once filled, rebalance."
    )

    # Conclusion
    if not stats.has_conclusion_content:
        weaknesses.append(
            "**Missing conclusion.** §6 contains only TODO placeholders. A paper without "
            "a conclusion is structurally incomplete. Even a draft conclusion summarizing "
            "the three validated dimensions would help reviewers."
        )

    # Figures
    if stats.figures_count < 2:
        weaknesses.append(
            f"**No figures.** The paper references no numbered figures. A gc(k) curve plot, "
            f"an AND/OR gate visualization, and a Listening Geometry profile comparison "
            f"are essential for reader comprehension. At minimum, add: (1) a schematic of "
            f"the intervention procedure, (2) a mock gc(k) curve with annotation, "
            f"(3) the four-profile taxonomy as a 2D plot."
        )

    r.weaknesses = weaknesses

    r.questions = [
        "The abstract mentions '29 experiments (2 real-model on Whisper, 27 mock-framework "
        "validation)' but the body text refers to '2 real experiments and 20 mock-framework "
        "experiments across 5 analysis axes' (§1, Contribution 4). Which count is correct?",
        "Is 'Schelling stability (σ)' defined anywhere in the paper? It appears in the "
        "abstract and §1 as a Listening Geometry dimension but I cannot find its definition "
        "in §3.",
        "The CITE placeholders (e.g., [CITE: Zhao 2602.23136]) — are these arXiv IDs? "
        "Please convert to standard citation format before submission.",
        "What is 'MicroGPT' (§4.7)? It appears in the RAVEL experiment but is never "
        "defined or cited.",
    ]

    r.suggestions = [
        ReviewItem(
            "Resolve all TODO markers before submission. Prioritize: (1) results data in "
            "§4.1 and §4.2 tables, (2) threshold values δ and ε in §3.2.1, "
            "(3) conclusion in §6.",
            section="Throughout",
            priority="high",
        ),
        ReviewItem(
            "Add at least 3 figures: (1) Intervention procedure schematic, "
            "(2) gc(k) curve example with annotated k*, (3) Four-profile taxonomy "
            "visualization. Consider also: AND/OR gate Venn diagram, mock vs real "
            "comparison plot.",
            section="§3–§4",
            priority="high",
        ),
        ReviewItem(
            "Standardize gc notation. Define a typographic convention in §3.1.2 and "
            "enforce it. Suggested: $\\mathrm{gc}(k)$ for the layer-indexed metric, "
            "$k^*$ for the listen layer, $\\alpha_{\\text{AND}}$ for AND-gate fraction.",
            section="§3.1.2",
            priority="medium",
        ),
        ReviewItem(
            "Tighten §2 Related Work by ~30%. Each subsection currently ends with a "
            "'Gap' statement — these are excellent, but the preceding paragraphs could "
            "be more concise. Consider merging §2.1 and §2.2 since both cover speech "
            "model interpretability.",
            section="§2",
            priority="medium",
        ),
        ReviewItem(
            "Reconcile experiment counts between abstract and body. Add a summary table "
            "listing all experiments (ID, type, model, status) as an appendix.",
            section="Abstract / §4",
            priority="low",
        ),
        ReviewItem(
            "Define Schelling stability (σ) in §3 or remove it from the abstract. "
            "Currently it appears without definition.",
            section="§3 / Abstract",
            priority="medium",
        ),
    ]

    return r


def format_review(review: Review) -> str:
    """Format a single review as markdown."""
    lines = [
        f"## {review.reviewer_name}: {review.reviewer_role}",
        "",
        f"**Overall Score: {review.score}/10**",
        "",
        f"**Summary:** {review.summary}",
        "",
        "### Strengths",
        "",
    ]
    for i, s in enumerate(review.strengths, 1):
        lines.append(f"{i}. {s}")
    lines.append("")
    lines.append("### Weaknesses")
    lines.append("")
    for i, w in enumerate(review.weaknesses, 1):
        lines.append(f"{i}. {w}")
    lines.append("")
    lines.append("### Questions for Authors")
    lines.append("")
    for i, q in enumerate(review.questions, 1):
        lines.append(f"Q{i}. {q}")
    lines.append("")
    lines.append("### Specific Suggestions")
    lines.append("")
    for i, s in enumerate(review.suggestions, 1):
        priority_tag = f"[{s.priority.upper()}]"
        section_tag = f"({s.section})" if s.section else ""
        lines.append(f"{i}. {priority_tag} {section_tag} {s.text}")
    lines.append("")
    return "\n".join(lines)


def generate_action_items(reviews: list[Review]) -> str:
    """Generate a combined, prioritized action items list."""
    items: list[tuple[str, str, str, str]] = []  # (priority, section, text, reviewer)

    for review in reviews:
        for s in review.suggestions:
            items.append((s.priority, s.section, s.text, review.reviewer_name))

    priority_order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda x: priority_order.get(x[0], 99))

    lines = [
        "## Combined Action Items (Prioritized)",
        "",
        "### P0: Must Fix Before Submission",
        "",
    ]

    current_priority = None
    item_num = 0
    for priority, section, text, reviewer in items:
        if priority != current_priority:
            current_priority = priority
            if priority == "medium":
                lines.append("")
                lines.append("### P1: Should Fix")
                lines.append("")
            elif priority == "low":
                lines.append("")
                lines.append("### P2: Nice to Have")
                lines.append("")
        item_num += 1
        section_tag = f" ({section})" if section else ""
        lines.append(f"{item_num}. **[{reviewer}]**{section_tag} {text}")

    return "\n".join(lines)


def generate_meta_analysis(stats: PaperStats, reviews: list[Review]) -> str:
    """Generate a meta-analysis section with paper statistics."""
    avg_score = sum(r.score for r in reviews) / len(reviews)
    lines = [
        "## Meta-Analysis",
        "",
        f"**Average Score: {avg_score:.1f}/10**",
        "",
        "### Paper Statistics",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Word count | {stats.word_count:,} |",
        f"| TODO markers | {stats.todo_count} |",
        f"| CITE placeholders | {stats.cite_placeholders} |",
        f"| Tables | {stats.tables_count} |",
        f"| Figures | {stats.figures_count} |",
        f"| Equations | {stats.equations_count} |",
        f"| Real experiments | {stats.real_experiments} |",
        f"| Mock experiments | {stats.mock_experiments} |",
        f"| Claims | {stats.claims_count} |",
        f"| Conclusion written | {'Yes' if stats.has_conclusion_content else 'No'} |",
        "",
        "### Submission Readiness Assessment",
        "",
    ]

    blockers = []
    if stats.todo_count > 5:
        blockers.append(f"{stats.todo_count} TODO markers remain in text")
    if not stats.has_conclusion_content:
        blockers.append("Conclusion section is empty")
    if stats.real_experiments < 3:
        blockers.append(
            f"Only {stats.real_experiments} real experiments "
            f"(vs. {stats.mock_experiments} mock)"
        )
    if stats.figures_count < 2:
        blockers.append("No numbered figures in the paper")

    if blockers:
        lines.append("**BLOCKERS (must resolve before submission):**")
        lines.append("")
        for b in blockers:
            lines.append(f"- {b}")
    else:
        lines.append("No critical blockers identified.")

    lines.append("")

    # Score interpretation
    lines.append("### Score Interpretation")
    lines.append("")
    if avg_score >= 7:
        lines.append("Scores suggest the paper is competitive for top venues with revisions.")
    elif avg_score >= 5:
        lines.append(
            "Scores suggest the paper has a strong conceptual core but requires "
            "substantial empirical strengthening before submission to a top venue. "
            "Consider targeting a workshop or completing the real experiments first."
        )
    else:
        lines.append("Scores suggest major revisions are needed.")

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate peer review for Paper A")
    parser.add_argument(
        "--draft",
        type=Path,
        default=DEFAULT_DRAFT,
        help=f"Path to paper draft (default: {DEFAULT_DRAFT})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output path (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    if not args.draft.exists():
        print(f"Error: draft not found at {args.draft}", file=sys.stderr)
        sys.exit(1)

    text = args.draft.read_text()
    print(f"Read {len(text):,} chars from {args.draft}")

    stats = analyze_paper(text)
    print(
        f"Paper stats: {stats.word_count:,} words, "
        f"{stats.todo_count} TODOs, "
        f"{stats.real_experiments} real + {stats.mock_experiments} mock experiments"
    )

    reviews = [
        review_methodology(text, stats),
        review_novelty(text, stats),
        review_clarity(text, stats),
    ]

    # Assemble output
    output_parts = [
        "# Simulated Peer Review: Paper A",
        "",
        '_"The Listening Geometry: Where Audio-Language Models Listen, Guess, and Collapse"_',
        "",
        f"Generated: deterministic review simulation",
        "",
        "---",
        "",
    ]

    for review in reviews:
        output_parts.append(format_review(review))
        output_parts.append("---")
        output_parts.append("")

    output_parts.append(generate_action_items(reviews))
    output_parts.append("")
    output_parts.append("---")
    output_parts.append("")
    output_parts.append(generate_meta_analysis(stats, reviews))

    output_text = "\n".join(output_parts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output_text)
    print(f"Review saved to {args.output}")

    # Print summary
    print("\n--- Review Summary ---")
    for review in reviews:
        print(f"  {review.reviewer_name} ({review.reviewer_role}): {review.score}/10")
    avg = sum(r.score for r in reviews) / len(reviews)
    print(f"  Average: {avg:.1f}/10")
    high_items = sum(
        1 for r in reviews for s in r.suggestions if s.priority == "high"
    )
    print(f"  High-priority action items: {high_items}")


if __name__ == "__main__":
    main()
