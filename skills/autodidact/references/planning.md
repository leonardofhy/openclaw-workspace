# 📋 Plan Action — Detailed Procedure

> 當 DECIDE 階段選擇 "plan" 時，按以下流程執行。

## 觸發條件（任一成立）
- goals.md 超過 7 天沒更新
- Leo 給了新的方向 feedback
- 遇到重大 blocker 或機會
- 連續 5+ cycles 沒有 plan
- 外部環境變化（新 deadline、新論文改變 landscape）

## 流程

### Phase 1: 盤點現狀 (2 min)

讀取以下檔案，建立當前狀態的 mental model：

```
goals.md        → 北極星 + 當前方向 + knowledge gaps
progress.md     → 最近做了什麼、什麼在動、什麼卡住
knowledge-graph.md → 知識結構、空白處
conference-pipeline.md → deadline 壓力
```

回答三個問題：
1. **我現在在哪？** — 用一段話描述當前狀態
2. **目標在哪？** — 最近的 milestone 是什麼（3 個月內）
3. **差距是什麼？** — 從現在到 milestone 之間缺什麼

### Phase 2: 掃描環境 (1 min)

檢查外部變化：
- Leo 最近有沒有新的 feedback 或方向調整？（檢查 goals.md 底部的任務隊列）
- 有沒有新的 deadline 迫近？
- 最近讀的論文有沒有改變 landscape？
- 有沒有等待 Leo 處理的 request？

### Phase 3: 生成選項 (2 min)

基於差距和環境，列出 3-5 個可能的下一步行動：

```markdown
| # | 行動 | 類型 | 預期產出 | 需要資源 | 影響力 |
|---|------|------|---------|---------|-------|
| 1 | ... | learn/build/... | ... | 時間/GPU/Leo | H/M/L |
```

每個選項必須回答：
- 這個行動讓我離北極星更近了嗎？
- 投入產出比如何？
- 有沒有依賴項（需要先做別的、需要 Leo 幫忙）？

### Phase 4: 選擇 + 排序 (1 min)

用這個決策框架排序：

1. **Blocker-first** — 如果有東西卡住了後續所有工作，先解決它
2. **Deadline-driven** — 有 deadline 的優先
3. **High-leverage** — 一個行動能解鎖多個後續行動
4. **Knowledge compounds** — 學習類行動在早期優先（地基要先打）
5. **Leo's energy** — 需要 Leo 幫忙的事，考慮他的時間和狀態

輸出：排序後的 **接下來 3-5 個 cycle 的行動計劃**

### Phase 5: 更新檔案 (1 min)

必須更新的：
- `goals.md` — 如果方向或優先級有變化
- `progress.md` — 記錄這次 plan 的結論

視情況更新的：
- `conference-pipeline.md` — deadline 變化
- `knowledge-graph.md` — 新的知識結構認知
- goals.md 底部「待請求 Leo 的任務隊列」— 新的 request

## 輸出格式

```markdown
# 🧠 Cycle #NN — YYYY-MM-DD HH:MM
## Action: plan
## Context: [為什麼現在需要 plan]

## 現狀
[一段話描述]

## 差距分析
- 目標：[最近 milestone]
- 缺少：[1] ... [2] ... [3] ...

## 選項評估
| # | 行動 | 影響力 | 可行性 | 選擇 |
|---|------|--------|--------|------|
| 1 | ... | H | H | ✅ |
| 2 | ... | M | H | ✅ |
| 3 | ... | H | L (需GPU) | ⏳ 請求Leo |

## 接下來 3-5 cycles 計劃
1. Cycle N+1: [行動]
2. Cycle N+2: [行動]
3. Cycle N+3: [行動]

## 待請求 Leo
- [ ] [如果有的話]

## Tags: #plan #direction
```

## Anti-patterns
- ❌ 花 10 分鐘 plan 但沒有具體的 next action
- ❌ Plan 完不更新 goals.md（plan 了等於沒 plan）
- ❌ 永遠在 plan 不去 execute（連續 2 次 plan → 強制切到 learn/build）
- ❌ 選項只有 1 個（至少列 3 個再選，避免 tunnel vision）
