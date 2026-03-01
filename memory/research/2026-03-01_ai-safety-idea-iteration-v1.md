# AI Safety × NLP/Speech — Idea Iteration v1 (2026-03-01)

## Focused themes from scout report
1. Audio jailbreak/compositional attack defenses are crowded on attacks, sparse on robust defenses.
2. Scalable oversight for speech agents is emerging (judge models, agent benchmarks), still weak on real-world multilingual/streaming settings.
3. Mechanistic interpretability for speech safety behavior is sparse and high-upside.

## Direction A (recommended): Safety-Critical Listen-Layer Audit
- Claim: Safety-relevant decisions in speech LLMs are concentrated in a small set of layers (listen-layer band), and this concentration predicts jailbreak susceptibility.
- Why now: connects your Paper A gc(k) work with safety; novelty is mechanism + safety bridge.
- 1-week MVP:
  - Build conflict-stimuli subset (benign vs harmful-like audio prompts)
  - Compute gc(k) profiles on safe/unsafe outcomes
  - Test whether peak shifts/attenuation correlate with attack success
- Expected output: mechanistic safety signal + small benchmark slice + ablation table.

## Direction B: Multilingual Compositional Guard Stress Test
- Claim: Audio-aware guards degrade sharply under multilingual + overlap + style-shift composition.
- Why now: attack papers are many, but adaptive multilingual defense evaluation is still sparse.
- 1-week MVP:
  - Select 2 languages + 2 accents + overlap/no-overlap conditions
  - Evaluate one guard pipeline + one baseline transcript-only guard
  - Report ASR drift, guard FP/FN, and attack success delta
- Expected output: practical defense gap map for real deployment.

## Decision (current)
- Primary: Direction A
- Secondary backup: Direction B

## Next actions
1. Convert Direction A into Idea Gate report (novelty/feasibility/value scores).
2. Define minimal dataset slice and metric table for 1-week MVP.
3. Produce “Paper A safety extension” one-page proposal.
