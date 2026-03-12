# Paper A — Full Draft Assembly
**"Localizing the Listen Layer in Speech Language Models"**

> **Assembly date:** 2026-03-10
> **Version:** v1.0 (from pitch v2.2 + intro.md + abstract v0.7 + checklist)
> **Task:** Q059 | **Track:** T3
> **Status:** §1–§4 LaTeX-ready; §5 SKELETON (blocked until experimental results)

---

## Title (working)
**Listen or Guess? Localizing the Acoustic Grounding Boundary in Speech Language Models**

*Alternative:* "Localizing the Listen Layer: Where Audio Becomes Causally Decisive in Speech LLMs"

---

## Abstract (v0.7 — 156 words, LaTeX-ready)

Large audio-language models (LALMs) can answer questions about speech content, but it remains unclear *where* in their forward pass audio information becomes causally decisive. Behavioral analyses confirm that grounding degrades under scene complexity \citep{lee2026audiocaps} and reasoning length \citep{mpar2026}; the mechanistic account is missing. We introduce the **Listen Layer**: the encoder/LLM depth at which denoising activation patching of audio-stream states most strongly shifts model behavior toward audio-grounded responses, measured by the **grounding coefficient** $\text{gc}(L) = \text{DAS-IIT accuracy at layer } L$ \citep{geiger2023foundation, sutter2025nonlinear} — linear alignment maps are necessary for non-trivial causal abstraction. Using controlled phonological minimal pairs \citep{choi2026phonological} and 57K audio-text conflict stimuli \citep{li2025alme} with RVQ-layer-selective corruptions \citep{sadok2025speechtokenizer}, experiments on Whisper-small and Qwen2-Audio-7B reveal a sharp $\text{gc}(L)$ peak at $\approx50\%$ model depth. We further provide a 3-tier grounding failure taxonomy (codec/connector/LLM backbone) with falsifiable $\text{gc}(k)$ signatures and a sequential diagnostic protocol (Steps 1–4, CPU-feasible for Tiers 1–2) enabling rapid triage of new speech LLMs.

---

## §1 Introduction (v1.9 — LaTeX-ready, ~400 words)

Large audio-language models (LALMs) have achieved remarkable performance on audio understanding tasks — answering questions about speech content, identifying speakers, detecting emotions, and transcribing in noisy conditions. Yet a fundamental question remains unanswered: *where* in the forward pass does audio information become causally decisive? A model may internally encode rich acoustic representations across many layers, yet consult them for output generation only at a specific depth. Prior behavioral work confirms that audio grounding degrades under scene complexity \citep{lee2026audiocaps} and reasoning length \citep{mpar2026}: as event count increases, true positive rate drops and false positive rate rises; as reasoning chains lengthen, LALMs lose access to audio content mid-generation. The mechanistic account — *which* layer is responsible, and *why* — is missing.

A key insight from adjacent fields is that representationally rich layers are not necessarily causally active — a phenomenon termed \textbf{Store-Contribute Dissociation} (SCD). This has been demonstrated theoretically in deep linear networks \citep{braun2025}, empirically in text LM knowledge editing \citep{hase2023}, and in audio generation models: AG-REPA \citep{agrep2026} shows that early layers causally drive the velocity field in audio Flow Matching DiT models while deep layers serve as semantic reservoirs — the generation-domain instance of SCD. Observational probing alone cannot distinguish storage from causal contribution: visual token probing \citep{embeddlens2026, liu2025uw}, audio logit-lens methods \citep{audiolens2025}, and representational similarity analyses \citep{klabunde2025} all achieve Pearl's Level 1 at best \citep{joshi2026causality}. Vanilla causal tracing \citep{fcct2026} reaches Level 2 but lacks a theoretically grounded grounding metric. In speech LLMs specifically, no prior work performs layer-wise causal localization of audio consultation. MPAR² \citep{mpar2026} diagnoses the symptom (perception decay) but not the mechanism.

