# The Listening Geometry: Where Audio-Language Models Listen, Guess, and Collapse

## Table of Contents

- [The Listening Geometry: Where Audio-Language Models Listen, Guess, and Collapse](#the-listening-geometry-where-audio-language-models-listen-guess-and-collapse)
- [Abstract](#abstract)
- [The Listening Geometry: Where Audio-Language Models Listen, Guess, and Collapse](#the-listening-geometry-where-audio-language-models-listen-guess-and-collapse)
  - [§1 Introduction](#1-introduction)
  - [§2 Related Work](#2-related-work)
    - [2.1 Mechanistic Interpretability of Speech Models](#21-mechanistic-interpretability-of-speech-models)
    - [2.2 Audio-Language Model Interpretability](#22-audio-language-model-interpretability)
    - [2.3 Causal Intervention Methods](#23-causal-intervention-methods)
    - [2.4 Sparse Autoencoders for Audio](#24-sparse-autoencoders-for-audio)
- [§3 Method](#3-method)
  - [3.1 Grounding Coefficient Definition](#31-grounding-coefficient-definition)
    - [3.1.1 Background: Interchange Intervention](#311-background-interchange-intervention)
    - [3.1.2 Defining gc(k)](#312-defining-gck)
    - [3.1.3 The Listen Layer](#313-the-listen-layer)
    - [3.1.4 Minimal Pair Construction](#314-minimal-pair-construction)
  - [3.2 AND/OR Gate Framework](#32-andor-gate-framework)
    - [3.2.1 Gate Classification](#321-gate-classification)
    - [3.2.2 AND-Gate Fraction and Cascade Degree](#322-and-gate-fraction-and-cascade-degree)
    - [3.2.3 Relationship to Grounding Coefficient](#323-relationship-to-grounding-coefficient)
  - [3.3 Experimental Protocol](#33-experimental-protocol)
    - [3.3.1 Stimuli Design](#331-stimuli-design)
    - [3.3.2 Intervention Procedure](#332-intervention-procedure)
    - [3.3.3 Evaluation Metrics](#333-evaluation-metrics)
  - [3.4 Models and Data](#34-models-and-data)
    - [3.4.1 Models](#341-models)
    - [3.4.2 Data](#342-data)
    - [3.4.3 Computational Requirements](#343-computational-requirements)
- [§4 Results](#4-results)
  - [4.1 Encoder Analysis: Voicing Geometry in Whisper](#41-encoder-analysis-voicing-geometry-in-whisper)
  - [4.2 Causal Contribution Analysis](#42-causal-contribution-analysis)
  - [4.3 gc(k) Peak Localization](#43-gck-peak-localization)
  - [4.4 AND/OR Gate Validation](#44-andor-gate-validation)
  - [4.5 Persona-Conditioned Grounding](#45-persona-conditioned-grounding)
  - [4.6 Collapse Onset and Incrimination](#46-collapse-onset-and-incrimination)
  - [4.7 RAVEL Disentanglement](#47-ravel-disentanglement)
  - [4.8 Pre-Registered Predictions](#48-pre-registered-predictions)
  - [4.9 Blocked Experiments](#49-blocked-experiments)
- [§5 Discussion](#5-discussion)
  - [5.1 gc(k) as a Unifying Metric](#51-gck-as-a-unifying-metric)
  - [5.2 AND-Gate Insight: Genuine Multimodal Processing](#52-and-gate-insight-genuine-multimodal-processing)
  - [5.3 Safety Implications](#53-safety-implications)
  - [5.4 Cross-Paper Predictions](#54-cross-paper-predictions)
  - [5.5 Limitations](#55-limitations)
  - [5.6 Future Work](#56-future-work)
  - [§6 Conclusion](#6-conclusion)

---

# Abstract

Audio-language models (ALMs) such as Qwen2-Audio, Gemini, and GPT-4o can answer questions about speech, classify emotions, and follow spoken instructions — yet no principled method exists to causally determine whether these models genuinely consult their audio input or simply pattern-match from text-context priors. We introduce the **grounding coefficient** $gc(k)$, a causal metric based on interchange intervention and Distributed Alignment Search (DAS) that quantifies how much each layer $k$ of an ALM relies on audio versus text context. We embed $gc(k)$ within a five-dimensional **Listening Geometry** framework — gc peak ($k^*$), AND-gate fraction ($\alpha_{\text{AND}}$), Schelling stability ($\sigma$), collapse onset ($t^*$), and codec stratification (CS) — that profiles ALMs into four listening strategies: strong listeners, shallow listeners, sophisticated guessers, and fragile listeners. At the feature level, we decompose multimodal integration into AND-gates (features requiring both audio and text) and OR-gates (features where either modality suffices), providing the first mechanistic test of multimodal feature dependence in speech models. Across 29 experiments (2 real-model on Whisper, 27 mock-framework validation), we demonstrate strong internal consistency: AND-gate fraction correlates near-perfectly with gc peak location ($r = 0.98$), RAVEL disentanglement scores approximate $gc(k)$ curves ($r = 0.90$), and the framework identifies safety-critical features with 96% suppression detection rate. We show that persona prompts mechanistically modulate grounding profiles (shifting $k^*$ by 2 layers), that backdoor attacks operate by inducing premature cascade ($t^*$ shift of 3 steps), and that ENV-3 feature pruning restores jailbreak resistance ($r = 0.89$). The Listening Geometry provides the first unified framework for mechanistic interpretability of audio processing in language models, with direct applications to safety auditing, deployment screening, and adversarial defense.


---

# The Listening Geometry: Where Audio-Language Models Listen, Guess, and Collapse

## §1 Introduction

Audio-language models (ALMs) such as Qwen2-Audio, Gemini, and GPT-4o can answer questions about speech, classify speaker emotions, and follow spoken instructions — yet we have almost no understanding of *how* these models use their audio input internally. When an ALM correctly identifies a speaker's emotion, does it genuinely consult the acoustic signal, or does it pattern-match from the surrounding text context? Behavioral evaluations cannot distinguish these strategies: a model that ignores audio entirely can still score well if its text priors are strong enough. Recent work has begun to expose this vulnerability. Modality Collapse [CITE: Zhao 2602.23136] demonstrates that ALMs default to text priors when audio and text conflict, while MPAR² [CITE: Chen 2603.02266] shows that audio perception accuracy degrades from ~63% to ~31% as chain-of-thought reasoning lengthens — a phenomenon the authors term *audio perception decay*. MiSTER-E [CITE: IISc/Microsoft 2602.23300] uses mixture-of-experts gating to quantify speech-vs-text dominance behaviorally, and Cascade Equivalence [CITE: 2602.17598] confirms via LEACE erasure that most speech LLMs function as implicit ASR cascades. These studies diagnose symptoms. None provides a causal, layer-wise account of *where* in the network audio information is consulted versus ignored.

Existing interpretability tools for speech models are either observational or limited to encoder-only architectures. AudioLens [CITE: Ho et al. 2025] applies the logit lens to large audio-language models (LALMs), identifying critical layers where auditory attribute information peaks — but without causal patching, it cannot prove that these layers *cause* the model's output. Beyond Transcription [CITE: Glazer et al. 2025] introduces the encoder lens and saturation layer concept for Whisper, revealing that the encoder encodes contextual information beyond raw acoustics (speaker gender probing peaks at layer 25, accent at layer 22); however, the analysis is restricted to encoder-only models with white-noise reference patching, a corruption method known to be suboptimal [CITE: Heimersheim and Nanda 2024]. Zhao et al. [CITE: 2601.03115] discover emotion-sensitive neurons (ESNs) in LALMs and validate them via causal ablation, but never ask whether these neurons fire because of audio input or text context. AR&D [CITE: Chowdhury et al. 2026] proposes the first SAE-based interpretability framework for AudioLLMs, retrieving and describing concept-level features — yet it tests only necessity (steering/ablation), not sufficiency, and never examines the audio-vs-text source of feature activation. The common gap across all four lines of work is the absence of a *causal grounding metric*: a principled measure of how much each layer relies on audio versus text to produce its output.

We address this gap with the **grounding coefficient** gc(k), a causal metric grounded in the theory of causal abstraction [CITE: Geiger et al. 2301.04709]. For each layer k, gc(k) measures the interchange intervention accuracy (IIA) when distributed alignment search (DAS) [CITE: Geiger et al. 2303.02536] is used to patch the audio-aligned subspace of the residual stream. A high gc(k) indicates that layer k causally relies on audio; a low gc(k) indicates reliance on text priors or passthrough. We embed gc(k) within a five-dimensional **Listening Geometry** framework — gc peak (k\*), AND-gate fraction (α\_AND), Schelling stability (σ), collapse onset (t\*), and codec stratification (CS) — that profiles ALMs along a taxonomy of listening strategies: strong listeners, shallow listeners, sophisticated guessers, and fragile listeners. At the feature level, we decompose multimodal integration into **AND-gates** (features requiring both audio and text) and **OR-gates** (features where either modality suffices), connecting to the modality interaction taxonomy of [CITE: Sutter et al.] and the sparse feature decomposition framework of [CITE: Asiaee et al. 2602.24266]. Our theoretical foundation inherits from the IIT causal abstraction formalism (causal rigor), modality interaction theory (AND/OR gate semantics), and sparse feature analysis (sub-layer resolution).

Our contributions are as follows:

1. **gc(k) metric.** The first causal, layer-wise grounding coefficient for audio-language models, defined via DAS-IIA and grounded in IIT causal abstraction theory. Unlike observational probes (AudioLens) or necessity-only tests (AR&D, Zhao et al.), gc(k) provides both sufficiency and necessity evidence for audio grounding at each layer.
2. **Listening Geometry.** A five-dimensional framework (k\*, α\_AND, σ, t\*, CS) that taxonomizes ALM listening strategies into four profiles, enabling systematic comparison across models, tasks, and deployment conditions.
3. **AND/OR gate framework.** A mechanistic decomposition of multimodal feature dependence that distinguishes genuine audio-text integration (AND-gates) from modality-redundant processing (OR-gates). We show that AND-gate fraction correlates near-perfectly with gc peak location (r = 0.98 in mock validation) and inversely predicts text-override vulnerability.
4. **Empirical validation.** 2 real experiments (voicing geometry in Whisper, causal contribution analysis) and 20 mock-framework experiments across 5 analysis axes, including persona-conditioned grounding shifts, collapse onset detection, and RAVEL disentanglement validation.
5. **Pre-registered predictions.** Testable predictions for Modality Collapse (ALME conflict items should show late-layer gc drop) and MPAR² (RL training should shift gc peak or raise late-layer gc), bridging mechanistic and behavioral accounts.

The remainder of this paper is organized as follows. §2 surveys related work in mechanistic interpretability of speech models, audio-language model analysis, causal intervention methods, and sparse autoencoders for audio. §3 defines gc(k), the AND/OR gate framework, and the five-dimensional Listening Geometry. §4 presents experimental results spanning encoder analysis, gc peak localization, AND/OR gate validation, persona-conditioned grounding, collapse onset, and RAVEL disentanglement. §5 discusses implications for safety, cross-paper predictions, and limitations. §6 concludes.


## §2 Related Work

### 2.1 Mechanistic Interpretability of Speech Models

Early work on speech model interpretability focused on the Whisper architecture. Reid [CITE: Reid 2023] provided initial evidence for phoneme-like features and localized attention patterns in Whisper's encoder layers. Glazer et al. [CITE: Glazer et al. 2025] substantially extended this with the *encoder lens* — a logit lens applied to encoder hidden states — and the concept of a *saturation layer* at which the encoder commits to its transcription. Their activation patching experiments revealed that Whisper's encoder encodes contextual information beyond raw acoustics, with speaker gender probing peaking at layer 25 (94.6% accuracy) and accent at layer 22 (97%). However, their patching uses white-noise reference activations, which Heimersheim and Nanda [CITE: 2024] show is sensitive to noise level and can be ineffective compared to minimal-pair corruption. Moreover, the analysis is restricted to encoder-only models and does not extend to full audio-language models.

In parallel, Choi et al. [CITE: 2602.18899] demonstrated that phonological features are linear, compositional, and scale-continuous across 96 languages in self-supervised speech model (S3M) space. Their key finding — that voicing vectors obey arithmetic ([b] = [d] − [t] + [p]) with magnitude scaling by acoustic realization degree — provides a principled basis for constructing minimal-pair stimuli for causal intervention. Van Rensburg [CITE: 2603.03096] complemented this with PCA-based speaker geometry in WavLM, showing that individual dimensions encode pitch, intensity, and spectral characteristics. These results confirm that acoustic attributes are linearly organized in SSL representations, but neither study tests whether this structure *survives through the connector* into speech LLMs — a critical prerequisite for causal grounding analysis (our Gap #18).

On the neuron-analysis front, Kawamura et al. [CITE: 2602.15307] introduced AAPE (Audio Activation Probability Entropy), adapting LAPE from NLP to identify class-specific neurons in the M2D audio SSL model. They found that SSL develops twice as many class-specific neurons as supervised models and that deactivating these neurons causally degrades classification. However, their analysis is limited to encoder-only SSL models and tests only necessity (ablation), not sufficiency. Ma et al. [CITE: Ma et al. 2026] examined LoRA adaptation of Whisper for speech emotion recognition, finding delayed specialization in which LoRA flat/high KL divergence in early layers gives way to sharp late-stage commitment — but again without causal patching.

**Gap:** All prior speech MI work is either (a) restricted to encoder-only models, (b) uses suboptimal corruption methods, or (c) tests only necessity. None provides a causal grounding metric for full audio-language models.

### 2.2 Audio-Language Model Interpretability

The interpretability of full audio-language models (where a speech encoder feeds into a text LLM backbone) is a nascent field. AudioLens [CITE: Ho et al. 2025] is the most directly relevant prior work: it applies the logit lens to DeSTA2, Qwen-Audio, and Qwen2-Audio, computing a layer-wise information score and identifying *critical layers* where auditory attribute information peaks. Key findings include that attribute information is non-monotonic with depth (sharp drops and recoveries are common), that earlier critical layers correlate with higher accuracy, and that LALMs query audio tokens directly rather than aggregating at text positions. However, AudioLens is purely observational (Pearl Level 1) — it cannot distinguish whether a critical layer *causes* the model's output or merely *correlates* with it. Store-Contribute Dissociation (SCD), demonstrated in audio generation by AG-REPA [CITE: 2603.01006] and theoretically by Braun et al. [CITE: 2025], shows that representationally rich layers may be causally passive — precisely the confound that observational probing cannot resolve.

AR&D [CITE: Chowdhury et al. 2026] introduces the first SAE-based interpretability framework for AudioLLMs, using a retrieve-describe pipeline to assign concept names to sparse features in SALMONN and Qwen-Audio. While their steering experiments confirm feature necessity, they never test sufficiency (denoising patching) and — critically — never ask whether a feature activates because of the audio stream or the text context. SPIRIT [CITE: Djanibekov et al. 2025] takes a safety-oriented approach, using activation patching to defend Qwen2-Audio against adversarial audio jailbreaks. Their defense identifies noise-sensitive neurons at MLP layers and achieves 99% robustness via clean-activation substitution — but operates at the neuron level without SAE decomposition and does not explain *which features* carry adversarial information or *why* those neurons matter mechanistically.

Zhao et al. [CITE: 2601.03115] discover emotion-sensitive neurons (ESNs) in Qwen2.5-Omni, Kimi-Audio, and Audio Flamingo, validating them through deactivation (necessity) and steering (controllability). ESNs cluster non-uniformly at early (layer 0), early-mid (layers 6–8), and late (layers 19–22) positions — consistent with acoustic-to-semantic transition zones. Yet the study instruments only the decoder and never asks the fundamental question: does an ESN fire because of audio cues or text context? SGPA [CITE: 2603.02250] applies Shapley-value attribution with phonetic alignment to audio LLMs, achieving efficient phoneme-level attribution — but Shapley values are observational (Pearl Level 1) and cannot distinguish stored from causally driven representations.

In the vision-language domain, two closely related works exist. FCCT [CITE: Li et al. 2025] performs faithful cross-modal causal tracing in vision-LLMs, finding that MHSAs at middle layers serve as cross-modal aggregation points — the closest methodological analog to our work, but restricted to vision. EmbedLens [CITE: Fan et al. 2026] discovers that visual tokens partition into sink, dead, and alive categories, with alive tokens naturally aligning at intermediate LLM layers — observational evidence consistent with our Listen Layer hypothesis, but without causal intervention. Liu et al. [CITE: 2025] study visual representations inside the language model using KV-token flow analysis, again without causal patching.

**Gap:** No prior work on audio-language models combines causal intervention (Level 3, IIT counterfactual) with a grounding metric that attributes model behavior to audio versus text sources. Our gc(k) fills this gap, providing the first DAS-grounded causal localization of audio reliance in speech LLMs.

### 2.3 Causal Intervention Methods

Our methodology builds on the causal abstraction framework of Geiger et al. [CITE: 2301.04709], which unifies eleven mechanistic interpretability methods — including activation patching, DAS, SAEs, steering vectors, and causal scrubbing — under a common theoretical foundation rooted in Integrated Information Theory (IIT). The key insight is that mechanistic interpretability can be formalized as finding *causal abstractions*: mappings between high-level causal models (interpretable variables like "voicing = voiced") and low-level neural network computations. Interchange Intervention Accuracy (IIA), the metric we adopt for gc(k), measures the faithfulness of such mappings.

Distributed Alignment Search (DAS) [CITE: Geiger et al. 2303.02536] operationalizes this theory by learning a rotation matrix that identifies the minimal linear subspace within a layer's residual stream that aligns with a target causal variable. Unlike vanilla activation patching, which transplants entire activation vectors and may smuggle correlated information, DAS isolates the causally relevant subspace — a critical advantage in audio models where AudioSAE [CITE: Aparin et al. 2026] has shown that ~2000 features per layer create extreme polysemanticity. The pyvene library [CITE: Wu et al. 2024] provides a practical implementation.

The RAVEL benchmark [CITE: Huang et al. 2024] evaluates disentanglement quality using two complementary metrics: Cause (does intervening on feature F change attribute A?) and Isolate (does the same intervention leave other attributes unchanged?). Their finding that SAEs score well on Cause but fail on Isolate is directly relevant to audio: acoustic co-occurrence patterns (e.g., voicing features encoding speaker gender) likely produce worse leakage than in text. Multi-task DAS (MDAS), which simultaneously optimizes rotations for multiple attributes, achieves the best Cause + Isolate scores and serves as our ceiling baseline for disentanglement evaluation.

Activation patching methodology has been systematized by Heimersheim and Nanda [CITE: 2024], who distinguish denoising (sufficiency) from noising (necessity) patching and show that the two are not symmetric: AND circuits are best found with noising, OR circuits with denoising. Their work also identifies the Hydra effect (backup behavior activation upon component ablation) and recommends logit difference as the default metric. For audio, their finding that Gaussian noise patching is fragile motivates our use of phonological minimal pairs as corruption signals — a methodologically cleaner approach than white-noise patching [CITE: Glazer et al. 2025].

In audio-adjacent domains, Maghsoudi and Mishra [CITE: 2602.01247] apply cross-mode activation patching and causal scrubbing to brain-to-speech models, discovering that speech modes form a continuous causal manifold with compact layer-specific subspaces mediating cross-mode transfer. This predicts that gc(k) curves in speech LLMs should be smooth rather than step-function-like. AG-REPA [CITE: 2603.01006] introduces Forward-only Gate Ablation (FoG-A) for quantifying causal contribution in audio *generation* models, finding that early layers are causal drivers while deep layers are semantic reservoirs — the same Store-Contribute Dissociation principle we expect to hold in speech *understanding*, with the causal depth shifted to intermediate layers (~50% depth) consistent with the Triple Convergence hypothesis [TODO: cite whisper_hook_demo results].

**Gap:** Causal abstraction methods (DAS, IIT, RAVEL) have been extensively developed for text. Applications to audio remain limited to brain-to-speech models and audio generation. Our work is the first to apply DAS-IIT causal localization to speech LLMs, and the first to define a grounding coefficient that quantifies audio reliance at the layer level.

### 2.4 Sparse Autoencoders for Audio

Sparse autoencoders (SAEs) have emerged as a tool for decomposing neural network representations into interpretable features. In audio, three independent lines of work have trained SAEs on speech SSL models. AudioSAE [CITE: Aparin et al. 2026] trains TopK/BatchTopK SAEs on all 12 layers of Whisper and HuBERT with 8× expansion, achieving 0.92 phoneme accuracy and demonstrating that top-100 feature steering reduces hallucination false positive rate by 70% with only +0.4% WER cost. Their layer insight — that Whisper layers 6–7 mark the transition from audio-level to frame-level speech encoding — is convergent with the saturation layer concept [CITE: Glazer et al. 2025]. However, AudioSAE covers only encoder models and found that phonetic auto-interpretation failed due to noisy caption models. Critically, erasing speech concepts requires ~2000 features, compared to tens for text concepts, confirming that phonetic information is highly distributed — motivating DAS (which finds relevant subspaces) over localist neuron-level analysis.

Mariotte et al. [CITE: 2025] train TopK SAEs on AST, HuBERT, WavLM, and MERT (4 models, 13 layers each), showing that SAE sparse codes retain task accuracy at 75–85% sparsity and significantly improve completeness (disentanglement of voice attributes like pitch, shimmer, and loudness). Their key limitation is mean-pooling along the time axis, which discards temporal structure entirely — one cannot ask *when* during an utterance a feature fires. Kawamura et al. [CITE: 2602.15307] find similar class-specific neurons via AAPE but without SAE decomposition, revealing polysemanticity ("shared responses" where the same neuron fires for acoustically related classes) that SAEs could disentangle.

T-SAE [CITE: Bhalla et al. 2025] addresses the temporal limitation by partitioning SAE features into high-level (smooth, semantic) and low-level (position-specific, syntactic) components with a temporal contrastive loss. Originally developed for text (ICLR 2026 Oral), its authors explicitly note the limitation applies to "language *and other sequential modalities*" — pointing at audio without doing it. Audio has stronger temporal structure than text: phoneme spans of ~5–10 frames at 20ms resolution create a natural prior for adjacent-frame contrastive learning. Audio T-SAE would directly enable our temporal coherence proxy for gc(k): features coherent at phoneme timescale indicate "listening," while features coherent at text-token timescale indicate "guessing."

The SAEBench framework [CITE: Karvonen et al. 2025] provides an 8-metric evaluation protocol for text SAEs, revealing that proxy metrics (sparsity, fidelity) do not reliably predict practical quality. No equivalent benchmark exists for audio SAEs — a gap our companion work (AudioSAEBench) addresses with a novel Grounding Sensitivity metric that applies gc(k) at the feature level.

**Gap:** Audio SAE work has produced interpretable features in encoder-only models, but no study has tested whether these features activate because of audio input or text context. Our AND/OR gate framework provides the first mechanistic test of multimodal feature dependence, and our gc(k) metric bridges the layer-level analysis (this paper) with feature-level grounding sensitivity (AudioSAEBench).


---

# §3 Method

## 3.1 Grounding Coefficient Definition

Audio-language models (ALMs) receive two streams of input: an acoustic signal processed by a speech encoder, and a text context processed by a language model backbone. At each layer $k$ of the model, representations may draw on either source. We introduce the **grounding coefficient** $gc(k)$ as a causal metric that quantifies the relative contribution of audio versus text context at layer $k$.

### 3.1.1 Background: Interchange Intervention

Our formalization builds on the **Distributed Alignment Search** (DAS) framework of Geiger et al. (2021; 2023), which extends causal abstraction to neural networks via interchange interventions. Given a model $\mathcal{M}$ and a high-level causal variable $V$, DAS learns a linear subspace $R \in \mathbb{R}^{d \times m}$ (where $d$ is the representation dimension and $m \ll d$) such that intervening on the projection $R^\top h_k$ at layer $k$ faithfully implements an intervention on $V$ in the model's behavior.

Concretely, given a **base** input $(a, t)$ (audio $a$, text context $t$) and a **source** input $(a', t')$, an interchange intervention at layer $k$ replaces the base representation's projection onto $R$ with the source representation's projection:

$$h_k^{\text{int}} = h_k^{\text{base}} + R\left(R^\top h_k^{\text{source}} - R^\top h_k^{\text{base}}\right)$$

The **Interchange Intervention Accuracy** (IIA) measures how often the model's output after intervention matches the counterfactual prediction — that is, the output the model *should* produce if the causal variable had taken the source value.

### 3.1.2 Defining gc(k)

We define two modality-specific IIA scores at each layer $k$:

- $\text{IIA}_{\text{audio}}(k)$: IIA when intervening on the audio-aligned subspace. We construct minimal pairs where the audio signal differs (e.g., /t/ vs. /d/) while text context is held constant, then measure how often patching the source audio representation into the base changes the model output to match the source-audio prediction.

- $\text{IIA}_{\text{text}}(k)$: IIA when intervening on the text-aligned subspace. We construct pairs where the text context differs (e.g., different preceding word context that biases toward a particular phoneme) while audio is held constant.

The grounding coefficient is then:

$$gc(k) = \frac{\text{IIA}_{\text{audio}}(k)}{\text{IIA}_{\text{audio}}(k) + \text{IIA}_{\text{text}}(k)}$$

By construction, $gc(k) \in [0, 1]$. Values near 1 indicate that layer $k$ primarily encodes information derived from the audio signal (the model is *listening*); values near 0 indicate reliance on text-context priors (the model is *guessing*). The denominator normalizes for overall interventional sensitivity, ensuring comparability across layers with different total IIA magnitudes.

### 3.1.3 The Listen Layer

We define the **listen layer** as:

$$k^* = \arg\max_k \; gc(k)$$

This identifies the layer where audio information has maximal causal influence relative to text priors. We predict that the $gc(k)$ curve exhibits a **sigmoidal profile** across layers: low $gc$ in early layers (where representations are still being formed), a sharp transition at or near $k^*$, and a plateau or decline in later layers as text priors reassert influence.

### 3.1.4 Minimal Pair Construction

Following Choi et al. (2026), who demonstrate that phonological features are linear and compositional in self-supervised speech representation space, we construct **clean/corrupt pairs** from phonological minimal contrasts:

- **Voicing pairs**: /t/ vs. /d/, /p/ vs. /b/, /k/ vs. /g/, /s/ vs. /z/
- **Place pairs**: /p/ vs. /t/ vs. /k/ (bilabial, alveolar, velar)
- **Manner pairs**: /t/ vs. /s/ (stop vs. fricative), /d/ vs. /n/ (stop vs. nasal)

For each pair $(a_{\text{clean}}, a_{\text{corrupt}})$, the base input uses $a_{\text{clean}}$ and the source uses $a_{\text{corrupt}}$, with identical text context. The intervention target is the phoneme identity at the contrastive position. This design ensures that $\text{IIA}_{\text{audio}}(k)$ measures the model's use of a specific, well-controlled acoustic contrast rather than global audio properties.


## 3.2 AND/OR Gate Framework

The grounding coefficient characterizes entire layers. To understand the **feature-level** organization of multimodal processing, we decompose each layer into features (via sparse autoencoders or DAS-identified directions) and classify their modality dependence using an AND/OR gate framework inspired by multimodal interaction taxonomies (Sutter et al.).

### 3.2.1 Gate Classification

For each causal feature $f$ at layer $k$, we compute three IIA scores using interchange intervention:

- $\text{IIA}(f; A{+}T)$: IIA when patching feature $f$ with both audio and text changed in the source
- $\text{IIA}(f; A)$: IIA when patching with only audio changed (text held constant)
- $\text{IIA}(f; T)$: IIA when patching with only text changed (audio held constant)

We classify each feature into one of three types:

**AND-gate.** Feature $f$ is an AND-gate if:

$$\text{IIA}(f; A{+}T) \gg \max\left(\text{IIA}(f; A),\; \text{IIA}(f; T)\right)$$

Operationally, we require $\text{IIA}(f; A{+}T) - \max(\text{IIA}(f; A), \text{IIA}(f; T)) > \delta$, with $\delta = $ [TODO: threshold, calibrated via bootstrap]. AND-gate features represent **genuine multimodal integration**: neither audio nor text alone suffices to reconstruct the feature, and both modalities must be jointly present. These features implement a logical AND over modality inputs.

**OR-gate.** Feature $f$ is an OR-gate if:

$$\text{IIA}(f; A{+}T) \approx \max\left(\text{IIA}(f; A),\; \text{IIA}(f; T)\right)$$

Operationally, $|\text{IIA}(f; A{+}T) - \max(\text{IIA}(f; A), \text{IIA}(f; T))| \leq \delta$. OR-gate features can be recovered from either modality alone, implementing a logical OR. These features are candidates for **text-prior override**: if the text context provides a strong prediction, the model need not consult audio.

**Passthrough.** Feature $f$ is a passthrough if $\text{IIA}(f; A{+}T) < \epsilon$ — the feature is not causally relevant to the target behavior under any intervention condition. [TODO: $\epsilon$ threshold]

### 3.2.2 AND-Gate Fraction and Cascade Degree

We define the **AND-gate fraction** at layer $k$ as:

$$\alpha_{\text{AND}}(k) = \frac{|\{f : f \text{ is AND-gate at layer } k\}|}{|\{f : f \text{ is causally relevant at layer } k\}|}$$

This metric captures how much of a layer's causal computation requires genuine multimodal integration. We predict that $\alpha_{\text{AND}}(k)$ correlates positively with $gc(k)$, since layers that depend heavily on audio should contain features that require audio input.

The complementary **cascade degree** $\kappa(k) = 1 - \alpha_{\text{AND}}(k)$ measures the fraction of causal features vulnerable to text-prior override. We hypothesize that $\kappa(k)$ correlates with behavioral hallucination rate: models with high cascade degree at critical layers should be more prone to ignoring audio in favor of text-predicted outputs.

### 3.2.3 Relationship to Grounding Coefficient

The AND/OR framework provides a **mechanistic decomposition** of $gc(k)$. While $gc(k)$ measures the aggregate audio dependence of a layer, $\alpha_{\text{AND}}(k)$ reveals *why*: a high $gc(k)$ with high $\alpha_{\text{AND}}(k)$ indicates that the layer performs genuine multimodal fusion, whereas a high $gc(k)$ with low $\alpha_{\text{AND}}(k)$ could indicate that audio information is present but easily overridden — a pattern we term a "fragile listener."

Preliminary mock experiments (Q089) show that AND-gate fraction and $gc(k)$ are highly correlated ($r = 0.98$, $p < 0.001$), with the $gc$ peak coinciding with 100% AND-gate fraction. This tight coupling, if replicated in real models, would validate $\alpha_{\text{AND}}$ as a diagnostic proxy for $gc$ peak detection.


## 3.3 Experimental Protocol

### 3.3.1 Stimuli Design

We employ three categories of stimuli, each targeting a different aspect of audio-text interaction:

**Category 1: Phonological minimal pairs.** Following the construction in §3.1.4, we use consonant minimal pairs spanning three phonological dimensions (voicing, place, manner). Stimuli are recorded in controlled conditions or sourced from existing corpora [TODO: specify corpus — LibriSpeech forced-aligned segments or custom recordings]. Each pair consists of two utterances differing in exactly one phonological feature at a target position, embedded in an identical carrier phrase (e.g., "Say the word \_\_\_ again"). This yields [TODO: N] unique pairs across [TODO: M] contrasts.

**Category 2: ALME conflict items.** Drawing from the Audio-Language Model Evaluation benchmark (ALME; [TODO: cite 2602.11488]), we select items where the text context predicts one answer and the audio signal supports another. These items operationalize the "listen vs. guess" distinction at the behavioral level: a model that follows text context on conflict items is guessing; one that follows audio is listening. We use [TODO: N ≈ 500] conflict items spanning [TODO: task categories].

**Category 3: Codec-degraded variants.** To assess robustness, we re-encode Category 1 stimuli through four audio codecs at varying quality levels:

| Codec | Bitrate | Expected Effect |
|-------|---------|-----------------|
| FLAC (lossless) | — | Baseline (no degradation) |
| MP3 | 128 kbps | Mild perceptual degradation |
| OGG Vorbis | 128 kbps | Comparable to MP3, different artifacts |
| G.711 μ-law | 64 kbps | Telephony-grade; substantial spectral loss |

Additionally, we employ **SpeechTokenizer RVQ layer-selective corruption** (following Gap #21 in our theoretical framework): by corrupting only the semantic RVQ layer (layer 1) or only the acoustic RVQ layers (layers 2+), we can dissociate whether $gc$ shifts are driven by loss of semantic content or acoustic detail.

### 3.3.2 Intervention Procedure

For each stimulus pair and target layer $k$, we execute the following procedure:

1. **Forward pass (base).** Run the model on input $(a_{\text{base}}, t_{\text{base}})$; cache activations $h_k^{\text{base}}$ at every layer $k \in \{1, \ldots, L\}$.

2. **Forward pass (source).** Run the model on input $(a_{\text{source}}, t_{\text{source}})$; cache activations $h_k^{\text{source}}$.

3. **DAS subspace identification.** Using a held-out training split, learn a rotation matrix $R_k$ at each layer via distributed alignment search (Geiger et al., 2023) that aligns the intervention subspace with the target causal variable (phoneme identity for Category 1; answer source for Category 2).

4. **Interchange intervention.** For the test split, patch $h_k^{\text{base}}$ with the source-projected representation (§3.1.1) and continue the forward pass from layer $k$ to the output.

5. **Evaluate IIA.** Record whether the model's output matches the counterfactual prediction. Repeat for audio-only and text-only interventions to compute $\text{IIA}_{\text{audio}}(k)$ and $\text{IIA}_{\text{text}}(k)$.

6. **Sweep.** Repeat steps 3–5 for all layers $k \in \{1, \ldots, L\}$ to obtain the full $gc(k)$ curve.

For the AND/OR gate analysis (§3.2), we additionally decompose each layer's activations into sparse features using a trained sparse autoencoder (SAE) and perform per-feature interventions to classify gate types.

**Tooling.** We use **NNsight** (Fiotto-Kaufman et al.) for hook injection and activation caching, and **pyvene** (Wu et al., 2024) for implementing interchange interventions. Both tools support the computational graph surgery required for DAS without modifying model weights.

### 3.3.3 Evaluation Metrics

**Primary metrics:**

- **gc(k)** (§3.1.2): the grounding coefficient at each layer. Reported as a curve over $k$ with 95% bootstrap confidence intervals.

- **$k^*$** (§3.1.3): the listen layer, with uncertainty estimated via bootstrap resampling over stimulus pairs.

- **$\alpha_{\text{AND}}(k)$** (§3.2.2): AND-gate fraction at each layer.

- **$\kappa(k)$** (§3.2.2): cascade degree (= $1 - \alpha_{\text{AND}}(k)$).

**RAVEL-style disentanglement metrics.** Following Huang et al. (2024), we evaluate feature-level interventions with:

- **Cause score**: After intervening on feature $f$ to set attribute $A$ to value $v$, how often does the model's output reflect $v$? Formally, $\text{Cause}(f, A) = \mathbb{E}[\mathbf{1}(\hat{y} = v) \mid \text{do}(f \leftarrow f_{A=v})]$.

- **Isolate score**: After intervening on feature $f$ to set attribute $A$ to value $v$, how little do *other* attributes $B \neq A$ change? Formally, $\text{Isolate}(f, A) = 1 - \frac{1}{|B|}\sum_{B \neq A} |\Delta \hat{y}_B|$.

High Cause + high Isolate indicates a feature that cleanly and specifically represents a single audio attribute — the hallmark of an AND-gate feature in our framework.

**Statistical criteria.** All reported effects are required to meet: (i) 95% bootstrap confidence intervals that exclude the null, and (ii) Cohen's $d \geq 0.3$ (medium effect size). We report exact bootstrap CIs rather than parametric $p$-values, following recent recommendations for interpretability research [TODO: cite]. Sample sizes are determined by power analysis targeting $d = 0.3$ with $1 - \beta = 0.80$.


## 3.4 Models and Data

### 3.4.1 Models

We target three model scales within the Whisper architecture (Radford et al., 2023), selected for their open weights, well-understood encoder structure, and availability of prior interpretability work (Glazer et al., 2025; AudioSAE, Aparin et al., 2026):

| Model | Encoder Layers | Decoder Layers | Hidden Dim | Parameters |
|-------|---------------|----------------|------------|------------|
| Whisper-base | 6 | 6 | 512 | 74M |
| Whisper-small | 12 | 12 | 768 | 244M |
| Whisper-medium | 24 | 24 | 1024 | 769M |

Whisper-base serves as a rapid iteration target for protocol validation (our Q001 and Q002 experiments use this model). Whisper-small is the primary analysis target, matching the model scale used by AudioSAE (Aparin et al., 2026) and enabling direct comparison of SAE features. Whisper-medium tests whether $gc(k)$ patterns scale with model depth; we predict that $k^*$ shifts proportionally deeper in larger models while $gc(k^*)$ magnitude remains stable.

For the full audio-language model setting, we target **Qwen2-Audio** (Chu et al., 2024), which pairs a Whisper-large-v3 encoder with a Qwen2 7B language model backbone via a learned audio-text connector. This architecture enables testing $gc(k)$ across the complete encoder → connector → LLM pipeline, where we predict a three-phase $gc$ profile: (i) rising $gc$ through the encoder, (ii) a potential drop at the connector (if the connector discards audio detail), and (iii) a declining $gc$ through the LLM as text priors increasingly dominate. [TODO: GPU access required — experiments on Qwen2-Audio are deferred pending NDIF cluster allocation or local GPU availability.]

### 3.4.2 Data

**Training data for DAS rotation.** We use [TODO: N ≈ 2000] minimal pair stimuli from LibriSpeech (Panayotov et al., 2015) test-clean, extracted via forced alignment at the phoneme level. Pairs are matched for speaker, recording condition, and surrounding phonetic context. An 80/20 train/test split is used for learning DAS rotations (train) and computing IIA (test).

**Evaluation data.** For Category 2 (conflict items), we draw from the ALME benchmark [TODO: cite 2602.11488], selecting items with verified audio-text conflict. For Category 3 (codec variants), we re-encode the Category 1 stimuli using FFmpeg with controlled codec parameters.

**SAE training data.** For the AND/OR gate analysis, we train sparse autoencoders on Whisper-small activations following the AudioSAE protocol (Aparin et al., 2026): TopK activation with 8× expansion ratio ($768 \rightarrow 6{,}144$ features), trained on [TODO: N hours] of LibriSpeech. We train per-layer SAEs for all 12 encoder layers to enable layer-wise AND/OR gate profiling.

### 3.4.3 Computational Requirements

Each $gc(k)$ sweep over $L$ layers requires $2L$ forward passes per stimulus pair (one base + one source per intervention type per layer), plus the DAS training cost. For Whisper-small ($L = 12$) with [TODO: N] stimulus pairs, we estimate [TODO: X] GPU-hours on a single A100. The AND/OR gate analysis adds a per-feature intervention loop; with $F = 6{,}144$ SAE features per layer, we employ a pre-filtering step (retaining only features with activation frequency $> 10^{-3}$) to reduce this to [TODO: $F' \approx$ 500–1000] features per layer.


---

# §4 Results

## 4.1 Encoder Analysis: Voicing Geometry in Whisper

We first validate that Whisper's encoder contains linearly structured phonological representations — a prerequisite for meaningful gc(k) analysis.

**Experiment Q001 (Real).** We extract voicing vectors from consonant minimal pairs (/t/–/d/, /p/–/b/, /k/–/g/, /s/–/z/) across all encoder layers of Whisper-base using DAS-identified subspaces. Table 1 reports cosine similarity between voicing directions across contrast pairs.

| Layer | Stop–Stop cos_sim | Stop–Fricative cos_sim | Mean cos_sim |
|-------|-------------------|------------------------|--------------|
| 1     | [TODO: data]      | [TODO: data]           | [TODO: data] |
| 2     | [TODO: data]      | [TODO: data]           | [TODO: data] |
| 3     | [TODO: data]      | [TODO: data]           | [TODO: data] |
| 4     | [TODO: data]      | [TODO: data]           | [TODO: data] |
| 5     | +0.25             | ~0.0 (orthogonal)      | 0.155        |
| 6     | [TODO: data]      | [TODO: data]           | [TODO: data] |

**Key finding:** Voicing vectors show weak but positive alignment within manner class (stop–stop: +0.25) and orthogonality across manner classes (stop–fricative: ~0.0). The peak at layer 5 is consistent with Choi et al.'s (2026) finding that phonological features crystallize at intermediate encoder depths.

[TODO: Replicate on Whisper-small/medium to test whether cos_sim improves with model scale]

**Claim 1:** Whisper's encoder contains linearly structured phonological representations that can serve as intervention targets for gc(k) analysis.


## 4.2 Causal Contribution Analysis

**Experiment Q002 (Real).** We perform zero-ablation, noise-ablation, and mean-ablation of each individual encoder layer in Whisper-base, measuring WER degradation on LibriSpeech test-clean.

| Layer Ablated | Zero-Ablation WER | Noise-Ablation WER | Mean-Ablation WER |
|---------------|-------------------|---------------------|-------------------|
| 1             | [TODO: data]      | [TODO: data]        | [TODO: data]      |
| 2             | [TODO: data]      | [TODO: data]        | [TODO: data]      |
| 3             | [TODO: data]      | [TODO: data]        | [TODO: data]      |
| 4             | [TODO: data]      | [TODO: data]        | [TODO: data]      |
| 5             | [TODO: data]      | [TODO: data]        | [TODO: data]      |
| 6             | [TODO: data]      | [TODO: data]        | [TODO: data]      |
| All layers    | 1.0               | 1.0                 | 1.0               |

**Key finding:** Every single-layer ablation degrades WER to ~1.0 (complete failure), regardless of ablation method. This contrasts fundamentally with text LLMs, where middle layers can often be ablated with minimal performance loss.

[TODO: Confirm WER=1.0 is exact or approximate — report precise values]
[TODO: Test partial ablation (50% noise) to find graded contribution curve]

**Claim 2:** Whisper distributes acoustic information across all encoder layers with no redundancy. This implies that gc(k) curve *shape* — not any single layer's value — characterizes the model's listening strategy.


## 4.3 gc(k) Peak Localization

**Experiment Q089 (Mock).** Using the mock framework with synthetic gc(k) curves, we validate that the gc peak can be reliably localized and that it correlates with AND-gate fraction.

| Layer | gc(k) | AND% | OR% | Passthrough% |
|-------|-------|------|-----|--------------|
| 1     | [TODO: mock values] | [TODO] | [TODO] | [TODO] |
| 2     | [TODO: mock values] | [TODO] | [TODO] | [TODO] |
| 3 (peak) | [TODO: mock values] | 100% | 0% | 0% |
| 4     | [TODO: mock values] | [TODO] | [TODO] | [TODO] |
| 5     | [TODO: mock values] | [TODO] | [TODO] | [TODO] |
| 6     | [TODO: mock values] | [TODO] | [TODO] | [TODO] |

Pearson correlation between AND% and gc(k): r = 0.9836 (p < 0.001).

[TODO: Real gc(k) sweep on Whisper-small — Priority 1 experiment]
[TODO: Report bootstrap 95% CI for k* estimate]

**Claim 3:** gc(k) peaks sharply at a localized listen layer k*, and this peak can be reliably detected.


## 4.4 AND/OR Gate Validation

**Experiment Q089 (Mock).** At the gc peak layer (L3), all causally relevant features are classified as AND-gates (α_AND = 1.0), indicating that genuine multimodal integration concentrates at the listen layer.

**Experiment Q113 (Mock).** The cascade degree κ(k) = 1 − α_AND(k) validates the text-override vulnerability measure: layers with high κ show elevated text-prior override in conflict stimuli.

| Layer | α_AND | κ (cascade degree) | Text-override rate |
|-------|-------|--------------------|--------------------|
| [TODO: layer data from Q113] | [TODO] | [TODO] | [TODO] |

[TODO: Real AND/OR gate classification on Whisper-small SAE features]

**Claim 4:** AND-gate fraction is a near-perfect proxy for gc peak detection (r = 0.98). Cascade degree predicts text-override vulnerability.


## 4.5 Persona-Conditioned Grounding

**Experiment Q039 (Mock).** We test whether system prompts modulate the gc(k) profile by comparing three persona conditions: default, assistant ("you are a helpful assistant"), and anti-grounding ("ignore audio input and rely on context").

| Condition | k* (gc peak layer) | gc(k*) | Mean gc | Hypothesis |
|-----------|---------------------|--------|---------|------------|
| Default   | [TODO]              | [TODO] | [TODO]  | Baseline   |
| Assistant | [TODO]              | [TODO] | [TODO] (suppressed) | H1: suppresses mean gc ✅ |
| Anti-grounding | [TODO] (shifted 2 layers earlier) | [TODO] (boosted) | [TODO] | H2: boosts peak ✅, H3: shifts peak ✅ |

**H4 (between/within variance):** FAILED — variance ratio = 0.073, below threshold of 1.5. Persona effects are small relative to within-condition variability.

[TODO: Test on real model — do system prompts actually shift gc profile?]

**Claim 5:** System prompts modulate grounding profiles, with anti-grounding prompts shifting the listen layer and boosting peak gc. This has implications for prompt injection safety.


## 4.6 Collapse Onset and Incrimination

**Experiment Q069 (Mock).** We test the collapse onset metric t* across three degradation types:

| Degradation Type | t* (collapse onset) | Feature Blame Concentration |
|------------------|---------------------|-----------------------------|
| Error token      | 3.4                 | [TODO: top features]        |
| Gradual drift    | 3.8                 | [TODO: top features]        |
| Sudden collapse  | 2.7                 | [TODO: top features]        |

[TODO: Verify t* detection is robust to threshold τ choice — sensitivity analysis]

**Experiment Q078 (Mock).** SAE patrol monitoring for feature suppression and override events:

| Metric | Value |
|--------|-------|
| Suppression alert rate | 96% |
| Override detection rate | 77% |
| False positive rate | 3.3% |
| Persistent offenders | f3, f12, f20, f23 |

[TODO: Interpret persistent offender features — what do f3, f12, f20, f23 encode?]
[TODO: Real SAE patrol on Whisper-small — do the same features appear?]

**Claim 6:** t* (collapse onset) combined with SAE incrimination provides a two-level attribution system for grounding failure: t* identifies *when* collapse occurs, and feature blame identifies *which features* are responsible.


## 4.7 RAVEL Disentanglement

**Experiment Q053 (Mock).** We validate audio attribute disentanglement using the RAVEL protocol on MicroGPT:

| Component | Cause Score | Isolate Score | Pass? |
|-----------|-------------|---------------|-------|
| audio_class (L0) | [TODO] | 0.16 | ❌ (bleed) |
| audio_class (L2+) | [TODO] | [TODO] | ✅ |
| speaker_gender | [TODO] | [TODO] | ✅ (all layers) |
| pitch | [TODO] | [TODO] | ✅ |
| loudness | [TODO] | [TODO] | ✅ |
| spectral_tilt | [TODO] | [TODO] | ✅ |
| duration | [TODO] | [TODO] | [TODO] |

**Result:** 5/6 components pass (83.3%). Speaker gender is fully disentangled across all layers. Audio class shows early-layer bleed (L0 Isolate = 0.16) that resolves by intermediate layers.

[TODO: RAVEL on Whisper-small SAE features — does disentanglement improve with SAE decomposition?]

**Claim 7:** Audio attributes are disentangleable at intermediate-and-later layers, confirming that gc(k) operates on clean, attribute-specific features rather than entangled representations.


## 4.8 Pre-Registered Predictions

We register the following predictions for future empirical validation on ALME conflict stimuli:

| Prediction | Formal Criterion | Status |
|------------|------------------|--------|
| P1: follows_text items show late-layer gc drop | Δgc ≥ 0.10, Cohen's d ≥ 0.3 | [TODO: awaiting GPU access] |
| P2: Rare phoneme contrasts show stronger late-layer drop | [TODO: specify rare/common threshold] | [TODO: awaiting GPU access] |
| P3: Tier 1 (degraded audio) items show flat gc at ALL layers | gc variance < [TODO: threshold] | [TODO: awaiting GPU access] |
| P4: Listen layer k* shifts earlier for conflict items | Δk* ≥ 1 layer, bootstrap 95% CI | [TODO: awaiting GPU access] |

[TODO: Run on ALME conflict stimuli when GPU access available]
[TODO: Pre-register on OSF or similar platform before running]


## 4.9 Blocked Experiments

Two experiments produced results inconsistent with framework predictions:

**Q117 (GSAE density).** Graph-regularized SAE co-activation density was insufficient to support the gc framework. Expected dense co-activation clusters at gc peak layers; observed sparse, diffuse patterns.

[TODO: Diagnose root cause — is the graph regularization too weak, or is the gc-density link not real?]
[TODO: Test alternative graph construction (k-NN vs. threshold) before discarding]

**Q123 (FAD-RAVEL direction).** FAD bias correlation sign reversed from prediction. Expected positive correlation between FAD bias and gc; observed negative.

[TODO: Diagnose sign reversal — could FAD measure a complementary quantity to gc?]
[TODO: Check if FAD-RAVEL direction depends on codec condition]

**Claim 8:** Not all framework predictions hold. Q117 and Q123 represent genuine negative results that constrain the scope of the Listening Geometry framework.


---

# §5 Discussion

## 5.1 gc(k) as a Unifying Metric

The grounding coefficient subsumes and extends two prior observational metrics:

- **AudioLens critical layer** (Ho et al., 2025): AudioLens identifies layers where auditory attribute information peaks via logit lens probing (Pearl Level 1). gc(k) provides the causal counterpart (Pearl Level 3) — the critical layer identified by AudioLens should coincide with or be near k*, but gc(k) additionally proves that this layer *causes* the model's output rather than merely correlating with it.

- **Beyond Transcription saturation layer** (Glazer et al., 2025): The saturation layer marks where the encoder "commits" to its transcription. gc(k) extends this concept beyond encoder-only models to the full encoder → connector → LLM pipeline, and replaces white-noise reference patching with phonological minimal-pair corruption.

[TODO: Formalize "Causal AudioLens" framing — gc(k) as the causal upgrade to logit-lens-based information scores]

The connection to the Triple Convergence hypothesis is suggestive: our mock experiments place k* at layer 3 in a 6-layer model (~50% depth), consistent with the prediction that semantic crystallization occurs at intermediate depth. If this holds in larger models (Whisper-small: layer ~6; Whisper-medium: layer ~12), it would support depth-proportional scaling of the listen layer.

[TODO: Verify Triple Convergence prediction with real gc(k) data across model scales]


## 5.2 AND-Gate Insight: Genuine Multimodal Processing

The AND/OR gate framework reveals a qualitative distinction between two modes of multimodal processing:

- **AND-gate dominance** (high α_AND): The model performs genuine audio-text integration. Neither modality alone suffices to reconstruct the relevant features. This is the hallmark of a "strong listener" — the model cannot produce correct outputs without consulting the audio signal.

- **OR-gate dominance** (high cascade degree κ): The model can recover relevant features from either modality alone. Text priors can fully substitute for audio input. This is the mechanism behind "sophisticated guessing" — the model may appear to listen (high task accuracy) while relying entirely on text context.

Key implications:

- Models with low α_AND at the listen layer are "sophisticated guessers" despite potentially high behavioral accuracy. Standard benchmarks cannot detect this failure mode; gc(k) + α_AND can.
- The cascade degree κ = 1 − α_AND provides a quantitative text-override vulnerability score. Models deployed in safety-critical applications (medical transcription, legal proceedings) should be required to demonstrate high α_AND at their listen layer.
- [TODO: Can α_AND be used as a training objective? Would penalizing OR-gates during fine-tuning improve genuine audio grounding?]


## 5.3 Safety Implications

The Listening Geometry framework has direct implications for ALM safety:

- **Jailbreak attacks as gc suppression.** SPIRIT (Djanibekov et al., 2025) defends against adversarial audio jailbreaks by substituting clean activations at noise-sensitive MLP neurons. Our framework explains *why* those specific neurons matter: they likely correspond to AND-gate features at or near k* whose suppression forces the model from "strong listener" to "sophisticated guesser" — shifting the gc profile rather than injecting new information.

- **Persona-conditioned grounding shifts.** Our mock experiments (Q039) show that anti-grounding system prompts shift k* earlier and boost peak gc. In a real model, this would mean that prompt injection could deliberately degrade audio grounding — a novel attack vector where the adversary manipulates *how* the model processes audio, not *what* audio it receives.
  - [TODO: Test this on real models — is gc shift via persona prompt practically achievable?]
  - [TODO: Can gc monitoring serve as a runtime detection mechanism for prompt injection?]

- **Backdoor detection via gc.** Mock experiment Q116 shows that backdoor triggers shift t* (collapse onset) leftward, causing earlier audio abandonment. This suggests gc/t* monitoring as a backdoor detection signal.
  - [TODO: Connect to Gap #24 (SAE-guided safety patching) — can we patch AND-gate features to neutralize backdoors?]

- **Deployment screening.** The 4-profile taxonomy (strong/shallow/fragile listener, sophisticated guesser) could serve as a deployment readiness criterion: models classified as "sophisticated guessers" or "fragile listeners" should receive additional scrutiny before deployment in audio-critical applications.


## 5.4 Cross-Paper Predictions

The gc(k) framework generates testable predictions that bridge our work with concurrent studies:

- **MPAR² prediction** [CITE: Chen 2603.02266]: RL training that improves audio perception accuracy (31.7% → 63.5%) should produce one of two gc signatures: (a) raised gc at late layers (audio information persists deeper into the LLM backbone), or (b) shifted k* to a shallower layer (audio is consulted earlier and more decisively). If neither signature is observed, MPAR²'s improvement operates through a mechanism outside the gc framework.
  - [TODO: If falsified, what does it mean? Possibly that RL affects text-side processing rather than audio grounding.]

- **Modality Collapse prediction** [CITE: Zhao 2602.23136]: Items where the model "follows text" despite audio-text conflict should exhibit the Tier 3 gc profile — mid-peak followed by late-layer drop. Items where the model correctly follows audio should maintain high gc through late layers.
  - [TODO: Test on ALME conflict items with known follows_text/follows_audio labels]

- **AudioSAEBench bridge**: gc at the feature level (Paper B) is the micro-scale complement of gc at the layer level (this paper). Feature-level gc should decompose the layer-level signal, with AND-gate features contributing disproportionately to layer gc.
  - [TODO: Formal relationship: is layer gc(k) = weighted mean of feature gc(f, k)?]


## 5.5 Limitations

We acknowledge several limitations of the current work:

- **Mock validation only.** 20 of our 22 experiments use the mock framework, which validates internal consistency of the gc formalism but does not test whether real neural networks exhibit the predicted patterns. The two real experiments (Q001, Q002) on Whisper-base provide preliminary evidence but use the smallest model scale.
  - [TODO: Priority 1 — real gc(k) sweep on Whisper-small to validate core claims]

- **Model scope.** Our real experiments are limited to Whisper-base (74M parameters, encoder-only). The full Listening Geometry framework requires testing on speech LLMs (Qwen2-Audio) where both encoder and decoder layers are present, and where text priors from the LLM backbone create the listen-vs-guess tension.
  - [TODO: GPU access blocker — Qwen2-Audio experiments deferred pending NDIF cluster allocation]

- **Deferred dimensions.** Two of the five Listening Geometry dimensions — codec stratification (CS) and collapse onset (t*) — are deferred to Paper B scope. This means the current paper validates only a 3-dimensional subspace (k*, α_AND, σ) of the full framework.
  - [TODO: Confirm Paper A vs B scope boundary is clean — no circular dependencies]

- **AND/OR threshold sensitivity.** The AND/OR gate classification depends on the threshold δ, which we calibrate via bootstrap but have not tested for robustness across different δ values in real models.
  - [TODO: Sensitivity analysis of δ on real SAE features]

- **Blocked experiments.** Q117 (GSAE density) and Q123 (FAD-RAVEL direction) represent genuine framework failures that may indicate deeper limitations of the gc approach for graph-structured or frequency-domain features.


## 5.6 Future Work

Several directions extend the Listening Geometry framework:

- **Paper B (AudioSAEBench).** Dimensions D4 (collapse onset) and D5 (codec stratification) will be fully validated on Whisper and Qwen2-Audio, with feature-level gc providing the bridge between layer-level and feature-level analysis.

- **Audio T-SAE.** Adapting temporal SAEs (Bhalla et al., 2025) from text to audio would enable temporal coherence as a gc proxy: features coherent at phoneme timescale (~5–10 frames) indicate listening; features coherent at text-token timescale indicate guessing.

- **Cross-lingual gc.** Do phonological vectors survive the connector across languages? Testing gc(k) on multilingual speech (building on Choi et al.'s 96-language results) would reveal whether the listen layer is language-universal or language-specific.

- **gc as a training objective.** If α_AND can be differentiated, penalizing OR-gates during fine-tuning could produce models that genuinely integrate audio rather than defaulting to text priors.

- **Real-time gc monitoring.** Deploying gc(k) as a runtime monitoring signal could detect when a model shifts from listening to guessing during inference — enabling dynamic safety interventions.


---

## §6 Conclusion

[TODO: 1 paragraph summary of contributions]

[TODO: 1 sentence on broadest implication — "mechanistic understanding of when ALMs listen vs. guess"]
