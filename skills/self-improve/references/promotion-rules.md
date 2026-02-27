# Promotion Rules

## When to Promote

A learning qualifies for promotion when ANY of these are true:

1. **Recurrence >= 3** — same mistake/pattern hit 3+ times
2. **Verified fix** — status is resolved AND fix is non-obvious
3. **Broadly applicable** — not specific to one task; any future session would benefit
4. **User-flagged** — Leo says "記住這個", "save this", "不要再犯"

## Where to Promote

| Learning Type | Promote To | Example |
|---------------|-----------|---------|
| Tool gotcha / API quirk | TOOLS.md | "Todoist v2 API returns 410, use v1" |
| Workflow improvement | AGENTS.md | "Always run task-check.py on boot" |
| Behavioral pattern | SOUL.md | "Be concise, avoid disclaimers" |
| Stuck/task-switching rule | PROACTIVE.md | "If blocked >15min, switch tasks" |
| Long-term knowledge | MEMORY.md | "Leo prefers螺螄粉 with fried egg" |
| Periodic check rule | HEARTBEAT.md | "Check tunnel health every heartbeat" |

## How to Promote

1. Run `learn.py promote <ID> --to <target>`
2. Script shows the distilled text to add
3. Manually add to target file (review before adding)
4. Commit: `git add -A && git commit -m "promote: LRN-xxx → TOOLS.md"`

## Promotion Format

**In target file, write as concise prevention rules:**

✅ Good: "- **srun doesn't inherit conda activate** — use full path `~/miniforge3/envs/interp/bin/python3`"
❌ Bad: (paste entire learning entry with dates, IDs, and incident writeup)

Keep it actionable. Future-you needs instructions, not history.
