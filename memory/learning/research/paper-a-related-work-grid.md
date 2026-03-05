# Paper A — Related-Work Comparison Grid
> **Purpose**: Anticipate reviewer objections ("incremental", "already done", "too similar to X")
> **Created**: 2026-03-01 (c-20260301-1445) | **Task**: Q012 | **Track**: T3

---

## 1. One-Line Differentiator

> **Our paper** (*Listen vs Guess*) is the first **causal audit** — not a defense, not a benchmark — that locates the exact layer where audio representations become *causally decisive*, using intervention (DAS + NNsight denoising patching), not correlation.

---

## 2. Comparison Table

| Dimension | **Our Method (Paper A)** | **FCCT** (Li et al. 2511.05923, AAAI 2026 Oral) | **SPIRIT** (EMNLP 2025) | **ALMGuard** (NeurIPS 2025) |
|-----------|--------------------------|--------------------------------------------------|--------------------------|------------------------------|
| **Goal** | Causal *localization* of audio consultation layer (diagnostic) | Causal tracing + training-free injection in Vision-LLMs (diagnostic + fix) | Post-hoc *defense* via inference-time activation patching against jailbreaks | Safety shortcut detection + mel-gradient guardrail input perturbation |
| **Modality** | Speech / Audio LLMs | Vision-Language Models (images) | Speech Language Models | Audio-Language Models |
| **Method core** | DAS + NNsight denoising patching; gc(L) = IIT accuracy per layer | Feature extraction → causal tracing → IRI (Inference-time Representation Injection) | Activation patching, bias addition, neuron pruning at inference time | Shortcut Activation Perturbations (SAP) + mel-gradient sparse mask |
| **Causal/interventional?** | ✅ Yes — IIT accuracy (DAS, Geiger et al.) | ✅ Yes — causal tracing (attribution-based) | ⚠️ Partial — patches activations but does not measure causal effect size | ❌ No — identifies "shortcuts" via gradient, not interventional |
| **Layer-wise sweep** | ✅ Full PROBE_LAYER × INTERVENE_LAYER 2D sweep | ⚠️ Layer attribution but no systematic IIA sweep | ⚠️ Tests specific layers, not systematic | ❌ No layer-wise audit |
| **Metric** | gc(L) = normalized IIT accuracy (theoretically grounded in IIT / Geiger et al. 2301.04709) | Layer attribution score | Jailbreak bypass rate reduction (up to 99%) | Jailbreak success rate (avg 4.6% with guardrail) | 
| **Training-free** | ✅ (test-time patching only) | ✅ (IRI is inference-time) | ✅ | ✅ |
| **Stimuli** | ALME 57K audio-text conflict pairs + Choi et al. phonological minimal pairs | VQA / visual reasoning benchmarks | Imperceptible-noise speech jailbreaks | Audio jailbreak prompts, 4 models |
| **Main output** | gc(L) curve → L* (Listen Layer) = interpretable diagnostic map | IRI vectors for targeted model correction | Hardened speech LM (jailbreak-robust) | Guardrail filtering harmful audio | 
| **Paper A relation** | **Core contribution** | Closest technical sibling (vision); we are the speech equivalent | We provide the *why* (where) that enables SPIRIT-style patches to be principled | We provide causal audit; ALMGuard provides downstream fix |

---

## 3. Reviewer Objection Matrix

