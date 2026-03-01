# Blocked Mode Playbook

When GPU/human approval blocks your primary experiments, **don't skip — do Tier 0 work.**

## Priority order (when blocked)

1. **CPU-only eval harness** — build the scaffold so GPU runs become one-liners later
2. **Paper reads from queue** — only Tier 0/1 priority, only if learn budget remains
3. **Experiment configs + expected outcomes** — write what you'd run and what you expect
4. **Related-work comparison grid** — preempt reviewer objections
5. **Ablation plan** — "what would falsify this hypothesis?"
6. **Paper sections** — method sketch, related work draft
7. **Write the rebuttal before the experiment** — forces clarity on claims

## Anti-patterns (never do when blocked)

- Checking if you're still blocked (use cooldown timer)
- Opening meta-awareness questions
- Reflecting on being blocked (it's not productive)
- Random arXiv browsing unrelated to queue tasks
- Creating new state files or processes

## When to escalate

If blocked >48h AND fallback tasks exhausted:
1. Write a brief unblock request (what's needed, estimated Leo time)
2. Update blockers.json with new unblock_check_at
3. Continue with lowest-priority fallback tasks
