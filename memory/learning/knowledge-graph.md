# 🗺️ Knowledge Graph

> 概念、論文、連結。Paper ideas 見 goals.md（single source of truth）。
> Last updated: 2026-02-26 17:00 (cycle #7: AudioLens deep read)

## Mech Interp × Speech/Audio — Field Map (2026)

### A) ASR / Whisper MI
- Ellena Reid (2023, LessWrong) — 早期 Whisper MI，phoneme-like features, localized attention
- **Glazer et al. "Beyond Transcription" (2025, aiOla)** — 🟢 DEEP READ — logit lens + probing + activation patching for Whisper-large-v3 + Qwen2-Audio [arXiv:2508.15882]
  - KEY METHODS: Encoder Lens (novel), saturation layer, white-noise reference patching
  - KEY FINDINGS: encoder encodes context (not just acoustics!), hallucination detectable from decoder residual stream (93.4% acc at layer 22), repetition = specific cross-attn heads
  - Speaker gender probing peaks layer 25 (94.6%), accent peaks layer 22 (97%), noise peaks layer 27 (90%)
  - DIRECT LINK to Track 3 (Listen vs Guess): saturation layer + patching sensitivity → operationalize grounding coefficient
- Mozilla Builders (2024) — Whisper SAE (L1, TopK), phonetic/positional features
- Open tools: whisper-interp (GitHub), whisper_logit_lens (GitHub)

### B) Speech Encoder SAEs
- **Mariotte et al. "Sparse Autoencoders Make Audio Foundation Models more Explainable" (Sep 2025, ICASSP 2026)** — 🟢 DEEP READ (cycle #27) [arXiv:2509.24793]
  - Models: AST (sound), HuBERT (speech), WavLM (speech), MERT (music) — 4 models, 13 layers each, D=768
  - SAE: TopK, N=2048 (8x expansion), per-layer on VocalSet (singing technique classification, 10 classes)
  - KEY FINDING 1 (layer info): Speech SSL peaks EARLY for acoustic tasks — HuBERT layer 3 (73%), WavLM layer 1 (72.5%); DROPS at layer 12 (55-60%). Contrast: AST stable across all layers.
  - KEY FINDING 2 (SAE): SAE sparse codes retain task accuracy (on par with dense probes at 75-85% sparsity)
  - KEY FINDING 3 (disentanglement): SAEs significantly improve COMPLETENESS — voice attributes (pitch, shimmer, loudness, spectral rolloff, HNR) are more independently encoded in sparse codes than in dense hidden states
  - KEY LIMITATION: **Mean-pooled along time axis** → NO temporal information → can't ask "when during utterance does feature fire?"
  - KEY GAP #12 (NEW): **Temporally-resolved SAE for audio** — nobody has done this. Mariotte loses time; AudioSAE has frame-level but doesn't analyze temporal patterns systematically. Knowing WHEN a sparse feature activates = direct connection to "Listen vs Guess" (which audio positions are causally critical?)
  - CODE: https://github.com/theomariotte/sae_audio_ssl
  - COMPARISON: Narrower than AudioSAE (single task, no causal steering), but 4 models vs AudioSAE's 2; disentanglement evaluated with completeness metric (AudioSAE doesn't use this)
  - LINK: 3 audio SAE papers now exist (AudioSAE + Mariotte + Plantinga-PD) → enough for AudioSAEBench meta-evaluation

- **Kawamura et al. "What Do Neurons Listen To?" (Feb 2026, EUSIPCO 2026)** — 🟢 DEEP READ (cycle #26) [arXiv:2602.15307]
  - Model: M2D (Masked Modeling Duo) ViT-SSL, 12 layers × 3072 neurons. Compared with supervised ViT baseline.
  - METHOD: AAPE (Audio Activation Probability Entropy) — adapts LAPE from NLP to audio. Three-step filter: activation rate → entropy selectivity → top class-specific activation probability.
  - KEY FINDING 1 (RQ1): SSL achieves ~100% class coverage across ALL unseen tasks. SL only 49% for VoxCeleb1. SSL develops 2x more class-specific neurons → generalization has mechanistic basis.
  - KEY FINDING 2 (RQ2): Neurons encode gender (cross-dataset VC1↔CREMA-D), pitch (Surge↔NSynth octave), arousal (ANG+HAP cluster), language family (Germanic vs Romance), genre acoustic similarity (classical+jazz)
  - KEY FINDING 3 (RQ3): Deactivating class-specific neurons significantly degrades classification > random deactivation → neurons causally necessary (necessity test / noising patching)
  - POLYSEMANTICITY: "shared responses" = same neuron fires for acoustically/semantically related classes = polysemanticity → SAE would disentangle → Track 2 (AudioSAEBench) connection
  - GAP: No SAE decomposition; no denoising (sufficiency) patching; no audio-vs-text pathway test (model is encoder-only SSL, so no text pathway — but this gap opens up in LALMs)
  - NEW GAP #11: In LALMs (Qwen2.5-Omni etc.), the same class-specific neuron (emotion/gender) could activate from audio cues OR text context — grounding_coefficient at neuron level = unanswered question
  - EXPERIMENT SKETCH: AAPE on LALM → find emotion/gender neurons → test grounding_coefficient via audio+text patching → "Class-specific Neuron Grounding" paper contribution (needs Leo approval)
  - CONVERGENCE WITH ZHAO et al. 2601.03115: Both find specialized neurons (ESNs for emotion in Zhao; class-specific neurons in Kawamura); both stop at necessity; neither does audio-vs-text pathway test → Leo can close both gaps in one paper

- **AudioSAE (Aparin et al., 2026, EACL)** — 🟢 DEEP READ — SAE on all 12 layers of Whisper/HuBERT [arXiv:2602.05027]
  - KEY SETUP: TopK/BatchTopK SAE, 8x expansion (768→6144 features), all-layer coverage
  - KEY FINDINGS: >50% feature stability across seeds; phoneme acc 0.92/0.89; **70% hallucination FPR reduction via top-100 feature steering** (α=1, WER cost only +0.4%)
  - LAYER INSIGHT: Whisper layer 6-7 = transition from audio-level → frame-level speech encoding
  - SPEECH ≠ TEXT: erasing speech concepts needs ~2000 features; text SAE needs only ~tens → phonetic info is distributed
  - EEG correlation: SAE features align with brain activity during speech perception (Pz electrode, 0-500ms lags)
  - KEY GAP: only encoder models; no LALMs; phonetic auto-interpretation failed (bad caption model)
  - CODE: https://github.com/audiosae/audiosae_demo
- Parra et al. (2025, EMNLP) — interpretable sparse features for SSL speech models
- SAE on speaker embeddings (Titanet) — monosemantic factors [arXiv:2502.00127]

### C) Audio-Language Models（最接近 Leo）
- **🔥 AudioLens (Neo Ho, Yi-Jyun Lee, Hung-yi Lee 2025, NTU → ASRU 2025)** — 🟢 DEEP READ — logit-lens on LALMs (DeSTA2, Qwen-Audio, Qwen2-Audio); auditory attribute perception [arXiv:2506.05140]
  - KEY METHODS: Layer-wise Information Score (= layer accuracy via vocab projection), Critical Layer (weighted avg layer index above threshold), 3 prompt formats
  - KEY FINDINGS:
    - Attribute info ≠ monotonic with depth; sharp drops+recoveries common
    - Success mode = info rises with depth; Failure mode = peaks mid-layer then drops
    - Earlier critical layer → better accuracy (more layers to refine)
    - **LALMs query audio tokens directly >> aggregate at text positions** (= "listen not guess")
    - No-training improvement: enrich deep layers with early attribute-rich reps → +16.3% acc
  - CRITICAL GAP: only Logit Lens (observational), NO causal patching → cannot prove causal grounding
  - DIRECT LINK: operationalizes "Listen vs Guess" (Track 3); Leo can extend with causal interventions
  - NOTE: 智凱哥 = Chih-Kai Yang (ckyang1124), GitHub: https://github.com/ckyang1124/AudioLens
  - CROSS-PAPER: critical layer ↔ saturation layer (Beyond Transcription); potential unified framework
- Beyond Transcription 也涵蓋 Qwen2-Audio
- **🟢 SPIRIT (Djanibekov et al., EMNLP 2025, MBZUAI)** — 🟢 DEEP READ — activation patching for audio jailbreak defense [arXiv:2505.13541]
  - KEY SETUP: PGD attack on Qwen2-Audio + LLaMa-Omni (both share Whisper encoder); AdvBench 246 samples
  - KEY FINDINGS: PGD achieves 100% ASR in some categories; activation patching (inject clean activations) reduces to ~1% with negligible utility cost; bias addition and neuron pruning also effective
  - BEST DEFENSE: patch at critical encoder-output/early-LM layers (found empirically, not mechanistically)
  - KEY GAP: no explanation of *where* adversarial signal lives; no SAE-guided patching
  - CODE: https://github.com/mbzuai-nlp/spirit-breaking
  - LEO'S OPPORTUNITY: AudioSAE features → surgically suppress adversarial features vs SPIRIT's blind layer patching

### C.1) Emotion-Sensitive Neurons in LALMs (New — Cycle #24/25)
- **Zhao, Schuller, Sisman "Discovering and Causally Validating Emotion-Sensitive Neurons in LALMs" (Jan 2026)** — 🟢 DEEP READ (Cycle #25) [arXiv:2601.03115]
  - Authors: JHU CLSP + Imperial College London GLAM; 16 pages, 6 figures
  - Models: Qwen2.5-Omni-7B, Kimi-Audio, Audio Flamingo 3; Benchmarks: IEMOCAP, MELD, MSP-Podcast
  - KEY METHODS: 
    - Attach hooks to **decoder MLP SwiGLU gates** (g = SiLU(u)); log on *correctly solved* items only
    - 4 selectors: LAP (freq), LAPE (entropy), MAD (magnitude contrastive), CAS (top-margin)
    - Interventions: Deactivation (zero mask = necessity test) + Steering (gain 1+α = controllability test)
    - 3 agnostic injection strategies (label-free): 2-Pass, Mix, Union
  - KEY FINDINGS:
    1. ESNs causally validated: self-deactivation >> cross-deactivation consistently across 3 models/3 datasets
    2. **Selector matters**: MAD/CAS >> LAP/LAPE for causal specificity
    3. **Layer clustering**: ESNs non-uniformly distributed — early (layer 0), early-mid (6-8), late (19-22)
       → **Matches Triple Convergence Hypothesis** (acoustic→semantic transition at mid layers)
    4. Steering works: amplifying ESNs biases predictions toward target emotion (dose-response)
    5. ESNs interact non-additively (agnostic injection weaker than targeted) → polysemanticity issue
    6. Partial cross-dataset transfer: asymmetric, emotion-category-dependent
  - **CRITICAL GAP** (= Track 3): Instruments decoder only; NEVER asks "does ESN fire because of audio or text input?"
    - grounding_coefficient applied at neuron level = unique contribution Leo can make
    - Method: find ESNs (Zhao) → for each cluster → patch audio vs patch text → gc per ESN cluster
  - **NEW SYNTHESIS**: ESN non-additivity → SAE would decompose into monosemantic emotion features → Track 2+3 intersection
    - "ESNs via SAE features" = cleaner causal unit than individual polysemantic neurons
  - LEO'S OPPORTUNITY: 2 new paper ideas — (1) grounding_coefficient at ESN level, (2) ESN discovery via AudioSAE features

### C.2) LoRA Mechanistic Interpretability (Speech)
- **"Behind the Scenes" (Ma et al., ICASSP 2026, 2509.08454)** — 🟢 DEEP READ (Cycle #16) — MI of LoRA-adapted Whisper for SER
  - KEY SETUP: Whisper-large-v2 + IEMOCAP 4-class SER; NNsight library; probing + logit-lens + CKA + SVD
  - KEY FINDING 1: **Delayed Specialization** — LoRA flat/high KL in early layers, then sharp late-stage commitment at top layers. Frozen encoder = volatile/unstable emotion representation. LoRA resolves representational conflict ASR→SER
  - KEY FINDING 2: **Forward Alignment, Backward Differentiation** — A matrix aligns with input features, B matrix differentiates for task. Deep layers: negative cosine similarity = "corrective/subtractive" signals suppress ASR-irrelevant features
  - KEY FINDING 3: LoRA creates new representational clusters (CKA) that align with our Triple Convergence transition zone
  - KEY GAP: No causal patching → cannot prove which LoRA components are causally necessary vs sufficient
  - CODE: https://github.com/harryporry77/Behind-the-Scenes
  - LEO'S OPPORTUNITY: Add patching to "Behind the Scenes" methodology → causally identify which LoRA layers matter → combine with AudioLens (Track 3 + Track 4 = one paper)
  - NEW TOOL: NNsight library — alternative to pyvene for Whisper encoder access; check API

### D) Generative Audio/Music MI
- SMITIN (2024), Facchiano (2025), TADA! (2026) — attention steering, SAE for music concepts
- TADA!: 少數 attention layers 控制 semantic concepts [arXiv:2602.11910]

### E) Brain-to-Speech
- Maghsoudi & Mishra (2026) — cross-mode patching, causal scrubbing [arXiv:2602.01247]

### F) Neural Audio Codecs（新角度）
- EnCodec → discrete tokens → 讓 audio MI 變成「LM-like」
- AudioLM, MusicGen/AudioGen 都基於 codec tokens
- MI 意義：token-level patching, SAE on residual stream 直接可用
- 目前 MI 研究幾乎空白

## 核心方法工具箱
→ 詳見 `skills/autodidact/references/toolbox.md`

## 🔗 Cross-Paper Connections (emerging picture)

| Concept A | Paper A | ↔ | Concept B | Paper B | Insight |
|-----------|---------|---|-----------|---------|---------|
| Saturation layer (encoder) | Beyond Transcription | ↔ | Critical layer (LALM) | AudioLens | Both = "where attribute resolves" — unify into shared framework? |
| Encoder encodes context | Beyond Transcription | ↔ | LALMs query audio directly | AudioLens | Two views of same phenomenon: audio pathway carries semantic context |
| Patching shows causal grounding | Beyond Transcription | ↔ | Logit Lens = only observational | AudioLens | **Gap = Leo's opportunity**: add causality to AudioLens framework |
| Hallucination in decoder residual | Beyond Transcription | ↔ | Failure = mid-layer peak then drop | AudioLens | Same failure signature? Check if AudioLens failure cases = hallucinations |

### Research Opportunity Crystallized (2026-02-26)
> **"Causal AudioLens"**: Take AudioLens methodology (Logit Lens + critical layer) → add patching experiments → produce grounding_coefficient = ratio of (Δacc when audio patched) / (Δacc when text patched). This is the missing causal link in AudioLens, and it directly operationalizes Track 3 "Listen vs Guess" hypothesis.

### New Synthesis Insight — Three Papers, One Phenomenon (2026-02-26 Cycle #8)
> **Whisper layers 6-7 = semantic-acoustic transition zone**:
> - AudioSAE: audio-level speech peaks layer 6, then drops → frame-level peaks layer 7 (phonetic encoding transition)
> - Beyond Transcription: "saturation layer" = where encoder commits to transcription
> - AudioLens: "critical layer" = where attribute resolves in LALM
> **Hypothesis**: All three independently found the same architectural transition point from different methodological angles. Testing this directly (SAE + saturation layer + critical layer on same model) = tractable experiment on MacBook.

### 🧪 Experiment 0: Triple Convergence Test (Cycle #11 crystallized — 2026-02-26)

**Q:** Do AudioSAE layer 6-7 transition, Beyond Transcription saturation layer, and AudioLens critical layer point to the *same* architectural feature in Whisper?

**Setup (MacBook-feasible, Whisper-tiny or small):**
1. **Saturation layer**: Run Encoder Lens on Whisper encoder — find the layer where logit lens output stabilizes (= saturation layer from Beyond Transcription). Expected: ~layer 6-7 for small model.
2. **Norm/CKA jump**: Use `whisper_hook_demo.py` — look for the layer where CKA similarity to final layer jumps (= representation converges). Expected: ~layer 6-7.
3. **Feature stability**: If SAE trained: compare feature stability profile per layer (from AudioSAE paper, Fig. 3). Not immediately runnable without SAE training, but CKA can proxy it.
4. **Claim**: If all three methods point to the same transition zone → strong evidence for a universal "semantic crystallization layer" in Whisper encoder.

**Minimal viable version (no SAE training needed):**
- `whisper_hook_demo.py` already captures layer norms + CKA
- Add: logit-lens decoder vocab projection at each layer (requires decoder embedding matrix)
- Result: saturation curve + CKA curve on same plot → visual test of convergence hypothesis

**Impact if confirmed:**
- Novel empirical finding (all prior papers used different models/methods)
- Directly supports "Causal AudioLens" paper: "first experiment" section
- Conference-quality if extended to multiple models (Whisper variants + HuBERT)

**Next step:** Extend `whisper_hook_demo.py` to include logit-lens projection → run → see if CKA jump and saturation layer coincide. ~2-3 hours coding.

| Concept A | Paper A | ↔ | Concept B | Paper B | New Connection |
|-----------|---------|---|-----------|---------|----------------|
| Layer 6-7 speech transition | AudioSAE | ↔ | Saturation layer | Beyond Transcription | Same phenomenon? |
| Layer 6-7 frame-level encoding | AudioSAE | ↔ | Critical layer | AudioLens | Three papers converge |
| Steering pipeline (suppress top-100) | AudioSAE | ↔ | White-noise patching | Beyond Transcription | Causal intervention templates |
| Speech concepts = distributed (2000 feat) | AudioSAE | ↔ | Encoder encodes context | Beyond Transcription | Distributed = context-sensitive |
| SAE feature steering (AudioSAE) | AudioSAE | ↔ | Blind activation patching (SPIRIT) | SPIRIT | **Gap → SAE-guided safety patching**: know WHICH features to suppress (not just which layers) |
| 70% hallucination FPR reduction | AudioSAE | ↔ | 99% jailbreak defense | SPIRIT | Both use sparse activation intervention; sparse+interpretable (SAE) > dense (SPIRIT) |
| Triple Convergence layer 3 (Whisper-base) | whisper_hook_demo | ↔ | Best defense = specific layer patching | SPIRIT | Does SPIRIT's optimal defense layer = Triple Convergence transition zone? |
| Delayed specialization (LoRA commits at deep layers) | Behind the Scenes | ↔ | Critical layer (attribute resolves at specific depth) | AudioLens | LoRA's late commitment = mechanistic explanation for critical layer behavior? |
| Counter-directional corrective signals in deep layers | Behind the Scenes | ↔ | Saturation layer (encoder commits to transcription) | Beyond Transcription | Both = "where the model decides" — unified by suppression mechanism |
| No causal patching | Behind the Scenes | ↔ | No causal patching | AudioLens | **Same gap in both papers → Leo can add patching to BOTH simultaneously** |
| Emotion-sensitive neurons (ESNs) causally ablatable | Zhao 2601.03115 | ↔ | LALMs query audio tokens directly | AudioLens | **New question: are ESNs driven by audio stream or text context?** → patching experiment needed |
| Neuron-level class-specific units | Kawamura 2602.15307 | ↔ | Polysemanticity in audio features | AudioSAE | Same phenomenon at different granularity → SAE = principled disentanglement of neuron polysemanticity |
| SAE enhances vocal attribute disentanglement | Mariotte 2509.24793 | ↔ | SAE for speech features (all layers) | AudioSAE | Two SAE papers, no comparison/evaluation → Track 2 AudioSAEBench fills this gap |

### 🧪 Experiment 1: Triple Convergence IIT Test (Cycle #34 proposal — 2026-02-27)

**Q:** Is the Whisper semantic crystallization layer (Triple Convergence) the same architectural location predicted by IIT theory as the peak causal abstraction point?

**Formal framing (Geiger et al. 2301.04709):**  
IIT accuracy should peak at the layer where the representation best *causally explains* the output. If Triple Convergence (~50% depth) = the causal abstraction layer, then interchange interventions at that layer should show highest IIT accuracy.

**Setup (MacBook-feasible, ~3h, NNsight + Whisper-small):**
1. Choose minimal pairs: same speaker, same duration, one attribute differs (e.g., accent A vs accent B; emotion A vs emotion B)
2. Run denoising patching: patch layer L activations from clean input into corrupt input → measure Δacc
3. Sweep all layers: find layer L* where Δacc is maximized (= highest causal sufficiency)
4. Test: Does L* ≈ layer 3 in Whisper-base (Triple Convergence zone)?
5. Compare: Do all three metrics converge at L*? (norm jump, CKA transition, logit lens saturation)

**Prediction:** IIT peak at ~50% depth (layer 3 in base, layer 6-7 in large) = causal abstraction theory predicts our empirically found transition zone.

**Impact if confirmed:**  
- First paper to apply causal abstraction formalism to speech encoder
- "Experiment 1" in "Causal AudioLens" paper
- Sets up grounding_coefficient as IIT-grounded metric (not ad hoc)

**Tools needed:** NNsight (for intervention), whisper_hook_demo.py (for CKA/norm baseline), real speech minimal pairs (.wav files)
**Prerequisite:** Leo approval + real speech file + `pip install nnsight openai-whisper` in venv

---

### I) Gap #13: EmoOmni / Thinker-Talker Emotional Bottleneck (Cycle #30 — 2026-02-27)

**Paper:** EmoOmni (ICML 2026 — arXiv scanned cycle #30)
**Architecture:** Thinker-Talker dual-module design: Thinker = speech encoder → Talker = LM
**Finding:** EmoOmni diagnoses emotion loss *behaviorally* — model performs poorly on emotion tasks
**Gap #13 (NEW):** Nobody has mapped *where* in the Thinker-Talker architecture emotional information is lost mechanistically
  - Is it the connector (bottleneck between encoder and LM)?
  - Early layers of the Thinker?
  - Early layers of the Talker after cross-attention?
**Leo's opportunity:** Apply logit-lens + causal patching at Thinker-Talker interface → mechanistically diagnose which boundary loses emotion signal
**Method:** Same as "Causal AudioLens" but applied to emotion attribute at the connector bottleneck
**Links:** Extends Track 3 (Listen vs Guess) + Track 5 (Safety / Emotion robustness)
**Priority:** Lower than Tracks 1-4; useful as supporting study or extension

### H) Crystallized Paper Opportunities (updated 2026-02-27)

1. **"Causal AudioLens"** (Track 3 anchor): AudioLens logit-lens + causal activation patching → grounding_coefficient. First paper with causal claims in LALM audio grounding. Co-author with 智凱哥.

2. **"SAE-guided Inference-time Safety Patching"** (Track 5): AudioSAE feature suppression → replace SPIRIT's blind layer patching with interpretable feature-level patching. More surgical, more mechanistic.

3. **"Causal AudioLens + LoRA"** (Track 3+4 combined): Both AudioLens and "Behind the Scenes" lack causal patching. One paper can add patching to BOTH — LALM grounding AND LoRA adaptation mechanism. Unified causal contribution.

4. **"Audio Minimal Pairs Patching Protocol"** (Track 1 methodological): Heimersheim & Nanda validates all prior audio MI uses suboptimal corruptions (white noise). Minimal pair audio corruptions (same speaker/duration/content structure, different target attribute) = cleaner causal evidence. Methodological improvement claim → benchmark paper.

5. **"Class-specific Neuron Grounding in LALMs"** (Track 2+3 intersection): Kawamura + Zhao both find class-specific neurons but never ask "is this neuron driven by audio or text?" Apply grounding_coefficient at ESN/class-specific neuron level. Closes the same gap two different papers left open simultaneously.

6. **"Temporally-resolved Audio SAE"** (Track 2 — AudioSAEBench extension): Mariotte mean-pools along time → loses temporal info. Nobody has asked "when during an utterance does each sparse feature activate?" Temporal SAE = direct connection to "Listen vs Guess" (which positions are causally critical?). Novel contribution to AudioSAEBench.

### G) Activation Patching Methodology
- **Heimersheim & Nanda (2024)** — 🟢 DEEP READ — "How to Use and Interpret Activation Patching" [arXiv:2404.15255]
  - KEY DISTINCTION: Denoising (clean→corrupt) tests SUFFICIENCY; Noising (corrupt→clean) tests NECESSITY — NOT symmetric!
  - AND circuits: use noising (finds all components); OR circuits: use denoising
  - METRICS hierarchy: logit diff > logprob > probability > accuracy (for exploratory patching)
  - ⚠️ Gaussian noise patching (Causal Tracing) is fragile — sensitive to noise level, can be ineffective
  - ⚠️ Backup behavior (Hydra effect): ablating key component activates backup → component looks less important than it is
  - Path patching: isolates direct A→B connections, needed for confirmatory circuit verification
  - AUDIO IMPLICATION: Beyond Transcription's white-noise patching = suboptimal corruption; minimal pair audio = cleaner evidence
  - NEW GAP (Leo): all audio MI papers use suboptimal corruptions — minimal pairs would be methodologically cleaner and more publishable

---

## 關鍵研究者/團隊
- **NTU 李宏毅 lab** — AudioLens (智凱哥！Leo 主場)
- aiOla Research (Glazer) — ASR MI, hallucination causal analysis
- Huawei Noah's Ark (Aparin) — AudioSAE
- MBZUAI — SPIRIT (audio safety)
- Stanford (Atticus Geiger) — causal abstraction theory + pyvene
- Neel Nanda — activation patching best practices, TransformerLens
- Mozilla Builders — Whisper SAE tooling
- Ellena Reid — early Whisper MI (LessWrong)
- Yuan Gong (MIT) — AST/SSAST audio transformers
