# Blocked Mode Playbook

When GPU/human approval blocks your primary experiments, **don't skip — do Tier 0 work.**

## Stage 1: Fallback tasks (converge-compatible)

Priority order when blocked:
1. **CPU-only eval harness** — build the scaffold so GPU runs become one-liners later
2. **Paper reads from queue** — only Tier 0/1 priority, only if learn budget remains
3. **Experiment configs + expected outcomes** — write what you'd run and what you expect
4. **Related-work comparison grid** — preempt reviewer objections
5. **Ablation plan** — "what would falsify this hypothesis?"
6. **Paper sections** — method sketch, related work draft
7. **Write the rebuttal before the experiment** — forces clarity on claims

## Stage 2: Explore-fallback (when fallback tasks exhausted)

When ALL tracks blocked AND fallback tasks exhausted → **phase regression to explore mode**.

This is NOT a failure state. Blocked converge = opportunity to explore.

**What to do in explore-fallback:**
1. **Ideate** — cross-pollinate ideas across domains, generate new research directions
2. **Scan trends** — arXiv trending topics, HN, conference proceedings
3. **Adjacent reads** — papers in related areas (multimodal interp, audio safety, speech × cognitive science)
4. **Ask Leo** — proactively ask for new interests or directions (via mailbox/Discord)
5. **Low-hanging fruit** — prioritize ideas that are novel AND tractable with current resources

**Explore-fallback quotas**: learn=8, build=2, reflect=2, ideate=4 (discovery-oriented)

**Self-replenishing queue**: Ideate cycles generate new tasks → queue stays populated → no more "exhausted" state.

**Explore-fallback exits when**:
- A blocked track gets unblocked (resume converge)
- A new explore-fallback discovery matures into its own converge track
- Leo redirects

## Anti-patterns (never do when blocked)

- ~~Stopping entirely because fallback is exhausted~~ → use explore-fallback instead
- Checking if you're still blocked (use cooldown timer)
- Opening meta-awareness questions
- Reflecting on being blocked (it's not productive)
- Creating new state files or processes without Leo approval

## When to escalate

If blocked >48h AND fallback tasks exhausted:
1. Write a brief unblock request (what's needed, estimated Leo time)
2. Update blockers.json with new unblock_check_at
3. Activate explore-fallback mode (automatic in v2)
