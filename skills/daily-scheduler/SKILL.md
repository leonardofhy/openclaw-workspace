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

## ⚠️ MANDATORY: File-first persistence

**Every schedule action MUST write to file BEFORE sending to Discord.**

Storage: `memory/schedules/YYYY-MM-DD.md`

### Workflow (non-negotiable order)

1. **Fetch data** (schedule_data.py)
2. **Write file** (`Write` tool → `memory/schedules/YYYY-MM-DD.md`)
3. **Send Discord** (`message` tool — copy from the file you just wrote)

### File format

```markdown
# 📅 YYYY-MM-DD (weekday) Daily Schedule

## v1 — 初版 (HH:MM)
[schedule content]
> optional context note

## v2 — 更新 (HH:MM)
[updated schedule]
> reason for change

## 實際紀錄
- ✅ HH:MM item completed
- ✅ HH:MM another item
- 🔵 HH:MM in progress
- ❌ HH:MM skipped/cancelled — reason
```

### Rules
- **plan** → create file with `## v1`, append `## 實際紀錄` section
- **update** → `Edit` to insert new `## vN` before `## 實際紀錄`
- **log** → `Edit` to append line to `## 實際紀錄`
- Never send Discord without writing file first. File is source of truth.

## ⚠️ MANDATORY: File is source of truth

**Schedule 查看/修改/生成，永遠以檔案為 source of truth：**
- **查看** → `Read` 檔案 → 展示
- **修改** → `Edit` 檔案 → `Read` 檔案 → 展示
- **生成** → `Write` 檔案 → `Read` 檔案 → 展示

**永遠不要從記憶中直接生成 schedule 展示給 Leo。**

## Weekly Generation

一次生成 7 天 schedule，每天早上刷新當日。

### Fetch weekly data
```bash
python3 skills/daily-scheduler/scripts/weekly_data.py          # 7 days from today
python3 skills/daily-scheduler/scripts/weekly_data.py --days 14 # 14 days
```

### Workflow
1. Run `weekly_data.py` → get 7 days of calendar + todoist
2. For each day without existing schedule: write `memory/schedules/YYYY-MM-DD.md` with `## v0 — 週排程草稿`
3. For each day WITH existing schedule: skip (don't overwrite Leo's manual edits)
4. Daily morning cron: refresh today's schedule to `## v1` with latest data

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
