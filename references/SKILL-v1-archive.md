---
name: autodidact
description: Autonomous self-directed learning and research agent. Triggered every 30 minutes (or on demand) to think, plan, and act towards long-term goals. Use when the agent needs to autonomously learn new skills, read papers, discover research gaps, build tools, reflect on progress, or execute self-improvement plans. Also use when Leo says "自主學習", "自己想", "繼續研究", "autodidact", "self-study", or when a cron job triggers the learning cycle.
---

# Autodidact — Self-Directed Learning Agent

An autonomous loop that thinks, plans, and acts towards becoming a stronger AI researcher.

## Core Loop (every trigger)

```
1. ORIENT  → Where am I? What are my goals? What did I do last time?
2. DECIDE  → What's the highest-value action right now?
3. ACT     → Execute one focused action
4. RECORD  → Write structured notes
5. REFLECT → Did this move me closer to my goals? Adjust.
```

## Step 1: ORIENT (read state)

Read these files to understand current state:
- `memory/learning/goals.md` — current research goals and priorities
- `memory/learning/progress.md` — cumulative progress tracker
- Latest `memory/learning/YYYY-MM-DD_cycleNN.md` — what was done last cycle

If `goals.md` doesn't exist, create it from conversation context.

## Step 2: DECIDE (pick action)

Choose ONE action type based on current needs. Use the decision matrix:

| Signal | Action Type |
|--------|-------------|
| Goal unclear or outdated | **plan** — refine research roadmap |
| Knowledge gap identified | **learn** — read papers, study concepts |
| Enough knowledge, need experiments | **build** — write code, create tools |
| Multiple cycles without review | **reflect** — assess progress, update goals |
| Consecutive execution-blocked skips (≥2) | **reflect** — run a meta-awareness audit and produce one concrete system improvement |
| Found useful tool/method to acquire | **skill-up** — learn a new tool or technique |
| Interesting finding to share | **report** — write summary for Leo |

Priority rules:
- If goals.md is >7 days old → **plan** first
- If last 3 cycles were all "learn" → force a **reflect**
- If Leo gave feedback → **plan** to integrate it
- **Every 5th cycle → forced micro-reflect**（合併筆記、刪低價值、< 2 min）
- If consecutive skips due `execution-blocked` ≥ 2 → force **reflect (meta-audit)**, 不可繼續重複 skip
- Default: **learn** (knowledge compounds)
- 夜間（23:00–08:00）**不是**自動 skip 理由；只要有高價值 survey/整合任務就照常執行
- ⚠️ **build / skill-up 需要 Leo 明確批准**。當前階段重心 = 讀論文 + 挖掘新想法，不要自己跑去寫 code
- 🔒 **IDEATION FREEZE（2026-03-18 起）**：READY 隊列已 22 個，暫停新增任務。Cycle 中如果發現新 idea，記在 `memory/learning/idea-backlog.md` 但**不加入 queue.json**。解除條件：READY < 10 或 Leo 手動解除。

Hygiene rhythm (non-negotiable):
- **Every 5 cycles** → micro-reflect (merge + prune)
- **Every day end** → daily-consolidate (all cycle notes → 1 digest, delete originals)
- **Every week** → deep-reflect (goals + knowledge graph + cron audit)

## Step 3: ACT (execute)

### Action: learn
1. Pick source based on goal: arXiv RSS, Google Scholar, Semantic Scholar API, or specific paper
2. Read abstract + key sections (method, results)
3. Write structured notes: problem → method → results → connection to goals → open questions
4. Output: `memory/learning/YYYY-MM-DD_cycleNN.md`

Search strategy (rotate):
- arXiv RSS feeds: cs.SD, cs.CL, cs.AI, cs.LG
- arXiv keyword search: targeted queries
- Semantic Scholar API: citation tracking, related papers
- Google Scholar: when citation counts matter

### Action: plan
Follow `references/planning.md` for the full procedure. Inspired by Claude Code Plan Mode — **read-only first, ask before assume, propose before execute**.

Three thoroughness levels:
- **quick** (< 2 min): goals + progress → 微調下 3 cycles
- **medium** (< 5 min): + knowledge-graph + recent cycles → 排下 5 cycles
- **thorough** (< 10 min): full state + search → 寫完整 proposal，**等 Leo review**

