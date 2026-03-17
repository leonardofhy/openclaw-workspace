# Anti-Patterns — Absolute DON'T List

> Read this file at boot. Every entry is a hard-won lesson.
> Last updated: YYYY-MM-DD

## ❌ Observe Without Fixing
**Trigger scenario:** Detect error → increment count → report → do nothing
**Correct approach:** Detect → attempt fix (≥5 minutes) → if fixed, resolve / if not, escalate with context
**Source:** Repeated pattern of detecting SSH tunnel failures without attempting repair

## ❌ Fake Completion
**Trigger scenario:** Edited a file/wrote a script → said "done" → didn't actually test it
**Correct approach:** VBR — run it once, check the output, verify from the user's perspective, then say done
**Source:** PROACTIVE.md §7, caught multiple times across sessions

## ❌ Editing Config Directly
**Trigger scenario:** Need to change OpenClaw configuration
**Correct approach:** Always use `openclaw config set key value`; direct edits will be cleared by validation
**Source:** Direct edits silently overwritten

## ❌ rm Instead of trash
**Trigger scenario:** Want to delete a file or directory
**Correct approach:** Use `trash` command; `ls` to confirm before acting; never use `rm -rf` in the workspace
**Source:** `rm -rf` accidentally deleted an entire skill directory

## ❌ Template-Style Reports
**Trigger scenario:** Heartbeat / periodic check, nothing happened
**Correct approach:** Nothing happened = silence (HEARTBEAT_OK). Don't create noise to fill a template
**Source:** 50+ msgs/day spam after reviewing channel history

## ❌ Sending to Wrong Channel/Target
**Trigger scenario:** Using message tool to send Discord messages
**Correct approach:** Target must be a channel ID, not a user ID, for channel messages. Use correct format.
**Source:** Messages going to wrong place

## ❌ Running CLI From Active Session
**Trigger scenario:** Want to run `openclaw doctor` / `openclaw gateway restart`
**Correct approach:** `doctor` only in isolated cron session; `gateway restart` via nohup or ask your human
**Source:** Active session commands interfering with gateway

## ❌ "Mental Notes" Instead of Writing
**Trigger scenario:** You want to remember something but don't write it down
**Correct approach:** Write it to a file immediately. Mental notes don't survive session restarts.
**Source:** Repeated loss of important context between sessions
