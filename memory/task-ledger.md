# Task Ledger

Last updated: 2026-02-27 19:34

## 運作規則（避免任務遺失）

- 每個新任務都要拿到一個 ID（`T-xx`）。
- 任務一定有狀態：`ACTIVE` / `WAITING` / `BLOCKED` / `DONE` / `PARKED`。
- 只要卡住超過 1 個 cycle，主動向 Leo 提出「需要什麼協助」。
- 卡住不等於移除：`BLOCKED` 任務必須保留，並標記下一次檢查時間。
- 每輪至少產出一個 artifact（筆記、腳本、log、結果、草稿段落）。

## Active / Open Loops

- `T-06` Battleship 真實實驗開工（環境就緒後的第一批任務）
  - 狀態：`ACTIVE`
  - 背景：`T-01` 環境固化已完成，現在轉入實驗產出階段
  - 已定優先：`A`（Listen layer 快驗）
  - 目前進度：
    - DeSTA2.5 listen-layer 快驗 smoke run 完成（n=4, k=3, 20 samples）
    - full run `n4_chunk3` 已上線（job 224389, RUNNING）
    - `n5_chunk0` 已排隊（job 224390, PENDING）
  - 下一步：
    - 完成 smoke run 後擴到 full-run（n4 缺塊 + n5 系列）
    - 回收 logs 給論文 Method/Results 草稿
  - 需要 Leo 協助（若卡住）：A 路線先跑哪個模型（DeSTA2.5 / Qwen2-Audio / Voxtral）

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

- `T-01` Battleship 實驗工作流固化（`~/Workspace/little-leo`）
  - 狀態：`DONE`
  - 交付：`run_cpu.sh` / `run_gpu.sh` / `check_jobs.sh` / `check_cli.sh` / `run_claude_once.sh` / `launch_claude_tmux.sh`
  - 驗證：GPU smoke job `224365` 成功 RUNNING；compute node 已可執行 Claude Code（載入 nvm 後）

- `T-00` 建立多任務追蹤機制（本檔）
  - 狀態：`DONE`
  - 備註：之後每輪更新本檔，不再只靠對話記憶
