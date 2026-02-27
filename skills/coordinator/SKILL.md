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

## 升級路徑

當前是基於 Discord #bot-sync + git 的鬆散協作。
未來可升級：
- GitHub Issues 做正式任務追蹤
- 共享 experiment dashboard
- 自動化 merge bot
