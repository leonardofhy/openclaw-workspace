# Paper A: Related Work Section Draft
# "Localizing the Listen Layer in Speech LLMs"
# Generated: c-20260304-0815 | Track: T3 | Status: Draft — Leo to refine prose + fill citations

---

## 2. Related Work

### 2.1 Modality Dynamics in Audio-Language Models

Recent large audio-language models (LALMs) — including Qwen2-Audio [CITATION], SALMONN [CITATION], and Gemini [CITATION] — encode speech via a frozen speech encoder (typically Whisper) whose output is projected into an LLM decoder via a connector module. This architectural split raises a fundamental question: *when*, if ever, does the LLM decoder consult audio representations rather than defaulting to language priors?

Li et al. [CITATION: ALME 2602.11488] construct 57K audio-text conflict stimuli and show behaviorally that LALMs frequently ignore audio content, listening to text instead. AudioLens [CITATION: 智凱哥, 2025] extends this with a logit-lens analysis revealing layer-wise information leakage — suggesting audio representations are *present* in intermediate layers but not necessarily *used*. The Modality Collapse hypothesis [CITATION: 2602.23136] formalizes this: speech information encoded in the connector may be discarded rather than integrated. These works are *observational* — they characterize what information is present via correlation or probing, without establishing causal effect.

We introduce a causal complement: instead of asking "is audio information here?", we ask "does intervening on audio information here *change the output*?" — the standard of causal mechanistic interpretability [CITATION: Geiger et al. 2301.04709].

### 2.2 Causal Interpretability in Language Models

Causal abstraction [CITATION: Geiger et al. 2301.04709] provides a principled framework for measuring whether a model's internal representation causally implements a hypothesized variable. Distributed Alignment Search (DAS) operationalizes this via intervention: given two inputs (A, B) that differ in variable X, we patch A's activations at layer L with B's activations, and measure whether the output switches as if X changed. The IIT accuracy (which we term gc(L)) is the intervention-induced accuracy normalized against a perfect-swap baseline.

Heimersheim & Nanda [CITATION: 2024] introduce *denoising patching* as a sufficiency test: patch in a "clean" intermediate representation and check if the output recovers correct behavior. We adapt this to audio-text conflict: we patch the audio encoder's output at layer L with representations from a same-content non-conflict stimulus, measuring whether the model's output switches from text-reliant to audio-reliant. This tests whether layer L causally mediates audio consultation.

Prior causal tracing work in text LLMs [CITATION: ROME, Meng et al.] and Vision-LLMs [CITATION: FCCT, Li et al. 2511.05923] establishes that specific layers localize factual memory and visual feature binding, respectively. We extend this paradigm to speech: identifying the *Listen Layer* — the layer L* at which gc(L) peaks — as the causal locus of audio consultation in speech LLMs.

### 2.3 Speech Safety and Audio Jailbreaks

The emergence of audio jailbreak attacks [CITATION: JALMBench ICLR 2026] — wherein adversarially crafted speech bypasses safety alignment — motivates mechanistic understanding of audio processing. SPIRIT [CITATION: EMNLP 2025] defends against such attacks via inference-time activation patching across layers, finding that certain intermediate layers are more effective patch points. However, SPIRIT does not measure *causal effect size per layer* — it applies patches and evaluates downstream jailbreak rates, without identifying *why* a layer is an effective target. Our gc(L) audit provides precisely this diagnostic: the layer-resolved causal map that would enable SPIRIT-style defenses to be principled rather than empirical.

ALMGuard [CITATION: NeurIPS 2025] identifies safety shortcuts in audio LMs via gradient-based mel-spectrogram perturbations (Shortcut Activation Perturbations; SAP). ALMGuard operates at the *input* level — it does not localize which internal layer processes these shortcuts. Our method provides the complementary *internal* view: where in the decoder does audio-encoded safety-relevant content become causally decisive?

JALMBench [CITATION: ICLR 2026] provides 246 curated audio jailbreak queries across 4 LALMs. We use this corpus in our T5 safety probe extension (§5).

### 2.4 Causal Tracing in Multimodal Models

FCCT [CITATION: Li et al. 2511.05923, AAAI 2026 Oral] is the closest structural sibling to our work: it performs causal tracing in Vision-LLMs to identify which layers bind visual features to language outputs, and proposes Inference-time Representation Injection (IRI) to leverage this for targeted model correction. FCCT is architecturally distinct — vision encoders emit patch tokens consumed by cross-attention MHSAs, whereas speech encoders emit dense frame embeddings consumed by a connector + LLM decoder. Circuit-level tools (CLT [CITATION]) support text token streams but not audio cross-attention; NNsight [CITATION: Fiotto-Kaufman et al.] provides the intervention API we rely on. Despite the architectural differences, FCCT validates the general approach: causal tracing in multimodal models is tractable and yields actionable insights.

Our contribution is the audio-domain instantiation of this paradigm: the first *causally grounded, layer-resolved* localization of audio consultation in speech LLMs, using gc(L) (IIT accuracy) as the intervention metric, applied to ALME-style conflict stimuli and extended to audio safety probing.

---

## Citation Checklist (for Leo to verify)

- [ ] Qwen2-Audio — add arXiv ID
- [ ] SALMONN — add arXiv ID  
- [ ] ALME: Li et al. arXiv:2602.11488
- [ ] AudioLens: 智凱哥 2025 — add actual citation
- [ ] Modality Collapse: arXiv:2602.23136
- [ ] Cascade Equivalence: arXiv:2602.17598
- [ ] Geiger et al. 2301.04709 — causal abstraction
- [ ] Heimersheim & Nanda 2024 — denoising patching
- [ ] FCCT: Li et al. arXiv:2511.05923 (AAAI 2026 Oral)
- [ ] SPIRIT: EMNLP 2025 — need full citation
- [ ] ALMGuard: NeurIPS 2025 — need full citation
- [ ] JALMBench: ICLR 2026 — need full citation
- [ ] ROME: Meng et al. — add arXiv ID
- [ ] NNsight: Fiotto-Kaufman et al. — add arXiv ID

---

## Word Count Estimate
~680 words. Interspeech allows 4+1 pages; this is targeted at ~0.8 pages.
Trim to ~500 words if space-constrained (cut §2.3 intro or merge with §2.4).
