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
- **last_touched**: 2026-03-18
- **描述**: 用 battleship 跑 chunk sensitivity，定位可能的 listen-layer 訊號
- **progress**: smoke run 完成；Q001/Q002 real experiments on Whisper-base done (voicing geometry + causal ablation); 20 mock experiments validate gc framework; Paper A outline drafted
- **next_action**: Scale up Q001/Q002 to Whisper-small/medium on battleship GPU

### M-02 | 論文產出（Results v0）
- **owner**: MacBook
- **priority**: P0
- **created**: 2026-02-27
- **last_touched**: 2026-03-18
- **描述**: AudioMatters 論文 Results section 初稿（承接已完成的 Method v1 + Setup v1）
- **progress**: Method + Setup v1 已完成；Paper A outline skeleton drafted (docs/paper-a-outline.md); 22 experiment results catalogued (unified dashboard); AudioMatters 已投稿 Interspeech 2026
- **next_action**: Paper A prose drafting — fill in §3 Method + §4 Results with real data

### M-03 | 研究雙軌推進
- **owner**: MacBook
- **priority**: P1
- **created**: 2026-02-27
- **last_touched**: 2026-03-18
- **描述**: 不被單一討論卡住，維持主線 + 備線
- **progress**: autodidact 已完成 22 experiments（READY queue 全清）; ideation freeze 啟動（READY < 10 才解凍）; Q117/Q123 診斷中
- **next_action**: Q117/Q123 修復 → 進入 real experiment batch（需 GPU）

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

### L-09 | 多源 Feed 推薦（HN + AF + LW + arXiv）
- **owner**: Lab
- **priority**: P1
- **created**: 2026-02-28
- **last_touched**: 2026-03-18
- **描述**: 每天多次從 HN、AlignmentForum、LessWrong、arXiv 蒐集並推送 Leo 感興趣文章，使用 skills/feed-recommend（已取代舊 skills/hn-recommend）
- **schedule**: 每小時靜默蒐集 + 每天 20:30 推送 top 10
- **progress**: feed-recommend 已完全覆蓋舊 hn-recommend 功能（HN 抓取、評分、dedup、digest）；profile 仍讀取 memory/hn/preferences.json
- **next_action**: 持續觀察 digest 品質；等 Leo 反饋調整 profile 權重
- **cron_ids**: `df22eb11`（每小時蒐集, spark）, `76817b6d`（20:30 digest, g53s）

### M-07 | LALM Knowledge Editing 研究（主力方向）
- **owner**: MacBook
- **priority**: P0
- **created**: 2026-03-24
- **last_touched**: 2026-03-24
- **描述**: Knowledge Editing × Large Audio Language Models 交叉研究，每週一下午和智凱哥、彥廷 meeting
- **phase**: Survey（Week 1-4）
- **progress**: 研究地圖、閱讀路線圖（35 篇）、每日論文偵察工具已建立；dry-run 成功找到直接相關論文
- **next_action**: 本週讀完 Phase 1 P0 papers（ROME, MEMIT, SALMONN, Qwen-Audio, multimodal KE survey）
- **resources**: `memory/lalm-ke/` (landscape, reading-roadmap, daily-workflow, survey-notes-template)
- **cron**: daily_scout.py (待設)
- **meeting**: 每週一下午（智凱哥 + 彥廷）

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
