# Task Board — Global

> 單一任務看板，Lab + MacBook 共用。每次 session 開始、每次 heartbeat 都掃一眼。
> ID 規則：`L-xx`（Lab bot）、`M-xx`（MacBook bot）
> 最後更新：2026-02-27 20:56

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

### M-01 | Battleship 實驗工作流固化
- **owner**: MacBook
- **priority**: P1
- **created**: 2026-02-27
- **last_touched**: 2026-02-27
- **描述**: 在 Battleship（`~/Workspace/little-leo`）固化實驗工作流
- **progress**: SSH 可用、路徑修正到 `~/Workspace`、CPU smoke + 背景 job 可跑
- **next_action**: 建 `run_cpu.sh` / `run_gpu.sh` / `logs/`；在 compute node 驗證 Claude Code
- **blockers**: 叢集上 Claude Code 可用安裝路徑/模組資訊（可能需要 Leo 協助）

### M-02 | 論文產出（Method v0）
- **owner**: MacBook
- **priority**: P0
- **created**: 2026-02-27
- **last_touched**: 2026-02-27
- **描述**: AudioMatters 論文 Method section 初稿
- **next_action**: 交付可寫入稿件的一頁骨架 + placeholder 實驗敘事

### M-03 | 研究雙軌推進
- **owner**: MacBook
- **priority**: P1
- **created**: 2026-02-27
- **last_touched**: 2026-02-27
- **描述**: 不被單一討論卡住，維持主線 + 備線
- **next_action**: 主線持續推進；備線：Listen layer 快驗 / neuron grounding / modality reliance stress test

### L-06 | 重構收尾（comms_tracker + sync_report + task-check） ✅
- **owner**: Lab
- **completed**: 2026-02-27
- **成果**: 3 個腳本全部用 shared JsonlStore/find_workspace，消除 16 行重複代碼

### L-07 | SYNC_PROTOCOL 落地驗證
- **owner**: Lab
- **priority**: P2
- **created**: 2026-02-27
- **last_touched**: 2026-02-27
- **描述**: 驗證混合同步協議實際運作：每日 merge、[STATE] 通知、reconcile
- **next_action**: 等 Mac Leo 完成 merge 後做第一次 smoke test

### L-03 | Autodidact GPU 實驗環境
- **owner**: Lab
- **priority**: P1
- **created**: 2026-02-27
- **last_touched**: 2026-02-27
- **描述**: 在 Lab 機器（2x RTX PRO 6000）建立 Tier 1-2 實驗環境
- **next_action**: 安裝 transformerlens + pyvene + s3prl；驗證 GPU 可用
- **deadline**: 2026-03-01

### L-04 | Cron 系統建立 ✅
- **owner**: Lab
- **completed**: 2026-02-27
- **成果**: 5 個 cron jobs — heartbeat (30min), scanner (06:00), merge (08:00), calendar (13:00), tunnel watchdog (2h)

## WAITING

### M-04 | 排程同步一致性
- **owner**: MacBook
- **priority**: P2
- **created**: 2026-02-27
- **last_touched**: 2026-02-27
- **描述**: schedule → GCal → Todoist 同步
- **waiting_for**: 規則確認（只改現在/未來；不得刪除過去事件）
- **source**: `memory/scheduling-rules.md`

### M-05 | Autodidact hourly cron 健康確認
- **owner**: MacBook
- **priority**: P2
- **created**: 2026-02-27
- **last_touched**: 2026-02-27
- **描述**: 先前 timeout，已改每小時 + timeout 600s
- **waiting_for**: 檢查下一輪 run 是否恢復 ok


## BLOCKED

（無）

## PARKED

（無）

## DONE

### L-00 | Discord Server 通訊設定
- **owner**: Lab
- **completed**: 2026-02-27
- **成果**: groupPolicy 改 open、allowBots=true、BOT_RULES.md 建立、#bot-sync 頻道啟用

### L-00b | Git 分支同步
- **owner**: Lab
- **completed**: 2026-02-27
- **成果**: macbook-m3 merge 到 lab-desktop（+5788 行，38 commits）

### M-00 | 建立多任務追蹤機制
- **owner**: MacBook
- **completed**: 2026-02-27
- **成果**: task-ledger.md 建立（現已遷移至本檔）

### L-01 | 系統環境搭建
- **owner**: Lab
- **completed**: 2026-02-27
- **成果**: pip (via get-pip.py)、google-auth/gspread/google-api-python-client 安裝完成；Python 3.12 確認可用

### L-02 | Bot 間通訊穩定化
- **owner**: Lab
- **completed**: 2026-02-27
- **成果**: allowBots=true 雙邊確認、ping/pong 測試通過、SYNC_PROTOCOL.md 建立並獲 Mac 確認

### L-05 | Secrets 同步
- **owner**: Lab
- **completed**: 2026-02-27
- **成果**: email_ops.env, todoist.env, google-service-account.json 從 Mac 搬入；Todoist、GCal、Diary、SMTP 全部驗證通過
