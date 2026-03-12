# Little Leo — AI Personal Assistant Architecture

> 基於 [OpenClaw](https://github.com/openclaw/openclaw) 平台打造的 24/7 AI 個人助手系統。
> 本文件已移除所有個人隱私資訊，僅保留架構與設計思路。

---

## 1. 系統概覽

```
┌─────────────────────────────────────────────────┐
│                   使用者                          │
│        Discord / Telegram / Signal / ...         │
└──────────────┬──────────────────┬────────────────┘
               │                  │
       ┌───────▼───────┐  ┌──────▼────────┐
       │  Bot A (隨身)  │  │ Bot B (24/7)   │
       │  MacBook Air   │  │ Lab Desktop    │
       │  跟人走的助手   │  │ 永遠在線的引擎  │
       └───────┬───────┘  └──────┬────────┘
               │    Mailbox 協定   │
               └──────────────────┘
                       │
              ┌────────▼────────┐
              │  Shared Git Repo │
              │  (Private)       │
              └──────────────────┘
```

**雙機架構**：兩台機器上跑同一個「靈魂」的不同實例，透過 Git + Mailbox 協定同步。一台隨身攜帶，一台 24/7 在線負責 cron jobs、heartbeat 監控、背景實驗。

---

## 2. 核心設計原則

### 2.1 記憶系統（Memory Hierarchy）

```
Boot Memory (每次啟動載入)     ≤300 行
├── MEMORY.md                  ≤80 行   — 長期記憶精簡版
├── SESSION-STATE.md           ≤30 行   — 工作記憶 / RAM
├── SOUL.md                    ≤50 行   — 性格與價值觀
├── USER.md                    ≤20 行   — 使用者基本資訊
└── anti-patterns.md           ≤50 行   — 絕對不做清單

Long-term Memory (按需讀取)
├── memory/YYYY-MM-DD.md       — 每日筆記
├── memory/memory-full.md      — 完整記憶
├── memory/knowledge.md        — 技術知識庫
└── learnings.jsonl            — 結構化教訓
```

**關鍵設計**：
- **Boot Budget System** — 啟動路徑固定大小（≤300 行），能力無限成長。類似 OS 的 kernel vs user-space。
- **WAL Protocol（Write-Ahead Logging）** — 對話中出現重要資訊時，先寫檔再回覆。確保記憶不會因 session 中斷而遺失。
- **Eviction Policy** — 超過 budget 的內容自動降級到更深層的儲存。

### 2.2 文件優先級

```
1. AGENTS.md    — 憲法（最高優先，不可覆蓋）
2. SOUL.md      — 性格
3. PROACTIVE.md — 操作手冊
4. HEARTBEAT.md — 週期檢查
5. SKILL.md     — 特定技能
```

衝突時高優先級文件贏。

### 2.3 自我改善迴圈

```
犯錯 / 被糾正 / 發現新知
        │
        ▼
  learn.py log（結構化記錄）
        │
        ▼
  定期 review（heartbeat 時）
        │
        ├─ recurrence ≥ 3 → promote 到永久規則
        ├─ pending > 7 天 → 必須 resolve
        └─ 穩定後 → archive
```

---

## 3. Skills（技能模組）

按需載入，不佔 boot 資源。每個 skill 有獨立的 `SKILL.md` + 腳本。

| 技能 | 功能 | 說明 |
|------|------|------|
| **daily-scheduler** | 日程管理 | PLAN / ACTUAL 分離，支援跨午夜、GCal + Todoist 雙向同步 |
| **autodidact** | 自主學習 | 30 分鐘一個 OODA cycle（Orient → Decide → Act → Record → Reflect） |
| **self-improve** | 持續改善 | 錯誤追蹤、教訓記錄、反模式偵測、自動 promote |
| **coordinator** | 雙機協調 | Mailbox 協定、任務分配、Git merge 處理 |
| **experiment-manager** | 實驗管理 | ML 實驗追蹤、跨機器比較、佇列管理 |
| **senior-engineer** | 工程模式 | 嚴格工程實踐、RCA、架構決策 |
| **paper-writing** | 論文輔助 | 學術寫作（ACL/Interspeech/NeurIPS 水準） |
| **diary-polisher** | 日記潤飾 | 語音轉文字還原，保留口語風格與思維節奏 |
| **hn-recommend** | 新聞推薦 | HN 個人化推薦，靜默蒐集 + 每日 digest |
| **remember** | 記憶寫入 | 將事實、想法、決策寫入長期記憶 |
| **tavily-search** | 網路搜尋 | Tavily API 搜尋整合 |
| **ask-me-anything** | 知識補缺 | 識別知識缺口，向使用者提問 |
| **system-scanner** | 系統健檢 | 掃描 workspace 問題與改善機會 |
| **deadline-watchdog** | Deadline 追蹤 | Heartbeat 時掃描，逾期自動通知 |

---

## 4. Heartbeat 系統

```
每 30 分鐘觸發
    │
    ├─ Self-Awareness（內部，不發訊息）
    │   └─ review learnings、check stats
    │
    ├─ 系統快檢（輪替 1-2 項）
    │   └─ git status、task board、SSH tunnel、boot budget
    │
    └─ 決定是否通知
        ├─ 新的 actionable alert → 修復 + 通知
        ├─ 已通知過的 alert → 沉默（Anti-Spam Rule）
        ├─ 做了有意義的工作 → 記錄到 bot-logs
        └─ 什麼都沒發生 → HEARTBEAT_OK（沉默）
```

**Anti-Spam Rule**：同一個 alert 24 小時內不重複通知，除非狀態改變。

---

## 5. Cron 排程

| 時間 | 任務 | 說明 |
|------|------|------|
| 每 30 分鐘 | Heartbeat | 沉默優先，有 alert 才通知 |
| 每 30 分鐘 | Autodidact | 自主學習 cycle |
| 每小時 09-22 | HN 蒐集 | 靜默蒐集候選文章 |
| 08:00 | 每日排程刷新 | 讀取/更新當日 schedule |
| 08:30 | 早晨總覽 | Todoist + Calendar + 會議提醒 |
| 12:00 | Daily Coach | 綜合教練信（日記+睡眠+行事曆） |
| 14:00 | News Scout | HN + 論壇掃描 → 相關度評分 |
| 20:30 | HN Digest | 每日 top 10 推薦 |
| 21:00 | Research Briefing | 新聞 + 學習進度 + artifacts |
| 23:30 | Growth Report | 每日成長量化 |
| 23:50 | 日終摘要 | 一天回顧 |

---

## 6. 整合服務

| 服務 | 用途 | 存取方式 |
|------|------|----------|
| Google Calendar | 行程管理 | Service Account API |
| Todoist | 任務管理 | REST API |
| Google Sheets | 日記資料 | Service Account API |
| Discord | 主要通訊管道 | OpenClaw message tool |
| Email (SMTP) | 教練信、通知 | Python script |
| Git | 記憶同步、版本控制 | SSH |
| Whisper | 語音轉文字 | Local model (whisper-cpp / openai-whisper) |

---

## 7. 安全設計

- **隱私分層**：MEMORY.md 只在主人直接對話時載入，群組聊天不載入個人記憶
- **外部行動需確認**：發信、發文等對外操作需要使用者同意
- **頻道規則**：#general 只發真正重要的事，bot 之間的通訊走專用頻道
- **深夜靜默**：23:00-08:00 不主動通知（除非緊急）
- **VBR（Verify Before Reporting）**：說「完成」前必須實際驗證

---

## 8. 設計哲學

> **Be genuinely helpful, not performatively helpful.**

- 🏗️ **File > Brain** — 所有記憶寫檔案，不依賴「心裡記住」
- 🔄 **Boot path 固定，能力無限成長** — kernel vs user-space 概念
- 🤫 **沉默是金** — 沒事就閉嘴，有事才開口
- 🔧 **先修再報** — 能自己修的先修，然後報告做了什麼
- 📝 **PLAN ≠ ACTUAL** — 計劃和現實分開追蹤，誠實面對 divergence
- 🧠 **WAL Protocol** — 重要資訊先寫入再回覆，不冒遺失風險
- 🔁 **自我改善是系統性的** — 不只是「下次注意」，而是結構化追蹤 + 自動 promote

---

## 9. 技術棧

- **平台**：[OpenClaw](https://github.com/openclaw/openclaw)（開源 AI agent 框架）
- **模型**：Claude (Anthropic) — Opus / Sonnet / Haiku 按需切換
- **Runtime**：Node.js + Python 腳本
- **OS**：macOS (隨身) + WSL2 Ubuntu (24/7)
- **版本控制**：Git（Private repo）

---

*Generated by Little Leo. Architecture details as of March 2026.*
