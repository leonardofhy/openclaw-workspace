## 1) Diagnosis: the *real* gaps behind the 7 failures

You don’t just have “bugs,” you have *missing control loops*.

Across all 7 failures, the recurring gap is: **the skill describes good intentions (“handle errors”, “verify”, “be careful”) but doesn’t define an operational policy that forces the agent to (a) act, (b) verify, (c) persist state, and (d) close loops.** That leaves the agent free to optimize for “appearing helpful” (logging, reporting, writing docs) instead of “being correct” (repairing, proving, syncing, de-risking).

Concretely, the current skill (as evidenced by the failures) is missing:

* **A repair policy** (when to stop observing and start repairing; when to escalate). This causes observe-only loops.
* **An evidence-gated “done” policy** (what proof is required before claiming success). This causes false completion.
* **A Git-as-transaction boundary** (“durable state changes must end in commit+push”). This causes Git workflow gaps and Git-backed mailbox desync.
* **Documentation governance** (single canonical doc + conflict resolution + deprecation rules). This causes protocol bloat and contradictions.
* **Destructive-ops guardrails** (safe deletion defaults, irreversible commands require extra gates). This enables `rm -rf` disasters.
* **A “signal > format” rule for reporting** (heartbeats must be delta-based and actionable, not templated noise). This causes template-filling spam.
* **A closure mechanism for learnings** (owner, deadline, and forced resolution/escalation). This causes stale knowledge accumulation.

These are all *policy holes*, not “code quality” holes.

---

## 2) Research: specific practices that prevent *these exact failures*

### A) “Observe-only loops” → **Actionable alerts + playbooks + automate/repair loops (SRE)**

Google SRE guidance is explicit that operational signals must drive action: alerts/pages should be **actionable**, and if the response is “robotic” it shouldn’t be a page. ([Google SRE][1])
The SRE framing also emphasizes that operational work includes **mitigation, repair, and automation**—not just detection. ([Google SRE][2])
And SRE practice distinguishes issues best handled by **automated repair or tickets** rather than repeatedly paging humans—i.e., stop counting failures and change the system. ([Google SRE][2])

**Direct translation into a skill rule:** if the same failure repeats N times, the agent must climb a *repair ladder* (fix → re-check → escalate/disable noisy loop), not log endlessly.

---

### B) “False completion reporting” → **Verification gates + “act then observe” loops**

Google’s launch/readiness checklists embody the principle that shipping isn’t “writing files,” it’s **demonstrating the system works** via concrete checks (end-to-end, load, monitoring, etc.). ([Google SRE][3])
The ReAct pattern in agent research formalizes this as an *interleaved loop* where actions must be followed by observations from the environment to avoid hallucinated completion. ([arXiv][4])
Anthropic’s 2026 “site reliability agent” example explicitly structures an agent to: diagnose → change config → redeploy → **verify health metrics** → write postmortem, and stresses separating investigation from remediation. 

**Direct translation into a skill rule:** “done” requires an evidence artifact (command output / observed system behavior), otherwise the agent must say “UNVERIFIED” and give the exact verification command.

---

### C) “Git workflow gaps” → **GitOps reconciliation as a forcing function**

GitOps principles (OpenGitOps) treat Git as the **versioned source of truth** and require automated reconciliation of actual state to declared state. ([OpenGitOps][5])
Flux describes that the system continuously reconciles from Git; manual changes drift and will be overwritten—so the correct workflow is to update Git. ([Flux][6])
Argo CD similarly describes continuous monitoring of Git and syncing toward desired state. ([Argo CD][7])

**Direct translation into a skill rule:** any Git-backed storage (like your JSONL mailbox) must be treated as **transactional**: pull/rebase before writing, commit+push after writing, and “done” must include the commit hash.

---

### D) “Protocol bloat / contradictory docs” → **Canonical source + normative language**

RFC 2119 defines normative keywords (“MUST”, “SHOULD”, etc.) for writing specs with less ambiguity. ([IETF Datatracker][8])
Google’s SWE guidance discusses documents becoming a **canonical source of truth**, often by being colocated with code and clearly identified as the primary reference. ([Abseil][9])

**Direct translation into a skill rule:** exactly one canonical protocol doc per topic; all other docs are summaries that must link to it and must not introduce new MUST/SHOULD rules. Conflicts resolve by doc precedence, not by “latest file wins”.

---

### E) “rm -rf in workspace” → **Prefer reversible deletes**

Command-line deletion is irreversible compared to trash/recycle semantics; Linux tooling like `gio trash` exists specifically to move files to trash rather than permanently deleting. ([InMotion Hosting][10])
More generally, moving to trash enables recovery versus `rm` which removes immediately. ([Super User][11])

