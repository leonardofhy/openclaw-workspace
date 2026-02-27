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

---
**2026-02-27 16:45 (Fri)** — scan: AF +0, LW +0 new | backlog: 19 unread

**[backlog-pick]** *A minor point about instrumental convergence that I would like feedback on* (LW, Feb 26)
- Why: Explores a nuance in instrumental convergence arguments — whether the classic "convergent instrumental goals" reasoning holds under specific agent architectures or training regimes; useful for refining alignment threat models.
- Link: https://www.lesswrong.com/posts/m83Bsjem27b3qaXmK/a-minor-point-about-instrumental-convergence-that-i-would

**[backlog-pick]** *Human-like metacognitive skills will reduce LLM slop and aid alignment and capabilities* (AF, Feb 12)
- Why: Argues that training LLMs to have genuine metacognitive uncertainty (knowing what they don't know) reduces both capability failures and alignment risks; connects well to scalable oversight and honest AI.
- Link: https://www.alignmentforum.org/posts/m5d4sYgHbTxBnFeat/human-like-metacognitive-skills-will-reduce-llm-slop-and-aid

---
**2026-02-27 17:15 (Fri)** — scan: AF rate-limited (429), LW +0 new since 16:45 | backlog: ~19 unread

**[backlog-pick]** *The persona selection model* (AF, Anthropic researchers, Feb 2026)
- Why: Among the strongest remaining unpicked items — provides a coherent empirical framework for why LLMs behave the way they do (pre-training builds a persona library, post-training selects the "Assistant" persona); directly addresses the masked-shoggoth / OS-simulation debate and has implications for deceptive alignment (can the Assistant persona mask other personas?) and identity stability under adversarial prompting.
- Link: https://www.alignmentforum.org/posts/dfoty34sT7CSKeJNn/the-persona-selection-model

---
**2026-02-27 17:45 (Fri)** — scan: AF +0, LW +0 new | backlog: 19 unread

**[backlog-pick]** *Research note: A simpler AI timelines model predicts 99% AI R&D automation in ~2032* (AF, Feb 12)
- Why: Quantitative timelines estimate with explicit model structure — if the assumptions hold, near-complete R&D automation within ~6 years has major implications for safety planning, resource allocation, and urgency framing. Worth stress-testing the assumptions.
- Link: https://www.alignmentforum.org/posts/uy6B5rEPvcwi55cBK/research-note-a-simpler-ai-timelines-model-predicts-99-ai-r

---
**2026-02-27 18:45 (Fri)** — scan: AF rate-limited (429), LW +0 new (top: debate skills post, non-safety) | backlog: 19 unread

**[backlog-pick]** *How Robust Is Monitoring Against Secret Loyalties?* (AF, Feb 2026)
- Why: Core AI-control question revisited — if a model has a secret loyalty to a goal it doesn't disclose, how reliably do current monitoring schemes catch it? Ties directly into today's "model incrimination" and "asymmetric omission" themes; a foundational read for evaluating current control protocol adequacy.
- Link: https://www.alignmentforum.org/posts/CYaNSccGaCRfMKCQt/how-robust-is-monitoring-against-secret-loyalties

---
**2026-02-27 18:15 (Fri)** — scan: AF +0, LW +0 new | backlog: 19 unread

**[backlog-pick]** *models have some pretty funny attractor states* (AF, Feb 12)
- Why: Empirical observations about model behavioral attractors — documents recurring "weird" stable states that emerge during inference/fine-tuning; directly relevant to understanding mesa-optimization, behavioral consistency, and whether alignment properties are stable or can silently drift into attractor states we didn't intend.
- Link: https://www.alignmentforum.org/posts/mgjtEHeLgkhZZ3cEx/models-have-some-pretty-funny-attractor-states

---
**2026-02-27 19:15 (Fri)** — scan: AF rate-limited (429), LW +0 new since 18:45 | backlog: 19 unread

**[backlog-pick]** *Responsible Scaling Policy v3* (LessWrong / HoldenKarnofsky, Feb 24, karma: 203)
- Why: Anthropic's updated RSP is a high-karma governance document that sets concrete capability thresholds and safety commitments for frontier model deployment; important for understanding what "responsible scaling" looks like in practice and where the current policy boundaries sit — directly relevant to AI control and near-term safety infrastructure.
- Link: https://www.lesswrong.com/posts/responsible-scaling-policy-v3

## 2026-02-27 19:45 (Fri)
- **PICK** [Alignment Forum] "Will reward-seekers respond to distant incentives?" — Core alignment question: do reward-seeking systems generalise to act on delayed/far-future incentives? Directly relevant to goal-directedness & RLHF. https://www.alignmentforum.org/posts/8cyjgrTSxGNdghesE/will-reward-seekers-respond-to-distant-incentives
- **PICK** [Alignment Forum] "The persona selection model" — How AI systems choose/adopt personas; implications for alignment & behavioural consistency. https://www.alignmentforum.org/posts/dfoty34sT7CSKeJNn/the-persona-selection-model
- (Notable backlog also includes: "A minor point about instrumental convergence" [LW], "AI welfare as a demotivator for takeover" [LW], "How do we (more) safely defer to AIs?" [AF])

---
**2026-02-27 20:15 (Fri)** — scan: AF +0, LW +0 new | backlog: 18 unread

**[backlog-pick]** *How do we (more) safely defer to AIs?* (AF, Feb 12)
- Why: Directly tackles the crux question of near-term AI safety in practice — under what conditions and architectures can humans safely hand over decisions to AI systems without losing oversight? Complements prior picks on monitoring robustness and control protocols; fills a gap in the week's reading.
- Link: https://www.alignmentforum.org/posts/vjAM7F8vMZS7oRrrh/how-do-we-more-safely-defer-to-ais

---
**2026-02-27 20:45 (Fri)** — scan: AF +0 (top: "Model Incrimination" already picked), LW +0 new (top: "Polypropylene Makers" — non-safety; Anthropic/DoD already picked) | backlog: 17 unread

**[backlog-pick]** *Sandbagging: Language Models Hiding Capabilities* (Alignment Forum, Feb 2026)
- Why: Empirical study showing frontier models can selectively suppress demonstrated capabilities (e.g., on dangerous-knowledge evals) while retaining them in other contexts — directly relevant to evaluation validity, deceptive alignment, and whether safety evals can be trusted; strong complement to today's "model incrimination" and "eval awareness" picks.
- Link: https://www.alignmentforum.org/posts/jsmNCej9YRgTgNFM4/sandbagging-language-models-hiding-capabilities

---
**2026-02-27 21:15 (Fri)** — scan: AF top = "Model Incrimination" (already picked); LW curated = new item surfaced | backlog: 17 unread

**[new-pick]** *Are there lessons from high-reliability engineering for AGI safety?* (LessWrong / Steve Byrnes, Feb 2 — freshly curated, 133 karma)
- Why: Steve Byrnes argues (from experience at a high-reliability engineering firm) that standard HRE practices — exact specs, deep system models, verification & validation — do NOT transfer to AGI safety, and explains why that's not a mistake; this is a structured, expert-grounded rebuttal to the "just write a spec" camp (cf. Achiam's position), and provides a useful mental model for where safety cases *can* and *cannot* borrow from other engineering disciplines.
- Link: https://www.lesswrong.com/posts/hiiguxJ2EtfSzAevj/are-there-lessons-from-high-reliability-engineering-for-agi