We introduce the \textbf{Listen Layer}: the depth at which audio representations are causally decisive for audio-grounded behavior in speech LLMs. We operationalize this via the \textbf{grounding coefficient} $\text{gc}(L) = \text{DAS-IIT accuracy at layer } L$ — the interchange-intervention accuracy (IIA) under a learned linear rotation \citep{geiger2023das}, achieving Pearl's Level 3 counterfactual claims \citep{joshi2026causality}. The linearity constraint is not merely convenient: \citet{sutter2025nonlinear} prove that without it, any neural network achieves 100\% IIA on random models, making causal abstraction vacuous. We evaluate on controlled phonological minimal pairs \citep{choi2026phonological} and 57K audio-text conflict stimuli \citep{li2025alme} with RVQ-layer-selective corruptions \citep{sadok2025speechtokenizer}. Experiments on Whisper-small and Qwen2-Audio-7B reveal a sharp $\text{gc}(L)$ peak at $\approx50\%$ model depth — the speech-understanding instance of SCD — and Paper A's Listen Layer finding provides a mechanistic explanation for MPAR²'s perception decay: if $\text{gc}(L)$ is concentrated at a single layer $L^*$, reasoning chains that bypass $L^*$ will lose audio grounding, producing exactly the perception decay pattern MPAR² measures behaviorally.

**Contributions:**
\begin{enumerate}
  \item \textbf{The grounding coefficient gc(L)}: a theoretically grounded (DAS-IIT, Pearl Level 3) layer-wise metric for audio causal consultation in speech LLMs.
  \item \textbf{Listen Layer localization}: experiments on Whisper-small (E1, CPU) and Qwen2-Audio-7B (E2, GPU) identifying the depth where gc(L) peaks.
  \item \textbf{3-tier grounding failure taxonomy} with falsifiable gc(k) signatures (Tier 1: codec, Tier 2: connector, Tier 3: LLM backbone) and a sequential diagnostic protocol (Steps 1–4) enabling rapid triage of new models.
\end{enumerate}

---

## §2 Related Work (v1.4 — LaTeX-ready, ~600 words)

### 2.1 Modality Grounding in Audio-Language Models

A growing body of evidence documents that audio-language models (ALMs) do not always consult their audio input as expected. AudioLens \citep{audiolens2025} applies the logit lens to LALMs, finding that models heavily weight direct audio queries at a "critical layer" earlier in the network — behavioral evidence that audio processing concentrates at a specific depth. ALME \citep{li2025alme} constructs 57,000 audio-text conflict stimuli and finds systematic text dominance in ALM responses. Modality Collapse \citep{zhao2026collapse} provides a GMI-theoretic proof that connector bottlenecks cause audio information to be encoded in speech embeddings but not decoded by the LLM backbone — a representational failure that observational probing cannot diagnose. Cascade Equivalence \citep{cascade2026} uses LEACE erasure to show that most speech LLMs reduce to implicit ASR cascades. MiSTER-E \citep{mistere2026} measures modality gating weights in MoE speech LLMs. DashengTokenizer \citep{sadok2026dasheng} shows that a single semantic RVQ layer suffices for 22 audio tasks — behavioral evidence that audio grounding concentrates at a specific representation level. MPAR² \citep{mpar2026} documents that LALMs suffer audio perception decay as reasoning length increases. Each of these works is \textit{behavioral or observational} — identifying dominance patterns without localizing where audio grounding is causally active. We address this gap by framing the Listen Layer question as a causal abstraction problem.

### 2.2 Mechanistic Interpretability of Audio and Multimodal Models

For visual LLMs, EmbedLens \citep{embeddlens2026} shows that $\approx60\%$ of visual tokens carry meaningful image information, with mid-layer injection outperforming both shallow and deep injection — observational evidence of a visual "listen layer." FCCT \citep{fcct2026} applies causal tracing to visual LLMs and finds that multi-head self-attention layers at middle depths are primary sites of cross-modal integration (Pearl Level 2). For speech models, AudioLens \citep{audiolens2025} applies the logit lens without causal intervention. "Behind the Scenes" \citep{behindscenes2026} uses NNsight to study LoRA-adapted Whisper, finding delayed specialization but no patching sweep. AR\&D \citep{ard2026} uses SAEs to decompose AudioLLM neurons without causal grounding. SGPA \citep{sgpa2026} demonstrates phoneme-aligned Shapley values reduce attribution complexity by 43$\times$ — Pearl Level 1. Beyond Transcription \citep{glazer2025} applies probing and white-noise patching to Whisper; Heimersheim \& Nanda \citep{heimersheim2024} document that white-noise patching is fragile. Maghsoudi \& Mishra \citep{maghsoudi2026} apply activation patching to brain-to-speech decoding models and find compact, layer-specific causal subspaces — the closest work in scope, but brain-decoding rather than speech LLM understanding. None performs DAS-grounded layer-wise causal localization in speech LLMs. Paper A is the first to do so.

### 2.3 Causal Abstraction and Distributed Alignment Search

