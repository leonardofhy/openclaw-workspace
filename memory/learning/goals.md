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

### Track 5：Safety Mechanistic Defenses (Listen-Layer Audit)
- **核心提案**: Safety-Critical Listen-Layer Audit via gc(k) — 逐層安全評分
- Audio prompt injection benchmark + trigger subspace 定位
- 最小副作用的 inference-time defense
- **Novelty verdict**: 🟡 YELLOW — 需要兩個 crisp claim 之一推到 GREEN:
  1. Safety signal emergence: harmful intent 在 audio encoder 特定層就線性可分（transcription 前）
  2. Audit → intervention bridge: gc(k) 指導在哪層 patch/prune，改善 SPIRIT/ALMGuard
- **最近 overlap**: SPIRIT (layer patching), ALMGuard (shortcut localization), SALMONN-Guard (multimodal guard)
- **MVP**: 7-day plan in `memory/learning/research/listen-layer-audit-deep-research-2026-03.md`
- 風險：負責任揭露，defense > attack
- **MATS Research Task 首選方向**（Audio Jailbreak 跨模態探測）

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

### Tier 0: 最高優先（Listen-Layer Audit 直接相關，2026-03 deep research 確認）
1. [ ] **SPIRIT** (EMNLP 2025) — 🥇 activation patching for speech jailbreak defense; up to 99% robustness w/o retraining [ACL Anthology](https://aclanthology.org/2025.emnlp-main.734.pdf)
2. [ ] **SACRED-Bench + SALMONN-Guard** (arXiv 2511.10222, Nov 2025) — 🥈 compositional audio attacks + multimodal guard; Gemini 2.5 Pro = 66% ASR even with guardrails [arXiv](https://arxiv.org/abs/2511.10222)
3. [ ] **ALMGuard** (NeurIPS 2025 poster) — 🥉 safety shortcut localization + mel-gradient sparse mask; cuts jailbreak ASR to 4.6% [NeurIPS](https://neurips.cc/virtual/2025/poster/115978)

### Tier 1: 高優先（attack surface + benchmarks）
4. [ ] **JALMBench** (ICLR 2026 poster) — 最大 audio jailbreak benchmark: 12 LALMs × 8 attacks × 5 defenses [OpenReview](https://openreview.net/forum?id=DJkQ236C8B)
5. [ ] **AJailBench + APT** (arXiv 2505.15406, May 2025) — 1,495 adversarial audio prompts + Bayesian-optimized perturbations [arXiv](https://arxiv.org/abs/2505.15406)
6. [ ] **LALM-as-a-Judge** (arXiv 2602.04796, Feb 2026) — ~24k dialogues; audio-LM as safety judge; sensitivity/specificity analysis [arXiv](https://arxiv.org/pdf/2602.04796)

### Tier 2: 重要補充（attack families + defenses）
7. [ ] **AudioJailbreak** (TDSC accepted, May 2025 / rev Feb 2026) — weak adversary + over-the-air robustness; claims GPT-4o bypass [arXiv](https://arxiv.org/abs/2505.14103)
8. [ ] **Multi-AudioJail** (arXiv 2504.01094, Apr 2025) — multilingual/accent attacks; +57pp jailbreak success [arXiv](https://arxiv.org/abs/2504.01094)
9. [ ] **StyleBreak** (arXiv 2511.10692, Nov 2025) — style/voice conditioned attacks [arXiv](https://arxiv.org/html/2511.10692v1)
10. [ ] **Defending speech-enabled LLMs via adversarial training** (Interspeech 2025) — PGD-style defense + conformer architecture description [ISCA](https://www.isca-archive.org/interspeech_2025/alexos25_interspeech.pdf)

### Tier 3: 基礎方法論（保留原清單）
11. [ ] **AudioLens** (智凱哥 2025, NTU) — lab 自己的工作！[arXiv:2506.05140]
12. [x] **Beyond Transcription** (Glazer 2025) — ASR MI 基礎方法論 [arXiv:2508.15882] ✅ 2026-02-26 deep read cycle #6
13. [ ] **AudioSAE** (Aparin 2026, EACL) — SAE for speech + steering [arXiv:2602.05027]
14. [ ] **Activation patching best practices** (Heimersheim & Nanda) — 避免 pitfalls
15. [ ] **Causal abstraction** (Geiger et al.) — 因果介入的理論基礎
16. [ ] Multimodal MI Survey (Lin 2025) [arXiv:2502.17516]
17. [x] **SAEBench** (Karvonen, Nanda et al., ICML 2025) — 8-metric multi-category evaluation ✅ 2026-02-27 cycle #38
18. [ ] ICML 2025 MI Tutorial materials
19. [ ] **Interspeech 2025 Tutorial** — "Interpretability for Speech Models"

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

## 待請求 Leo 的任務隊列
1. 🔬 **Deep Research**: Mech Interp × Speech 領域深度掃描（已請求 2/26）
2. 🔧 **Deep Research**: 自主 AI agent 系統的可持續架構（已請求 2/26）
