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
1. [ ] **AudioLens** (智凱哥 2025, NTU) — lab 自己的工作！[arXiv:2506.05140]
2. [x] **Beyond Transcription** (Glazer 2025) — ASR MI 基礎方法論 [arXiv:2508.15882] ✅ 2026-02-26 deep read cycle #6
3. [ ] **AudioSAE** (Aparin 2026, EACL) — SAE for speech + steering [arXiv:2602.05027]
4. [ ] **Activation patching best practices** (Heimersheim & Nanda) — 避免 pitfalls
5. [ ] **SPIRIT** (2025, EMNLP) — audio safety interventions [arXiv:2505.13541]
6. [ ] **Causal abstraction** (Geiger et al.) — 因果介入的理論基礎
7. [ ] Multimodal MI Survey (Lin 2025) [arXiv:2502.17516]
8. [ ] **SAEBench** — SAE evaluation methodology
9. [ ] ICML 2025 MI Tutorial materials
10. [ ] **Interspeech 2025 Tutorial** — "Interpretability for Speech Models"（結構化入門）

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
1. Run `whisper_hook_demo.py` — verify toolchain works end-to-end
2. Extend hook demo with logit-lens projection → run "Triple Convergence" experiment
3. Read SPIRIT (arXiv:2505.13541) — safety track anchor paper
4. Contact 智凱哥 about AudioLens codebase access

**Recommended next cycle:** `build` — extend whisper_hook_demo.py with logit-lens projection to test Triple Convergence hypothesis. MacBook-feasible, ~2-3 hours.

## 待請求 Leo 的任務隊列
1. 🔬 **Deep Research**: Mech Interp × Speech 領域深度掃描（已請求 2/26）
2. 🔧 **Deep Research**: 自主 AI agent 系統的可持續架構（已請求 2/26）
