---
name: autodidact
description: >
  Autonomous self-directed learning and research agent (v2).
  Triggered every 30 minutes (or on demand) via cron.
  Use when the agent needs to autonomously learn, plan, build, or reflect
  towards long-term research goals. Also use when Leo says "自主學習",
  "自己想", "繼續研究", "autodidact", "self-study", or when a cron job triggers.
---

# Autodidact v2 — Autonomous Research Agent

Bounded boot. Phase-aware. Build-first.

## Step 0: Precheck

```bash
python3 skills/autodidact/tools/precheck.py
```

- If output starts with `SKIP` → reply `HEARTBEAT_OK` immediately. Done.
- If output starts with `RUN` → continue to Step 1.

## Step 1: ORIENT (boot — read state only)

Read these files IN ORDER. Total boot context < 500 lines.

1. `skills/autodidact/BOOT.md` — stable rules, phase definitions, decision matrix
2. `memory/learning/state/active.json` — current phase, tracks, budgets, stats
3. `memory/learning/state/queue.json` — task queue (max 25)
4. `memory/learning/state/blockers.json` — current blockers + cooldown

### DO NOT boot-load these files:
- ~~progress.md~~ (deprecated → events.jsonl)
- ~~goals.md~~ (deprecated → active.json + BOOT.md)
- ~~knowledge-graph.md~~ (deprecated → kg/ directory, query via kg_query.py)
- ~~meta-awareness-board.md~~ (removed — generated recursive self-reflection)

### Budget reset
If `active.json` budgets `budget_reset_date` ≠ today → reset budgets to phase defaults (see BOOT.md quotas table), update `budget_reset_date`.

## Step 2: DECIDE

Follow the decision matrix in BOOT.md. Key rules:

1. Check queue for READY tasks matching current phase
2. Pick action based on priority: **build > learn > plan > reflect > skip**
3. Enforce quotas: if a budget is exhausted, pick a different action type
4. If blocked: use fallback tasks from blockers.json (see BOOT.md Blocked Mode)
5. If nothing to do: principled skip with 1-line reason

### Blocked mode
When `blockers.json` has `blocked: true` and `now < unblock_check_at`:
- Do NOT check if still blocked
- Pick from `fallback_tasks` list
- Read `skills/autodidact/playbooks/blocked.md` for task ideas

## Step 3: ACT

Execute ONE focused action. Stay within 90 seconds compute.

### learn
- Must tie to a specific queue task (Q-xxx)
- Read the paper/resource
- Write structured notes: problem → method → results → connection to tracks → open questions
- Update the queue task status if done

### build (Tier 0 / Tier 1 only)
- Tier 0 (always OK): code scaffolds, tests, eval harnesses, configs, paper sections, static analysis, comparison tables
- Tier 1 (auto-allowed): CPU-only scripts <5 min, unit tests, small-sample analyses
- Tier 2 (Leo approval only): GPU runs, large downloads, expensive infra
- Write code, test it, document what you built

### plan
- Quick (<2 min): review active tracks, adjust next 3 tasks
- Medium (<5 min): review + experiment spec drafting
- Thorough (<10 min): full state review, produce proposal for Leo

### reflect (triggers only)
- Only run when: task failed 2x, phase transition, end-of-day, build milestone
- Max 12 lines output
- Must produce a concrete action item (not just observations)

## Step 4: RECORD

**Append ONE JSON line** to `memory/learning/logs/events.jsonl`:
```json
{"v":1,"ts":"2026-03-01T12:00:00+08:00","cycle_id":"c-20260301-1200","phase":"converge","action":"build","task_id":"Q005","summary":"Implemented gc(k) eval harness scaffold with mock data","artifacts":["skills/autodidact/scripts/gc_eval.py"],"next":"Test with real Whisper activations when Leo unblocks","blocked":false,"duration_sec":80}
```

**Optional**: Write a cycle file to `memory/learning/cycles/` for detailed notes (deep reads, complex builds). Keep under 100 lines. Use format: `c-YYYYMMDD-HHMM.md`.

## Step 5: UPDATE STATE

Update `memory/learning/state/active.json`:
1. Decrement the budget for the action type used (learn/build/reflect)
2. Update `stats` (increment relevant counter)
3. Update `last_cycle` with cycle_id, action, and 1-line summary
4. If a queue task was completed → update it via `queue_ops.py complete Q-xxx`

## Constraints

- Each cycle: aim for < 90 seconds compute (cron hard timeout: 300s)
- Boot context: < 500 lines (enforced by file structure)
- Max 25 tasks in queue.json
- Cycle files GC'd after 48h (gc.py runs daily)
- No random arXiv browsing in converge/execute phase
- No meta-awareness questions or self-reflection boards
- Direction changes (goals, SKILL.md, cron) need Leo approval

## Tools

| Tool | Purpose |
|------|---------|
| `tools/precheck.py` | Gate: should this cycle run? |
| `tools/gc.py` | Garbage collect cycle files + validate caps |
| `tools/queue_ops.py` | Manage task queue (add/complete/block/unblock/list) |
| `tools/kg_query.py` | Query knowledge graph (Phase 5, not yet built) |

## Integration

- **task-board.md**: Autodidact does NOT write to the main task board. Research tasks stay in queue.json.
- **self-improve (learn.py)**: Use for system-level lessons, not research notes.
- **senior-engineer**: Apply when writing code (build actions).
- **events.jsonl**: Single append-only audit trail. Never edit past entries.

## Values

See `references/values.md` for full list. Core: Build > Read. Bounded. Phase-disciplined. Leo's time is precious.
