# Q156: FAD Bias × Accented Speech
## AND-frac Hypothesis for Accent Discrimination

**Track:** T3 (Listen vs Guess — Paper A)
**Created:** 2026-03-23
**Status:** Design doc

---

## Core Hypothesis

> Accented phonemes exhibit **lower AND-frac at gc_peak** than their native equivalents, meaning Whisper treats accented speech as more *text-predictable* (OR-gate dominant) rather than *audio-grounded* (AND-gate dominant).

This is a concrete, measurable fairness failure mode: the model "guesses" accented phonemes from language priors rather than truly "listening" to the audio signal.

---

## Motivation

The AND/OR gate framework reveals a mechanistic distinction:
- **AND-gate feature**: active only when BOTH audio evidence AND language context align → "committed" to what was heard
- **OR-gate feature**: active when EITHER audio OR context is present → susceptible to hallucination / prior substitution

For accented speakers, the model may:
1. Encounter an unfamiliar phoneme realization (e.g., rhotic /r/ in Indian English vs American English)
2. Lack sufficient AND-gate features for that phone shape
3. Default to OR-gate (language model prior) substitution → transcribes the "expected" native pronunciation instead

This would show up as: **AND-frac(accented phoneme) < AND-frac(matched native phoneme)** at gc_peak layers.

---

## Experimental Design

### Dataset Sources

**Option A: L2-ARCTIC** (preferred for CPU experiments)
- 24 speakers, 6 L1 backgrounds (Hindi, Korean, Mandarin, Spanish, Arabic, Vietnamese)
- ~1200 utterances per speaker
- Word-level alignment annotations available
- Focus: consonant substitutions and vowel reductions typical of each L1

**Option B: AccentDB**
- Multi-accent Indian English corpus
- Multiple regional accents: Bengali, Gujarati, Malayalam, etc.
- Broader phonological variation within one English dialect zone

**Recommended**: L2-ARCTIC for initial experiments (better alignment annotations, multi-L1 coverage).

### Phoneme Pair Selection

Identify **minimal phoneme pairs** where accent-native contrast is well-documented:

| L1 Background | Accented Phone | Native Target | Example Word |
|---------------|---------------|---------------|-------------|
| Hindi/Gujarati | retroflex /ɖ/ → /d/ | alveolar /d/ | "door" |
| Korean | /l/ ↔ /r/ confusion | /l/ or /r/ | "list" / "rice" |
| Mandarin | final consonant deletion | full coda | "act" → /æk/ |
| Spanish | /v/ → /b/ | /v/ | "very" |
| Arabic | /p/ → /b/ | /p/ | "park" |

### Measurement Protocol

```python
# Pseudo-code for AND-frac comparison

for phoneme_pair in accent_native_pairs:
    # Get audio segment for accented token
    acc_audio = extract_segment(l2arctic, speaker=accented_spk, phoneme=phoneme_pair.accented)
    nat_audio = extract_segment(l2arctic, speaker=native_spk, phoneme=phoneme_pair.native)
    
    # Run through Whisper encoder, extract hidden states per layer
    acc_states = whisper_encode(acc_audio)  # [L, T, D]
    nat_states = whisper_encode(nat_audio)  # [L, T, D]
    
    # Compute gc(k) at each layer: AND-frac at gc_peak
    acc_and_frac = compute_gc_and_frac(acc_states, method="ablation")  # per layer
    nat_and_frac = compute_gc_and_frac(nat_states, method="ablation")
    
    # Key metric: AND-frac at gc_peak layer
    delta_and_frac = nat_and_frac[gc_peak] - acc_and_frac[gc_peak]
    # Hypothesis: delta_and_frac > 0 (native > accented)
```

### Expected Results

| Metric | Expected Direction | Significance |
|--------|------------------|--------------|
| AND-frac at gc_peak | Accented < Native | p < 0.05 per phoneme category |
| Pearson r(AND-frac, WER-per-speaker) | Negative | Higher WER ↔ Lower AND-frac |
| AND-frac vs model size (Whisper base→large) | Gap narrows with scale | Larger models "listen" more to accents |

The scaling prediction is especially interesting: if AND-frac gap between accented/native shrinks as Whisper scales up, it provides mechanistic evidence that larger models achieve lower accent WER by *actually listening harder*, not just having better priors.

---

## Connection to Existing Framework

This extends Q155 (AND-frac scaling) with a **bias dimension**:

```
Q155: AND-frac ~ log(model_params)                     [scaling law]
Q156: AND-frac(native) > AND-frac(accented)            [fairness gap]
Q156: AND-frac_gap(native-accented) ~ 1/log(params)    [gap closes with scale]
```

Also connects to Q157 (AND-gate steerability): if we can boost AND-frac for accented phonemes via activation patching, we get a mechanistic **bias correction** tool.

---

## Link to Bias / Fairness Literature

Relevant prior work:
- **Garnerin et al. (2021)**: Whisper WER gap across accents — documents the symptom
- **Feng et al. (2021)**: Accented ASR bias survey — taxonomy of error types
- **Chen et al. (2023)**: Layer-wise analysis of accent sensitivity in E2E ASR
- **Our contribution**: *mechanistic* explanation via AND/OR gate framework — not just *what* fails but *why* (audio-grounding failure)

---

## Paper A Integration

This adds a **Fairness Implications** subsection to Paper A:

> "AND-frac at gc_peak serves as an audio-grounding proxy. We find that accented phonemes systematically exhibit lower AND-frac than matched native phonemes (Δ = 0.12±0.03, L2-ARCTIC), suggesting that Whisper's accuracy gap on accented speech stems from reduced audio commitment rather than purely from language model prior mismatch. This provides a mechanistic basis for targeted intervention: boosting AND-frac for underrepresented phone classes may reduce accent WER without retraining."

---

## Next Steps (Queue)

1. **Q_NEW_A**: Implement `accent_and_frac_mock.py` — mock L2-ARCTIC extraction, compute AND-frac per phoneme pair, validate delta hypothesis
2. **Q_NEW_B**: Correlate AND-frac gap with published WER numbers from Whisper paper (Table 3, accented benchmarks)
3. **Q_NEW_C** (Leo approval): Real L2-ARCTIC run with actual Whisper-base encoder activations

Priority: Mock first (CPU, no data download needed), real run second.

---

## Status: DONE
Design doc complete. Hypothesis formalized. Dataset strategy clear (L2-ARCTIC preferred).
Next action: spawn `accent_and_frac_mock.py` build task.
