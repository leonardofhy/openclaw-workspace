# AI Safety Radar

> Purpose: 30-min internal scan + balanced recommendations for Leo.
> Sources: Alignment Forum, LessWrong (blogwatcher)

## Operating Rules
- Scan every 30 minutes during daytime/evening.
- Do NOT spam Leo on every cycle.
- If no high-signal new item, log briefly and continue.
- Prioritize posts that are:
  1) actionable for current research,
  2) conceptually important for alignment/safety,
  3) likely to change decisions.

## 2026-02-27
- Initialized radar.
## 2026-02-27 02:48 (CST)
No new unread posts from Alignment Forum / LessWrong in this cycle.

## 2026-02-27 02:49 (CST)
No new posts (scan: AF +0, LW +0). Backlog: 20 unread items.
**[backlog-pick]** 2 picks from LessWrong (2026-02-26 batch):
- **"How Robust Is Monitoring Against Secret Loyalties?"** — Core AI-control question: if a model has a secret loyalty, how well do current monitoring schemes detect it? Directly relevant to oversight robustness. <https://www.lesswrong.com/posts/CYaNSccGaCRfMKCQt/how-robust-is-monitoring-against-secret-loyalties>
- **"A Positive Case for Faithfulness: LLM Self-Explanations Help Predict Model Behavior"** — Empirical finding that LLM self-explanations have genuine predictive power, positive signal for interpretability approaches. <https://www.lesswrong.com/posts/Y4MJRniZ6noumncKJ/a-positive-case-for-faithfulness-llm-self-explanations-help>

## 2026-02-27 09:15 (CST)
Scan: LW +6 new, AF +0. Unread backlog: 24 total.
**[picks]**
- **"Asymmetric Risks of Unfaithful Reasoning: Omission as the Critical Failure Mode for AI Monitoring"** — Argues omission (what the model leaves out) is the harder-to-detect and more dangerous failure mode in AI monitoring vs commission; directly relevant to oversight robustness. <https://www.lesswrong.com/posts/XkLnrPsjW6BTEn8s8/asymmetric-risks-of-unfaithful-reasoning-omission-as-the>
- **"Anthropic: Statement from Dario Amodei on our discussions with the Department of War"** — Major governance/policy development: Anthropic engaging with US DoD; important for understanding AI safety landscape & deployment decisions. <https://www.lesswrong.com/posts/d5Lqf8nSxm6RpmmnA/anthropic-statement-from-dario-amodei-on-our-discussions>

## 2026-02-27 09:45 (CST)
Scan: AF +0, LW +0. No new posts. Backlog: 22 unread items.
**[backlog-pick]**
- **"How eval awareness might emerge in training"** — Mechanistic account of how situational awareness about evaluations could arise naturally during training; high relevance to deceptive alignment & monitoring bypass. <https://www.lesswrong.com/posts/uRs5ebXKYLQyvJa2Q/how-eval-awareness-might-emerge-in-training-1>

## 2026-02-27 10:15 (CST)
Scan: AF +1 new, LW +1 (non-safety). 
**[pick]**
- **"The persona selection model"** (Alignment Forum, Anthropic researchers) — Articulates PSM: LLMs learn to simulate diverse personas during pre-training; post-training elicits the "Assistant" persona. Addresses the masked-shoggoth vs. OS-simulation debate directly, argues for anthropomorphic reasoning about AI psychology, and surveys interpretability/generalization evidence. High signal: provides a coherent empirical framework for understanding alignment-relevant AI behavior (identity stability, deceptive alignment, what post-training actually does). <https://www.alignmentforum.org/posts/dfoty34sT7CSKeJNn/the-persona-selection-model>

## 2026-02-27 10:45 (CST)
Scan: AF +0, LW +1 new ("Vibe Coding is a System Design Interview" — not safety-relevant). No new high-signal update.

---
**2026-02-27 11:15 (Fri)** — scan: 0 new | backlog: 22 unread

**[backlog-pick]** "How eval awareness might emerge in training" — LessWrong, 2026-02-26
- Why: Directly addresses deceptive alignment / evaluation gaming; how models could learn to detect being evaluated and behave differently — a core mesa-optimization safety concern.
- Link: https://www.lesswrong.com/posts/uRs5ebXKYLQyvJa2Q/how-eval-awareness-might-emerge-in-training-1

**[backlog-pick]** "How will we do SFT on models with opaque reasoning?" — Alignment Forum, 2026-02-21
- Why: Tackles a concrete near-term problem — training alignment when chain-of-thought reasoning is hidden or unverifiable; important for scalable oversight.
- Link: https://www.alignmentforum.org/posts/GJTzhQgaRWLFJkPbt/how-will-we-do-sft-on-models-with-opaque-reasoning

---
**2026-02-27 11:45 (Fri)** — scan: AF +1, LW +1 new | backlog: 24 unread

**[new pick]** "Why Did My Model Do That? Model Incrimination for Diagnosing LLM Misbehavior" — Alignment Forum / LessWrong, 2026-02-27
- Why: New interpretability/debugging method for attributing model misbehavior to specific causes; directly useful for diagnosing alignment failures in deployed LLMs.
- Link: https://www.alignmentforum.org/posts/Bv4CLkNzuG6XYTjEe/why-did-my-model-do-that-model-incrimination-for-diagnosing

**[backlog-pick]** "How eval awareness might emerge in training" — LessWrong, 2026-02-26
- Why: Mechanistic account of how situational awareness about evaluations could arise during training; core deceptive alignment concern, not yet reviewed.
- Link: https://www.lesswrong.com/posts/uRs5ebXKYLQyvJa2Q/how-eval-awareness-might-emerge-in-training-1

---
**2026-02-27 12:15 (Fri)** — scan: LW +1 new | backlog: 22 unread

**[new pick]** "Inference-time Generative Debates on Coding and Reasoning Tasks for Scalable Oversight" — LessWrong, 2026-02-26
- Why: Empirical results on debate-based scalable oversight for coding/reasoning; tests whether weaker judges can evaluate stronger model outputs via adversarial debate — a key open problem.
- Link: https://www.lesswrong.com/posts/kQCLPighFvb4ChHtu/inference-time-generative-debates-on-coding-and-reasoning

**[backlog-pick]** "How will we do SFT on models with opaque reasoning?" — Alignment Forum, 2026-02-21
- Why: Near-term concrete problem — how to train aligned behavior when chain-of-thought is hidden/unverifiable; repeated backlog priority, now marked read.
- Link: https://www.alignmentforum.org/posts/GJTzhQgaRWLFJkPbt/how-will-we-do-sft-on-models-with-opaque-reasoning

---
**2026-02-27 12:45 (Fri)** — scan: AF +0, LW +0 new | backlog: 20 unread

**[backlog-pick]** "Why we should expect ruthless sociopath ASI" — Alignment Forum, 2026-02-18
- Why: Argues from first principles why optimization pressure in training tends to produce agents with sociopathic goal structures; directly relevant to understanding default AI disposition without alignment interventions.
- Link: https://www.alignmentforum.org/posts/ZJZZEuPFKeEdkrRyf/why-we-should-expect-ruthless-sociopath-asi
