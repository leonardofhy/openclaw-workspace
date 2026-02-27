# Project: AudioMatters

## Overview
- 目標會議：**Interspeech 2026**
- 投稿 Deadline：**2025-02-25**
- 作者序：Leo (1st), 智凱哥 (Co-1st), 晨安哥 (2nd)
- Leo 的**人生第一篇論文，一作身分**

## Timeline
- `2026-02-18 16:58` `[CONTEXT]` 每週五下午 15:00 Meeting。本週目標：提前討論 + 整合新模型/Benchmark 到實驗結果。
- `2026-02-20` `[MILESTONE]` 會議確認作者序。實驗數據「過於充足」，需篩選精華放入論文。討論論文脈絡、補充實驗方向。專題生因貢獻不足不列入作者序。
- `2026-02-22` `[PROGRESS]` Leo 帶病推進約 3 小時工作（14:45-16:15 + 17:15-18:40）。進度穩定。
- `2026-02-22` `[NOTE]` Todoist 任務「整合新模型與 Benchmark 到實驗結果」due 2/27。

## Key Tasks (Remaining)
- [ ] 論文文字段落精修（方法、實驗、結果討論）
- [ ] 結果圖表最終版
- [ ] Related work 段落
- [ ] 排版格式確認（Interspeech template）
- [ ] 共同作者 review & sign-off

## Notes
- Leo 的研究模式：有 deadline 壓力 + 實驗室有人陪 = 高效；一個人在家 + 任務模糊 = 容易拖延
- 晨安哥建議：「先想論文要放什麼」再決定補充實驗方向
- `2026-02-27 22:07` `[PLAN]` 2026-02-27 Leo shared a GPT-5.2 Pro paper blueprint for speech LLM mechanistic interpretability: TAP (Attribution search -> Confirmatory patching -> Subspace verification), with Figure1-3 layout and abstract draft. Treat as draft scaffold; verify all citations and narrow initial scope (start from DeSTA + one comparison model) before writing claims.
- `2026-02-27 22:09` `[LITERATURE]` 2026-02-27 Leo provided a GPT-5.2 Pro literature map (20 papers) for speech LLM mechanistic interpretability, grouped by causal intervention/patching/SAE/grounding/alignment. Key reusable backbone: #19 activation patching best practices, #1 AudioSAE, #2 AR&D, #5 group-sparse multimodal SAE, #14 multimodal causal tracing, #8 SPIRIT. Core proposed gap: alignment-aware speech causal tracing with token-time alignment and feature->circuit->behavior validation.
- `2026-02-27 22:11` `[PLAN]` 2026-02-27 Leo shared a detailed Localizing-the-Listen-Layer blueprint: strong evidence for a layer-range/interface view (not necessarily a single layer), with 3 single-GPU MVPs (1) layer-wise audio attention suppression curve, (2) clean-vs-corrupt activation patching causal tracing, (3) layer-restricted LoRA sweep. Suggested execution order: Exp1 -> Exp2 -> Exp3 and target outcome is layer sensitivity + causal recovery + trainable-layer localization.
