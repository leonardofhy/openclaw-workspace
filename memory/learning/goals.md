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

## Paper Ideas（按優先級和可行性）
1. 🥇 **Mech interp of speech understanding in Omni-LLMs** → NeurIPS 2026 / ICLR 2027
   - 可行性：需要 GPU（跑 forward pass + probing on Qwen-Audio/SALMONN）
   - 預估時間：3-4 個月
2. 🥈 **SpeechLens toolkit** → EMNLP 2026 Demo Track
   - 可行性：主要是 engineering work，可以在 MacBook 上開發
   - 預估時間：2 個月
3. 🥉 **Audio adversarial × mech interp = safety** → Workshop paper
   - 可行性：需要 adversarial audio generation + interp analysis
   - 預估時間：1-2 個月

## Knowledge Gaps（要填的坑）
- [ ] TransformerLens / activation patching 實作
- [ ] SAE 訓練和分析
- [ ] Whisper / HuBERT encoder 逐層運作機制
- [ ] Qwen-Audio / SALMONN 架構細節
- [ ] Multimodal token alignment 機制
- [ ] 頂會論文寫作技巧（structure, framing, storytelling）

## 成功指標
- **3 個月內**: 完成 1 篇 mech interp 方向的 pilot study（可以是 workshop paper）
- **6 個月內**: 投稿 1 篇頂會論文（NeurIPS/EMNLP/ICLR）
- **1 年內**: 建立在 speech mech interp 領域的 recognized presence

## Must-Read List
- [ ] Beyond Transcription: Mech Interp in ASR (2025-08)
- [ ] Behind the Scenes: Whisper LoRA Mech Interp (2025-09)
- [ ] What Do Neurons Listen To (2026-02)
- [ ] Survey on Mech Interp for MMFMs (2025-02)
- [ ] Prisma toolkit (2025-04)
- [ ] Visual Representations inside LM (2025-10)

## Key Deadlines
| Conference | Deadline | Target Paper |
|-----------|----------|-------------|
| Interspeech 2026 | PDF 2026-03-05 | AudioMatters |
| NeurIPS 2026 | ~2026-05 | Mech interp of speech in Omni-LLMs |
| EMNLP 2026 | ~2026-06 | SpeechLens toolkit |

## 待請求 Leo 的任務隊列
1. 🔬 **Deep Research**: Mech Interp × Speech 領域深度掃描（已請求 2/26）
2. 🔧 **Deep Research**: 自主 AI agent 系統的可持續架構（已請求 2/26）
