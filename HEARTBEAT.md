# HEARTBEAT.md - Periodic Checks

> 核心原則：**沉默是金。只在有意義時才開口。**
> #general 是給人看的，不是機器日誌。

## 決策流程（每次 heartbeat）

### Step 1: Self-Awareness（內部，不發訊息）
1. `python3 skills/self-improve/scripts/learn.py review` — 檢查 pending
2. `python3 skills/self-improve/scripts/learn.py stats` — 看趨勢
3. 有 pending > 7 天的 → **立即 promote 或 resolve**（見 Learnings TTL）
4. 有 recurrence ≥ 3 的 error → **觸發 Fix-First Protocol**（見 PROACTIVE.md §10）

### Step 2: 系統快檢（每次挑 1-2 個）
- `python3 skills/shared/ensure_state.py` → 確保 state files 存在（首次 boot 自動建立）
- `git status --short` → 有未 commit 就 commit + push
- `python3 skills/task-check.py` → 有 alert 就處理
- SSH tunnel 存活檢查
- 輪替項目（見下方）

### Step 3: 決定是否通知

**🚨 Anti-Spam Rule（最高優先）：**
1. 讀 `memory/heartbeat-state.json` 的 `recent_alerts`
2. 如果你要發的 alert **內容本質上和過去 24h 內已發的一樣**（同一個 task stale、同一個系統故障、同一個 deadline），**不要發**
3. 只有在 **狀態改變** 時才重新通知（例：stale task 被修了又 stale、新的故障、deadline 進入更緊急階段）
4. 發完 alert 後，寫入 `heartbeat-state.json`：`recent_alerts[<key>] = {ts, summary}`
5. 每次 heartbeat 開始時清理 >24h 的舊 entries

```
IF 有 NEW actionable alert（之前 24h 沒發過同樣的）
  → 修復問題（能修的先修）
  → 發 #general：簡短說發生什麼 + 你做了什麼 + Leo 需要做什麼（如有）
  → 更新 heartbeat-state.json
  → 不需要固定模板，說人話

ELSE IF 有 actionable alert 但已通知過
  → 不發 #general（已通知，等 Leo 或等狀態變化）
  → 可以寫到 memory/YYYY-MM-DD.md 記錄你檢查過了

ELSE IF 做了有意義的工作（修 bug、推進任務、清理 learnings）
  → 寫到 memory/YYYY-MM-DD.md
  → 發 #bot-logs：簡短記錄（供事後 audit）
  → 不發 #general

ELSE（什麼都沒發生，一切正常）
  → HEARTBEAT_OK（沉默）
```

## 輪替檢查（每次挑 1-2 個做）

### 📅 行事曆 & 任務 & Deadlines
- 跑 `python3 skills/task-check.py`，有 alert 就處理
- 跑 `python3 skills/deadline_watch.py --days 14`，有 urgent/overdue 就通知 Leo
- 檢查 2 小時內行事曆事件，需要就設 cron 提醒

### 🔄 Task Board ↔ Todoist 同步
- `python3 skills/shared/task_sync.py --sync` — 雙向同步 task-board 和 Todoist
- Push: ACTIVE 任務的 next_action → Todoist（label TB_<id>）
- Pull: Todoist 完成的 TB_ 任務 → 更新 task-board last_touched + progress

### 🔀 Git 同步
- `git status --short`，有未 commit 的就自動 commit + push

### ⏱️ Cron 健康檢查（每次 heartbeat）
- `python3 skills/shared/cron_monitor.py --alert`
- 有 alert（MISSED/FAILING/STALE/SLOW）→ 視嚴重度通知 #general 或記錄 #bot-logs
- 狀態寫入 `memory/cron-health.json`

### 🔧 系統健康（每週一次）
- 跑 `python3 skills/system-scanner/scripts/scan.py`
- 🔴 立刻通知 Leo（#general），⚠️ 記錄到 memory

### 📡 SSH 隧道
- 確認 tunnel 存活，斷了就重建（不只是報告）

### 📝 記憶維護（每 2-3 天）
- 今天的 memory/YYYY-MM-DD.md 是否存在
- MEMORY.md 是否需要更新（注意 ≤80 行 budget）

### 📏 Boot Budget 檢查（每週一次）
- 跑 `python3 skills/shared/boot_budget_check.py`
- exit 1 (⚠️ 接近上限) → 主動瘦身（evict 舊內容到 memory-full.md 或 archive）
- exit 2 (🔴 超過上限) → 立即處理，不等下次 heartbeat
- SESSION-STATE.md: archive >48h 的 Recent Context 到 daily memory

### 🧹 Todoist 衛生（每 3 天一次）
- 跑 `python3 skills/shared/todoist_hygiene.py` — 自動清重複 + flag 過期
- 會自動刪除精確重複的任務
- 會 flag 相似度高的任務給 Leo 確認
- 會 flag >3 天過期的任務
- 結果寫入 `memory/heartbeat-state.json`

### 🔄 Learnings 清理（每週一次，或 pending > 5 時）
- 跑 `learn.py review`
- recurrence ≥ 3 → promote（加到對應 .md）
- pending > 7 天 → 必須 resolve 或 escalate
- 目標：pending ≤ 3

## 頻道規則
- **#general**（`978709248978599979`）：**只發真正重要的事**（系統故障、需要 Leo 立刻決策、重大 milestone）。Bot 之間的通訊**不准用 #general**
- **#bot-logs**（`1477354525378744543`）：機器日誌、routine 工作記錄、self-awareness、daily growth report
- **#bot-sync**（`1476624495702966506`）：跨 bot 通訊、@mention、mailbox 通知
- Bot 之間的所有互動 → **#bot-sync**（即時）或 **#bot-logs**（記錄）
- 深夜 (23:00-08:00) 不發 #general，除非緊急
- #bot-logs 和 #bot-sync 不受時間限制
