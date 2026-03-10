# Nanda 5-Principle Eval Protocol: Audio Jailbreak Detection
> Track: T5 (Listen-Layer Audit / Paper C / MATS)  
> Task: Q059 | Created: 2026-03-07 | Status: Tier 0 doc

---

## Purpose

Apply Nanda's 5 mechanistic interpretability principles to validate that our audio jailbreak **detection approach is mechanistically grounded**, not just empirically lucky. Each principle becomes a concrete evaluation checkpoint.

---

## Background: Nanda's 5 Principles

Nanda (Anthropic / EleutherAI) articulates MI as requiring:

| # | Principle | Short Form |
|---|-----------|-----------|
| 1 | **Identify the mechanism** | Find which components process the relevant feature |
| 2 | **Causal intervention validates it** | Ablations / activation patching confirm causal role |
| 3 | **Ground truth circuit = minimal** | Circuit is not larger than needed |
| 4 | **Generalizes across inputs** | Mechanism works on diverse jailbreak types, not one example |
| 5 | **Connects to model behavior** | Mechanism explains why the model complies/refuses |

---

## Eval Protocol: One Checkpoint per Principle

### Principle 1 — Identify the Mechanism

**Claim**: Audio jailbreaks modulate specific audio encoder layers (L12–L19 in Whisper-large-v2), producing anomalous residual stream activation norms.

**Eval checkpoint P1:**
- [ ] Run `unified_eval.py` on 10 clean speech + 10 jailbreak samples
- [ ] Extract per-layer residual norm at L12, L15, L18
- [ ] Show that jailbreak samples have norm deviation > 2σ above benign baseline
- **Success metric**: Wilcoxon signed-rank test p < 0.05 on norm differences
- **Script**: `skills/autodidact/scripts/unified_eval.py` (existing)

---

### Principle 2 — Causal Intervention Validates It

**Claim**: Patching jailbreak activations → benign activations at identified layers causes model to refuse / respond normally.

**Eval checkpoint P2:**
- [ ] Implement `causal_patch_jailbreak.py`: replace L15 residual stream in jailbreak audio with mean-benign activation
- [ ] Measure: does output shift from compliance to refusal?
- [ ] Measure gc(k) score before/after patching
- **Success metric**: ≥70% of jailbreak samples change predicted class after patch
- **Tier**: Tier 1 (CPU, toy audio) → Tier 2 (full model) pending Leo approval
- **Script**: `skills/autodidact/scripts/causal_patch_jailbreak.py` (to build)

---

### Principle 3 — Minimal Sufficient Circuit

**Claim**: The jailbreak-relevant mechanism can be localized to ≤3 attention heads per layer.

**Eval checkpoint P3:**
- [ ] Run attention head knockout: zero out each head's output individually at L15
- [ ] Measure which head knockouts most reduce detection performance
- [ ] Show top-3 heads account for ≥80% of the signal
- **Success metric**: ablation curve shows steep drop from top-3 heads, plateau after
- **Script**: `skills/autodidact/scripts/head_knockout_eval.py` (to build)
- **Tier**: Tier 1 (CPU with toy audio, Whisper-small)

---

### Principle 4 — Generalizes Across Inputs

**Claim**: The identified mechanism works on:
- (a) adversarial audio (GCG-audio)
- (b) natural jailbreak attempts (direct speech commands)
- (c) multilingual jailbreaks (Mandarin prompt injection)

**Eval checkpoint P4:**
- [ ] Define 3 jailbreak subcategories in `jailbreak_taxonomy.md`
- [ ] Run P1 eval on each subcategory separately
- [ ] Report per-category AUROC
- **Success metric**: AUROC > 0.7 on all 3 subcategories
- **Data note**: We need at least 5 samples per subcategory — can use synthetic for now
- **Script**: extend `unified_eval.py` with `--category` flag

---

### Principle 5 — Connects to Model Behavior

**Claim**: The activation pattern we detect causally predicts whether the downstream LLM (Qwen2-Audio, Whisper+LLM pipeline) will comply with the jailbreak.

**Eval checkpoint P5:**
- [ ] Build `behavior_correlation.py`: score each sample with gc(k) probe, compare to LLM output (comply/refuse) labels
- [ ] Compute Spearman ρ between probe score and compliance rate
- [ ] Visualize: scatter plot of probe score vs compliance probability
- **Success metric**: Spearman ρ > 0.5
- **Tier**: Tier 1 (CPU, toy model behavior labels)

---

## Protocol Execution Order

```
P1 (norm analysis) → P3 (minimal circuit) → P4 (generalization)
       ↓                                           ↓
      P2 (causal patch, needs P1 layers)     P5 (behavior link, needs P4 data)
```

P1 is the gating experiment. If P1 fails (no significant norm deviation), the whole hypothesis needs revisiting.

---

## Artifacts To Build (linked to queue tasks)

| Artifact | Principle | Status |
|----------|-----------|--------|
| `unified_eval.py` (existing) | P1 | ✅ exists (needs audio samples) |
| `causal_patch_jailbreak.py` | P2 | ❌ to build |
| `head_knockout_eval.py` | P3 | ❌ to build |
| `jailbreak_taxonomy.md` | P4 | ❌ to write |
| `behavior_correlation.py` | P5 | ❌ to build |

---

## Integration with MATS Proposal

This protocol maps directly to the MATS research task proposal (Q056):
- **Task 1** (MATS) = P1 + P3 (find & minimize circuit)
- **Task 2** (MATS) = P2 (causal intervention)
- **Task 3** (MATS) = P4 + P5 (generalization + behavioral link)

The 5-principle structure gives reviewers confidence that we're doing *real MI*, not just training a probe and calling it done.

---

## Open Questions

1. Can we get synthetic jailbreak audio data without GPU? (Yes — text-to-speech + adversarial perturbation scripts)
2. Does Whisper-small exhibit the same mechanism as Whisper-large-v2? (Should test P1 on both)
3. How to handle the case where P1 fails but gc(k) still works? (Suggests gc(k) is detecting surface statistics, not mechanism)
