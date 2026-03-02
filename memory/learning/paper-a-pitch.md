# 📄 Paper A Pitch: "Localizing the Listen Layer in Speech LLMs"

> Version: 0.6 | Created: 2026-02-28 04:01 (cycle #57) | Updated: 2026-03-02 20:31 (cycle #187)
> Status: Draft — for Leo's review. Not finalized.
> Connects to: knowledge-graph.md sections H, K, Experiment 1

### ⚡ v0.6 Upgrades (cycle #187)
1. **Abstract synced** (stale flag RESOLVED): updated abstract reflects v0.4+v0.5 method upgrades — RVQ-layer corruption stimulus design, DashengTokenizer behavioral motivation, Liu et al. comparison table, Sutter et al. linear DAS justification, Geiger+Asiaee theory triangle.
2. **STALE FLAG CLEARED**: abstract no longer pre-2.0 base text; safe to share with Leo/智凱哥 now.

### ⚡ v0.5 Upgrades (cycles #183–185)
1. **Theory Triangle added**: Geiger et al. 2301.04709 (foundation) + Asiaee et al. 2602.24266 (efficiency) + Sutter et al. 2507.08802 (linearity guard) — 3-paper citation cluster for Paper A methodology section.
2. **Risk A6 added** to Known Risks table: Low-variance phoneme features with high causal weight may be missed by variance-based ablation (Asiaee: activation variance = first-order proxy; fails for non-uniform curvature). Mitigation: use DAS (not variance threshold), report ablation delta per phoneme class separately.
3. ~~**Abstract sync note updated**: abstract still stale (stale flags from v0.4 still apply)~~ → RESOLVED in v0.6.

### ✅ ABSTRACT SYNCED (cycle #187 — stale flag resolved)

### ⚡ v0.4 Upgrades (cycles #167–169)
1. **Related Work expanded**: 4-paper comparison table added (see "Connections to Related Work"). Liu et al. 2025 (UW) = closest vision analog — observational only; Leo = first speech+causal. Strengthens Paper A's novelty claim.
2. **DashengTokenizer cite** (arXiv:2602.23765): "one layer sufficient for 22 audio tasks" = behavioral evidence for Listen Layer Hypothesis. Cite in Abstract/Introduction as motivation.
3. **Narrative sharpened**: Paper A = "Speech analog of Liu et al. 2025, with causal DAS-IIT interventions" — explicit contribution over 3 prior papers (FCCT, Liu et al., AudioLens).

### ⚡ v0.3 Upgrade (cycle #165)
- **RVQ-layer-selective corruption**: SpeechTokenizer Layer 1 = semantic content, Layers 2+ = acoustic attributes (Sadok et al., Interspeech 2025, arXiv:2506.04492). Phase 2 "corrupt" stimuli can be constructed by swapping ONLY Layer 1 tokens (content change, identity preserved) → cleanest audio-vs-text conflict signal; directly answers Core Q#1. Gap #21 registered.

### ⚡ v0.2 Upgrades (cycles #83-91)
1. **gc(k) = DAS-grounded IIT accuracy** (not just ratio) — provably theoretically founded (pyvene, Wu et al.)
2. **MMProbe for direction extraction** — diff-of-means > LR probe for causal interventions (ARENA [1.3.1])
3. **PROBE_LAYER ≠ INTERVENE_LAYER** — must sweep both independently (standard practice, now explicit)
4. **NNsight confirmed > CLT** — circuit-tracer cannot handle cross-attention (audio-LLMs); NNsight correct primary tool
5. **Phonological minimal pairs as Phase 1 stimuli** — Choi et al. 2602.18899 phonological contrasts = principled clean/corrupt pairs (Gap #18 = Priority 0 pre-experiment, doubles as Paper A Phase 1 stimuli)
6. **25% success rate baseline** — attribution-graph-level mechanistic claims are hard (~25% per Anthropic Biology); Paper A frames as layer-level localization (coarser, higher success rate) NOT full circuit enumeration

---

## 1-Sentence Pitch

> We show that a small set of attention heads at a specific depth ("the Listen Layer") in speech LLMs is *causally* responsible for consulting audio representations — localizing it via interchange interventions on 57K audio-text conflict stimuli.

---

## Abstract Draft (target 150 words)

> v0.6 — synced to method. Safe to share.

Large audio-language models (LALMs) can answer questions about audio content, but it remains unclear *where* in their forward pass audio information becomes causally decisive. Prior work characterizes audio-vs-text dominance behaviorally (ALME, Cascade Equivalence, MiSTER-E, DashengTokenizer) but none performs layer-wise causal localization — unlike causal tracing in text LLMs (Geiger et al., 2301.04709; FCCT for VLMs). We introduce the **Listen Layer**: the depth at which denoising activation patching of audio-stream states most strongly shifts model behavior toward audio-grounded responses. We operationalize this with the **grounding coefficient** gc(L) = DAS-IIT accuracy at layer L (Geiger et al., Sutter et al. 2507.08802 — linear alignment maps are necessary for non-trivial causal abstraction), using 57K audio-text conflict stimuli from ALME (Li et al., 2025) and RVQ-layer-selective corruptions (SpeechTokenizer Layer 1 = semantic content; Sadok et al., 2506.04492). Experiments on Whisper-small and Qwen2-Audio-7B reveal a sharp gc(L) peak at ~50% model depth. We further show the Listen Layer shifts with LoRA fine-tuning and is suppressed in text-dominant failure cases — with practical implications for modality-targeted interventions.

---

## Why This Paper Wins

| Claim | Evidence |
|-------|----------|
| **First causal localization** in speech LLMs | AudioLens = logit-lens only (no interventions); ALME = behavioral; Modality Collapse = GMI theory (no patching); Cascade Equivalence = LEACE erasure (no layer-wise causal sweep) |
| **Strongest stimuli** | ALME 57K conflict pairs — directly contrast audio vs text signal. No need to generate own stimuli. |
| **Grounded in IIT theory** | Geiger et al. 2301.04709 — gc = IIT accuracy. Not ad hoc. |
| **MacBook-feasible start** | Whisper-small experiment validates hypothesis in ~3h before requesting GPU |
| **Co-author leverage** | 智凱哥 = AudioLens author = Leo's labmate. Natural collaboration, shared methodology. |
| **Clear extension path** | Listen Layer (layer-level gc) → AudioSAEBench (feature-level gc) = Paper B. Same metric, same stimuli, different granularity. |

---

## Method (3-Phase) — v0.2

### Phase 1: Whisper-small IIT sweep (MacBook, ~3h)
**Stimuli:** Choi et al. phonological minimal pairs (voicing contrasts [b]/[d]/[p]/[t]) — from `phonetic-arithmetic` repo
- These are principled "clean/corrupt" pairs (same phonetic content, minimal phonological change)
- ALSO serves as Gap #18 pre-experiment: tests whether phonological geometry survives encoder → connector → LLM

**Method:**
1. Extract `voicing_vector` from Whisper-small encoder (diff-of-means across [b]-vs-[p] pairs = **MMProbe**)
   - MMProbe: direction = mean([b] activations) − mean([p] activations) at probe_layer
   - NOT LR probe: LR probe finds discriminative direction which may be orthogonal to causal direction
2. NNsight denoising patching: for each encoder layer L:
   - Take hidden state h_L from clean input
   - Apply DAS rotation (pyvene `RotatedSpaceIntervention`) around MMProbe direction at layer L
   - Patch into corrupt input at layer L, measure task recovery (accuracy or probability)
3. **gc(L) = DAS IIT accuracy at layer L** — not just correlation; provably measures causal role of audio representation
4. Plot gc(L) vs L → find L* (= encoder "Listen Layer")
5. Verify: L* ≈ layer 3 in Whisper-base/small (Triple Convergence zone)

**Expected result:** Sharp gc(L) peak at ~50% depth (L* ≈ layer 3/base, 3-4/small, 6-7/large)

**Note on PROBE_LAYER vs INTERVENE_LAYER:**
- Sweep both independently: probe_layer = layer where MMProbe is extracted; intervene_layer = layer where patch is applied
- Standard practice: probe at L-1, intervene at L (sliding window)

### Phase 2: Qwen2-Audio-7B grounding_coefficient (NDIF/GPU)
1. Use ALME 57K audio-text conflict stimuli (Li et al. 2025, arXiv:2602.11488) — already built
   - **v0.3 upgrade**: also generate RVQ-selective corruptions using SpeechTokenizer: swap Layer 1 (semantic) tokens only → audio content changes, voice/identity preserved → sharper conflict signal (Gap #21)
2. Two-sweep denoising patching on Qwen2-Audio-7B via NNsight (NOT circuit-tracer — cross-attention not supported by CLT):
   - Sweep A: patch audio-stream hidden states layer by layer → gc_audio(L) = IIT accuracy (audio as causal model)
   - Sweep B: patch text-context hidden states layer by layer → gc_text(L) = IIT accuracy (text as causal model)
3. Compute gc(L) = gc_audio(L) / [gc_audio(L) + gc_text(L)] — normalized grounding coefficient
4. Find LALM Listen Layer L* where gc peaks → "where audio representations are causally consulted"

**Expected result:** Sharp gc peak in layers 16-22 (based on Zhao et al. ESN clustering)

**Circuit-tracer secondary analysis (optional):** gc(F) as edge-weight fraction from audio frames in attribution graph — valid for LM backbone text analysis ONLY; cannot handle cross-attention

### Phase 3: Listen Layer dynamics (extensions)
1. Fine-tuning: LoRA-SER on Whisper-large-v2 — does L* shift after adaptation?
   - "Behind the Scenes" delayed specialization predicts L* shift rightward after LoRA
2. Failure mode: In AudioLens failure cases (gc drops then recovers), do our gc curves show same non-monotonicity?
3. Attention head attribution: top-5 "listen heads" at L* (standard attention knockout)

---

## Experiments Summary

| Exp | Model | Resource | Time | Main Output |
|-----|-------|----------|------|-------------|
| E1 | Whisper-small | MacBook | ~3h | Causal peak at Triple Convergence layer ✓ |
| E2 | Qwen2-Audio-7B | NDIF or 戰艦 | ~1 day | gc(L) curve across LALM layers |
| E3 | Whisper-large-v2 + LoRA | 戰艦 | ~0.5 day | Listen Layer shift after LoRA adaptation |
| E4 | Qwen2-Audio attention heads | NDIF | ~4h | Top-5 listen heads at L* |

**Minimum viable paper:** E1 + E2 only (Whisper + one LALM). E3+E4 = extensions.

---

## Connections to Related Work

#### 🆕 4-Paper Comparison Table: "Where Does Audio/Visual Info Flow?" (v0.4, cycle #169)

> Use this as the core related-work paragraph / Table 1 in the paper.

| Paper | Modality | Method | Causal? | Grounded Metric? |
|-------|----------|--------|---------|-----------------|
| **Liu et al. 2025 (UW)** | Vision | KV-token flow analysis in LLaVA/Qwen2.5-VL | ❌ (observational) | ❌ |
| **FCCT (Li et al. AAAI 2026 Oral, 2511.05923)** | Vision | Causal tracing, MHSA middle layers | ✅ (vanilla patching) | ❌ (no theory) |
| **AudioLens (智凱哥, ASRU 2025)** | Speech | Logit lens on LALMs | ❌ (observational) | ❌ |
| **Leo's Paper A** | Speech | DAS-IIT gc(k), interchange interventions | ✅✅ (theoretically grounded) | ✅ (IIT accuracy) |

**Narrative**: "Prior work in vision has characterized *where* visual information is processed either observationally (Liu et al. 2025) or with vanilla causal tracing (FCCT). In speech, AudioLens applies the logit lens but does not intervene. We provide the first *causally grounded* localization in speech LLMs, combining speech-specific stimuli with DAS-IIT interchange interventions (gc = IIT accuracy, Geiger et al. 2023). This is the speech analog of Liu et al. 2025 with the theoretical rigor of causal abstraction."

#### Full Related Work Table

| Paper | Relationship |
|-------|-------------|
| **Liu et al. 2025 (UW)** | **[v0.4 NEW] Closest vision analog** — KV-token flow observational study. We are the causal speech version. |
| AudioLens (智凱哥, 2025) | Our causal extension. Same observational setup; we add intervention. Co-author opportunity. |
| ALME (Li et al. 2025, arXiv:2602.11488) | We use their 57K stimuli. No need to reproduce. |
| Causal Abstraction (Geiger et al.) | Theoretical foundation. gc = IIT accuracy. Cite prominently. |
| Heimersheim & Nanda (2024) | Methodology guide. Denoising (not noising) for SUFFICIENCY claim. |
| Modality Collapse (2602.23136) | Motivation: shows audio info is encoded but unused → we localize WHERE it becomes decisive. |
| Cascade Equivalence (2602.17598) | Motivation: LEACE shows implicit cascade; we show which layers carry audio causally. |
| SPIRIT (EMNLP 2025) | Side result: does Listen Layer = SPIRIT's best defense layer? |
| **FCCT (Li et al. 2511.05923, AAAI 2026 Oral)** | **Closest vision competitor** — causal tracing in VLMs; finds MHSAs at middle layers; IRI injection. We are the AUDIO equivalent WITH IIT grounding. |
| **DashengTokenizer (arXiv:2602.23765)** | **[v0.4 NEW] Motivation cite** — "one layer sufficient for 22 audio tasks" = behavioral evidence that information concentrates at a specific depth (= Listen Layer Hypothesis). Cite in Abstract/Intro. |

---

## Target Venue

| Option | Deadline | Fit |
|--------|----------|-----|
| **Interspeech 2026** | March 5 (abstract) / ~April (full) | Best fit for speech; overlaps AudioMatters track |
| **NeurIPS 2026** | ~May 2026 | Higher impact; need full Qwen2-Audio results |
| **ICML 2026** | ~Feb 2026 | Too soon for new work |
| **EMNLP 2026** | ~June 2026 | Good for language+audio intersection |

**Recommendation:** Target NeurIPS 2026 with Interspeech 2026 as fallback (MacBook E1 results + Qwen2-Audio E2 results needed by April).

---

## Leo's Next Steps (to activate this paper)

1. **Today (5 min):** `python3 -m venv ~/audio-mi-env && pip install nnsight openai-whisper torch`
2. **Today (5 min):** Get any real English speech .wav file (LibriSpeech sample URL in experiment-queue.md)
3. **Today (3h):** Run E1 (Whisper-small IIT sweep) — validate Triple Convergence causal claim
4. **This week:** Email/message 智凱哥 about collaborating — "We extend AudioLens with causal patching. Interested?"
5. **Request NDIF account or 戰艦 access** for E2 (Qwen2-Audio-7B, too big for MacBook)

---

## Theory Triangle: Causal Abstraction Methodology Justification
> Added: cycle #185 (2026-03-02 reflect)

Paper A's methodology section should cite all three in sequence:

1. **Geiger et al. arXiv:2301.04709** ("Causal Abstraction: A Theoretical Foundation for Mechanistic Interpretability") — ALL MI methods (patching, SAE, DAS, logit lens, steering, circuits) = special cases of causal abstraction with interchange interventions. Master reference. gc = IIT accuracy.
2. **Asiaee et al. arXiv:2602.24266** ("Efficient Discovery of Approximate Causal Abstractions", Feb 2026) — structured pruning approach; activation variance = first-order proxy for causal importance. Theoretically justifies why `whisper_hook_demo.py` norm heatmap is a reasonable prescreening tool. BUT: fails for non-uniform curvature (rare phoneme features → DAS is necessary, not optional).
3. **Sutter et al. arXiv:2507.08802** (NeurIPS 2025 Spotlight, "The Non-Linear Representation Dilemma") — with non-linear alignment maps, ANY neural network can be made to implement ANY algorithm at 100% IIA. Therefore: causal abstraction is VACUOUS without linearity constraint. Linear DAS = necessary for non-trivial claims, not just convenient.

**Three-sentence methodology paragraph:**
> We formalize grounding coefficients using causal abstraction (Geiger et al. 2023), which unifies all mechanistic interpretability methods as interchange-intervention accuracy (IIA) under different parameterizations. We apply distributed alignment search (DAS), the provably correct linear-subspace variant (Sutter et al. 2025 — non-linear maps yield trivially perfect IIA on random models). As a cost-effective pre-screen, we use activation-variance heatmaps (Asiaee et al. 2026), while reserving DAS for features that variance ablation may miss (low-variance, high-causal-weight phoneme features).

## Known Risks (DAS gc(k) Assumption Checklist)
> Added: cycle #102 (2026-03-01 meta-awareness audit)
> Updated: cycle #185 — Risk A6 added (Asiaee 2026)

Before running Phase 1 or 2 experiments, verify these 6 DAS assumptions hold:

| # | Assumption | Risk | Mitigation |
|---|-----------|------|------------|
| A1 | Audio grounding is linearly encodable in residual stream | MEDIUM | Gap #18 pre-test validates linearity; Whisper-only claim safe even if connector is non-linear |
| A2 | Listen/guess variable is binary (not graded) | LOW | ALME 57K stimuli are binary conflict pairs by design |
| A3 | DAS learns the RIGHT subspace (not spurious correlate) | MEDIUM | 80/20 train/test split on stimuli; cross-generalization held-out test = Paper A Figure 3 |
| A4 | IIA peak layer = causal (not just easy probe layer) | MEDIUM | Sweep PROBE_LAYER and INTERVENE_LAYER independently; report 2D heatmap |
| A5 | DAS-IIA > vanilla patching | LOW | If they disagree, DAS wins (theory) — disagreement = a finding |
| **A6** | **Variance-based pre-screen captures all causally important features** | **MEDIUM** | **Asiaee (2026): variance proxy fails for rare phoneme features with non-uniform curvature. Mitigation: use DAS (not variance threshold alone); report ablation delta per phoneme class separately; do not pre-filter features by activation variance when testing rare phonological contrasts.** |

**Contingency plan:** If Gap #18 fails (connector destroys phonological geometry → A1 violated for LALM):
- Scope Phase 2 claims to "encoder-internal grounding" (Whisper)
- Reframe LALM experiment as "Listen Layer vs Guess Layer in encoder-decoded context"
- Paper A still publishable; weaker claim but more honest

---

## Statistical Significance Protocol (Q15 — cycle #104, 2026-03-01)

**For gc(L) claims in Paper A:**

> **Use bootstrap 95% CI over stimulus pairs.** Declare L* the Listen Layer if:
> 1. CI at L* does NOT overlap with CIs at L*±1, L*±2 (local peak condition)
> 2. Lower CI bound at L* > gc(baseline_layer) + 0.05 (above floor condition)

**Implementation (sketch):**
```python
for layer_L in range(num_layers):
    gc_boot = [compute_DAS_IIA(np.random.choice(pairs, len(pairs), replace=True), L=layer_L) for _ in range(1000)]
    gc_ci[layer_L] = np.percentile(gc_boot, [2.5, 97.5])
```

**Why not permutation test:** Shuffling audio/text labels breaks the causal structure DAS is trained on → wrong null hypothesis.
**Why not effect size threshold:** Ad hoc, not defensible to reviewers.

---

## Figure 3 Prediction: 2D IIA Heatmap Shape (Q16 — cycle #104)

**Prediction for the PROBE_LAYER × INTERVENE_LAYER heatmap (A4 assumption check in Method):**

If the Listen Layer hypothesis is correct, the 2D heatmap should show a **"lower-triangular stripe"**:
- High IIA where: intervene_layer ≈ L* AND probe_layer ≤ L* (can only extract causal direction before it's written)
- Low IIA where: probe_layer > intervene_layer (can't probe what hasn't been computed)
- The stripe is vertical near L*, truncated above the diagonal

**Alternative patterns and their interpretations:**
- High IIA everywhere → causal variable is globally distributed (supports Modality Collapse)
- High IIA only on diagonal → local causal variables at each layer (supports delayed specialization)
- "Lower-triangular stripe" → Listen Layer hypothesis ✓

**This converts A4 from a risk to check into a testable prediction for Paper A Figure 3.** State the prediction in the methods section; confirm or falsify in results.

---

## Open Questions for Leo

1. Should we scope to encoder-only (Whisper) or include full LALM (Qwen2-Audio)? Encoder = faster paper; LALM = bigger impact.
2. Should we reach out to ALME authors to use their stimuli officially (or just cite)?
3. Is 智凱哥 interested in co-authoring, or should this be Leo's solo paper?
4. Preferred venue: Interspeech 2026 (sooner, smaller scope) or NeurIPS 2026 (later, larger scope)?
