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
