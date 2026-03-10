# Cycle c-20260311-0101 — design (Q063)
## Phase: explore-fallback | Action: design | Task: Q063
## Audio-RAVEL Minimal Pair Stimuli Plan

> Created: 2026-03-11 01:01 (Asia/Taipei)
> Track: T2 (AudioSAEBench — Paper B)
> Depends on: audio-ravel-protocol.md, paper-b-s3-outline.md, Choi et al. arXiv:2602.18899
> DoD: stimulus table, TTS source, 5 contrasts × 4 lang × 20 pairs = 400 pairs spec

---

## 1. Design Rationale

Audio-RAVEL (AudioSAEBench Category 0) requires minimal pairs that isolate single phonological
features. Protocol spec (audio-ravel-protocol.md) specifies Choi et al. 2602.18899 as primary
source + TTS fallback. This doc extends the protocol to a **concrete 400-pair stimulus table**:
- 5 phonological contrasts (not 3 as in protocol v1 — expanding scope)
- 4 languages (not English-only — strengthens multilingual claim)
- 20 pairs per contrast × language = 400 total
- TTS source specified per language
- Repo access status + fallback plan

This is the operationalization step between the protocol spec and Phase 1 implementation.

---

## 2. Five Phonological Contrasts

Selected based on: (1) universality across target languages, (2) linear SAE feature geometry
predicted by Choi et al., (3) clear Cause/Isolate separation, (4) theoretical interest.

| ID | Contrast | Feature | Level 0 | Level 1 | Why it matters |
|----|----------|---------|---------|---------|----------------|
| C1 | Voicing | [±voice] | Voiceless /p t k s/ | Voiced /b d g z/ | Most studied; Choi et al. primary axis |
| C2 | Manner | Plosive vs Fricative | /t p k/ (plosive) | /s f θ/ (fricative) | Tests manner-of-articulation features in SAE |
| C3 | Place | Labial vs Alveolar | /p b f v m/ | /t d s z n/ | Tests place features; partially correlated with C1 (control needed) |
| C4 | Nasality | [±nasal] | /b d g/ (oral stops) | /m n ŋ/ (nasal stops) | Tests sonorance; distinct from C1/C2/C3 (good Isolate control) |
| C5 | Vowel height | High vs Mid-Low | /i u/ (high) | /e o a/ (mid-low) | Vowel domain — ensures SAE is not consonant-only; stress-free contrast |

**Contrast orthogonality (key for Isolate test):**

| Contrast | C1 Voice | C2 Manner | C3 Place | C4 Nasal | C5 V-Height |
|----------|----------|-----------|----------|----------|-------------|
| C1 Voice | — | ✅ orthogonal | ✅ orthogonal | Partial¹ | ✅ orthogonal |
| C2 Manner | — | — | ✅ orthogonal | Partial² | ✅ orthogonal |
| C3 Place | — | — | — | ✅ orthogonal | ✅ orthogonal |
| C4 Nasal | — | — | — | — | ✅ orthogonal |
| C5 V-Height | — | — | — | — | — |

¹ Nasals are always voiced — C4 pairs must control for voicing to test Isolate(F_nasal, nasal).
  Mitigation: use /b-m/ and /d-n/ pairs (place-matched voicing-controlled nasality contrast).

² Nasals are stops (manner=plosive) — C2 Isolate must exclude nasal stops from manner test set.
  Mitigation: fricative end of C2 = /s f θ/ (no nasals); plosive end = /t p k/ (oral only).

**Corpus design rule**: For each target contrast (Cx), all orthogonal attributes must be HELD
CONSTANT across the pair. Example for C1 (voicing) in English:
- /t/ vs /d/ in word-initial position before /iː/ (e.g., "tea" vs "dee") — same manner (plosive),
  same place (alveolar), same vowel environment, same speaker.

---

## 3. Four Target Languages

Selected for: (1) resource richness (TTS + ASR), (2) typological diversity (consonant inventories
differ), (3) Choi et al. coverage (2602.18899 spans 96 languages; EN/ZH/DE/JA confirmed).

| Lang | Code | Why | C1 | C2 | C3 | C4 | C5 |
|------|------|-----|----|----|----|----|-----|
| English | en | Primary; Choi et al. main language; LibriSpeech reference | ✅ | ✅ | ✅ | ✅ | ✅ |
| Mandarin | zh | Tonal; lacks voiced/voiceless stop distinction in content words → C1 uses aspirated vs unaspirated; cross-lingual robustness test | C1* | ✅ | ✅ | ✅ | ✅ |
| German | de | Rich consonant inventory, clear VOT distinction; close to EN but typologically distinct; available in Choi et al. | ✅ | ✅ | ✅ | ✅ | ✅ |
| Japanese | ja | Mora-timed; has gemination; pitch-accent; voicing contrast limited to certain positions; cross-typological test | C1† | ✅ | ✅ | ✅ | ✅ |

