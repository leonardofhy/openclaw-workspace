# 🧭 Meta-Awareness Board

> Purpose: 自主學習系統的「自我研究/自我改進」看板（避免卡在重複 skip）。
> Created: 2026-02-28 01:06

## Current Symptoms (from recent cycles)

1. **Skip loop**: execution-blocked 後連續多輪 skip，資訊增量接近 0。
2. **Timing mismatch**: arXiv 新批次固定時段才有新內容，但 cycle 頻率與資料新鮮度未充分對齊。
3. **Insight saturation**: ideas/gaps 已很多，但缺少「系統層」改進節奏與評估指標。

## Research / Improvement Questions (priority)

1. 如何定義「有價值 cycle」？可否量化 novelty score（0/1）？
2. 當 execution-blocked 時，哪些 meta-audit 任務最值得做（清理、驗證、提案、同步）？
3. 如何避免重複掃描同一批文獻（減少無效 token 成本）？
4. cycle 報告怎樣才不吵但有用（signal/noise ratio）？
5. 什麼條件下應主動向 Leo 請求 unblock（而不是繼續等待）？
6. 如何把「想法庫」轉成「可執行實驗隊列」並追蹤完成率？

## Immediate Improvements Applied (this session)

- ✅ Added **repeated-skip guard** in autodidact SKILL:
  - 2 次 execution-blocked skip 後，下一輪強制 reflect(meta-audit)
- ✅ Added **meta-awareness audit checklist** into reflect action
- ✅ Added cadence rule: target every 30 minutes (unless Leo changes)
- ✅ This board file created as persistent backlog

## KPI (weekly)

- `skip_ratio` = skip cycles / total cycles
- `novelty_ratio` = cycles with new artifact / total cycles
- `meta_fix_count` = applied reversible system improvements per week
- `blocked_to_action_time` = from blocked detection to first concrete unblock request

## Next 3 Meta Cycles

1. Build a lightweight novelty classifier for cycle outputs (new paper? new hypothesis? new artifact?)
2. ~~Add unblock request template (when blocked > 2 cycles)~~ ✅ DONE cycle #51 → `experiment-queue.md` created with unblock checklist + execution queue
3. Run one weekly cron audit: keep / edit / disable jobs by value