| Objection | Why It Fails Against Us |
|-----------|------------------------|
| "SPIRIT already does layer-level patching in speech LMs" | SPIRIT patches layers to *reduce jailbreak success* (defense). We measure *causal effect size per layer* (gc = IIT accuracy) to identify *why* certain layers matter. SPIRIT doesn't show which layer is causally decisive — it tries multiple and takes what works. Our audit provides the principled basis for choosing where to patch. |
| "This is just FCCT applied to audio" | FCCT targets vision-language models, uses feature-attribution causal tracing, and proposes IRI for intervention. We target speech LLMs, use DAS + NNsight denoising patching, and measure IIT accuracy (not attribution scores). The methodological pipeline differs. FCCT = "what features drive vision tokens?" We = "which layer makes audio causally decisive?" |
| "ALMGuard already finds safety shortcuts in audio models" | ALMGuard finds *input-level* shortcuts (mel-gradient SAP) to trigger safety behaviors — it's an intervention tool, not a layer-diagnostic. It does not identify at which layer safety-relevant audio representations become causally active. Our gc(L) curve provides exactly this layer-resolution audit. |
| "Incremental: just another modality transfer of causal tracing" | FCCT is vision; interpretability work for audio LLMs is nearly absent. More importantly: audio cross-attention (encoder → LLM) is architecturally distinct from visual patch tokens → MHSAs. Circuit-tracer (CLT) cannot handle cross-attention; we need NNsight. The Listen Layer is a concept with no prior operationalization in speech. |
| "Not enough novelty vs AudioLens" | AudioLens (智凱哥, our labmate) is **observational** (logit-lens). We add causal interventions (DAS patching). We go from "audio representations are present" → "audio representations are causally decisive at layer L*." That's the full mechanistic step. |

---

## 4. Positioning Statement (for Related Work section draft)

> Prior work characterizes audio-vs-text dominance **behaviorally** (ALME; AudioLens) or provides **inference-time defenses** (SPIRIT; ALMGuard) without pinpointing *where* in the forward pass audio information becomes causally decisive.  
> FCCT demonstrates causal tracing in Vision-LLMs and proposes inference-time repair — but vision encoders (patch tokens → cross-attention MHSAs) differ structurally from speech encoders (waveform → Whisper encoder → connector → LLM decoder), and circuit-level tools (CLT) do not support audio cross-attention.  
> We introduce the **Listen Layer** — the first *causally grounded*, layer-resolved localization of audio consultation in speech LLMs — using DAS + NNsight denoising patching on 57K audio-text conflict stimuli, with gc(L) (IIT accuracy, Geiger et al. 2301.04709) as the intervention metric.  
> Our diagnostic complements both SPIRIT (principled layer selection for activation patching) and ALMGuard (causal grounding for shortcut identification), while serving as the audio analogue to FCCT.

---

## 5. Citation Cluster (for Related Work section)

```
[Causal foundation]
- Geiger et al. 2301.04709 — Causal Abstraction / IIT accuracy (gc definition)
- Heimersheim & Nanda 2024 — Denoising patching for sufficiency

[Direct audio prior work]
- AudioLens (智凱哥, 2025) — observational layer analysis (we extend causally)
- ALME (Li et al. arXiv:2602.11488) — stimuli source (57K conflict pairs)
- Modality Collapse (2602.23136) — motivation: audio encoded but unused
- Cascade Equivalence (2602.17598) — LEACE implicit cascade

[Closest competitors — must cite + differentiate]
- FCCT (Li et al. 2511.05923, AAAI 2026 Oral) — causal tracing in Vision-LLMs
- SPIRIT (EMNLP 2025) — layer-level activation patching for speech safety
- ALMGuard (NeurIPS 2025) — safety shortcut detection for audio LMs

[Supporting / context]
- JALMBench (ICLR 2026) — jailbreak benchmark for audio LMs
- SACRED-Bench + SALMONN-Guard — compositional audio attacks
```

---

## 6. What Q008-Q010 Should Fill In

Reading SPIRIT, ALMGuard, SACRED-Bench (Q008-Q010) will let us:
1. Add exact architecture details to the comparison table (column 3 & 4)
2. Confirm SPIRIT's "best defense layer" position → test if it matches our L*
3. Map ALMGuard's shortcut localization to gc(L) — are they finding the same layers?
4. Add attack taxonomy from SACRED-Bench to T5 stimuli design

→ **Update this file after Q008-Q010 are done.**
