# HEARTBEAT.md - Periodic Checks

## 🔴 必做：30 分鐘工作匯報（每次 heartbeat）

**每次 heartbeat 都要發一則 Discord 訊息給 Leo**（channel: discord, target: 756053339913060392）：

格式：
```
🦁 [HH:MM] Lab Status
▶ 剛完成：<上 30 分鐘做了什麼，1-2 行>
▶ 接下來：<下 30 分鐘要做什麼，具體到任務 ID 和動作>
▶ 卡點：<如果有卡住的事，沒有就省略>
```

規則：
- **必須發**，不能跳過，不能只 HEARTBEAT_OK
- 簡短，3-5 行以內
- 有實質內容（不是「一切正常」這種廢話）
- 如果上 30 分鐘沒做任何事，要寫為什麼 + 接下來打算怎麼推進

## 輪替檢查（每次挑 1-2 個做）

### 📅 行事曆 & 任務
- 跑 `python3 skills/task-check.py`，有 alert 就報告
- 檢查 2 小時內行事曆事件，需要就設 cron 提醒

### 🔀 Git 同步
- `git status --short`，有未 commit 的就自動 commit + push

### 🔧 系統健康（每週一次）
- 跑 `python3 skills/system-scanner/scripts/scan.py`
- 🔴 立刻通知 Leo，⚠️ 記錄到 memory

### 📡 SSH 隧道
- 確認 tunnel 存活，斷了就重建

### 📝 記憶維護（每 2-3 天）
- 今天的 memory/YYYY-MM-DD.md 是否存在
- MEMORY.md 是否需要更新

## 規則
- 深夜 (23:00-08:00) 不發非緊急訊息
- 工作匯報是唯一不能省的
