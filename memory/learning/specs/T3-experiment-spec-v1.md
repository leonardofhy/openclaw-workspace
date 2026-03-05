# T3 Experiment Spec — Listen vs Guess (Paper A)
**Version:** v1 | **Date:** 2026-03-01 | **Status:** Ready for Leo Review

---

## 1. Hypothesis

Audio Language Models (ALMs) process speech through two distinguishable computational strategies within the audio encoder:

- **Listen**: direct acoustic feature extraction (lower/mid layers) — precise phoneme-level information
- **Guess**: cross-modal context filling (upper layers + connector) — lexical/semantic priors compensate when acoustics are ambiguous

**Testable claim**: There exists a critical transition layer k* (the "Listen Layer") such that:
- For k < k*, representations are dominated by acoustic evidence (high gc(k), causally sufficient)
- For k ≥ k*, representations increasingly reflect language priors (gc(k) drops, shortcuts dominate)

**gc(k)** = the proportion of transcription variance causally attributed to acoustic signal up to layer k, measured via causal patching.

---

## 2. Stimuli Design

### 2a. Synthetic Phoneme Pairs (CPU-compatible, no real speech needed)
Generate minimal-pair stimuli using text-to-speech or synthetic signal injection:

| Pair Type | Example | Purpose |
|-----------|---------|---------|
| Voicing contrast | /p/ vs /b/ (in "pack" vs "back") | Tests if early layers detect voice onset time (VOT) |
| Place of articulation | /t/ vs /k/ (in "tap" vs "cap") | Tests spectral cue encoding |
| Vowel height | /ɪ/ vs /iː/ ("bit" vs "beat") | Tests formant trajectory sensitivity |
| Noise robustness | clean vs +15dB white noise | Tests where noise resilience breaks down |

**Toy stimuli for CPU eval:**
- Use `numpy` to generate simple sine-wave approximations of vowel formants
- Or use `espeak-ng` / `pyttsx3` to produce minimal pairs (no GPU)
- 10-20 stimulus pairs sufficient for harness validation

### 2b. Conflict Stimuli (ALME test)
- Audio says "pack" but context implies "back" → measures if upper layers override acoustic evidence
- Requires: simple concatenation of acoustic signal + biasing prefix text

---

## 3. Layer Range

**Target model:** Whisper-small (initially; Whisper-medium as stretch goal)
- Audio encoder: 12 transformer layers (small), 24 (medium)
- **Primary sweep:** layers 0–11 (encoder only)
- **Secondary:** connector + first LM decoder layer (if applicable)

**Measurement points:** every layer (stride 1) for fine resolution of k*

---

## 4. gc(k) Threshold Hypothesis

**Expected gc(k) curve shape:**
```
gc(k)
1.0 |████████████████\
    |                 \______
0.5 |                        \_____
0.0 +------------------------------- k
    0    2    4    6    8   10   12
             k* ≈ 6-8?
```

- gc(k) ≈ 1.0 for k ≤ 4 (early acoustic encoding)  
- gc(k) drops sharply at k* (transition point)
- gc(k) ≈ 0.3–0.5 for k ≥ 8 (language prior dominates)

**Operationalization:**
- Patch activation at layer k with counterfactual (silence / noise-replaced signal)
- Measure change in output logit for target phoneme
- gc(k) = 1 - (output change / maximum possible change)

**Threshold for k* detection:** inflection point where d/dk gc(k) is maximally negative

---

## 5. Eval Criteria (Definition of Done)

### Tier 0 (CPU, mock data) — already started in Q005
- [ ] `gc_eval.py` produces a gc(k) curve given: model stub, mock activations, layer range
- [ ] Unit tests pass for edge cases (k=0, k=max, flat curve, steep curve)
- [ ] Output format: JSON + matplotlib plot saved to `artifacts/gc_curve_YYYYMMDD.png`

### Tier 1 (CPU, real Whisper-small, synthetic phoneme stimuli)
- [ ] Load `openai/whisper-small` via HuggingFace (no GPU needed, CPU inference)
- [ ] Extract intermediate layer representations via forward hooks
- [ ] Run gc(k) sweep across all 12 encoder layers
- [ ] Produce gc(k) curve for ≥3 phoneme-pair types
- [ ] Identify k* candidate from inflection point detection
- [ ] Document: does k* shift for noisy vs clean stimuli?

### Success criteria for paper
- k* is consistent across ≥5 stimulus types (low variance)
- gc(k) curve is significantly non-flat (KS test vs uniform, p < 0.01)
- k* correlates with known Whisper layer interpretability findings (if any exist)

---

## 6. Expected Output

1. **`artifacts/T3/gc_curve_whisper_small_phoneme_pairs.png`** — the gc(k) plot
2. **`artifacts/T3/gc_results.json`** — raw numbers (layer → gc score per stimulus)
3. **`artifacts/T3/stimuli/`** — generated phoneme pair audio files (.wav)
4. **1-paragraph narrative** for Paper A introduction: "We found that Whisper-small exhibits a sharp Listen-Layer transition at k*=N..."

---

## 7. Timeline & Approvals Needed

| Step | Tier | Needs Leo? | Est. Time |
|------|------|-----------|-----------|
| Synthetic stimuli generation | 0 | No | 30 min |
| Tier 0 harness finalization | 0 | No | Done (Q005) |
| Whisper-small CPU run | 1 | **Yes — approve** | 10-20 min CPU |
| Real speech validation | 1 | **Yes — .wav file** | After Q004 |
| Qwen2-Audio replication | 2 | **Yes — GPU** | TBD (Q003) |

**Immediate ask for Leo:**
1. ✅ Approve Tier 1 CPU run on Whisper-small (no GPU, ~15 min, no cost)
2. Provide one real speech .wav file for Q004 validation (any recording works)

---

## 8. Connection to Tracks

- **T3** (Listen vs Guess, Paper A): This spec IS the unlock artifact for converge→execute
- **T5** (Audio Jailbreak): gc(k) harness reusable for safety probe (Q006 scaffold)
- **Q019 → Q001/Q002**: Unblocks causal patching experiments once Tier 1 approved

---

*Prepared by autodidact cycle c-20260301-1915 | Awaiting Leo review before GPU experiments proceed*
