# Paper A Outline — Grounding Coefficient: Mechanistic Interpretability of Audio-Language Models

> **Track:** T3 (Listen vs Guess in Audio-LLMs)
> **Status:** Skeleton v1.0 — 2026-03-18
> **Working title:** "The Listening Geometry: Where Audio-Language Models Listen, Guess, and Collapse"

---

## Abstract (sketch)

Audio-language models (ALMs) can either genuinely consult their audio input or rely on text-context priors — but no existing method causally distinguishes these strategies at the layer level. We introduce the **grounding coefficient** gc(k), a causal metric based on interchange intervention that quantifies how much each layer k relies on audio versus text context. We define a 5-dimensional **Listening Geometry** framework (gc peak, AND-gate fraction, Schelling stability, collapse onset, codec stratification) that profiles ALMs as strong listeners, shallow listeners, sophisticated guessers, or fragile listeners. [TODO: 1 sentence on key empirical result from real experiments. 1 sentence on implications for safety/deployment.]

---

## 1. Introduction (3-4 paragraphs)

### Para 1 — Problem: Listen or Guess?
- ALMs (Qwen2-Audio, Gemini, GPT-4o) process speech, but behavioral evaluations can't distinguish genuine audio grounding from text-prior pattern matching
- Modality Collapse (Zhao et al. 2602.23136): ALMs default to text priors when audio and text conflict
- MPAR² (2603.02266): RL training improves audio perception 31.7% → 63.5%, but mechanism unknown
- **Gap:** No causal, layer-wise account of where audio information is consulted vs. ignored

### Para 2 — What exists: observational tools
- AudioLens (Ho et al. 2025): logit lens on LALMs, finds critical layers, but NO causal patching
- Beyond Transcription (Glazer et al. 2025): encoder lens + saturation layer for Whisper, but encoder-only
- Zhao et al. (2601.03115): emotion-sensitive neurons, causal ablation, but never asks "audio or text source?"
- AR&D (Chowdhury et al. 2026): SAE features for AudioLLMs, but no audio-vs-text pathway test
- **Common gap across ALL 4:** observational or necessity-only; no denoising patching; no grounding metric

### Para 3 — Our contribution: grounding coefficient + Listening Geometry
- gc(k) = IIT-based causal metric (Geiger et al. 2021 DAS framework)
- 5-dimensional Listening Geometry framework for profiling ALMs
- AND/OR gate decomposition: which features require BOTH audio + text (genuine multimodal) vs. either alone
- Theory triangle: IIT causal abstraction (Geiger) + modality interaction theory (Sutter) + sparse feature decomposition (Asiaee)
- [TODO: brief mention of experimental validation scope]

### Para 4 — Contributions list
1. **gc(k) metric**: first causal, layer-wise grounding coefficient for ALMs
2. **Listening Geometry**: 5D framework (k*, α_AND, σ, t*, CS) that taxonomizes ALM listening strategies
3. **AND/OR gate framework**: mechanistic decomposition of multimodal feature dependence
4. **Empirical validation**: [TODO: N] experiments including voicing geometry in Whisper and causal contribution analysis
5. **Pre-registered predictions** for Modality Collapse (ALME conflict items) and MPAR² (RL-induced gc shift)

---

## 2. Related Work

### 2.1 Mechanistic Interpretability of Speech Models
- Whisper MI: Reid (2023), Glazer et al. (2025 — encoder lens, saturation layer), Van Rensburg (2026 — PCA speaker geometry)
- Phonological geometry: Choi et al. (2026 — voicing vectors linear in S3M space, 96 languages)
- Speech SAEs: AudioSAE (Aparin 2026), Mariotte (2025), Kawamura (2026 — AAPE neuron analysis)
- [TODO: cite NNsight, pyvene as tooling]

