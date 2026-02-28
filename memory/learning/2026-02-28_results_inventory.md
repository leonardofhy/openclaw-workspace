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

Once you fill numbers, I can immediately generate:
- Abstract v0 (~150 words)
- Results paragraph v0 (camera-ready style)
- Figure captions v0 (all figures/tables in one pass)
