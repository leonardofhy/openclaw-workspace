# Paper A — Results & Discussion Section Skeleton
> "Localizing the Listen Layer in Speech LLMs"
> Status: Skeleton — section headers, table/figure stubs, placeholders. Fill prose + real numbers in.
> Created: 2026-03-02 by autodidact (Q025)

---

## 4. Results

### 4.1 Listen Layer Localization in Whisper-small

**Narrative placeholder:** gc(k) peaks sharply at layer [TODO], consistent with a localized listen layer rather than distributed processing.

#### Table 1: gc(k) by Layer — Whisper-small (Phonological Minimal Pairs)

| Layer | gc(k) | IIT-acc (audio) | IIT-acc (baseline) | CKA to audio input |
|-------|-------|-----------------|--------------------|--------------------|
| 0     | —     | —               | —                  | —                  |
| 1     | —     | —               | —                  | —                  |
| …     | —     | —               | —                  | —                  |
| [ℓ*]  | **peak** | —           | —                  | —                  |
| …     | —     | —               | —                  | —                  |
| L-1   | —     | —               | —                  | —                  |

> [TODO: populate from gc_eval.py output; highlight ℓ* row in bold]

#### Figure 1: gc(k) Curve — Whisper-small

```
[FIGURE STUB]
X-axis: Layer index (0 … L-1)
Y-axis: Grounding Coefficient gc(k)
Series: gc(k) ± stderr across N stimuli pairs
Mark ℓ* with vertical dashed line + annotation
Panel B (optional): CKA heatmap (layer × layer)
```

> [TODO: generate from scripts/gc_eval.py; save to figures/fig1_gck_whisper.pdf]

---

### 4.2 Causal Patching Experiment

**Narrative placeholder:** Patching at ℓ* from clean→corrupt (and vice versa) produces the largest behavior flip, confirming causal sufficiency of the listen layer.

#### Table 2: Causal Patching — Behavior Flip Rate by Layer

| Patched Layer | Flip Rate (↑ = audio-grounded) | Δ vs. Baseline |
|---------------|-------------------------------|----------------|
| [TODO]        | —                             | —              |
| [ℓ*]          | **—**                         | **—**          |
| [TODO]        | —                             | —              |

> [TODO: populate from causal patching sweep; Q001/Q002 results when unblocked]

#### Figure 2: Patching Effect vs. Layer Depth

```
[FIGURE STUB]
X-axis: Layer index
Y-axis: Behavior flip rate (%)
Series: Clean→Corrupt patch (dashed), Corrupt→Clean patch (solid)
Mark ℓ* — expected peak on both curves
```

> [TODO: generate after Q001/Q002 complete; save to figures/fig2_patching.pdf]

---

### 4.3 Ablations

#### 4.3.1 Probe Type Ablation

| Probe | gc(ℓ*) | ℓ* location |
|-------|--------|-------------|
| MMProbe (ours) | — | — |
| Linear Probe | — | — |
| Random Baseline | — | — |

> [TODO: run variants in gc_eval.py with --probe-type flag]

#### 4.3.2 Stimulus Set Size

| N pairs | gc(ℓ*) | Stability (var) |
|---------|--------|-----------------|
| 10      | —      | —               |
| 50      | —      | —               |
| 100     | —      | —               |

> [TODO: populate via Q026 synthetic stimuli generator output]

#### 4.3.3 Phoneme Category Breakdown (Whisper-small)

| Contrast Type | ℓ* (modal) | gc peak value |
|---------------|-----------|---------------|
| Voicing [b/p, d/t] | — | — |
| Place [b/d, p/t]   | — | — |
| Manner [TODO]      | — | — |

> [TODO: run stratified eval; relevant to Gap #18]

---

### 4.4 Generalization to Qwen2-Audio-7B

**Placeholder:** [Results pending Q003 — GPU required; add after Leo approves]

#### Table 3: Cross-Model Listen Layer Location

| Model | ℓ* (abs) | ℓ* / L (rel) | gc peak |
|-------|----------|-------------|---------|
| Whisper-small | — | — | — |
| Qwen2-Audio-7B | [BLOCKED: GPU] | — | — |

> [TODO: fill Qwen2 row after Q003 completes]

---

## 5. Discussion

### 5.1 Interpretation of the Listen Layer

[TODO: 2-3 paragraphs]
- What does it mean that ℓ* is localized? (Modular vs. distributed view)
- Connection to IIT: the layer is not just "where audio lives" but where it causally governs output
- Comparison with findings in LLM circuits (Meng et al., ROME; Geiger et al., DAS)

### 5.2 Why Does It Matter for ASR Error Correction?

[TODO: 1-2 paragraphs]
- If ℓ* is known, interventions can be targeted → more efficient than full fine-tuning
- Potential: inference-time audio grounding boost without gradient update
- Link to T5 (jailbreak detection): same principle applies to adversarial audio

### 5.3 Limitations

- **Scale**: Experiments on Whisper-small; generalization to larger models (Qwen2-Audio-7B) pending
- **Stimulus artificiality**: Phonological minimal pairs are cleaner than real-world ambiguous speech; effect size may differ in naturalistic settings
- **Probe linearity assumption**: MMProbe assumes a linear direction; non-linear structure not captured
- **Single conflict type**: ALME corpus focuses on factual audio-text conflict; other conflict types (prosodic, emotional) unexplored
- **Static ℓ***: We treat ℓ* as fixed per model; it may vary with context, speaker, or acoustic condition

### 5.4 Future Work

- [ ] Extend to Qwen2-Audio-7B and audio-llava-class models
- [ ] Investigate ℓ* shift under noise/accent conditions
- [ ] Use ℓ* location for targeted LoRA fine-tuning (intervention efficiency hypothesis)
- [ ] Apply listen-layer framing to audio jailbreak detection (T5 track)
- [ ] Explore multi-listen-layer architectures (is ℓ* ever bimodal?)
- [ ] Synthetic stimuli from Q026 → validate vs. real phoneme pairs (sanity check)

---

## Appendix A: Supplementary Results

### A.1 Phonological Geometry Through Connector (Gap #18)

[TODO: report cosine similarity of voicing direction before/after connector layer — Q001 results when unblocked]

### A.2 Full Layer-by-Layer gc(k) Tables

[TODO: full tables for all models]

### A.3 Synthetic Stimuli Validation (Q026)

[TODO: compare gc curves on synthetic vs. real phoneme pairs after Q026 complete]

---

*Skeleton complete. Real numbers: populate after gc_eval.py + Q026 synthetic stimuli are run.*
*Blocked experiments (Q001-Q004): fill after Leo approves venv + real speech.*
