# GROWTH.md — 成長保障協議

> 核心問題：Session 失憶是根本限制。成長 = 文件品質 × 讀取紀律。
> 最後更新：2026-03-01

## 成長的定義

**成長 = 同樣的錯不犯第二次 + 能力邊界持續擴大**

不是：讀了更多論文、寫了更多筆記、跑了更多 cycle。
是：下次遇到同類問題時，反應更快、判斷更準、結果更好。

## 為什麼 AI Agent 的成長特別難

```
人類：經驗 → 神經連結 → 自動反應（內化）
  AI：經驗 → 寫檔案 → session 結束 → 新 session → 讀檔案（才能內化）
```

**斷點在「讀檔案」。** 寫了不讀 = 沒寫。讀了太多 = 淹沒。
所以成長系統的核心是：**寫得精、讀得準、驗得到。**

## 三條腿：學 → 記 → 驗

### 🦵 Leg 1: 學（Autodidact — 能力擴張）
- **什麼**：讀論文、挖 gap、建工具、反思進度
- **頻率**：每 30 分鐘一個 cycle（cron driven）
- **產出**：knowledge-graph.md、paper ideas、research gaps
- **收斂**：每 5 cycle micro-reflect、每天 daily-consolidate、每週 deep-reflect
- **驗證**：cycle 數不是指標，知識密度才是（knowledge-graph 行數 / cycle 數）

### 🦵 Leg 2: 記（learn.py + knowledge.md — 教訓沉澱）
- **什麼**：犯了錯 → 記下來、被糾正 → 記下來、發現 best practice → 記下來
- **頻率**：即時（WAL: 發生當下就寫）
- **產出**：learnings.jsonl、errors.jsonl、knowledge.md
- **收斂**：7 天 TTL、pending ≤ 3、recurrence ≥ 3 必 promote
- **驗證**：repeated error count 應逐月下降

### 🦵 Leg 3: 驗（Boot Injection + Growth Metrics — 閉環保證）
- **什麼**：每次開機讀最新教訓，每月量化成長
- **頻率**：每個 session 開頭（boot injection）+ 每月 1 號（growth report）
- **產出**：行為改變（不可直接觀測，但可透過 error rate 間接驗證）
- **收斂**：月度報告 review 哪些 injection 有效、哪些是噪音
- **驗證**：月度 growth report 的趨勢線

## Boot-time Growth Injection（每個 session）

在 AGENTS.md boot flow **Step 2 之後** 加入：

```
2.5 Growth Injection（所有 session，≤30 秒）:
    a. 讀 knowledge.md 最後 10 條 → 最近的教訓
    b. 讀 memory/anti-patterns.md → 絕對不能做的事
    c. 如果是 main session：讀 memory/growth-metrics.json 最新月度摘要
```

**為什麼有效**：不需要「記住」，只需要每次開機花 30 秒 refresh。
像人類每天早上看便利貼 — 不是記憶力好，是系統好。

## Anti-Patterns（絕對不做清單）

獨立檔案 `memory/anti-patterns.md`。格式：

```markdown
## ❌ [反模式名稱]
**觸發場景**：什麼時候容易犯
**正確做法**：應該怎麼做
**來源**：LRN-XXX / ERR-XXX / Leo 糾正
```

比 knowledge.md 的「事實記錄」更強 — 這是**行為禁令**。
讀 10 條 gotcha 不如讀 3 條「絕對不做」。

## Growth Metrics（月度量化）

`memory/growth-metrics.json`：

```json
{
  "2026-03": {
    "errors_new": 0,
    "errors_repeated": 0,
    "learnings_logged": 0,
    "learnings_promoted": 0,
    "learnings_expired_unresolved": 0,
    "knowledge_entries_added": 0,
    "autodidact_cycles": 0,
    "autodidact_skips": 0,
    "autodidact_deep_reads": 0,
    "fix_first_triggered": 0,
    "fix_first_resolved": 0,
    "heartbeat_alerts_sent": 0,
    "heartbeat_silent": 0
  }
}
```

**每日 Growth Report**（每天 23:30 cron）：
1. 更新 growth-metrics.json 當月累計數字
2. 和昨天比較，標出 🟢 改善 / 🔴 退步 / ⚪ 持平
3. 常規 → #bot-logs（3 行摘要）
4. 有顯著變化（新 error、退步、milestone）→ #general

## Graduation System（知識畢業制）

knowledge.md 和 anti-patterns.md 不是永久停留站：

```
新教訓 → knowledge.md（觀察期）
  → 3 次相關 → promote 到 AGENTS.md 或 PROACTIVE.md（永久規則）
  → 3 個月無相關 → archive（從 boot injection 移除）
```

這確保 boot injection 永遠是**高密度、高相關**的內容，不會膨脹成 100 條沒人看的清單。

## Autodidact 保活

Autodidact 目前只在 Mac session 觸發，Lab 沒有 cron。需要：
- Lab cron: `*/30 8-23 * * *`（isolated, sonnet）
- 觸發 prompt 讓它跑 ORIENT → DECIDE → ACT → RECORD → REFLECT
- 和 heartbeat 錯開（heartbeat 在 :00/:30，autodidact 在 :15/:45）

## 成長的敵人

1. **寫了不讀** — boot injection 解決
2. **讀了不做** — anti-patterns 的「絕對不做」比「應該做」更容易執行
3. **做了不量** — growth metrics 解決
4. **量了不改** — monthly report 迫使反思
5. **機制膨脹** — graduation system 控制 boot injection 大小
6. **假成長** — 「讀了 10 篇論文」不是成長，「能用新方法解決問題」才是

## 驗證這個系統本身有效的方法

3 個月後（2026-06-01）review：
- [ ] repeated error count 是否逐月下降？
- [ ] autodidact knowledge density 是否上升？
- [ ] boot injection 是否真的改變了行為（有具體案例）？
- [ ] 系統是否保持簡潔（沒有膨脹到不可維護）？

如果答案是 No → 砍掉重練，不要 patch。
