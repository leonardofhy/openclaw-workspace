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
3. ~~Run one weekly cron audit: keep / edit / disable jobs by value~~ ✅ DONE cycle #52 → audit complete, findings in 2026-02-28_cycle52.md

## Q4 Answer: Cycle Report Signal/Noise (✅ cycle #53)

**Problem:** Cycle reports are verbose (full notes), making it hard for Leo to see "what's new" quickly.

**Applied improvement — 3-line report format:**
```
ACTION: [type]
NOVELTY: [one sentence — the single most valuable new thing]
NEXT: [one sentence — what should happen next]
```

Rule: If nothing new, report = skip notice only (2 lines max). Never repeat context already in goals/progress.

**Applies to:** all cron-triggered cycle summaries going forward.

## Q5 Answer: When to Proactively Request Leo Unblock (✅ cycle #53)

**Problem:** System was execution-blocked for 48+ hours without explicitly flagging to Leo.

**Rule (now written):**
- After **3 consecutive execution-blocked skips** (not just 2 for meta-audit): generate an explicit unblock request message to Leo via Discord
- Format: "I've been execution-blocked for N cycles (since [time]). Unblock needed: [top 1-2 actions]. Estimated unblock time: 15 min."
- Trigger: write this into a flag file `memory/learning/unblock-request.md` so main session can detect and send it

**Applied improvement:** Added `unblock-request.md` protocol note. Main session should check for this file and relay to Leo.

## Cron Audit Findings (2026-02-28 01:31)

**System health:** 25/27 jobs healthy. 2 issues found:
- ⚠️ Dead job: `提醒-SL-Weekly-Meeting` — disabled + past deadline (Feb 26) + error state → flag for Leo to delete
- ⚠️ Sunday 21:00 congestion: 3-4 jobs fire simultaneously (週報 + 週排程生成 + weekly-research-summary + NTUAIS reset) — acceptable, all isolated sessions
- ✅ Skip guard working: 55% skip rate is correct (execution-blocked), meta-audit triggered after 5 consecutive skips

## Flag for Leo
- **Delete:** `提醒-SL-Weekly-Meeting` cron job (id: d70f2ffd-…) — disabled, past, error state
- **Monitor:** `ai-safety-radar-30min` — reassess after 1 week if generating signal
