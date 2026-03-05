# Autodidact v2 Redesign — Deep Research

> Source: Leo's deep research tool, received 2026-03-01 11:37
> Status: Implementation planning

## Summary

Root-cause diagnosis of 8 failures (F1-F8) → 8 root causes (RC1-RC8) → 11-section redesign proposal.

### Root Causes
- **RC1**: No working-set vs archive separation (logs as state)
- **RC2**: No enforced invariants (no GC, no hard caps)
- **RC3**: Monolithic read instead of retrieval (no query API)
- **RC4**: No canonical state object (multiple overlapping files)
- **RC5**: Missing phase controller + done-ness criteria
- **RC6**: Build permission too coarse (all build = risky)
- **RC7**: Cron frequency mismatched to task granularity
- **RC8**: Multi-machine Git sync amplifies conflicts

### Key Design Principles (from literature survey)
- AI Scientist: project-as-directory + pipeline stages > global append-only logs
- ResearchAgent: knowledge as entities+relations (queryable), not prose dump
- Voyager: unbounded long-term memory OK if retrieval is bounded (top-k)
- Reflexion: reflection should be event-triggered, not habitual
- Agent Laboratory: phase gates + "N relevant texts then stop" prevents infinite reading
- OpenHands: context condensation as first-class scaling problem

### v2 Architecture (11 sections)
1. **File layout + bounded boot** (<500 lines total boot read)
2. **Event log (JSONL)** replacing progress.md + daily/weekly digests
3. **Goals: active/backlog/archive** (max 2 tracks, 3 objectives, 5 tasks active)
4. **Queryable KG** (nodes/edges JSONL, active subgraph capped at 200/800)
5. **Phase controller** (explore→converge→execute state machine + quotas)
6. **Smart skip** (precheck.py gate before spawning LLM)
7. **Blocked-time playbook** (cooldown + fallback tasks)
8. **Build tiers** (Tier 0 always allowed, Tier 1 CPU auto, Tier 2 needs Leo)
9. **Bounded reflection** (budget + triggers, max 5 open tickets)
10. **Real GC** (mandatory deletion, fail-loudly on cap violations)
11. **Ecosystem integration** (task-board, self-improve, senior-engineer)

### 48-Hour Migration Priority
1. `active.json` + `BOOT.md` → cuts F1
2. `events.jsonl` → stops unbounded growth
3. `gc.py` → fixes F2
4. Phase + quotas → fixes F7, pushes build
5. Blocked cooldown + playbook → fixes F4
6. Precheck wrapper → fixes F3

Full document: `/home/leonardo/.openclaw/media/inbound/5520d9a5-c56e-4662-9bdf-a6debeddead9.txt`
