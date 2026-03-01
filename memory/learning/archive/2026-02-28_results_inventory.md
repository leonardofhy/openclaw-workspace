# Results Inventory Draft (2026-02-28)

Project focus: **Paper A — Localizing the Listen Layer in Speech LLMs**
Status: **Assistant-drafted v1 for Leo review**

---

## 1) Candidate Figure/Table Plan

### Figures
- **Fig-1 (Concept Figure / Pipeline)**
  - Content: audio-text conflict setup + layer-wise denoising patching workflow.
  - Claim: We can isolate where audio becomes causally decisive, not just behaviorally correlated.

- **Fig-2 (Main Curve: grounding coefficient over layers)**
  - Content: `gc(L)` curve across model depth.
  - Claim: A sharp mid-depth peak identifies the Listen Layer.

- **Fig-3 (Cross-model comparison)**
  - Content: normalized layer index of peak `gc` for Whisper-small and Qwen2-Audio-7B.
  - Claim: Listen Layer localization is consistent across architectures when normalized by depth.

- **Fig-4 (Failure-mode / stress cases)**
  - Content: text-dominant failure examples with suppressed `gc` peak.
  - Claim: When model fails to ground in audio, Listen Layer signal weakens or shifts.

### Tables
- **Tab-1 (Main benchmark results on conflict stimuli)**
  - Content: baseline vs ours on conflict-resolution accuracy.
  - Claim: causal patching identifies stronger audio-grounded behavior than text-dominant baseline.

- **Tab-2 (Ablation: patching variants)**
  - Content: denoising vs noising patching, layer windows, head masking.
  - Claim: Listen Layer finding is robust to intervention design choices.

- **Tab-3 (Efficiency / practicality)**
  - Content: runtime and compute profile for Whisper vs Qwen2-Audio experiments.
  - Claim: method is feasible from lightweight validation to large-model scale-up.

---

## 2) Top-3 Result Numbers (Draft slots)

> I pre-filled structure + interpretation direction. Leo only needs to replace values.

1. **Peak grounding coefficient at Listen Layer**
   - Baseline (non-peak layers avg): `TBD`
   - Ours (peak layer): `TBD`
   - Δ absolute: `TBD`
   - Δ relative: `TBD`
   - Interpretation: audio causality concentrates at a narrow depth band instead of being uniformly distributed.

2. **Conflict-resolution accuracy improvement (audio-grounded decisions)**
   - Baseline (text-dominant or no-patching): `TBD`
   - Ours (patching at Listen Layer): `TBD`
   - Δ absolute: `TBD`
   - Δ relative: `TBD`
   - Interpretation: intervening at Listen Layer flips decisions toward audio evidence.

3. **Cross-model localization consistency (normalized depth)**
   - Whisper-small peak depth: `TBD`
   - Qwen2-Audio peak depth: `TBD`
   - Difference: `TBD`
   - Interpretation: Listen Layer appears in comparable relative depth zones across models.

---

## 3) Ready-to-use Result Interpretation Sentences

- **For Fig-2:**
  - "Figure 2 shows a pronounced peak in grounding coefficient at mid-depth layers, suggesting that audio information becomes causally decisive only in a narrow Listen Layer."

- **For Tab-1:**
  - "Table 1 shows that patching at the Listen Layer substantially improves conflict-resolution accuracy over text-dominant baselines, indicating stronger audio grounding."

- **For Tab-2:**
  - "Table 2 shows that the localization pattern remains stable across intervention variants, suggesting that the Listen Layer finding is not an artifact of a specific patching configuration."

- **For Fig-4:**
  - "Figure 4 shows that in failure cases the grounding peak is weakened or displaced, suggesting a mechanistic link between Listen Layer integrity and robust audio-grounded inference."

---

## 4) Abstract Draft (4-sentence version)

1. **Background**
   - Large audio-language models can answer speech-related queries, but it remains unclear where audio evidence becomes causally decisive during inference.

2. **Gap**
   - Prior work characterizes modality dominance behaviorally, yet does not localize the network depth at which audio representations are actually consulted.

