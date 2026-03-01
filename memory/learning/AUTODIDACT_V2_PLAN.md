# Autodidact v2 Migration Plan

> Classification: **C — Infra / automation / shared state** (treat as production)
> Author: Little Leo (Lab), 2026-03-01
> Source: Leo's deep research (autodidact-v2-redesign.md)
> Status: **DRAFT — awaiting Leo approval**

---

## 0. Problem Quantification

### Boot cost (v1)
| File | Lines | Boot-loaded? |
|------|-------|-------------|
| SKILL.md | ~200 | ✅ always |
| progress.md | 566 | ✅ always |
| goals.md | 196 | ✅ always |
| Latest cycle file | ~60 | ✅ always |
| **Boot total** | **~1,022** | **2x over 500-line target** |

### Agent-loaded during cycles (adds to context mid-run)
| File | Lines | Purpose |
|------|-------|---------|
| knowledge-graph.md | 433 | Prose dump of papers/concepts |
| meta-awareness-board.md | 332 | Self-reflection questions (F6 generator) |
| ai-safety-radar.md | 463 | Paper scout report |
| paper-a-pitch.md | 201 | Paper A draft |
| paper-b-pitch.md | 219 | Paper B draft |
| experiment-queue.md | 187 | Blocked experiment list |
| idea_gate.md | 142 | Idea evaluation tracker |
| 2026-02-28_results_inventory.md | 154 | One-time snapshot |
| unblock-request.md | 83 | Single blocker description |
| SUNDAY-BRIEF.md | 80 | Ephemeral handoff doc |
| backlog-scan-list.md | 51 | Paper scan queue |
| paper-reading-list.md | 29 | Reading queue |
| **Auxiliary total** | **~2,374** | |

### File hoarding
- **98 cycle files** across 4 days (avg 24.5/day)
- **3 daily digests** exist — but source cycle files never deleted after digesting
- **77 cycle files** are pre-digest (should have been deleted)
- **952KB** total directory size, 4 days old

