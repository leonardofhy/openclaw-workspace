# §3 Method

## 3.1 Grounding Coefficient Definition

Audio-language models (ALMs) receive two streams of input: an acoustic signal processed by a speech encoder, and a text context processed by a language model backbone. At each layer $k$, representations may draw on either source. We introduce the **grounding coefficient** $gc(k)$ as a causal metric that quantifies the relative contribution of audio versus text context at layer $k$.

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

Operationally, we require $\text{IIA}(f; A{+}T) - \max(\text{IIA}(f; A), \text{IIA}(f; T)) > \delta$. We set $\delta$ via a bootstrap null distribution: for each feature, we compute IIA(f; A+T) under 1000 random label permutations and set $\delta$ as the 95th percentile of this null distribution. AND-gate features represent **genuine multimodal integration**: neither audio nor text alone suffices to reconstruct the feature, and both modalities must be jointly present.

**OR-gate.** Feature $f$ is an OR-gate if:

$$\text{IIA}(f; A{+}T) \approx \max\left(\text{IIA}(f; A),\; \text{IIA}(f; T)\right)$$

Operationally, $|\text{IIA}(f; A{+}T) - \max(\text{IIA}(f; A), \text{IIA}(f; T))| \leq \delta$. OR-gate features can be recovered from either modality alone, implementing a logical OR. These features are candidates for **text-prior override**: if the text context provides a strong prediction, the model need not consult audio.

**Passthrough.** Feature $f$ is a passthrough if $\text{IIA}(f; A{+}T) < \epsilon$ — the feature is not causally relevant to the target behavior under any intervention condition. We set $\epsilon = 0.05$, matching the noise floor of random IIA estimates in pilot experiments.

### 3.2.2 AND-Gate Fraction and Cascade Degree

We define the **AND-gate fraction** at layer $k$ as:

$$\alpha_{\text{AND}}(k) = \frac{|\{f : f \text{ is AND-gate at layer } k\}|}{|\{f : f \text{ is causally relevant at layer } k\}|}$$

This metric captures how much of a layer's causal computation requires genuine multimodal integration. We predict that $\alpha_{\text{AND}}(k)$ correlates positively with $gc(k)$, since layers that depend heavily on audio should contain features that require audio input.

The complementary **cascade degree** $\kappa(k) = 1 - \alpha_{\text{AND}}(k)$ measures the fraction of causal features vulnerable to text-prior override. We hypothesize that $\kappa(k)$ correlates with behavioral hallucination rate: models with high cascade degree at critical layers should be more prone to ignoring audio in favor of text-predicted outputs.

### 3.2.3 Relationship to Grounding Coefficient

The AND/OR framework provides a **mechanistic decomposition** of $gc(k)$. While $gc(k)$ measures the aggregate audio dependence of a layer, $\alpha_{\text{AND}}(k)$ reveals *why*: a high $gc(k)$ with high $\alpha_{\text{AND}}(k)$ indicates that the layer performs genuine multimodal fusion, whereas a high $gc(k)$ with low $\alpha_{\text{AND}}(k)$ could indicate that audio information is present but easily overridden — a pattern we term a "fragile listener."

Preliminary mock experiments (Q089) show that AND-gate fraction and $gc(k)$ are highly correlated ($r = 0.98$, $p < 0.001$), with the $gc$ peak coinciding with 100% AND-gate fraction. This tight coupling, if replicated in real models, would validate $\alpha_{\text{AND}}$ as a diagnostic proxy for $gc$ peak detection.

## 3.3 Experimental Protocol

This section outlines our stimulus design and intervention procedures for measuring grounding coefficients across different model architectures.

### 3.3.1 Stimuli Design

We employ three categories of stimuli, each targeting a different aspect of audio-text interaction:

**Category 1: Phonological minimal pairs.** Following the construction in §3.1.4, we use consonant minimal pairs spanning three phonological dimensions (voicing, place, manner). Stimuli are [PENDING: requires experimental data — LibriSpeech forced-aligned segments or custom recordings]. Each pair consists of two utterances differing in exactly one phonological feature at a target position, embedded in an identical carrier phrase (e.g., "Say the word \_\_\_ again"). This yields [PENDING: requires experimental data] unique pairs across [PENDING: requires experimental data] contrasts.

**Category 2: ALME conflict items.** Drawing from the Audio-Language Model Evaluation benchmark (ALME; [TODO: cite 2602.11488]), we select items where the text context predicts one answer and the audio signal supports another. These items operationalize the "listen vs. guess" distinction at the behavioral level: a model that follows text context on conflict items is guessing; one that follows audio is listening. We use [PENDING: requires experimental data] conflict items spanning [PENDING: requires experimental data] task categories.

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

**Statistical criteria.** All reported effects are required to meet: (i) 95% bootstrap confidence intervals that exclude the null, and (ii) Cohen's $d \geq 0.3$ (medium effect size). We report exact bootstrap CIs rather than parametric $p$-values, following recent recommendations for interpretability research (Efron & Hastie, 2016). Sample sizes are determined by power analysis targeting $d = 0.3$ with $1 - \beta = 0.80$.

## 3.4 Models and Data

This section details our target model architectures and experimental datasets.

