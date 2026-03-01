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
- `git status --short` → 有未 commit 就 commit + push
- `python3 skills/task-check.py` → 有 alert 就處理
- SSH tunnel 存活檢查
- 輪替項目（見下方）

### Step 3: 決定是否通知

```
IF 有 actionable alert（overdue task / broken system / Leo 需要知道的事）
  → 修復問題（能修的先修）
  → 發 #general：簡短說發生什麼 + 你做了什麼 + Leo 需要做什麼（如有）
  → 不需要固定模板，說人話

ELSE IF 做了有意義的工作（修 bug、推進任務、清理 learnings）
  → 寫到 memory/YYYY-MM-DD.md
  → 發 #bot-logs：簡短記錄（供事後 audit）
  → 不發 #general

ELSE（什麼都沒發生，一切正常）
  → HEARTBEAT_OK（沉默）
```

## 輪替檢查（每次挑 1-2 個做）

### 📅 行事曆 & 任務
- 跑 `python3 skills/task-check.py`，有 alert 就處理
- 檢查 2 小時內行事曆事件，需要就設 cron 提醒

### 🔀 Git 同步
- `git status --short`，有未 commit 的就自動 commit + push

### 🔧 系統健康（每週一次）
- 跑 `python3 skills/system-scanner/scripts/scan.py`
- 🔴 立刻通知 Leo（#general），⚠️ 記錄到 memory

### 📡 SSH 隧道
- 確認 tunnel 存活，斷了就重建（不只是報告）

### 📝 記憶維護（每 2-3 天）
- 今天的 memory/YYYY-MM-DD.md 是否存在
- MEMORY.md 是否需要更新

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
