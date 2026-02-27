# Known Issues — 踩坑記錄

> 每次遇到 bug 都記錄在這裡，避免重複踩坑。

---

### [2026-02-27] openclaw.json 直接編輯被 validation 清掉
- **症狀**: 手動加的 `guilds` key 在 gateway restart 後消失
- **環境**: Lab WSL2, OpenClaw 2026.2.25
- **原因**: OpenClaw config validation 會清掉不認識的格式。直接改 JSON 不安全
- **修復**: 用 `openclaw config set channels.discord.groupPolicy open` 才是正確方式
- **預防**: 永遠用 `openclaw config set`，不要直接改 openclaw.json

### [2026-02-27] WORKSPACE 路徑錯誤（parent 層數不對）
- **症狀**: `task-board.md not found`、`experiments.jsonl` 寫到錯誤位置
- **環境**: Lab WSL2
- **原因**: `Path(__file__).resolve().parent.parent.parent` 從 `skills/X/scripts/` 只走到 `skills/`，差一層
- **修復**: 改成 `.parent.parent.parent.parent` 走到 workspace root
- **預防**: 新腳本寫 WORKSPACE 路徑時，一定要 print 出來驗證

### [2026-02-27] rm -rf skills/memory 誤刪正式 skill
- **症狀**: `skills/memory/SKILL.md` 和 `fetch_latest_diary.py` 被刪
- **環境**: Lab WSL2
- **原因**: 清理錯誤路徑的 `skills/memory/experiments/` 時用了 `rm -rf skills/memory`
- **修復**: 從 git history 恢復 (`git show HEAD~1:path > file`)
- **預防**: 刪除前用 `ls` 確認目標；用 `rm -rf skills/memory/experiments` 而不是整個 `skills/memory`

### [2026-02-27] Gateway restart 從 session 內部失敗
- **症狀**: `exec` 指令 timeout 或斷線
- **環境**: Lab WSL2, OpenClaw 2026.2.25
- **原因**: 重啟 gateway 會斷開當前 session 的 WebSocket 連線
- **修復**: 用 `nohup bash -c 'sleep 2 && systemctl --user restart openclaw-gateway' &`
- **預防**: 需要重啟 gateway 時用 nohup 背景執行，或請 Leo 手動跑