### Behavioral evidence of failure
- Last 20 cycles (#96-115): **10 skips, 7 reflects, 2 learns, 1 report, 0 builds**
- Meta-board reached "20/20 SATURATED" — system invented busywork to justify reflect cycles
- "Execution-blocked 43h" with no blocked-time playbook
- progress.md growing ~40 lines/day = unbounded

---

## 1. Architecture Decisions

### D1: Data location — `memory/learning/` (not `skills/autodidact/`)
**Rationale**: Our convention is code in `skills/`, data in `memory/`. All current autodidact data already lives in `memory/learning/`. Tools (Python scripts) go in `skills/autodidact/tools/`.
```
skills/autodidact/
  SKILL.md          # v2 (rewritten)
  BOOT.md           # Stable rules (<200 lines, changes rarely)
  tools/            # precheck.py, gc.py, kg_query.py, queue_ops.py
  playbooks/        # blocked.md, explore.md, converge.md, execute.md
  references/       # existing (values.md, planning.md, cheatsheets)
  scripts/          # existing research code (whisper_*.py)

memory/learning/
  state/
    active.json     # Single source of truth (<120 lines)
    queue.json      # Task queue (<200 lines, max 25 tasks)
    blockers.json   # Current blockers + cooldown (<80 lines)
  logs/
    events.jsonl    # Append-only cycle log (replaces progress.md)
    metrics.jsonl   # Append-only cost/timing metrics
  kg/
    active_nodes.jsonl    # Bounded (≤200 nodes)
    active_edges.jsonl    # Bounded (≤800 edges)
    archive_nodes.jsonl   # Append-only overflow
    archive_edges.jsonl   # Append-only overflow
    kg_summary.md         # Map-of-the-map (<150 lines)
  cycles/           # Ephemeral per-cycle notes (GC after 48h)
  digests/
    daily/          # Daily consolidation
    weekly/         # Weekly consolidation
  pitches/          # Paper pitches (paper-a-pitch.md, paper-b-pitch.md)
  archive/          # Deprecated files moved here
```

### D2: Boot set = BOOT.md + active.json + queue.json + blockers.json
**Target: <500 lines total.**
| File | Max lines | Content |
|------|-----------|---------|
| BOOT.md | 200 | North star, core loop, phase rules, quotas, constraints |
| active.json | 120 | Phase, active tracks, objectives, stats, budgets |
| queue.json | 200 | Top 25 tasks with status/priority |
| blockers.json | 80 | Current blockers + cooldown + fallback tasks |
| **Total** | **600** | Slightly over but JSON is token-dense; effective ~450 |

Everything else is **lazy-loaded via query scripts** — only when the task requires it.

### D3: Kill meta-awareness-board
The meta-board generated 20+ recursive self-reflection questions, consuming cycles with zero external value. Replace with:
- **max 5 self-improve tickets** tracked in active.json (not a separate file)
- Reflection only on **triggers**: task failure 2x, phase transition, end-of-day digest, build milestone
- Budget: max 1 reflect cycle/day (not 7 of 20 as observed)

### D4: Consolidate overlapping files
| Current file | v2 destination | Action |
|-------------|---------------|--------|
| progress.md | logs/events.jsonl + active.json stats | Parse stats → active.json, archive file |
| goals.md | BOOT.md (north star) + active.json (objectives) | Split and archive |
| knowledge-graph.md | kg/active_nodes.jsonl + active_edges.jsonl | Migrate to structured JSONL |
| meta-awareness-board.md | active.json self_improve_tickets (max 5) | Extract open items, archive rest |
| experiment-queue.md | queue.json tasks | Migrate to queue, archive |
| unblock-request.md | blockers.json | Migrate, delete |
| SUNDAY-BRIEF.md | *(ephemeral, auto-generated)* | Delete |
| idea_gate.md | queue.json (type=idea) | Migrate, archive |
| backlog-scan-list.md | queue.json (type=scan) | Migrate, archive |
| paper-reading-list.md | queue.json (type=read) | Migrate, archive |
| ai-safety-radar.md | kg/ nodes + pitches/ | Split, archive |
| 2026-02-28_results_inventory.md | digests/daily/ | Move to digest, archive |

### D5: Precheck runs inside the LLM session (not external)
OpenClaw cron spawns LLM sessions — we can't run Python before the LLM. So:
1. SKILL.md v2 Step 0 = `python3 tools/precheck.py`
2. If output = `SKIP` → agent replies `HEARTBEAT_OK` immediately (1 tool call, ~2 seconds)
3. If output = `RUN` → proceed with full cycle
**Cost**: Still spawns a session, but skip cycles cost ~500 tokens vs ~8000 for full cycles.
**Future optimization**: If we move to system cron, precheck can gate before LLM spawn (zero cost skip).

### D6: Keep sonnet model for now
Deep paper reads require sonnet quality. Cost savings come from:
- Bounded boot (50% fewer input tokens)
- Real skips via precheck (no busywork cycles)
- GC reducing file count
- These 3 together likely save more than a model downgrade would.

### D7: Phase starts at `converge`
Based on current state (16 deep reads, 19 gaps, 7 ideas, 2 paper pitches), the system is clearly past `explore`. Initial phase = `converge` with exit criteria for `execute`.

### D8: Existing research scripts stay
`whisper_hook_demo.py`, `whisper_logit_lens.py` stay in `skills/autodidact/scripts/`. They're research code, not infrastructure.

---

## 2. Phased Rollout

### Phase 0: Schema Design (no file changes, ~20 min)
**Goal**: Define all JSON schemas before writing any code.

- [ ] Define `active.json` schema (phase, tracks, objectives, stats, budgets, self_improve_tickets)
- [ ] Define `queue.json` schema (tasks with id, type, status, priority, track, due, definition_of_done)
- [ ] Define `blockers.json` schema (blocked, reason, unblock_check_at, fallback_mode, fallback_tasks)
- [ ] Define `events.jsonl` line schema (ts, cycle_id, phase, action, task_id, summary, artifacts, next, blocked, duration_sec)
- [ ] Define KG node/edge schemas
- [ ] Draft BOOT.md outline (<200 lines)

**Verify**: All schemas reviewed, no ambiguity.
**Rollback**: N/A (design only).

### Phase 1: State Infrastructure (~30 min)
**Goal**: Create new state files seeded from existing data. Old files untouched.

- [ ] Create directory structure: `memory/learning/{state,logs,cycles,digests/daily,digests/weekly,kg,pitches,archive}`
- [ ] Create `state/active.json` — seed from goals.md (north star, active tracks, objectives) + progress.md (cumulative stats)
- [ ] Create `state/queue.json` — seed from experiment-queue.md + idea_gate.md + backlog-scan-list.md + paper-reading-list.md (top 25 items only)
- [ ] Create `state/blockers.json` — seed from unblock-request.md
- [ ] Create `logs/events.jsonl` — empty (new cycles start writing here)
- [ ] Create `logs/metrics.jsonl` — empty
- [ ] Write `skills/autodidact/BOOT.md` — extract north star from goals.md, add phase rules + quotas + constraints

**Verify**: `python3 -c "import json; [json.load(open(f)) for f in ['memory/learning/state/active.json','memory/learning/state/queue.json','memory/learning/state/blockers.json']]"` succeeds. Boot files total <500 lines: `wc -l skills/autodidact/BOOT.md memory/learning/state/*.json | tail -1`.
**Rollback**: `rm -r memory/learning/{state,logs,kg,cycles,pitches,archive}; rm skills/autodidact/BOOT.md`.

### Phase 2: Build Tools (~40 min)
**Goal**: precheck.py + gc.py + queue_ops.py working and tested.
**Depends on**: Phase 1 (needs state files to exist).

- [ ] Write `skills/autodidact/tools/precheck.py`
  - Reads queue.json + blockers.json + active.json (cheap, no LLM)
  - Checks: READY tasks? New approvals? GC overdue? Blocked cooldown expired?
  - Outputs: `RUN` or `SKIP` + 1-line reason
  - Forced run every 6 hours regardless (anti-false-negative)
- [ ] Write `skills/autodidact/tools/gc.py`
  - Consolidates cycle files >48h into daily digests (moves existing `*-digest.md` to `digests/daily/`)
  - Deletes consolidated cycle files
  - Trims active KG to caps (200 nodes / 800 edges → overflow to archive)
  - Validates state file sizes (fail loudly if over caps)
  - `--dry-run` by default, `--apply` to execute
- [ ] Write `skills/autodidact/tools/queue_ops.py`
  - add/complete/block/unblock/list operations on queue.json
  - Enforces max 25 items (oldest completed → evicted)
- [ ] *(Phase 5)* `kg_query.py` deferred — KG migration is Phase 5

**Verify**:
```bash
python3 skills/autodidact/tools/precheck.py          # outputs RUN or SKIP
python3 skills/autodidact/tools/gc.py --dry-run       # shows what would be deleted/consolidated
python3 skills/autodidact/tools/queue_ops.py list      # shows seeded tasks
```
**Rollback**: Delete tool files (no state changes).

### Phase 3: SKILL.md v2 + Cron Update (~30 min)
**Goal**: New cycles use v2 boot flow. This is the commit point.
**Depends on**: Phase 1 + Phase 2.

- [ ] Back up current SKILL.md → `skills/autodidact/SKILL.v1.md`
- [ ] Rewrite SKILL.md v2:
  - Step 0: Run precheck.py → SKIP = immediate exit
  - Step 1: ORIENT = read BOOT.md + active.json + queue.json + blockers.json ONLY
  - Step 2: DECIDE = phase-aware decision matrix with quotas
  - Step 3: ACT = action types with phase-specific allowed actions
  - Step 4: RECORD = write events.jsonl line + optional cycle file
  - Step 5: UPDATE STATE = update active.json (stats, budgets, last_cycle)
  - Remove: progress.md references, knowledge-graph.md boot-load, meta-board
- [ ] Write playbooks: `playbooks/blocked.md`, `playbooks/converge.md`
- [ ] Update cron description/task prompt (if needed — the cron triggers the skill, so SKILL.md change should be sufficient)
- [ ] **Manual test**: Trigger one autodidact cycle, verify it:
  - Reads BOOT.md + state files (not progress.md)
  - Writes to events.jsonl (not progress.md)
  - Respects phase quotas
  - Total boot context <500 lines

**Verify**: Manual cycle completes successfully. `cat memory/learning/logs/events.jsonl | python3 -m json.tool` shows valid entry. `wc -l memory/learning/progress.md` unchanged (v2 doesn't touch it).
**Rollback**: `mv skills/autodidact/SKILL.v1.md skills/autodidact/SKILL.md` — one file restore.

### Phase 4: Data Migration + Cleanup (~20 min)
**Goal**: Delete hoarded files, archive deprecated files, run GC.
**Depends on**: Phase 3 verified (v2 cycles working).
**Wait**: Run ≥3 successful v2 cycles before this phase.

- [ ] Run `gc.py --apply` to:
  - Delete 77 pre-digest cycle files (digests already exist for Feb 26-28)
  - Consolidate Mar 1 cycles into digest
  - Move 3 existing digest files to `digests/daily/`
- [ ] Move deprecated files to `archive/`:
  - `progress.md` → `archive/progress.v1.md`
  - `meta-awareness-board.md` → `archive/meta-awareness-board.v1.md`
  - `unblock-request.md` → DELETE (migrated to blockers.json)
  - `SUNDAY-BRIEF.md` → DELETE (ephemeral)
  - `backlog-scan-list.md` → DELETE (migrated to queue.json)
  - `paper-reading-list.md` → DELETE (migrated to queue.json)
  - `2026-02-28_results_inventory.md` → `digests/daily/`
- [ ] Move pitches: `paper-a-pitch.md`, `paper-b-pitch.md` → `pitches/`
- [ ] Leave in place (still valuable, lazy-loaded):
  - `goals.md` — keep as reference but BOOT.md is canonical
  - `ai-safety-radar.md` — migrate to KG in Phase 5
  - `idea_gate.md` — keep until queue.json proven
  - `experiment-queue.md` — keep until queue.json proven
- [ ] Add deprecation pointer to `goals.md`: "Canonical state now in state/active.json + BOOT.md"
- [ ] `git add -A && git commit -m "autodidact: v2 migration phase 4 — cleanup + archive" && git push`

**Verify**: `find memory/learning -name '2026-*_cycle*.md' | wc -l` < 10. `du -sh memory/learning/` significantly smaller.
**Rollback**: `git checkout HEAD~1 -- memory/learning/` restores all files.

### Phase 5: KG + Build Tiers + Advanced (~60 min, tomorrow)
**Goal**: Structured queryable KG, build tier system.
**Depends on**: Phase 4 complete, v2 running stable.

- [ ] Parse knowledge-graph.md → `kg/active_nodes.jsonl` + `kg/active_edges.jsonl`
  - Nodes: papers, concepts, gaps, ideas (with id, type, title, tags, summary)
  - Edges: relations (motivates, uses, contradicts, extends, etc.)
- [ ] Write `skills/autodidact/tools/kg_query.py`
  - `--node <id> --depth N` — subgraph around a node
  - `--search <term>` — text search across nodes
  - `--neighbors <id>` — direct connections
  - Output clipped to <50 lines for prompt inclusion
- [ ] Write `kg/kg_summary.md` — "map of the map" (<150 lines)
- [ ] Add build tier definitions to BOOT.md:
  - Tier 0 (always OK): code scaffolding, tests, eval harness, configs, paper sections, static analysis
  - Tier 1 (auto-allowed): CPU-only scripts <5 min, unit tests, small-sample analyses
  - Tier 2 (Leo approval): GPU runs, large downloads, expensive infra changes
- [ ] *(Optional)* Approval packet template: `state/pending_approvals.md`
- [ ] Deprecate `knowledge-graph.md` → `archive/knowledge-graph.v1.md`

**Verify**: `python3 skills/autodidact/tools/kg_query.py --search "AudioLens"` returns relevant nodes. Active node count ≤200.
**Rollback**: KG files are additive; can delete `kg/` dir without affecting v2 core.

---

## 3. Cron Changes

### Current cron
- ID: `0bf052cf`
- Schedule: `:15/:45 08-23`
- Model: sonnet
- Task: triggers autodidact skill

### Changes needed
- **Phase 3**: No cron config change needed. SKILL.md v2 handles precheck internally.
- **Future optimization**: If skip rate >60%, consider:
  - Reducing frequency to every hour during known dead zones (weekends, late night)
  - Or adding system cron precheck gate (zero-cost skip)

---

## 4. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| v2 SKILL.md confuses agent → broken cycles | Medium | High | Keep v1 as backup; manual test before enabling cron; rollback = 1 file |
| Over-pruning loses valuable context | Low | Medium | Archive everything before deleting; digests contain summaries + file refs |
| Schema drift in JSONL over time | Medium | Low | Add `version` field to all schemas; gc.py validates schema |
| precheck false-negative (skips when work exists) | Low | Medium | Force-run every 6h regardless; queue_ops makes READY tasks explicit |
| Phase quotas too restrictive | Medium | Low | Quotas are config in active.json; adjustable without code change |
| GC deletes cycle file before digest written | Low | High | gc.py checks digest exists before deleting; `--dry-run` default |
| Multi-machine conflict (Mac also runs cycles) | Low | Medium | Only Lab runs autodidact cron; single-writer by convention. Formalize later if needed |

---

## 5. Success Metrics (measure after 1 week)

| Metric | v1 baseline | v2 target |
|--------|------------|-----------|
| Boot context lines | ~1,022 | <500 |
| Cycle files retained | 98 (4 days) | <20 (48h window) |
| Skip+reflect % of last 20 cycles | 85% (17/20) | <40% |
| Build actions per day | 0 | ≥2 |
| Total files in memory/learning/ | 115 | <30 (excluding archive/) |
| Directory size (excl. archive) | 952KB | <200KB |

---

## 6. Dependencies DAG

```
Phase 0 (Schema Design)
    ↓
Phase 1 (State Infrastructure)
    ↓
Phase 2 (Build Tools)
    ↓
Phase 3 (SKILL.md v2 + Test) ← COMMIT POINT
    ↓
    [run ≥3 v2 cycles successfully]
    ↓
Phase 4 (Data Migration + Cleanup)
    ↓
Phase 5 (KG + Build Tiers)
```

**Estimated total time**: ~3 hours across phases 0-4, +1 hour for phase 5.
**Can be interrupted**: Each phase is independently committable to Git.

---

## 7. What I'm NOT Doing (and why)

| Skipped feature | Reason |
|----------------|--------|
| Multi-machine lease/lock | Only Lab runs autodidact cron; unnecessary complexity |
| External cron precheck (zero-cost skip) | Requires system cron setup; internal precheck is good enough for now |
| Weekly digests | Daily digests are sufficient; weekly can be added later if needed |
| Approval packet system | Start with simple blockers.json; upgrade if friction is high |
| Model switching (sonnet → g53s) | Deep reads need sonnet quality; cost savings come from other vectors |
| Full queue_ops API | Start with basic add/complete/list; expand as needed |
