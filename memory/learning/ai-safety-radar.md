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

---
**2026-02-28 09:15 (Sat)** — scan: AF rate-limited (429), LW +2 new since yesterday (Feb 28 00:36+) | backlog: ~17 unread

**[new pick]** *Anthropic and the DoW: Anthropic Responds* (Zvi, LessWrong, Feb 27 20:50, karma: 41)
- Why: Zvi's breakdown of the live Anthropic/DoD standoff — DoD gave Anthropic a 5pm-Friday ultimatum for "unfettered access" or face DPA invocation / supply chain risk designation; Zvi assesses the governance dynamics and what Anthropic's response reveals about where AI safety red lines meet national security pressure. Direct follow-up to Dario's statement (already picked); important for understanding how safety commitments hold under coercive government pressure.
- Link: https://www.lesswrong.com/posts/ppj7v4sSCbJjLye3D/anthropic-and-the-dow-anthropic-responds

**[new — low karma, noted]** *The Topology of LLM Behavior* (LW, Feb 28, karma: 11)
- Why: Informal mental model framing LLM generation as a weighted random walk through a semantic attractor landscape — alignment constraints as attractors; low-karma but potentially useful intuition for thinking about behavioral stability and drift. Watch karma.
- Link: https://www.lesswrong.com/posts/iPmqM4qn7YnktcSus/the-topology-of-llm-behavior-1

---
**2026-02-28 09:45 (Sat)** — scan: LW new since 09:15; AF rate-limited (429)

**[new picks]**
- **"Sam Altman says OpenAI shares Anthropic's red lines in Pentagon fight"** (LW, Feb 27, karma: 74 ↑ from ~6 overnight) — karma surge signals community weight; reports OpenAI and Anthropic aligned on refusing DoD "unfettered access" demands, a concrete governance moment: two leading labs holding the same safety red line under DPA pressure. Direct follow-up to Dario's statement + Zvi's breakdown (both previously picked). <https://www.lesswrong.com/posts/sam-altman-says-openai-shares-anthropic-s-red-lines-in>
- **"New ARENA material: 8 exercise sets on alignment science & interpretability"** (LW / Callum McDougall, Feb 27, karma: 46) — ARENA published 8 new problem sets covering alignment science + interpretability; high practical value for anyone building technical alignment skills or evaluating the current training-ground state of the field. <https://www.lesswrong.com/posts/new-arena-material-8-exercise-sets-on-alignment-science-and>

---
**2026-02-28 10:15 (Sat)** — scan: AF rate-limited (429), LW +3 new since 09:45 (all low-karma: Mindscapes/Mind Palaces [1], Coherent Care/abramdemski [15], RSP Versions [7]) | no new high-signal posts

**[backlog-pick]** *Side by Side Comparison of RSP Versions* (LessWrong / Corm, Feb 27, karma: 7)
- Why: Direct comparison of how Responsible Scaling Policy versions have evolved; useful for tracking concrete safety commitment drift over time and understanding which thresholds/trigger conditions have changed across labs — relevant to governance and accountability tracking, especially amid the current Anthropic/DoD red-lines standoff.
- Link: <https://www.lesswrong.com/posts/side-by-side-comparison-of-rsp-versions>

---
**2026-02-28 10:45 (Sat)** — scan: AF rate-limited (429), LW no new posts since 10:15 (most recent: Mindscapes/Mind Palaces 01:04 UTC, karma: 1 — non-safety). All high-signal items from today already picked.

No high-signal update.

---
**2026-02-28 11:15 (Sat)** — scan: AF rate-limited (429), LW 0 new posts since 10:45 (confirmed via API after 02:45 UTC). All high-signal items for today already picked.

No high-signal update.

---
**2026-02-28 11:45 (Sat)** — scan: AF rate-limited (429), LW 0 new posts since 03:15 UTC | backlog: ~17 unread

