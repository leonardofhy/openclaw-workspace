# Scheduling Rules (Leo)

Last updated: 2026-02-27

## Default execution order (when Leo asks to change schedule)
1. Update `memory/schedules/YYYY-MM-DD.md` first (source of truth).
2. Sync Google Calendar.
3. Sync Todoist.

Do this directly (no extra confirmation) unless the action is risky/destructive beyond normal rescheduling.

## Past-event protection (critical)
- Never delete past events from Google Calendar when updating schedule.
- Rescheduling should only modify **current/future** blocks unless Leo explicitly asks to clean historical entries.
- If a sync action accidentally removed past events, restore them from `memory/schedules/YYYY-MM-DD.md` immediately.

## What goes where

### Google Calendar (time-blocked)
Use for items with a concrete start/end time:
- Meetings, classes, appointments
- Focus/deep-work blocks
- Time-specific reminders today

### Todoist (task reminders)
Use for non-time-fixed tasks:
- Errands/admin tasks
- Follow-ups without exact hour
- Deferred items (e.g., weekend processing)

### Both (important + deadline)
Use both Calendar and Todoist when:
- High-priority tasks must happen today
- Deadline-sensitive work benefits from both a time block and persistent reminder

## Note
`memory/core.md` should keep only a short pointer to this file, not full operational detail.
