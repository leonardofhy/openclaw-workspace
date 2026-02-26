# 🗺️ AI PhD Knowledge Graph

> 持續更新的知識地圖，追蹤我學到的概念、論文、和它們之間的關係

## 核心研究領域

### ⭐ Mechanistic Interpretability × Speech/Multimodal (Leo 主興趣)
- **現有工作僅 4 篇**（2025-08 至 2026-02），領域幾乎空白
- "Beyond Transcription" (2025-08) — 第一篇 systematic mech interp for ASR
- "Behind the Scenes" (2025-09) — Whisper + LoRA mech interp for SER
- "Brain-to-Speech Mech Interp" (2026-02) — neuroscience crossover
- "What Do Neurons Listen To" (2026-02) — audio SSL neuron dissection
- **Survey** (2025-02): 覆蓋 vision-language，speech 幾乎未提及 = GAP
- **Toolkit**: Vision 有 Prisma，speech/audio 無對應 = GAP
- **關鍵方法**: activation patching, probing, SAE, logit lens

### ⭐ AI Safety × Speech
- Jailbreak detection via activation disentanglement (2026-02)
- Adversarial activation patching for deception detection (2025-07)
- **Speech-specific safety 研究 = 0 篇** → 巨大 gap

### Audio Representation Learning
- **UniWhisper** (2602.21772) — unified instruction format, continual multi-task, 20-task evaluation
  - 上游: Whisper (OpenAI)
  - 方法: instruction-answer format → next-token training
  - 評估: MLP probe + kNN (lightweight)

### Audio Evaluation / Benchmarking
- **AudioMatters** (我們的!) — Interspeech 2026 投稿中
  - 待比較: UniWhisper 的 20-task coverage vs 我們的 benchmark scope

### Emotional Audio Understanding
- **EmoOmni** (2602.21900) — E-CoT for multimodal emotional dialogue
  - 架構: Thinker-Talker with explicit emotional instruction

### Low-Resource ASR
- **TG-ASR** (2602.22039) — Taiwanese Hokkien, translation-guided
- **Bangla ASR** (2602.21741) — Whisper fine-tune + Demucs

## 關鍵概念索引
| 概念 | 首次見於 | 筆記 |
|------|----------|------|
| Unified instruction format | UniWhisper | 把異質 tasks 統一成 instruction→answer |
| MLP probe evaluation | UniWhisper | Lightweight encoder 品質評估 |
| Emotional CoT (E-CoT) | EmoOmni | 從感知到回應的情感推理鏈 |
| PGCA mechanism | TG-ASR | 多語言 embedding 融合 |

## 待追蹤的研究者/實驗室
- Yuxuan Chen (UniWhisper)
- Yi-Hsuan Yang lab @ 台灣 (music/audio generation)
- Lei Xie group (EmoOmni, speech emotion)

## AudioMatters 競品地圖 (2026-02)

```
                    Scope
           Narrow ◄─────────► Broad
           │                      │
Encoder    │  UniWhisper           │
Only       │  (20 tasks,          │
           │   probe-based)       │
           │                      │
           │  SUPERB/HEAR         │  ← AudioMatters 目標位置
           │  (older, pre-LLM)    │  （跨場景 × 跨能力 × LLM-era）
           │                      │
End-to-End │  AudioRAG            │
           │  (retrieval only)    │
           │                      │
           │  EmoOmniEval         │
           │  (emotion only)      │
           │                      │
           │  PhoStream           │
           │  (streaming only)    │
```

## 累計統計
- 論文已讀: 2 (1 精讀 + 1 競品分析 covering 8 papers)
- 論文待讀: 6
- 學習天數: 1