**[backlog-pick]** *Coherent Care* (abramdemski, LessWrong, Feb 27, karma: 18)
- Why: abramdemski (MIRI / decision theory) on "coherent care" — likely concerns what it means for an agent to have consistent, well-formed preferences / values that constitute genuine caring rather than proxy optimization; directly relevant to goal-structure alignment and the difference between satisfying human preferences and an AI that actually *cares* about good outcomes. Steady karma growth signals community endorsement.
- Link: https://www.lesswrong.com/posts/coherent-care (title-based; confirm URL on read)

**[watching]** *The Topology of LLM Behavior* (LW, Feb 28) — karma grew to 17 (from 11 at 09:15); still worth monitoring before reading.

---
**2026-02-28 12:15 (Sat)** — scan: AF rate-limited (429), LW +0 new safety-relevant posts since 03:15 UTC (only new: "Jhana 0" [meditation, karma: 2], "Mindscapes and Mind Palaces" [karma: 1]) | backlog: ~16 unread

No high-signal update. *The Topology of LLM Behavior* still at karma 17 (unchanged since 09:15); holding in watch queue pending karma growth before committing a read slot.

---
**2026-02-28 12:45 (Sat)** — scan: AF rate-limited (429), LW +1 new since 04:15 UTC ("Schelling Goodness, and Shared Morality as a Goal", karma: 9, Rationality tag — not safety-core, too early to commit) | backlog: ~16 unread

**[backlog-picks]**
- **"3 Challenges and 2 Hopes for the Safety of Unsupervised Elicitation"** (LW, Feb 27, karma: 19, MATS Program / Scalable Oversight) — Addresses the core problem of eliciting aligned behavior without reliable human supervision; MATS provenance + scalable oversight tag makes this directly relevant to the unsupervised-elicitation bottleneck where safety research needs to go. <https://www.lesswrong.com/posts/DKLrdLLxm5kLJbr7G/3-challenges-and-2-hopes-for-the-safety-of-unsupervised>
- **"The Dawn of AI Scheming"** (LW, Feb 27, karma: 13, tags: Deceptive Alignment / AI Control / Threat Models) — Survey/threat-model piece on AI scheming; low-ish karma but the tag cluster (deceptive alignment + AI evaluations + coherence arguments) signals conceptually important content for understanding how scheming could arise and be detected. <https://www.lesswrong.com/posts/4rZbyJN8KjM9LHwh8/the-dawn-of-ai-scheming>

**[watching]** *The Topology of LLM Behavior* — still at karma 17 (flat for 3+ hours); may be settling. Dropping from active watch; will promote if karma spikes above 25.

---
**2026-02-28 13:15 (Sat)** — scan: AF +1 new, LW +10 new | backlog: 30 unread (post-scan)

Filtered non-safety noise (marked read): Jhana 0, Mindscapes & Mind Palaces, Lithium/Alzheimer's linkpost, The tick in my back, Ball+Gravity preference, AI Security Bootcamp Singapore.

**[new pick]** *Schelling Goodness, and Shared Morality as a Goal* (AF + LW crosspost, Feb 28, karma: early)
- Why: Alignment Forum provenance signals researcher-level content; Schelling coordination as a foundation for shared morality is directly relevant to multi-stakeholder value alignment — how to find stable convergence points across agents/humans with different values, a key challenge for scalable alignment.
- Links: AF: <https://www.alignmentforum.org/posts/TkBCR8XRGw7qmao6z/schelling-goodness-and-shared-morality-as-a-goal> | LW: <https://www.lesswrong.com/posts/TkBCR8XRGw7qmao6z/schelling-goodness-and-shared-morality-as-a-goal>

**[backlog-pick]** *AI #157: Burn the Boats* (Zvi Mowshowitz, LessWrong, Feb 26)
- Why: Zvi's weekly digest — this edition covers the Anthropic/DoD standoff week; high-signal synthesis of the governance crisis, red-line dynamics, and broader lab positioning; good map of what actually happened that week in condensed form.
- Link: <https://www.lesswrong.com/posts/zC3Rtrj6RXwEde9h6/ai-157-burn-the-boats>

