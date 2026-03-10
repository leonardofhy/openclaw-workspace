# Paper A Related Work Gap Matrix
*Cycle: c-20260306-1031 | Task: Q058 | Track: T3*

## 8 Prior Works × 5 Dimensions

**Row** = paper. **Col** = dimension.  
**✅** = covered. **◑** = partial/indirect. **❌** = gap (Paper A contribution).

| Paper | Behavioral grounding evidence | Mechanistic (circuit-level) | Audio/Speech | Safety/Robustness | Evaluation metric |
|-------|------------------------------|----------------------------|--------------|-------------------|-------------------|
| Lee et al. 2026 (AudioCapsV2, 2603.03855) | ✅ 71K clips, TPR/FPR under event complexity | ❌ black-box survey | ✅ audio-LLM | ◑ robustness under prompt variance | ◑ yes/no accuracy; no mechanistic metric |
| Zhao et al. 2602.23136 (ALME, Modality Collapse) | ✅ 57K conflict pairs, behavioral collapse rate | ❌ no circuit attribution | ✅ speech-LLM conflict | ◑ indirect (safety not main focus) | ◑ TPR/FPR on conflict pairs; no layer metric |
| Choi et al. 2602.18899 (Phonological Geometry) | ❌ representation analysis only | ◑ linear probes (not patching) | ✅ speech (96 langs) | ❌ | ◑ cosine similarity, decoding accuracy |
| Lin et al. 2502.17516 (MMFM MI Survey) | ◑ surveys behavioral + mechanistic for VLMs | ◑ covers VLM circuits only | ❌ **ZERO audio** | ◑ partial (safety in VLMs) | ◑ survey taxonomy, no audio metric |
| SPIRIT (Djanibekov et al., EMNLP 2025) | ✅ 100% ASR jailbreak rate behavioral | ◑ neuron-level (not SAE-feature) | ✅ Whisper encoder | ✅ adversarial robustness | ◑ ASR WER delta; no gc(k) layer metric |
| RAVEL (Huang et al., ACL 2024) | ❌ representation (text LM) | ✅ Cause+Isolate metric, MDAS | ❌ text only | ❌ | ✅ disentanglement benchmark |
| AudioSAE (Aparin et al., EACL 2026) | ◑ steering success = implicit behavioral | ◑ SAE features (not circuits/patching) | ✅ Whisper speech | ❌ | ◑ consistency, dead neurons, cossim |
| Beyond Transcription (Glazer 2025) | ◑ probing accuracy behavioral | ◑ probing (not patching) | ✅ ASR | ❌ | ◑ decoding accuracy; no causal metric |

---

## Dimension Key

1. **Behavioral grounding evidence** — Does the paper measure *when/how much* models ground audio vs. text priors (TPR/FPR, conflict accuracy, etc.)?
2. **Mechanistic (circuit-level)** — Does the paper trace grounding to specific layers, heads, or features via patching or causal abstraction?
3. **Audio/Speech** — Is the paper's primary domain speech/audio (vs. text, VLMs, or general)?
4. **Safety/Robustness** — Does the paper connect grounding to safety or adversarial robustness?
5. **Evaluation metric** — Does the paper provide a *reusable, layer-resolved metric* for grounding? (Not just end-task accuracy)

---

## Paper A's Position

Paper A contributes what **NO prior work** covers simultaneously:

| Column | What Paper A provides |
|--------|-----------------------|
| Behavioral | gc(k) behaviorally validates when model "listens" vs "guesses" via counterfactual audio patching |
| Mechanistic | First **causal, layer-resolved** circuit-level account of audio grounding using DAS/IIT |
| Audio | Speech/audio-native (Whisper encoder + Audio-LLM) — not borrowed from text MI |
| Safety | gc(k) predicts safety failure: low-gc layers = text-pathway dominance = jailbreak vulnerability |
| Metric | gc(k) = grading coefficient, a **novel, reusable scalar** measuring per-layer causal grounding |

**The gap statement for Paper A §2:**
> "While prior work has either characterized *behavioral* audio grounding (Lee et al. 2026; Zhao et al. 2026) or provided *mechanistic* accounts for text/vision models (Lin et al. 2025; RAVEL), no work provides a mechanistic, layer-resolved, causally grounded account of audio processing in speech LLMs. Paper A fills this gap via the grounding coefficient gc(k), the first metric that jointly satisfies all five dimensions."

---

## Narrative Framing for Paper A §2

**Structure suggestion (related work section):**

### §2.1 Audio Grounding — Behavioral Evidence
- Lee et al. 2026: behavioral degradation under scene complexity → *motivates mechanistic account*
- Zhao et al. ALME: modality collapse (text priors override audio) → *gc(k) = mechanistic test of collapse*

### §2.2 Mechanistic Interpretability — Text and Vision
- Lin et al. 2025 survey: MI mature for VLMs, **absent for audio** → *white space confirmed*
- RAVEL: Cause+Isolate metric for text → *Paper B extends to audio; Paper A borrows causal-abstraction framing*

### §2.3 Audio Representation and Features
- Choi et al.: phonological geometry is linear in S3M encoders → *Paper A tests whether this geometry survives into LLM*
- AudioSAE: monosemantic features extractable from Whisper → *Paper B; Paper A uses SAE-guided layer selection*
- Beyond Transcription: probing for non-transcription info → *complementary (probing ≠ causal)*

### §2.4 Safety and Robustness
- SPIRIT: audio jailbreaks defeated by MLP patching → *Paper A provides mechanistic WHY via gc(k)*
- Gap: No prior work predicts which layers are safety-relevant from first principles

---

## Key Insight for §1 (Introduction)
The gap matrix reveals a **2×2 tension**:

|  | Behavioral | Mechanistic |
|--|------------|-------------|
| **Text/VLM** | ✅ many works | ✅ many works |
| **Audio/Speech** | ✅ Lee + Zhao | ❌ **Paper A** |

Audio MI is the missing quadrant. This is Paper A's core positioning claim.

---

*Cycle c-20260306-1031 | Duration ~75s | Next: Complete Q058, queue needs fresh tasks*
