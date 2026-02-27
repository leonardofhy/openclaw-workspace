# Task Ledger

Last updated: 2026-02-27

## 運作規則（避免任務遺失）

- 每個新任務都要拿到一個 ID（`T-xx`）。
- 任務一定有狀態：`ACTIVE` / `WAITING` / `BLOCKED` / `DONE` / `PARKED`。
- 只要卡住超過 1 個 cycle，主動向 Leo 提出「需要什麼協助」。
- 卡住不等於移除：`BLOCKED` 任務必須保留，並標記下一次檢查時間。
- 每輪至少產出一個 artifact（筆記、腳本、log、結果、草稿段落）。

## Active / Open Loops

- `T-01` Battleship 實驗工作流固化（`~/Workspace/little-leo`）
  - 狀態：`ACTIVE`
  - 已完成：SSH 可用、路徑修正到 `~/Workspace`、CPU smoke + 背景 job 可跑
  - 下一步：
    - 建 `run_cpu.sh` / `run_gpu.sh` / `logs/`
    - 在 compute node 驗證 Claude Code（或替代 CLI）
  - 需要 Leo 協助（若卡住）：叢集上 Claude Code 可用安裝路徑/模組資訊

- `T-02` 論文今晚產出（Method v0）
  - 狀態：`ACTIVE`
  - 下一步：先交付可寫入稿件的一頁骨架 + placeholder 實驗敘事

- `T-03` 研究雙軌推進（不被單一討論卡住）
  - 狀態：`ACTIVE`
  - 主線：目前討論方向持續
  - 備線：Listen layer 快驗 / neuron grounding / modality reliance stress test

- `T-04` 排程同步一致性（schedule → GCal → Todoist）
  - 狀態：`WAITING`
  - 規則：只改現在/未來；不得刪除過去事件
  - 來源：`memory/scheduling-rules.md`

- `T-05` autodidact hourly cron 健康確認
  - 狀態：`WAITING`
  - 背景：先前 timeout，已改每小時 + timeout 600s
  - 下一步：檢查下一輪 run 是否恢復 `ok`

## Done

- `T-00` 建立多任務追蹤機制（本檔）
  - 狀態：`DONE`
  - 備註：之後每輪更新本檔，不再只靠對話記憶
