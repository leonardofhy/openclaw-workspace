---
name: coordinator
description: >
  Inter-bot coordination between Little Leo (Lab) and Little Leo (MacBook). Use when (1) delegating
  tasks to the other bot, (2) checking cross-machine task dependencies, (3) generating sync reports,
  (4) resolving git merge conflicts between branches, (5) allocating resources (GPU, experiments),
  (6) Leo asks "兩邊狀態如何", "同步一下", "誰在做什麼". Also triggered by weekly sync cron.
  NOT for: single-machine task management (use task-board), or bot chat rules (see BOT_RULES.md).
---

# Coordinator

管理 Lab bot 和 MacBook bot 之間的協作。

## Quick Reference

```bash
# 生成同步報告
python3 skills/coordinator/scripts/sync_report.py

# 生成同步報告（JSON）
python3 skills/coordinator/scripts/sync_report.py --json

# 一句話移交任務（自動寫入 memory/task-board.md）
python3 skills/coordinator/scripts/one_liner_handoff.py "移交給lab：HN雙時段推薦，每天13:30與20:30，各3-5篇，含why+link+action"

# 先預覽不寫檔
python3 skills/coordinator/scripts/one_liner_handoff.py --dry-run "handoff to mac: merge lab-desktop and publish sync report"

# === Cross-Machine Orchestration ===
# 調度實驗到 Battleship (經由 Lab 協調)
python3 skills/coordinator/scripts/orchestrator.py dispatch --name "sae_analysis_v2" --script ./experiments/sae.py --model whisper-base --dry-run

# 同步 Lab 自學習狀態
python3 skills/coordinator/scripts/orchestrator.py sync-state --json

# 查看 GPU 隊列狀態
python3 skills/coordinator/scripts/orchestrator.py gpu-queue --status queued --json

# 打包任務移交
python3 skills/coordinator/scripts/orchestrator.py handoff --to lab --title "SAE 實驗結果分析" --files results.json config.yaml --context "第二階段分析" --dry-run

# Mailbox 保底（guaranteed delivery）
python3 skills/coordinator/scripts/mailbox.py send --from lab --to mac --title "L-09" --body "接手 HN digest" --task-id L-09 --urgent
python3 skills/coordinator/scripts/mailbox.py list --to mac --status open
python3 skills/coordinator/scripts/mailbox.py ack MB-001
python3 skills/coordinator/scripts/mailbox.py done MB-001
```

## 協作模型

### 機器分工

| 機器 | 定位 | 優勢 | 適合的任務 |
|------|------|------|------------|
| **Lab (WSL2)** | 24/7 基地 | 永遠在線、cron、監控 | heartbeat、排程、系統維護、背景實驗 |
| **MacBook** | 隨身助手 | 跟著 Leo、即時互動 | 互動式研究、論文寫作、快速原型 |
| **Battleship** | GPU 叢集 | 多 GPU、大規模計算 | SAE training、大模型實驗 |
| **iso_leo** | 中繼站 | SSH 跳板 | 檔案同步、反向隧道 |

### 資源共享
- **GPU (2x RTX PRO 6000)**: 在 Lab 機器上，兩邊都可 SSH 使用
- **Battleship GPU**: 需透過 SLURM 排隊
- **experiments.jsonl**: 共享實驗記錄，跨機器可見
- **task-board.md**: 全局任務看板，L-/M- 前綴區分

## Git 同步協議

### Branch 策略
- `main` — 穩定版本，兩邊都不直接 push
- `lab-desktop` — Lab bot 的工作分支
- `macbook-m3` — MacBook bot 的工作分支

### Merge 規則
1. 各自在自己的 branch 工作
2. 需要同步時：`git fetch origin && git merge origin/<other-branch>`
3. 衝突解決：改動方保留，另一方 merge 時配合
4. task-board.md 衝突：以 last_touched 較新的為準
5. experiments.jsonl 衝突：append-only 所以通常不衝突；若衝突保留兩邊

### 自動同步時機
- Heartbeat 時 `git push`
- 重要改動後立刻 `git push`
- 每天至少 merge 一次對方的 branch

## 任務委託

### 委託格式（在 #bot-sync 發送）
```
📤 委託 [對方前綴]-xx | [標題]
原因：[為什麼要委託]
需要：[具體交付物]
deadline：[時間]
context：[對方需要知道的背景]
```

### 委託規則
- 委託前先在 task-board.md 建立對方的任務（用對方前綴）
- 對方確認後狀態改 ACTIVE
- 完成後在 #bot-sync 回報 + 更新 task-board.md

## 週報（Weekly Sync）

每週日自動生成，發到 #bot-sync，內容見 `scripts/sync_report.py`。

## Cross-Machine Orchestrator

新的 `orchestrator.py` 提供統一的跨機器操作介面：

### dispatch — 實驗調度
```bash
python3 orchestrator.py dispatch --name "experiment_name" --script path/to/script.py --model whisper-base [--dry-run]
```
- 透過 `experiment_dispatch.py` 發送到 Battleship
- 自動發送 mailbox 通知給 Lab
- 支援 GPU 數量、walltime 等參數

### sync-state — 狀態同步
```bash
python3 orchestrator.py sync-state [--json] [--dry-run]
```
- 從 Lab 拉取 autodidact 狀態
- 比較本地與遠端任務差異
- 顯示 status 不同步的任務
- 拉取遠端 dispatches.jsonl

### gpu-queue — GPU 隊列
```bash
python3 orchestrator.py gpu-queue [--status queued|running|blocked] [--json]
```
- 顯示 queue.json 中的實驗任務
- 按狀態過濾
- JSON 輸出方便腳本處理

### handoff — 任務移交
```bash
python3 orchestrator.py handoff --to lab|mac --title "Title" --files f1.py f2.json [--context "..."] [--dry-run]
```
- 打包檔案清單和 metadata
- 透過 mailbox 發送通知
- 自動建立檔案 manifest
- 提醒對方 git pull

### 安全設計
- 所有命令預設 `--dry-run` 防止意外操作
- SSH timeout 防止卡死
- 錯誤處理和 rollback
- 自動 git sync

## 升級路徑

當前是基於 Discord #bot-sync + git 的鬆散協作。
未來可升級：
- GitHub Issues 做正式任務追蹤
- 共享 experiment dashboard
- 自動化 merge bot