### 2.2 Audio-Language Model Interpretability
- AudioLens (Ho et al. 2025): logit lens, critical layer, information score — observational only
- AR&D (Chowdhury et al. 2026): SAE feature retrieve-describe pipeline for AudioLLMs — no causal grounding
- SPIRIT (Djanibekov et al. 2025): activation patching for jailbreak defense — noise-sensitive neurons, no SAE
- Zhao et al. (2601.03115): emotion-sensitive neurons (ESNs) — causal ablation but decoder-only, no audio-vs-text
- Behind the Scenes (Ma et al. 2026): LoRA MI for Whisper SER — no causal patching
- **Gap synthesis:** ALL above papers either (a) observational or (b) do necessity patching only or (c) never test audio-vs-text source → gc(k) fills all three gaps simultaneously

### 2.3 Theoretical Foundations
- IIT / Causal Abstraction: Geiger et al. (2021, 2301.04709) — DAS, interchange intervention accuracy (IIA)
- Multimodal interaction: Sutter et al. — modality interaction taxonomy
- Sparse decomposition: Asiaee et al. — feature-level grounding
- [TODO: Modality Collapse (Zhao 2602.23136), ALME (2602.11488), MPAR² (2603.02266) as behavioral motivation]
- Theory triangle: IIT (causal formalism) + Sutter (interaction taxonomy → AND/OR gates) + Asiaee (sparse feature-level analysis) → gc(k) inherits all three

---

## 3. Method

### 3.1 Grounding Coefficient gc(k)
- **Definition:**
  ```
  gc(k) = IIA_audio(k) / (IIA_audio(k) + IIA_text(k))
  ```
  where IIA_audio(k) = interchange intervention accuracy when patching audio representations at layer k; IIA_text(k) = same for text representations
- Linear DAS rotation (Geiger et al.) to find acoustic→text intervention subspace
- Sweep all encoder/decoder layers → gc(k) curve
- **Listen Layer** k* = argmax_k gc(k)
- Predicted pattern: sigmoid across layers, sharp transition at k*
- [TODO: formal notation for clean/corrupt pair construction]

### 3.2 AND/OR Gate Framework
- **Definition:** For each causal feature f at layer k:
  - **AND-gate:** IIA(A+T) >> max(IIA(A), IIA(T)) — requires BOTH audio and text
  - **OR-gate:** IIA(A+T) ≈ max(IIA(A), IIA(T)) — either modality suffices
  - **Passthrough:** feature not causally relevant
- α_AND(k) = fraction of causal features that are AND-gates at layer k
- **Prediction:** α_AND inversely correlates with hallucination rate
- Cascade degree = 1 - α_AND (Q113: measures text-override vulnerability)

### 3.3 Five-Dimensional Listening Geometry
| Dimension | Symbol | Definition | Section |
|-----------|--------|-----------|---------|
| gc peak | k* | argmax_k gc(k) | §3.1 |
| AND-gate fraction | α_AND(k*) | fraction of AND-gate features at k* | §3.2 |
| Schelling stability | σ | feature overlap across model seeds | §3.3.1 |
| Collapse onset | t* | decoder step where audio isolation drops below τ | §3.3.2 |
| Codec stratification | CS | max gc peak shift across audio codecs | §3.3.3 |

#### 3.3.1 Schelling Stability σ
- σ = overlap of top-k% IIA features across S ≥ 3 model seeds
- Separates core circuit from incidental features
- Prediction: AND-gate features have higher σ than OR-gate/passthrough

#### 3.3.2 Collapse Onset t*
- t* = min{t : Isolate_in(t) < τ}, τ = 0.1
- Extends gc from encoder to full forward pass (decoder dimension)
- Models with early t* more vulnerable to text-prior override

#### 3.3.3 Codec Stratification CS
- CS = max |k*(c1) - k*(c2)| / L across codecs {lossless, MP3-128, OGG-128, G.711}
- High CS = deployment-fragile (adversary can shift k* via codec choice)

### 3.4 Profiling Taxonomy

