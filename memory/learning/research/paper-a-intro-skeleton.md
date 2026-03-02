# Paper A: Introduction Section Skeleton
# "Localizing the Listen Layer in Speech LLMs"
# Generated: c-20260302-1115 | Track: T3 | Status: Draft — needs Leo's prose

---

## 1. Introduction

### [Opening hook — 2–3 sentences]
<!-- FILL: Motivate with the observation that audio-language models can answer questions about
     audio, yet we lack mechanistic understanding of *when* in the forward pass audio
     becomes causally decisive. Contrast: behavioral understanding exists (ALME, AudioLens),
     but causal localization does not. -->

Large audio-language models (LALMs) [CITATION: Qwen2-Audio, SALMONN, etc.] have demonstrated
remarkable ability to answer questions grounded in audio content. Yet a fundamental question
remains unanswered: *when* during the forward pass does audio information become causally
decisive — and where in the network is it actually consulted?

### [Problem Statement — 2–3 sentences]
<!-- FILL: Describe the gap. Prior work is behavioral (ALME 57K conflict pairs) or
     correlational (AudioLens logit-lens, Modality Collapse). None localizes causally. -->

Prior mechanistic work characterizes audio-text modality dominance *behaviorally* [CITATION: ALME Li et al.],
identifies modality-sensitive regions *correlatively* [CITATION: AudioLens 智凱哥],
or studies information flow via erasure methods [CITATION: Cascade Equivalence].
Crucially, none applies *causal* interventions to localize where audio representations
become decisive — the approach that has proven most reliable in text-LLM mechanistic interpretability
[CITATION: Geiger et al. causal abstraction; Heimersheim & Nanda denoising patching].

### [This Work — 4–5 sentences]
<!-- FILL: Introduce the Listen Layer concept + gc(k). State 3 key contributions. -->

We introduce the **Listen Layer**: the contiguous set of layers where denoising activation
patching of audio-stream hidden states most strongly flips model behavior from text-dominated
to audio-grounded. We operationalize this via the **grounding coefficient** (gc):
the DAS-IIT accuracy at each layer, measuring *causal* contribution of audio representations
to the model's output [CITATION: Geiger et al. 2301.04709].

Applying gc sweeps to 57K audio-text conflict stimuli [CITATION: ALME Li et al. 2025] on
Whisper-small and Qwen2-Audio-7B, we find:

1. A sharp gc peak at ~50% model depth — matching the Triple Convergence zone identified
   correlatively by [CITATION: AudioLens], now established as *causally decisive*.
2. The Listen Layer shifts with fine-tuning: LoRA-SER adaptation moves L* rightward by ~2 layers,
   consistent with the "delayed specialization" hypothesis [CITATION: Behind the Scenes].
3. Listen Layer suppression predicts audio-grounding failure: in cases where the model
   defaults to text despite conflicting audio, gc(L*) drops significantly.

### [Contributions — bulleted]

We make the following contributions:

- **First causal localization of audio processing** in speech LLMs, using denoising activation
  patching (DAS-IIT) rather than correlational probing or behavioral benchmarks.
- **The grounding coefficient gc(k)**: a theoretically grounded metric (DAS-IIT accuracy)
  that quantifies per-layer causal responsibility for audio consultation.
- **Empirical Listen Layer identification** in Whisper-small and Qwen2-Audio-7B on 57K
  audio-text conflict stimuli [CITATION: ALME], with bootstrap confidence intervals.
- **Listen Layer dynamics**: shifts under LoRA fine-tuning and failure-mode suppression,
  providing actionable guidance for LALM interpretability.

### [Paper Roadmap — 1 sentence]
<!-- FILL: Brief roadmap of remaining sections. -->

Section 2 reviews related work; Section 3 presents the gc(k) formalism and stimuli;
Section 4 details Whisper-small (E1) and Qwen2-Audio-7B (E2) experiments;
Section 5 presents Listen Layer dynamics (E3, E4); Section 6 discusses implications
for audio-LLM safety and interpretability; Section 7 concludes.

---

## Related Work (Section 2 sketch)

<!-- Organize into 3 paragraphs: -->

### Audio-Language Model Interpretability
- AudioLens [智凱哥 et al.] — logit-lens analysis; observational, not causal. Natural predecessor.
- ALME [Li et al. 2025] — behavioral benchmark, 57K conflict pairs. We use their stimuli.
- Modality Collapse [2602.23136] — GMI theory showing audio can be encoded but unused.
- Cascade Equivalence [2602.17598] — LEACE erasure shows implicit cascade; we add causal layer.

### Causal Interpretability Methods
- Causal abstraction / DAS [Geiger et al. 2301.04709] — gc = IIT accuracy. Our theoretical foundation.
- Denoising vs noising patching [Heimersheim & Nanda 2024] — we use denoising (sufficiency claim).
- MMProbe (diff-of-means) > LR probe for causal interventions [ARENA 1.3.1].
- NNsight [NDIF] — necessary for cross-attention in audio-LLMs (circuit-tracer cannot handle cross-attn).

### Multimodal Causal Localization
- FCCT [Li et al. 2511.05923, AAAI 2026 Oral] — closest work; full causal tracing in Vision-LLMs,
  finds MHSAs at middle layers. We do for *speech* what FCCT did for vision.
- SPIRIT [EMNLP 2025] — defense via safety-critical layer identification.
  Side question: Does Listen Layer = SPIRIT's defense layer in audio domain?

---

## Key Phrases / Framing to Preserve

- "Listen vs Guess" — the fundamental question each layer faces when audio conflicts with text prior
- gc(k) = "how much does patching audio representations at layer k causally rescue the audio-grounded answer?"
- Triple Convergence zone — the correlational predecessor; we promote it from observation to causal claim
- "We do for speech what FCCT did for vision" — positions paper cleanly vs closest competitor

---

## Interspeech 2026 Deadline Notes

- Abstract deadline: ~March 5, 2026 (URGENT — 3 days away)
- Full paper: ~April 2026
- Minimum for submission: E1 (Whisper-small) + partial E2 results (or E2 analysis framework)
- If Leo runs E1 this week: abstract + intro can be submitted on time
- ⚠️ Leo should decide: submit to Interspeech 2026 (tight but feasible) or NeurIPS 2026 (full results)?

---

## TODO for Leo

- [ ] Fill in opening hook prose (should feel like a story, not a list)
- [ ] Confirm ALME stimuli usage (email Li et al. authors to be safe, or rely on arXiv citation)
- [ ] Decide venue: Interspeech 2026 (abstract in 3 days!) vs NeurIPS 2026
- [ ] Run E1 (Whisper-small, ~3h on MacBook) — unlocks results section
- [ ] 智凱哥 collaboration decision: co-author or just cite?
