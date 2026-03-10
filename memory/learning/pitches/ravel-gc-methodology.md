# RAVEL × gc(k): Causal Isolation Methodology Extension
**Track:** T3 (Listen vs Guess) | **Task:** Q071 | **Date:** 2026-03-08
**Type:** Tier 0 methodology extension doc

---

## 1. Background: What RAVEL Does

**RAVEL** (Causally Abstracted Variables for Representation Learning — Ravel et al.) is a
mechanistic interpretability evaluation framework that tests whether a probing method
achieves *causal isolation*: not just *correlation* with a target attribute, but
*non-interference* with orthogonal attributes when you intervene on the representation.

RAVEL's two-criterion test:
1. **Cause**: Patching representation $\hat{h}$ from a source input into a target input
   changes the model output on attribute A (the target attribute).
2. **Isolate**: The same patch does NOT change model output on attribute B (orthogonal attribute).

A method passes RAVEL if it achieves high Cause AND high Isolate scores simultaneously.
The key insight: interventions should be *surgically specific*.

**Why it matters**: Without the Isolate criterion, a probe could be latching onto a
"master controller" dimension that affects many things at once — interventions would be
blunt instruments. RAVEL forces us to prove surgical precision.

---

## 2. The Problem: gc(k) is Not Yet RAVEL-Certified

Our current gc(k) metric measures *causal influence* (listen vs guess) but does NOT
verify causal isolation. Specifically:

- **Known**: High gc(k) at layer k* → acoustic features causally determine output
- **Unknown**: Does patching gc(k)-identified features at k* affect ONLY phonetic content,
  or does it also disrupt prosody, speaker identity, language ID, emotional tone, etc.?

If gc(k) features are not causally isolated, our causal patching results (Paper A §4.x)
may be confounded: we might be claiming "we patched phonetic grounding" when we actually
patched a shared representation that also changes speaker identity → output changes are
partially due to speaker-dependent LM bias, not acoustic content restoration.

**This is a real threat to Paper A's validity.**

---

## 3. Extending gc(k) with RAVEL Cause/Isolate

### 3.1 Attribute Decomposition

We define 3 mutually exclusive audio attributes for the RAVEL test:

| Attribute | Symbol | Definition | Test output |
|-----------|--------|------------|-------------|
| Phonetic content | A_phon | What words are spoken | Transcript tokens |
| Speaker identity | A_spkr | Who is speaking | Speaker classification score |
| Language identity | A_lang | What language is spoken | Language ID probability |

These three can be independently measured from a forward pass → suitable for RAVEL testing.

### 3.2 Cause Score for gc(k)

For a phonetic patching experiment at layer k*:
1. **Source**: clean audio x_src (content: "cat")
2. **Target**: corrupted audio x_tgt (content: "dog", same speaker, same language)
3. **Patch**: replace h^(k*)_{x_tgt} ← h^(k*)_{x_src}

**Cause(k*) = P(transcript = "cat" | patched) - P(transcript = "cat" | unpatched)**

High Cause → gc(k*) features carry phonetic content causally.

### 3.3 Isolate Score for gc(k)

Same patch as above, measuring orthogonal attributes:

**Isolate_spkr(k*) = 1 - |P(speaker = src_speaker | patched) - P(speaker = tgt_speaker | unpatched)|**
**Isolate_lang(k*) = 1 - |P(language = src_lang | patched) - P(language = tgt_lang | unpatched)|**

**Combined Isolate(k*) = min(Isolate_spkr, Isolate_lang)**

High Isolate → patching gc(k*) features does NOT contaminate speaker/language representations.

**RAVEL-gc(k) Score** = Cause(k*) × Isolate(k*)
→ Only high if BOTH causal influence AND surgical specificity are achieved.

### 3.4 Layer-wise RAVEL Profile

Run the above across all encoder layers k = 1..K:

