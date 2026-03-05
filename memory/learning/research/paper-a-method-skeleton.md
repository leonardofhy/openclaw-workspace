# Paper A — Method Section Skeleton
> "Localizing the Listen Layer in Speech LLMs"
> Status: Skeleton — headers + equation placeholders + figure stubs. Fill prose in.
> Created: 2026-03-02 by autodidact (Q022)

---

## 3. Method

### 3.1 Problem Formulation

Let **M** be a large audio-language model (LALM) with layers $\ell \in \{1, \ldots, L\}$.
Given a conflict stimulus $(a, t, q)$ — audio $a$, contradicting text context $t$, and question $q$ —
define the **grounding coefficient** at layer $\ell$ as:

$$
\text{gc}(\ell) = \text{IIT-acc}_\text{audio}(\ell)
$$

[TODO: expand — cite Geiger et al. 2301.04709; define IIT-acc formally as task recovery under DAS rotation]

The **Listen Layer** $\ell^*$ is:

$$
\ell^* = \arg\max_{\ell} \; \text{gc}(\ell)
$$

We interpret $\ell^*$ as the depth at which audio representations are *causally consulted* to resolve audio-text conflict.

---

### 3.2 Stimuli

#### 3.2.1 Phase 1: Phonological Minimal Pairs (Whisper-small)

We use phonological minimal pairs from Choi et al. (phonetic-arithmetic) as clean/corrupt stimulus pairs.

- **Contrast:** voicing contrasts [b]/[p], [d]/[t]
- **Rationale:** [TODO: 1 sentence — minimal phonetic change = principled interchange intervention]
- **Size:** [TODO: N pairs]

These stimuli serve dual purpose: (1) Phase 1 Listen Layer localization, (2) Gap #18 phonological geometry test (§A.1).

#### 3.2.2 Phase 2: Audio-Text Conflict Pairs (Qwen2-Audio-7B)

We use the ALME 57K audio-text conflict corpus (Li et al., 2025, arXiv:2602.11488).

- **Format:** (audio clip, contradicting text context, factual question)
- **Coverage:** [TODO: domain breakdown — speech, sound events, music?]
- **Selection:** [TODO: subset used for patching sweep, if any filtering applied]

---

### 3.3 Representation Extraction: MMProbe

To extract a causal audio direction at each layer, we use the **mean-difference probe (MMProbe)**:

$$
\vec{v}_\text{audio}(\ell) = \frac{1}{|C^+|}\sum_{i \in C^+} h_\ell^{(i)} \;-\; \frac{1}{|C^-|}\sum_{i \in C^-} h_\ell^{(i)}
$$

where $C^+$ and $C^-$ are the positive (audio-grounded) and negative (text-dominated) examples.

**Why MMProbe over LR probe:** [TODO: 1 sentence — LR probe finds discriminative direction ≠ causal direction; diff-of-means aligns with residual stream geometry]

---

### 3.4 Causal Intervention: Distributed Alignment Search (DAS)

We apply **denoising activation patching** via DAS (Geiger et al., 2301.04709) using NNsight:

**Algorithm:**
1. For each layer $\ell$:
   a. Extract clean hidden state $h_\ell^\text{clean}$ (audio-grounded input)
   b. Apply DAS rotation $R_\ell$ around $\vec{v}_\text{audio}(\ell)$ at layer $\ell$ of the corrupt input
   c. Measure task recovery: $\text{IIT-acc}(\ell) = P(\hat{y} = y_\text{audio} \mid \text{patched at } \ell)$
2. Sweep independently: **probe\_layer** (where $\vec{v}$ is extracted) and **intervene\_layer** (where patch is applied)
3. Report the full 2D sweep heatmap as Figure 1

**Implementation:** NNsight (not circuit-tracer — CLT does not support cross-attention in audio-LLMs)

**Computational cost:** [TODO: estimated per-layer time; Whisper-small on MacBook ~3h; Qwen2-Audio-7B on NDIF GPU ~?]

> **Figure 1 stub:** 2D heatmap — probe_layer × intervene_layer → IIT-acc. Expected: diagonal band with peak at $\ell^* \approx$ 50% depth.

---

### 3.5 Normalized Grounding Coefficient (Phase 2 only)

For Qwen2-Audio-7B, we compute both audio and text grounding coefficients and normalize:

$$
\text{gc}_\text{norm}(\ell) = \frac{\text{gc}_\text{audio}(\ell)}{\text{gc}_\text{audio}(\ell) + \text{gc}_\text{text}(\ell)}
$$

This controls for the baseline causal effect of text-context representations and isolates audio-specific consultation.

> **Figure 2 stub:** Two curves — $\text{gc}_\text{audio}(\ell)$ and $\text{gc}_\text{text}(\ell)$ — across layers. Expected: audio peaks mid-network, text peaks early or late.

---

### 3.6 Listen Layer Dynamics (Phase 3 Extensions)

To test whether $\ell^*$ is a stable architectural property or a learned behavior:

**3.6.1 Fine-tuning shift:** Apply LoRA-SER to Whisper-large-v2; re-measure gc(ℓ); compare $\ell^*_\text{base}$ vs $\ell^*_\text{ft}$.
[TODO: LoRA rank, learning rate, dataset (SER = Speech Emotion Recognition)]

**3.6.2 Failure mode suppression:** For text-dominant failure cases (where M outputs text-grounded answer despite audio contradiction), plot gc(ℓ) — expect flattened curve (no clear $\ell^*$).

> **Figure 3 stub:** gc(ℓ) curves overlaid — baseline vs LoRA-SER vs failure cases.

---

## Key Notations (for paper consistency)

| Symbol | Meaning |
|--------|---------|
| $\ell^*$ | Listen Layer (argmax of gc) |
| gc(ℓ) | Grounding coefficient at layer ℓ |
| $\vec{v}_\text{audio}(\ell)$ | MMProbe audio direction at layer ℓ |
| $R_\ell$ | DAS rotation matrix at layer ℓ |
| IIT-acc | Task recovery accuracy under DAS patch |
| $C^+, C^-$ | Audio-grounded / text-dominated example sets |
| LALM | Large Audio-Language Model |

---

## TODOs Before Submission

- [ ] Fill formal IIT-acc definition (§3.1) — cite Geiger et al.
- [ ] Add phonological pair count and ALME subset size (§3.2)
- [ ] Add 1-line MMProbe justification (§3.3)
- [ ] Add Qwen2-Audio compute estimate (§3.4)
- [ ] Fill LoRA-SER hyperparameters (§3.6)
- [ ] Decide: include Phase 3 in main paper or appendix?
- [ ] Align notation with Phase 1 results before finalizing §3.5
