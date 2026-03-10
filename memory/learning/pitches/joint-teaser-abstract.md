# Joint Teaser Abstract: Paper A + Paper C
## Under the Unified Listen-Layer Theory

> Version: 1.0 | Created: 2026-03-06 (Q049, cycle c-20260306-0945)
> Tracks: T3 (Paper A) + T5 (Paper C / MATS)
> Purpose: Unified positioning of both papers; ~250 words for grant/MATS pitch decks

---

## Abstract

Audio language models (ALMs) — systems like Whisper, Qwen2-Audio, and SALMONN — jointly encode acoustic input and generate text via a large language model backbone. Despite strong benchmark performance, these models exhibit systematic failures: they hallucinate words unsupported by audio, ignore acoustic evidence when text priors are strong, and can be jailbroken through audio-modality attacks that text-content filters entirely miss. We argue these failures share a common mechanistic root.

We introduce the **grounding coefficient** gc(k): a layer-wise causal patching metric that measures the fraction of model output variance causally attributable to acoustic evidence at encoder layer k. Applied across layers, gc(k) traces a characteristic curve with a sharp peak at a critical layer k* — the **Listen Layer** — beyond which the language-model prior dominates. This curve is the audio analogue of a "causal circuit boundary" in mechanistic interpretability.

**Paper A** ("Listen or Guess?") formalizes gc(k) and empirically localizes k* in Whisper-small and Qwen2-Audio-7B using DAS-based causal patching on minimal-pair phoneme stimuli. We show gc(k*) correlates with acoustic hallucination rates and serves as a layer-level fault-attribution signal for ASR errors.

**Paper C** ("Listen-Layer Audit") deploys gc(k) as an inference-time safety monitor. When an audio jailbreak is active, the gc(k) pattern at k* is measurably anomalous — providing a zero-shot, attack-agnostic detector evaluated on the 246-query JALMBench benchmark. The same audit identifies pre-deployment risk: ALMs with low gc(k*) (models that predominantly "guess") exhibit greater susceptibility to audio emergent misalignment after fine-tuning.

Together, the two papers establish the Listen Layer as both an **interpretability primitive** (where does audio causally matter?) and a **safety primitive** (is this audio interaction normal?). One metric. Two papers. A unified mechanistic framework for audio-grounded language models.

---

## Positioning Summary

| | Paper A | Paper C |
|--|---------|---------|
| Venue target | Interspeech / ACL 2026 | MATS Research Task → NeurIPS 2026 Safety |
| Core claim | gc(k) localizes the Listen Layer causally | gc(k) anomaly = zero-shot jailbreak detector |
| Primary contribution | Causal localization of audio grounding | Safety audit derived from mechanistic signal |
| Shared infrastructure | `gc_eval.py`, DAS harness, Whisper hooks | Same — builds on Paper A's toolchain |
| Status | §3 complete; eval harness passing unit tests | MATS proposal draft v0.3 ready for Leo review |

---

## One-Line Version (for slides)

> We locate the layer where speech LLMs stop listening and start guessing — and show that layer's causal signature doubles as a zero-shot safety monitor for audio jailbreaks.
