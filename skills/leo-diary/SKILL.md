---
name: leo-diary
description: Leo 的個人日記研究員。當 Leo 問起日記相關的問題時使用，包括：查詢特定日期或時期發生了什麼、搜尋某人或某事件、分析情緒與睡眠趨勢、整理重大事件時間軸、進行關鍵字頻率分析、或任何與 Daily Meta-Awareness Log 日記內容有關的查詢與分析。
---

# Leo 日記研究員

## 快速開始

**日記路徑**: `/Users/leonardo/Downloads/Daily Meta-Awareness Log (Responses) - MetaLog.csv`  
**背景資料**: 讀取 `references/diary_context.md` 了解日記結構、人物關係、人生章節

## 可用腳本

| 腳本 | 用途 | 用法 |
|------|------|------|
| `scripts/read_diary.py` | 讀取全部或指定日期範圍的日記（優先 Google Sheets） | `python3 read_diary.py [start] [end]` |
| `scripts/search_diary.py` | 搜尋關鍵字/人物出現的日記 | `python3 search_diary.py <關鍵字>` |
| `scripts/keyword_freq.py` | 關鍵字頻率分析（零 token，純 Python） | `python3 keyword_freq.py [start] [end]` |
| `scripts/insights.py` | 最近 N 天的洞察報告（心情/精力/睡眠/最新日記） | `python3 insights.py [days=7]` |
| `scripts/sleep_calc.py` | 睡眠時長計算與趨勢分析 | `python3 sleep_calc.py --days 14` |
| `scripts/daily_coach_v3.py` | 每日教練信（整合日記+行事曆+Todoist） | `python3 daily_coach_v3.py` |
| `scripts/todoist_sync.py` | Todoist 任務同步（含已完成任務） | `python3 todoist_sync.py --limit 50 --completed-today` |
| `scripts/gcal_today.py` | Google Calendar 事件查詢 | `python3 gcal_today.py --days-ahead 0 --days-range 2` |
| `scripts/system_health.py` | 系統全面健檢 | `python3 system_health.py` |
| `scripts/email_utils.py` | 共用寄信模組（讀取 secrets） | `from email_utils import send_email` |

## /insights 指令
當 Leo 說 `/insights` 或「給我洞察」時：
1. 執行 `python3 insights.py 7`（預設7天）
2. 補充 LLM 觀察：近期日記裡有什麼值得注意的主題或情緒？
3. 給 2-3 條具體的反思問題

可加參數：`/insights 30`（看最近30天）

## 時間戳注意事項
- Timestamp = Google Form 提交時間，**不一定等於當天日期**
- 跨夜填寫時（如凌晨 1 點），描述的是「昨天」的事
- 新日記（約 2025/10 後）通常在開頭明確寫「今天是 X 月 X 日」→ 以日記內文日期為準
- 查詢特定日期時，若無精確結果，需檢查前後一天的內容

日期格式：`YYYY-MM-DD`，例如 `2025-09-01 2025-12-31`

## 工作流程

### 查詢型（「我在某天/某時期做了什麼？」）
1. 用 `read_diary.py` 讀取指定日期範圍
2. 直接閱讀內容並回答

### 搜尋型（「我什麼時候提到 X？」）
1. 用 `search_diary.py <關鍵字>` 搜尋
2. 整理搜尋結果並回答

### 分析型（關鍵字頻率、趨勢）
1. 先用 `keyword_freq.py` 跑零 token 的基礎分析
2. 如需語意分析，再用 `read_diary.py` 取相關段落送 LLM

### 深度分析型（情緒軌跡、成長報告）
1. 讀取 `references/diary_context.md` 了解背景
2. 分期讀取日記（按月或按章節）
3. 整理後輸出報告，存到 workspace

## Token 節省原則
- 關鍵字統計 → 優先用 `keyword_freq.py`（0 token）
- 只需幾篇 → 用 `read_diary.py` 指定日期範圍
- 需要全文分析 → 分批處理，每批 20-30 篇
- 已有分析報告 → 讀 `/Users/leonardo/.openclaw/workspace/diary_analysis_report.md`

## 注意事項
- 日記為中文（繁簡混用）+ 口語語音輸入，解讀時考慮上下文
- 睡眠品質欄位近期已停填，不要強迫分析此欄
- 分析結果可寄 email 至 leonardofoohy@gmail.com（見 TOOLS.md）
