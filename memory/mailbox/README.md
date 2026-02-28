# Mailbox — Cross-Bot Communication

> 兩個 bot 的可靠通訊管道。Git-backed，guaranteed delivery。

## 使用方式

### 發送
寫一條訊息到對方的 inbox：
- Lab → Mac：append to `to-mac.md`
- Mac → Lab：append to `to-lab.md`

### 格式
```markdown
## [YYYY-MM-DD HH:MM] [PRIORITY] Subject
Body（簡短，≤5 行）
**Action needed**: 對方需要做什麼
---
```

Priority: 🔴 URGENT（核心檔案改動）| 🟡 INFO（一般通知）| ⚪ FYI

### 接收
每次 boot 時（AGENTS.md Step 1 之後）：
1. 讀自己的 inbox（`to-lab.md` 或 `to-mac.md`）
2. 處理每條訊息
3. 處理完的訊息移到 `archive/YYYY-MM.md`
4. 清空 inbox

### 為什麼不只用 Discord
- Discord #bot-sync 是 best-effort（對方可能離線、config 沒配好）
- Git mailbox 是 guaranteed（只要 boot 就會讀到）
- 兩者並行：Discord 求快，Git 求穩
