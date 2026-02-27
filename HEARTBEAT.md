# HEARTBEAT.md - Periodic Checks

## 🔴 必做：30 分鐘 Self-Awareness + 工作匯報（每次 heartbeat）

**每次 heartbeat 必須執行以下流程，然後發 Discord 訊息給 Leo**（target: `978709248978599979`（#general））：

### Step 1: Self-Awareness（自我檢視）
1. `python3 skills/self-improve/scripts/learn.py review` — 檢查 pending learnings/errors
2. `python3 skills/self-improve/scripts/learn.py stats` — 看整體趨勢
3. 回顧上 30 分鐘：有沒有犯錯、卡住、或做得不夠好的地方？
4. 如果發現問題 → **立刻修**（不是記下來以後修），然後 log 到 learn.py
5. 如果有 ⚡PROMOTE ready 的 → 執行 promotion

### Step 2: 系統快檢（每次挑 1-2 個）
- `git status --short` → 有未 commit 就 commit + push
- `python3 skills/task-check.py` → 有 alert 就處理
- SSH tunnel 存活檢查
- 其他輪替項目（見下方）

### Step 3: 報告（必發）
```
🦁 [HH:MM] Lab Self-Awareness
📊 系統：<learn.py stats 摘要>
🔍 反思：<這 30 分鐘做得如何？有什麼問題？>
🔧 改進：<做了什麼改進？或「無需改進」>
▶ 剛完成：<上 30 分鐘做了什麼>
▶ 接下來：<下 30 分鐘要做什麼>
```

規則：
- **必須發**，不能跳過，不能只 HEARTBEAT_OK
- 反思要有實質內容（不是「一切正常」）
- 如果做了改進，要寫具體改了什麼
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

### 🔄 Self-Improvement Review（每週一次）
- 跑 `python3 skills/self-improve/scripts/learn.py review`
- 有 ⚡PROMOTE 的就執行 promotion（加到對應的 .md 檔）
- 跑 `learn.py stats` 看整體趨勢

## 規則
- 深夜 (23:00-08:00) 不發非緊急訊息
- 工作匯報是唯一不能省的
