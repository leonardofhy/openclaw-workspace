# SKILL: daily-scheduler

## Description
Take a raw brain dump of tasks/goals and structure them into a concrete daily schedule. Output a Markdown plan first for review. Upon user confirmation, push tasks to Todoist via API and events to Google Calendar.

## Usage
- Trigger when the user says "Here is my plan for today", "Help me plan my day", or "排一下行程".
- Input: Unstructured text with tasks, constraints, and fixed events.
- Output: 
  1. Plan logic (energy levels, context switching, deep work).
  2. Markdown Schedule (Timeblocking).
  3. Confirmation Request (Questions/Ambiguities).

## Data Sources
- **Todoist**: `python3 skills/leo-diary/scripts/todoist_sync.py --limit 50 --completed-today`
- **Google Calendar**: `python3 skills/leo-diary/scripts/gcal_today.py --days-ahead 0 --days-range 2`
- **Memory**: `memory/YYYY-MM-DD.md` for recent context

## Rules
1. **Deep Work First**: Schedule hard/creative tasks (coding, writing) during peak energy hours (usually 14:00-18:00 for Leo).
2. **Parallel Processing**: Identify tasks that are "Passive/Monitoring" (e.g., training models) vs "Active" (e.g., writing docs). Schedule Active tasks *during* Passive blocks.
3. **Batch Shallow Work**: Group admin/email/messages into a "Admin Block".
4. **Buffer Time**: Always leave 15-30m buffers.
5. **Health-Aware**: Check if Leo is sick/tired (from recent memory), adjust intensity accordingly.
6. **Format**:
   - `[Time]` Task (Priority)
   - *Italic for breaks/meals*

## Post-Confirmation Actions
- Create tasks in Todoist: `POST https://api.todoist.com/api/v1/tasks`
- Create calendar events: Use `gcal_today.py` patterns or Google Calendar API directly
- Set cron reminders for time-sensitive tasks

## Dependencies
- `memory` (Read/Write)
- `cron` (For reminders)
- `todoist_sync.py` (Task data)
- `gcal_today.py` (Calendar data)
