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

---
**2026-02-27 13:15 (Fri)** — scan: AF rate-limited (429), LW +0 new since 12:45 | backlog: 20 unread

**[backlog-pick]** "Frontier AI companies probably can't leave the US" — LessWrong / Redwood Research, 2026-02-26 (karma: 99)
- Why: Analyses structural reasons (compute, talent, regulation, capital) why frontier labs can't credibly relocate; important for understanding the AI governance landscape and what policy levers actually constrain lab behavior.
- Link: https://blog.redwoodresearch.org/p/frontier-ai-companies-probably-cant (via LW: /posts/frontier-ai-companies-probably-can-t-leave-the-us)

---
**2026-02-27 13:45 (Fri)** — scan: AF +0 new (already seen top item), LW curated +1 new | backlog: 20 unread

**[new pick]** "Are there lessons from high-reliability engineering for AGI safety?" — LessWrong, 2026-02-27
- Why: Author (full-time AGI safety researcher, ex-engineering R&D) carefully argues *why* standard HRE practices (spec-writing, V&V, component models) don't transfer to AGI safety, while identifying what kernel of truth remains; directly relevant to methodology debates in alignment. Thoughtful steel-man of the "just use engineering best practices" camp + rebuttal.
- Link: https://www.lesswrong.com/posts/HQTueNS4mLaGy3BBL/are-there-lessons-from-high-reliability-engineering-for-agi

---
**2026-02-27 14:15 (Fri)** — scan: AF +0, LW +1 new (non-safety: debate skills post) | backlog: 21 unread

**[backlog-pick]** "How do we (more) safely defer to AIs?" — Alignment Forum, 2026-02-12
- Why: Directly tackles corrigibility in practice — under what conditions is deferring to AI decisions actually safe, and how do we structure that safely? Core oversight/control question as autonomy increases.
- Link: https://www.alignmentforum.org/posts/vjAM7F8vMZS7oRrrh/how-do-we-more-safely-defer-to-ais

---
**2026-02-27 14:45 (Fri)** — scan: AF rate-limited (429), LW +0 new since 14:15 | backlog: ~20 unread

**[backlog-pick]** "Eliciting Latent Knowledge: Challenges and Approaches" — Alignment Forum (ARC), ongoing series
- Why: ELK remains a foundational unsolved problem — how to get a model to report its actual beliefs rather than what it thinks the reporter wants to hear; directly relevant given today's picks on self-explanation faithfulness and monitoring robustness. Good complement to the "persona selection model" framing from earlier today.
- Link: https://www.alignmentforum.org/tag/eliciting-latent-knowledge-elk

## 2026-02-27 15:15 (Asia/Taipei)
No new posts this cycle (scan: AF 0 new, LW 0 new). Backlog: 21 unread. Picked 2 backlog items:

- **[backlog-pick]** *Why we should expect ruthless sociopath ASI* (AF, Feb 18) — argues training dynamics systematically select for power-seeking dispositions; directly relevant to alignment failure modes. https://www.alignmentforum.org/posts/ZJZZEuPFKeEdkrRyf/why-we-should-expect-ruthless-sociopath-asi
- **[backlog-pick]** *A Conceptual Framework for Exploration Hacking* (AF, Feb 12) — formalizes how an agent could manipulate its own exploration to evade oversight; important for understanding deceptive alignment. https://www.alignmentforum.org/posts/suRWiTNnazrRsoBKR/a-conceptual-framework-for-exploration-hacking

---
**2026-02-27 15:45 (Fri)** — scan: AF +0, LW +0 new | backlog: 19 unread

**[backlog-pick]** *Will reward-seekers respond to distant incentives?* (AF, Feb 16)
- Why: Directly bears on goal stability / mesa-optimization: whether reward-seeking agents discount far-future incentives (including safety-relevant ones); crucial for understanding if AI systems might ignore long-horizon alignment properties even when aligned on proximate objectives.
- Link: https://www.alignmentforum.org/posts/8cyjgrTSxGNdghesE/will-reward-seekers-respond-to-distant-incentives

**[backlog-pick]** *AI welfare as a demotivator for takeover* (LW, Feb 26)
- Why: Novel argument that AI moral patienthood / welfare considerations could create endogenous disincentives against power-seeking and takeover — a potentially underexplored alignment lever that reframes AI welfare not just as a concern but as a possible safety mechanism.
- Link: https://www.lesswrong.com/posts/gYE7DnExWWJmCwvhf/ai-welfare-as-a-demotivator-for-takeover

---
**2026-02-27 16:15 (Fri)** — scan: AF +0, LW +0 new | backlog: ~19 unread

**[backlog-pick]** *How do we (more) safely defer to AIs?* (AF, Feb 12)
- Why: Directly addresses the corrigibility/deference tension — when and how humans should trust AI judgment without creating unsafe lock-in; highly relevant as frontier models gain more autonomy in agentic settings.
- Link: https://www.alignmentforum.org/posts/vjAM7F8vMZS7oRrrh/how-do-we-more-safely-defer-to-ais
