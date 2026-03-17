# Cycle c-20260315-1515 — Q104: t* as Regulatory Capability Threshold

> Action: learn | Track: T5 | Phase: explore-fallback
> Created: 2026-03-15T15:15 +08:00

---

## Design Doc: t* as Regulatory Capability Threshold

**Research Question:** Can the collapse onset step t* (from Q085) serve as a compute-light, interpretable capability standard for audio-LLMs? Can regulators, auditors, and model card authors use t* as a certification threshold?

---

## Background

t* is the decoder step at which audio information stops causally influencing the model's output (from Q085: `collapse_onset_step` = argmin(Isolate_in(t), threshold = 0.1)). High t* = audio drives transcription deep into decoding. Low t* = model defaults to language model priors after only a few steps.

This is different from gc(L) (encoder layer sweep) — t* measures **decoder-side** audio utilization over generation time, not encoder-side causal localization.

---

## t* Taxonomy

| t* Range | Label | Interpretation | Risk Level |
|----------|-------|----------------|-----------|
| t* ≥ 8 | **Genuine Audio** | Model audio causally shapes ≥8 decoder steps; audio grounding is sustained | LOW |
| 4 ≤ t* < 8 | **Partial Grounding** | Audio matters early but drops off; moderate reliance on language prior | MEDIUM |
| 1 ≤ t* < 4 | **Early Collapse** | Audio is decisive only for 1-3 tokens; model switches to LM prior quickly | HIGH |
| t* < 1 (≈0) | **Text Wrapper** | Audio has negligible causal role; model is effectively an LM operating on noisy input | CRITICAL |

**Calibration anchor (empirical target, to verify with real data):**
- Whisper-small on clean speech: t* ≈ 10-15 (expectation based on encoder strength)
- Distorted / overlong context: t* degrades to 2-4
- Safety-bypassed model (OBLITERATUS scenario): t* expected < 3

---

## Compute-Light Audit Protocol

### Step 1: Minimal Pair Audio Pairs (same as gc(k))
- Use same 20 phonological minimal pair clips as gc(k) protocol (Paper A §4)
- No new data required if gc(k) protocol already run

### Step 2: Run collapse_onset_step Diagnostic (CPU, Tier-1)
```
python3 skills/autodidact/scripts/collapse_onset_step.py \
  --model whisper-small \
  --audio-dir audit/minimal_pairs/ \
  --output-dir audit/results/
```
- Outputs: Isolate_in(t) curve per example, t* per example, t* distribution summary
- Runtime: ~3 min for 20 pairs on CPU (whisper-small forward pass)

### Step 3: Compute t* Score
- t*_mean: mean across 20 minimal pair examples
- t*_min: minimum (worst-case) — for certification purposes, use this
- Classification: apply taxonomy table above

### Step 4 (optional): Stratified t* by phoneme class
- Run separately for voicing contrasts, place contrasts, manner contrasts
- Flag classes with differential t* — disparity detection (Risk A6 in Paper A)

**Total: ~5 min CPU, 20 pairs, no GPU required.**

---

## Governance Framing

### Why t* > gc(k) for regulatory contexts

gc(k) is a **spatial** measure (which layer). t* is a **temporal** measure (how long during generation). Both are needed for a complete structural certificate:

| Measure | Answers | Certification Role |
|---------|---------|-------------------|
| gc(L) encoder sweep | "Where does the model listen?" | Encoder capability: can it extract audio? |
| t* collapse onset | "How long does it keep listening?" | Decoder commitment: does it act on audio? |

A model could pass gc(k) (has a listen layer) but fail t* (uses audio for only 1 step). **Both certificates are required for full structural grounding.**

### Regulatory Use Cases

1. **Model Card Standard:** Require gc_peak + t*_mean + t*_min as mandatory fields in audio-LLM model cards. Simple scalar values, compute-light, reproducible.

2. **Pre-Deployment Audit:** Before high-stakes deployment (clinical, legal, border control), run both protocols as pass/fail gates. Proposed thresholds: gc_peak > 0.6 AND t* ≥ 4 (partial grounding minimum).

3. **RL Training Certification (MPAR² scenario):** gc(k) + t* certificate pair verifies that RL training genuinely restored audio utilization, not just behavioral benchmark scores. t* should increase from pre-MPAR² to post-MPAR².

4. **Adversarial Hardening Verification:** After safety fine-tuning, verify t* does not regress. A model that increased behavioral safety scores but shows decreased t* may have traded audio grounding for over-reliance on text-based safety filters.

---

## Connection to Paper C (T5)

Paper C (Listen-Layer Audit / MATS proposal) is about detecting **safety-relevant audio grounding failures**. t* adds a temporal dimension to the Paper C contribution:

- **Section 3 (Metrics):** Add t* as the third metric alongside M7 (ΔGS) and M9 (causal abstraction consistency). Rename to "tri-metric safety signature": {gc(k), M9, t*}
- **Section 4 (Detection Protocol):** Add Step 2.5: run collapse_onset_step after encoder gc sweep
- **Appendix (Policy):** ~500-word policy note on t* taxonomy as capability standard, referencing EU AI Act Annex III (high-risk AI systems) and NIST AI RMF auditing requirements

**Key claim for Paper C:** "An audio-LLM with t* < 3 is not a genuine audio-language model — it is a text-language model with audio tokenization as input formatting. Our protocol detects this distinction in 5 minutes on CPU, without adversarial examples, without access to training data, and without proprietary model weights."

---

## Open Questions for Leo

1. Should t*_min or t*_mean be the certification threshold? Mean is less sensitive to outliers; min is more conservative (worst-case audit).
2. Is the taxonomy calibration (t* ≥ 8 = genuine) consistent with Whisper-small empirical behavior? Need to verify with Q085 script.
3. Paper C vs standalone policy note: similar dilemma as gc-regulatory-audit-pitch.md Q84. Probably Paper C appendix first, then FAccT 2027 workshop.

---

## Artifacts
- This design doc (cycle file, will GC in 48h → should be saved to pitches/)
- Next: Q085 script should output t* values; when complete, verify taxonomy calibration

## Next
Promote this design to `memory/learning/pitches/t-star-regulatory-threshold.md` (needs persisting before GC). Q107 (RAVEL Isolate curve as gc proxy) is a direct computational complement — when t* ≈ argmin(Isolate), we get a single unified spatial-temporal certificate.