| Profile | k* | α_AND | σ | t* | CS | Behavior |
|---------|-----|-------|---|----|----|----------|
| Strong listener | Deep | High | High | Late | Low | Audio genuinely drives output; robust |
| Shallow listener | Shallow | Mid | Mid | Mid | Low | Audio used but easily overridden |
| Sophisticated guesser | Deep | Low | Low | Early | High | Complex audio processing but ignores it |
| Fragile listener | Deep | High | High | Late | High | Listens well only on training distribution |

### 3.5 Experimental Protocol
- **Stimuli:** Minimal pairs (phonological contrasts: voicing, place, manner) + ALME conflict items (57K)
- **Models:** [TODO: Whisper-small/medium (encoder), Qwen2-Audio (full LALM)]
- **Tools:** NNsight for hook injection, pyvene for intervention
- **Codec preprocessing (Gap #21):** SpeechTokenizer RVQ layer-selective corruption
  - Layer 1 tokens = semantic; Layers 2+ = acoustic → attribute-selective audio corruption
- **Evaluation protocol:** Bootstrap 95% CI, Cohen's d ≥ 0.3 threshold, per §3.8 of pitch doc

### 3.6 Diagnostic Tree (3-Tier Taxonomy)
- **Tier 1 (Codec):** Audio signal lost at encoding → gc flat near chance at ALL layers
- **Tier 2 (Connector):** Audio reaches encoder but lost at connector → gc peak in encoder, drops to 0 in LLM
- **Tier 3 (LLM backbone):** Audio enters LLM but overridden by text priors → mid-peak + late-drop gc profile
- Applied as pre-filter before ALME conflict analysis

---

## 4. Results

### 4.1 Encoder Analysis: Voicing Geometry in Whisper
- **Experiment Q001 (REAL):** Voicing vector extraction from minimal pairs (t/d, p/b, k/g, s/z) across encoder layers
  - Layer 5 peak (cos_sim=0.155), stop-stop weak alignment (+0.25), stop-fricative orthogonal
  - Partial linear phonological structure confirmed; motivates larger model experiments
- **Claim:** Whisper encoder has linearly structured phonological representations (prerequisite for gc)
- [TODO: Whisper-small/medium replication with stronger signal]

### 4.2 Causal Contribution Analysis
- **Experiment Q002 (REAL):** Zero/noise/mean ablation of each encoder layer → WER degradation
  - ALL layers critical — WER=1.0 on any single-layer ablation
  - **Key finding:** Whisper distributes information across all layers; no redundant layers
  - Differs fundamentally from text LLMs (middle layers ablatable)
- **Claim:** Distributed encoding → gc(k) curve shape matters more than any single layer

### 4.3 gc(k) Peak Localization (Mock → Real)
- **Experiment Q089 (MOCK):** AND% × gc(k) Pearson r = **0.9836**, peak at Layer 3 confirmed
- [TODO: Real gc(k) sweep on Whisper-small — Priority 1 experiment]
- **Claim:** gc(k) peaks sharply → localized listen layer exists

### 4.4 AND/OR Gate Validation
- **Experiment Q089 (MOCK):** At gc peak (L3): AND=100%, OR=0%, Passthrough=0%
- **Experiment Q113 (MOCK):** Cascade degree = 1 - α_AND validates text-override vulnerability measure
- **Claim:** AND-gate fraction is a near-perfect proxy for gc peak detection

### 4.5 Persona-Conditioned Grounding
- **Experiment Q039 (MOCK):** Anti-grounding persona shifts gc peak 2 layers earlier + boosts peak gc
  - Assistant persona: suppresses mean gc without shifting peak
  - H2 ✅ (anti-ground boosts peak), H3 ✅ (anti-ground shifts peak), H1 ✅ (assistant suppresses mean)
  - H4 ❌ (between/within variance ratio = 0.073, threshold >1.5)
- **Claim:** System prompts modulate grounding profile — safety implications

### 4.6 Collapse Onset and Incrimination
- **Experiment Q069 (MOCK):** t* detection identifies error-onset across degradation types
  - error_token t*=3.4, gradual_drift t*=3.8, sudden_collapse t*=2.7
  - Feature blame concentrates on audio-tracking features
- **Experiment Q078 (MOCK):** SAE patrol — suppression alert rate 96%, override 77%, FPR 3.3%
  - 4 persistent offenders: [f3, f12, f20, f23] → interpretability candidates
- **Claim:** t* + SAE incrimination = two-level attribution for grounding failure

### 4.7 RAVEL Disentanglement
- **Experiment Q053 (MOCK):** MicroGPT RAVEL validates audio_class disentanglement
  - 5/6 components pass (83.3%), speaker_gender fully disentangled across all layers
  - L0 audio_class bleed (Isolate=0.16) confirms early layers still entangled
- **Claim:** Audio attributes are disentangleable at intermediate+ layers → gc operates on clean features

### 4.8 Pre-Registered Predictions (Modality Collapse × gc)
- **P1:** follows_text items show late-layer gc drop (Δgc ≥ 0.10, d ≥ 0.3)
- **P2:** Rare phoneme contrasts show stronger late-layer drop than common ones
- **P3:** Tier 1 (degraded audio) items show flat gc at ALL layers (distinct from Tier 3)
- **P4:** Listen layer k* shifts earlier for conflict items vs. baselines
- [TODO: Run on ALME conflict stimuli when GPU access available]

### 4.9 [BLOCKED] Experiments
- **Q117:** GSAE density too weak — graph-regularized SAE co-activation density insufficient for gc framework
- **Q123:** FAD-RAVEL direction wrong — FAD bias correlation sign reversed from prediction
- [TODO: Diagnose root cause; revise or discard these predictions]

---

## 5. Discussion

### 5.1 gc(k) as a Unifying Metric
- Subsumes AudioLens critical layer (observational → causal)
- Subsumes Beyond Transcription saturation layer (encoder-only → full LALM)
- Connects to Triple Convergence: layer 3 in base ≈ 50% depth = semantic crystallization
- [TODO: formalize "Causal AudioLens" framing]

### 5.2 AND-Gate Insight: Genuine Multimodal Processing
- AND-gate fraction distinguishes genuine audio-text integration from independent processing
- Cascade degree (1 - α_AND) as text-override vulnerability measure
- Implication: models with low α_AND are "sophisticated guessers" despite high task accuracy

### 5.3 Safety Implications
- Jailbreak = forces gc suppression → shifts listener profile toward sophisticated guesser
- SPIRIT defense operates at noise-sensitive neurons; gc explains WHY those neurons matter
- Persona-conditioned grounding: anti-grounding prompts shift gc peak → prompt injection risk
- [TODO: Connect to Gap #24 (SAE-guided safety patching)]

### 5.4 Cross-Paper Predictions
- **MPAR² prediction:** RL training should raise gc(L_late) or shift k* shallower
- **Modality Collapse prediction:** Tier 3 failure = mid-peak + late-drop gc profile
- **AudioSAEBench bridge:** gc at feature level (Paper B) = micro-scale of gc at layer level (this paper)
- [TODO: If falsified, what does it mean?]

### 5.5 Limitations
- Mock experiments validate framework logic but not real neural network behavior
- Q001/Q002 on Whisper-base show partial results; larger models needed
- [TODO: GPU access blocker for full LALM experiments]
- Codec stratification (D5) and collapse onset (D4) deferred to Paper B scope

### 5.6 Future Work
- Paper B: D4 + D5 on Whisper + Qwen2-Audio; AudioSAEBench evaluation
- Feature-level gc (AudioSAEBench) as micro-scale complement
- Audio T-SAE (temporal coherence as gc proxy)
- Cross-lingual gc: do phonological vectors survive connector across languages?

---

## 6. Conclusion
- [TODO: 1 paragraph summary of contributions]
- [TODO: 1 sentence on broadest implication — "mechanistic understanding of when ALMs listen vs. guess"]

---

## Appendix: Experiments → Claims Mapping

| Experiment | ID | Type | Key Result | Supports Claim |
|---|---|---|---|---|
| Voicing vector geometry | Q001 | Real | Layer 5 peak cos_sim=0.155 | §4.1: linear phonological structure in Whisper |
| Causal contribution (ablation) | Q002 | Real | All layers critical, WER=1.0 | §4.2: distributed encoding, no redundant layers |
| AND/OR gc patching | Q089 | Mock | AND% × gc r=0.9836, peak L3 | §4.3–4.4: gc peak localization, AND-gate = gc proxy |
| Persona gc benchmark | Q039 | Mock | Anti-ground shifts 2 layers, H2+H3 ✅ | §4.5: persona-conditioned grounding |
| gc incrimination | Q069 | Mock | t* detection: 3 degradation types | §4.6: collapse onset detection |
| SAE incrimination patrol | Q078 | Mock | 96% suppression detection, 4 offenders | §4.6: two-level attribution |
| MicroGPT RAVEL | Q053 | Mock | 5/6 pass, speaker_gender disentangled | §4.7: attribute disentanglement |
| Cascade degree | Q113 | Mock | 1-α_AND validates override vulnerability | §4.4: AND/OR gate validation |
| FAD bias × gc | Q096 | Mock | r = −0.96 | §4.4: FAD bias inversely tracks gc |
| RAVEL × gc proxy | Q107 | Mock | r = 0.87 | §4.7: RAVEL isolation as gc proxy |
| Codec OR-gate | Q109+ | Mock | r = −0.90 | §3.3.3: codec degrades AND-gate → OR-gate |
| Persona × gate type | Q091 | Mock | Gate-type shifts with persona | §4.5: persona affects AND/OR distribution |
| Schelling × gate | Q092 | Mock | AND-gate features more stable across seeds | §3.3.1: Schelling stability validation |
| Collapse × gate | Q093 | Mock | AND-gates collapse later than OR-gates | §4.6: gate type predicts collapse resilience |
| T-SAE × gc incrimination | Q094 | Mock | Temporal coherence correlates with gc | §5.6: T-SAE as gc proxy (future work) |
| Hallucination × gc | Q110 | Mock | gc predicts hallucination onset | §4.8: gc as hallucination predictor |
| Backdoor = cascade induction | Q116 | Mock | Backdoor shifts t* leftward | §5.3: safety — backdoor detection via gc |
| GSAE density | Q117 | Mock | **BLOCKED** — density too weak | §4.9: negative result |
| FAD-RAVEL direction | Q123 | Mock | **BLOCKED** — sign reversed | §4.9: negative result |

> **Total: 2 real + 20 mock (18 pass, 2 blocked)**

---

## Figure Plan

| Figure | Content | Source |
|--------|---------|--------|
| Fig 1 | gc(k) curve across layers (Whisper) | [TODO: real gc_eval.py output] |
| Fig 2 | Causal patching effect vs. layer depth | [TODO: Q001/Q002 extension] |
| Fig 3 | AND/OR gate distribution across layers | Q089 mock → [TODO: real] |
| Fig 4 | 5D Listening Geometry radar chart (strong listener vs. guesser) | §3.4 taxonomy |
| Fig 5 | 3-Tier diagnostic tree flowchart | §3.6 |
| Fig 6 | Persona-conditioned gc shift | Q039 mock → [TODO: real] |
| Table 1 | gc(k) by layer | [TODO: real data] |
| Table 2 | Experiments → claims mapping | Appendix (above) |
| Table 3 | 3-Tier taxonomy signatures | §3.6 |

---

## Key [TODO] Items

1. **GPU access** — Full LALM experiments (Qwen2-Audio) blocked on NDIF/戰艦
2. **Whisper-small/medium replication** — Q001 voicing geometry needs larger model
3. **Real gc(k) sweep** — Priority 1 experiment (IIT Triple Convergence test)
4. **ALME conflict analysis** — Pre-registered predictions P1-P4 await execution
5. **Q117/Q123 diagnosis** — Blocked experiments need root-cause analysis
6. **Abstract finalization** — Needs real empirical headline result
7. **Paper A vs B split** — D4+D5 deferred to Paper B; confirm boundary is clean