```
For each k:
    - Compute Cause(k), Isolate_spkr(k), Isolate_lang(k)
    - RAVEL_score(k) = Cause(k) × min(Isolate_spkr(k), Isolate_lang(k))
    - Plot as a 3-panel figure across layers

Expected profile:
    - Low k: low Cause (not yet phonetically specific)
    - Mid k (k*): HIGH Cause, HIGH Isolate → RAVEL peak = listen-layer boundary
    - High k: Cause may still be high, but Isolate may drop (entangled representations)
```

The listen-layer k* is validated by RAVEL if and only if it is the RAVEL peak layer.

---

## 4. Implementation Plan (Tier 0 → Tier 1 CPU)

### Phase 1: Synthetic Data (Tier 0 scaffold, no real data)
- TTS: generate 50 pairs (same speaker, different content) + 50 pairs (different speaker, same content)
- Mock speaker classifier: cosine similarity on x-vectors (pre-extracted)
- Mock language classifier: langdetect on transcript

### Phase 2: CPU experiment (Tier 1, < 5 min)
- Model: Whisper-small (CPU feasible)
- 100 sample pairs (50 same-spkr/diff-content, 50 diff-spkr/same-content)
- Layer-wise patching via existing `gc_eval.py` hook infrastructure
- Output: RAVEL_score profile across 32 encoder layers

### Phase 3: Report in Paper A
- New subsection: "§3.6 Causal Isolation Validation via RAVEL"
- Figure: 3-panel RAVEL profile (Cause / Isolate / RAVEL-score vs layer)
- Table: RAVEL-gc(k) peak layer vs our gc(k) peak layer (should match if method is valid)
- Claim: "gc(k) identifies causally isolated phonetic features at k*, confirmed by RAVEL"

---

## 5. Connection to Existing Work

| Prior method | RAVEL status | gc(k) advantage |
|-------------|-------------|-----------------|
| DAS (Geiger et al.) | Designed for RAVEL compliance | gc(k) extends to audio domain (no text tokens needed) |
| Probing classifiers | Fail Isolate (entangled) | gc(k) uses causal patching, not linear probe |
| Attention attribution | Often fail Cause (correlational) | gc(k) explicitly measures output probability shift |
| LEACE | Good Isolate, weak Cause | gc(k) jointly optimizes both |

**Key novelty claim**: gc(k) is the first audio-native metric that is designed to pass RAVEL.
Verifying this empirically (Phase 2) would be a strong methodological contribution.

---

## 6. Threat Responses

**Q: "Doesn't speaker voice contaminate your phonetic patches?"**
A: Exactly what RAVEL-Isolate_spkr tests. We measure it. If contamination exists, we
   report it honestly and discuss subspace disentanglement as future work.

**Q: "Layer k* might differ across speakers / languages"**
A: True → we report RAVEL profile mean ± std across speaker groups. Robustness of k*
   across groups is an ablation we pre-register.

**Q: "Your Isolate metric is too loose (transcript-level, not activation-level)"**
A: We use transcript-level output attribution as a proxy. Direct activation-space RAVEL
   would require a speaker/language probe head — add as Appendix if reviewer asks.

---

## 7. Slot in Paper A

- **§3.6** (new): "Causal Isolation Validation: RAVEL Protocol for gc(k)"
  (~150 words, 1 figure reference)
- **Appendix B** (new): Full RAVEL implementation + per-layer table
- **§4.2** update: Add "gc(k) passes RAVEL at k*" as empirical claim with pointer to §3.6

---

## 8. Next Steps

1. ✅ This doc (Q071 complete)
2. 🟢 Q072: Extend `AntiConfoundChecker` to include RAVEL Isolate score computation
3. → Then: integrate into `gc_eval.py` as `--ravel` flag (Tier 1 CPU, new task)
4. → Paper A §3.6 draft (Tier 0, new task after Q072)

---

*Q071 complete. Next: Q072 (AC-11 RAVEL causal isolation — extend AntiConfoundChecker Tier 1).*
