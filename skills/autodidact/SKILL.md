---
name: autodidact
description: >
  Autonomous self-directed learning and research agent (v2.1).
  Triggered every 30 minutes (or on demand) via cron.
  Use when the agent needs to autonomously learn, plan, build, or reflect
  towards long-term research goals. Also use when Leo says "自主學習",
  "自己想", "繼續研究", "autodidact", "self-study", or when a cron job triggers.
---

# Autodidact v2.1 — Autonomous Research Agent

Bounded boot. Phase-aware. Build-first.

## Step 0: Precheck

```bash
python3 skills/autodidact/tools/precheck.py
```
- `SKIP` → reply `HEARTBEAT_OK` immediately. Done.
- `RUN` → continue to Step 1.

## Step 1: ORIENT (boot — read state only)

Read IN ORDER (total boot < 500 lines):
1. `skills/autodidact/BOOT.md` — stable rules, phase definitions, decision matrix
2. `memory/learning/state/active.json` — phase, tracks, budgets, stats
3. `memory/learning/state/queue.json` — task queue (max 25)
4. `memory/learning/state/blockers.json` — blockers + cooldown

**DO NOT** boot-load: ~~knowledge-graph.md~~ (remains reference until kg_query.py built; new knowledge → kg/*.md), ~~meta-awareness-board.md~~ (removed).

If `budget_reset_date` ≠ today → reset budgets to phase defaults (BOOT.md), update date.

## Step 2: DECIDE

Follow BOOT.md decision matrix:
1. Check queue for READY tasks matching current phase
2. Priority: **build > learn > plan > reflect > skip**
3. Enforce quotas; if budget exhausted, pick different action type
4. If blocked: use fallback tasks (see BOOT.md Blocked Mode)
5. Nothing to do: principled skip with 1-line reason

**IDEATION FREEZE (2026-03-18):** READY >= 10 → no new queue tasks. Ideas → `idea-backlog.md` only. Lift when READY < 10 or Leo approves.

**Blocked mode:** When `blocked: true` and `now < unblock_check_at` — do NOT reassess. Pick from `fallback_tasks` or `playbooks/blocked.md`.

## Step 3: ACT

ONE focused action. Stay within 90 seconds compute.

**learn** — Tie to Q-xxx. Structured notes: problem → method → results → connections → open questions.

**build** — Tier 0 (always OK): scaffolds, tests, harnesses, paper sections. Tier 1 (auto): CPU-only <5 min. Tier 2 (Leo only): GPU, large downloads. Write code, test, document.

**plan** — Quick (<2 min): adjust next 3 tasks. Medium (<5 min): + experiment spec. Thorough (<10 min): full proposal for Leo.

**ideate** — `ideate_seeds.py --json` → 20 cross-source combinations (novelty+feasibility >= 7) → queue via `queue_ops.py add` (unless FREEZE). Write all 20 to cycle file.

**reflect** — Triggers only: task failed 2x, phase transition, end-of-day, milestone. Max 12 lines + concrete action item.

## Step 4: RECORD

Append ONE JSON line to `memory/learning/logs/events.jsonl`:
```json
{"v":1,"ts":"...","cycle_id":"c-YYYYMMDD-HHMM","phase":"...","action":"...","task_id":"Q-xxx","summary":"...","artifacts":[],"next":"...","blocked":false,"duration_sec":80}
```
Optional cycle file in `cycles/` (<100 lines, format: `c-YYYYMMDD-HHMM.md`).

## Step 5: UPDATE STATE

Update `active.json`: decrement budget, update stats + `last_cycle`. If task completed → `queue_ops.py complete Q-xxx`.

## Constraints

- Cycle compute: < 90s (hard timeout: 300s). Boot context: < 500 lines.
- Max 25 queue tasks. Cycle files GC'd after 48h.
- No random arXiv in converge/execute. No meta-awareness boards.
- Night (23:00-08:00) is NOT auto-skip if high-value work available.
- Direction changes (goals, SKILL.md, cron) need Leo approval.
- **Hygiene:** every 5 cycles → micro-reflect; daily → consolidate; weekly → deep-reflect.

## Tools

`precheck.py` (gate) · `gc.py` (cleanup) · `queue_ops.py` (queue CRUD) · `ideate_seeds.py` (ideation seeds) · `kg_query.py` (knowledge search, v0)

## Integration

Autodidact does NOT write to task-board.md. Research → queue.json. Code → apply senior-engineer. Audit → events.jsonl (append-only, never edit).

## Values

See `references/values.md`. Core: Build > Read. Bounded. Phase-disciplined. Leo's time is precious.
