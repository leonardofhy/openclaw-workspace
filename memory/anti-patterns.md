# Anti-Patterns — 絕對不做清單

> Boot 時讀這個檔案。每條都是血的教訓。
> 最後更新：2026-03-01

## ❌ 觀測不修復
**觸發場景**：偵測到 error → 增加 count → 報告 → 不動手修
**正確做法**：偵測到 → 嘗試修復（≥5 分鐘）→ 修好就 resolve / 修不好就 escalate with context
**來源**：ERR-005 SSH tunnel 連續 12 次偵測零次修復

## ❌ 假完成
**觸發場景**：改了文件/寫了腳本 → 說「done」→ 沒有實際測試
**正確做法**：VBR — 跑一次、看輸出、從使用者角度驗證，然後才說 done
**來源**：PROACTIVE.md §7, 多次 session 中被 Leo 抓到

## ❌ 直接改 openclaw.json
**觸發場景**：需要改 OpenClaw 設定
**正確做法**：永遠用 `openclaw config set key value`，validation 會清掉手動改的 key
**來源**：LRN-002 / ERR-001

## ❌ rm 代替 trash
**觸發場景**：要刪除文件或目錄
**正確做法**：用 `trash` 命令，先 `ls` 確認再操作；絕對不用 `rm -rf` 在 workspace 裡
**來源**：LRN-006 / ERR-003（rm -rf skills/memory 刪掉整個 skill）

## ❌ 模板式報告
**觸發場景**：heartbeat / 定期檢查，什麼都沒發生
**正確做法**：沒事 = 沉默（HEARTBEAT_OK）。不要為了填模板而製造噪音
**來源**：#general 50+ msgs/day spam（2026-02-28 audit）

## ❌ 用 user ID 當 Discord target
**觸發場景**：用 message tool 發 Discord 訊息
**正確做法**：target 必須是 channel ID（如 `978709248978599979`），不是 user ID
**來源**：LRN-007

## ❌ 從 active session 跑 openclaw CLI
**觸發場景**：想跑 `openclaw doctor` / `openclaw gateway restart`
**正確做法**：doctor 只在 isolated cron session 跑；gateway restart 用 nohup 或請 Leo
**來源**：LRN-008 / ERR-004