### 3.4.1 Models

We target three model scales within the Whisper architecture (Radford et al., 2023), selected for their open weights, well-understood encoder structure, and availability of prior interpretability work (Glazer et al., 2025; AudioSAE, Aparin et al., 2026):

| Model | Encoder Layers | Decoder Layers | Hidden Dim | Parameters |
|-------|---------------|----------------|------------|------------|
| Whisper-base | 6 | 6 | 512 | 74M |
| Whisper-small | 12 | 12 | 768 | 244M |
| Whisper-medium | 24 | 24 | 1024 | 769M |

Whisper-base serves as a rapid iteration target for protocol validation (our Q001 and Q002 experiments use this model). Whisper-small is the primary analysis target, matching the model scale used by AudioSAE (Aparin et al., 2026) and enabling direct comparison of SAE features. Whisper-medium tests whether $gc(k)$ patterns scale with model depth; we predict that $k^*$ shifts proportionally deeper in larger models while $gc(k^*)$ magnitude remains stable.

For the full audio-language model setting, we target **Qwen2-Audio** (Chu et al., 2024), which pairs a Whisper-large-v3 encoder with a Qwen2 7B language model backbone via a learned audio-text connector. This architecture enables testing $gc(k)$ across the complete encoder → connector → LLM pipeline, where we predict a three-phase $gc$ profile: (i) rising $gc$ through the encoder, (ii) a potential drop at the connector (if the connector discards audio detail), and (iii) a declining $gc$ through the LLM as text priors increasingly dominate. [PENDING: requires experimental data — experiments on Qwen2-Audio are deferred pending NDIF cluster allocation or local GPU availability.]

### 3.4.2 Data

**Training data for DAS rotation.** We use [PENDING: requires experimental data] minimal pair stimuli from LibriSpeech (Panayotov et al., 2015) test-clean, extracted via forced alignment at the phoneme level. Pairs are matched for speaker, recording condition, and surrounding phonetic context. An 80/20 train/test split is used for learning DAS rotations (train) and computing IIA (test).

**Evaluation data.** For Category 2 (conflict items), we draw from the ALME benchmark [TODO: cite 2602.11488], selecting items with verified audio-text conflict. For Category 3 (codec variants), we re-encode the Category 1 stimuli using FFmpeg with controlled codec parameters.

**SAE training data.** For the AND/OR gate analysis, we train sparse autoencoders on Whisper-small activations following the AudioSAE protocol (Aparin et al., 2026): TopK activation with 8× expansion ratio ($768 \rightarrow 6{,}144$ features), trained on [PENDING: requires experimental data] hours of LibriSpeech. We train per-layer SAEs for all 12 encoder layers to enable layer-wise AND/OR gate profiling.

### 3.4.3 Computational Requirements

Each $gc(k)$ sweep over $L$ layers requires $2L$ forward passes per stimulus pair (one base + one source per intervention type per layer), plus the DAS training cost. For Whisper-small ($L = 12$) with [PENDING: requires experimental data] stimulus pairs, we estimate [PENDING: requires experimental data] GPU-hours on a single A100. The AND/OR gate analysis adds a per-feature intervention loop; with $F = 6{,}144$ SAE features per layer, we employ a pre-filtering step (retaining only features with activation frequency $> 10^{-3}$) to reduce this to [PENDING: requires experimental data] features per layer.

## 3.5 Scope and Limitations

This section acknowledges the current scope constraints and methodological limitations that inform our interpretation of results and future research directions.

**Encoder-only focus.** Our current experiments focus primarily on Whisper-base (encoder-only architecture) for protocol validation and rapid iteration. While this provides crucial insights into speech representation processing, it does not capture the full audio-language interaction dynamics present in complete ALMs like Qwen2-Audio. The encoder-only scope limits our ability to observe text-prior override mechanisms that operate at the language model level, where our theoretical framework predicts the most pronounced "listening vs. guessing" trade-offs occur.

**Mock experiment validation.** Our preliminary experiments employ mock data to validate the algebraic framework and statistical properties of $gc(k)$ and $\alpha_{\text{AND}}(k)$ metrics. While these experiments confirm the mathematical coherence of our approach and establish baseline expectations (e.g., the tight correlation between AND-gate fraction and grounding coefficient), they cannot validate whether real neural networks exhibit the predicted behavioral patterns. The transition from mock to real experiments represents a critical empirical test of our theoretical predictions.

**Linear causal measurement.** The $gc(k)$ metric captures linear causal influence through DAS-based interchange interventions, which identify linear subspaces that faithfully represent high-level causal variables. This approach may miss nonlinear causal contributions where audio information influences model behavior through complex, non-additive interactions with text representations. While linear decomposition has proven effective for phonological features in speech models (Choi et al., 2026), higher-order multimodal interactions may require extensions beyond our current framework.

**Pre-registered predictions.** We have pre-registered specific predictions for ALME conflict item analysis and MPAR² RL-induced grounding shifts to prevent post-hoc hypothesis adjustment. However, these predictions await experimental validation pending GPU access for full-scale ALM experiments. The pre-registration provides methodological rigor but also constrains our ability to adapt the framework based on unexpected empirical patterns that may emerge during real model analysis.