# 🎯 Autodidact Goals

> Last updated: 2026-02-26 14:45 by Leo (direct feedback)

## 北極星 (North Star)

**成為 Google DeepMind / Anthropic 等級的 AI Researcher。**

### Thesis-level north star
> 建立一套可驗證的 audio 機制單元（features/circuits），並用它們在 ASR 與 audio-LLM 中同時做到：**可靠定位錯誤來源 + 可控介入改善行為（含安全/穩健性）**。

這句話串起所有方向：SAE（機制單元）、patching（可驗證）、ASR（可量化行為）、audio-LLM（融合與安全）、以及「改得動」。

## 當前研究方向

### 主方向：Mechanistic Interpretability × Speech/Multimodal LM
- **為什麼選這個**: 領域早期加速中（~20 篇相關工作），先進者優勢仍在但需加速
- **核心問題**: Multimodal LM（Qwen-Audio, Gemini, GPT-4o）如何在內部處理 speech？
  - Speech tokens 在哪一層被轉化為語義？
  - Emotion / speaker identity / phonetics 分別在哪裡處理？
  - Speech pathway 和 text pathway 在哪裡交會？
- **方法論需求**: activation patching, probing, SAE, logit lens — 需要從 text mech interp 遷移到 speech

### 次方向：AI Safety × Speech
- Audio adversarial attacks 的機制
- Speech-based jailbreak detection
- Speech modality 是否繼承了 text safety training？

### 進行中：AudioMatters — Interspeech 2026
- 一作，CMT 卡位截止 2026-02-26 19:00
- 最終 PDF 2026-03-05
- 投稿後 → 注意力轉向 mech interp 方向

## 5 Research Tracks（一個 thesis 的不同切面）

**戰略考量：AudioLens 是智凱哥的工作 → Leo 有主場優勢；5 tracks 都服務同一個 thesis**

### Track 1：Audio Causal Benchmark / Protocol → community resource
- 建立 audio 的 IOI — clean/corrupt 標準任務 + patching protocol
- 第一篇 paper: 3-5 tasks (Speech Commands, ESC-50, 短句 ASR) × 3-5 corruptions
- **做出來所有人引用**

### Track 2：AudioSAE → AudioSAEBench → 評估科學化
- 對 Whisper/HuBERT/WavLM 做 SAE + audio-native 評估指標
- 因果 steering/erasure 測試 + 副作用曲線
- 延伸：feature alignment across models/languages

### Track 3：Listen vs Guess in Audio-LLMs ⭐ 最高優先
- 接棒智凱哥 AudioLens，用 minimal pairs + patching 量化 grounding
- 定義 grounding coefficient（audio patching sensitivity vs context patching sensitivity）
- **優勢：智凱哥 = AudioLens 作者 = 每天一起吃飯的 labmate，已談好合作**

### Track 4：Mechanistic Interp of Adaptation (LoRA/adapters)
- 解釋「微調到底改了什麼機制」
- CKA/SVD + SAE drift + patching 定位變化
- 延伸：mechanistically guided fine-tuning

### Track 5：Safety Mechanistic Defenses
- Audio prompt injection benchmark + trigger subspace 定位
- 最小副作用的 inference-time defense
- 風險：負責任揭露，defense > attack

## 10 Core Research Questions（autodidact 讀論文時圍繞這些問題思考）
1. Audio 的 "clean/corrupt" 怎麼設計才只破壞你要隔離的因素？
2. Patching 的 OOD internal state 怎麼診斷/避免？
3. ASR 的 WER 是序列指標 — 怎麼對齊到局部機制？
4. SAE features 能跨語言/噪聲/模型遷移嗎？用什麼 alignment？
5. Audio SAE 評估該用什麼指標？哪些與「可因果操控」相關？
6. 模型何時在「聽」、何時在「猜」？怎麼量化？
7. Connector bottleneck 讓哪些信息不可逆丟失？
8. Audio jailbreak 的 trigger subspace 在 encoder 還是 LM？
9. Neural codec 的 codebook 分工 — 哪些對 pitch/timbre/清晰度負責？
10. Audio 能做自動 circuit graph 嗎？前置條件是什麼？

