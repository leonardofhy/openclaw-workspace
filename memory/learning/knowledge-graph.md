# 🗺️ Knowledge Graph

> 概念、論文、連結。Paper ideas 見 goals.md（single source of truth）。
> Last updated: 2026-02-26 17:00 (cycle #7: AudioLens deep read)

## Mech Interp × Speech/Audio — Field Map (2026)

### A) ASR / Whisper MI
- Ellena Reid (2023, LessWrong) — 早期 Whisper MI，phoneme-like features, localized attention
- **Glazer et al. "Beyond Transcription" (2025, aiOla)** — 🟢 DEEP READ — logit lens + probing + activation patching for Whisper-large-v3 + Qwen2-Audio [arXiv:2508.15882]
  - KEY METHODS: Encoder Lens (novel), saturation layer, white-noise reference patching
  - KEY FINDINGS: encoder encodes context (not just acoustics!), hallucination detectable from decoder residual stream (93.4% acc at layer 22), repetition = specific cross-attn heads
  - Speaker gender probing peaks layer 25 (94.6%), accent peaks layer 22 (97%), noise peaks layer 27 (90%)
  - DIRECT LINK to Track 3 (Listen vs Guess): saturation layer + patching sensitivity → operationalize grounding coefficient
- Mozilla Builders (2024) — Whisper SAE (L1, TopK), phonetic/positional features
- Open tools: whisper-interp (GitHub), whisper_logit_lens (GitHub)

### B) Speech Encoder SAEs
- **AudioSAE (Aparin et al., 2026, EACL)** — 🟢 DEEP READ — SAE on all 12 layers of Whisper/HuBERT [arXiv:2602.05027]
  - KEY SETUP: TopK/BatchTopK SAE, 8x expansion (768→6144 features), all-layer coverage
  - KEY FINDINGS: >50% feature stability across seeds; phoneme acc 0.92/0.89; **70% hallucination FPR reduction via top-100 feature steering** (α=1, WER cost only +0.4%)
  - LAYER INSIGHT: Whisper layer 6-7 = transition from audio-level → frame-level speech encoding
  - SPEECH ≠ TEXT: erasing speech concepts needs ~2000 features; text SAE needs only ~tens → phonetic info is distributed
  - EEG correlation: SAE features align with brain activity during speech perception (Pz electrode, 0-500ms lags)
  - KEY GAP: only encoder models; no LALMs; phonetic auto-interpretation failed (bad caption model)
  - CODE: https://github.com/audiosae/audiosae_demo
- Parra et al. (2025, EMNLP) — interpretable sparse features for SSL speech models
- SAE on speaker embeddings (Titanet) — monosemantic factors [arXiv:2502.00127]

### C) Audio-Language Models（最接近 Leo）
- **🔥 AudioLens (Neo Ho, Yi-Jyun Lee, Hung-yi Lee 2025, NTU → ASRU 2025)** — 🟢 DEEP READ — logit-lens on LALMs (DeSTA2, Qwen-Audio, Qwen2-Audio); auditory attribute perception [arXiv:2506.05140]
  - KEY METHODS: Layer-wise Information Score (= layer accuracy via vocab projection), Critical Layer (weighted avg layer index above threshold), 3 prompt formats
  - KEY FINDINGS:
    - Attribute info ≠ monotonic with depth; sharp drops+recoveries common
    - Success mode = info rises with depth; Failure mode = peaks mid-layer then drops
    - Earlier critical layer → better accuracy (more layers to refine)
    - **LALMs query audio tokens directly >> aggregate at text positions** (= "listen not guess")
    - No-training improvement: enrich deep layers with early attribute-rich reps → +16.3% acc
  - CRITICAL GAP: only Logit Lens (observational), NO causal patching → cannot prove causal grounding
  - DIRECT LINK: operationalizes "Listen vs Guess" (Track 3); Leo can extend with causal interventions
  - NOTE: 智凱哥 = Chih-Kai Yang (ckyang1124), GitHub: https://github.com/ckyang1124/AudioLens
  - CROSS-PAPER: critical layer ↔ saturation layer (Beyond Transcription); potential unified framework
- Beyond Transcription 也涵蓋 Qwen2-Audio
- **🟢 SPIRIT (Djanibekov et al., EMNLP 2025, MBZUAI)** — 🟢 DEEP READ — activation patching for audio jailbreak defense [arXiv:2505.13541]
  - KEY SETUP: PGD attack on Qwen2-Audio + LLaMa-Omni (both share Whisper encoder); AdvBench 246 samples
  - KEY FINDINGS: PGD achieves 100% ASR in some categories; activation patching (inject clean activations) reduces to ~1% with negligible utility cost; bias addition and neuron pruning also effective
  - BEST DEFENSE: patch at critical encoder-output/early-LM layers (found empirically, not mechanistically)
  - KEY GAP: no explanation of *where* adversarial signal lives; no SAE-guided patching
  - CODE: https://github.com/mbzuai-nlp/spirit-breaking
  - LEO'S OPPORTUNITY: AudioSAE features → surgically suppress adversarial features vs SPIRIT's blind layer patching

### D) Generative Audio/Music MI
- SMITIN (2024), Facchiano (2025), TADA! (2026) — attention steering, SAE for music concepts
- TADA!: 少數 attention layers 控制 semantic concepts [arXiv:2602.11910]

### E) Brain-to-Speech
- Maghsoudi & Mishra (2026) — cross-mode patching, causal scrubbing [arXiv:2602.01247]

### F) Neural Audio Codecs（新角度）
- EnCodec → discrete tokens → 讓 audio MI 變成「LM-like」
- AudioLM, MusicGen/AudioGen 都基於 codec tokens
- MI 意義：token-level patching, SAE on residual stream 直接可用
- 目前 MI 研究幾乎空白

## 核心方法工具箱
→ 詳見 `skills/autodidact/references/toolbox.md`

## 🔗 Cross-Paper Connections (emerging picture)

| Concept A | Paper A | ↔ | Concept B | Paper B | Insight |
|-----------|---------|---|-----------|---------|---------|
| Saturation layer (encoder) | Beyond Transcription | ↔ | Critical layer (LALM) | AudioLens | Both = "where attribute resolves" — unify into shared framework? |
| Encoder encodes context | Beyond Transcription | ↔ | LALMs query audio directly | AudioLens | Two views of same phenomenon: audio pathway carries semantic context |
| Patching shows causal grounding | Beyond Transcription | ↔ | Logit Lens = only observational | AudioLens | **Gap = Leo's opportunity**: add causality to AudioLens framework |
| Hallucination in decoder residual | Beyond Transcription | ↔ | Failure = mid-layer peak then drop | AudioLens | Same failure signature? Check if AudioLens failure cases = hallucinations |

### Research Opportunity Crystallized (2026-02-26)
> **"Causal AudioLens"**: Take AudioLens methodology (Logit Lens + critical layer) → add patching experiments → produce grounding_coefficient = ratio of (Δacc when audio patched) / (Δacc when text patched). This is the missing causal link in AudioLens, and it directly operationalizes Track 3 "Listen vs Guess" hypothesis.

### New Synthesis Insight — Three Papers, One Phenomenon (2026-02-26 Cycle #8)
> **Whisper layers 6-7 = semantic-acoustic transition zone**:
> - AudioSAE: audio-level speech peaks layer 6, then drops → frame-level peaks layer 7 (phonetic encoding transition)
> - Beyond Transcription: "saturation layer" = where encoder commits to transcription
> - AudioLens: "critical layer" = where attribute resolves in LALM
> **Hypothesis**: All three independently found the same architectural transition point from different methodological angles. Testing this directly (SAE + saturation layer + critical layer on same model) = tractable experiment on MacBook.

### 🧪 Experiment 0: Triple Convergence Test (Cycle #11 crystallized — 2026-02-26)

**Q:** Do AudioSAE layer 6-7 transition, Beyond Transcription saturation layer, and AudioLens critical layer point to the *same* architectural feature in Whisper?

**Setup (MacBook-feasible, Whisper-tiny or small):**
1. **Saturation layer**: Run Encoder Lens on Whisper encoder — find the layer where logit lens output stabilizes (= saturation layer from Beyond Transcription). Expected: ~layer 6-7 for small model.
2. **Norm/CKA jump**: Use `whisper_hook_demo.py` — look for the layer where CKA similarity to final layer jumps (= representation converges). Expected: ~layer 6-7.
3. **Feature stability**: If SAE trained: compare feature stability profile per layer (from AudioSAE paper, Fig. 3). Not immediately runnable without SAE training, but CKA can proxy it.
4. **Claim**: If all three methods point to the same transition zone → strong evidence for a universal "semantic crystallization layer" in Whisper encoder.

**Minimal viable version (no SAE training needed):**
- `whisper_hook_demo.py` already captures layer norms + CKA
- Add: logit-lens decoder vocab projection at each layer (requires decoder embedding matrix)
- Result: saturation curve + CKA curve on same plot → visual test of convergence hypothesis

**Impact if confirmed:**
- Novel empirical finding (all prior papers used different models/methods)
- Directly supports "Causal AudioLens" paper: "first experiment" section
- Conference-quality if extended to multiple models (Whisper variants + HuBERT)

**Next step:** Extend `whisper_hook_demo.py` to include logit-lens projection → run → see if CKA jump and saturation layer coincide. ~2-3 hours coding.

| Concept A | Paper A | ↔ | Concept B | Paper B | New Connection |
|-----------|---------|---|-----------|---------|----------------|
| Layer 6-7 speech transition | AudioSAE | ↔ | Saturation layer | Beyond Transcription | Same phenomenon? |
| Layer 6-7 frame-level encoding | AudioSAE | ↔ | Critical layer | AudioLens | Three papers converge |
| Steering pipeline (suppress top-100) | AudioSAE | ↔ | White-noise patching | Beyond Transcription | Causal intervention templates |
| Speech concepts = distributed (2000 feat) | AudioSAE | ↔ | Encoder encodes context | Beyond Transcription | Distributed = context-sensitive |
| SAE feature steering (AudioSAE) | AudioSAE | ↔ | Blind activation patching (SPIRIT) | SPIRIT | **Gap → SAE-guided safety patching**: know WHICH features to suppress (not just which layers) |
| 70% hallucination FPR reduction | AudioSAE | ↔ | 99% jailbreak defense | SPIRIT | Both use sparse activation intervention; sparse+interpretable (SAE) > dense (SPIRIT) |
| Triple Convergence layer 3 (Whisper-base) | whisper_hook_demo | ↔ | Best defense = specific layer patching | SPIRIT | Does SPIRIT's optimal defense layer = Triple Convergence transition zone? |

### G) Activation Patching Methodology
- **Heimersheim & Nanda (2024)** — 🟢 DEEP READ — "How to Use and Interpret Activation Patching" [arXiv:2404.15255]
  - KEY DISTINCTION: Denoising (clean→corrupt) tests SUFFICIENCY; Noising (corrupt→clean) tests NECESSITY — NOT symmetric!
  - AND circuits: use noising (finds all components); OR circuits: use denoising
  - METRICS hierarchy: logit diff > logprob > probability > accuracy (for exploratory patching)
  - ⚠️ Gaussian noise patching (Causal Tracing) is fragile — sensitive to noise level, can be ineffective
  - ⚠️ Backup behavior (Hydra effect): ablating key component activates backup → component looks less important than it is
  - Path patching: isolates direct A→B connections, needed for confirmatory circuit verification
  - AUDIO IMPLICATION: Beyond Transcription's white-noise patching = suboptimal corruption; minimal pair audio = cleaner evidence
  - NEW GAP (Leo): all audio MI papers use suboptimal corruptions — minimal pairs would be methodologically cleaner and more publishable

---

## 關鍵研究者/團隊
- **NTU 李宏毅 lab** — AudioLens (智凱哥！Leo 主場)
- aiOla Research (Glazer) — ASR MI, hallucination causal analysis
- Huawei Noah's Ark (Aparin) — AudioSAE
- MBZUAI — SPIRIT (audio safety)
- Stanford (Atticus Geiger) — causal abstraction theory + pyvene
- Neel Nanda — activation patching best practices, TransformerLens
- Mozilla Builders — Whisper SAE tooling
- Ellena Reid — early Whisper MI (LessWrong)
- Yuan Gong (MIT) — AST/SSAST audio transformers
