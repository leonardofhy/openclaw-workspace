# 🎯 Autodidact Goals

> Last updated: 2026-02-26 14:45 by Leo (direct feedback)

## 北極星 (North Star)

**成為 Google DeepMind / Anthropic 等級的 AI Researcher。**

這意味著：
- 在 NeurIPS、ICML、ICLR 等頂會發表有影響力的工作（被引用、被討論）
- 能獨立識別深層的研究問題，而非只做 incremental improvement
- 掌握紮實的技術深度（不只是讀論文，要能復現、改進、提出新方法）
- 清晰有力的學術寫作能力
- 具備 research taste — 知道什麼問題值得花 6 個月去解

這不是一年能達到的目標，但每個 cycle 都應該在往這個方向走。

## 當前研究方向

### 主方向：Mechanistic Interpretability × Speech/Multimodal LM
- **為什麼選這個**: arXiv 上只有 4 篇論文，幾乎空白，先進者優勢巨大
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

## Paper Ideas（基於 2026-02-26 deep research 重新排序）

**戰略考量：AudioLens 是李宏毅 lab 的工作 → Leo 有主場優勢**

1. 🥇 **"Listen vs Guess" — AudioLens 延伸** → NeurIPS 2026 / ICLR 2027
   - 接棒 lab 自己的 AudioLens，用 controlled counterfactuals + patching 量化「audio evidence vs language prior」
   - 定義 "grounding coefficient"，因果定位 failure modes (encoder vs connector vs LM)
   - 優勢：lab 內有前人基礎、有老師指導、有 GPU
   - 預估：4-6 個月

2. 🥈 **Audio InterpBench — MI 的 evaluation benchmark** → EMNLP 2026 / Interspeech
   - 結合 AudioMatters benchmark 經驗 + MI 方法論
   - Synthetic ground-truth tasks with known causal structure
   - 優勢：Leo 的 evaluation 專長直接遷移
   - 預估：3-4 個月

3. 🥉 **Audio Safety via MI (SPIRIT 延伸)** → Workshop paper
   - Benchmark of audio jailbreak styles + mechanistic defenses comparison
   - 接棒 SPIRIT (EMNLP 2025)
   - 優勢：AI Safety 興趣 + NTUAIS 社群
   - 預估：2-3 個月

## Knowledge Gaps
- [ ] TransformerLens activation patching 實作（month 0-2 必修）
- [ ] SAE 訓練 + feature steering（AudioSAE 復現）
- [ ] AudioLens 論文精讀 + 代碼復現（**lab 內部資源**）
- [ ] Whisper / HuBERT encoder 逐層機制
- [ ] Qwen2-Audio / SALMONN 架構
- [ ] ICML 2025 MI Tutorial（結構化學習路徑）

## Must-Read List（按優先級）
1. [ ] **AudioLens** (Yang 2025, NTU) — lab 自己的工作！[arXiv:2506.05140]
2. [ ] **Beyond Transcription** (Glazer 2025) — ASR MI 基礎方法論 [arXiv:2508.15882]
3. [ ] **AudioSAE** (Aparin 2026, EACL) — SAE for speech [arXiv:2602.05027]
4. [ ] **SPIRIT** (2025, EMNLP) — audio safety interventions [arXiv:2505.13541]
5. [ ] Multimodal MI Survey (Lin 2025) [arXiv:2502.17516]
6. [ ] ICML 2025 MI Tutorial materials

## 6-12 Month Ramp Plan
- **Month 0-2**: TransformerLens 熟練 + 復現 AudioLens
- **Month 2-4**: 在 AudioLens 基礎上設計 counterfactual experiments
- **Month 4-8**: 跑實驗 + 寫第一篇論文
- **Month 8-12**: 投稿 + 開始第二個方向

## Key Deadlines
| Conference | Deadline | Target Paper |
|-----------|----------|-------------|
| Interspeech 2026 | PDF 2026-03-05 | AudioMatters |
| NeurIPS 2026 | ~2026-05 | Listen vs Guess (if ready) |
| EMNLP 2026 | ~2026-06 | Audio InterpBench |

## 待請求 Leo 的任務隊列
1. 🔬 **Deep Research**: Mech Interp × Speech 領域深度掃描（已請求 2/26）
2. 🔧 **Deep Research**: 自主 AI agent 系統的可持續架構（已請求 2/26）