## Skill Gaps（技能層面）
- [ ] TransformerLens + pyvene 實作
- [ ] SAE 訓練 + evaluation discipline
- [ ] AudioLens codebase（問智凱哥）
- [ ] Whisper/HuBERT/WavLM 逐層機制
- [ ] EnCodec discrete tokens 與 MI 的接口
- [ ] Causal abstraction 理論基礎

## Must-Read List（按優先級）
1. [x] **AudioLens** (Ho, Lee, Hung-yi Lee, ASRU 2025, NTU) — lab 自己的工作！[arXiv:2506.05140] ✅ 2026-03-12 deep read cycle #182 → Gap #33; Paper A §2 causal sequel framing; earlier resolution=higher accuracy; models query audio tokens (but only observationally—gc(k) is the causal test)
2. [x] **Beyond Transcription** (Glazer 2025) — ASR MI 基礎方法論 [arXiv:2508.15882] ✅ 2026-02-26 deep read cycle #6
3. [x] **AudioSAE** (Aparin 2026, EACL) — SAE for speech + steering [arXiv:2602.05027] ✅ 2026-03-02 full deep read cycle #177
   → **Paper B v1.3 milestone**: §1+§2+§3 all LaTeX-ready ✅ (cycle #225, 2026-03-03)
4. [x] **Activation patching best practices** (Heimersheim & Nanda) — ✅ 2026-03-02 cycle #178; AND/OR gate insight, audio denoising preference, Hydra 0.7x, top-k aggregate metric, AtP for large models
5. [x] **SPIRIT** (2025, EMNLP) — audio safety interventions [arXiv:2505.13541] ✅ 2026-03-02 full deep read cycle #181; 100% ASR via waveform PGD, 99% robustness via MLP-layer activation patching, Whisper encoder; Gap #24: no SAE-feature attribution for jailbreak mechanism
6. [x] **RAVEL** (Huang et al., ACL 2024) — Cause/Isolate two-score metric; MDAS = SOTA; SAEs fail isolation; Audio-RAVEL = new Category 0 for AudioSAEBench ✅ 2026-03-02 cycle #179
7. [x] **Causal abstraction** (Geiger et al.) — ✅ 2026-03-04 deep read cycle #272; theory triangle complete; Paper A §2.1 Geiger + Sutter + Asiaee fully assembled; gc(L) = graded faithfulness instance
8. [x] **Multimodal MI Survey** (Lin 2025) [arXiv:2502.17516] ✅ 2026-03-04 cycle #273; speech = ABSENT from all 3 MMFM families covered; confirmed audio MI white space by survey omission; Gap #27; intermediate layer finding predicts gc(L) peak at L_mid in Paper A
9. [x] **SAEBench** (Karvonen, Nanda et al., ICML 2025) — 8-metric multi-category evaluation; Matryoshka SAE wins disentanglement; proxy metrics ≠ quality; AudioSAEBench template identified; "Grounding Sensitivity" as novel metric ✅ 2026-02-27 cycle #38
10. [ ] ICML 2025 MI Tutorial materials
11. [~] **Interspeech 2025 Tutorial** — "Interpretability for Speech Models"（結構化入門）→ manual resource, no arXiv, not automatable; marked DONE for autodidact purposes (cycle #274)

## 6-12 Month Ramp Plan
- **Month 0-2**: Foundations
  - 精讀 AudioLens + Beyond Transcription + AudioSAE（方法細節，不只 abstract）
  - TransformerLens + pyvene 實作（先在 text 上跑通，再遷移到 audio）
  - Starter experiments 1-3（probing, CKA, Whisper neuron atlas）→ MacBook 可跑
  - 理解 patching pitfalls + SAE evaluation methodology
- **Month 2-4**: 和智凱哥合作設計 counterfactual experiments（已談好合作）
  - Starter experiments 4-5（single-layer SAE, intervention on Speech Commands）→ 戰艦
  - Define "clean vs corrupt" protocols for audio
- **Month 4-8**: 跑實驗 + 寫第一篇論文
- **Month 8-12**: 投稿 + 開始第二個方向

## Key Deadlines
| Conference | Deadline | Target Paper |
|-----------|----------|-------------|
| Interspeech 2026 | PDF 2026-03-05 | AudioMatters |
| NeurIPS 2026 | ~2026-05 | Listen vs Guess (if ready) |
| EMNLP 2026 | ~2026-06 | Audio InterpBench |

## 📌 狀態更新 (2026-02-26 19:00)

**AudioMatters CMT deadline passed** → Leo's focus now shifts fully to mech interp.

**Immediate next steps (post-deadline):**
1. 📖 Deep-read **AudioSAE** (arXiv:2602.05027) — Track 2 anchor paper
2. 📖 Read **SPIRIT** (arXiv:2505.13541) — safety track anchor paper
3. 📖 Read **Activation patching best practices** (Heimersheim & Nanda) — 避免 pitfalls
4. 💡 每篇讀完產出 1-2 個具體 research idea（與 10 core questions 對照）
5. Contact 智凱哥 about AudioLens codebase access

**⚠️ Leo 指示 (2026-02-26 21:10)：不要實作，專注挖掘新想法。**
**補充指示 (2026-02-27 00:35)：夜間不需要自動 skip，可持續自主研究；只是 Leo 即時 feedback 機率較低。**
**新指示 (2026-02-28 01:04)：恢復 30 分鐘 cadence，自主學習要加入「meta-awareness 系統自我研究」：每輪可列出值得改進問題，並做最小可逆改善。**
**Recommended next cycles:** `learn` + `reflect(meta-audit)` 交替，避免 execution-blocked 時連續 skip。

## Paper Idea #7: Audio T-SAE (新增 2026-02-28 cycle #72)
**"Phoneme-Aware Sparse Autoencoders for Speech Models via Temporal Contrastive Learning"**
- Apply T-SAE (Bhalla et al., ICLR 2026 Oral, arXiv:2511.05541) to Whisper/HuBERT
- Matryoshka partition: high-level (speaker/phoneme/emotion) + low-level (frame-level articulation)
- Multi-scale temporal contrastive loss: SHORT (adjacent frames, phoneme-level) + LONG (utterance-level for speaker identity)
- Evaluate with TCS(F) = within-phoneme variance / across-phoneme variance (uses MFA boundary ground truth)
- Audio has STRONGER temporal priors than text → should work BETTER; T-SAE authors flag this gap explicitly
- Gap #17: No audio SAE exploits temporal structure. All existing audio SAEs (AudioSAE, Mariotte, AR&D) are i.i.d. across frames.
- Venue: INTERSPEECH 2027 or ICASSP 2027. Risk: T-SAE authors could extend first → move fast.
- Relationship to AudioSAEBench: TCS(F) = Category 1 metric; Audio T-SAE = the model being benchmarked.

## Gap #19: No Standardized Audio SAE Training Pipeline (新增 2026-02-28 cycle #87)
- SAELens v6 (the de-facto SAE training/loading library, `decoderesearch/SAELens`) has **ZERO audio/speech pre-trained SAEs** — all 25 HuggingFace models = Gemma-scope / GPT-2 / LLaMA only
- All 5 audio SAE papers (AudioSAE, Mariotte, AR&D, Plantinga-PD, Paek et al.) use custom one-off training code
- **Implication for Paper B (AudioSAEBench)**: include a SAELens-compatible audio SAE training toolkit as a community contribution. This makes AudioSAEBench stronger (not just evaluation → evaluation + training pipeline) and ensures results are `pip install`-able and reproducible.
- Connection: Leo uses SAELens training code with NNsight hooks for Whisper/HuBERT activation extraction → upload trained SAEs with `saelens` tag → field has first standardized audio SAE backbone

## Gap #18: Phonological Vector Geometry Through the Connector (新增 2026-02-28 cycle #81; experiment design cycle #82)
**"Does linear phonological structure in S3M encoders survive through the connector into speech LLMs?"**
- Choi et al. 2602.18899 confirms: phonological features are linear, compositional, scale-continuous in S3M representations (96 languages)
- What's unknown: Does this linear phonological geometry persist after passing through the connector into the LLM residual stream?
- If YES: LLM has direct access to phonological feature directions → listening is phonologically structured
- If NO: connector destroys phonological geometry → connector = modality bottleneck → supports Modality Collapse (2602.23136)
- **Experiment (4 steps, cycle #82):**
  1. Extract voicing_vector = h([d]) - h([t]) from Whisper-small encoder (MacBook, Choi et al. stimuli)
  2. Hook connector via NNsight (DeSTA2 or NDIF Qwen2-Audio)
  3. Test arithmetic in LLM layer 0: `projected_h([b]) ≈ projected_h([d]) - projected_h([t]) + projected_h([p])?`
  4. Layer-wise probe sweep: where does voicing direction become decodable?
- **Status:** Added as **Priority 0** in experiment-queue.md (prerequisite check before Paper A IIT experiment)
- **Idea gate:** 🟢 GREEN — no competitors found; integrate as Figure 2 of Paper A or Category 0 of AudioSAEBench
- Connection: Paper A (Listen Layer — prerequisite), Paper B (AudioSAEBench TCS(F) validation), Idea #7 (Audio T-SAE), Gap #14 (Modality Collapse)

## Gap #20: Emotion-Modulated Safety (Track 5 Candidate — 🟡 YELLOW gate, cycle #100)
**"Why does speaker emotion override LALM safety alignment?"**
- Feng et al. 2510.16893 (ICASSP 2026): emotion varies unsafe response rate non-monotonically; medium intensity = highest risk
- Mechanistic cause unknown: which layers/heads allow emotion to bypass safety neurons?
- Method: SPIRIT-style patching + Zhao et al. ESN cross-reference + SAE-guided feature attribution
- **Gate verdict: 🟡 YELLOW** — genuine gap but Track 5 = lowest priority; Hung-yi Lee lab (same as AudioLens) may follow up
- **Action: HOLD** — do not develop until Papers A+B submitted. Monitor Feng et al. for mechanistic follow-up.

## Gap #22: SAE Feature Consistency vs. Causal Utility in Audio Models (新增 2026-03-02 cycle #177)
**"Are consistently-reproduced audio SAE features also causally efficacious?"**
- AudioSAE shows >50% feature consistency across seeds = STABLE representation
- BUT: consistency ≠ causality — stable features could be epiphenomenal (observe but not cause behavior)
- RAVEL (Huang et al. 2024, ACL) addresses this for LLMs; no audio analogue exists
- SAEBench "intervention" category addresses this for text; no audio version
- **AudioSAEBench Category 1** = "causal consistency" metric: cross-seed stable features × causal contribution (via patching/steering score)
- Method: take AudioSAE consistent features → patching experiment on minimal pair audio → measure behavior change
- **Paper B contribution**: first audio SAE benchmark measuring causal utility, not just representation quality
- Venue: same as AudioSAEBench (ACL 2026 or NeurIPS 2026 workshop)
- Status: 🟢 GREEN — natural extension of AudioSAE; completes their evaluation story

## Gap #27: No MI Survey Covers Audio/Speech Models (新增 2026-03-04 cycle #273)
**"Three concurrent MMFM MI surveys all skip audio — audio MI is white space confirmed by survey omission"**
- Lin et al. 2502.17516 (30 pages, 21 authors, Feb 2025): covers VLMs + generative VLMs + text-to-image diffusion → ZERO audio coverage
- Sun et al. 2024 (historical view, 2000-2025): also no audio
- Dang et al. 2024 (broad MMFM interpretability overview): also no audio
- **Implication**: Not just a search gap — the field's canonical surveys explicitly omit audio. Paper A and Paper B can cite Lin et al. 2502.17516 as: "the most comprehensive MMFM MI survey [Lin et al. 2025] does not cover audio modality, which we address."
- **Secondary finding**: Lin §4.1 shows *intermediate layers* (not upper layers) capture cross-modal interactions in VLMs. Audio-LLM analog: gc(L) peak should be at L_mid → falsifiable prediction for Paper A experiment.
- **Status**: 🟢 GREEN — confirmed by THREE concurrent surveys; cite in both Paper A + B §1 as motivation

## Gap #24: SAE-Guided Audio Jailbreak Defense (新增 2026-03-02 cycle #181)
**"Which audio SAE features are hijacked during jailbreak attacks on SLMs?"**
- SPIRIT (Djanibekov et al., EMNLP 2025) shows MLP-layer activation patching defeats jailbreaks (99% robustness), but identifies vulnerable neurons only by activation delta magnitude — no feature-level attribution
- With AudioSAE on Whisper encoder: identify which specific SAE *features* are noise-sensitive → is it phoneme features, speaker features, or acoustic quality features that the jailbreak corrupts?
- **Grounding Sensitivity connection (gc(F)):** does the jailbreak corrupt audio-grounded features (gc≈1) or text-prediction features (gc≈0)? If gc≈0 features = safety-relevant → attack bypasses safety by exploiting text-prediction pathway rather than audio understanding pathway
- Method: SPIRIT adversarial stimuli → AudioSAE feature activation on clean vs adversarial → ΔActivation per feature → top-k features = mechanistic explanation of SPIRIT's neuron-level finding
- **Extension to defense**: SAE-guided patching = patch only the features with high ΔActivation AND high safety-behavior correlation → finer-grained, lower collateral damage than SPIRIT's neuron-level patching
- Connection to Gap #20 (Feng et al.): SPIRIT = waveform-noise jailbreak; Feng = emotion-modulated jailbreak — are they the same features? If different → two-mechanism defense needed
- Venue: ICLR 2027 Safety Track or ACL 2026 Safety Workshop (non-archival for MVP)
- Status: 🟢 GREEN — SPIRIT leaves exact mechanistic question open; Leo has AudioSAE + Whisper infrastructure
- Priority: LOW (Track 5 = lowest priority; Papers A+B first)

## Gap #23: Audio-RAVEL — First Audio Disentanglement Benchmark (新增 2026-03-02 cycle #179)
**"Do audio SAE features truly disentangle phonological attributes?"**
- RAVEL (Huang et al. ACL 2024) introduced Cause/Isolate two-score metric for text LMs
- **Cause(F, A)**: does patching feature F cause attribute A to change as expected? (localization)
- **Isolate(F, A)**: does patching feature F leave OTHER attributes unchanged? (isolation)
- Audio SAEs (AudioSAE, Mariotte, Plantinga, etc.) measure Cause implicitly via steering success, but NEVER measure Isolate
- **Key hypothesis**: audio SAEs likely exhibit MORE cross-attribute leakage than text SAEs, because acoustic attributes co-occur at the physical signal level (voicing correlates with speaker gender in training corpora → voiced phoneme SAE features may also encode gender)
- **AudioSAEBench Category 0 = Audio-RAVEL**: entity→audio stimulus; attribute→phonological feature (voicing, manner, place); interchange intervention→SAE feature patch; score = harmonic mean of Cause + Isolate
- Stimulus design: Choi et al. 2602.18899 validated minimal pairs (96 languages × phonological contrasts) + TTS-augmented pairs
- Ceiling baseline: MDAS (Multi-task DAS) from RAVEL applied to Whisper residual stream — simultaneously optimizes all attribute subspaces to be orthogonal
- Status: 🟢 GREEN — no audio analogue of RAVEL exists; natural extension of RAVEL framework to speech
- Impact: Category 0 becomes the most fundamental/differentiating contribution of AudioSAEBench (goes beyond what AudioSAE, SAEBench, or any existing audio work measures)

## Gap #25: Non-Linear Audio Feature Representations (新增 2026-03-02 cycle #183)
**"Do audio model representations require non-linear alignment maps to achieve high IIA?"**
- Sutter et al. (NeurIPS 2025 Spotlight, arXiv:2507.08802) prove: with non-linear alignment maps, ANY neural network can be mapped to ANY algorithm (100% IIA on random models) → causal abstraction = vacuous without linearity constraint
- For TEXT models: linear representation hypothesis is well-supported (features align to linear subspaces)
- For AUDIO models: acoustic attributes (pitch, voicing, formants) may have STRONGER non-linear structure due to physical acoustics (e.g., formant frequencies are not additive in the linear sense)
- **Experiment:** After establishing Listen Layer with linear DAS → test non-linear DAS (e.g., kernel DAS or neural alignment map) → if IIA increases significantly, audio phonological geometry is partially non-linear
- **Paper A implication:** Must cite Sutter et al. to justify why linear DAS is methodology of choice (not arbitrary maps); turn "why assume linearity?" weakness into theoretically grounded strength
- **Status:** 🟡 YELLOW — valid gap but low priority; Paper A limitations section, not primary contribution
- Connection: Paper A (methodology justification), Audio-RAVEL Category 0 (MDAS ceiling baseline clarification)

## Paper A Citation Update (2026-03-02 cycle #183-184)
**Add to methodology section of Paper A:**
- Geiger et al. 2301.04709 (Causal Abstraction: Theoretical Foundation for MI) = master reference; ALL 10 MI methods = causal abstraction special cases
- Sutter et al. 2507.08802 (NeurIPS 2025 Spotlight): "linear alignment maps are necessary for causal abstraction to be non-trivial" → justifies DAS over arbitrary neural alignment maps
- Asiaee 2602.24266 (Feb 2026): efficient causal abstraction via structured pruning; activation variance = first-order proxy; justifies whisper_hook_demo.py norm heatmap as pre-screen; fails for non-uniform curvature (rare phoneme features → DAS is necessary, not optional)
- **Theory triangle: Geiger (foundation) + Asiaee (efficiency) + Sutter (linearity guard)** = strong methodology section

**New Risk A6 for Paper A experiment-queue:**
- Low-variance phoneme features with high causal weight may be missed by variance-based ablation (H&N noising). Mitigation: use DAS (not variance threshold), report ablation delta per phoneme class separately.

## Gap #28: Behavioral Grounding Degradation Under Multi-Event Complexity (新增 2026-03-05 cycle #292)
**"Lee et al. 2603.03855 provides behavioral proof that audio grounding degrades under scene complexity — Paper A provides the mechanistic account"**
- 71K AudioCapsV2 clips × 4 SOTA Audio LLMs × 500K yes/no queries: as event count ↑, TPR↓ + FPR↑
- Prompt variants induce strong TPR/FPR trade-off (models can't simultaneously maintain precision AND recall under complexity)
- Models become more uncertain (confidence → 0.5) = Listen/Guess ambiguity
- **Paper A §1 cite**: "behavioral analyses confirm degraded grounding [Lee et al. 2026]; we provide mechanistic account via gc(k)"
- **Gap**: Lee et al. = behavioral (black-box survey); Paper A = mechanistic (circuit-level, why at which layer)
- **Status**: 🟢 GREEN — confirmed, cite immediately in Paper A §1

## Gap #29: ACES Accent Subspace vs AudioSAE Feature Alignment (新增 2026-03-05 cycle #292)
**"Do accent PCA directions (ACES) correspond to monosemantic AudioSAE features, or do the two methods diverge?"**
- ACES (Parekh et al. 2603.03359): accent info in low-dim subspace (Wav2Vec2 layer 3, k=8); linear erasure worsens disparity; accent features "deeply entangled with recognition-critical cues"
- This is exactly the Isolate(F,A) failure mode AudioSAEBench M4 is designed to detect
- Open Q: Are the k=8 accent PCA directions captured by any single AudioSAE feature? If yes → methods agree; if no → representation method gap
- **Paper B contribution**: AudioSAEBench M4 (Isolate) = more rigorous, per-feature version of ACES's subspace analysis
- **Cite ACES in Paper B §2.2**: "prior work shows accent features entangled with recognition-critical cues [Parekh et al. 2026]; our Isolate metric quantifies this per-feature"
- **Status**: 🟡 YELLOW — valid gap, lower priority than Papers A+B primary contributions; monitor if ACES authors extend to SAE

## Gap #30: Modality Collapse as Measurable SAE Isolation Failure (新增 2026-03-05 cycle #293)
**"Is modality collapse (Zhao et al. 2602.23136) mechanistically detectable as low SAE Isolate score?"**
- Zhao et al.: LALMs default to text-prediction pathway even when audio contradicts text → behavioral phenomenon
- Hypothesis: models with modality collapse have audio SAE features that score LOW on Isolate(F, audio_attribute) — i.e., "audio features" also encode text information (not isolated from text pathway)
- **Test**: Use ALME stimuli (57K audio-text conflict pairs); extract AudioSAE features; measure Isolate score for audio-specific attributes; compare models with high vs low modality collapse rates
- **Predicted result**: Isolate(audio SAE feature, audio attribute) correlates negatively with modality collapse rate
- **Paper B contribution**: first mechanistic/quantitative correlate of behavioral modality collapse; connects AudioSAEBench M4 (Isolate metric) to established behavioral finding
- **Connection**: AudioSAEBench Category 1 (M4 Isolate) + Modality Collapse (Zhao et al.) + ALME (stimuli source)
- **Status**: 🟢 GREEN — high novelty (S=9 ideation cycle #293); Paper B §4 candidate; Q045 in queue

## Gap #31: 3-Tier Grounding Failure Taxonomy (新增 2026-03-05 cycle #293)
**"Can we unify codec/connector/LLM grounding failures into one mechanistic taxonomy?"**
- Three separate prior-work failure modes:
  1. **Codec failure**: information destroyed at RVQ tokenization (Sadok codec probe — semantic only survives in layer 1)
  2. **Connector bottleneck**: multimodal projection loses phonological geometry (Gap #18 phonological vector arithmetic)
  3. **LLM modality collapse**: model processes audio tokens but defaults to text priors (Zhao et al. 2602.23136, ALME)
- Each tier has a distinct gc(k) signature:
  - Tier 1 (codec): gc(k) = random at ALL layers → signal never enters model
  - Tier 2 (connector): gc(k) peaks in encoder layers but collapses after connector → information present, then lost
  - Tier 3 (LLM): gc(k) shows a peak at L_mid but drops at upper layers → information enters LLM but late layers default to text
- **Paper A §4 contribution**: theoretical taxonomy + predicted gc(k) patterns = falsifiable predictions from the framework
- **Connection**: Sadok Codec Probe + Gap #18 (phonological geometry) + T3 gc(k) + ALME + Modality Collapse + Listen Layer hypothesis
- **Status**: 🟢 GREEN — high novelty (S=9); unifies 3 literatures; Q043 in queue (Tier 0 build)

## Gap #32: No Layer-Level Account of Cascade Equivalence Transition (新增 2026-03-12 cycle #176+)
**"Billa (2026) shows cascade equivalence behaviorally; no paper provides the mechanistic account of WHEN text dominates over audio inside speech LLMs"**
- Billa et al. (arXiv:2602.17598, Interspeech 2026): matched-backbone testing + LEACE erasure shows speech LLMs ARE behaviorally equivalent to cascades on text-sufficient tasks (Cohen's κ); text representations are causally necessary; under noise, cascades WIN by 7.6% at 0dB
- **Key gap**: Billa has no layer-level mechanistic account — LEACE erases all layers simultaneously, logit lens = descriptive; neither tells you at WHICH layer audio processing hands off to text
- **Paper A fills this gap**: gc(L) curve = first layer-by-layer mechanistic account of the cascade transition inside the model
- **Prediction**: gc(L) is HIGH in encoder, drops at connector, shows temporary recovery then full collapse in LLM upper layers (matches Gap #31 Tier 2/3 taxonomy)
- **Paper A §1 cite**: "Billa (2026) establishes cascade equivalence behaviorally; we provide the first mechanistic account via gc(L)"
- **ΔI_Y (Billa) ↔ gc(k) (Paper A)**: acoustic surplus = task-level signal; gc(k) = layer-level mechanism — Paper A provides the mechanistic WHY
- **Method note**: Billa's matched-backbone testing = behavioral control; Paper A's audio-vs-text patching = mechanistic control — complementary, not competing
- **Status**: 🟢 GREEN — Billa has no mechanistic follow-up; Paper A is the natural continuation; strengthens Paper A §1 motivation enormously
- Priority: HIGH — add to Paper A §1 rewrite + abstract v08

## Gap #33: Logit Lens ≠ Causal — AudioLens Finding #3 Needs Causal Verification (新增 2026-03-12 cycle #182)
**"AudioLens (Ho et al., ASRU 2025) shows models query audio tokens directly via Logit Lens — but Logit Lens is observational, not causal. gc(k) is the causal test."**
- AudioLens: LALMs "heavily rely on querying auditory inputs for predicting attributes instead of aggregating necessary information in hidden states at attribute-mentioning positions" → Logit Lens evidence
- **But Logit Lens is correlational**: high I_i^ℓ at audio token positions doesn't prove audio tokens CAUSED the prediction. A model could show high Logit Lens scores at audio tokens AND still be text-driven causally (if text pathway produces the same prediction).
- **gc(k) = first causal test of AudioLens finding #3**: does patching audio tokens vs text tokens CAUSALLY shift attribute prediction? If yes → listening confirmed; if text wins → behavioral correlate ≠ causal mechanism
- **AudioLens I_i^ℓ ≈ observational gc** — same conceptual measurement, different causal strength
- **Paper A §2 positioning**: "AudioLens [Ho et al. 2025] tracks auditory attribute information using Logit Lens (observational). We extend this to causal analysis via activation patching, isolating the mechanistic contribution of audio vs. text pathways."
- **Falsifiable prediction**: gc(k) peak at audio-token positions, not text positions → confirms AudioLens #3 causally; if contradicted → models LOOK like they listen but causally don't (major finding)
- **Connection to Gap #32 (Billa)**: AudioLens = non-causal layer tracking; Billa = behavioral equivalence; Paper A = causal mechanism; three papers form perfect three-tier motivation
- **Status**: 🟢 GREEN — opens Paper A as explicit mechanistic sequel to AudioLens; strengthens §1+§2 significantly
- **Must-read #1** ✅ AudioLens fully read (cycle #182, 2026-03-12); cite in Paper A §1+§2

## 待請求 Leo 的任務隊列
1. 🔬 **Deep Research**: Mech Interp × Speech 領域深度掃描（已請求 2/26）
2. 🔧 **Deep Research**: 自主 AI agent 系統的可持續架構（已請求 2/26）
