
# Archived from task-board.md (2026-03-13)


### L-00 | Discord Server 通訊設定
- **owner**: Lab
- **completed**: 2026-02-27
- **成果**: groupPolicy 改 open、allowBots=true、BOT_RULES.md 建立、#bot-sync 頻道啟用

### L-00b | Git 分支同步
- **owner**: Lab
- **completed**: 2026-02-27
- **成果**: macbook-m3 merge 到 lab-desktop（+5788 行，38 commits）

### M-01 | Battleship 實驗工作流固化
- **owner**: MacBook
- **completed**: 2026-02-27
- **成果**: `~/Workspace/little-leo` 建置完成；交付 `run_cpu.sh` / `run_gpu.sh` / `check_jobs.sh` / `check_cli.sh` / `run_claude_once.sh` / `launch_claude_tmux.sh`；compute node 可執行 Claude Code（載入 nvm）

### M-00 | 建立多任務追蹤機制
- **owner**: MacBook
- **completed**: 2026-02-27
- **成果**: task-ledger.md 建立（現已遷移至本檔）

### L-01 | 系統環境搭建
- **owner**: Lab
- **completed**: 2026-02-27
- **成果**: pip (via get-pip.py)、google-auth/gspread/google-api-python-client 安裝完成；Python 3.12 確認可用

### L-02 | Bot 間通訊穩定化
- **owner**: Lab
- **completed**: 2026-02-27
- **成果**: allowBots=true 雙邊確認、ping/pong 測試通過、SYNC_PROTOCOL.md 建立並獲 Mac 確認

### L-05 | Secrets 同步
- **owner**: Lab
- **completed**: 2026-02-27
- **成果**: email_ops.env, todoist.env, google-service-account.json 從 Mac 搬入；Todoist、GCal、Diary、SMTP 全部驗證通過

### L-03 | Autodidact GPU 實驗環境
- **owner**: Lab
- **completed**: 2026-02-27
- **成果**: conda env `interp` (Python 3.11)；transformerlens + pyvene + s3prl + torch 2.10+cu128；RTX 3090 25.3GB 驗證通過
- **文檔**: memory/L-03-GPU-ENV.md

### L-04 | Cron 系統建立
- **owner**: Lab
- **completed**: 2026-02-27
- **成果**: 5 cron jobs：heartbeat (*/30 08-23), scanner (06:00), merge (08:00), calendar (13:00), tunnel (*/2h)

### L-06 | 重構收尾
- **owner**: Lab
- **completed**: 2026-02-27
- **成果**: task-check.py + sync_report.py 改用 shared JsonlStore；消除 16 行重複代碼；所有 JSONL 操作統一
