# LALM-KE Reading Roadmap
> Created: 2026-03-24 | Weekly checkpoint: Monday PM meeting
> Priority: P0 = must read this week | P1 = read by end of survey phase | P2 = reference/skim

---

## Phase 1 — Week 1: Foundations (Survey & Seminal)

Goal: Understand KE for LLMs deeply, and get grounded in LALMs. By Monday meeting you should be able to explain both areas.

### Knowledge Editing — Surveys & Foundations

| # | Title | Authors | Year | Link | Why Read | Priority |
|---|-------|---------|------|------|----------|----------|
| 1 | **A Survey of Knowledge Editing of Neural Networks** | Mazzi et al. (also: Yao et al. has a competing survey) | 2023 | [arxiv:2310.16218](https://arxiv.org/abs/2310.16218) | Best comprehensive survey; covers ROME, MEMIT, MEND, SERAC, IKE with unified framework | **P0** |
| 2 | **Editing Large Language Models: Problems, Methods, and Opportunities** | Yao et al. | 2023 | [arxiv:2305.13172](https://arxiv.org/abs/2305.13172) | ACL 2023 survey; defines problem formally, categorizes methods, lists benchmarks | **P0** |
| 3 | **Locating and Editing Factual Associations in GPT** (ROME) | Meng et al. | 2022 | [arxiv:2202.05262](https://arxiv.org/abs/2202.05262) | Seminal paper; introduces causal tracing + rank-1 editing; foundational for all locate-then-edit methods | **P0** |
| 4 | **Mass-Editing Memory in a Transformer** (MEMIT) | Meng et al. | 2023 | [arxiv:2210.07229](https://arxiv.org/abs/2210.07229) | Extends ROME to batch editing thousands of facts; directly applicable to LALM experiments | **P0** |

### LALM / Audio LLM — Foundations

| # | Title | Authors | Year | Link | Why Read | Priority |
|---|-------|---------|------|------|----------|----------|
| 5 | **SALMONN: Towards Generic Hearing Abilities for Large Language Models** | Tang et al. | 2023 | [arxiv:2310.13289](https://arxiv.org/abs/2310.13289) | Most cited open LALM; dual encoder (Whisper + BEATs) + Vicuna; likely target model for experiments | **P0** |
| 6 | **Qwen-Audio: Advancing Universal Audio Understanding via Unified Large-Scale Audio-Language Models** | Chu et al. | 2023 | [arxiv:2311.07919](https://arxiv.org/abs/2311.07919) | Strong commercial LALM with open weights; good alternative target for editing experiments | **P0** |
| 7 | **AudioPaLM: A Large Language Model That Can Speak and Listen** | Rubenstein et al. | 2023 | [arxiv:2306.12925](https://arxiv.org/abs/2306.12925) | Google's audio LM; understand different architectural choices | **P1** |
| 8 | **WavLLM: Towards Robust and Adaptive Speech Large Language Model** | Hu et al. | 2024 | [arxiv:2404.00656](https://arxiv.org/abs/2404.00656) [VERIFY] | Microsoft's LALM; covers robustness which connects to KE locality | **P1** |

### Interpretability Foundations (connects Leo's expertise)

| # | Title | Authors | Year | Link | Why Read | Priority |
|---|-------|---------|------|------|----------|----------|
| 9 | **Interpretability in the Wild: a Circuit for Indirect Object Identification in GPT-2** | Wang et al. | 2022 | [arxiv:2211.00593](https://arxiv.org/abs/2211.00593) | Causal tracing methodology Leo already knows; refresh for LALM extension | **P1** |
| 10 | **COUNTERFACT: Evaluating Knowledge Editing in Language Models** | Meng et al. | 2022 | [arxiv:2202.05262](https://arxiv.org/abs/2202.05262) | The standard KE benchmark; need to understand to design LALM-KE version | **P0** |

> 📌 **Note:** COUNTERFACT is part of the ROME paper (same arxiv). Read both together.

---

## Phase 2 — Weeks 2-3: Core Methods Deep Dive

Goal: Understand each major KE paradigm well enough to implement or adapt. Pick 1-2 to try on SALMONN/Qwen-Audio.

### Meta-Learning / Gradient-Based Editing

| # | Title | Authors | Year | Link | Why Read | Priority |
|---|-------|---------|------|------|----------|----------|
| 11 | **Fast Model Editing at Scale** (MEND) | Mitchell et al. | 2022 | [arxiv:2110.11309](https://arxiv.org/abs/2110.11309) | Hypernetwork learns to predict weight updates; scalable; ICLR 2022 | **P0** |
| 12 | **Editing Factual Knowledge in Language Models** (KN) | De Cao et al. | 2021 | [arxiv:2104.08164](https://arxiv.org/abs/2104.08164) | Knowledge Neurons paper; identifies fact-storing neurons; precursor to ROME's causal tracing | **P1** |
| 13 | **MALMEN: Memory-Augmented LM Editing Networks** | Tan et al. | 2023 | [arxiv:2310.00926](https://arxiv.org/abs/2310.00926) [VERIFY] | Extends MEND to batch editing; relevant for scaling up | **P2** |

### Memory-Augmented / External Memory Editing

| # | Title | Authors | Year | Link | Why Read | Priority |
|---|-------|---------|------|------|----------|----------|
| 14 | **Editing Large Language Models via Scope Classifier** (SERAC) | Mitchell et al. | 2022 | [arxiv:2206.06832](https://arxiv.org/abs/2206.06832) | Scope classifier routes queries to counterfactual model; best locality guarantees | **P0** |
| 15 | **In-Context Knowledge Editing** (IKE) | Zheng et al. | 2023 | [arxiv:2301.10405](https://arxiv.org/abs/2301.10405) | Retrieval-augmented editing via in-context examples; zero parameter change; easy to test on LALMs | **P1** |
| 16 | **GRACE: Generalized Rapid Adaptations via Codebook Editing** | Hartvigsen et al. | 2023 | [arxiv:2211.11031](https://arxiv.org/abs/2211.11031) | Discrete codebook memory; strong locality; works at inference time | **P1** |

### Evaluation & Benchmarks

| # | Title | Authors | Year | Link | Why Read | Priority |
|---|-------|---------|------|------|----------|----------|
| 17 | **Can LMs be Good Knowledge Editors? Evaluating with ZsRE** | Levy et al. | 2017 / adapted 2022 | — | Zero-shot RE benchmark; used as KE eval; understand what makes a good KE benchmark | **P1** |
| 18 | **Evaluating the Ripple Effects of Knowledge Editing in Language Models** (RippleEdits) | Cohen et al. | 2023 | [arxiv:2307.12976](https://arxiv.org/abs/2307.12976) | Tests whether edits propagate through reasoning; key for LALM-KE generality | **P0** |
| 19 | **MQuAKE: Assessing Knowledge Editing in LMs via Multi-Hop Questions** | Zhong et al. | 2023 | [arxiv:2305.14795](https://arxiv.org/abs/2305.14795) | Multi-hop editing benchmark; harder and more realistic | **P1** |

### Audio / Speech Foundations

| # | Title | Authors | Year | Link | Why Read | Priority |
|---|-------|---------|------|------|----------|----------|
| 20 | **HuBERT: Self-Supervised Speech Representation Learning by Masked Prediction of Hidden Units** | Hsu et al. | 2021 | [arxiv:2106.07447](https://arxiv.org/abs/2106.07447) | Core audio encoder used in many LALMs; understand what features it extracts | **P1** |
| 21 | **Robust Speech Recognition via Large-Scale Weak Supervision** (Whisper) | Radford et al. | 2022 | [arxiv:2212.04356](https://arxiv.org/abs/2212.04356) | Whisper is the de facto ASR encoder in most LALMs (SALMONN, WavLLM) | **P1** |
| 22 | **Dynamic-SUPERB: Towards A Dynamic, Collaborative, and Comprehensive Instructional-tuning Benchmark for Speech** | Huang et al. | 2023 | [arxiv:2309.09510](https://arxiv.org/abs/2309.09510) | From Prof. Lee's group; benchmark construction methodology useful for designing LALM-KE benchmark | **P1** |
| 23 | **SUPERB: Speech processing Universal PERformance Benchmark** | Yang et al. | 2021 | [arxiv:2105.01051](https://arxiv.org/abs/2105.01051) | Baseline audio benchmark; understand what "good audio benchmark" looks like | **P2** |
| 24 | **SpeechGPT: Empowering Large Language Models with Intrinsic Cross-Modal Conversational Abilities** | Zhang et al. | 2023 | [arxiv:2305.11000](https://arxiv.org/abs/2305.11000) | Another architecture variant; speech token LLM (different from encoder approach) | **P2** |
| 25 | **LLaSA: Large Language and Speech Assistant** | [VERIFY] | 2024 | — | Recent LALM worth knowing | **P2** |

---

## Phase 3 — Week 4+: Frontier & Intersection Papers

Goal: Find the closest existing work to LALM-KE. If it doesn't exist, that's your gap. Also cover interpretability methods applicable to multimodal settings.

### KE in Multimodal / Vision-Language Models (closest analog)

| # | Title | Authors | Year | Link | Why Read | Priority |
|---|-------|---------|------|------|----------|----------|
| 26 | **Can We Edit Multimodal Large Language Models?** | Cheng et al. | 2023 | [arxiv:2310.08475](https://arxiv.org/abs/2310.08475) | First paper to study KE in vision-language models (LLaVA etc.); most directly relevant — **read carefully** | **P0** |
| 27 | **VLKEB: A Multi-modal Knowledge Editing Benchmark** | [VERIFY] | 2024 | — | If it exists: benchmark for vision-language KE; template for audio version | **P1** |
| 28 | **UniKE: An Editing Method for Large Multimodal Models** | [VERIFY] | 2024 | — | Unified KE for multimodal models | **P1** |
| 29 | **Multimodal Knowledge Editing in LLMs** (general survey) | [VERIFY multiple recent papers on arxiv] | 2024 | — | Search arxiv for "multimodal knowledge editing" — growing area | **P1** |

### Mechanistic Interpretability in Multimodal Models

| # | Title | Authors | Year | Link | Why Read | Priority |
|---|-------|---------|------|------|----------|----------|
| 30 | **Vision-Language Models are Biased** / MI of VLMs | Various | 2023-24 | — | [VERIFY] How MI tools extend to multimodal; template for LALM MI | **P1** |
| 31 | **What Do Large Language Models Know About Physics? Extracting Knowledge from LLMs** | [VERIFY] | 2023 | — | Knowledge extraction / probing; relevant to locating audio knowledge | **P2** |
| 32 | **Finding Neurons in a Haystack: Case Studies with Sparse Probing** | Gurnee et al. | 2023 | [arxiv:2305.01610](https://arxiv.org/abs/2305.01610) | Probing method to find knowledge-storing neurons; directly applicable | **P1** |
| 33 | **Fact Verification and Evidence Finding** (knowledge probing survey) | Various | — | — | Understand probing for facts in LLMs | **P2** |

### Emerging LALM-KE Adjacent Work

| # | Title | Authors | Year | Link | Why Read | Priority |
|---|-------|---------|------|------|----------|----------|
| 34 | **Knowledge Editing for Large Language Models: A Survey** | Zhang et al. | 2024 | [arxiv:2401.01286](https://arxiv.org/abs/2401.01286) [VERIFY] | Very recent comprehensive survey; check for any multimodal section | **P0** |
| 35 | **WISE: Whitebox In-Context Editing for Large Language Models** | Wang et al. | 2024 | [arxiv:2405.14768](https://arxiv.org/abs/2405.14768) [VERIFY] | Recent hybrid method; check if applicable to multimodal | **P2** |

---

## Weekly Reading Targets

| Week | Target | Papers |
|------|--------|--------|
| **Week 1** (THIS WEEK) | Phase 1 P0s + #26 (multimodal KE) | #1, #2, #3+#10, #4, #5, #6, #26 = 7 core reads |
| **Week 2** | Phase 2 methods | #11, #14, #18, #15, #16, #34 |
| **Week 3** | Audio foundations + benchmarks | #20, #21, #22, #19, #32 |
| **Week 4** | Frontier + gap analysis | #26-35, search arXiv for latest |

---

## arXiv Search Queries (to find more papers)

```
"knowledge editing" "audio"
"knowledge editing" "speech"
"knowledge editing" "multimodal"
"LALM" OR "audio language model" "editing"
"ROME" "multimodal"
"MEMIT" "speech"
"mechanistic interpretability" "audio"
```
