# Paper A — Introduction Draft
**Track:** T3 (Listen vs Guess)
**Version:** v0.1 | **Date:** 2026-03-05

---

## Title (working)
**Listen or Guess? Locating the Acoustic Grounding Boundary in Speech Language Models**

---

## Introduction (~400 words)

Automatic speech recognition (ASR) has entered the era of audio language models (ALMs): systems such as Whisper, Qwen2-Audio, and SALMONN jointly encode acoustic input and generate text via a large language model decoder. These models achieve remarkable performance — yet they fail in systematic, predictable ways. A model that correctly transcribes "pack" in isolation may hallucinate "back" when a biasing context is present, not because its acoustic encoder is confused, but because its language prior overwrites the acoustic evidence before transcription.

This failure mode suggests that within an ALM's audio encoder, two qualitatively different computations occur in sequence: *direct acoustic evidence accumulation* (we call this "Listen") and *cross-modal prior filling* ("Guess"). The transition from Listen to Guess is not a design choice — it emerges from training — but locating it precisely would expose the mechanism behind acoustic hallucinations, context-biased errors, and adversarial audio vulnerabilities.

We formalize this boundary as the **grounding coefficient** gc(k): the proportion of transcription variance causally attributable to the audio representation at encoder layer k, measured via causal patching. A high gc(k) indicates that the model's output is predominantly driven by acoustic evidence up to layer k; a low gc(k) indicates that the language-model prior has taken over. We hypothesize that gc(k) traces a characteristic sigmoid curve across layers, with a sharp transition at a critical layer k* — the **Listen Layer**.

This paper makes three contributions:
1. **Formalization of gc(k)**: We define the grounding coefficient as a layer-wise causal patching metric and provide an efficient estimation algorithm for Whisper-class encoders.
2. **Empirical localization of the Listen Layer**: Using synthetic phoneme-pair stimuli, we identify k* for Whisper-small and Whisper-medium and validate that gc(k*) correlates with acoustic hallucination rate on LibriSpeech noise conditions.
3. **Two downstream applications**: (a) a zero-shot jailbreak detector for ALMs based on Listen Layer gc anomaly, and (b) a diagnostic tool for attributing ASR errors to acoustic vs. linguistic causes.

Together, these results establish the Listen Layer as a mechanistically interpretable control point within speech LLMs — a foundation for targeted intervention, robustness improvements, and safety-relevant monitoring.

---

## Notes
- "Listen or Guess?" framing: accessible, catchy, maps directly to gc(k)
- Contribution 3b ties to Paper A applications; contribution 3a bridges to T5/Paper C
- Related work section will position vs: causal tracing (Meng et al.), layer-wise probing (tenney et al.), audio hallucination (maiti et al.)

---

## §2 Methodology Stub — Sutter Linearity Guard (v0.1, Q048, 2026-03-06)

### Why Linear Alignment Maps? (Defending DAS)

Causal abstraction \citep{geiger2021} provides the formal foundation for gc(k): the grounding coefficient measures whether a high-level causal variable (acoustic evidence) is *faithfully* realized in the model's internal representation at layer k. A natural concern is that non-linear alignment maps could trivially achieve high IIA even when no genuine grounding structure exists. Sutter et al. (NeurIPS 2025 Spotlight) establish this rigorously: with sufficiently expressive (non-linear) alignment maps, \emph{any} neural network can be made to appear causally consistent with \emph{any} algorithm, rendering causal abstraction vacuous as a scientific claim. We therefore restrict gc(k) estimation to \textbf{linear DAS} (distributed alignment search with linear rotation; \citealt{wu2024}): any increase in IIA observed under this constraint genuinely reflects linear acoustic feature structure in the representation, not an artifact of an expressive alignment function. This choice also aligns with the broader linear representation hypothesis for neural language models \citep{park2023} and with Asiaee et al.'s (2026) efficiency result showing that activation variance serves as a reliable pre-screen precisely because high-variance layers tend to have linearly readable features.

**Key cite:** Sutter et al., "Causal Abstraction Requires Linear Alignment Maps," NeurIPS 2025 Spotlight (arXiv:2507.08802)
**Placement:** §2.2 (after DAS definition, before gc(k) estimation algorithm)
**Tone:** Weakness-turned-strength — "one might object... we address this by..."
