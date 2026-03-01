# Mailbox (Lab ↔ Mac)

> 可靠的跨 bot 通訊管道。Git-backed，guaranteed delivery on boot。

## 使用方式

**Store**: `memory/mailbox/messages.jsonl`
**IDs**: `MB-xxx`（auto-increment）
**Status**: `open` → `acked` → `done`

### 指令
```bash
# 發送
python3 skills/coordinator/scripts/mailbox.py send --to mac --title "..." --body "..." [--urgent]

# 查看（boot 時必查）
python3 skills/coordinator/scripts/mailbox.py list --to lab --status open

# 確認收到
python3 skills/coordinator/scripts/mailbox.py ack MB-001

# 標記完成
python3 skills/coordinator/scripts/mailbox.py done MB-001
```

### SLA + ACK 規則
- Discord 委託 **10 分鐘沒 ACK** → 必寫 mailbox（`--urgent`）
- 收到 mailbox → 回 `✅ ACK <MB-id>`
- 完成後 → 回 `✅ DONE <MB-id>`
- Boot/heartbeat 時必查 `list --to <me> --status open`

### ⚠️ Git Sync 規則（重要）
Mailbox 是 Git-backed。**對方寫的訊息在對方的 branch 上。** 
收到 @mention 關於 mailbox 時，必須先 pull：

```bash
# Lab 收到 Mac 的 mailbox 通知：
git fetch origin macbook-m3 && git merge origin/macbook-m3 --no-edit

# Mac 收到 Lab 的 mailbox 通知：
git fetch origin lab-desktop && git merge origin/lab-desktop --no-edit

# 然後才能 list / ack / done
python3 skills/coordinator/scripts/mailbox.py list --to <me> --status open
```

**發送方也要遵守**：send + git push + @mention 三步一起做，缺一不可。

### 為什麼不只用 Discord
- Discord @mention = 即時通道（13 秒級回應，但對方要在線）
- Git mailbox = 離線保底（guaranteed，boot 時讀到）
- **兩者角色不同**：Discord 傳遞通知，mailbox 保存記錄 + 追蹤狀態

### Critical Change Protocol
修改核心檔案（AGENTS/SOUL/HEARTBEAT/PROACTIVE/GROWTH/SYNC_PROTOCOL）時：
1. 寫 mailbox `--urgent` + git push
2. Discord @mention 對方（包含內容摘要，不要只說「去看 mailbox」）
3. 對方收到 → git pull 對方 branch → ACK → 處理 → DONE
