---
name: experiment-manager
description: >
  Track, manage, and compare ML experiments across machines. Use when (1) starting a new experiment run,
  (2) recording experiment results, (3) comparing runs, (4) checking what experiments have been tried,
  (5) queuing next experiments, (6) Leo asks "之前跑過什麼", "實驗結果", "比較一下", "下一個要跑什麼".
  NOT for: reading papers (use autodidact), writing code (use senior-engineer), or task management (use task-board).
---

# Experiment Manager

## Quick Start

```bash
# 查看所有實驗
python3 skills/experiment-manager/scripts/exp_tracker.py list

# 新增實驗
python3 skills/experiment-manager/scripts/exp_tracker.py add \
  --name "whisper logit lens" \
  --task "layer-analysis" \
  --model "whisper-base" \
  --params '{"layers": 6, "method": "logit_lens"}' \
  --command "python3 whisper_logit_lens.py" \
  --machine lab

# 記錄結果
python3 skills/experiment-manager/scripts/exp_tracker.py result EXP-001 \
  --status success \
  --metrics '{"accuracy": 0.934, "layers_identified": 2}' \
  --summary "CKA shows 2 clusters: acoustic (0-2) and semantic (3-5)"

# 比較實驗
python3 skills/experiment-manager/scripts/exp_tracker.py compare EXP-001 EXP-002

# 查看佇列
python3 skills/experiment-manager/scripts/exp_tracker.py queue

# 標記失敗（含原因，避免重複踩坑）
python3 skills/experiment-manager/scripts/exp_tracker.py result EXP-003 \
  --status failed \
  --summary "OOM on whisper-large, need gradient checkpointing"
```

## 實驗生命週期

```
QUEUED → RUNNING → SUCCESS / FAILED / CANCELLED
                      ↓
                  記錄到 paper notes
```

## 資料存儲

- **實驗記錄**: `memory/experiments/experiments.jsonl`（append-only，一行一個 JSON）
- **ID 格式**: `EXP-001`, `EXP-002`...（自動遞增）
- **每筆記錄包含**: id, name, task, model, params, command, machine, status, created, started, completed, metrics, summary, failed_reason, tags

## 使用場景

### 跑實驗前
1. `exp_tracker.py list --status success --task X` — 看看同類實驗有沒有人跑過
2. `exp_tracker.py add ...` — 登記新實驗
3. 記錄 command 要完整可復現

### 跑完後
1. `exp_tracker.py result EXP-xxx --status success/failed ...`
2. 成功的實驗加 metrics 和 summary
3. 失敗的實驗一定要記 failed_reason

### 寫論文時
1. `exp_tracker.py list --status success --task X` — 找所有相關成功實驗
2. `exp_tracker.py compare ...` — 側面比較
3. Summary 和 metrics 可直接引用

## 和其他系統的關係

- **task-board.md**: 任務 next_action 裡引用 EXP-xxx ID
- **autodidact**: 學習 cycle 產出的實驗計劃 → 登記到這裡
- **senior-engineer**: 寫實驗程式碼 → 用這裡的 command 跑
- **inter-bot coordination**: Lab 跑的實驗標記 machine=lab，Mac 標記 machine=mac

## 詳細格式

見 `references/experiment-format.md`
