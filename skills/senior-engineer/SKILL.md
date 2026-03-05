---
name: senior-engineer
description: >
  Senior Engineer Mode — enforce rigorous engineering practices for ALL work:
  code, infrastructure, protocols, and documentation. Use when (1) building new
  features or scripts, (2) fixing bugs with proper root cause analysis,
  (3) refactoring for maintainability, (4) making architecture decisions,
  (5) designing protocols or system changes, (6) modifying shared infrastructure,
  (7) spawning coding agents that need higher quality output. Also use when Leo says
  "engineer mode", "認真寫", "工程模式", or when changes touch critical files
  (AGENTS.md, PROACTIVE.md, HEARTBEAT.md, cron jobs, data pipelines, API integrations).
  NOT for quick one-liner fixes, reading/exploring code, or non-coding tasks.
---

# Senior Engineer Mode

Ship changes that are **verified**, **safe**, and **synced**.
Prefer being correct over sounding confident.

## 1) Classify the work (pick ONE)

**A. New code** → must be runnable + include a smoke test command.
**B. Modify existing system** → must preserve behavior or prove the new behavior.
**C. Infra / automation / shared state** → treat as production: plan, diff, rollback, verify.

Pick the classification BEFORE writing anything. It determines what "done" means.

## 2) Rules (checkable)

**R1 — Evidence-gated claims**
Never say "done / fixed / enabled" unless you **ran a verification command** and can point to the output.
If you can't verify, say **UNVERIFIED** + the exact command(s) to verify.

**R2 — No observe-only loops**
If the same check fails **twice**, stop counting. Do a concrete repair attempt, then re-check.
After **3 failed repair attempts**, escalate: disable the noisy loop + create a tracked action item + report the escalation.

**R3 — Git is the transaction boundary**
For any repo-backed state change (code, configs, JSONL stores):
- `git pull --rebase` (or `fetch + merge`) before writing
- `commit + push` after writing
- "done" must include: branch + commit hash
Never end a task with a dirty working tree unless explicitly blocked.

**R4 — Single source of truth for protocols**
Exactly one canonical doc per topic. Other docs may summarize but MUST NOT introduce new rules.
If you change protocol behavior, update the canonical doc. Mark old text "Superseded: …".
Doc hierarchy: AGENTS.md > SOUL.md > PROACTIVE.md > HEARTBEAT.md > Skill SKILL.md.

**R5 — Destructive actions require safety rails**
In a workspace/repo: **no `rm -rf`**.
Tracked files: `git rm`. Untracked: `trash` or `.trash/<timestamp>/`.
Large deletions: commit before + after so recovery is one `git checkout`.

**R6 — Signal > templates**
Do not emit long status templates. Only report when there is new evidence, state change, decision, or action taken.
Every report must include the **next concrete action** (or "blocked by X").

**R7 — Close loops on learnings**
No orphan learnings. Every learning/TODO → owner, next step, due date.
Each session: close ≥1 stale item (age > 48h) or reschedule with reason + new due date.
Use `learn.py` for tracking; promote recurrence ≥3 to permanent docs.

## 3) Coding Rules (when classification = A or B)

**C1 — 先讀後寫**: Read existing patterns, naming, error handling before writing. Match the codebase's style. Reuse existing modules (`skills/shared/jsonl_store.py`, `email_utils.py`).

**C2 — 最小變更**: Smallest diff that solves the problem. No unrelated refactors. No rewriting entire files unless asked.

**C3 — 錯誤處理不是可選**: Handle errors, validate inputs, consider empty/null/malformed data. Log meaningful messages to stderr. Never silently swallow exceptions.

**C4 — Trade-off 透明**: When multiple approaches exist: max 2 options, state why you recommend one. Write reasoning in code comments or `memory/knowledge.md`.

## 4) Anti-patterns (never)

- Counting the same failure repeatedly without repair/escalation
- "Done" after writing files but before running anything
- Changing Git-backed state without commit+push
- Creating overlapping protocol docs instead of updating the canonical one
- `rm -rf` in the repo/workspace
- Heartbeat spam with no new information
- Logging learnings that sit "pending" indefinitely
- Inventing new abstractions when existing ones work (YAGNI)
- Outputting entire files instead of targeted edits

## 5) Before you say DONE (5 checks)

1. ✅ I **ran** the relevant command(s) and saw expected output
2. ✅ I can point to the **exact files changed** (minimal diff)
3. ✅ Git is **clean**; commit + push completed (hash recorded)
4. ✅ Recurring failures have a **repair/escalation** recorded
5. ✅ Docs/protocols **updated**, or explicitly "no doc change needed"

## Context: Our Workspace

- **Stack**: Python 3.12, shell scripts (bash/zsh), OpenClaw automation
- **Structure**: `skills/*/scripts/*.py` for tools, `memory/` for data, `secrets/` for credentials
- **Shared modules**: `skills/shared/jsonl_store.py`, `skills/leo-diary/scripts/email_utils.py`
- **Conventions**: argparse CLIs, stderr for errors, stdout for data, `sys.path.insert` for imports
- **Testing**: Run scripts directly; `--dry-run` flags where applicable; no formal test framework
- **Safety**: `trash` > `rm`; ask before external actions; never log secrets
- **Two instances**: Lab (WSL2, `lab-desktop` branch) + Mac (`macbook-m3` branch), periodic merge

## For Spawned Coding Agents

Prepend to task:
> Apply Senior Engineer Mode: classify work (new/modify/infra), read existing code first,
> minimal diffs, include verification commands, handle errors and edge cases, commit+push when done.

## References

- Diagnosis + research behind these rules: `references/research-2026-03.md`
- Full guide with scenario prompts: `references/full-guide.md`
