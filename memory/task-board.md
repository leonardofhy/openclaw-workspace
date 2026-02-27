# Task Board — Global

> 單一任務看板，Lab + MacBook 共用。每次 session 開始、每次 heartbeat 都掃一眼。
> ID 規則：`L-xx`（Lab bot）、`M-xx`（MacBook bot）
> 最後更新：2026-02-28 01:13

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
- **last_touched**: 2026-02-28
- **描述**: 用 battleship 跑 chunk sensitivity，定位可能的 listen-layer 訊號
- **progress**: smoke run（n=4,k=3,20 samples）完成；full run 進行中（21:46 時點：`n4_chunk3` 3562 行、`n5_chunk0` 1188 行）；已重提 n5 任務 `job 224422`（RUNNING）；夜間已把 merge-to-main 流程修穩，早上可無阻接續實驗收尾
- **next_action**: 明早第一段先檢查 n4/n5 任務是否完成；完成則立即跑 evaluate 產生 `*_comprehensive_results.json`，並更新 `chunk_sensitivity_desta25.md` v2（Method/Results Δ 表）；未完成則 11:30 再次檢查
- **blockers**: GPU 資源排隊/同機器並行導致完成時間波動

### M-02 | 論文產出（Results v0）
- **owner**: MacBook
- **priority**: P0
- **created**: 2026-02-27
- **last_touched**: 2026-02-28
- **描述**: AudioMatters 論文 Results section 初稿（承接已完成的 Method v1 + Setup v1）
- **progress**: Leo 回報 Method 第一版與 Setup 第一版已完成；Results v0 寫作包已補上 40 分鐘 kickoff 清單（填表→主敘事→ablation）
- **next_action**: 早上第一個寫作時段先完成 kickoff 清單前 2 項（Table X 數字 + hardest subset），中午前交付 Main Results 四句版本

### M-03 | 研究雙軌推進
- **owner**: MacBook
- **priority**: P1
- **created**: 2026-02-27
- **last_touched**: 2026-02-28
- **描述**: 不被單一討論卡住，維持主線 + 備線
- **progress**: 已納入 Leo 新指示：autodidact 恢復 30 分鐘 cadence，新增 meta-awareness 自我改進模式（避免 execution-blocked 連續 skip）；已建立 `meta-awareness-board.md` 與 `experiment-queue.md`
- **next_action**: 主線持續推進；備線改為 listen-layer 三步循環（Exp1 attention suppression → Exp2 activation patching → Exp3 layer-restricted LoRA）；blocked 時優先執行 meta-audit 第 1 項（novelty classifier 草案）

### L-01 | 系統環境搭建
- **owner**: Lab
- **priority**: P0
- **created**: 2026-02-27
- **last_touched**: 2026-02-27
- **描述**: WSL 環境完整搭建 — pip、Python 套件、secrets 同步
- **next_action**: 安裝 pip + google-auth/gspread/google-api-python-client；從 Mac 搬 secrets
- **blockers**: 需要 sudo 權限裝 pip，或找替代方案（conda/uv）
- **deadline**: 2026-02-28

### L-02 | Bot 間通訊穩定化
- **owner**: Lab
- **priority**: P1
- **created**: 2026-02-27
- **last_touched**: 2026-02-27
- **描述**: 確保 Lab bot 和 MacBook bot 能在 #bot-sync 即時對話
- **next_action**: 確認 Mac bot 設了 allowBots=true；測試雙向自動回覆
- **depends_on**: Mac bot 設定
- **deadline**: 2026-02-28

### L-03 | Autodidact GPU 實驗環境
- **owner**: Lab
- **priority**: P1
- **created**: 2026-02-27
- **last_touched**: 2026-02-27
- **描述**: 在 Lab 機器（2x RTX PRO 6000）建立 Tier 1-2 實驗環境
- **next_action**: 安裝 transformerlens + pyvene + s3prl；驗證 GPU 可用
- **deadline**: 2026-03-01

### L-04 | Cron 系統建立
- **owner**: Lab
- **priority**: P2
- **created**: 2026-02-27
- **last_touched**: 2026-02-27
- **描述**: 在 Lab 機器設定 cron jobs（heartbeat、autodidact、排程刷新等）
- **next_action**: 參考 Mac 的 cron 設定，建立 Lab 版本
- **deadline**: 2026-03-02

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

### L-05 | Secrets 同步
- **owner**: Lab
- **priority**: P0
- **created**: 2026-02-27
- **last_touched**: 2026-02-27
- **描述**: 從 Mac 搬 secrets 到 WSL（email_ops.env, todoist.env, google-service-account.json）
- **waiting_for**: Mac bot 或 Leo 透過 SSH tunnel 搬檔案
- **next_action**: 確認 secrets 到位後跑 system scanner 驗證

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

### M-01 | Battleship 實驗工作流固化
- **owner**: MacBook
- **completed**: 2026-02-27
- **成果**: `~/Workspace/little-leo` 建置完成；交付 `run_cpu.sh` / `run_gpu.sh` / `check_jobs.sh` / `check_cli.sh` / `run_claude_once.sh` / `launch_claude_tmux.sh`；compute node 可執行 Claude Code（載入 nvm）

### M-00 | 建立多任務追蹤機制
- **owner**: MacBook
- **completed**: 2026-02-27
- **成果**: task-ledger.md 建立（現已遷移至本檔）
