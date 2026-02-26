# 🎯 Conference Publication Pipeline

> 目標：以 AI PhD student 的標準，持續產出 top conference 論文

## 當前投稿進度

### 🔴 Active — Interspeech 2026
- **論文**: AudioMatters (1st author!)
- **CMT 卡位截止**: 2026-02-26 19:00 ⚠️ 今天！
- **最終 PDF 截止**: 2026-03-05
- **狀態**: 實驗數據充足，論文框架討論中

## 下一步目標 Conference（按 deadline 排序）

### Tier 1 Speech/Audio
| Conference | 預估 Deadline | 備註 |
|-----------|--------------|------|
| Interspeech 2026 | ✅ 進行中 | AudioMatters |
| ASRU 2026 | ~2026-06 | IEEE, speech recognition |
| SLT 2026 | ~2026-09 | IEEE, spoken language |
| ICASSP 2027 | ~2026-10 | IEEE, signal processing 頂會 |

### Tier 1 ML/NLP
| Conference | 預估 Deadline | 備註 |
|-----------|--------------|------|
| NeurIPS 2026 | ~2026-05 | ML 頂會 |
| EMNLP 2026 | ~2026-06 | NLP 頂會，ARR rolling |
| ACL 2027 | ~2026-10 | NLP 最頂，ARR rolling |
| ICLR 2027 | ~2026-09 | ML 頂會 |

## 我（AI agent）能做的具體事情

### 📊 Phase 1: Research Gap Discovery（現在開始）
- [x] 每日 arXiv Radar — 掃描新論文、追蹤趨勢
- [x] 每 30 min 精讀 — 累積 domain knowledge
- [x] Knowledge Graph — 串聯概念關係
- [ ] **Gap Analysis** — 每週從讀過的論文中提煉 3 個 open problems
- [ ] **Related Work 自動整理** — 給定 topic，自動搜集+分類 related work

### 🔬 Phase 2: Experiment Support（AudioMatters 投稿後）
- [ ] 幫寫 experiment scripts（數據處理、evaluation pipeline）
- [ ] 自動跑 baseline 比較
- [ ] 結果可視化（tables, plots）
- [ ] Ablation study 設計建議

### ✍️ Phase 3: Paper Writing
- [ ] Related work section 草稿
- [ ] 論文模板準備（LaTeX, conference format）
- [ ] Rebuttal 輔助（reviewer comment 分析 + 回覆草稿）

### 📅 Phase 4: Ongoing
- [ ] Conference deadline tracker（自動提醒 30/14/7 天前）
- [ ] 每週 research summary（本週讀了什麼、有什麼 insight）
- [ ] 追蹤競爭者的新工作

## 🔬 Research Direction: Mech Interp × Speech Multimodal LM

### Why This Is Gold
- arXiv 上 "mechanistic interpretability" + "speech" 只有 **4 篇論文**
- Multimodal mech interp survey (2025-02) **幾乎沒覆蓋 speech**
- Vision 有 toolkit (Prisma)，speech **沒有**
- AI Safety 社群做 LLM interp，**沒人做 speech safety**

### Paper Ideas（優先級排序）
1. 🥇 **Mech Interp of Speech Understanding in Omni-LLMs** → NeurIPS/ICLR
2. 🥈 **SpeechLens Toolkit** → EMNLP Demo / Interspeech
3. 🥉 **Audio Adversarial × Mech Interp = Safety** → NeurIPS SafeGenAI

### Must-Read List
- [ ] Beyond Transcription: Mech Interp in ASR (2025-08)
- [ ] Behind the Scenes: Whisper LoRA Mech Interp (2025-09)
- [ ] What Do Neurons Listen To (2026-02)
- [ ] Survey on Mech Interp for MMFMs (2025-02)
- [ ] Prisma toolkit (2025-04)
- [ ] Visual Representations inside LM (2025-10)

---

*下次更新：深讀 must-read list，設計實驗方案*
