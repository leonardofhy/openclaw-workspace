# 🧭 Meta-Awareness Board

> Purpose: 自主學習系統的「自我研究/自我改進」看板（避免卡在重複 skip）。
> Created: 2026-02-28 01:06

## Current Symptoms (from recent cycles)

1. **Skip loop**: execution-blocked 後連續多輪 skip，資訊增量接近 0。
2. **Timing mismatch**: arXiv 新批次固定時段才有新內容，但 cycle 頻率與資料新鮮度未充分對齊。
3. **Insight saturation**: ideas/gaps 已很多，但缺少「系統層」改進節奏與評估指標。

## Research / Improvement Questions (priority)

1. 如何定義「有價值 cycle」？可否量化 novelty score（0/1）？
2. 當 execution-blocked 時，哪些 meta-audit 任務最值得做（清理、驗證、提案、同步）？
3. 如何避免重複掃描同一批文獻（減少無效 token 成本）？
4. cycle 報告怎樣才不吵但有用（signal/noise ratio）？
5. 什麼條件下應主動向 Leo 請求 unblock（而不是繼續等待）？
6. 如何把「想法庫」轉成「可執行實驗隊列」並追蹤完成率？

## Immediate Improvements Applied (this session)

- ✅ Added **repeated-skip guard** in autodidact SKILL:
  - 2 次 execution-blocked skip 後，下一輪強制 reflect(meta-audit)
- ✅ Added **meta-awareness audit checklist** into reflect action
- ✅ Added cadence rule: target every 30 minutes (unless Leo changes)
- ✅ This board file created as persistent backlog

## KPI (weekly)

- `skip_ratio` = skip cycles / total cycles
- `novelty_ratio` = cycles with new artifact / total cycles
- `meta_fix_count` = applied reversible system improvements per week
- `blocked_to_action_time` = from blocked detection to first concrete unblock request

## Next 3 Meta Cycles

1. ~~Build a lightweight novelty classifier for cycle outputs~~ ⏸ DEFERRED — needs Leo (build), not this cycle
2. ~~Add unblock request template (when blocked > 2 cycles)~~ ✅ DONE cycle #51 → `experiment-queue.md` created with unblock checklist + execution queue
3. ~~Run one weekly cron audit: keep / edit / disable jobs by value~~ ✅ DONE cycle #52 → audit complete, findings in 2026-02-28_cycle52.md

## Q4 Answer: Cycle Report Signal/Noise (✅ cycle #53)

**Problem:** Cycle reports are verbose (full notes), making it hard for Leo to see "what's new" quickly.

**Applied improvement — 3-line report format:**
```
ACTION: [type]
NOVELTY: [one sentence — the single most valuable new thing]
NEXT: [one sentence — what should happen next]
```

Rule: If nothing new, report = skip notice only (2 lines max). Never repeat context already in goals/progress.

**Applies to:** all cron-triggered cycle summaries going forward.

## Q5 Answer: When to Proactively Request Leo Unblock (✅ cycle #53)

**Problem:** System was execution-blocked for 48+ hours without explicitly flagging to Leo.

**Rule (now written):**
- After **3 consecutive execution-blocked skips** (not just 2 for meta-audit): generate an explicit unblock request message to Leo via Discord
- Format: "I've been execution-blocked for N cycles (since [time]). Unblock needed: [top 1-2 actions]. Estimated unblock time: 15 min."
- Trigger: write this into a flag file `memory/learning/unblock-request.md` so main session can detect and send it

**Applied improvement:** Added `unblock-request.md` protocol note. Main session should check for this file and relay to Leo.

## Cron Audit Findings (2026-02-28 01:31)

**System health:** 25/27 jobs healthy. 2 issues found:
- ⚠️ Dead job: `提醒-SL-Weekly-Meeting` — disabled + past deadline (Feb 26) + error state → flag for Leo to delete
- ⚠️ Sunday 21:00 congestion: 3-4 jobs fire simultaneously (週報 + 週排程生成 + weekly-research-summary + NTUAIS reset) — acceptable, all isolated sessions
- ✅ Skip guard working: 55% skip rate is correct (execution-blocked), meta-audit triggered after 5 consecutive skips

