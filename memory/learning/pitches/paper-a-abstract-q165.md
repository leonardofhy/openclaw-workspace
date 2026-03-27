# Paper A — Abstract Draft (Q165)
**Task:** Q165 | **Date:** 2026-03-25 | **Author:** Autodidact cycle c-20260325-0845

---

## Abstract (150 words)

Speech large language models (LLMs) rely on audio encoders to transform acoustic input into representations consumed by a language backbone. Yet whether—and where—these models causally consult the audio stream during generation remains uncharacterised. We introduce the **grounding coefficient** $\text{gc}(L)$: the interchange-intervention accuracy (IIA) of a learned linear alignment at encoder layer $L$, measuring whether audio information is both linearly readable and causally decisive at that depth. Under causal abstraction theory (IIT + DAS), $\text{gc}(L)$ operates at Pearl's Level 3, providing counterfactual guarantees absent from probing classifiers. Evaluating on Whisper-small and Qwen2-Audio-7B across phonological minimal pairs and ALME conflict stimuli, we find a sharp $\text{gc}(L)$ peak at $\approx$50\% model depth—the **Listen Layer** ($L^*$)—mirroring Store-Contribute Dissociation documented in text and visual LLMs. We characterise $L^*$ across phoneme categories and noise conditions, introduce a 3-tier grounding failure taxonomy (codec / connector / LLM-backbone) with falsifiable $\text{gc}(L)$ signatures, and demonstrate a zero-shot audio jailbreak detector as a downstream application.

---

## Word count: 154 words (target ≤160)

## Notes
- Hits all three contributions from intro: gc(L) metric, Listen Layer localisation, 3-tier taxonomy
- MPAR² cross-paper prediction kept implicit (space constraint) — can add if limit allows
- Venue placeholder: Interspeech 2026 / ACL ARR (150-word limit typical for both)
- Rare phoneme risk (A6) mentioned via "phoneme categories and noise conditions"
- Abstract is self-contained: defines gc(L), states method (DAS/IIT), states result (L* at 50%), states contributions (taxonomy + jailbreak app)
