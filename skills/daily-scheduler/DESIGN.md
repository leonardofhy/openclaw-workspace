# Daily Scheduler — Engineering Design Document

> Version: 2.0 | Date: 2026-02-26 | Author: Little Leo

## 1. Problem Statement

Leo needs a scheduling system that:
1. **Pre-generates** weekly schedules from Calendar + Todoist data
2. **Refreshes** daily with latest changes
3. **Updates in real-time** as Leo reports progress throughout the day
4. Uses **file as single source of truth** (never display from memory)
5. Is **energy-aware** and respects Leo's patterns

### Current Pain Points
- Schedule only exists when Leo manually asks "排行程"
- No carry-over of unfinished tasks to next day
- No conflict detection when new events are added
- No dashboard integration for schedule display
- Medication schedule is hardcoded in `schedule_data.py`

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    DATA LAYER                            │
├──────────────┬──────────────┬──────────────┬────────────┤
│ Google Cal   │ Todoist API  │ Memory/*.md  │ Tags JSON  │
│ (events)     │ (tasks)      │ (context)    │ (metrics)  │
└──────┬───────┴──────┬───────┴──────┬───────┴─────┬──────┘
       │              │              │             │
       ▼              ▼              ▼             ▼
┌──────────────────────────────────────────────────────────┐
│              FETCH LAYER (scripts)                        │
├─────────────────────┬────────────────────────────────────┤
│ schedule_data.py    │ Single-day: calendar + todoist +   │
│                     │ medication + memory context        │
├─────────────────────┼────────────────────────────────────┤
│ weekly_data.py      │ Multi-day: 7-14 days grouped by   │
│                     │ date + existing schedule check     │
└─────────┬───────────┴──────────────┬─────────────────────┘
          │                          │
          ▼                          ▼
┌──────────────────────────────────────────────────────────┐
│              SCHEDULE ENGINE (NEW)                        │
├──────────────────────────────────────────────────────────┤
│ schedule_engine.py                                       │
│                                                          │
│ • parse_schedule(file) → ScheduleState                   │
│ • generate_day(data, rules) → schedule blocks            │
│ • detect_conflicts(events) → conflicts[]                 │
│ • spillover(yesterday, today) → unfinished tasks         │
│ • render(schedule, mode) → formatted string              │
│ • diff(old, new) → what changed                          │
└─────────┬────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────┐
│              FILE LAYER (source of truth)                 │
├──────────────────────────────────────────────────────────┤
│ memory/schedules/YYYY-MM-DD.md                           │
│                                                          │
│ Format:                                                  │
│   # 📅 YYYY-MM-DD (weekday) Daily Schedule               │
│   ## v0 — 週排程草稿 (auto, MM/DD HH:MM)                 │
│   ## v1 — 早晨更新 (auto, HH:MM)                         │
│   ## vN — 即時更新 (HH:MM)                                │
│   ## 實際紀錄                                              │
│   ## 日終回顧                                              │
└─────────┬────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────┐
│              DELIVERY LAYER                               │
├──────────────────────────────────────────────────────────┤
│ • Discord DM (via message tool)                          │
│ • Webchat (direct reply)                                 │
│ • Schedule file (memory/schedules/YYYY-MM-DD.md)          │
└──────────────────────────────────────────────────────────┘
```

---

## 3. Core Component: schedule_engine.py

The missing piece. A pure-Python engine that handles schedule logic deterministically, reducing LLM token usage.

### 3.1 Data Model

```python
@dataclass
class TimeBlock:
    start: str          # "09:30"
    end: str            # "12:00"
    emoji: str          # "🔬"
    title: str          # "AudioMatters 深度工作"
    category: str       # "research" | "meeting" | "admin" | "meal" | "health" | "rest"
    source: str         # "calendar" | "todoist" | "pattern" | "manual"
    priority: int       # 1-4 (from todoist) or 0 (fixed anchor)
    is_fixed: bool      # True = calendar event, medication
    task_id: str | None # Todoist task ID for completion tracking
    notes: str          # Extra context

@dataclass
class DaySchedule:
    date: str           # "2026-02-26"
    weekday: str        # "四"
    version: int        # Latest version number
    blocks: list[TimeBlock]
    unscheduled: list[dict]  # Tasks that didn't fit
    context_notes: list[str] # Health, deadlines, etc.
    actual_log: list[str]    # Completed items
```

### 3.2 Core Functions

```python
def parse_schedule(filepath: Path) -> DaySchedule:
    """Parse existing .md file into structured DaySchedule."""

def generate_day(
    date: str,
    calendar_events: list[dict],
    todoist_tasks: list[dict],
    medication: list[dict] | None,
    spillover: list[dict],       # Unfinished from yesterday
    memory_context: dict | None, # Health/energy signals
    rules: dict,                 # Time-blocking rules
) -> DaySchedule:
    """Generate a full day schedule from data sources."""

def render_schedule(schedule: DaySchedule, mode: str = "plan") -> str:
    """Render schedule to markdown format for file storage."""

def render_display(schedule: DaySchedule, now: str) -> str:
    """Render schedule for display with ✅/▶/⏳ markers."""

def detect_conflicts(blocks: list[TimeBlock]) -> list[tuple[TimeBlock, TimeBlock]]:
    """Find overlapping time blocks."""

def get_spillover(yesterday_path: Path) -> list[dict]:
    """Extract unfinished tasks from yesterday's actual log."""

def update_schedule(
    schedule: DaySchedule,
    completed: list[str],   # Items just completed
    new_context: str,       # "我剛做完X"
    now: str,               # Current time
) -> DaySchedule:
    """Re-plan remaining time given new context."""
```

### 3.3 Time-Blocking Algorithm

```
INPUT: fixed_anchors[] + tasks[] + patterns[] + remaining_hours
OUTPUT: blocks[]

1. Place FIXED ANCHORS (calendar events, medication)
   → These never move

2. Place PATTERN BLOCKS (Leo-specific)
   → Weekday: lab dinner 18:00-19:30
   → Saturday: swim 15:00-17:00
   → Every day: 22:30 洗漱, 23:00 sleep

3. Find AVAILABLE SLOTS between anchors
   → Apply buffers (15min before/after meetings)

4. Assign TASKS to slots (priority queue):
   a. P1 overdue → earliest morning slot
   b. P1 due today → largest available block
   c. Research/deep work → morning slots (energy peak)
   d. Admin batch → afternoon or post-dinner
   e. Quick tasks (Duolingo, 俯臥撐) → 10min after meal
   f. P2-P4 → remaining slots

5. ENERGY ADJUSTMENT:
   if energy ≤ 2: swap deep_work ↔ admin
   if sick: shorten blocks by 25%, add rest buffers

6. CONFLICT CHECK:
   Any overlaps → warn in output

7. OVERFLOW → add to ⚠️ 未排入 list
```

---

## 4. File Format (Enhanced)

```markdown
# 📅 2026-02-26 (Thursday) Daily Schedule

## v0 — 週排程草稿 (auto, 02/23 21:00)
[initial weekly generation]

## v1 — 早晨更新 (auto, 08:00)
[refreshed with latest data]

## v2 — 即時更新 (12:30)
[after Leo reported "我吃完飯了"]

## 實際紀錄
- ✅ 09:00 起床梳洗
- ✅ 09:30–11:30 AudioMatters 深度工作
- 🔵 12:00 午餐（知名學者）
- ❌ 22:00 俯臥撐 — 太累跳過

## 日終回顧 (auto, 23:50)
- 完成率: 8/12 (67%)
- 未完成 → 明日: 俯臥撐, Duolingo
- 亮點: CMT 卡位成功 🎉
- 偏差: 研究討論比預期長 +1h，壓縮了晚間時間
```

### Key Addition: 日終回顧
- Auto-generated by 23:50 cron
- Calculates completion rate from 實際紀錄
- Identifies spillover tasks → writes them into tomorrow's schedule
- Captures deviations from plan (helps improve future scheduling)

---

## 5. Cron Integration

```
┌─────────┬────────────────────────────────────┬─────────┬──────────┐
│ Time    │ Job                                │ Model   │ Delivery │
├─────────┼────────────────────────────────────┼─────────┼──────────┤
│ Sun 21  │ Weekly: generate next 7 days (v0)  │ sonnet  │ Discord  │
│ Daily 8 │ Refresh: update today's (v0→v1)    │ sonnet  │ silent   │
│ Daily 8:30 │ Morning briefing (existing)     │ sonnet  │ Discord  │
│ Daily 23:50 │ Day-end review + spillover     │ sonnet  │ Discord  │
└─────────┴────────────────────────────────────┴─────────┴──────────┘
```

### Spillover Flow (23:50 cron)
```
1. Read today's schedule file
2. Compare planned blocks vs 實際紀錄
3. Items without ✅ = unfinished
4. Write 日終回顧 section
5. Read tomorrow's schedule file
6. Prepend unfinished items to tomorrow (mark as 📥 spillover)
7. Notify Discord if completion < 50%
```

---

## 6. Schedule File as Output

Schedule files at `memory/schedules/YYYY-MM-DD.md` serve as the single source of truth for daily plans.

---

## 7. Implementation Roadmap

### Phase 1: Engine Core (NOW) ← we are here
- [x] `weekly_data.py` — multi-day data fetch
- [x] 7-day schedule file generation
- [x] Cron: weekly gen + daily refresh
- [ ] `schedule_engine.py` — parse/generate/render functions
- [ ] Conflict detection

### Phase 2: Smart Updates (next)
- [ ] Spillover: 23:50 cron reads today, writes unfinished → tomorrow
- [ ] `update_schedule()` — re-plan remaining time
- [ ] Schedule file rendering improvements

### Phase 3: Analytics (later)
- [ ] 日終回顧 auto-generation
- [ ] Weekly completion rate tracking
- [ ] Plan vs actual deviation analysis
- [ ] Schedule accuracy score (how often do plans match reality?)

### Phase 4: Polish (future)
- [ ] Dynamic medication management (not hardcoded)
- [ ] Leo preference learning from deviation patterns
- [ ] Natural language schedule queries ("下週三下午有空嗎？")
- [ ] Multi-week view for trip planning

---

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Over-automation kills flexibility | Leo ignores auto-schedules | Keep v0 as "草稿", always allow manual override |
| Token cost from LLM scheduling | Monthly cost increase | Use sonnet for cron, engine for deterministic parts |
| Stale data in pre-generated schedules | Wrong schedule displayed | Daily 08:00 refresh catches most changes |
| Spillover avalanche (tasks pile up) | Demotivating | Cap spillover at 3 tasks, suggest deprioritizing rest |
| Schedule file corruption | Lost data | Git auto-commit after changes |

---

## 9. Decision Record

### DR-001: File as Source of Truth (2026-02-25)
**Context**: Schedule was sometimes generated from memory, causing inconsistencies.
**Decision**: All schedule operations must read/write files. Never display from LLM memory.
**Why**: Single source of truth prevents drift. Files survive session restarts.

### DR-002: LLM vs Engine for Generation (2026-02-26)
**Context**: Could build a pure-Python schedule generator or use LLM.
**Decision**: Hybrid — engine handles deterministic parts (anchors, conflict detection, rendering), LLM handles judgment calls (task prioritization, energy-aware adjustments).
**Why**: Engine reduces token cost for routine operations; LLM adds intelligence for edge cases.

### DR-003: Weekly Pre-generation (2026-02-25)
**Context**: Schedules were only created on-demand.
**Decision**: Generate 7 days ahead every Sunday, refresh daily.
**Why**: Reduces morning latency, enables cross-day planning, catches conflicts early.
