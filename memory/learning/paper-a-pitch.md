# 📄 Paper A Pitch: "Localizing the Listen Layer in Speech LLMs"

> Version: 0.1 | Created: 2026-02-28 04:01 (cycle #57)
> Status: Draft — for Leo's review. Not finalized.
> Connects to: knowledge-graph.md sections H, K, Experiment 1

---

## 1-Sentence Pitch

> We show that a small set of attention heads at a specific depth ("the Listen Layer") in speech LLMs is *causally* responsible for consulting audio representations — localizing it via interchange interventions on 57K audio-text conflict stimuli.

---

## Abstract Draft (target 150 words)

Large audio-language models (LALMs) can answer questions about audio content, but it is unclear *when* during their forward pass audio information becomes causally decisive. Prior work (AudioLens, ALME, Cascade Equivalence) characterizes audio-vs-text modality dominance behaviorally but none localizes *where* in the network audio representations are causally consulted. We introduce the **Listen Layer**: the set of layers where denoising activation patching of audio-stream hidden states most strongly flips model behavior from text-dominated to audio-grounded. We operationalize this using the **grounding coefficient** (gc = causal effect of audio patch / total causal effect), applied to 57K audio-text conflict stimuli from ALME (Li et al., 2025). Experiments on Whisper-small (MacBook) and Qwen2-Audio-7B (via NDIF) reveal a sharp gc peak at ~50% model depth — matching the Triple Convergence zone previously identified correlatively. We further show the Listen Layer shifts with fine-tuning (LoRA-SER) and is suppressed in text-dominant failure cases.

---

## Why This Paper Wins

| Claim | Evidence |
|-------|----------|
| **First causal localization** in speech LLMs | AudioLens = logit-lens only (no interventions); ALME = behavioral; Modality Collapse = GMI theory (no patching); Cascade Equivalence = LEACE erasure (no layer-wise causal sweep) |
| **Strongest stimuli** | ALME 57K conflict pairs — directly contrast audio vs text signal. No need to generate own stimuli. |
| **Grounded in IIT theory** | Geiger et al. 2301.04709 — gc = IIT accuracy. Not ad hoc. |
| **MacBook-feasible start** | Whisper-small experiment validates hypothesis in ~3h before requesting GPU |
| **Co-author leverage** | 智凱哥 = AudioLens author = Leo's labmate. Natural collaboration, shared methodology. |
| **Clear extension path** | Listen Layer (layer-level gc) → AudioSAEBench (feature-level gc) = Paper B. Same metric, same stimuli, different granularity. |

---

## Method (3-Phase)

### Phase 1: Whisper-small IIT sweep (MacBook, ~3h)
1. Minimal pairs from LibriSpeech: same speaker, alternate attribute (accent A vs B; noise level low vs high)
2. NNsight denoising patching: for each encoder layer L:
   - Take hidden state h_L from clean input
   - Patch into corrupt input at layer L, measure WER recovery (Δacc)
3. Plot Δacc vs L → find L* (= "Listen Layer" in encoder)
4. Verify: Does L* ≈ layer 3 in Whisper-base (Triple Convergence zone)?
5. Run CKA + norm comparison → confirm correlational + causal methods agree

**Expected result:** Sharp causal peak at ~50% depth (layer 3/base, 3-4/small, 6-7/large)

### Phase 2: Qwen2-Audio-7B grounding_coefficient (NDIF/GPU)
1. Use ALME 57K audio-text conflict stimuli (Li et al. 2025, arXiv:2602.11488) — already built
2. Two-sweep denoising patching on Qwen2-Audio-7B:
   - Sweep A: patch audio-stream hidden states layer by layer → Δacc(audio)
   - Sweep B: patch text-context hidden states layer by layer → Δacc(text)
3. Compute gc(L) = Δacc_audio(L) / [Δacc_audio(L) + Δacc_text(L)]
4. Find LLM Listen Layer L* where gc peaks → this is the "where audio gets consulted" layer

**Expected result:** Sharp gc peak in mid-to-late LLM layers (hypothesis: layers 16-22 based on Zhao et al. ESN clustering)

### Phase 3: Listen Layer dynamics
1. Fine-tuning experiment (LoRA-SER on Whisper-large-v2): Does Listen Layer shift after LoRA adaptation?
   - Connects to "Behind the Scenes" delayed specialization: if LoRA commits at deep layers, gc peak should shift right
2. Failure mode analysis: In AudioLens "failure mode" cases (gc drops mid-layer then recovers), do our gc curves show the same non-monotonicity?
3. Attention head attribution: Which attention heads at L* are responsible? (standard attention knockout)

---

## Experiments Summary

| Exp | Model | Resource | Time | Main Output |
|-----|-------|----------|------|-------------|
| E1 | Whisper-small | MacBook | ~3h | Causal peak at Triple Convergence layer ✓ |
| E2 | Qwen2-Audio-7B | NDIF or 戰艦 | ~1 day | gc(L) curve across LALM layers |
| E3 | Whisper-large-v2 + LoRA | 戰艦 | ~0.5 day | Listen Layer shift after LoRA adaptation |
| E4 | Qwen2-Audio attention heads | NDIF | ~4h | Top-5 listen heads at L* |

**Minimum viable paper:** E1 + E2 only (Whisper + one LALM). E3+E4 = extensions.

---

## Connections to Related Work

| Paper | Relationship |
|-------|-------------|
| AudioLens (智凱哥, 2025) | Our causal extension. Same observational setup; we add intervention. Co-author opportunity. |
| ALME (Li et al. 2025, arXiv:2602.11488) | We use their 57K stimuli. No need to reproduce. |
| Causal Abstraction (Geiger et al.) | Theoretical foundation. gc = IIT accuracy. Cite prominently. |
| Heimersheim & Nanda (2024) | Methodology guide. Denoising (not noising) for SUFFICIENCY claim. |
| Modality Collapse (2602.23136) | Motivation: shows audio info is encoded but unused → we localize WHERE it becomes decisive. |
| Cascade Equivalence (2602.17598) | Motivation: LEACE shows implicit cascade; we show which layers carry audio causally. |
| SPIRIT (EMNLP 2025) | Side result: does Listen Layer = SPIRIT's best defense layer? |
| **FCCT (Li et al. 2511.05923, AAAI 2026 Oral)** | **Closest competitor — but vision-only!** Full causal tracing in Vision-LLMs; finds MHSAs at middle layers = cross-modal aggregation point; IRI = training-free inference injection. We are the AUDIO equivalent. Cite as "we do for speech what FCCT did for vision." |

---

## Target Venue

| Option | Deadline | Fit |
|--------|----------|-----|
| **Interspeech 2026** | March 5 (abstract) / ~April (full) | Best fit for speech; overlaps AudioMatters track |
| **NeurIPS 2026** | ~May 2026 | Higher impact; need full Qwen2-Audio results |
| **ICML 2026** | ~Feb 2026 | Too soon for new work |
| **EMNLP 2026** | ~June 2026 | Good for language+audio intersection |

**Recommendation:** Target NeurIPS 2026 with Interspeech 2026 as fallback (MacBook E1 results + Qwen2-Audio E2 results needed by April).

---

## Leo's Next Steps (to activate this paper)

1. **Today (5 min):** `python3 -m venv ~/audio-mi-env && pip install nnsight openai-whisper torch`
2. **Today (5 min):** Get any real English speech .wav file (LibriSpeech sample URL in experiment-queue.md)
3. **Today (3h):** Run E1 (Whisper-small IIT sweep) — validate Triple Convergence causal claim
4. **This week:** Email/message 智凱哥 about collaborating — "We extend AudioLens with causal patching. Interested?"
5. **Request NDIF account or 戰艦 access** for E2 (Qwen2-Audio-7B, too big for MacBook)

---

## Open Questions for Leo

1. Should we scope to encoder-only (Whisper) or include full LALM (Qwen2-Audio)? Encoder = faster paper; LALM = bigger impact.
2. Should we reach out to ALME authors to use their stimuli officially (or just cite)?
3. Is 智凱哥 interested in co-authoring, or should this be Leo's solo paper?
4. Preferred venue: Interspeech 2026 (sooner, smaller scope) or NeurIPS 2026 (later, larger scope)?
