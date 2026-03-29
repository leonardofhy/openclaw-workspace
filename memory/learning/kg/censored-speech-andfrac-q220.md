# Censored Speech × AND-frac: Q220 Design Notes

**Created:** 2026-03-29 (Cycle c-20260329-2245, learn prep for Q220)
**Track:** T3
**Status:** Design ready — execute tomorrow as first build task

---

## Problem Statement

**Q220 core question:** When Whisper transcribes "sensitive" speech content (profanity, politically sensitive topics, hate speech fragments), does the AND-frac commit layer L* shift or does AND-frac magnitude change compared to neutral speech?

This is the audio analog to the censored LLM hypothesis (Q171): in text LLMs, refusal/censorship behavior is associated with shifted internal activation patterns. If Whisper processes sensitive audio differently at L*, that has implications for:

1. **Audio interpretability**: Content-sensitivity is mechanistically visible
2. **Safety probes**: AND-frac at L* as a real-time "sensitive content" detector
3. **Paper A / Paper C synthesis**: Bridges T3 and T5

---

## Two Competing Hypotheses

### H1: L* Shifts (Content-Dependent Commit Layer)
Sensitive content → phoneme ambiguity higher (speaker hedges, drops volume, deviates from neutral prosody) → AND-frac crystallization delayed → L* shifts RIGHT (deeper layers needed to commit).

**Prediction:** L*_sensitive > L*_neutral by ≥1 layer

**Mechanism:** Acoustic signal itself is different (emotional speech characteristics) → more processing needed before commitment.

### H2: L* Fixed, AND-frac Magnitude Drops
Same commit layer, but lower peak AND-frac value → Whisper is less "confident" at L* for sensitive content.

**Prediction:** same L* position, AND-frac_peak_sensitive < AND-frac_peak_neutral by ≥15%

**Mechanism:** Whisper's phoneme crystallization is layer-fixed; sensitivity manifests as lower commitment confidence, not later commitment.

### H3 (Null): No Difference
Content sensitivity does not affect Whisper encoder internals — purely acoustics-driven, insensitive to semantic content at phoneme stage.

---

## Experimental Design

### Stimuli Selection (CPU-only, Whisper-base)

**Sensitive set (10 utterances):** Use synthetic/public-domain text-to-speech or LibriSpeech-adjacent samples. Avoid actual harmful content — use **edge cases** that would trigger content moderation:
- 3 × profanity (mild: from public datasets like CHiME or spontaneous speech corpora)
- 3 × politically charged but factual statements (e.g., news headlines about controversial topics)
- 2 × emotionally charged (anger, distress — from MSP-Podcast or IEMOCAP if available)
- 2 × whispered/mumbled speech (acoustic ambiguity proxy)

**Neutral set (10 utterances):** Matched by duration ±0.5s, similar phoneme complexity:
- 10 × factual, emotionally neutral utterances from LibriSpeech test-clean

**Important:** If real sensitive audio not available, generate with a TTS model (pyttsx3 or espeak) for both sets with matched acoustic properties. This tests semantic content effect while controlling acoustics.

### Feature Extraction

```python
# For each utterance u in {sensitive_set ∪ neutral_set}:
# 1. Run whisper-base encoder on mel spectrogram
# 2. Collect hidden_states[l] for l in 0..5 (6 encoder layers)
# 3. Compute AND-frac(l) using existing and_frac_utils.py
# 4. Find L* = argmax(AND-frac) for each utterance
# 5. Record: {utt_id, category, L*, AND-frac_per_layer[], duration}
```

### Analysis

**Primary metric:** L* position (0-5 for Whisper-base encoder)
- Mann-Whitney U test: L*_sensitive vs L*_neutral (n=10 each)
- Report: median L*, IQR, p-value

**Secondary metric:** AND-frac at L*
- Compare peak AND-frac values
- Effect size (Cohen's d)

**Tertiary:** AND-frac profile shape similarity
- Spearman correlation between average sensitive vs neutral AND-frac curves across layers

### Expected Output

Table:
| Condition | L* (median) | AND-frac@L* (mean±SD) | n |
|-----------|------------|----------------------|---|
| Sensitive | ? | ? | 10 |
| Neutral | ? | ? | 10 |
| p-value | Mann-Whitney | t-test | - |

Interpretation written (3-4 sentences).

---

## Connections to Prior Work

| Related Work | Connection |
|---|---|
| Q205: Censored GPT-2 | AND-frac differs for refused vs accepted tokens → audio analog |
| Q206: WER improvement via steering | L* is the right intervention point → Q220 confirms L* is content-sensitive |
| Q209: Head circuit dissection at L* | If L* shifts, HEAD roles must also shift → interesting ablation |
| Q171: Censored LLMs (blocked) | Theoretical motivation — access via secondary sources |
| T5 SPIRIT-style erasing | If sensitive content changes AND-frac, erasing that direction becomes well-motivated |

---

## Open Questions

1. **Is semantic content visible to encoder?** Whisper's encoder processes audio → mel → phonemes. Semantic meaning is mostly decoder. So H3 (null) is plausible. However, *prosodic* properties of sensitive speech (emotional valence, speech rate) ARE in the encoder → H1/H2 via acoustic proxy.

2. **What's the right "sensitive" proxy?** Pure acoustic control (matched TTS) vs natural sensitive speech (unmatched acoustics). Should do BOTH.

3. **How to handle Whisper's built-in filtering?** Whisper-base does not censor output but may have trained on filtered data. Encoder may be robust to content. Check: do profanity-containing utterances get transcribed accurately or hallucinated?

4. **Link to hallucination (Q206 territory)?** If sensitive content causes L* drop in AND-frac, does that predict Whisper hallucination on sensitive tokens?

---

## Implementation Notes

- Existing infrastructure: `and_frac_utils.py` already computes AND-frac per layer
- Mock version: synthesize sensitive/neutral pairs with espeak, control pitch+rate
- Real version: use LibriSpeech test-clean (neutral) + recorded sensitive speech if available
- Runtime: <2 min on CPU for 20 utterances × 6 layers

---

## Paper A Integration

If H1 or H2 confirmed:
> "The commit layer L* is sensitive not only to acoustic difficulty (accented speech, noise) but also to *content type*, suggesting that Whisper's listen layer encodes a form of semantic uncertainty..."

This would be a strong §5 (Broader Implications) paragraph and potentially a standalone experiment in a journal extension.
