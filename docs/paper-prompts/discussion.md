# Task: Write §5 Discussion

You are a senior ML researcher helping write a paper on mechanistic interpretability of audio-language models.

## Context

Read these files first:
- `docs/paper-a-discussion-stub.md` — current §5 stub (partially written)
- `docs/paper-a-method.md` — §3 Method (for framework details)
- `docs/paper-a-results.md` — §4 Results (for findings to discuss)
- `docs/paper-a-outline.md` — §5 outline

## Your task

Expand the stub into a complete `docs/paper-a-discussion.md` (new file).

### §5.1 gc(k) as a Unifying Metric
Expand the existing stub. Add:
- Explicit comparison to AudioLens (Ho et al., 2025): gc(k) is the "causal upgrade" to their observational lens
- Comparison to Glazer et al.'s saturation layer: gc(k) extends encoder-only to full pipeline
- The "Causal AudioLens" framing: gc(k) at Pearl Level 3 vs. logit lens at Pearl Level 1
- The Triple Convergence prediction: if k* ≈ 50% depth holds across scales (base→small→medium), this supports depth-proportional crystallization

### §5.2 AND-Gate Insight
Expand existing stub. Add:
- Why OR-gate dominance is a safety-critical failure mode (medical transcription, legal proceedings)
- The cascade degree κ = 1 − α_AND as a deployment risk score
- Concrete recommendation: models should report κ alongside task accuracy
- Open question: can α_AND be improved via training objectives?

### §5.3 Limitations and Scope (NEW — 3-4 paragraphs)
Write honestly about:
1. Current scope: Whisper-base encoder only; full ALM experiments pending
2. Mock experiment status: 27 experiments validate algebraic logic, not neural behavior
3. Linearity assumption: gc(k) captures linear causal influence; superposition and nonlinear circuits not captured
4. Generalization: findings on English Whisper may not extend to multilingual or instruction-tuned models

### §5.4 Future Work
3-4 concrete next steps:
1. Scale up Q001/Q002 to Whisper-small/medium (pending GPU)
2. Test gc(k) on Qwen2-Audio full pipeline
3. Validate pre-registered predictions on ALME conflict items
4. Test whether RL training (MPAR²) shifts gc(k) profiles toward stronger listening

### Output
Write the complete new file `docs/paper-a-discussion.md`. Target: ≤200 lines. 
Be rigorous but readable — this is for an interpretability/AI safety audience (Interspeech/NeurIPS level).