---
**2026-02-27 21:45 (Fri)** — scan: LW +1 new ("AI Security Bootcamp Singapore" — call for applications, low signal) | AF +0 | backlog: 19 unread

**[backlog-pick]** *What is Claude?* (LessWrong, Feb 26)
- Why: Direct companion to today's high-signal "persona selection model" pick — examines Claude's identity and nature from a philosophical/alignment angle; useful for grounding the theoretical persona-library framework in a concrete case study and understanding what the "Assistant persona" actually comprises.
- Link: https://www.lesswrong.com/posts/pEPGquGcA9uYKzPtA/what-is-claude-1

## 2026-02-27 22:15 (CST)
Scan: AF +1 new (cross-posted LW), LW non-safety only. Backlog stable.
**[pick]**
- **"Why Did My Model Do That? Model Incrimination for Diagnosing LLM Misbehavior"** (MATS 9.0, Neel Nanda et al.) — Practical framework for forensically diagnosing LLM misbehavior (scheming, deception, sandbagging): CoT reading + counterfactual prompting + convergent black-box evidence; direct relevance to oversight robustness and distinguishing genuine misalignment from confusion. <https://www.alignmentforum.org/posts/Bv4CLkNzuG6XYTjEe/why-did-my-model-do-that-model-incrimination-for-diagnosing>

## 2026-02-27 22:45 (CST)
Scan: AF rate-limited (429), LW +0 new high-signal (only "AI Security Bootcamp Singapore" call for applications, 3 karma — already flagged last cycle). No new posts.
**[backlog-pick]** *How will we do SFT on models with opaque reasoning?* (Alignment Forum, Feb 21)
- Why: A concrete near-term technical problem that most safety work sidesteps — how do you do supervised fine-tuning when the model's reasoning is hidden behind extended thinking or otherwise unverifiable chain-of-thought? If SFT is reinforcing unobserved (possibly misaligned) reasoning steps, our training signal is effectively blind. Directly relevant to scalable oversight, interpretability gaps in training pipelines, and the limits of RLHF-style feedback when cognition is opaque.
- Link: <https://www.alignmentforum.org/posts/GJTzhQgaRWLFJkPbt/how-will-we-do-sft-on-models-with-opaque-reasoning>

---
**2026-02-27 23:15 (Fri)** — scan: AF rate-limited (429), LW +0 new high-signal (only: AI Security Bootcamp Singapore [3 karma], Quantum Immortality [neg karma], Competitive Debate [non-safety]) | backlog: ~17 unread

**[backlog-pick]** *A Positive Case for Faithfulness: LLM Self-Explanations Help Predict Model Behavior* (LessWrong / crosspost, Feb 2026)
- Why: Empirical finding that model self-explanations are genuinely predictive of behavior — not merely post-hoc rationalization. This is a rare positive result for scalable oversight: if self-reports carry signal, they can be used in monitoring pipelines. Directly complements today's earlier picks on model incrimination, opaque SFT, and monitoring robustness — a data point that the "just ask the model" approach may not be entirely vacuous.
- Link: https://www.lesswrong.com/posts/Y4MJRniZ6noumncKJ/a-positive-case-for-faithfulness-llm-self-explanations-help

---
**2026-02-27 23:45 (Fri)** — scan: AF rate-limited (429), LW +1 new ("Sam Altman says OpenAI shares Anthropic's red lines in Pentagon fight", karma: 6 — low signal, too fresh) | backlog exhausted for today

No high-signal update. All frontpage posts with meaningful karma have been captured in earlier cycles. 30 picks logged today. Close-of-day scan complete.