*Mandarin C1 variant: aspirated vs unaspirated (pinyin p- vs b-, t- vs d-, k- vs g-), which maps
 to the acoustic voicing dimension even though not phonologically "voiced". SAE feature C1 may
 align with this acoustic correlation even without phonological voicing. Prediction: lower C1
 Cause score for ZH than EN (expected: Cause_C1_ZH ≈ 0.55 vs Cause_C1_EN ≈ 0.75).

†Japanese C1: voicing contrast exists (e.g., /ka/ vs /ga/, /ta/ vs /da/) but distributional
 patterns differ from EN (voiced stops in JA are often prenasalized). Same minimal pairs usable.

---

## 4. Concrete Stimulus Table: 5 Contrasts × 4 Languages × 20 Pairs = 400 Pairs

### 4.1 English (en) — 100 pairs

**Stimulus source**: Choi et al. arXiv:2602.18899 (English subset, word-level phoneme pairs)
- Repo: `https://github.com/google-research/phonological-arithmetic` (check for release; paper
  says "publicly available" but actual URL TBD — confirm in Phase 1 implementation)
- Format expected: (word1, word2, phoneme_label_1, phoneme_label_2, wav_or_text)
- Fallback: CMU Pronouncing Dictionary + Coqui TTS (see §5)

| C-ID | Example pairs (word-level) | Phoneme contrast | N pairs | Notes |
|------|--------------------------|-----------------|---------|-------|
| C1-en | tea/dee, tip/dip, cap/cab, pick/pig, rack/rag | /t-d/, /k-g/, /p-b/ | 20 | All word-initial, VC or CVC |
| C2-en | tip/sip, top/sop, par/far, pick/sick, tape/safe | /t-s/, /p-f/, initial position | 20 | Manner only; same place as needed |
| C3-en | tip/pip, dip/bip, ten/pen, deck/beck | /t-p/ (alveolar vs labial) | 20 | Controlled for voicing (both voiceless or both voiced) |
| C4-en | bee/me, dip/nip, bay/may, gear/near | /b-m/, /d-n/ | 20 | Oral vs nasal; same place; same voicing class (voiced) |
| C5-en | beat/bate, beet/bat, seem/same, feet/fate | /iː-eɪ/, /iː-æ/ | 20 | High front vs mid-low; consonants identical |

**Speaker design**: 
- Primary: single-speaker (Choi et al. controlled stimuli or single TTS voice)
- Secondary: 4-speaker variation (2M/2F) for Isolate generalization test (speaker identity = held-constant attribute)

---

### 4.2 Mandarin Chinese (zh) — 100 pairs

**Stimulus source**: Choi et al. (confirmed coverage for ZH) — Mandarin minimal pairs
- Fallback: MaCow/CMN word list + Coqui-TTS zh-CN voice (e.g., coqui/tts-models--zh_CN_espeak_ng_multi-speaker)
- Tone-controlled: all pairs match on tone (e.g., both Tone 1) to isolate consonant contrast

| C-ID | Example pairs (pinyin) | Phoneme contrast | N pairs | Notes |
|------|----------------------|-----------------|---------|-------|
| C1-zh | bā/pā, dào/tào, gǒu/kǒu | aspirated vs unaspirated | 20 | C1 variant for ZH; see §3 note |
| C2-zh | tā/sā, pī/fī, kū/hū | plosive vs fricative (aspirated plosive vs fricative) | 20 | Tone 1 only |
| C3-zh | bō/dō, pā/tā, mā/nā | bilabial vs alveolar | 20 | Both aspirated OR both unaspirated per pair |
| C4-zh | bā/mā, dān/nān, bō/mō | oral stop vs nasal | 20 | /b-m/, /d-n/ at same place; match tone |
| C5-zh | mī/mā (i vs a), nī/nā, bī/bā | High /i/ vs low /a/; high /u/ vs mid /o/ | 20 | VH in CV syllables; identical initial consonant |

---

### 4.3 German (de) — 100 pairs

**Stimulus source**: Choi et al. (confirmed coverage for DE) + MHG minimal pair corpora
- Fallback: Coqui TTS de-DE voice (e.g., `tts_models/de/thorsten/tacotron2-DDC`)
- German has strong aspiration contrast; VOT differences larger than EN

