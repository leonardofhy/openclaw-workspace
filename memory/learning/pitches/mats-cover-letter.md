# MATS Cover Letter
## "Mechanistic Audio Safety: Listen-Layer Audit for Jailbreak Detection"

> Created: 2026-03-25 | Task: Q169 | Track: T5
> For: MATS (Mechanistic Interpretability Track or AI Safety Track)

---

## Cover Letter Draft

Dear MATS Admissions Committee,

I am a first-year Master's student at National Taiwan University (GICE), applying to MATS because I believe **mechanistic interpretability is the right lens for audio-language model safety** — and because I have preliminary results that say so.

My research builds on a deceptively simple observation: when a speech model processes audio, it does not actually "listen" uniformly across all layers. Using causal patching on Whisper-base, I identified a **Listen Layer** — a narrow peak in the grounding coefficient gc(L) — where audio representations causally determine model behavior. Models that miss this peak (low gc(k)) guess from language priors rather than grounding in acoustics. This is not just interesting mechanistically; it is a safety hazard.

Here is the safety implication that motivates my MATS application: **audio jailbreaks work by suppressing the Listen Layer.** When an adversarial audio input attacks a speech LLM, the gc(L) profile does not peak — it flattens or shifts. The model stops consulting the audio channel and falls back on its text-language priors, which can be manipulated with injection or prosodic command overlays. This gives us a **zero-shot, attack-agnostic jailbreak detector**: compute gc(L) at inference time; anomaly score = KL-divergence from the benign gc(L) baseline. No labeled attack examples required. No fine-tuning required.

I have already built CPU-feasible mocks demonstrating this signal:
- `audio_jailbreak_andfrac_mock.py`: AND-frac < 0.4 under jailbreak vs. > 0.6 benign; r(jailbreak, AND-frac) < −0.5
- `commitment_head_ablation_mock.py`: ablating Listen-Layer commitment heads increases hallucination rate ≥ 20%
- `real_steerability.py`: on 5 real L2-ARCTIC samples, causal patching raises AND-frac ≥ 0.05

The second use-case — **pre-deployment emergent misalignment screening** — extends this work toward proactive AI safety. Models with low gc(k) profiles are disproportionately vulnerable to fine-tune-induced safety degradation. A single inference-time gc(k) audit, run *before* deployment or fine-tuning, can flag high-risk checkpoints. This is the first proposed mechanism for audio emergent misalignment risk stratification.

**Why MATS?** I want to be part of a community that treats mechanistic interpretability as a prerequisite for safety, not an academic curiosity. My work is small-scale and CPU-feasible today; with MATS mentorship and compute, I can run the full JALMBench evaluation (246 queries, 5 attack paradigms), benchmark against SALMONN-Guard and SPIRIT, and build the pre-deployment screening pipeline. The adversarial robustness argument is particularly compelling to me as a safety rationale: an attacker evading gc(L) detection must craft audio that *preserves normal causal audio processing while achieving the jailbreak* — these are structurally conflicting objectives.

My longer-term goal is to establish mechanistic safety protocols for audio models that parallel the interpretability-based oversight being developed for text LLMs. Audio is underexplored, yet audio interfaces are where safety guarantees are weakest. I believe gc(k) audits, Listen Layer identification, and commitment head probes form the first layer of a rigorous audio safety framework — and I want to build it.

I would be grateful for the opportunity to develop this work within the MATS community.

Sincerely,
Leonardo (胡皓雍)
National Taiwan University, GICE
[leonardofoohy@gmail.com]

---

## Notes for Leo

- **Length:** ~420 words — within MATS typical 1-page limit if typeset at 11pt
- **Track choice:** Framed primarily for **MI track** (gc(L) = causal quantity, Listen Layer = core MI work), but safety framing is strong enough for **AI Safety track** too. Could trim the technical details and expand safety motivation if targeting safety track.
- **Tone:** Technical but not dry — tries to convey genuine motivation, not just credentials.
- **Open questions:**
  1. Should I mention Paper A directly by name/title, or keep it as "my research"?
  2. Is the emergent misalignment angle strong enough to keep, or does it dilute the jailbreak focus?
  3. Any specific MATS mentors / labs to name-drop in closing (I left it generic intentionally)?
  4. Word count target? MATS website says 1 page; this is ~420 words which fits comfortably.

---

## Relationship to Proposal

This cover letter is a narrative companion to `mats-proposal-v1.md`.
- Proposal = technical depth (method, timeline, anti-confound checklist)
- Cover letter = motivation + positioning + safety argument

Both together form the MATS application package for T5 (Listen-Layer Audit / Paper C).
