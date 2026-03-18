# Task Board — Global

> 單一任務看板，Lab + MacBook 共用。每次 session 開始、每次 heartbeat 都掃一眼。
> ID 規則：`L-xx`（Lab bot）、`M-xx`（MacBook bot）
> 最後更新：2026-03-13 11:30

## 規則

### 容量限制
- **每台機器最多 5 個 ACTIVE 任務**（認知負荷上限）
- 超過 5 個必須 PARK 或完成一個才能加新的
- WAITING/BLOCKED 不算在額度內，但每台總數不超過 10

### Staleness 偵測
- ACTIVE 任務 **3 天沒更新** → 🔴 標記 STALE，heartbeat 時主動提醒 Leo
- WAITING 任務 **7 天沒更新** → 🟡 標記 STALE
- STALE 任務必須在下一次 session 中處理：推進、降級為 PARKED、或關閉

### 狀態定義
- `ACTIVE` — 正在做，每次 session 都要推進
- `WAITING` — 等外部條件（等 Leo、等別人、等資源）
- `BLOCKED` — 卡住了，需要幫助
- `PARKED` — 暫時不做，但不刪除
- `DONE` — 完成

### 每次 Session 起床流程
1. 讀 task-board.md
2. 檢查 staleness（距離 last_touched 天數）
3. 挑 1-2 個自己的 ACTIVE 任務推進
4. 更新 last_touched 和 next_action

### 每次完成任務時
1. 狀態改 DONE，記錄完成日期和成果
2. 移到 Done 區
3. Done 區超過 10 個時，舊的移到 `memory/task-archive.md`

---

## ACTIVE

### M-06 | DeSTA2.5 Listen-layer 快驗（A 路線）
- **owner**: MacBook
- **priority**: P0
- **created**: 2026-02-27
- **last_touched**: 2026-03-13
- **描述**: 用 battleship 跑 chunk sensitivity，定位可能的 listen-layer 訊號
- **progress**: smoke run 完成；full run 結果待確認（Leo 近期忙 NTUAIS + lab admin，研究暫停）
- **next_action**: 等 Leo 回到研究模式後檢查 n4/n5 結果

### M-02 | 論文產出（Results v0）
- **owner**: MacBook
- **priority**: P0
- **created**: 2026-02-27
- **last_touched**: 2026-03-13
- **描述**: AudioMatters 論文 Results section 初稿（承接已完成的 Method v1 + Setup v1）
- **progress**: Method + Setup v1 已完成；Results v0 kickoff 清單待執行（Leo 近期忙雜務）
- **next_action**: 等 Leo 有空時 kickoff Results 寫作（Table X 數字 + hardest subset）

### M-03 | 研究雙軌推進
- **owner**: MacBook
- **priority**: P1
- **created**: 2026-02-27
- **last_touched**: 2026-03-13
- **描述**: 不被單一討論卡住，維持主線 + 備線
- **progress**: autodidact 30min cadence 運行中；meta-awareness board 已建立
- **next_action**: 等研究模式回歸後，推進 listen-layer 三步循環

### L-08 | 財務管理（主線）
- **owner**: Lab
- **priority**: P0
- **created**: 2026-02-27
- **last_touched**: 2026-03-13
- **描述**: 管理 Leo 的財務：獎學金申請追蹤、收入增加策略、支出監控
- **tracker**: memory/finance/FINANCE_TRACKER.md
- **progress**: Pathfinder 逾期 3 天需 follow up（原始 deadline 今天 3/13）；NTU 國際傑出研究生獎學金確認逾期 2 天（原始 3/15）；Leo 表示需要找收入來源（玉山費用討論中浮現）；留華轉賬逾期；僑委會信逾期
- **next_action**: 1) Pathfinder budget 修改 + follow up email（今天！）2) 確認 NTU 國際傑出研究生獎學金時程 3) 需要 Leo 提供最新記帳匯出更新財務快照
- **recurring**: 每週更新一次 FINANCE_TRACKER

### L-07 | SYNC_PROTOCOL 落地驗證
- **owner**: Lab
- **priority**: P2
- **created**: 2026-02-27
- **last_touched**: 2026-03-13
- **描述**: 驗證混合同步協議實際運作：每日 merge、[STATE] 通知、reconcile
- **progress**: SSH tunnels 維修中（iso_leo 預計 3/13 修好，battleship 已恢復），日常 merge cron 受影響
- **next_action**: 等 iso_leo tunnel 恢復後跑一輪端到端 SYNC 驗證

### L-09 | HN 雙時段推薦（移交自 Mac）
- **owner**: Lab
- **priority**: P1
- **created**: 2026-02-28
- **last_touched**: 2026-03-13
- **描述**: 每天 2 次閱讀 Hacker News，分析後推送 Leo 感興趣文章
- **schedule**: 每小時靜默蒐集 + 每天 20:30 推送 top 10
- **progress**: 系統穩定運行中，3/12 已推送 daily digest（10 篇，#7 TADA 語音生成與 Leo 研究相關）
- **next_action**: 持續觀察 digest 品質；等 Leo 反饋調整 profile 權重
- **cron_ids**: `df22eb11`（每小時蒐集, spark）, `76817b6d`（20:30 digest, g53s）

## WAITING

（無）


## BLOCKED

（無）

## PARKED

### M-04 | 排程同步一致性
- **owner**: MacBook | **priority**: P2 | **created**: 2026-02-27
- **描述**: schedule → GCal → Todoist 同步規則確認
- **parked_reason**: 同步已在運行，低優先

### M-05 | Autodidact hourly cron 健康確認
- **owner**: MacBook | **priority**: P2 | **created**: 2026-02-27
- **描述**: 先前 timeout，已改 30min cadence + timeout 600s
- **parked_reason**: 目前穩定運行中，不需主動追蹤

## DONE

（Archived to memory/task-archive.md on 2026-03-13）
