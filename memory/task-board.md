# Task Board — Little Leo (Lab)

> 單一任務看板。每次 session 開始、每次 heartbeat 都掃一眼。
> 最後更新：2026-02-27

## 規則

### 容量限制
- **最多 5 個 ACTIVE 任務**（認知負荷上限）
- 超過 5 個必須 PARK 或完成一個才能加新的
- WAITING/BLOCKED 不算在額度內，但總數不超過 10

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
3. 挑 1-2 個 ACTIVE 任務推進
4. 更新 last_touched 和 next_action

### 每次完成任務時
1. 狀態改 DONE，記錄完成日期和成果
2. 移到 Done 區
3. Done 區超過 10 個時，舊的移到 `memory/task-archive.md`

---

## ACTIVE

### T-10 | 系統環境搭建
- **優先級**: P0
- **created**: 2026-02-27
- **last_touched**: 2026-02-27
- **描述**: WSL 環境完整搭建 — pip、Python 套件、secrets 同步
- **next_action**: 安裝 pip + google-auth/gspread/google-api-python-client；從 Mac 搬 secrets
- **blockers**: 需要 sudo 權限裝 pip，或找替代方案（conda/uv）
- **deadline**: 2026-02-28

### T-11 | Bot 間通訊穩定化
- **優先級**: P1
- **created**: 2026-02-27
- **last_touched**: 2026-02-27
- **描述**: 確保 Lab bot 和 MacBook bot 能在 #bot-sync 即時對話
- **next_action**: 確認 Mac bot 設了 allowBots=true；測試雙向自動回覆
- **depends_on**: Mac bot 設定
- **deadline**: 2026-02-28

### T-12 | Autodidact GPU 實驗環境
- **優先級**: P1
- **created**: 2026-02-27
- **last_touched**: 2026-02-27
- **描述**: 在 Lab 機器（2x RTX PRO 6000）建立 Tier 1-2 實驗環境
- **next_action**: 安裝 transformerlens + pyvene + s3prl；驗證 GPU 可用
- **deadline**: 2026-03-01

### T-13 | Cron 系統建立
- **優先級**: P2
- **created**: 2026-02-27
- **last_touched**: 2026-02-27
- **描述**: 在 Lab 機器設定 cron jobs（heartbeat、autodidact、排程刷新等）
- **next_action**: 參考 Mac 的 cron 設定，建立 Lab 版本
- **deadline**: 2026-03-02

## WAITING

### T-14 | Secrets 同步
- **優先級**: P0
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

### T-09 | Discord Server 通訊設定
- **completed**: 2026-02-27
- **成果**: groupPolicy 改 open、allowBots=true、BOT_RULES.md 建立、#bot-sync 頻道啟用

### T-08 | Git 分支同步
- **completed**: 2026-02-27
- **成果**: macbook-m3 merge 到 lab-desktop（+5788 行，38 commits）
