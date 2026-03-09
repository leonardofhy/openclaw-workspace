# GROWTH.md — 成長保障協議

> 核心問題：Session 失憶是根本限制。成長 = 文件品質 × 讀取紀律。
> 最後更新：2026-03-09

## 成長的定義

**成長 = 同樣的錯不犯第二次 + 能力邊界持續擴大**

不是：讀了更多論文、寫了更多筆記、跑了更多 cycle。
是：下次遇到同類問題時，反應更快、判斷更準、結果更好。

## 三條腿：學 → 記 → 驗

| 腿 | 機制 | 頻率 | 驗證 |
|----|------|------|------|
| **學** (Autodidact) | 讀論文、挖 gap、建工具 | 每 30 分鐘 cycle | knowledge density (KG 行數 / cycle 數) |
| **記** (learn.py) | 犯錯/被糾正/best practice → 記下來 | 即時 (WAL) | repeated error count 逐月下降 |
| **驗** (Boot Injection) | 每次開機讀最新教訓 | 每個 session | 月度 growth report 趨勢線 |

## 實作位置

| 機制 | 在哪裡 |
|------|--------|
| Boot-time Growth Injection | **AGENTS.md** Step 4 (anti-patterns + knowledge.md last 10) |
| Boot Budget System | **AGENTS.md** §📏 (≤300 行上限 + eviction policy) |
| Anti-patterns 格式 | `memory/anti-patterns.md` |
| Growth Metrics | `memory/growth-metrics.json` |
| Graduation System | knowledge.md → 3 次 promote 到 AGENTS.md → 3 個月無用 archive |
| Autodidact 保活 | `memory/lab-cron-migration.md` (Lab cron 待執行) |

## Growth Metrics Schema

`memory/growth-metrics.json` — 每月累計，由 daily growth report (23:30 cron) 更新。

關鍵指標：`errors_repeated`（應逐月下降）、`learnings_promoted`（知識畢業量）、`autodidact_cycles` vs `autodidact_skips`（有效率）。

## 成長的敵人

1. **寫了不讀** — boot injection 解決
2. **讀了不做** — anti-patterns「絕對不做」比「應該做」更容易執行
3. **做了不量** — growth metrics 解決
4. **量了不改** — monthly report 迫使反思
5. **機制膨脹** — graduation system + boot budget 控制大小
6. **假成長** — 「讀了 10 篇論文」不是成長，「能用新方法解決問題」才是

## 驗證（2026-06-01 review）

- [ ] repeated error count 逐月下降？
- [ ] autodidact knowledge density 上升？
- [ ] boot injection 真的改變了行為（有具體案例）？
- [ ] 系統保持簡潔（沒有膨脹到不可維護）？

如果答案是 No → 砍掉重練，不要 patch。