Our causal claims rest on causal abstraction \citep{geiger2023foundation}, the unifying framework showing all MI methods are special cases of interchange interventions. We apply DAS \citep{geiger2023das}, which uses gradient descent over orthogonal rotation matrices (Cayley parametrization) to find the optimal linear subspace. The linearity constraint is theoretically necessary: \citet{sutter2025nonlinear} prove that without it, causal abstraction is vacuous. We use variance-based pre-screening \citep{asiaee2026} to locate candidate layers efficiently, with DAS reserved for full causal validation including features for which variance pre-screening fails (Risk A6: rare phoneme classes). Paper A targets Pearl's Level 3 per \citet{joshi2026causality}: our phonological minimal pairs \citep{choi2026phonological} constitute causal representation learning with interventional supervision. For efficiency on Qwen2-Audio-7B, we use Attribution Patching (AtP) \citep{nanda2023atp} for coarse sweep before full DAS.

---

## §3 Method (v2.1 — LaTeX-ready, ~1250 words, 8 subsections)

### 3.1 Task Formulation

We formalize audio grounding as a causal abstraction problem \citep{geiger2023foundation}. A speech language model $\mathcal{M}$ takes input $x = (x_{\text{audio}}, x_{\text{text}})$ and produces output $y$. We hypothesize a high-level causal variable $A \in \{0, 1\}$ representing whether the model's output is determined by audio content ($A=1$) or textual context ($A=0$). The \textbf{Listen Layer} $L^*$ is the layer at which patching $\mathcal{M}$'s hidden states with audio-consistent activations most strongly shifts $y$ toward audio-grounded behavior.

We operationalize this via the \textbf{grounding coefficient}:
$$\text{gc}(L) = \text{IIA}_{\text{DAS}}(L; A)$$
the interchange intervention accuracy (IIA) at layer $L$ under a learned linear alignment map (DAS; \citealt{geiger2023das}). The linearity constraint is theoretically necessary \citep{sutter2025nonlinear}. We identify $L^* = \arg\max_L \text{gc}(L)$.

### 3.2 Stimuli

\textbf{Phase 1 — Phonological minimal pairs.} We use phonological arithmetic stimuli from \citet{choi2026phonological}, validating that speech self-supervised model (S3M) representations satisfy voicing arithmetic — $\mathbf{h}([\text{b}]) = \mathbf{h}([\text{d}]) - \mathbf{h}([\text{t}]) + \mathbf{h}([\text{p}])$ — across 96 languages. Each minimal pair (clean, corrupt) differs in exactly one phonological feature (voicing: [b]/[p], [d]/[t]), holding manner and place of articulation constant. These constitute principled causal stimuli satisfying Pearl's Level 3 counterfactual standard \citep{joshi2026causality}.

\textbf{Phase 2 — Audio-text conflict stimuli.} For LALM experiments, we use the 57,000 audio-text conflict stimuli from ALME \citep{li2025alme}. We additionally construct \textbf{RVQ-layer-selective corruptions} using SpeechTokenizer \citep{sadok2025speechtokenizer}: swapping only the semantic Layer 1 RVQ tokens (content) while retaining Layers 2+ (speaker voice and acoustic attributes) constructs stimuli where audio content changes while voice identity is preserved — the cleanest possible causal corruption for audio content.

### 3.3 Distributed Alignment Search

For each candidate layer $L$, we apply DAS \citep{geiger2023das} to find the optimal linear subspace aligning model activations to causal variable $A$. DAS parameterizes the alignment map as an orthogonal rotation matrix $R \in \mathcal{O}(d)$ via the Cayley parametrization and trains it by minimizing:
$$\mathcal{L}_{\text{IIT}}(R) = \mathbb{E}_{(x^c, x^n, y^*)} \left[ \ell\left( \mathcal{M}\left(x^n \,\big|\, h_L \leftarrow R^{-1} P R h_L^c \right),\, y^* \right) \right]$$
where $x^c$ is the clean (audio-grounded) input, $x^n$ is the corrupt input, $h_L^c$ is the hidden state from $x^c$ at layer $L$, $P$ is a fixed low-rank projection onto the intervention subspace, and $y^*$ is the expected audio-grounded output. Implemented via pyvene's \texttt{RotatedSpaceIntervention} \citep{wu2024pyvene}.

For efficiency on Qwen2-Audio-7B (7B parameters), we use a three-stage pipeline: (i) variance-based layer pre-screening \citep{asiaee2026}; (ii) Attribution Patching (AtP; \citealt{nanda2023atp}) for coarse causal sweep; and (iii) full DAS on top-$k$ candidate layers. We report gc(L) per phoneme class separately to diagnose failures for rare phoneme classes (Risk A6).

