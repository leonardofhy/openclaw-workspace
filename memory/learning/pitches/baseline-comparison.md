# Baseline Comparison: gc(k) Audio Jailbreak Detector vs. Prior Methods

> Track: T5 — Listen-Layer Audit / MATS proposal
> Task: Q057
> Created: 2026-03-07

## Summary

This table positions the gc(k)-based Listen-Layer detector against leading jailbreak/safety baselines:
PAIR (prompt-based), GCG (gradient-based suffix), and SALAD-Bench (evaluation suite).

---

## Comparison Table

| Dimension            | **gc(k) + Listen-Layer** (ours) | **PAIR** | **GCG** | **SALAD-Bench** |
|----------------------|----------------------------------|----------|---------|-----------------|
| **Type** | Activation-based detector | Black-box attack | White-box attack | Evaluation benchmark |
| **Role** | Defense / detection | Attack generation | Attack generation | Attack taxonomy + eval |
| **Inputs** | Audio waveform → internal activations (hook at listen-layer) | Text prompt pairs (iterative LLM refinement) | Text prompt + gradient access | Text/multimodal prompts |
| **Modality** | Audio-native (waveform) | Text | Text | Text / multimodal |
| **Compute** | CPU-feasible (forward pass only, no GPU for detection) | Moderate (LLM API calls ~20 rounds) | High (backprop through full model) | N/A (benchmark, run cost varies) |
| **Interpretability** | ✅ High — pinpoints which layer / which feature circuit fired | ❌ None (black box) | ❌ None (gradient artifact) | ❌ None (aggregate score) |
| **Requires model weights** | ✅ Yes (hook into internals) | ❌ No (API-only OK) | ✅ Yes (gradient access) | ❌ No |
| **Attack-agnostic** | ✅ Yes — detects semantic anomalies regardless of attack method | ❌ No (is itself the attack) | ❌ No (is itself the attack) | ❌ N/A |
| **Audio-specific** | ✅ Yes (listener-layer in Whisper/audio-LLM) | ❌ No | ❌ No | Partial (some audio splits) |
| **Causal / mechanistic** | ✅ Yes (causal patching identifies responsible features) | ❌ No | ❌ No | ❌ No |
| **Limitations** | Needs model internals; hook design is model-specific; no published AUROC on real jailbreaks yet | Arms race: model knows to refuse; brittle phrasing | Requires white-box access; generates adversarial text not audio | Not a detector; taxonomy depends on curation; no audio-native attacks catalogued |
| **Output** | Binary flag + layer attribution + feature index | Adversarial prompt string | Adversarial suffix string | Safety category score |
| **Paper / ref** | This work (T5 pitch) | Chao et al. 2023 | Zou et al. 2023 | Li et al. 2024 |

---

## Key Differentiators

1. **Modality gap**: PAIR and GCG are text-only; audio jailbreaks (prosody, noise masking, foreign phoneme injection) are invisible to them. Our method operates on waveform-derived activations.

2. **Interpretability**: Other methods are oracle (detect vs. no detect) or attack generators. gc(k) provides a *mechanistic explanation* — which internal feature fired, at which layer — enabling targeted patching.

3. **Compute**: GCG requires per-sample gradient computation (expensive). gc(k) is a single forward pass with a lightweight hook; suitable for real-time or batch screening.

4. **Generalization**: Because we detect anomalies in the *activation geometry* of the listen-layer, the detector is attack-agnostic — it doesn't need to be trained on attack-specific patterns.

---

## Limitations to Acknowledge in Paper

- Ground truth labels for audio jailbreaks are scarce (no large public benchmark); evaluation uses synthetic data + SALAD-Bench text analogues.
- Hook design is Whisper-specific; porting to Qwen2-Audio requires re-identifying the listen-layer (Q003, blocked on GPU).
- gc(k) thresholds are currently heuristic; learned thresholds (logistic probe) need labeled real-speech data (Q004).

---

## Next Steps (queue)

- Q058: LaTeX skeleton for Paper A (which will include a version of this table in §4 Experimental Setup)
- Q003: Extend listen-layer localization to Qwen2-Audio (blocked, needs GPU + Leo approval)
