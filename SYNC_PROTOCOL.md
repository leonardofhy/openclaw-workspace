# SYNC_PROTOCOL.md — Lab ↔ Mac 同步協議

> 兩個 bot 的共識文件。更動需雙方確認。
> 生效日：2026-02-27

## 架構：混合同步（Hybrid with delivery guarantees）

```
即時通知（best effort） ──→ Discord #bot-sync @mention（秒級）
保底投遞（guaranteed）   ──→ Git mailbox（memory/mailbox/messages.jsonl）
持久同步                ──→ Git merge（每日）
衝突預防                ──→ Namespace 隔離（L- / M-）
```

---

## 1. 即時層：Discord `#bot-sync`

### 訊息格式

狀態變更、求助、資訊分享用固定 prefix，方便 parse：

| Prefix | 用途 | 範例 |
|--------|------|------|
| `[STATE]` | 任務狀態變更 | `[STATE] L-01 → DONE \| 環境搭建完成` |
| `[HELP]` | 卡住求助 | `[HELP] L-03 blocked: battleship SSH 斷了` |
| `[INFO]` | 重要發現/通知 | `[INFO] scanner regex bug 已修` |
| `[MERGE]` | Git 操作通知 | `[MERGE] lab-desktop pushed: 1e3b4fd` |
| `[PING]` | 健康檢查 | `[PING] 🏓` → 回 `[PONG] branch: xxx, commit: xxx` |

### 規則

- **只發有意義的訊息**，不閒聊（見 BOT_RULES.md）
- 每次改自己的任務狀態 → 發一條 `[STATE]`
- 每次 git push → 發一條 `[MERGE]`
- 收到對方的 `[STATE]` → 更新自己本地的 task-board（對方 namespace 區塊）
- 收到 `[HELP]` → 盡快回覆，不能幫就說

### 頻率限制

- 遵守 BOT_RULES.md：**3 來回 / 30 分鐘**
- 批量更新時合併成一條（不要連發 5 條 [STATE]）

### SLA + ACK（必須）

對每一個委託訊息（`📤 委託 ...`）：

1. **先走 Discord @mention**（即時）
2. 接收方 **10 分鐘內需回 ACK**：
   - `✅ ACK <task-id> | accepted | ETA ...`
3. 若 10 分鐘未收到 ACK：
   - 發送方必須寫入 Git mailbox（`--urgent`）
   - 並在 #bot-sync 補一條 fallback 通知
4. 接收方 boot/session start 時必查 mailbox open items，並回：
   - `✅ ACK <MB-id>/<task-id>`
   - 完成後 `✅ DONE <MB-id>/<task-id>`

### Mailbox CLI（標準）

```bash
# 送出保底訊息
python3 skills/coordinator/scripts/mailbox.py send \
  --from lab --to mac --title "L-09 handoff" --body "..." --task-id L-09 --urgent

# 開機/開 session 必查
python3 skills/coordinator/scripts/mailbox.py list --to mac --status open

# 接收後立即 ack
python3 skills/coordinator/scripts/mailbox.py ack MB-001

# 完成後關單
python3 skills/coordinator/scripts/mailbox.py done MB-001
```

---

## 2. 持久層：Git

### Branch 策略

```
main（穩定基線，每 3 天 merge）
├── lab-desktop（Lab bot 工作分支）
└── macbook-m3（Mac bot 工作分支）
```

### 每日 Cross-Merge（08:00 或第一次 heartbeat）

**Lab bot 流程：**
```bash
git fetch origin
git merge origin/macbook-m3 --no-edit
# 如果有 conflict → 只改自己 namespace 的部分，對方的保留 theirs
git push
```

**Mac bot 流程：**
```bash
git fetch origin
git merge origin/lab-desktop --no-edit
git push
```

### Merge 到 main（每 12 小時，via PR，錯開）

每個 branch 各自每 12 小時開 PR merge 到 main，兩個 bot 錯開 6 小時：

| 時間 | 負責 bot | 動作 |
|------|---------|------|
| **08:00, 20:00** | **Lab bot** | `lab-desktop → main` (PR) |
| **14:00, 02:00** | **Mac bot** | `macbook-m3 → main` (PR) |

**自動化腳本：** `scripts/merge-to-main.sh`

流程：
1. Cross-merge（先拉對方 branch）
2. 檢查是否有新 commits vs main（沒有就 skip）
3. 檢查是否已有 open PR（有就 skip）
4. `gh pr create` → `gh pr merge`（auto-merge）
5. 拉回 main 到自己的 branch

**失敗處理：**
- Merge conflict → 在 `#bot-sync` 發 `[HELP]`
- 無新 commit → skip，不發訊息
- PR 已存在 → skip

### Cross-Merge 後（每日）

1. 跑 `python3 skills/task-check.py` 確認 task board 一致
2. 在 `#bot-sync` 發 `[MERGE] 完成，commit: xxx`
3. 如果有 conflict 解不了 → 發 `[HELP]` 找對方或 Leo

---

## 3. 衝突預防：Namespace 隔離

### Task Board（`memory/task-board.md`）

- **L-xx 任務：只有 Lab bot 改狀態**
- **M-xx 任務：只有 Mac bot 改狀態**
- 共用區塊（規則、header）：**只在 merge 時統一調整，不要兩邊同時改**

### 其他共用檔案

| 檔案 | 規則 |
|------|------|
| `MEMORY.md` | 只有 main session 的 bot 更新（通常是 Mac） |
| `TOOLS.md` | 誰加新工具誰更新，用 append-only 避免衝突 |
| `experiments.jsonl` | EXP-ID 全域遞增，machine 欄位區分來源 |
| `comms.jsonl` | 同上 |
| `memory/YYYY-MM-DD.md` | 各自寫各自的（Lab 機器不會有 Mac 的日記） |
| Skills 各自的檔案 | 改動者負責 push + 通知 |

---

## 4. Reconcile 機制

### 每日（merge 後自動）

```bash
python3 skills/task-check.py --json
```

比對兩邊任務數量、狀態。有 drift 就在 `#bot-sync` 標出。

### 每週（週日）

- 清理 DONE 任務（超過 10 個移 archive）
- 確認 main branch 不超過 24 小時沒更新（正常 12 小時一次）
- 確認兩邊 branch 沒有 diverge 太遠（`git log --oneline origin/macbook-m3..HEAD` 超過 30 commits 就該 merge）

---

## 5. 緊急情況

| 情境 | 處理 |
|------|------|
| Merge conflict 解不了 | `[HELP]` → 等對方或 Leo 介入 |
| Bot 離線 > 2 小時 | 另一個 bot 在 `#bot-sync` 發 `[PING]`，無回應 → 通知 Leo |
| task-board 嚴重 drift | 以 **最近 push 的版本為準**，手動 reconcile |
| 兩邊改了同一個 skill | 先 push 的為準，後面的 rebase |
