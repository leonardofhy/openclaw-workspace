# Backlog Scan List (when today's new scans are exhausted)

Last updated: 2026-02-28

## Recently Found (cycle #79, Feb 28)
- **MMA-Bench (2511.22826, Chen et al., Nov 2025)** — MLLMs + contradicting modalities; black-box + white-box interp; behavioral "modality alignment tuning". Vision domain, SCAN only. Motivates "modality prioritization" framing for Paper A pitch. NOT a competitor (no causal layer patching, vision not speech).
- **"When Tone and Words Disagree" (Jan 2026)** — SER acoustic-semantic conflict robustness study. Behavioral, no MI. SCAN only.

## Trigger condition
Use this list when:
- Today's arXiv new submissions are fully scanned, and
- No high-value immediate build task is available.

## Scan order (highest ROI first)

1) **Recent backlog (last 30 days)**
- arXiv cs.SD / cs.CL / cs.AI
- Queries:
  - "speech llm mechanistic interpretability"
  - "audio language model patching"
  - "audio text grounding llm"
  - "modality collapse speech"

2) **Near-history backlog (1–6 months)**
- Focus on papers cited by recent 2025–2026 speech-LALM interpretability papers
- Priority: methods that support causal localization (patching, interventions, attribution at layer/head level)

3) **Foundational backlog (pre-2025)**
- Causal abstraction / interchange intervention training lineage
- Transformer interpretability methods that can transfer to audio-LMs

## Inclusion criteria
Keep paper if it satisfies at least one:
- Gives causal method applicable to audio/speech LLMs
- Mentions audio-vs-text pathway / grounding behavior
- Introduces tools/benchmarks usable by Leo’s Track 3/4/5

## Skip criteria
Skip if mostly:
- Pure ASR benchmark with no interpretability/causal angle
- Music generation without transfer value to speech-LALM
- Duplicate of already-read ideas with no methodological novelty

## Output format per scan batch
For each batch, write:
- 1-line paper summary
- why relevant / why skipped
- potential gap link (if any)
- candidate experiment implication (if any)

Store notes in `memory/learning/YYYY-MM-DD_cycleNN.md` and summarize key keepers in `knowledge-graph.md`.
