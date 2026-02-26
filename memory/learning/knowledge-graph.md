# 🗺️ Knowledge Graph

> 概念、論文、連結。Paper ideas 見 goals.md（single source of truth）。
> Last updated: 2026-02-26 (based on deep research report)

## Mech Interp × Speech/Audio — Field Map (2026)

### A) ASR / Whisper MI
- Ellena Reid (2023, LessWrong) — 早期 Whisper MI，phoneme-like features, localized attention
- **Glazer et al. "Beyond Transcription" (2025, aiOla)** — logit lens + patching for ASR, hallucination/repetition 因果分析 [arXiv:2508.15882]
- Mozilla Builders (2024) — Whisper SAE (L1, TopK), phonetic/positional features
- Open tools: whisper-interp (GitHub), whisper_logit_lens (GitHub)

### B) Speech Encoder SAEs
- **AudioSAE (Aparin et al., 2026, EACL)** — SAE on Whisper/HuBERT all layers, feature steering 減少 false detection [arXiv:2602.05027]
- Parra et al. (2025, EMNLP) — interpretable sparse features for SSL speech models
- SAE on speaker embeddings (Titanet) — monosemantic factors [arXiv:2502.00127]

### C) Audio-Language Models（最接近 Leo）
- **🔥 AudioLens (Yang et al., 2025, NTU 李宏毅 lab!)** — logit-lens for LALMs, attribute tracking [arXiv:2506.05140]
- Beyond Transcription 也涵蓋 Qwen2-Audio
- **SPIRIT (EMNLP 2025, MBZUAI)** — activation patching 防禦 audio jailbreak [arXiv:2505.13541]

### D) Generative Audio/Music MI
- SMITIN (2024), Facchiano (2025), TADA! (2026) — attention steering, SAE for music concepts
- TADA!: 少數 attention layers 控制 semantic concepts [arXiv:2602.11910]

### E) Brain-to-Speech
- Maghsoudi & Mishra (2026) — cross-mode patching, causal scrubbing [arXiv:2602.01247]

## 核心方法工具箱
| 方法 | 用途 | 工具 |
|------|------|------|
| Activation patching | 因果定位 | TransformerLens |
| Logit lens / vocab projection | 逐層 attribute tracking | 自建 |
| SAE (Sparse Autoencoder) | Feature discovery + steering | 自建 / AudioSAE |
| Linear probing | 資訊存在性測試 | sklearn / custom |
| Feature steering | 干預 + 控制 | SAE-based |

## 關鍵研究者/團隊
- **NTU 李宏毅 lab** — AudioLens (Leo 主場！)
- aiOla Research (Glazer) — ASR MI
- Huawei Noah's Ark (Aparin) — AudioSAE
- MBZUAI — SPIRIT (audio safety)
- Mozilla Builders — Whisper SAE tooling
- Ellena Reid — early Whisper MI (LessWrong)
