# KG: Accent × AND-Frac Fairness — Theoretical Grounding

**Created:** 2026-03-23  
**Cycle:** c-20260323-2115  
**Serves:** Q162–Q170 (accent mock cluster, T3)  
**Status:** Synthesized from existing KG + known ASR fairness literature

---

## Problem Framing

**Central claim (to be validated by mocks):**  
> Accented phonemes are systematically treated as *text-predictable* (OR-gate) rather than *audio-grounded* (AND-gate) by Whisper, causing AND-frac(accented) < AND-frac(native). This AND-frac gap is the mechanistic root of ASR accent bias.

---

## Why Should AND-Frac Differ for Accented Speech?

### 1. Training Distribution Argument
- Whisper trained on ~680K hours, majority native English + high-resource languages.
- L2-ARCTIC / AccentDB phonemes (e.g., retroflex /ɹ/ for Indian-English, dental fricatives for Mandarin-accented English) are **underrepresented**.
- Underrepresented phoneme = model cannot reliably extract audio-grounded features → falls back on language model prior → OR-gate behavior.

### 2. Featural Ambiguity Argument
- Native phonemes have high **acoustic discriminability** (large formant separation in training data).
- Accented phonemes often overlap with multiple native categories (e.g., Indian /v/ ~ /w/, Korean /l-r/).
- When acoustic signal is ambiguous, the model ATTENDS LESS to the audio token → AND-frac drops.
- This is the same mechanism as silence-induced t* shift (Q149), but driven by featural ambiguity rather than signal absence.

### 3. The AND-OR Gate Mechanism (from existing KG)
- AND-gate: feature fires only if audio token AND linguistic context agree.
- OR-gate: feature fires if audio token OR linguistic context provides support.
- For native phonemes: model builds AND-gate circuit (double verification).
- For accented phonemes: model bypasses audio verification → pure OR-gate (language model fills in expected word).
- **Result**: model "hears" what it expects, not what is said → hallucination pathway identical to silence case.

### 4. Connection to t* Shift (Hallucination Pathway)
From Q149 (silence × t*): silence_fraction > 0.7 → t* < 4 → hallucination onset.  
**Hypothesis for accent**: accent behaves as *functional silence* for under-trained phoneme categories.  
- Acoustic commitment (t*) shifts earlier because AND-gate never triggers.
- Model commits based on prior, not observation.
- **Prediction**: accent_level correlates with t* < 4; mediated by AND-frac.

---

## Key Constructs for Q162–Q170 Mocks

| Construct | Mock Variable | Expected Direction |
|-----------|--------------|-------------------|
| AND-frac | `and_frac_native`, `and_frac_accented` | native > accented, Δ ≥ 0.08 |
| Phoneme confusion rate | confusion matrix entry | accented > native |
| Commitment time (t*) | `tstar` | accented shifts earlier (< 4) |
| Beam diversity (Isolate) | `beam_entropy` | lower for accented (collapsed hypothesis space) |
| Commitment head entropy | per-head entropy | higher for accented (less committed) |
| AND-frac Fairness Gap (AFG) | `and_frac_native - and_frac_accented` per L1 | AFG ≥ 0.08 on ≥4 L1 groups |
| SNR sensitivity | AND-frac slope under noise | accented slope ≥ 2× native |
| Hallucination steps | `hallucination_steps` | accent_level → more steps, mediated by AND-frac |
| Beam rescoring gain | `wer_gap_reduction` | AND-frac rescoring reduces gap ≥ 30% |

---

## L2-ARCTIC Coverage (Mock Targets)
- 6 L1 backgrounds: Hindi (HI), Korean (KO), Mandarin (ZH), Spanish (ES), Vietnamese (VI), Arabic (AR)
- Key phoneme contrasts per group:
  - ZH: /θ/→/s/, /ð/→/z/, /ɹ/→/w/ or /l/
  - KO: /l-r/ merger, final consonant deletion
  - HI: retroflex vs. dental stops, /w/~/v/
  - ES: /ʃ/~/tʃ/, schwa epenthesis
  - AR: emphatic consonants, /p/~/b/
  - VI: tone-conditioned vowel quality shifts

---

## Literature Anchors (from memory)
- **Radford et al. 2022 (Whisper)**: reported WER degradation on non-native English; attributed to training distribution.
- **L2-ARCTIC (Zhao et al. 2018)**: 24 L2 speakers (4/L1), ~1h each, phoneme-aligned. Perfect for AND-frac mock.
- **AccentDB**: ~5800 samples across Indian accent families.
- **Koenecke et al. 2020 (Science)**: commercial ASR WER gap for Black vs. White speakers — social consequence of acoustic OR-gate bias.
- **Anchor paper needed**: "Why does Whisper hallucinate?" (2023/2024) — search for Hughes et al. or similar; directly validates t* mechanism.

---

## Connections to Existing KG Nodes
- `and-or-gate-ravel-fad-unification.md` → AND-frac definition + RAVEL extension
- `ravel-isolate-beam-rescoring.md` → Isolate(k) + beam diversity link
- **New connection**: AND-frac Fairness Gap (AFG) = quantitative bias metric derived from gc(k) analysis

---

## Open Questions
1. Does AND-frac truly drop for accented phonemes, or does *confusion rate* increase independently?  
   → Q163 (phoneme_confusion_l2_mock) tests this.
2. Is the AFG L1-specific or phoneme-category-specific?  
   → Q162 tests per-L1; future work: per-phoneme-category.
3. Does AND-frac beam rescoring (Q170) actually improve fairness or just overall accuracy?  
   → Critical for paper framing: "fairness-aware" requires differential improvement.
4. Is the accent × noise interaction (Q168) additive or superadditive?  
   → Superadditive would be a stronger finding: structural disadvantage compounds with acoustic degradation.