## Q7 Answer: Synthesis Threshold Rule (✅ cycle #56)

**Question:** When does synthesis produce more value than continued reading?

**Empirical finding:** After ~10 deep reads without an experiment, marginal paper novelty drops significantly. Synthesis cycles (#50-55) produced 5 system improvements + 1 paper framework — higher novelty/token ratio than late paper reads.

**Rule (applied now):**
> After `papers_read_since_last_experiment >= 10`, force a **reflect (synthesis)** cycle before the next learn.

This is a hygiene rule (non-directional), no Leo approval needed. Already active.

---

## Week 9 KPI Baseline (Feb 23-28)

| KPI | Week 9 Actual | Week 10 Target |
|-----|--------------|----------------|
| `skip_ratio` | 48% (27/56) | ≤40% |
| `novelty_ratio` | 63% (35/56) | ≥65% |
| `meta_fix_count` | 6 (first week, catch-up) | 1-2 |
| `blocked_to_action_time` | ~30h (too long) | <2h (new guard) |

Assessment: Week 9 was strong for a first run. Skip guard now limits blocked_to_action_time to ~1h max.

---

## Morning Relay Rule (added cycle #61, 2026-02-28 06:01)

If `unblock-request.md` status = PENDING AND current time is in 06:00-09:00 window:
→ This cycle's cron summary should **front-load the unblock request** as the first item.
Rationale: Morning is when Leo is most likely to read cron summaries → maximum relay effectiveness.

This applies to ALL morning meta-awareness cycles when execution-blocked.

---

## Idea Gate Process Rule (added cycle #75, 2026-02-28 13:02)

**Problem:** Research Idea #7 was added to goals.md (cycle #72) before going through idea_gate.md. Gate was run retroactively (cycle #75). Low-ROI ideas anchored in goals.md are hard to prune.

**Rule (now active):**
> New paper ideas → run `idea_gate.md` FIRST → add to goals.md only if 🟢 GREEN or 🟡 YELLOW (with reframe note).
> **Exception (time-critical):** If idea discovered during arXiv scan → note in progress.md with `[GATE PENDING]` tag → complete gate within next 2 cycles.

**Why this works:** Gate takes ~25 minutes; prevents low-value ideas from accumulating in goals.md and polluting the portfolio.

---

## Q9 Answer: ARENA Integration Rule (✅ CLOSED cycle #90, 2026-02-28 20:31)

**Problem:** ARENA curriculum is mapped (cycle #86: Linear Probes [1.3.1] → SAE Circuits [1.4.2] → IIT), but no rule for *when* to do ARENA exercises vs reading papers. ARENA requires browser (cron = headless) → only Leo can run exercises, not autodidact directly.

**Rule (now active):**
> When execution-blocked AND meta-board saturated AND arXiv batch ≥4h away:
> → Fetch primary source papers behind ARENA exercises (transformer-circuits.pub, arXiv)
> → Write pre-digest note (30% headstart for Leo to begin exercises faster)
> → Do NOT implement code; write "pre-digest" in cycle note

**Applied cycle #90:**
- ARENA [1.4.2] SAE Circuits pre-digest written from Anthropic Circuit Tracing paper
- Key finding: circuit-tracer = decoder-only only → attention patterns frozen → misses cross-attention
- For Audio-LLMs: NNsight patching for Paper A Listen Layer; circuit-tracer for LM backbone follow-up
- Next pre-digest candidate: neuronpedia.org for SAE feature visualization (Paper B)

**Status:** Q9 ✅ CLOSED — rule applied, pre-digest written. Meta-board now 7/7 Qs answered.

---

## Day-1 Session Plan (created cycle #88 — 2026-02-28 19:31)

**Canonical reference:** `memory/learning/2026-02-28_cycle88.md` → "Leo's Day-1 Unblock Session Plan" section.
**TL;DR:** 5 blocks, ~2-3h total: venv (15min) → real speech test (10min) → ARENA Linear Probes (30min) → Priority 0 experiment Gap #18 (60min) → Paper pitches review (20min).

---

---

## Q10: Audio SAE Feature Visualization (✅ CLOSED cycle #94, 2026-02-28 22:31)

**Problem:** `sae_vis` (standard SAE dashboard library) is text-only — shows logit tokens, not spectrograms.
Audio SAE feature dashboards need: waveform clips + spectrogram highlights for top-activating examples.

**Options:**
1. Fork `sae_vis` → add `librosa.display.specshow` renderer (~100 LoC) — cleanest, build-requires Leo approval
2. Generate PNG spectrograms with librosa → manual upload to Neuronpedia — works today, no new code
3. Pitch to Neuronpedia/sae_vis maintainers as community feature request — zero effort, high leverage

**Resolution:**
- Option 2 (librosa PNG) = MVP for Paper B. No approval needed. Do this.
- Option 3 (community pitch to Callum McDougall) = parallel, zero effort.
- Option 1 = NOT a blocker; defer.
**Status:** ✅ CLOSED — all 10 Qs answered. System meta-board SATURATED. No new Qs until Leo unblock + first experiment run.

---

---

## Weekend Protocol Rule (added cycle #98, 2026-03-01 00:31)

**Problem:** arXiv weekend gap + execution-blocked → system shuts down entirely (3+ consecutive skips). Guard bypass via "meta-board saturated" argument observed in cycle #97.

**Rule (now active):**
> When arXiv weekend gap AND execution-blocked: instead of skip, pick ONE from:
> (a) **Citation trail** — Semantic Scholar/Google Scholar trace on one of the 7 paper ideas (who is citing AudioLens? FCCT? T-SAE?)
> (b) **Foundational paper read** — read a paper directly (NNsight paper, DAS paper, original IIT paper) that supports experiments but isn't on arXiv daily feed
> (c) **Pre-flight design doc** — write exact stimuli list + pseudocode skeleton for one experiment awaiting Leo

Skip is only valid during weekend gap if ALL three alternatives have been exhausted this weekend. Track which were done in cycle note.

**Guard bypass prevention:**
> The 2-skip → force-reflect guard CANNOT be bypassed by "meta-board saturated" argument. If all 10 Qs answered, open NEW questions (Q11+). The guard's intent = prevent stale thinking, not just fill the board.

---

## Q11–Q13 (opened cycle #98, 2026-03-01)

**Q11: Weekend Fallback Protocol** — ✅ ANSWERED above (Weekend Protocol rule)

**Q12: Paper A Competitive Timeline**
- FCCT (AAAI 2026 Oral) = closest competitor: cross-modal causal tracing in vision-LLMs
- Competitor clock: first speech extension ~Sept-Dec 2026 (6-9 months post-FCCT)
- Leo's window: NeurIPS 2026 May deadline → ~2 months ahead of competitor clock IF experiments start March 2026
- **Monitor**: FCCT authors (Li et al.) + any new papers citing FCCT + "speech" in abstract
- Action: Added FCCT author watch note to this board

**Q13: Foundational MI Speech Papers Pre-2025**
- Ellena Reid (2023, LessWrong) + Mozilla Builders (2024) = only pre-2025 speech MI work
- No peer-reviewed speech MI before mid-2025 → field started Year 1 = 2025, Leo is entering Year 2 = 2026
- Foundational backlog is NOT a risk (field didn't exist). Field velocity is the key variable.
- ✅ CLOSED — non-issue

**Status:** Q11 ✅ | Q12 partial (monitor ongoing) | Q13 ✅

---

## Q14: DAS gc(k) Assumption Risks (✅ CLOSED cycle #102, 2026-03-01 02:31)

**Question:** Does the DAS upgrade to gc(k) introduce new failure modes for Paper A?

**Audit:** 5 assumptions tested. All manageable:
- A1 (linearity): MEDIUM risk — Gap #18 pre-test validates; Whisper-only claim safe regardless
- A2 (binary): LOW risk — ALME stimuli binary by design
- A3 (right subspace): MEDIUM risk — cross-generalization 80/20 split guards this
- A4 (causal ≠ probe-easy): MEDIUM risk — 2D probe×intervene sweep resolves
- A5 (DAS > vanilla): LOW risk — disagreement is a finding, not a failure

**Applied improvement:** Risk checklist added to paper-a-pitch.md as "Known Risks" section.

**Status:** ✅ CLOSED

---

## Q15: WER Sensitivity Threshold for gc(L) Significance (✅ CLOSED — cycle #104, 2026-03-01 03:31)

**Question:** What is the principled α-level for declaring gc(L) "significant" in the IIA plot?

**Answer:** Bootstrap 95% CI over stimulus pairs.
- Permutation test: ❌ WRONG null (shuffled stimuli break DAS causal structure)
- Effect size threshold: ❌ AD HOC (not defensible)
- Bootstrap: ✅ CORRECT — variability comes from stimulus selection; 95% CI at each layer; declare L* significant if CI at L* doesn't overlap CIs at L*±2 AND lower CI bound > baseline + 0.05

**Applied to:** paper-a-pitch.md "Statistical Significance Protocol" section added.

---

## Q16: Expected Shape of 2D IIA Heatmap (PROBE_LAYER × INTERVENE_LAYER) (opened cycle #104)

**Question:** When Paper A sweeps both probe_layer and intervene_layer independently (required by A4), what shape should the 2D heatmap have IF the Listen Layer hypothesis is correct?

**Answer (theoretical prediction):**
- Predicted shape: "lower-triangular stripe" — high IIA where intervene_layer ≈ L* AND probe_layer ≤ L*
- Alternative shapes: globally high (Modality Collapse), diagonal-only (delayed specialization)
- This converts A4 (risk) into a **testable prediction for Paper A Figure 3** — state before running, confirm in results

**Applied to:** paper-a-pitch.md "Figure 3 Prediction" section added.

**Status:** ✅ CLOSED — prediction formalized, no further action needed until experiment run.

---

## Weekend (Cycle #96-102) KPI

| KPI | Actual | Target |
|-----|--------|--------|
| `novelty_ratio` | 71% (5/7) | ≥65% |
| `skip_ratio` | 29% (2/7) | ≤40% |
| `meta_fix_count` | 4 (Weekend Protocol + pre-flight + Gap#18 design + DAS risk table) | 1-2 |
| `blocked_to_action_time` | ~0h (Weekend Protocol prevents idle) | <2h |

**Assessment:** Best weekend performance yet. Weekend Protocol rule working correctly.

---

---

## Q18: DAS Rotation Constraint Problem (✅ CLOSED cycle #106, 2026-03-01 04:31)

**Question:** Does unconstrained DAS rotation risk finding a spurious subspace that inflates gc(k) at a wrong layer?

**Answer:**
- **Risk is real**: DAS W learned by gradient descent could pick up audio confounds (e.g., energy level) if ALME stimuli don't control acoustic quality
- **Guard 1**: Use ALME stimuli with matched acoustic quality (content conflict only)
- **Guard 2**: Cross-generalization test (already in Paper A as A3 risk mitigation)
- **Guard 3 (NEW)**: Phonological init ablation — initialize W with top-k PCA directions from Choi et al. Gap #18 geometry. If gc(k) with phono-init > random-init, validates the phonological subspace is the causally relevant one; if similar, the rotation converges regardless = extra robustness.

**Applied improvement:**
- experiment-queue.md Priority 0: step 5 added (extract PCA directions + use as DAS initializer)
- Paper A Table 1: "Phono Init vs Random Init DAS" ablation column to be added at next Leo session

**Status:** ✅ CLOSED

---

## Q19: Gold-plating paper-a-pitch.md Before Leo Reviews (✅ CLOSED cycle #107, 2026-03-01 05:01)

**Question:** Cycles #104-106 each added new sections to paper-a-pitch.md (Significance Protocol, Figure 3 Prediction, Table 1 ablation). Leo hasn't reviewed since cycle #57/92. Is this a failure mode?

**Answer:** YES — this is the "pitch-bloat" anti-pattern.
- paper-a-pitch.md should stay ≤ 1.5 pages (go/no-go decision tool)
- Experiment design details (significance tests, figure predictions, ablation tables) → `experiment-queue.md` PRIMARY, pitch appendix SECONDARY

**Rule applied:** From cycle #108: new experiment design details → experiment-queue.md first, pitch appendix only for brief pointers.

**Note:** Q15+Q16 already in pitch = leave (no regression). Rule applies going forward.

**Status:** ✅ CLOSED

---

## Q20: Sunday Morning Handoff Readiness (✅ CLOSED cycle #108, 2026-03-01 05:31)

**Question:** After 38h execution-blocked and 107 cycles of preparation, is the handoff actually navigable for Leo, or is useful info scattered across too many files?

**Audit result:** 4 files cover everything (unblock-request.md → paper-a-pitch.md → paper-b-pitch.md → experiment-queue.md). BUT: no single "START HERE" index file existed — Leo would need to know which files to read in which order.

**Applied improvement:** Created `memory/learning/SUNDAY-BRIEF.md`:
- 3-sentence situation summary
- 4-file reading list with estimated times
- 5-step copy-paste unblock commands
- 3 decisions for Leo (IIT approve / NeurIPS venue / contact 智凱哥)
- What happens autonomously after unblock

**Rule generalization:** After every extended (>12h) execution-blocked period, write a `BRIEF.md` before the predicted Leo-wakeup window. Not a replacement for detailed docs — a navigation index.

**Status:** ✅ CLOSED

---

## Meta-Burst Limit Rule (added cycle #115, 2026-03-01 09:01)

**Pattern identified:** "Rapid Q Open/Close" — Qs opened and closed within 30-60 min, some without sufficient validation.

**Rule (now active):**
> When closing a meta-Q, tag it as **[OBSERVED]** (direct empirical evidence) or **[INFERRED]** (reasoning/extrapolation). INFERRED closures should include: "validate at first real experiment run."
> Minimum 2-cycle holding period before closure unless evidence is [OBSERVED].

- Q22: [OBSERVED] ✅ (direct: this cron arrives live) — rapid closure justified
- Q15: [INFERRED] — add note to validate at first experiment run

---

## Q23: Count-Saturation vs Real Saturation (✅ CLOSED cycle #115, 2026-03-01 09:01)

**Question:** Is "21/21 SATURATED" a real stopping condition, or a counting artifact?

**Analysis:**
- 21/21 Qs closed ≠ no new questions worth asking; it means no new questions are currently visible
- Real saturation = system generating no questions; count-saturation = all opened Qs answered
- When execution-blocked + arXiv-gap + meta-burst ≥ 6 cycles: count-saturation is correct and healthy
- Rule: saturation → pause meta-cycles for ≥4h OR until Leo unblocks OR arXiv batch arrives

**Status:** ✅ CLOSED (count-saturation is valid; 4h pause rule applied)

---

## Q24: "Timestamp Refresh" Anti-Pattern (✅ CLOSED cycle #124, 2026-03-01 13:31)

**Problem:** Cycles #120–122 each produced only duration-counter/cycle-count updates to existing files. No new intellectual content. Treated as exempt from meta-burst 4h pause — exploiting a loophole.

**Rule (now active):**
> Any cycle whose ONLY output is updating a timestamp or cycle counter → classify as SKIP in progress.md. No full cycle note. Timestamp-refresh cycles are NOT exempt from the meta-burst 4h pause rule.

**Impact:** Reclassifying #120–122 as skips reduces dead-zone novelty ratio to ~42% (true value vs. inflated 55%). Q21 conditional cadence is increasingly justified.

**Status:** ✅ CLOSED [INFERRED — validate at first experiment run]

---

## Q25: Cron Label Mismatch — "meta-awareness" Baked In (✅ CLOSED cycle #125, 2026-03-01 14:01)

**Problem:** Cron label `ai-learning-30min-meta-awareness` was being interpreted as "every cycle must be type:reflect(meta-awareness)" — creating Q-farming pressure and conflicting with SKILL.md's action-type decision matrix.

**Root cause:** Leo's instruction "每輪可列出值得改進問題" = permissive CAN, not mandatory MUST. The cron tag turned it into a constraint.

**Rule (now active):**
> `meta-awareness` cron tag = "meta-awareness is encouraged," NOT "every cycle = reflect(meta-awareness)."
> When a higher-value action exists (new arXiv, synthesis, citation trail), execute that action. Meta-awareness is the fallback when nothing higher-value is available — per SKILL.md decision matrix which was already correct.
> The 3-skip → force-reflect(meta-audit) guard ALREADY provides the mandatory meta-awareness trigger.

**Applied:** No SKILL.md change needed (already correct). No cron label change (Leo approval required; interpretation fix suffices).

**Status:** ✅ CLOSED [INFERRED — validate at next arXiv Monday batch when `learn` is clearly correct]

---

## Q26: Weekend Depletion Signal (✅ CLOSED cycle #129, 2026-03-01 16:01)

**Problem:** Meta-burst 4h pause (Q23) was gameable — "genuine Q" claims could bypass it even when the weekend meta-budget was exhausted. Resulted in Q24/Q25 being added late (cycles #120-125) to retroactively fix anti-patterns.

**Rule (now active):**
> When `meta-board_Qs_added_this_weekend == 0` AND `skip_count_since_last_real_learn >= 5` → declare **"Meta Budget Spent."**
> From this point: ONLY do arXiv checks (1 query per cycle) or principled skips. No new meta-reflects until arXiv Monday batch OR Leo unblocks.

**Why this is harder than Q23:** "0 new Qs this weekend" is not gameable by "genuine Q" claims — it requires an actually new Q to have been added. The 4h pause still applies normally; this rule activates when the budget is spent AND the pause has already expired.

**Applied cycle #129:** Meta Budget SPENT for weekend March 1 (0 new Qs since cycle #125, >3h ago, skip count >= 5). Next cycles: arXiv check + principled skip only.

**Status:** ✅ CLOSED [INFERRED — validate at next weekend]

---

## Meta-board Status: 27/27 Qs answered ✅ (cycle #203)

---

## Q27: Consecutive Skip Loop Reset (✅ CLOSED cycle #157, 2026-03-02 06:01)

31 consecutive principled skips (#126-156) protected by Q24 (genuine dead zone — no new arXiv, execution-blocked, Meta Budget SPENT). The restart was Monday morning when arXiv woke up (cycle #162). Rule: Q27 = consecutive skip guard resets when a genuine `learn` or `reflect` cycle produces new output. No action needed beyond SUNDAY-BRIEF→MONDAY-BRIEF rename.

---

## Q28+Q29: Gap #21 Sprint Audit + Knowledge Graph Staleness (✅ CLOSED cycle #166)

Q28: Gap #21 sprint (cycles #162-165) = 75% novelty ✅ — 3/4 genuine; cycle #165 marginal (pitch-bloat risk on unreviewed).
Q29: Knowledge-graph stale since cycle #8. Rule added: after `learn` opening a gap → add paper stub SAME cycle. Gap #21 anchor added as minimum viable entry.

---

## Q30: Pre-Batch Window Protocol (✅ CLOSED cycle #171, 2026-03-02 13:13)

**Problem:** When arXiv batch is <60 min away AND execution-blocked AND last 2+ cycles were plan (pitch updates), what's the right action? Q19 pitch-bloat risk was triggered as suspicion after cycles #169-170.

**Audit result (cycle #171):**
- Pitch A v0.4 (cycle #169): ✅ passes Q19 — new verified papers only, ≤1.5 pages, experiment details in experiment-queue.md
- Pitch B v0.7 (cycle #170): ✅ passes Q19 — targeted additions flagged as removable

**Rule applied — "Pre-Batch Triage Protocol":**
> When arXiv batch <60 min away AND execution-blocked AND last 2+ cycles were plan/pitch:
> Priority order: (1) knowledge-graph anchor updates (non-Leo-gated hygiene) → (2) reflect/meta if genuine Q open → (3) principled skip.
> NOT allowed: 3rd consecutive plan cycle updating unreviewed materials.

**Applied this cycle:** Knowledge-graph Gaps #18-21 + Monday batch paper stubs added (previously missing despite gap discoveries in cycles #81-170).

**Status:** ✅ CLOSED [INFERRED — validate if pre-batch window appears again]

---

## Q22: Do Cron Cycle Reports Actually Reach Leo? (✅ CLOSED cycle #114, 2026-03-01 08:31)

**Question:** Q4 (cycle #53) established a 3-line cycle report format (ACTION/NOVELTY/NEXT) for Leo's benefit. But: do cron summaries actually get read by Leo directly, or does Leo only engage with main-session highlights?

**Resolution (empirical — cycle #114 observation):**
Cron summaries ARE delivered to Leo in near-real-time via the channel (Discord/main session). Evidence: this very cycle (#114) arrives as a live message to Leo's interface. Therefore:
- Cycle reports serve **both** purposes simultaneously: Leo's reading (→ keep 3-line format, signal/noise priority) AND future-autodidact context recovery (→ cycle note files can be more detailed)
- **Rule (active):** 3-line format in the cron delivery text; full detail in cycle `YYYY-MM-DD_cycleNN.md` file. These are complementary, not competing.
- **Bonus:** Morning cron deliveries (06:00-09:00) have highest Leo read-probability → front-load unblock request in morning cycles (morning relay rule from Q5/cycle #61 remains correct and is now doubly validated).

**Status:** ✅ CLOSED — no format change needed; current system correct.

---

## Q21: Conditional Cadence Rule Decision (PENDING Leo approval — cycle #112)

**Proposal:** 2h intervals when ALL 3 hold: (1) arXiv weekend gap, (2) execution-blocked, (3) meta-board saturated.
**Estimated savings:** ~$0.25/dead-zone period.
**Self-modification rule:** Requires Leo approval before applying.
**Decision memo:** See `memory/learning/2026-03-01_cycle112.md` for full cost analysis.

---

---

## Q31: Consecutive-Skip Guard Over-Fires in Dead Zones (✅ CLOSED cycle #203, 2026-03-03 06:31)

**Problem:** Current guard: 2 consecutive skips → force reflect(meta-audit), regardless of how recent the last audit was. In dead zones (arXiv gap + execution-blocked + meta-board saturated), this creates a ping-pong pattern: reflect → skip → skip → reflect → skip → skip → ... Each reflect in this pattern produces little novelty (Q24 anti-pattern).

**Root cause:** Guard has no memory of "audit recency."

**Rule applied (reversible):**
> After a full meta-audit cycle, the consecutive-skip guard resets its counter AND enters a **90-minute cooldown**. Skip cycles within the cooldown do NOT count toward the next guard trigger. After cooldown expires, guard re-arms.
> This preserves the guard's intent (catch genuine loop stagnation) while preventing false-positive audits in same-morning dead zones.

**Applied cycle #203:** Guard reset. Next arm = 08:01 AM Tuesday (90min cooldown from 06:31 AM).

**Status:** ✅ CLOSED [INFERRED — validate at next dead-zone period if ping-pong reappears]

---

## Flag for Leo
- **Delete:** `提醒-SL-Weekly-Meeting` cron job (id: d70f2ffd-…) — disabled, past, error state
- **Monitor:** `ai-safety-radar-30min` — reassess after 1 week if generating signal
- **⭐ UNBLOCK REQUEST (PENDING since 02:01 AM):** See `memory/learning/unblock-request.md` — 15-20 min of Leo's time unlocks all experiments
- **📋 DAY-1 PLAN READY:** `memory/learning/2026-02-28_cycle88.md` — step-by-step session plan to start experiments immediately
- **🎨 Q10:** Audio SAE visualization gap — `sae_vis` = text only. Options + recommendation above. Quick decision needed for Paper B.