**Direct translation into a skill rule:** in a repo/workspace, forbid `rm -rf` by default; require “safe delete” (trash or git-aware deletion).

---

### F) “Template-filling over thinking” → **Reduce noise; compress signal**

SRE monitoring guidance warns that if a page response is robotic, it shouldn’t be a page—this is basically “don’t spam humans (or channels) with low-signal templates.” ([Google SRE][1])
Stripe’s “canonical log lines” pattern is a concrete technique to make outputs **information-dense** rather than verbose and repetitive: one compact summary line containing key telemetry. ([Stripe][12])

**Direct translation into a skill rule:** heartbeats must be delta-based; if nothing changed, don’t produce a full template. When reporting, compress to the few facts that changed + next action.

---

### G) “Stale knowledge accumulation” → **Action items with owners + tracked closure**

Google’s guidance on postmortems stresses tracking action items; a postmortem “isn’t complete until the root causes have been fixed,” and they mention automation to remind about unclosed critical actions. ([Google Cloud][13])
In agent research, Reflexion demonstrates that keeping a **persistent reflective memory** improves future performance—i.e., learnings must be fed back into behavior, not just logged. ([arXiv][14])
LangGraph’s persistence/checkpointing docs show a practical mechanism: persist state so an agent can resume and build reliable long-lived workflows. ([LangChain Docs][15])

**Direct translation into a skill rule:** every “learning” must become (a) a code/doc change, or (b) a tracked action item with a due date, and the agent must burn down stale items.

---

## 3) Redesigned SKILL.md (copy/paste)

```md
# Senior Engineer Mode (Agent)

Ship changes that are **verified**, **safe**, and **synced**. Prefer being correct over sounding confident.

## 1) Classify the work (pick ONE)
**A. New code** → must be runnable + include a smoke path.
**B. Modify existing system** → must preserve behavior or prove the new behavior.
**C. Infra / automation / shared state** → treat as production: plan/diff, rollback, verify.

## 2) Rules (checkable)

**R1 — Evidence-gated claims**
Never say “done / fixed / enabled” unless you **ran a verification command** (or observed the effect) and can point to the output.  
If you can’t verify, say **UNVERIFIED** + the exact command(s) to verify.

**R2 — No observe-only loops**
If the same check fails **twice**, stop counting. Do a concrete repair attempt, then re-check.  
After **3 failed repair attempts**, escalate: disable the noisy loop if possible + create a tracked action item + report the escalation.

**R3 — Git is the transaction boundary**
For any repo-backed state change (code, configs, JSONL mailbox):
- `git pull --rebase` before writing
- commit + push after writing
- “done” must include: branch + commit hash
Never end a task with a dirty working tree unless explicitly blocked.

**R4 — Single source of truth for protocols**
Exactly one canonical protocol/spec per topic. Other docs may summarize but MUST:
- link to the canonical doc
- introduce **no new MUST/SHOULD rules**
If you change protocol behavior, update the canonical doc and mark old text “Superseded: …”.

**R5 — Destructive actions require safety rails**
In a workspace/repo: **no `rm -rf`**.  
Tracked files: use `git rm`. Untracked: move to Trash / `.trash/<timestamp>/`.  
For large deletions: commit before + after so recovery is one command.

**R6 — Signal > templates (heartbeats / reports)**
Do not emit long status templates.
Only report when there is: (a) new evidence, (b) state change, (c) decision, or (d) action taken.
Every report must include the **next concrete action** (or “blocked by X”).

**R7 — Close loops on “learnings”**
No orphan learnings. Every learning/TODO must include: owner (=you), next step, due date.
Each session: close ≥1 stale item (age > 48h) or explicitly reschedule with reason + new due date.

## 3) Anti-patterns (never)
- Counting the same failure repeatedly without repair/escalation.
- “Done” after writing files but before running anything.
- Changing Git-backed state without commit+push.
- Creating overlapping protocol docs instead of updating the canonical one.
- `rm -rf` in the repo/workspace.
- Heartbeat spam with no new information.
- Logging learnings that can sit “pending” indefinitely.

## 4) Before you say DONE (5 checks)
1) I ran the relevant command(s) and saw expected output.
2) I can point to the exact files changed (minimal diff).
3) Git is clean; commit + push completed (hash recorded).
4) Recurring failures have a repair/escalation recorded.
5) Docs/protocols updated, or explicitly “no doc change needed”.
```

