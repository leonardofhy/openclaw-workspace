# Paper A — Related Work Draft
**Track:** T3 (Listen vs Guess)
**Version:** v0.1 | **Date:** 2026-03-06
**Task:** Q053

---

## Related Work (~520 words)

### Causal Tracing in Language Models

Our grounding coefficient gc(k) is most directly inspired by causal tracing (Meng et al., 2022; ROME), which measures the causal effect of individual components on model output by patching activations from "corrupted" to "clean" runs. We adapt this framework to the audio modality: instead of localizing factual knowledge in attention heads, we localize acoustic grounding across encoder layers. Crucially, prior causal tracing work operates in text-only models on semantic knowledge; we are the first to apply layer-wise causal patching to the audio encoder of an ALM to measure *modality-specific evidence utilization*. Concurrent work on Distributed Alignment Search (DAS; Geiger et al., 2023) provides the patching formalism underlying our DAS-based gc(k) estimation.

### Mechanistic Interpretability of Multimodal Models

Tenney et al. (2019) demonstrate that linguistic structure emerges hierarchically across BERT layers — lower layers encode syntax, higher layers semantics. Analogous layer-probing work in vision-language models (Cao et al., 2022) identifies "modality fusion layers" where image and text representations first interact. Our Listen Layer hypothesis posits a modality-separation version of this: there exists a critical layer k* beyond which the acoustic evidence is dominated by the linguistic prior, detectable via causal (not correlational) probing. This is a stronger claim than feature geometry analysis, and our gc(k) metric provides the causal warrant that standard linear probes do not.

### Acoustic Hallucination in ASR and ALMs

Hallucination in ASR systems — generating plausible but acoustically unsupported transcriptions — is well-documented (Maiti et al., 2023; Koenecke et al., 2024). Maiti et al. catalog hallucination types in Whisper, attributing them to strong language prior influence. Our work provides a mechanistic account: hallucinations concentrate in samples where the model is in "Guess" mode (low gc(k) at k*), and we operationalize this as a quantitative per-sample fault attribution. Concurrent work on biasing and prefix injection (Prabhavalkar et al., 2023) shows that context priors can override acoustic evidence, consistent with our Listen-Guess dichotomy.

### Audio Safety and Jailbreak Detection

The audio modality introduces unique attack surfaces: adversarial audio patches (Carlini & Wagner, 2018; Yakura & Sakuma, 2018), audio prompt injection (Kang et al., 2024), and — most relevant to our downstream application — the JALMBench benchmark (246 queries; Chen et al., 2024), which systematically evaluates audio-specific jailbreak attacks on ALMs. Existing detection methods rely on text-content filters applied post-hoc to transcriptions, which miss audio-modality attacks by design. Our gc(k) anomaly detector operates at the activation level, before transcription, providing attack-agnostic zero-shot detection. The only existing mechanistic defense is activation steering (Turner et al., 2023), which requires supervised identification of "refusal directions" — our approach needs no supervision.

### Eval Infrastructure for Mechanistic Interpretability

Recent work on TransformerLens (Nanda et al., 2022) and baukit provides layer hooking infrastructure for transformer circuits research. Our `gc_eval.py` and `listen_layer_audit.py` extend this paradigm to audio transformers (Whisper-class models), filling a gap: no open mechanistic interpretability tooling targets audio LM encoders. AudioSAEBench (2025) benchmarks sparse autoencoders on audio models, which is complementary — SAE features can be used to interpret *what* is encoded at k*, while gc(k) tells us *how much* acoustic evidence is causally operative.

---

## Citations to Add (BibTeX pending)
- Meng et al., 2022 — ROME / causal tracing
- Geiger et al., 2023 — DAS
- Tenney et al., 2019 — BERT layer probing
- Maiti et al., 2023 — Whisper hallucinations
- Chen et al., 2024 — JALMBench
- Nanda et al., 2022 — TransformerLens
- Kang et al., 2024 — audio prompt injection
- AudioSAEBench, 2025

---

## Notes
- Q052 done. Cite Maiti et al. prominently in intro § as well.
- Methods section (Q054) will formalize gc(k) and DAS estimation algorithm.
- Need to add 1-2 sentences positioning vs. linear probing (doesn't prove causation).
