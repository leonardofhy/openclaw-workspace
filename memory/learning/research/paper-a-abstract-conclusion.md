# Paper A: Abstract + Conclusion Skeletons
> Track: T3 | Task: Q037 | Created: 2026-03-03 | Status: Skeleton (Leo fills numbers)
> Format target: Interspeech 2026 (4 pages, ~200-word abstract)

---

## Abstract (target: ~200 words)

<!-- HOOK: 1–2 sentences. Why audio-language models matter + the gap. -->
Large audio-language models (LALMs) process both speech and text, yet it remains unclear *where* in the forward pass audio representations become causally decisive for the model's output.

<!-- GAP/PROBLEM: 1–2 sentences. What prior work does + what it can't answer. -->
Prior work characterizes audio-vs-text modality dominance behaviorally (ALME, AudioLens; Billa 2026 formalizes this as the Cascade Equivalence Hypothesis — speech LLMs behave like ASR+LLM pipelines on text-sufficient tasks and lose to cascades under 0dB noise) but does not localize the *causal* locus of audio consultation to specific layers or components.

<!-- METHOD: 2–3 sentences. What we do + key concepts. -->
We introduce the **grounding coefficient** gc(k), a layer-wise interchange-intervention metric grounded in IIT theory (Geiger et al., 2023), and use it to identify the **Listen Layer** — the network depth at which patching audio-stream activations most strongly flips model behavior from text-dominated to audio-grounded. We evaluate on [N] audio-text conflict stimuli from ALME (Li et al., 2025) using [MODEL_NAME].

<!-- KEY RESULTS: 2–3 sentences. Main numbers + what they mean. -->
We find a sharp gc peak at layer [L*] (~[X]% model depth), consistent with the Triple Convergence zone.
The Listen Layer shifts under LoRA fine-tuning (LoRA-SER: Δ[ΔL] layers) and is suppressed in text-dominant failure cases.
[OPTIONAL: Comparison to baseline / ablation result.]

<!-- CONTRIBUTION: 1 sentence. Why it matters + what it enables. -->
Our results provide the first causal localization of audio grounding in speech LLMs, enabling targeted interventions for robustness and safety.

---

## Conclusion (target: ~250–350 words)

### 5.1 Summary

We introduced the **grounding coefficient** gc(k) and used it to causally localize the **Listen Layer** in [MODEL_NAME].
Key findings:
- gc peaks sharply at layer [L*] ≈ [X]% depth
- Ablation: [result of patching random layer vs L*]
- Fine-tuning: LoRA-SER shifts L* by [ΔL] layers
- Failure mode: gc suppressed at L* in text-dominant error cases

### 5.2 Limitations

<!-- Be honest. Reviewers will dock you if you don't address these. -->
1. **Single model.** Results shown for [MODEL_NAME]. Generalization to Qwen2-Audio-7B and other LALMs is left for future work (Tier 2 GPU experiments).
2. **Synthetic stimuli.** Phase 1 uses phonological minimal pairs (Choi et al.); naturalistic speech and out-of-distribution stimuli may yield different gc profiles.
3. **Layer granularity.** gc(k) is computed at the residual-stream layer level, not head or feature level. Finer-grained localization is the subject of Paper B (AudioSAEBench).
4. **Causal vs mechanistic.** We localize *where* (layer-level), not *how* (circuit). Full circuit enumeration is harder (~25% success rate per Anthropic Biology) and out of scope.

### 5.3 Future Work

- **Paper B (AudioSAEBench):** Scale from layer-level to feature-level gc using sparse autoencoders. Same stimuli, same metric, finer granularity.
- **Safety application (T5):** Use Listen Layer as anomaly signal for audio jailbreak detection (listen_layer_audit.py).
- **Cross-architecture:** Replicate on Qwen2-Audio-7B and [OTHER_MODEL] to test universality.
- **Controllable intervention:** Directly suppress/amplify L* to steer audio vs text grounding at inference time.

---

## Interspeech Format Checklist

- [ ] Abstract ≤ 200 words
- [ ] 4 pages main + 1 page references
- [ ] Sections: 1. Intro, 2. Method (gc definition + stimuli + models), 3. Experiments, 4. Results, 5. Conclusion
- [ ] All claims have citations or "ablation shows"
- [ ] Reproducibility: stimuli source, model checkpoint, random seed noted
- [ ] Ethics: audio data sourcing, potential misuse of jailbreak detection noted

---

## Submission Notes

- **Target venue:** Interspeech 2026
- **Deadline:** [CHECK — typically April submission]
- **Co-author flag:** 智凱哥 (AudioLens) — discuss authorship before submitting
- **Submission system:** [ISCA portal — confirm URL]
