# Mailbox (Lab ↔ Mac)

> 可靠的跨 bot 通訊管道。Git-backed，guaranteed delivery on boot。

## 使用方式

**Store**: `memory/mailbox/messages.jsonl`
**IDs**: `MB-xxx`（auto-increment）
**Status**: `open` → `acked` → `done`

### 指令
```bash
# 發送
python3 skills/coordinator/scripts/mailbox.py send --to mac --subject "..." --body "..." [--urgent]

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

### 為什麼不只用 Discord
- Discord #bot-sync 是 best-effort（對方可能離線）
- Git mailbox 是 guaranteed（只要 boot 就會讀到）
- 兩者並行：Discord 求快，Git 求穩

### Critical Change Protocol
修改核心檔案（AGENTS/SOUL/HEARTBEAT/PROACTIVE/GROWTH/SYNC_PROTOCOL）時：
1. 寫 mailbox `--urgent`
2. Discord @mention 對方
3. 對方收到後 git pull + ACK + 確認 boot flow