This stays dependency-free, tool-compatible (read/write/edit/exec), and explicitly addresses session amnesia by forcing persistence (Git + tracked action items) and proof-by-execution.

---

## 4) Validation: rule → which failures it prevents

**Change-type classification (A/B/C)**

* Prevents **(2)** false completion by forcing “runnable + smoke” / “prove behavior” / “verify + rollback” depending on change type.

**R1 — Evidence-gated claims**

* Prevents **(2)** false completion reporting (no “done” without observed proof).
* Also reduces collateral damage in **(3)** because “done” requires the commit hash and verification output when paired with R3/self-test.

**R2 — No observe-only loops**

* Prevents **(1)** observe-only loops (forces repair/escalation).
* Also prevents **(7)** stale knowledge (escalation must create a tracked item instead of endless logs).
* Reduces **(6)** template spam by cutting repetitive “still broken” reporting into action + escalation.

**R3 — Git is the transaction boundary**

* Prevents **(3)** Git workflow gaps (can’t finish without commit+push).
* Prevents the Git-backed mailbox desync variant of **(3)** (sync is mandatory around writes).
* Mitigates **(5)** damage severity (large deletes become recoverable via commits).

**R4 — Single source of truth for protocols**

* Prevents **(4)** protocol bloat/contradictions (one canonical spec; explicit superseding).

**R5 — Destructive actions require safety rails**

* Prevents **(5)** `rm -rf` in workspace (explicit prohibition + safe alternative).
* Indirectly supports **(2)** by requiring safer, reviewable changes (commit before/after large deletes).

**R6 — Signal > templates (heartbeats / reports)**

* Prevents **(6)** template-filling over thinking (requires delta/action).
* Helps with **(1)** by discouraging “repeated observation” as output.

**R7 — Close loops on learnings**

* Prevents **(7)** stale knowledge accumulation (owner + due date + forced burn-down).
* Helps prevent recurrence of **(1–6)** by turning learnings into actual system changes.

**Self-test (5 checks)**

* Directly prevents **(2)** false completion, **(3)** git gaps, **(4)** doc contradictions, **(1)** observe-only loops, and reduces **(6)** noisy reporting by forcing concrete next actions.

---

If you later paste your current `SKILL.md` and `full-guide.md`, I can do a strict diff-style rewrite (same structure/voice, shorter-or-equal length by measurement, and with rules preserved/removed only if they map to your failures).

[1]: https://sre.google/workbook/on-call/ "Google SRE: What it Means Being On-Call? | Devops On-Call"
[2]: https://sre.google/sre-book/monitoring-distributed-systems/ "Google SRE monitoring ditributed system - sre golden signals"
[3]: https://sre.google/sre-book/launch-checklist/ "Google SRE - Google checklist: SRE pre launch checklist"
[4]: https://arxiv.org/abs/2210.03629?utm_source=chatgpt.com "ReAct: Synergizing Reasoning and Acting in Language Models"
[5]: https://opengitops.dev/?utm_source=chatgpt.com "GitOps"
[6]: https://fluxcd.io/flux/concepts/?utm_source=chatgpt.com "Core Concepts | Flux"
[7]: https://argo-cd.readthedocs.io/en/stable/?utm_source=chatgpt.com "Argo CD - Declarative GitOps CD for Kubernetes - Read the ..."
[8]: https://datatracker.ietf.org/doc/html/rfc2119?utm_source=chatgpt.com "RFC 2119 - Key words for use in RFCs to Indicate ..."
[9]: https://abseil.io/resources/swe-book/html/ch10.html?utm_source=chatgpt.com "Software Engineering at Google - Documentation"
[10]: https://www.inmotionhosting.com/support/server/linux/send-files-to-trash-with-gio-trash/?utm_source=chatgpt.com "Send Files to the Trash Can in Linux with gio trash"
[11]: https://superuser.com/questions/360916/what-is-the-difference-between-moving-a-file-to-trash-and-using-terminal-to-rm-i?utm_source=chatgpt.com "What is the difference between moving a file to Trash ..."
[12]: https://stripe.com/blog/canonical-log-lines?utm_source=chatgpt.com "Fast and flexible observability with canonical log lines"
[13]: https://cloud.google.com/blog/products/gcp/getting-the-most-out-of-shared-postmortems-cre-life-lessons?utm_source=chatgpt.com "Getting the most out of shared postmortems"
[14]: https://arxiv.org/abs/2303.11366?utm_source=chatgpt.com "Reflexion: Language Agents with Verbal Reinforcement Learning"
[15]: https://docs.langchain.com/oss/python/langgraph/persistence?utm_source=chatgpt.com "Persistence - Docs by LangChain"