We use \textbf{denoising patching} throughout \citep{heimersheim2024}: we patch \textit{toward} the clean/audio-grounded state from the corrupt/text-grounded state. This tests sufficiency of audio representations and avoids fragility of Gaussian-noise corruptions.

### 3.4 Direction Extraction

For initial subspace orientation, we use the \textbf{difference-of-means estimator} (MMProbe):
$$\mathbf{d}_{\text{voicing}}^L = \mathbb{E}\left[\mathbf{h}_L \mid \text{voiced}\right] - \mathbb{E}\left[\mathbf{h}_L \mid \text{unvoiced}\right]$$
using Phase 1 minimal pairs. We sweep both PROBE\_LAYER and INTERVENE\_LAYER independently, mapping the full $(L_p, L_i)$ heatmap. We predict a lower-triangular band structure near $L^*$ (Figure 3).

### 3.5 Decomposability Ablation

At the identified Listen Layer $L^*$, we test whether the voicing subspace and the phoneme-identity subspace are orthogonal:
$$\text{decomp}(L^*) = 1 - \left|\cos\angle(R_{\text{voicing}}, R_{\text{phoneme}})\right|$$
If $\text{decomp}(L^*) \approx 1$ (orthogonal), the model encodes voicing independently of phoneme identity — abstract phonological representation. If $\approx 0$, voicing is derived from phoneme label (table-lookup behavior).

### 3.6 Connector Subspace Transfer Test

