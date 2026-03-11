# Paper A — Introduction Draft
**Track:** T3 (Listen vs Guess)
**Version:** v0.2 | **Date:** 2026-03-12 | **Updated:** Q077 — incorporated Billa (2026) CEH + Gap #32

---

## Title (working)
**Listen or Guess? Locating the Acoustic Grounding Boundary in Speech Language Models**

---

## Introduction (~450 words)

Automatic speech recognition (ASR) has entered the era of audio language models (ALMs): systems such as Whisper, Qwen2-Audio, and SALMONN jointly encode acoustic input and generate text via a large language model decoder. These models achieve remarkable performance — yet they fail in systematic, predictable ways. A model that correctly transcribes "pack" in isolation may hallucinate "back" when a biasing context is present, not because its acoustic encoder is confused, but because its language prior overwrites the acoustic evidence before transcription.

This failure mode is increasingly well characterized at the behavioral level. Li et al. (2025) show via the ALME benchmark that ALMs can be contextually biased toward incorrect transcriptions even when the acoustic signal is unambiguous. Billa (2026) formalizes this further via the **Cascade Equivalence Hypothesis (CEH)**: on text-sufficient tasks (where acoustic surplus ΔI_Y = I(A;Y) − I(T;Y) ≈ 0), speech LLMs behave statistically indistinguishably from matched-backbone ASR+LLM cascades, and under noise conditions (0 dB SNR), cascades can outperform integrated speech LLMs by up to 7.6%. The CEH implies that, for a non-trivial range of inputs, the speech LLM's audio encoder contributes near-zero causal surplus — it is "guessing" from text priors rather than "listening" to the audio.

What these behavioral analyses cannot answer is *where* in the forward pass audio representations become causally decisive. The acoustic surplus ΔI_Y is a task-level measure; it does not localize the moment of audio-to-text handoff to any specific layer or component. Billa (2026) provides a layer-level sanity check via logit lens — transcript tokens emerge in hidden states as early as intermediate layers — but does not establish *causality*: whether those layers are responsible for final output or are epiphenomenal.

We address this gap mechanistically. Within an ALM's audio encoder, two qualitatively different computations occur in sequence: *direct acoustic evidence accumulation* (we call this "Listen") and *cross-modal prior filling* ("Guess"). The transition from Listen to Guess is not a design choice — it emerges from training — but locating it precisely would expose the mechanism behind acoustic hallucinations, context-biased errors, and adversarial audio vulnerabilities.

We formalize this boundary as the **grounding coefficient** gc(k): the proportion of transcription variance causally attributable to the audio representation at encoder layer k, measured via causal patching under linear distributed alignment search (DAS). A high gc(k) indicates that the model's output is predominantly driven by acoustic evidence up to layer k; a low gc(k) indicates that the language-model prior has taken over. We hypothesize that gc(k) traces a characteristic sigmoid curve across layers, with a sharp transition at a critical layer k* — the **Listen Layer** — mechanistically corresponding to the behavioral cascade-equivalence transition identified by Billa (2026).

This paper makes three contributions:
1. **Formalization of gc(k)**: We define the grounding coefficient as a layer-wise causal patching metric under linear DAS and provide an efficient estimation algorithm for Whisper-class encoders.
2. **Empirical localization of the Listen Layer**: Using synthetic phoneme-pair stimuli and ALME conflict items, we identify k* for Whisper-small and Whisper-medium and validate that gc(k*) correlates with acoustic hallucination rate on LibriSpeech noise conditions.
3. **Two downstream applications**: (a) a zero-shot jailbreak detector for ALMs based on Listen Layer gc anomaly (T5/Paper C), and (b) a diagnostic tool for attributing ASR errors to acoustic vs. linguistic causes.

Together, these results provide the first layer-level causal account of the acoustic-to-linguistic transition in speech LLMs — a mechanistic complement to the behavioral cascade equivalence established by Billa (2026) and a foundation for targeted intervention, robustness improvements, and safety-relevant monitoring.

---

## §1 Positioning Changes (v0.1 → v0.2)

| Change | Rationale |
|--------|-----------|
| Added Billa (2026) CEH + 7.6% noise finding as motivation | Strongest behavioral evidence for text dominance; peer-reviewed Interspeech 2026 submission |
| Added ΔI_Y definition and acoustic surplus concept | Bridges behavioral and mechanistic framing; sets up gc(k) as layer-level version |
| Added "behavioral analyses cannot answer WHERE" paragraph | Sharpens the gap; directly responds to Gap #32 |
| Revised final contribution statement | Now explicitly frames Paper A as mechanistic complement to Billa (2026) |
| Preserved Sutter linearity guard in §2 stub | No change needed |

---

## §2 Methodology Stub — Sutter Linearity Guard (v0.1, Q048, 2026-03-06)

### Why Linear Alignment Maps? (Defending DAS)

Causal abstraction \citep{geiger2021} provides the formal foundation for gc(k): the grounding coefficient measures whether a high-level causal variable (acoustic evidence) is *faithfully* realized in the model's internal representation at layer k. A natural concern is that non-linear alignment maps could trivially achieve high IIA even when no genuine grounding structure exists. Sutter et al. (NeurIPS 2025 Spotlight) establish this rigorously: with sufficiently expressive (non-linear) alignment maps, \emph{any} neural network can be made to appear causally consistent with \emph{any} algorithm, rendering causal abstraction vacuous as a scientific claim. We therefore restrict gc(k) estimation to \textbf{linear DAS} (distributed alignment search with linear rotation; \citealt{wu2024}): any increase in IIA observed under this constraint genuinely reflects linear acoustic feature structure in the representation, not an artifact of an expressive alignment function. This choice also aligns with the broader linear representation hypothesis for neural language models \citep{park2023} and with Asiaee et al.'s (2026) efficiency result showing that activation variance serves as a reliable pre-screen precisely because high-variance layers tend to have linearly readable features.

**Key cite:** Sutter et al., "Causal Abstraction Requires Linear Alignment Maps," NeurIPS 2025 Spotlight (arXiv:2507.08802)
**Placement:** §2.2 (after DAS definition, before gc(k) estimation algorithm)
**Tone:** Weakness-turned-strength — "one might object... we address this by..."

---

## Citation Block (for §1)

```bibtex
@inproceedings{billa2026ceh,
  title     = {The Cascade Equivalence Hypothesis},
  author    = {Billa, Jayadev},
  booktitle = {Interspeech 2026},
  year      = {2026},
  note      = {arXiv:2602.17598}
}
```
