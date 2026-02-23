---
name: daily-scheduler
description: Plan, update, or view Leo's daily schedule. Use when Leo asks to plan today's schedule, reschedule after something changed, show current schedule, or says things like "排一下行程", "幫我排 schedule", "我剛做完X接下來呢", "今天還有什麼", "重新排", "展示今天行程". Always run schedule_data.py first to get fresh data.
---

# Daily Scheduler

Handles three modes based on what Leo says:

| Mode | Trigger | What to do |
|------|---------|-----------|
| **plan** | Morning, "排今天行程", "幫我規劃" | Full day schedule from now to 23:00 |
| **update** | "我剛才...", "行程有變", "接下來怎麼排" | Re-plan remaining time given new context |
| **view** | "展示行程", "今天怎麼樣", "還有什麼" | Show current schedule status |

## Step 1: Always fetch fresh data first

```bash
cd /Users/leonardo/.openclaw/workspace
python3 skills/daily-scheduler/scripts/schedule_data.py
```

Add `--tomorrow` to include tomorrow's calendar.
Add `--no-memory` to skip memory context (faster).

The JSON output gives you: current time/phase, calendar events, Todoist tasks, medication, memory context.

## Step 2: Build the schedule

### Time-blocking rules

**Fixed anchors** (never move):
- Google Calendar events → exact time blocks
- Medication slots (from `medication.upcoming_today`)
- 23:00 = bedtime (hard stop)

**Energy-aware scheduling:**
- `morning` (before 12:00): deep work, complex thinking, writing
- `afternoon` (12:00–17:00): meetings, research, coding
- `evening` (17:00–21:00): lab dinner ~18:00, lighter tasks, social
- `night` (21:00–23:00): wrap-up, review, light admin, sleep prep

**Task assignment rules:**
- P1 (priority=4) tasks due today → must appear in schedule with a time slot
- P2 (priority=3) tasks due today → schedule if time allows
- Overdue tasks → flag prominently, schedule early
- AudioMatters / research → always gets the largest deep-work block
- Quick tasks (Duolingo, 俯臥撐) → batch into 10-min block after meals
- Admin (emails, stats, signups) → batch into one 30-min admin block

**Buffers:**
- 15 min before/after meetings
- 30 min for dinner transition
- 20 min sleep prep before 23:00

**Health adjustments:**
- If sick (from memory context): reduce intensity, shorten deep work blocks, prioritize rest
- If low energy (metrics.energy ≤ 2): admin > deep work, no late-night work

### Output format

**For `plan` and `update` modes:**

```
📅 [date] 剩餘行程（[remaining_hours]h）

• 20:00–20:30 🚿 洗澡 + 休息
• 20:30–21:00 💊 吃藥 + 俯臥撐 + Duolingo（順手做）
• 21:00–22:30 🔬 **AudioMatters 衝刺**（deadline 2/25）
• 22:30–23:00 📋 網管回報 + 收尾
• 23:00 🌙 就寢

⚠️ 未排入：[任何沒時間做的任務]
```

Emoji guide: 🔬 research, 📋 admin, 💊 medication, 🚿 hygiene, 🍜 food, 💪 exercise, 🌙 sleep, ✉️ email, 📅 meeting

**For `view` mode:**
Same bullet format. Past items prefixed with ✅, current with ▶️, future as normal bullets.

## Leo-specific patterns (observed)

- **Lab dinner**: almost every weekday ~18:00–19:30, counts as a fixed block
- **研究討論**: often happens organically after dinner; leave buffer
- **Duolingo + 俯臥撐**: quick tasks, always batch together after meals
- **睡前作息**: 22:30 洗漱, 23:00 sleep; phone-free last 30 min helps
- **AudioMatters** > everything else when deadline < 3 days
- **Weekend**: swim on Saturday afternoon, more flexible schedule
- **Health**: when sick, replace deep work with lighter tasks; shorter blocks

## When to suggest reschedule reminders

If a key task (AudioMatters, urgent email) has no time block, suggest:
> 要我設一個 21:00 的提醒讓你開始衝論文嗎？

Use `cron` or Google Calendar API to create the reminder if Leo agrees.