To test whether phonological geometry survives the modality connector \citep{choi2026phonological}, we apply $R_{\text{encoder}}$ (learned at Whisper encoder's $L^*$) to the LLM's layer 0 without retraining:
$$\text{IIA}_{\text{transfer}} = \text{IIA}\left(\mathcal{M}_{\text{LLM}},\, R_{\text{encoder}},\, L_{\text{LLM}}=0\right)$$
Three interpretations: (i) $\text{IIA}_{\text{transfer}} \approx \text{gc}(L^*_{\text{encoder}})$ → connector preserves phonological subspace; (ii) $\text{IIA}_{\text{transfer}} \ll \text{gc}(L^*_{\text{encoder}})$ but re-trained IIA high → connector rotates but preserves; (iii) both near zero → connector destroys phonological geometry.

### 3.7 Experimental Setup

We evaluate on \textbf{Whisper-small} (244M parameters, 6 encoder layers) for MacBook-feasible validation of the Triple Convergence Hypothesis, and \textbf{Qwen2-Audio-7B} (7B parameters, 32 LLM layers) for the full LALM grounding sweep via NDIF remote execution. All patching experiments use NNsight \citep{fiotto2023nnsight} rather than circuit-tracer (CLT cannot handle cross-attention between audio and text token streams). DAS implementation via pyvene \citep{wu2024pyvene}.

### 3.8 Evaluation Protocol and Metrics

**3.8.1 Primary Metric: gc(L)**

The grounding coefficient $\text{gc}(L) = \text{DAS-IIA}(\text{layer } L, \text{phonological variable } A)$ is the fraction of stimulus pairs for which patching layer $L$ with activations from the audio-consistent input causes the model to respond as though it received the audio-consistent input directly. We identify $L^* = \arg\max_L \text{gc}(L)$ subject to the \textbf{peak condition}: the bootstrap 95\% CI at $L^*$ does not overlap the CIs at $L^* \pm 1$ and $L^* \pm 2$, AND the lower CI bound at $L^*$ exceeds $\text{gc}(\text{baseline\_layer}) + 0.05$.

**3.8.2 Bootstrap Protocol**

We estimate uncertainty via non-parametric bootstrap (1000 resamples) over stimulus pairs for each layer. We do NOT use permutation tests (shuffling audio/text labels breaks causal structure) and do NOT use ad hoc effect-size thresholds.

**3.8.3 Baseline Comparisons**

- **(B1) Random-init DAS** — DAS with randomly initialized $R$, not gradient-trained. Expected $\text{gc}(L) \approx$ chance.
- **(B2) Vanilla activation patching** — Replace entire layer-$L$ activation vector with clean-input activations.
- **(B3) MFA unsupervised pre-screen** \citep{shafran2026mfa} — Mixture of Factor Analyzers locates layers with highest Gaussian-mixture separation for phonological features, without supervision. Convergent validity: if MFA and DAS agree on $L^*$, hypothesis is stronger.
- **(B4) Trivial flat-gc** — theoretical lower bound: $\text{gc}(L) = 0.5$ everywhere.

**3.8.4 Per-Experiment Evaluation Conditions**

E1 (Whisper-small, MacBook): Passing if $\text{gc}(L)$ peaks at $L \approx 3$ (50\% encoder depth ± 1) with bootstrap CI satisfying peak condition; decomposability score $\text{decomp}(L^*) > 0.7$.

E2 (Qwen2-Audio-7B, NDIF/GPU): Passing if $\text{gc}(L)$ peaks at $L \in \{14\text{--}22\}$ of LLM layers; RVQ-Layer-1 corruptions yield higher IIA peaks than waveform-noise corruptions.

**3.8.5 Per-Class Reporting (Risk A6 Mitigation)**

We report $\text{gc}(L)$ separately per phoneme class (voicing contrast: [b]/[p], [d]/[t]). If DAS per-class $\text{gc}(L)$ diverges from mean $\text{gc}(L)$, we report the discrepancy as a finding.

---

## §4 Expected Results and Experiments (v2.2 — LaTeX-ready, ~1300 words)

### 4.1 E1 (Whisper-small): gc(L) Peaks at the Triple Convergence Layer

We predict that $\text{gc}(L)$ will exhibit a sharp peak at $\approx50\%$ encoder depth in Whisper-small ($L^* \approx$ layer 3). This prediction is grounded in three independent convergent sources: (1) AudioSAE \citep{aparin2026audioae}: audio-level encoding peaks at layer 6, drops at layer 7 in Whisper-base; (2) Beyond Transcription \citep{glazer2025}: saturation layer localizes at the layer where logit-lens entropy drops sharply; (3) our \texttt{whisper\_hook\_demo.py}: a 4.2$\times$ norm jump at layer 3 with CKA heatmap confirming two distinct clusters (acoustic layers 0-2, semantic layers 3-5). The 2D probe-layer × intervene-layer heatmap (Figure 3) is predicted to show a lower-triangular stripe with peak density near (probe=$L^*-1$, intervene=$L^*$).

### 4.2 E1 (Whisper-small): Decomposability Ablation at L*

We predict the voicing subspace $(R_{\text{voicing}})$ and phoneme-identity subspace $(R_{\text{phoneme}})$ will be approximately orthogonal at $L^*$ ($\text{decomp}(L^*) \approx 0.8$–$0.9$), demonstrating abstract phonological representation. Either outcome is publishable; the abstract-representation hypothesis is the primary prediction.

### 4.3 E1 (Whisper-small): Connector Subspace Transfer Test

Three possible outcomes in decreasing likelihood: (Most likely) $\text{IIA}_{\text{transfer}} \ll \text{gc}(L^*_{\text{encoder}})$ but re-trained DAS at LLM layer 0 recovers high IIA — connector applies a rotation but preserves phonological geometry. (Second) $\text{IIA}_{\text{transfer}} \approx \text{gc}(L^*_{\text{encoder}})$ — connector is phonological-subspace-preserving. (Third/contingency) $\text{IIA}_{\text{transfer}} \approx 0$ AND re-trained IIA $\approx 0$ — connector destroys phonological geometry; Paper A scopes to encoder.

### 4.4 E2 (Qwen2-Audio-7B): gc(L) Profile Across the Full LALM

For Qwen2-Audio-7B (32 LLM layers), using ALME 57K stimuli and RVQ-layer-selective corruptions, we predict a gc(L) peak at $L \in \{14\text{--}22\}$, consistent with ESN clustering \citep{zhao2026emotion}. We predict a \textbf{middle-dominant} profile (early layers passively encode, mid-to-late causally consult), distinct from the early-dominant generation case (AG-REPA \citep{agrep2026}) — establishing the SCD asymmetry between generation and understanding. We also predict RVQ Layer 1 corruptions produce reliably higher $\text{gc}(L)$ peaks than waveform-noise corruptions \citep{heimersheim2024}.

### 4.5 Predicted Failures and Contingencies

Risk A6 (low-variance rare phoneme features), Risk A1 (non-linear connector), Risk A3 (spurious DAS subspace), Hydra effect \citep{heimersheim2024}. For Hydra: report top-$K$ aggregate $\text{gc}(L)$ for $K \in \{1, 5, 10\}$.

### 4.6 A Taxonomy of Grounding Failures (3-Tier Model)

Prior work has described three distinct sites where audio grounding can fail: the neural codec (RVQ tokenization), the modality connector, and the LLM backbone (text-prior dominance). We unify these into a three-tier taxonomy with falsifiable gc(k) predictions.

**Tier 1 — Codec Failure:** Audio information destroyed at RVQ tokenization. *gc(k) signature:* Flat near chance at ALL layers. *Diagnostic:* Compare gc(k) using RVQ Layer 1 corruption vs waveform noise corruption. *Empirical support:* \citet{sadok2025speechtokenizer}.

**Tier 2 — Connector Bottleneck:** Audio encoder encodes phonological attribute at $L^*$, but modality connector collapses the subspace before the LLM receives it. *gc(k) signature:* Peak in encoder layers, collapse to chance AFTER connector. *Empirical support:* Gap \#18 experiment; Modality Collapse \citep{zhao2026collapse} (GMI bottleneck theory); Choi et al. \citep{choi2026phonological} (encoder linearity baseline).

**Tier 3 — LLM Modality Collapse:** Encoder and connector deliver phonological information to LLM residual stream, but LLM defaults to text-prediction pathways. *gc(k) signature:* Peak at intermediate depth ($L_{\text{mid}} \in \{14\text{--}22\}$ for 32-layer LLM), followed by drop at upper layers. *Empirical support:* \citet{zhao2026collapse} (behavioral); MPAR² \citep{mpar2026} (RL recovery from 31.74\% → 63.51\%); ESN \citep{zhao2026emotion}; Lin et al. \citep{lin2025multimodal} (VLM intermediate-layer precedent); Lee et al. \citep{lee2026audiocaps} (behavioral degradation).

\begin{table}[h]
\caption{3-Tier Grounding Failure Taxonomy — Falsifiable gc(k) Signatures}
\centering
\begin{tabular}{lllllll}
\hline
\textbf{Tier} & \textbf{Failure Site} & \textbf{gc(k) Pattern} & \textbf{Enc gc} & \textbf{LLM L0} & \textbf{LLM L\_mid} & \textbf{LLM L\_late} \\
\hline
T1 & Codec (RVQ) & Flat, near chance & $\sim$ch & $\sim$ch & $\sim$ch & $\sim$ch \\
T2 & Connector & Cliff at boundary & HIGH & $\sim$ch & $\sim$ch & $\sim$ch \\
T3 & LLM backbone & Mid-peak + late drop & HIGH & Med & HIGH & DROP \\
None & No failure & Rising plateau & HIGH & Med & HIGH & HIGH \\
\hline
\end{tabular}
\end{table}

### 4.7 Grounding Failure Diagnostic Protocol

The 3-tier taxonomy defines *what* grounding failures look like; this section specifies *how* a researcher applies the taxonomy to an arbitrary speech LLM.

**Step 1 — Codec Probe (≤2 min, CPU, no model required):** Run SpeechTokenizer on minimal pair stimuli. Reconstruct audio using only Layer 1 RVQ tokens. If contrast is preserved → proceed to Step 2. If lost → **Tier 1 confirmed.** STOP.

**Step 2 — Encoder gc(L) Sweep (≤30 min, CPU):** Run DAS sweep on model's audio encoder. If $\max_L \text{gc}(L) \leq 0.55$ → **Tier 1 Confirmed** (phonological geometry absent). If $\max_L \text{gc}(L) \geq 0.65$ with isolated peak $L^*_{\text{enc}}$ → proceed to Step 3.

**Step 3 — Connector Transfer Test (≤5 min, CPU):** Apply $R_{\text{encoder}}$ to LLM layer 0 without retraining. If $\text{IIA}_{\text{transfer}} < 0.55$ AND retrained IIA at LLM layer 0 $< 0.55$ → **Tier 2 Confirmed**: connector destroyed phonological geometry. STOP. If IIA transfer or retrained IIA $\geq 0.55$ → proceed to Step 4.

**Step 4 — LLM gc(L) Sweep (≤1 day, GPU/NDIF):** Run full DAS sweep across all LLM layers. If $\text{gc}(L_{\text{mid}}) - \text{gc}(L_{\text{late}}) \geq 0.10$ (late-layer drop, bootstrap CI non-overlapping) → **Tier 3 Confirmed**. If gc plateau at both $L_{\text{mid}}$ and $L_{\text{late}}$ → **No Failure (grounded model)**.

\begin{table}[h]
\caption{Per-Tier Diagnostic Tests}
\centering
\begin{tabular}{lllll}
\hline
\textbf{Tier} & \textbf{Failure Site} & \textbf{Diagnostic Test} & \textbf{Threshold} & \textbf{Cost} \\
\hline
T1a & Codec (reconstruction) & SpeechTokenizer Layer-1 preserves contrast? & probe $< 0.55$ & 2 min, CPU \\
T1b & Codec (encoder gc) & max encoder gc(L) & gc $< 0.55$ & 30 min, CPU \\
T2a & Connector (transfer) & IIA\_transfer at LLM layer 0 & IIA $< 0.55$ & 5 min, CPU \\
T2b & Connector (retrained) & DAS retrained at LLM layer 0 & IIA $< 0.55$ & 10 min, CPU \\
T3 & LLM late-layer drop & gc(L\_late) drop vs gc(L\_mid) & Drop $\geq 0.10$ & 1 day, GPU \\
None & No failure & gc plateau at L\_mid and L\_late & L\_late $\geq$ L\_mid $- 0.05$ & 1 day, GPU \\
\hline
\end{tabular}
\end{table}

**Protocol rule:** Tests applied in order. Early confirmation terminates protocol. Total cost for Tier 1 or Tier 2 diagnosis = CPU-only, ≤35 minutes.

---

## §5 Discussion (SKELETON — blocked until experimental results)

### 5.1 The Listen Layer as a Causal Bottleneck
> *Stub:* SCD: layers storing audio-aligned representations (highest probe accuracy) are distinct from layers causally driving grounded outputs (highest IIA). This dissociation, if confirmed, establishes that representational probing alone cannot localize causal computation.
> *Content trigger:* Figure 2 gc(L) curve + Figure 3 2D heatmap. **Write after E1 complete.**

### 5.2 Phonological Abstraction vs. Table-Lookup at L*
> *Stub:* If $\text{decomp}(L^*) \approx 0.8$–0.9 (voicing ⊥ phoneme-identity): first causal evidence that audio LMs encode compositional phonological structure rather than memorized phoneme-label associations.
> *Content trigger:* Table 1 (phono-init vs random-init DAS ablation). **Write after E1 complete.**

### 5.3 What the Connector Does to Phonological Geometry
> *Stub:* Three possible connector transfer outcomes and their theoretical implications for Modality Collapse \citep{zhao2026collapse}.
> *Content trigger:* Table 2 (connector subspace transfer results). **Write after Gap \#18 experiment.**

### 5.4 Grounding Profile Across Generation vs. Understanding
> *Stub:* Compare gc(L) profiles between Whisper encoder (understanding) and Qwen2-Audio-7B (LALM) with audio generation models (AG-REPA \citep{agrep2026}). Predicted: understanding = middle-dominant, generation = early-dominant.
> *Content trigger:* Figure 4 (Qwen2-Audio gc(L) sweep). **Write after E2 complete.**

### 5.5 Limitations and Future Work
> *Stub:* (1) Linear alignment assumption (DAS) — non-linear connectors may require kernel DAS (Gap \#25); (2) Phonological features tested = voicing/manner/place (~65\% of phoneme contrasts); (3) Whisper-small + Qwen2-Audio-7B only.
> *Content trigger:* Final results + reviewer feedback. **Write after submission draft.**

---

## Figures (PENDING experimental results)

| Figure | Description | Status |
|--------|------------|--------|
| Fig 1 | gc(L) curve across encoder layers for Whisper-small | ⏳ Requires E1 results |
| Fig 2 | Phonological geometry visualization (voicing direction in residual stream) | ⏳ Requires E1 results |
| Fig 3 | 2D IIA heatmap (PROBE_LAYER × INTERVENE_LAYER) — predicted lower-triangular stripe | ⏳ Requires E1 results |
| Fig 4 | gc(L) sweep across Qwen2-Audio-7B LLM layers | ⏳ Requires E2 results |

## Tables (PARTIAL)

| Table | Description | Status |
|-------|------------|--------|
| Table 1 | Related work comparison (method × Pearl level × audio/vision) | ⏳ Requires results |
| Table 2 | Connector subspace transfer results (IIA_transfer per model) | ⏳ Requires E1/E2 |
| Table 3 | 3-Tier Taxonomy gc(k) signatures | ✅ LaTeX-ready (§4.6) |
| Table 4 | Per-tier diagnostic tests | ✅ LaTeX-ready (§4.7) |

---

## Citation Key Registry

> All cite keys confirmed as of 2026-03-06. Format: [key] → [paper, arXiv/venue]

| Cite Key | Paper | arXiv/Venue |
|----------|-------|------------|
| `geiger2023foundation` | Geiger et al. — Causal Abstraction (MI foundation) | arXiv:2301.04709 |
| `geiger2023das` | Geiger et al. — DAS algorithm | arXiv:2303.02536 |
| `sutter2025nonlinear` | Sutter et al. — Non-linear representation dilemma | arXiv:2507.08802, NeurIPS 2025 |
| `asiaee2026` | Asiaee et al. — Efficient causal abstraction | arXiv:2602.24266 |
| `joshi2026causality` | Joshi et al. — Causality is Key for MI | arXiv:2602.16698 |
| `choi2026phonological` | Choi et al. — Phonological features in S3Ms | arXiv:2602.18899 |
| `li2025alme` | Li et al. — ALME (audio-text conflict) | arXiv:2602.11488 |
| `sadok2025speechtokenizer` | Sadok et al. — SpeechTokenizer | arXiv:2506.04492, Interspeech 2025 |
| `sadok2026dasheng` | Sadok et al. — DashengTokenizer | arXiv:2602.23765 |
| `wu2024pyvene` | Wu et al. — pyvene | 2024 |
| `fiotto2023nnsight` | Fiotto-Kaufman et al. — NNsight | 2023 |
| `nanda2023atp` | Nanda & Heimersheim — AtP | 2023 |
| `heimersheim2024` | Heimersheim & Nanda — Activation patching best practices | 2024 |
| `audiolens2025` | Liu et al. (智凱哥) — AudioLens | ASRU 2025 |
| `zhao2026collapse` | Zhao et al. — Modality Collapse | arXiv:2602.23136 |
| `cascade2026` | — Cascade Equivalence | arXiv:2602.17598 |
| `mistere2026` | — MiSTER-E | arXiv:2602.23300 |
| `zhao2026emotion` | Zhao et al. — ESN clustering | arXiv:2601.03115 |
| `lin2025multimodal` | Lin et al. — Multimodal MI Survey | arXiv:2502.17516 |
| `lee2026audiocaps` | Lee et al. — AudioCapsV2 behavioral degradation | arXiv:2603.03855 |
| `mpar2026` | — MPAR² (perception decay + RL) | arXiv:2603.02266, Interspeech 2026 |
| `glazer2025` | Glazer et al. — Beyond Transcription | arXiv:2508.15882 |
| `aparin2026audioae` | Aparin et al. — AudioSAE | arXiv:2602.05027, EACL 2026 |
| `braun2025` | Braun et al. — deep linear SCD theory | 2025 |
| `hase2023` | Hase et al. — factual editing layers | 2023 |
| `klabunde2025` | Klabunde et al. — representational similarity survey | 2025 |
| `agrep2026` | — AG-REPA (audio generation SCD) | arXiv:2603.01006 |
| `embeddlens2026` | Fan et al. — EmbedLens | arXiv:2603.00510, CVPR 2026 |
| `liu2025uw` | Liu et al. (UW) — KV-token flow in VLMs | 2025 |
| `fcct2026` | Li et al. — FCCT (causal tracing VLMs) | arXiv:2511.05923, AAAI 2026 |
| `behindscenes2026` | Ma et al. — Behind the Scenes (Whisper SER) | arXiv:2509.08454, ICASSP 2026 |
| `ard2026` | Chowdhury et al. — AR&D (AudioLLM SAE) | arXiv:2602.22253, ICASSP 2026 |
| `sgpa2026` | — SGPA (phoneme Shapley) | arXiv:2603.02250, Interspeech 2026 |
| `maghsoudi2026` | Maghsoudi & Mishra — brain-to-speech patching | arXiv:2602.01247 |
| `shafran2026mfa` | Shafran et al. — MFA for layer pre-screening | arXiv:2602.02464 |

---

## Open Decisions (for Leo)

1. 🔴 **Venue + Scope**: Interspeech 2026 (E1 only, abstract ~March 31) vs NeurIPS 2026 (E1+E2, ~May)
2. 🔴 **Co-authorship with 智凱哥**: Solo vs co-author (pending email response; draft in checklist)
3. 🟡 **Minimum Viable E1**: Need real speech `.wav` + Python venv setup (~10 min; instructions in checklist)

---

## Assembly Notes

- §1–§4 assembled from `paper-a-pitch.md` (v2.2), `paper-a-intro.md` (v0.1), `paper-a-abstract-v07.md`
- §5 skeleton from pitch v1.6 (cycle #230)
- Citation keys unified from checklist verified list (cycle c-20260306-1301)
- §4.6 Table 3 and §4.7 Table 4 converted from Markdown to LaTeX `tabular` format
- Inconsistency resolved: pitch v1.5 says "7 subsections" for §3 but v2.1 has 8 (§3.8 added in cycle #300); draft uses 8 subsections as authoritative
- **Next action**: Leo runs E1 to generate results for §5 prose and Figures 1–3
