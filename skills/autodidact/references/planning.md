# 📋 Plan Action — Research-First Planning

> 參考 Claude Code Plan Mode + Codex 設計：先讀、再問、再規劃、最後才執行。

## 核心原則

1. **Read-only first** — Plan 階段只讀不寫（除了最終輸出 plan 本身）
2. **Ask, don't assume** — 遇到不確定的方向性問題，列出來等 Leo 判斷，不自己猜
3. **Thoroughness scales** — 不是每次 plan 都要花 10 分鐘，按需求分級
4. **Plan ≠ Execute** — Plan 的輸出是一份可審閱的提案，不是直接行動

## 觸發條件（任一成立）
- goals.md 超過 7 天沒更新
- Leo 給了新方向 feedback
- 遇到重大 blocker 或機會
- 連續 5+ cycles 沒有 plan
- 外部環境變化（新 deadline、新論文改變 landscape）

## Thoroughness Levels

| Level | 花費 | 適用場景 |
|-------|------|---------|
| **quick** (< 2 min) | 讀 goals + progress | 例行檢查，微調下一步 |
| **medium** (< 5 min) | + knowledge-graph + 最近 5 cycles | 週中期調整，整合新資訊 |
| **thorough** (< 10 min) | + 全部狀態檔 + 外部搜索 | 方向性大調整，新 research idea |

先判斷需要哪個 level，避免每次都做 thorough。

## 流程

### Phase 1: GATHER（只讀）

按 thoroughness level 讀取狀態檔：

```
[quick]    goals.md + progress.md（最後 10 行）
[medium]   + knowledge-graph.md + 最近 5 個 cycle notes
[thorough] + conference-pipeline.md + arxiv-radar + 外部搜索
```

### Phase 2: DIAGNOSE

回答三個核心問題：
1. **Position** — 我現在在哪？（一句話）
2. **Target** — 最近的 milestone 是什麼？（3 個月內的具體目標）
3. **Gap** — 從 Position 到 Target 缺什麼？（列 bullets）

### Phase 3: IDENTIFY UNKNOWNS

列出你**不確定的事**。這是最關鍵的步驟 — 好的 plan 不是假裝什麼都知道，而是清楚知道什麼不知道。

分類：
- **可以自己解決的** → 排進 cycle 計劃（learn / build / skill-up）
- **需要 Leo 判斷的** → 加入「Questions for Leo」
- **需要外部資源的** → 加入「待請求 Leo 的任務隊列」

### Phase 4: GENERATE OPTIONS

列出 3-5 個下一步選項：

```markdown
| # | 行動 | 類型 | 預期產出 | 所需資源 | 影響力 | 風險 |
|---|------|------|---------|---------|--------|------|
```

每個選項必須通過 **北極星檢驗**：這讓我離 DeepMind/Anthropic 等級更近嗎？

### Phase 5: PROPOSE（不是 DECIDE）

輸出一份 **plan proposal**，而不是直接開始執行：

- 如果是 **quick** level → 直接排定下 3 cycles，自行執行
- 如果是 **medium** level → 排定下 5 cycles，有 Questions for Leo 的話等回覆
- 如果是 **thorough** level → 寫完整 proposal，**必須等 Leo review 後才執行方向性改變**

## 輸出格式

```markdown
# 🧠 Cycle #NN — YYYY-MM-DD HH:MM
## Action: plan [quick|medium|thorough]
## Context: [為什麼需要 plan]

## Position
[一句話描述現狀]

## Target (3-month milestone)
[具體目標]

## Gap Analysis
- [1] ...
- [2] ...

## Unknowns
### 可自行解決
- ...
### ❓ Questions for Leo
- ...
### 🔧 需要 Leo 幫忙
- ...

## Options
| # | 行動 | 影響力 | 可行性 | 推薦 |
|---|------|--------|--------|------|

## Proposed Plan (next N cycles)
1. Cycle N+1: [行動] — [預期產出]
2. Cycle N+2: ...

## Tags: #plan
```

## Anti-patterns
- ❌ 連續 2 次 plan → 強制切到 learn/build（防止空轉）
- ❌ thorough plan 完不等 Leo review 就改方向
- ❌ Plan 裡只有模糊的「繼續研究」— 每個 cycle 要有具體 deliverable
- ❌ 假裝知道答案 — 不確定就列進 Unknowns
- ❌ 選項只有 1 個 — 至少 3 個，避免 tunnel vision
