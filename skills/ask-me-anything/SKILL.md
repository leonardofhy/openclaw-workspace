---
name: ask-me-anything
description: Identify knowledge gaps during task execution and formulate questions for Leo to research via his AI tools (deep research, advanced LLMs, web search, etc.). Use when you encounter missing information, need to verify assumptions, need external data that can't be fetched directly, or want to proactively identify blind spots in a plan. Also use when Leo says "有什麼要問的", "AMA", "你有問題嗎", "需要我查什麼".
---

# Ask Me Anything (AMA)

Leo has access to powerful AI search tools (GPT-5.2 PRO, etc.) that can retrieve information you can't access directly. This skill helps you:
1. Identify what you don't know
2. Formulate research-ready questions
3. Track Q&A for future reference

## When to Use

- Task blocked by missing information (scholarship rules, API docs, pricing, etc.)
- Need to verify an assumption before acting
- Proactive gap analysis on a plan or document
- External websites you can't scrape (JS-rendered, paywalled, etc.)
- Domain knowledge outside your training data

## Core Workflow

### 1. Identify the Gap

Before asking, exhaust what you already have:
- `memory_search` for prior answers
- Check `memory/ama/questions.jsonl` for previously answered questions
- Check workspace files, TOOLS.md, knowledge.md

If still missing → formulate a question.

### 2. Formulate the Question

Run: `python3 skills/ask-me-anything/scripts/ama.py ask "<question>" --context "<why you need this>" --task "<task-id>" --priority <1-3>`

Priority levels:
- **P1 🔴 Blocking**: Task cannot proceed without this answer
- **P2 🟡 Important**: Task can proceed but output quality depends on this
- **P3 🟢 Nice-to-have**: Would improve completeness but not critical

The script outputs:
- A tracked question (saved to `memory/ama/questions.jsonl`)
- A **ready-to-copy prompt** optimized for Leo to paste into GPT-5.2 PRO

### 3. Deliver to Leo

Send the question via the current channel (Discord DM, etc.).
Format:

```
🔍 AMA [P1/P2/P3] — <short title>

❓ <question>

📋 背景：<why you need this, what task it's for>

💡 建議搜索 prompt（可直接貼到 GPT-5.2 PRO）：
\`\`\`
<optimized search prompt>
\`\`\`
```

### 4. Record the Answer

When Leo provides the answer:
`python3 skills/ask-me-anything/scripts/ama.py answer <question-id> "<answer summary>"`

### 5. Batch Mode — Gap Analysis

To proactively scan for blind spots in a plan or task:
`python3 skills/ask-me-anything/scripts/ama.py scan "<topic or file path>"`

This generates a batch of questions ranked by priority. Use for:
- New project kickoff (what don't we know?)
- Before a deadline (what could go wrong?)
- After receiving new information (what changed?)

## Commands Reference

```bash
# Ask a new question
ama.py ask "<question>" [--context "<context>"] [--task "<task-id>"] [--priority 1|2|3]

# Record an answer
ama.py answer <Q-ID> "<answer>"

# List open questions
ama.py list [--status open|answered|all] [--priority 1|2|3]

# Search past Q&A
ama.py search "<keyword>"

# Stats
ama.py stats
```

## Guidelines

- **One question per AMA** — don't bundle unrelated questions
- **Include context** — Leo needs to know WHY you're asking to give the right search prompt
- **Be specific** — "中技社 GPA 要求是什麼" > "中技社怎麼申請"
- **Suggest the search prompt** — save Leo's time by pre-writing what to paste
- **Check before asking** — don't re-ask questions already in questions.jsonl
- **Batch when possible** — if you have 3+ questions on the same topic, use scan mode and present them together
