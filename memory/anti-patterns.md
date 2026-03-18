# Anti-Patterns — 絕對不做清單

> Boot 時讀。每條都是血的教訓。最後更新：2026-03-18

## ❌ 假完成
改了文件/寫了腳本 → 說 done → 沒測試。**正確**：VBR — 跑一次、看輸出、驗證後才說 done。(PROACTIVE.md §7)

## ❌ 直接改 openclaw.json
永遠用 `openclaw config set key value`，手動改會被 validation 清掉。(LRN-002/ERR-001)

## ❌ 模板式報告
沒事 = 沉默（HEARTBEAT_OK）。不要為了填模板製造噪音。(2026-02-28 audit)

## ❌ 用 user ID 當 Discord target
target 必須是 channel ID（如 `978709248978599979`），不是 user ID。(LRN-007)

## ❌ 從 active session 跑 openclaw CLI
doctor 只在 isolated cron session 跑；gateway restart 用 nohup 或請 Leo。(LRN-008/ERR-004)

## ❌ 有推土機用鏟子（2026-03-17）
改 >3 檔案 or 需理解 codebase → 派 Claude Code，別自己一行行 Edit。

## Claude Code 調度規則（Leo 決策 2026-03-17）
- **直接 Edit**：≤3 檔案、改動明確、不需 codebase context
- **派 Claude Code**：新功能/refactor/跨多檔/需測試
- **執行**：`cd /project && claude --permission-mode bypassPermissions --print 'task'`
- **Orchestrator**：我拆任務+寫 prompt+選 workdir+驗收（git diff+測試）
- **避免**：不給 workdir（agent 亂跑）、prompt 太模糊（要目標+限制）
