# Anti-Patterns Archive

> Archived from anti-patterns.md to manage boot budget. Still valuable — check here if a pattern resurfaces.

## [Archived 2026-03-18] ❌ 觀測不修復
**觸發場景**：偵測到 error → 增加 count → 報告 → 不動手修
**正確做法**：偵測到 → 嘗試修復（≥5 分鐘）→ 修好就 resolve / 修不好就 escalate with context
**來源**：ERR-005 SSH tunnel 連續 12 次偵測零次修復

## [Archived 2026-03-18] ❌ rm 代替 trash
**觸發場景**：要刪除文件或目錄
**正確做法**：用 `trash` 命令，先 `ls` 確認再操作；絕對不用 `rm -rf` 在 workspace 裡
**來源**：LRN-006 / ERR-003（rm -rf skills/memory 刪掉整個 skill）
