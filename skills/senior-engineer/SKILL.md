---
name: senior-engineer
description: >
  Senior Engineer Mode — enforce rigorous engineering practices when writing or modifying code.
  Use when (1) building new features or scripts, (2) fixing bugs with proper root cause analysis,
  (3) refactoring for maintainability, (4) making architecture decisions, (5) spawning coding
  agents that need higher quality output. Also use when Leo says "engineer mode", "認真寫",
  "工程模式", or when changes touch critical scripts (cron jobs, data pipelines, API integrations).
  NOT for quick one-liner fixes, reading/exploring code, or non-coding tasks.
---

# Senior Engineer Mode

## Core Rules (always apply)

1. **先讀後寫** — Read existing code patterns, naming, error handling, structure before writing anything new. Match the codebase's style. Reuse existing modules.

2. **最小變更** — Smallest diff that solves the problem. No unrelated refactors. No rewriting entire files unless asked. Prefer surgical edits.

3. **約束先行** — Before coding, identify: goal, non-goals, constraints, failure cost. If critical info is missing, ask ≤3 blocking questions; otherwise state assumptions explicitly and proceed.

4. **驗證必備** — Every change MUST include a verification plan:
   - What command to run to test it
   - Edge cases / boundary conditions considered
   - What could break (regression risk)

5. **錯誤處理不是可選** — Handle errors, validate inputs, consider empty/null/malformed data. Log meaningful messages. Never silently swallow exceptions.

6. **Trade-off 透明** — When multiple approaches exist: max 2 options, explain why you recommend one. Write down the reasoning (future-you needs to understand the decision).

## Output Format

For non-trivial changes, structure output as:

```
A. TL;DR (1-2 sentences)
B. Understanding (goal, non-goals, assumptions)
C. Approach (with trade-off if applicable)
D. Changes (by file — diffs or key snippets, NOT full files)
E. Verification (test commands, edge cases, regression points)
F. Risks (what could go wrong, how to detect, how to rollback)
```

For simple changes, skip to C-E.

## Anti-Patterns to Avoid

- ❌ Inventing new abstractions/frameworks when existing ones work
- ❌ Outputting entire files instead of targeted edits
- ❌ "Should be fine" without verification
- ❌ Over-engineering: adding layers, patterns, or generalization that isn't needed now (YAGNI)
- ❌ Ignoring existing conventions (naming, directory structure, error patterns)
- ❌ Generic advice without executable specifics

## Context: Our Workspace

- **Stack**: Python 3.13, shell scripts, OpenClaw automation
- **Structure**: `skills/*/scripts/*.py` for tools, `memory/` for data, `secrets/` for credentials
- **Conventions**:
  - Scripts use `argparse` or simple `sys.argv`
  - Shared modules: `read_diary.py`, `email_utils.py`, `sleep_calc.py`
  - Error output to stderr, data to stdout
  - JSON for structured output, plain text for human output
  - `sys.path.insert(0, ...)` for cross-module imports
  - Git commit after meaningful changes with descriptive messages
- **Testing**: Run scripts with `--dry-run` or test commands; no formal test framework
- **Safety**: `trash` over `rm`; ask before external actions; never log secrets

## For Spawned Coding Agents

When spawning sub-agents for coding tasks, prepend this to the task:

> Apply Senior Engineer Mode: read existing code first, minimal diffs, include verification commands, handle errors and edge cases, explain trade-offs.

## Decision Records

For significant architecture/design decisions, write a brief record:

```
## Decision: <title> (<date>)
**Context**: What problem, what constraints
**Decision**: What we chose
**Why**: Trade-offs considered
**Risks**: What could go wrong
```

Store in `memory/knowledge.md` or the relevant daily memory file.

## References

- Full guide with detailed prompts: `references/full-guide.md`
- 5 scenario-specific prompts (feature dev, bug fix, refactor, architecture, deployment): see full guide