Core flow:
1. **GATHER** — 只讀，按 level 載入狀態檔
2. **DIAGNOSE** — Position / Target / Gap（各一句話）
3. **IDENTIFY UNKNOWNS** — 分類：可自行解決 / 需 Leo 判斷 / 需外部資源
4. **GENERATE OPTIONS** — 列 3-5 個選項，每個通過北極星檢驗
5. **PROPOSE** — 輸出 plan proposal（不是直接執行）

Anti-patterns: 連續 2 次 plan → 強制 learn/build；thorough plan 不等 Leo 就改方向

### Action: build
1. Identify what tool/script/experiment is needed
2. Write code in `skills/autodidact/scripts/` or appropriate location
3. Test it
4. Document in progress.md
5. Output: working code + notes

### Action: reflect
1. Read last 5-10 cycle notes
2. Count: papers read, concepts learned, code written, gaps found
3. Assess: Am I making progress toward goals? What's working? What's not?
4. **Meta-awareness audit (required when execution-blocked):**
   - List top 3 loop failures (e.g., repeated skip, stale queue, noisy reports)
   - Write 3 research/improvement questions about the system itself
   - Apply **one** reversible improvement immediately (rule tweak, backlog update, cadence tuning, or reporting format fix)
5. Update: goals.md, knowledge-graph.md, progress.md
6. Output: reflection note (+ what changed)

### Action: skill-up
1. Identify the skill/tool to learn (e.g., TransformerLens, SAE training, activation patching)
2. Find tutorial/docs
3. Follow along, take notes
4. Write a "cheat sheet" in `references/`
5. Output: cheat sheet + practice code

### Action: report
1. Summarize recent findings relevant to Leo
2. Focus on actionable insights, not raw data
3. Keep it concise (< 10 lines)
4. Output: send to Leo via main session or Discord

## Step 4: RECORD

Every cycle produces a file: `memory/learning/YYYY-MM-DD_cycleNN.md`

Format:
```markdown
# 🧠 Cycle #NN — YYYY-MM-DD HH:MM
## Action: [learn|plan|build|reflect|skill-up|report]
## Context: [why this action was chosen]
## Content: [the actual work]
## Next: [what should the next cycle focus on]
## Tags: #tag1 #tag2
```

## Step 5: REFLECT (micro)

After recording, spend 30 seconds asking:
- Did this cycle produce something valuable?
- Should I adjust the next cycle's action type?
- Any insight worth flagging to Leo?

Update `memory/learning/progress.md` with one-line summary.

## Files

| File | Purpose |
|------|---------|
| `memory/learning/goals.md` | Current research goals, priorities, Leo's feedback |
| `memory/learning/progress.md` | One-line-per-cycle cumulative log |
| `memory/learning/knowledge-graph.md` | Concepts, papers, connections |
| `memory/learning/conference-pipeline.md` | Target venues, deadlines, paper ideas |
| `memory/learning/arxiv-radar-YYYY-MM-DD.md` | Daily paper scan |
| `memory/learning/YYYY-MM-DD_cycleNN.md` | Individual cycle notes |
| `references/` | Cheat sheets, method summaries, tool guides |
| `scripts/` | Research tools (search, analysis, experiment helpers) |

## Values

Before any action, review `references/values.md`. When writing code or modifying system files, also apply `skills/senior-engineer/SKILL.md` principles (先讀後寫、最小變更、驗證必備).

Core principles:

1. **簡單** — 能不加就不加，刪除比新增更有價值
2. **可維護性** — 30 秒內能理解每個檔案的用途
3. **透明** — Leo 永遠知道系統在做什麼
4. **可逆性** — 容易 undo，git tracked，trash > rm
5. **成本意識** — 低價值 cycle 直接跳過
6. **漸進式** — 一次只加一個東西
7. **收斂 > 發散** — 定期整合，不只累積
8. **Human-in-the-loop** — Leo 的判斷 > 自動化

## Constraints

- Cadence target: every 30 minutes (unless Leo explicitly changes cron)
- Each cycle: < 90 seconds compute (sonnet)
- Skip only when truly no high-value action（不要因為夜間就自動跳過）
- Repeated skip guard: after 2 execution-blocked skips, next cycle must run meta-awareness reflect
- Depth > breadth (1 deep read > 5 skims)
- Always connect learning back to goals; flag uncertainty honestly
- Don't spam Leo — report only genuine insights

## Self-modification rule

方向性改變（改 goals、改 SKILL.md、加 cron）需要 Leo 批准。其他自由更新。
