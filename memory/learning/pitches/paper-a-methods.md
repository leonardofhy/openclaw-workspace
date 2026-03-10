# Paper A — Methods Section Scaffold
**Track:** T3 (Listen vs Guess)
**Version:** v0.1 | **Date:** 2026-03-06
**Task:** Q054

---

## 3. Methods (~700-word scaffold)

### 3.1 Problem Setup

Let $\mathcal{M}$ be a pre-trained audio language model with encoder $\text{Enc}$ and decoder $\text{Dec}$. Given an audio waveform $x$, $\text{Enc}$ maps $x$ to a sequence of hidden states $\{h^{(k)}\}_{k=1}^{K}$ where $k$ indexes encoder layers. The decoder autoregressively generates transcript $y = (y_1, \ldots, y_T)$ conditioned on $h^{(K)}$ (or a pooled representation thereof).

**Listen vs Guess dichotomy.** We distinguish two modes of operation:
- **Listen mode**: $y$ is primarily determined by acoustic evidence in $x$
- **Guess mode**: $y$ is primarily determined by the decoder's language prior, with $x$ contributing minimally

We seek a scalar metric that, given $(x, y)$, quantifies the degree to which $x$ causally determines $y$ at each layer $k$.

---

### 3.2 Grounding Coefficient gc(k)

**Definition.** The grounding coefficient at layer $k$ for sample $(x, y)$ is:

$$\text{gc}(k) = \frac{\mathbb{E}_{x' \sim \mathcal{N}(x)}[p(y \mid h^{(k)}_{x}) - p(y \mid h^{(k)}_{x'})]}{p(y \mid h^{(K)}_{x})}$$

where $x'$ is a corrupted version of $x$ obtained by masking or noise perturbation, and $h^{(k)}_{x}$ denotes the layer-$k$ representation from the clean run.

**Interpretation.** gc(k) ≈ 1 means layer $k$'s representation causally determines the output (acoustic information intact). gc(k) ≈ 0 means the output is invariant to layer $k$'s acoustic content (language prior dominates).

**Listen Layer k\*.** We define the Listen Layer as:

$$k^* = \arg\max_k \text{gc}(k)$$

The distribution of $\text{gc}(k^*)$ across a corpus characterizes whether the model is predominantly Listening (high $\text{gc}(k^*)$) or Guessing (low $\text{gc}(k^*)$) on that data.

---

### 3.3 Corruption Protocol

We consider three corruption strategies, each targeting different aspects of acoustic information:

| Corruption Type | Method | Targets |
|----------------|--------|---------|
| **Gaussian Noise** | Add $\mathcal{N}(0, \sigma^2)$ to raw waveform | Broadband acoustic detail |
| **Frequency Masking** | Zero out F random frequency bands (SpecAugment-style) | Phonetic features |
| **Silence Pad** | Replace $x$ with zero waveform | All acoustic content |

For each sample, we run the model on both $x$ (clean) and $x'$ (corrupted), hook activations at every layer, and compute the output probability shift.

---

### 3.4 Hook Architecture

We use PyTorch forward hooks to intercept encoder activations at every layer during inference. No gradient computation is required.

```
Audio Input x
    → Whisper Encoder
        → [Layer 1 hook] → h^(1)
        → [Layer 2 hook] → h^(2)
        → ...
        → [Layer K hook] → h^(K)
    → Decoder
        → Output logits p(y | h^(K))
```

Key implementation details:
- **Patching**: During the corrupted run $x'$, we can patch $h^{(k)}_{x'}$ ← $h^{(k)}_x$ at specific layers to measure the counterfactual effect of restoring acoustic information at exactly layer $k$
- **Model support**: Whisper-tiny, Whisper-base, Whisper-small (CPU feasible); Whisper-large, Qwen2-Audio (GPU, Leo approval required)
- **Memory**: Layer-wise activation storage requires ~O(K × T × D) floats; for Whisper-base, this is ~32 × 1500 × 512 = 24M floats per sample (≈96 MB), manageable on CPU

---

### 3.5 Evaluation Protocol

**Corpus construction (CPU-feasible).**
- Synthetic: generate audio via TTS (pyttsx3 / gTTS) for 100 templated sentences with known ground-truth transcriptions
- Real (requires Leo): LibriSpeech dev-clean subset (100 samples) or provided .wav files
- Adversarial: apply JALMBench-style audio perturbations to 20 samples

**Metrics per sample:**
1. `gc(k)` curve across all layers (primary output)
2. `k*` = argmax layer
3. `gc_at_kstar` = scalar grounding score
4. `wer_clean` / `wer_corrupted` for sanity check
5. Binary label: Listen (gc(k*) > θ) vs Guess (gc(k*) ≤ θ), threshold θ = 0.5

**Aggregate metrics:**
- Mean gc(k) curve per dataset split
- Listen rate = fraction of samples with gc(k*) > θ
- Layer distribution of k* (histogram)
- Correlation: gc(k*) vs WER degradation on corrupted input

**Baselines:**
- Random baseline: gc(k) = 0.5 (uniform)
- Entropy-based baseline: output entropy of corrupted run (no causal patching)
- Linear probe baseline: probing accuracy for acoustic features at each layer

---

### 3.6 Experimental Setup (CPU-Feasible Plan)

| Parameter | Value |
|-----------|-------|
| Model | Whisper-tiny (39M params) |
| Hardware | CPU only (no GPU required) |
| Corpus size | 100 synthetic + 20 adversarial |
| Corruption runs | 3 per sample (noise/mask/silence) |
| Est. runtime | ~2 min/sample → ~4h total (parallelizable) |
| Output | `results/gc_curves.json`, `results/summary_table.md` |

**Phase 2 (GPU, Leo approval):** Scale to Whisper-large and Qwen2-Audio; use LibriSpeech full dev-clean (2703 samples); run causal patching experiments Q001, Q002.

---

### 3.7 Connection to Downstream Applications

The gc(k) metric is designed to be modality-agnostic and task-agnostic:

- **Hallucination detection**: Flag samples where gc(k*) < θ as high-hallucination risk before transcription
- **Audio jailbreak detection** (Track T5): Anomalously high gc(k*) on adversarial audio indicates acoustic-level manipulation; use as zero-shot detector
- **Selective decoding**: Route low-gc samples to a more conservative decoder or abstain

---

*TODO markers for full paper:*
- [ ] Add formal proof that gc(k) = 0 iff output invariant to $h^{(k)}$ (information-theoretic argument)
- [ ] Add diagram: clean vs corrupted activation flow + patching arrow
- [ ] Clarify: "corruption" must not change decoder prior (i.e., silence pad changes what decoder expects — need to control for this)
- [ ] Reference ROME / DAS patching formalism precisely
- [ ] Check: does Whisper use cross-attention to audio at every decoder step? If yes, patching at final encoder layer is clean; if not, gc(k) needs to account for mid-decoding attention
