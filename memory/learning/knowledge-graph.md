# 🗺️ Knowledge Graph

> 概念、論文、連結。Paper ideas 和 must-read list 見 goals.md（single source of truth）。

## Mech Interp × Speech（主方向）
- 現有工作僅 4 篇（2025-08 至 2026-02）
- 關鍵方法: activation patching, probing, SAE, logit lens
- Vision 有 Prisma toolkit，speech 無對應
- 相鄰: text interp (TransformerLens), vision interp (Prisma), radiology MLLM + SAE

## Audio Evaluation（AudioMatters 相關）
- UniWhisper: unified instruction format, 20-task, encoder-only eval
- 現有 benchmarks 都 narrow-scoped → AudioMatters 填 cross-scenario gap

## 概念索引
| 概念 | 來源 | 筆記 |
|------|------|------|
| Activation patching | Text mech interp | 需遷移到 speech |
| SAE (Sparse Autoencoder) | Anthropic / Radiology MLLM | 可用於 feature discovery |
| Logit lens | Text interp | 觀察 token prediction 如何逐層變化 |
| Unified instruction format | UniWhisper | 異質 tasks 統一成 instruction→answer |

## 研究路徑圖（Method Transfer）
```
Text Mech Interp (TransformerLens, SAE)
    ↓ transfer methods
Vision Mech Interp (Prisma toolkit)
    ↓ template to follow
Speech Mech Interp ← WE ARE HERE (building)
    ↓ apply to
Omni-LLMs (Qwen-Audio, SALMONN, Gemini)
```

## MacBook-Feasible Experiments (no GPU needed)
- TransformerLens on GPT-2 (CPU fine for small models)
- Probing on pre-computed Whisper activations
- Logit lens visualization (post-hoc, no training)
- SAE analysis on saved activations

## 待追蹤研究者
- Kawamura et al. (audio SSL neuron dissection, 2026)
- Glazer et al. (mech interp ASR, IBM?, 2025)
- Sonia Joseph / Lee Sharkey (Prisma, vision interp)
