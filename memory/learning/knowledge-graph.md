# 🗺️ Knowledge Graph

> 概念、論文、連結。Paper ideas 見 goals.md（single source of truth）。
> Last updated: 2026-02-26 (based on deep research report)

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
- **AudioSAE (Aparin et al., 2026, EACL)** — SAE on Whisper/HuBERT all layers, feature steering 減少 false detection [arXiv:2602.05027]
- Parra et al. (2025, EMNLP) — interpretable sparse features for SSL speech models
- SAE on speaker embeddings (Titanet) — monosemantic factors [arXiv:2502.00127]

### C) Audio-Language Models（最接近 Leo）
- **🔥 AudioLens (智凱哥, 2025, NTU 李宏毅 lab)** — logit-lens for LALMs, attribute tracking [arXiv:2506.05140]（Leo 最近的 labmate，AudioMatters co-1st author）
- Beyond Transcription 也涵蓋 Qwen2-Audio
- **SPIRIT (EMNLP 2025, MBZUAI)** — activation patching 防禦 audio jailbreak [arXiv:2505.13541]

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