3. **Method**
   - We propose Listen Layer localization via layer-wise denoising activation patching and quantify audio reliance using a grounding coefficient over audio-text conflict stimuli.

4. **Result**
   - Experiments on Whisper-small and Qwen2-Audio reveal a sharp mid-depth grounding peak and improved audio-grounded conflict resolution, supporting a localized causal "Listen Layer" hypothesis.

---

## 5) Results Storyline v1

- **Core claim**
  - Audio grounding in speech LLMs is not diffuse; it is mechanistically localized to a small set of layers.

- **Evidence chain**
  1. Layer sweep identifies a strong `gc(L)` peak.
  2. Intervening at peak layers changes behavior more than non-peak layers.
  3. Pattern replicates across at least two model families.

- **Likely reviewer concerns**
  - Is this an intervention artifact?
  - Does this generalize beyond one dataset/model?
  - Are we measuring audio grounding or confounded text cues?

- **Planned reinforcement**
  - Robustness ablations (patching design choices).
  - Cross-model replication (Whisper + Qwen2-Audio).
  - Failure-case analysis where text dominates.

---

## 6) Immediate Next Edits Needed from Leo

1. Fill Top-3 numbers with real values.
2. Confirm final figure/table count for 4-page constraint.
3. Decide venue framing language (Interspeech-style concise vs NeurIPS-style broader mechanism framing).

## 7) Abstract v0 (~150 words, ready for number fill)

Large audio-language models can answer questions about speech content, yet it remains unclear where audio evidence becomes causally decisive during inference. Prior studies characterize audio-vs-text dominance behaviorally, but do not localize the network depth at which audio representations are actually consulted. We propose **Listen Layer localization**, a layer-wise denoising activation patching framework, and quantify audio reliance with a **grounding coefficient** computed on audio-text conflict stimuli. Across Whisper-small and Qwen2-Audio-7B, we observe a sharp grounding peak at mid-depth layers, indicating that audio causality is concentrated in a narrow depth band rather than distributed uniformly. Intervening at this peak layer improves conflict-resolution accuracy by **[X]** absolute points (**[Y]%** relative) over non-peak interventions, while robustness checks across patching variants preserve the same localization pattern. These findings provide causal evidence for a localized Listen Layer and offer a practical target for analysis, adaptation, and safety interventions in speech LLMs.

---

## 8) Results paragraph v0 (paper-style)

Figure 2 shows that grounding coefficient values are low in early layers, rise sharply in the middle of the network, and then decline toward deeper layers, yielding a clear single-peak profile. This pattern indicates that audio evidence is not consumed uniformly across depth, but becomes causally decisive within a narrow layer band. Consistent with this interpretation, Table 1 shows that denoising interventions at the peak layer improve audio-text conflict resolution substantially more than interventions at non-peak layers, confirming that the identified layer is functionally privileged. Table 2 further shows that this localization is stable across intervention variants, including patching window and masking strategy, suggesting that the effect is not an artifact of one specific intervention design. Finally, cross-model comparison (Figure 3) reveals similar normalized peak positions in Whisper-small and Qwen2-Audio-7B, supporting the generality of the Listen Layer hypothesis.

---

## 9) Figure/Table captions v0

- **Figure 1.** Overview of Listen Layer localization. We construct audio-text conflict inputs and perform layer-wise denoising activation patching to measure where audio evidence causally changes model decisions.

- **Figure 2.** Grounding coefficient over depth. A sharp mid-depth peak identifies the Listen Layer, where audio representations have maximal causal influence.

- **Figure 3.** Cross-model normalized localization. Peak grounding layers align in relative depth across Whisper-small and Qwen2-Audio-7B.

- **Figure 4.** Failure-case grounding profiles. Text-dominant failures exhibit attenuated or shifted grounding peaks compared with successful audio-grounded cases.

- **Table 1.** Main conflict-resolution performance. Intervening at the Listen Layer yields the strongest improvement in audio-grounded decision accuracy.

- **Table 2.** Robustness to intervention design. Listen Layer localization remains stable across patching variants and masking strategies.

- **Table 3.** Compute profile and runtime. We report practical cost from lightweight Whisper validation to large-model Qwen2-Audio analysis.
