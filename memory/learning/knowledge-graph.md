# 🗺️ Knowledge Graph

> 概念、論文、連結。Paper ideas 見 goals.md（single source of truth）。
> Last updated: 2026-03-02 10:31 (cycle #166: staleness flag + Gap #21 anchor)
> ⚠️ STALE ALERT: Cycles #8-165 (~150 cycles of discoveries) are NOT reflected here.
> Full state in: goals.md (gaps #1-21, paper ideas, must-read list), progress.md (all cycle logs), experiment-queue.md.
> Recent major additions missing from graph: Choi et al. phonological arithmetic, DAS/IIT method, T-SAE idea, Modality Collapse paper, AudioSAEBench analysis, Gap #21 (codec causal patching).
> TODO (Leo-gated): decide if deep knowledge-graph refresh is worth ~2 cycles.

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

- **Choi et al. 2602.18899 "Phonological Vector Arithmetic in S3Ms"** (Feb 2026, ACL submission) — 🟢 DEEP-SCAN (cycle #81)
  - 96 languages, multiple S3Ms (HuBERT/WavLM/wav2vec 2.0)
  - KEY FINDING: phonological features are LINEAR, COMPOSITIONAL, and SCALE-CONTINUOUS in S3M space
  - Arithmetic: [b] = [d] - [t] + [p] (voicing vector = linear, subtracts/adds cleanly)
  - Magnitude scales with acoustic realization degree (partially voiced = intermediate position)
  - Cross-lingual: phonological vectors universal across 96 languages
  - Code: github.com/juice500ml/phonetic-arithmetic
  - CONNECTIONS: (1) Validates TCS(F) metric (Paper B AudioSAEBench) — phoneme boundaries are geometrically well-defined; (2) Provides stimuli design blueprint for minimal-pair audio patching (phonological contrast pairs = principled "clean/corrupt" construction); (3) Motivates Audio T-SAE (Idea #7) — phonological features are linear = SAE-learnable; (4) Suggests cross-lingual feature alignment evaluation axis for AudioSAEBench
  - **NEW GAP #18**: Phonological vector geometry shown in S3M encoder — does it SURVIVE through the connector into speech LLMs? Nobody has tested. If connector destroys phonological linearity → connector = bottleneck. Test: extract voicing_vector from S3M layer, project via connector with NNsight, test arithmetic in LLM layer 0.

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
- **T-SAE (Bhalla et al., Oct 2025, Harvard/MIT)** — 🟢 DEEP READ (cycle #71) — Temporal SAEs [arXiv:2511.05541]
  - **Venue: ICLR 2026 Oral** ⭐ — landmark paper; code: https://github.com/AI4LIFE-GROUP/temporal-saes
  - **Core problem**: Standard SAEs treat tokens as i.i.d. → recover token-specific, NOISY, LOCAL syntactic artifacts ("sentence ending", "capitalized first word") instead of HIGH-LEVEL semantic concepts.
  - **Key insight**: Language has two structure types: (1) high-level / global (semantic = "discussion of plant biology") — evolves SMOOTHLY over tokens; (2) low-level / local (syntactic = "plural noun") — specific to individual positions.
  - **Method**: Partition SAE features into high-level (20%) and low-level (80%), Matryoshka-style. Add **temporal contrastive loss** on high-level features between ADJACENT TOKENS `(z_t, z_{t-1})`. Positives = same sequence; negatives = different sequences. Prevents smoothness collapse.
  - **Loss**: `ℒ = ℒ_matryoshka + α*ℒ_contrastive`, α=1.0
  - **Key results**: T-SAE high-level features cluster by TOPIC and SEQUENCE IDENTITY; low-level features cluster by PART-OF-SPEECH (correctly disentangled); reconstruction quality maintained; safety case study: detects jailbreak concepts more reliably.
  - **Authors explicitly note**: limitation applies to "language *and other sequential modalities*" — pointing at audio without doing it.
  - **Audio transfer hypothesis**: Audio has STRONGER temporal structure than text:
    - Phoneme spans ~5-10 frames at 20ms → adjacent frames within phoneme should share high-level feature
    - T-SAE adjacent-token contrastive = PERFECT prior for phoneme-level feature discovery
    - Speaker identity / emotion / accent = long-range consistency → long-range contrastive variant
    - AudioSAE + Mariotte both have the i.i.d. token problem; T-SAE fixes it
  - **Experiment sketch (Audio T-SAE)**: Train on Whisper-small layer 3-5 activations (LibriSpeech). Contrastive pairs = (frame_t, frame_{t-1}) same utterance; negatives = different utterances. Hypothesis: high-level features should segment at phoneme boundaries; probe high-level for phoneme identity → should be better than standard SAE.
  - **NEW SYNTHESIS (cycle #71)**:
    - **New metric for AudioSAEBench**: `TCS(F)` = Temporal Coherence Score = within-phoneme variance / across-phoneme variance of feature F activations. T-SAE should score higher than standard SAE. Adds a SECOND novel metric to Paper B alongside `gc(F)` (Grounding Sensitivity).
    - **Triangulation for Paper A**: T-SAE temporal coherence as PROXY for audio vs text processing layer. If a layer's SAE features are coherent at PHONEME timescale → "listening"; if coherent at TEXT TOKEN timescale → "guessing". Non-causal validation complement to grounding_coefficient.
  - **Connection to Gap #12** (Mariotte loses temporal info via mean-pooling): T-SAE = direct methodological solution. Answers when each feature fires during utterance = direct proxy for "which audio positions causally matter."

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

### C.0) SAE-based Interpretability Framework for AudioLLMs (New — Cycle #37)
- **AR&D (Chowdhury et al., ICASSP 2026)** — 🟢 DEEP READ (cycle #37) [arXiv:2602.22253]
  - Authors: Townim Faisal Chowdhury et al., submitted Feb 24, 2026
  - Subtitle: "A Framework for Retrieving and Describing Concepts for Interpreting AudioLLMs"
  - Claims: **"First mechanistic interpretability framework for AudioLLMs"**
  - KEY METHOD (AR&D Pipeline):
    1. **Retrieve**: Find max-activating audio clips for each SAE feature
    2. **Describe**: Auto-caption those clips → assign concept names to features
    3. **Validate**: Human evaluation + steering (ablation/gain)
  - KEY FINDINGS: AudioLLMs encode structured, interpretable features; SAE disentangles polysemantic neurons into monosemantic features; auto-naming achieves high human agreement; steering confirms causality (necessity test)
  - MODEL TYPE: AudioLLMs (multimodal audio-text models, e.g., SALMONN, Qwen-Audio) — distinct from AudioSAE which only covers encoder-only models
  - KEY GAP 1: Only steering (necessity), no denoising patching (sufficiency) → cannot prove causal grounding
  - KEY GAP 2: **No audio-vs-text pathway test**: their SAE features are named with audio concepts, but nobody asks "does this feature activate from audio input or text context?" = Track 3 grounding_coefficient entirely untested
  - KEY GAP 3: Auto-captioner naming is noisy → minimal pair + patching = more rigorous labeling method
  - PROJECT: https://townim-faisal.github.io/AutoInterpret-AudioLLM/
  - LEO'S OPPORTUNITY: AR&D = "what features exist"; Leo's patching = "why they activate (audio vs text)". Complementary, not competing. Their SAE feature maps = useful baseline for Track 3 grounding_coefficient experiments.
  - FIELD STATUS (as of Feb 27): 4 papers now at AudioLLM level — AudioLens, SPIRIT, Zhao 2601.03115, AR&D — NONE do denoising patching. Leo still first.

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
| Layer-level gc (Listen Layer — which layer consults audio?) | Track 3 / Causal AudioLens | ↔ | Feature-level gc (AudioSAEBench — which SAE feature is audio-grounded?) | Track 2 / AudioSAEBench | **⭐ SAME METRIC at different granularity**: grounding_coefficient unifies both papers. Same stimuli (ALME), same IIT theory. Paper A validates macro; Paper B scales to micro. |

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

### J) SAEBench — Text SAE Evaluation Framework (Cycle #38)
- **SAEBench (Karvonen, Rager, Nanda et al., ICML 2025)** — 🟢 DEEP READ [arXiv:2503.09532]
  - 8-metric framework across 4 categories: Concept Detection, Interpretability, Reconstruction, Feature Disentanglement
  - **Key finding**: Proxy metrics (sparsity + fidelity) do NOT reliably predict practical quality
  - **Matryoshka SAE** underperforms on proxy metrics but WINS on feature disentanglement (grows with scale)
  - Feature Absorption = known failure mode (high sparsity ≠ monosemanticity)
  - 200+ SAEs benchmarked across 7 architectures
  - **GAP #15**: No equivalent benchmark for audio/speech SAEs → AudioSAEBench fills this gap
  - **Grounding Sensitivity metric (NOVEL)**: for each SAE feature, compute grounding_coefficient via minimal pair patching. Features with gc≈1 = audio-grounded; gc≈0 = context-driven. No text-SAE equivalent. Audio-native contribution.
  - CODE: github.com/adamkarvonen/SAEBench; Interactive: neuronpedia.org/sae-bench

### K) AudioSAEBench Protocol Design v0.1 (Cycle #54)

**Full protocol:** see `memory/learning/2026-02-28_cycle54.md`

**5 Evaluation Categories:**
1. **Acoustic Concept Detection** — feature-level concept F1 (time-resolved; LibriSpeech/ESC-50/VocalSet)
2. **Disentanglement / Completeness** — linear probe independence via Mariotte's completeness metric
3. **Reconstruction Fidelity** — `task_preservation_ratio` = WER/emotion-F1 with SAE vs without SAE
4. **Causal Controllability** — Cohen's d (ablation) + steering precision (gain); both necessity + controllability
5. **Grounding Sensitivity (NOVEL)** — `gc(F)` per feature via ALME minimal pairs (57K stimuli); grounding histogram

**Key comparison vs prior work:**

| Dimension | AudioSAE | Mariotte | AR&D | **AudioSAEBench** |
|-----------|----------|----------|------|-------------------|
| Multi-metric | ❌ | ❌ | ❌ | ✅ (5 categories) |
| Grounding Sensitivity | ❌ | ❌ | ❌ | ✅ **NOVEL** |
| Temporal resolution | partial | ❌ | ❌ | ✅ (per-timestep) |
| Causal controllability | ✅ | ❌ | ✅ | ✅ (both tests) |

**Models:** Whisper-base/small (MacBook-feasible) → Whisper-large-v3, HuBERT, WavLM → Qwen2-Audio-7B via NDIF
**Stimuli:** LibriSpeech + IEMOCAP + ESC-50 + VocalSet + ALME conflict pairs (arXiv:2602.11488)
**Title:** "AudioSAEBench: Multi-Metric Evaluation of SAEs for Speech and Audio Language Models"
**Venue:** NeurIPS 2026 Datasets & Benchmarks OR INTERSPEECH 2027
**Timing risk:** AR&D (Chowdhury et al.) has partial overlap → move fast on defining Grounding Sensitivity

**Grounding Sensitivity metric (NOVEL — KEY contribution):**
For feature F with concept C (e.g., "speaker emotion = sad"):
- Create minimal pair: (audio=C, text=neutral) vs (audio=neutral, text=C)
- `gc(F)` = act(audio=C, text=neutral) / [act(audio=C, text=neutral) + act(audio=neutral, text=C)]
- `gc=1.0` → pure audio grounding; `gc=0.0` → pure text prediction
- ALME 57K conflict stimuli = perfect off-the-shelf test set for this
- **No text-SAE benchmark has an equivalent metric** — audio-native unique contribution

**Connection to Listen Layer (Track 3):**
> Grounding Sensitivity at FEATURE level (AudioSAEBench) is the same metric as grounding_coefficient at LAYER level (Listen Layer / Causal AudioLens). Same theoretical foundation (IIT/Causal Abstraction), same stimuli (ALME), different granularity. Paper A validates the layer-level metric; Paper B scales it to features. Run Paper A first.

**Collaboration opportunities:**
- AR&D authors (concept labeling pipeline) — potential co-author for Category 1
- AudioSAE authors (Aparin et al.) — baseline SAE infrastructure

### H) Crystallized Paper Opportunities (updated 2026-02-28)

**⭐ RECOMMENDED EXECUTION ORDER (cycle #55 synthesis):**
> Paper A (Track 3, fast) → Paper B (Track 2, community resource)  
> Reason: Paper A's grounding_coefficient IS Paper B's Category 5 (Grounding Sensitivity). Validate at layer level first; scale to feature level second.

1. **"Localizing the Listen Layer in Speech LLMs"** ⭐ (Track 3 anchor, EXECUTE FIRST)
   - AudioLens logit-lens + causal activation patching → layer-level grounding_coefficient
   - Use ALME conflict stimuli (57K pairs, already built) — no need to generate own stimuli
   - Find layer L* where audio causal contribution peaks = "Listen Layer"
   - First paper with causal claims in LALM audio grounding
   - Co-author with 智凱哥; ~3h MacBook experiment to start
   - **Previous title candidate**: "Causal AudioLens"

2. **"AudioSAEBench: Multi-Metric Evaluation of SAEs for Speech and Audio LMs"** ⭐ (Track 2, EXECUTE SECOND)
   - Full protocol in KG section K; 5-category benchmark (Grounding Sensitivity = NOVEL)
   - Builds on Paper A's validated grounding_coefficient method (scales to feature level)
   - Larger scope: multiple SAE baselines + GPU for Qwen2-Audio
   - Venue: NeurIPS 2026 D&B or INTERSPEECH 2027

3. **"SAE-guided Inference-time Safety Patching"** (Track 5): AudioSAE feature suppression → replace SPIRIT's blind layer patching with interpretable feature-level patching. More surgical, more mechanistic.

4. **"Causal AudioLens + LoRA"** (Track 3+4 combined): Both AudioLens and "Behind the Scenes" lack causal patching. One paper can add patching to BOTH — LALM grounding AND LoRA adaptation mechanism. Unified causal contribution.

5. **"Class-specific Neuron Grounding in LALMs"** (Track 2+3 intersection): Kawamura + Zhao both find class-specific neurons but never ask "is this neuron driven by audio or text?" Apply grounding_coefficient at ESN/class-specific neuron level. Closes the same gap two different papers left open simultaneously.

6. **"Temporally-resolved Audio SAE"** (Track 2 — AudioSAEBench extension): Mariotte mean-pools along time → loses temporal info. Nobody has asked "when during an utterance does each sparse feature activate?" Temporal SAE = direct connection to "Listen vs Guess" (which positions are causally critical?). Novel contribution to AudioSAEBench.
   - **Methodology found (cycle #70)**: Bhalla et al. "Temporal SAEs" (arXiv:2511.05541, Harvard/MIT, Oct 2025) — T-SAE adds contrastive loss on adjacent tokens to enforce temporal smoothness → recovers semantic concepts without supervision. Audio has STRONGER temporal structure than text (phoneme durations are fixed; formants smooth within phoneme, change at boundaries). T-SAE should work better on audio than text. Direct method backbone for this paper idea.

### F2) Neural Audio Codec Interpretability

- **Sadok, Hauret, Bavu "Bringing Interpretability to Neural Audio Codecs"** (Grenoble Alpes / CNAM / ISL, **Interspeech 2025**) — 🟢 SCAN (cycle #162) [arXiv:2506.04492]
  - **Models analyzed:** DAC, SpeechTokenizer, Mimi, BigCodec — 4 RVQ-based codecs
  - **Method (2-stage):**
    1. *Analysis*: Pretrained AnCoGen-Melspectrogram probes codec tokens → maps where content/identity/pitch are encoded in RVQ layers
    2. *Synthesis*: AnCoGen-Codec plugins trained on DAC + Mimi → direct attribute↔token prediction + manipulation
  - **KEY FINDING**: SpeechTokenizer (only codec with explicit disentanglement via HuBERT teacher) → RVQ layer 1 = phonetic content; layers 2+ = acoustic attributes (timbre, prosody). DAC/Mimi have emergent/implicit structure.
  - **METHOD LIMITATION**: Probe-based only — no causal patching. AnCoGen finds *correlational* attribute-token mappings; causal necessity not tested.
  - **CONNECTIONS TO LEO'S WORK:**
    - Q9 (codec codebook division): This paper directly answers for 4 codecs via probing. SpeechTokenizer layer 1 = content, layers 2+ = acoustic — use this as design blueprint for Track 1 "clean/corrupt" codec corruption protocols.
    - Track 1 (Audio IOI Causal Benchmark): Codec token corruption = cleaner/more principled clean/corrupt signal than white-noise patching (Heimersheim & Nanda Gap). Corrupt only RVQ layers 2+ (speaker) while preserving layer 1 (content).
    - Paper B (AudioSAEBench): RVQ layer partitioning = natural scaffold for Category 1 (Acoustic Concept Detection). SpeechTokenizer's designed disentanglement = validation baseline for SAE-discovered features.
    - Paek et al. cycle #80: Paek = SAE on generation codecs (EnCodec/DiffRhythm). Sadok et al. = probe-based analysis of 4 comprehension/generation codecs. Together: codec interpretability field has probing + SAE, but NO CAUSAL PATCHING → Leo's gap.
  - **NEW GAP #21: Codec Causal Patching in LALM Inference** — nobody has asked: "does zeroing RVQ layer k in the input to a speech LLM (Qwen2-Audio, Gemini) causally interrupt the LALM's understanding of speaker identity/pitch?" AnCoGen shows tokens *correlate* with attributes; causal necessity in downstream LALM = unanswered. Extend as Track 1 experiment.

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

### L) ARENA Curriculum — Pre-Experiment Skill-Up Path (Cycle #86 — 2026-02-28)

**Source:** ARENA 3.0, branch `alignment-science` (merging to main ~Mar 1, 2026)
**Repo:** https://github.com/callummcdougall/ARENA_3.0 (branch: `alignment-science`)
**Updated exercises:** Feb 27, 2026 (karma 65 on LessWrong by CallumMcDougall)

**New exercise sets directly relevant to Leo's research:**

#### [1.3.1] Linear Probes — ✅ STUDIED (cycle #89, 2026-02-28 20:01)
- Replicates "Geometry of Truth" (Marks & Tegmark) + Apollo deception probes
- **Sections:** Extract activations → PCA → MM vs LR probes → CAUSAL INTERVENTIONS → deception detection → attention probes
- **Key lessons (cycle #89):**
  - **MMProbe > LRProbe for causal interventions** — difference-of-means direction is more causally implicated despite lower classification accuracy. Apply to gc(k): use `mean(audio_condition) - mean(no_audio_condition)` not logistic regression.
  - **PROBE_LAYER ≠ INTERVENE_LAYER** — in Geometry of Truth: PROBE=14, INTERVENE=8. For Paper A: need to sweep both separately. The layer that classifies best ≠ layer where patching has most effect.
  - **layer_sweep_accuracy = gc(k) template** — sweep all layers, compute MM probe accuracy at each layer, plot curve → peak = "Listen Layer"
  - **Cross-generalization matrix** — train probe on condition A, test on B; high off-diagonal = universal direction. Paper A validation: train on Speech Commands stimuli, test on ALME 57K conflict stimuli.
  - **Attention probe (Section 5)** — single learned query over ALL sequence positions, better than last-token for sequence-level classification. Audio application: learns which audio frames are diagnostically important → new Paper B metric baseline
  - **Causal intervention implementation:** `h_new = h - 2 * (h @ d / ||d||²) * d` (reflection through hyperplane perpendicular to probe direction)
- **Paper A method section: now fully specified** (MMProbe for direction, layer sweep for gc(k), cross-generalization for universality, causal patching for IIT validation)
- Colab: https://colab.research.google.com/github/callummcdougall/arena-pragmatic-interp/blob/main/chapter1_transformer_interp/exercises/part31_linear_probes/1.3.1_Linear_Probes_exercises.ipynb
- **Estimated time:** 3-4h (any GPU; smaller models work for concept validation)

#### [1.4.2] SAE Circuits (Attribution Graphs)
- Replaces old "Function Vectors" exercise with full attribution graph pipeline
- **Section 1:** Latent-to-latent, token-to-latent, latent-to-logit GRADIENTS → linear proxy for SAE feature circuits
- **Section 2:** TRANSCODERS — variant of SAEs that reconstruct MLP computation (not just activations); blind case study using only weights
- **Section 3:** ATTRIBUTION GRAPHS from scratch (Gemma 3-1B + GemmaScope 2 transcoders); Anthropic's full circuit-tracing methodology; builds Neumann series pruning
- **Section 4:** `circuit-tracer` library — Dallas/Austin two-hop recall; feature swapping; generation with interventions
- **Papers:** "Circuit Tracing" (Anthropic 2025) + "Transcoders Find Interpretable LLM Feature Circuits" (Dunefsky et al., 2024)
- **Key discovery for Leo:** `circuit-tracer` = possible direct tool for Paper A Listen Layer localization. Replace text token embeddings → audio frame embeddings in the attribution graph to localize "Listen Layer"
- Colab: https://colab.research.google.com/github/callummcdougall/arena-pragmatic-interp/blob/main/chapter1_transformer_interp/exercises/part42_sae_circuits/1.4.2_SAE_Circuits_exercises.ipynb
- **Estimated time:** 4-6h (Colab Pro for sections 3-4; sections 1-2 need only GPT-2)

#### [4.1] Emergent Misalignment
- LoRA fine-tune mechanistic analysis using TransformerLens + SAEs
- **Direct relevance:** "What does fine-tuning change mechanistically?" = Track 4's research question
- **Methods:** Model organisms, autoraters, behavioral evaluation

#### [1.3.4] Activation Oracles
- Model diffing exercises (compare two models' representations)
- CKA is the basis (already used in whisper_hook_demo.py)

**SAELens v6 — fully mapped (cycle #87):**
- Repo: `decoderesearch/SAELens` (formerly `jbloomAus/SAELens`); `pip install sae-lens`
- Pre-trained SAE registry: **ZERO audio/speech SAEs** — all 25 models = Gemma-scope variants + GPT-2 + LLaMA
- Works with NNsight: `sae.encode(acts_tensor)` takes any PyTorch tensor from NNsight hook
- **Gap #19**: No standardized audio SAE training pipeline. SAELens training code = correct backbone for AudioSAEBench; trained SAEs can be uploaded with `saelens` tag → community adoption
- Transcoders available for Gemma 2-2B (for ARENA [1.4.2] exercise)
- Leo's workflow: NNsight hook → Whisper activations → SAELens trainer → save → `SAE.load_from_disk()`

**Recommended study path (pre-experiment):**
```
1. [1.3.1] Linear Probes   (3-4h) → methodology backbone for Paper A DAS-gc(k)
2. [1.4.2] SAE Circuits    (4-6h, sections 1-2 first) → circuit-tracer = direct tool for Track 1
3. Run IIT experiment (Priority 1 in experiment-queue.md)
```
**Estimated net savings:** ~6h of experimental debugging avoided by understanding methodology first.

## 🆕 Latest Paper (cycle #162, 2026-03-02)

### Gap #21 Anchor — Neural Audio Codec Interpretability
- **Sadok et al. "Bringing Interpretability to Neural Audio Codecs" (Interspeech 2025, arXiv:2506.04492)**
  - 4 codecs: DAC, SpeechTokenizer, Mimi, BigCodec; linear probes for content/identity/pitch in RVQ layers
  - KEY FINDING: SpeechTokenizer Layer 1 = semantic content (HuBERT-supervised); Layers 2+ = acoustic attributes (speaker, pitch, timbre)
  - AnCoGen plugin: attribute↔token prediction bidirectional
  - GAP #21: No causal patching of codec token streams in LALM inference (fully open — 6 arXiv queries, 0 results)
  - CONNECTIONS: Core Q#1 ("clean/corrupt design" = ANSWERED via RVQ layer semantics), Track 1 (Benchmark Protocol), Paper B (AudioSAEBench Category 1), Gap #18 (phonological geometry test = Layer 1 only patch)

## 關鍵研究者/團隊
- **NTU 李宏毅 lab** — AudioLens (智凱哥！Leo 主場)
- aiOla Research (Glazer) — ASR MI, hallucination causal analysis
- Huawei Noah's Ark (Aparin) — AudioSAE
- MBZUAI — SPIRIT (audio safety)
- Stanford (Atticus Geiger) — causal abstraction theory + pyvene; **DAS (Distributed Alignment Search)** = learns optimal linear subspace alignment per layer via IIT training loss; upgrade from vanilla patching → gc(k) = IIT accuracy at layer k = theoretically grounded grounding_coefficient; pyvene wraps any PyTorch model, ~50 lines for full DAS sweep; `pip install pyvene` (add to venv checklist)
- Neel Nanda — activation patching best practices, TransformerLens
- Mozilla Builders — Whisper SAE tooling
- Ellena Reid — early Whisper MI (LessWrong)
- Yuan Gong (MIT) — AST/SSAST audio transformers
- CallumMcDougall — ARENA curriculum (circuit-tracer, SAE Circuits, Linear Probes — best hands-on MI learning resource)