| C-ID | Example pairs | Phoneme contrast | N pairs | Notes |
|------|---------------|-----------------|---------|-------|
| C1-de | Tisch/Disch, Pack/Back, Kasse/Gasse | /t-d/, /p-b/, /k-g/ | 20 | Word-initial; standard Hochdeutsch |
| C2-de | Tor/Sor, Tat/Sat, Paar/Faar | plosive /t p/ vs fricative /s f/ | 20 | German /z/=[ts] avoid; use /s/ fricative |
| C3-de | Pack/Tack, Bahn/Dahn, Pein/Tein | labial vs alveolar | 20 | Controlled voicing |
| C4-de | Bahn/Mann, Dahn/Nahn, Berg/Nerg | /b-m/, /d-n/ | 20 | Oral vs nasal; same place |
| C5-de | bitten/batten, Lit/Lat, Pin/Pan | /ɪ/ vs /a/ | 20 | High front vs open central; identical consonant frame |

---

### 4.4 Japanese (ja) — 100 pairs

**Stimulus source**: Choi et al. (confirmed JA coverage) — kana-level minimal pairs
- Fallback: Coqui TTS ja-JP voice (`tts_models/ja/kokoro/tacotron2-DDC`) or Google TTS (free tier)
- Mora-level alignment: each stimulus = 1-2 mora; MFA not needed (mora boundaries are clear)

| C-ID | Example pairs (kana/romaji) | Phoneme contrast | N pairs | Notes |
|------|---------------------------|-----------------|---------|-------|
| C1-ja | ka/ga, ta/da, ko/go, te/de | /k-g/, /t-d/ (voicing in medial/initial) | 20 | Both in plain (non-prenasalized) context |
| C2-ja | ta/sa, to/so, ka/ha | stop vs fricative | 20 | /t-s/, /k-h/ |
| C3-ja | pa/ta, ba/da, ma/na | bilabial vs alveolar | 20 | Include /p-t/ pair (both voiceless) |
| C4-ja | ba/ma, da/na, bi/mi | oral stop vs nasal | 20 | /b-m/, /d-n/; same mora-final vowel |
| C5-ja | ki/ka, mi/ma, ni/na | /i/ vs /a/ | 20 | High front vs low central |

---

## 5. TTS Fallback Plan

If Choi et al. corpus is not publicly accessible (repo status unknown as of cycle date):

### Step 1: Word selection (CPU, ~30 min)
```python
# skills/autodidact/scripts/stimuli/select_minimal_pairs.py
# Input: CMU Pronouncing Dictionary (EN) / Unidic (JA) / CEDict (ZH) / IPA-DE dict
# Algorithm:
#   For each contrast Ci, find word pairs (w1, w2) where:
#     - IPA(w1) and IPA(w2) differ by exactly 1 phoneme (= the target contrast feature)
#     - All other phonemes identical
#     - Word frequency matched (log-freq band ±0.5)
#     - Word length: 1-2 syllables only
#   Output: CSV with (word1, word2, contrast_id, lang, ipa1, ipa2)
```

### Step 2: TTS synthesis (CPU, ~2 hours for 400 pairs)
```
Per language:
  EN: Coqui TTS p225 voice (LJ Speech single speaker, well-studied in ASR)
      Command: tts --model_name "tts_models/en/ljspeech/tacotron2-DDC" --text "..."
  ZH: Coqui TTS zh-CN or edge-tts (Microsoft Azure free tier, zh-CN-XiaoxiaoNeural)
  DE: Coqui Thorsten (high quality, open source): tts_models/de/thorsten/tacotron2-DDC
  JA: edge-tts ja-JP-NanamiNeural (or kokoro-tts if available CPU)

Duration control: sox rate resample to 16kHz, normalize amplitude to -20 LUFS
Filename: {lang}_{contrast}_{word1}_{word2}_{pair_idx}.wav
```

### Step 3: Validation (CPU, ~1 hour)
```python
# Run Whisper-small on all 400 generated clips
# Verify: correct word recognized for >95% of clips
# Flag: clips where Whisper fails → remove from corpus
# Report: synthesis success rate per language
```

### Step 4: Multi-speaker augmentation (optional, Tier 1)
For Isolate generalization test: resample each pair with 2nd TTS voice (different speaker).
→ Tests that SAE patch effect is speaker-independent (critical for Audio-RAVEL generalization claim)
Use: pyttsx3 or edge-tts with different voice codes per language

---

## 6. Final Stimulus Metadata Schema

