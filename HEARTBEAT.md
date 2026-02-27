# HEARTBEAT.md - Periodic Checks

## 每次 Heartbeat 執行以下檢查（輪替，不需每次全做）：

### 📋 任務看板（每次必做）
- 執行 `python3 skills/task-check.py` 檢查 staleness 和 deadline
- 如果有 🔴 STALE 或 OVERDUE，立刻通知 Leo 並推進任務
- 讀 `memory/task-board.md` 挑 1 個任務推進
- 推進後更新 task-board.md 的 last_touched 和 next_action

### 📅 行事曆 & 任務（高優先）
- 檢查今天剩餘行事曆事件，如果 2 小時內有事件且沒設提醒，立刻設 cron 提醒
- 掃描 Todoist overdue 任務數量，如果 > 5 個，Discord 提醒 Leo 整理

### 📝 記憶維護（每 2-3 天）
- 檢查今天的 memory/YYYY-MM-DD.md 是否存在，不存在則建立
- 如果最近 3 天沒有更新 MEMORY.md，考慮從日記中提煉新 insights

### 🔧 系統健康（每週）
- 執行 `python3 skills/leo-diary/scripts/system_health.py` 做全面健檢
- 如果有 ❌ FAIL，立刻通知 Leo 並嘗試修復
- 如果有 ⚠️ WARN，記錄到今日 memory 檔案

### 🌡️ Leo 的狀態感知
- 如果是深夜 (00:00-03:00) 且 Leo 還在線，溫和提醒早睡
- 如果知道 Leo 生病中（檢查最近 memory），適時關心

### 🔀 Git 同步（每次 heartbeat）
- 執行 `git status --short`，如果有未 commit 的 tracked changes，自動 `git add -A && git commit && git push`
- Commit message 用簡短描述（如 `chore: heartbeat auto-commit`，或描述實際改動）

## 規則
- 不要每次都做所有檢查，挑 1-2 個最需要的
- 深夜 (23:00-08:00) 不主動發訊息，除非緊急
- 如果都不需要做，直接 HEARTBEAT_OK
