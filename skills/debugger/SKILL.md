---
name: debugger
description: >
  Systematic debugging and troubleshooting framework. Use when (1) encountering errors or bugs,
  (2) a script that worked before now fails, (3) cross-machine environment differences cause issues,
  (4) need to diagnose intermittent failures, (5) Leo says "debug", "為什麼壞了", "這個 error",
  "幫我查", "troubleshoot". Complements senior-engineer (which focuses on writing good code).
  NOT for: writing new code (use senior-engineer), system health checks (use system-scanner).
---

# Debugger

## Root Cause Analysis Framework

遇到 bug 時，按此順序排查，不要跳步：

### Step 1: Reproduce（重現）
- 能穩定重現嗎？→ 記錄重現步驟
- 間歇性的？→ 記錄出現頻率和條件
- 只在某台機器？→ 記錄環境差異
- **記錄**: 完整 error message + stack trace

### Step 2: Isolate（隔離）
- **最近改了什麼？** → `git log --oneline -10` + `git diff`
- **環境差異？** → Python 版本、套件版本、OS
- **最小復現？** → 能不能用 5 行程式碼重現？
- **資料問題？** → 輸入檔案是否存在、格式是否正確

### Step 3: Hypothesize（假設）
- 列出最多 3 個可能原因
- 每個原因配一個驗證方法
- 從最可能的開始驗證

### Step 4: Fix（修復）
- 最小修改原則（和 senior-engineer 一致）
- 修完要能解釋**為什麼**壞了
- 加防禦性程式碼防止復發

### Step 5: Record（記錄）
- 寫進 `references/known-issues.md`
- 格式見下方

## 跨機器除錯

Lab (WSL2) 和 MacBook 的常見差異：

| 差異 | Lab (WSL2) | MacBook |
|------|-----------|---------|
| OS | Ubuntu 24.04 on WSL2 | macOS |
| Python | 3.12 (system) | 3.13 (Homebrew) |
| pip | 需要 sudo 或 --user | 正常 |
| 路徑 | /home/leonardo/ | /Users/leonardo/ |
| GPU | 可 SSH 到 lab 機器 | 可 SSH 到 lab 機器 |
| Secrets | 可能缺失 | 完整 |
| Whisper | 不確定 | whisper-cli (cpp) |

### 跨機器 debug checklist
1. 腳本用的是絕對路徑還是相對路徑？
2. 有沒有 hardcode 某台機器的路徑？
3. Python 套件版本是否一致？
4. 環境變數是否設了？
5. Secrets 是否到位？

## 常見錯誤模式

見 `references/known-issues.md` — 每次踩坑都記錄下來。

## 記錄格式

```markdown
### [日期] 問題標題
- **症狀**: 具體 error message
- **環境**: 哪台機器、Python 版本、相關套件
- **原因**: root cause
- **修復**: 做了什麼
- **預防**: 怎麼避免再發生
```