```json
{
  "stimulus_id": "C1-en-001",
  "lang": "en",
  "contrast_id": "C1",
  "contrast_name": "voicing",
  "word1": "tea",
  "word2": "dee",
  "ipa1": "/tiː/",
  "ipa2": "/diː/",
  "target_phoneme1": "t",
  "target_phoneme2": "d",
  "target_feature": "voicing",
  "control_features": ["manner:plosive", "place:alveolar", "vowel:iː"],
  "speaker_id": "ljspeech_p225",
  "tts_model": "tts_models/en/ljspeech/tacotron2-DDC",
  "wav1": "stimuli/C1-en-001-tea.wav",
  "wav2": "stimuli/C1-en-001-dee.wav",
  "source": "choi_2602.18899",  // or "tts_fallback"
  "whisper_verified": true,
  "whisper_asr_word1": "tea",
  "whisper_asr_word2": "dee"
}
```

Storage: `memory/learning/stimuli/audio-ravel/metadata.jsonl` (one entry per pair)
WAVs: `memory/learning/stimuli/audio-ravel/{lang}/{contrast_id}/` (gitignored, local only)

---

## 7. Language × Contrast Coverage Matrix

| | C1-Voice | C2-Manner | C3-Place | C4-Nasal | C5-VHeight | TOTAL |
|--|---------|----------|----------|----------|-----------|-------|
| EN | 20 | 20 | 20 | 20 | 20 | **100** |
| ZH | 20* | 20 | 20 | 20 | 20 | **100** |
| DE | 20 | 20 | 20 | 20 | 20 | **100** |
| JA | 20 | 20 | 20 | 20 | 20 | **100** |
| **TOTAL** | **80** | **80** | **80** | **80** | **80** | **400** |

*ZH C1 = aspirated/unaspirated (acoustic voicing proxy), as specified in §3.

---

## 8. Estimated Build Time

| Phase | Task | CPU Time (MacBook Air M2) | Human Time |
|-------|------|--------------------------|------------|
| 1a | Clone Choi et al. repo + select EN subset | 20 min | 30 min (verify corpus) |
| 1b (fallback) | CMU Dict selection script → 400 pairs CSV | 30 min | 15 min |
| 2 | TTS synthesis 400 pairs × 4 voices | ~2 hours | 15 min (setup) |
| 3 | Whisper-small verification pass | ~10 min | 5 min (check failures) |
| 4 | Metadata JSONL generation | 5 min | — |
| **TOTAL** | | **~3 hours** | **~65 min** |

All Tier 1 (CPU-only, no Leo approval needed). Whisper-small runs on MacBook Air M2 in ~0.5s/sample.

---

## 9. Integration into Audio-RAVEL Protocol

This 400-pair table directly implements **Phase 1** of the Audio-RAVEL implementation plan
(audio-ravel-protocol.md §6 Phase 1: Stimulus Preparation):

- ✅ "Download Choi et al. minimal pairs corpus (English subset)" → §4.1 + §5 fallback
- ✅ "Select 100 pairs × 3 attributes" → Expanded to 400 pairs × 5 contrasts × 4 languages
- ✅ "Validate: run Whisper ASR on all pairs" → §5 Step 3
- → Phase 2 (SAE feature identification) unblocked once stimuli are ready

**Next action**: `skills/autodidact/scripts/stimuli/select_minimal_pairs.py` scaffold (Q063 build follow-on, Tier 0/1).

---

## 10. Open Questions

1. **Choi et al. repo access**: Primary source. Search `github.com/google-research/phonological-arithmetic`
   and supplementary of arXiv:2602.18899 (check Feb 2026 paper for "our stimuli are available at...").

2. **ZH aspirated vs voicing**: Does AudioSAE have ZH features labeled? If AudioSAE-Whisper is
   trained on English-dominant LibriSpeech, ZH stimuli test cross-lingual feature generalization.
   Prediction: feature_concept_F1 drops for ZH vs EN (expected: 0.65 vs 0.88 for voicing feature).

3. **Mandarin tones as confound**: Tonal variation within a pair could affect gc(F) measurement
   (tone 1 vs tone 4 changes F0 substantially). Solution: match all pairs on tone. For C5-zh
   (vowel height), use tone 1 only (constant F0 contour).

4. **Japanese prenasalization**: Some /b/ in JA may surface as [mb] (prenasalized) in certain
   speakers/dialects. Filter these from C4 pairs using formant analysis or ASR probability check.

5. **TTS vs natural speech**: RAVEL paper used Wikipedia text + natural speech (Wikipedia corpora).
   Our TTS fallback is less natural but more controlled. Impact: TCS(F) (temporal coherence) may
   be artificially high for TTS (cleaner phoneme boundaries). Flag in paper: "TTS stimuli — clean
   upper bound; natural speech test deferred to Tier 2."

---

*DoD check: stimulus table ✅ | TTS source ✅ | 5 contrasts × 4 languages × 20 pairs = 400 pairs ✅*
*Q063 DONE. Next: implement select_minimal_pairs.py scaffold (Tier 0 build, ~50 LOC).*