---
**2026-02-28 13:45 (Sat)** — scan: AF rate-limited (429), LW +0 new since 05:15 UTC | backlog: ~14 unread

No high-signal update. All visible RSS items already covered; recent backlog picks fresh (Schelling Goodness, AI #157, 3 Challenges/Unsupervised Elicitation, Dawn of AI Scheming). Holding queue until next cycle.

---
**2026-02-28 14:15 (Sat)** — scan: AF +0 new, LW +0 new | backlog: 24 unread

No new posts. All 10 feed items already in db.

**[backlog-pick]** *Side by Side Comparison of RSP Versions* (LessWrong, Feb 27)
- Why: Direct analytical comparison of Responsible Scaling Policy versions across labs — highest-signal policy-tracking content in the current backlog; tracks how safety commitments are evolving (or weakening) as labs update their RSPs over time.
- Link: <https://www.lesswrong.com/posts/aKpXgbJKvoeJ7Ler8/side-by-side-comparison-of-rsp-versions>

**[watching]** *Anthropic and the DoW: Anthropic Responds* (LW, Feb 27) — governance/policy angle on the Anthropic-DoD standoff; holding as context companion to AI #157 already picked.

---
**2026-02-28 14:45 (Sat)** — scan: AF +0 new, LW +0 new since 14:15 | backlog: ~23 unread

No new posts. Feed identical to 14:15 snapshot.

**[backlog-pick]** *Why Did My Model Do That? Model Incrimination for Diagnosing LLM Misbehavior* (Alignment Forum, Feb 27)
- Why: AF-native (researcher-grade signal) post on diagnosing *why* a model misbehaved — sits at the intersection of interpretability and safety evaluation; directly actionable for anyone building evals or trying to attribute misbehavior to training causes vs. deployment context; complements the unsupervised elicitation / scheming-detection thread already in queue.
- Link: <https://www.alignmentforum.org/posts/Bv4CLkNzuG6XYTjEe/why-did-my-model-do-that-model-incrimination-for-diagnosing>

---
**2026-02-28 15:15 (Sat)** — scan: AF rate-limited (429), LW +0 new since 14:45 | backlog: ~22 unread

No new posts since last cycle. Feed unchanged.

**[backlog-pick]** *New ARENA material: 8 exercise sets on alignment science & interpretability* (LessWrong, Feb 27, CallumMcDougall, karma: 64)
- Why: ARENA is the primary hands-on curriculum for alignment research training; 8 new exercise sets covering alignment science + interpretability represents a significant curriculum expansion — high value for anyone doing or supervising alignment research skill development; solid karma signal (64) confirms community endorsement.
- Link: <https://www.lesswrong.com/posts/nQAN2vxv2ASjowMda/new-arena-material-8-exercise-sets-on-alignment-science-and>

---
**2026-02-28 15:45 (Sat)** — scan: AF +0 new, LW +0 new since 15:15 | backlog: ~21 unread

No new posts. Both feeds unchanged from prior cycle. Recent backlog queue already well-stocked (ARENA material, Model Incrimination, RSP Comparison, Schelling Goodness, AI #157, 3 Challenges/Unsupervised Elicitation, Dawn of AI Scheming). No high-signal update this cycle.

---
**2026-02-28 16:15 (Sat)** — scan: AF top = "Schelling Goodness" (already picked 13:15), LW top = same | backlog: ~21 unread

No new posts. Both feeds identical to 15:45 snapshot; Saturday afternoon lull.

**[backlog-pick]** *The Topology of LLM Behavior* (LessWrong, Feb 28, karma grown from 11→17+ since morning)
- Why: Informal but useful framing of LLM generation as navigation through a weighted semantic attractor landscape — alignment constraints as attractors that can be stable or fragile; complements the week's thread on behavioral stability (attractor states, persona selection, sandbagging). Karma growth throughout the day signals the community finding it worth engaging with; now worth committing a read slot.
- Link: https://www.lesswrong.com/posts/iPmqM4qn7YnktcSus/the-topology-of-llm-behavior-1

---
**2026-02-28 17:15 (Sat)** — scan: AF +0 new, LW +0 new | backlog: ~21 unread

No new posts. Saturday evening quiet continues. Feeds flat since morning.

**[backlog-pick]** *Side by Side Comparison of RSP Versions* (LessWrong, Feb 27)
- Why: Systematic diff of Anthropic's Responsible Scaling Policy revisions over time — directly useful for understanding how red lines and commitments have evolved, especially timely given the ongoing Anthropic/DoD controversy dominating this week's feed; policy tracking anchor.
- Link: <https://www.lesswrong.com/posts/aKpXgbJKvoeJ7Ler8/side-by-side-comparison-of-rsp-versions>

---
**2026-02-28 16:45 (Sat)** — scan: AF rate-limited (429), LW +0 new since 16:15 | backlog: ~21 unread

No new posts. Both feeds unchanged from 16:15 cycle; Saturday afternoon quiet continues.

**[backlog-pick]** *Sam Altman says OpenAI shares Anthropic's red lines in Pentagon fight* (LessWrong, Feb 27, karma: 76)
- Why: Direct governance signal — Altman publicly aligning OpenAI with Anthropic's autonomous weapons red lines in the DoD standoff; closes the loop on the Dario/DoW statement already in the watching queue and reveals industry-level coordination on the "no lethal autonomy" norm; high karma + AI Governance/Autonomous Weapons tags confirm community signal weight.
- Link: <https://www.lesswrong.com/posts/sam-altman-says-openai-shares-anthropic-s-red-lines-in>

---
**2026-02-28 17:45 (Sat)** — scan: AF +0 new (top: "Schelling Goodness"), LW +0 new | backlog: ~21 unread

No new posts. Both feeds identical to earlier Saturday cycles; Saturday evening quiet. All top LW/AF items this week already picked (Schelling Goodness, Model Incrimination, ARENA material, DoW coverage, RSP comparison, Sam Altman red lines, Frontier AI can't leave US). Backlog well-stocked — no further picks warranted this cycle.

---
**2026-02-28 18:15 (Sat)** — scan: AF top = "Schelling Goodness" (unchanged), LW top = same | backlog: ~21 unread

No new posts. Both feeds flat since morning; Saturday evening quiet continues. No backlog pick — well-stocked from earlier cycles today (RSP comparison, Sam Altman red lines, Topology of LLM Behavior, ARENA material). No further picks warranted this cycle.

---
**2026-02-28 18:01 (Sat)** — scan: AF +0 new, LW +0 new | backlog: ~21 unread (unchanged)

No new posts. Saturday evening quiet continues.

**[portfolio connection note — cycle #85]** 
*New ARENA material* (Feb 27, karma: 65) = highest-value actionable item this week for Leo specifically:
- **Linear Probes** → directly teaches probing for Paper B AudioSAEBench
- **Attribution Graphs** → `circuit-tracer` library = hands-on circuit analysis (Track 1 + Paper A methodology)
- **Emergent Misalignment** → LoRA exercises = Track 4 foundation
- **Recommendation:** Leo should do ARENA "Linear Probes" + "Attribution Graphs" exercises BEFORE first NNsight/pyvene experiment. 2-4 day investment = higher quality experiments.
- URL: https://learn.arena.education/ (branch: `alignment-science`, merging to main this Sunday)

---
**2026-02-28 18:45 (Sat)** — scan: AF rate-limited (429), LW +0 new (top: "Schelling Goodness", 04:25 UTC, unchanged) | backlog: ~21 unread

No new posts. Both feeds flat since morning; all high-signal items from this week already picked (Schelling Goodness, ARENA material, Dario DoW statement, Zvi DoW responds, Sam Altman red lines, RSP comparison, AI #157). No further picks warranted this cycle.

---
**2026-02-28 19:15 (Sat)** — scan: AF +0 new, LW +0 new | backlog: ~19 unread (2 formally marked read)

No new posts. Backlog housekeeping: marked articles [37] "The Topology of LLM Behavior" and [40] "Side by Side Comparison of RSP Versions" as read in blogwatcher — both had been verbally picked in earlier cycles (18:01, 18:45) but not formally marked. No new high-signal items this cycle.

---
**2026-02-28 19:45 (Sat)** — scan: AF rate-limited (429), LW top = "Schelling Goodness" (04:25 UTC, unchanged) | backlog: ~19 unread

No new high-signal updates. Both feeds flat since morning; Saturday evening quiet continues. All notable items from this week already picked and logged (Schelling Goodness, ARENA material, DoW series, RSP comparison, Sam Altman red lines). No further picks warranted — backlog well-stocked from today's earlier cycles.

---
**2026-02-28 20:15 (Sat)** — scan: AF rate-limited (429), LW +0 new since 05:50 UTC (13:50 CST; last LW post was "How can rationalists perform exceptionally well?", karma: -4 — non-safety) | backlog: ~19 unread

No new posts on primary feeds. EA Forum auxiliary scan surfaced one notable item not yet formally captured:

**[backlog-pick]** *Pete Hegseth declares Anthropic a supply-chain risk* (EA Forum, Feb 27, karma: 53)
- Why: The formal designation — not just a threat — of Anthropic as a supply-chain risk by the DoD Secretary is a concrete governance escalation beyond what was captured in earlier picks (Zvi's breakdown described this as a threatened consequence of the standoff, not an accomplished fact); closes the loop on the week's Anthropic/DoD arc and sets the actual regulatory posture going into the weekend; high karma confirms community weight.
- Link: <https://forum.effectivealtruism.org/posts/pete-hegseth-declares-anthropic-a-supply-chain-risk>

---
**2026-02-28 20:45 (Sat)** — scan: AF rate-limited (429), LW top = "Schelling Goodness" (04:25 UTC, unchanged) | backlog: ~19 unread

No new posts. Saturday evening quiet continues. All high-signal items from this week already picked and logged. No further picks warranted this cycle.

---
**2026-02-28 21:15 (Sat)** — scan: AF rate-limited (429), LW top = "Schelling Goodness" (04:25 UTC Feb 28, unchanged) | EA Forum top = "Pete Hegseth/Anthropic supply-chain risk" (Feb 27, already picked) | backlog: ~19 unread

No new posts. Both feeds identical to prior cycles; Saturday night quiet. All high-signal items from this week already picked and logged (Schelling Goodness, ARENA material, Model Incrimination, DoW coverage series, RSP comparison, Sam Altman red lines, Pete Hegseth/supply-chain risk). No further picks warranted this cycle.

---
**2026-02-28 22:15 (Sat)** — scan: AF rate-limited (429), LW top = "Schelling Goodness" (04:25 UTC, unchanged) | EA Forum top = "OpenAI from Non-profit to deal with the U.S. Department of War" (already picked 21:45) | backlog: ~19 unread

No new posts. Both feeds identical to 21:45 cycle; Saturday night quiet continues. All high-signal items from this week logged. No further picks warranted this cycle.

---
**2026-02-28 21:45 (Sat)** — scan: AF rate-limited (429), LW top = "Schelling Goodness" (04:25 UTC, unchanged) | EA Forum: +1 new post not previously logged

**[new-pick]** *OpenAI from Non-profit to deal with the U.S. Department of War* (EA Forum, Feb 28, score: 5.4)
- Why: Completes the week's DoW arc — where previous picks covered Anthropic's standoff and Sam Altman's solidarity statement, this captures OpenAI actually finalizing its corporate structure conversion *and* signing the Pentagon deal simultaneously; the combination of for-profit conversion + military contract in the same moment is the governance data point that closes the week's narrative arc on AI/DoD alignment.
- Link: <https://forum.effectivealtruism.org/posts/zYEkakZiRAbgxfDxQ/openai-from-non-profit-to-deal-with-the-u-s-department-of>
