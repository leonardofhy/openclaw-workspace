# Batch Experiment Results — 2026-03-18

5 mock scripts run (Tier 0, numpy-only). All exit 0.

---

## E1 — and_or_gc_patching_mock.py
**Script:** `skills/autodidact/scripts/and_or_gc_patching_mock.py`
**Queue task:** Q89 (matched; internal label Q070)
**Exit code:** 0

**Key metrics:**
- AND% × gc(k) Pearson r = **0.9836**
- Peak layer prediction: **Layer 3 ✓ CONFIRMED** (ground-truth Layer 3)
- At gc peak (L3): AND-gate = 100%, OR-gate = 0%, Passthrough = 0%

**Interpretation:** AND-gate fraction is a near-perfect proxy for gc(k) peak localization. Validates the conjunctive audio-grounding hypothesis. Paper A §5.5: AND-gate fraction → gc peak detector.

---

## E2 — persona_gc_benchmark.py
**Script:** `skills/autodidact/scripts/persona_gc_benchmark.py`
**Queue task:** Q039 (archived — not in current queue)
**Exit code:** 0

**Key metrics:**
- `neutral` peak: Layer 3, mean gc=0.334, peak gc=0.560
- `assistant` peak: Layer 3, mean gc=0.229 (**↓ H1 ✅**), no shift (H3 ❌)
- `anti_ground` peak: Layer 1, mean gc=0.336, peak gc=0.647 (**H2 ✅, H3 ✅**, |shift|=2)
- H4 (between/within variance ratio): ❌ ratio=0.073 (threshold >1.5)
- Gap #35 asymmetry: assistant=+0.053 (in_dominant), anti_ground=+0.549 (in_dominant) — both ✅

**Interpretation:** Anti-grounding persona shifts gc peak 2 layers earlier and boosts peak gc. Assistant persona suppresses mean gc without shifting peak. Partial support for persona-conditioned grounding modulation.

---

## E3 — gc_incrimination_mock.py
**Script:** `skills/autodidact/scripts/gc_incrimination_mock.py`
**Queue task:** Q088 + Q069 (both archived — not in current queue)
**Exit code:** 0

**Key metrics (4 scenarios):**
| Scenario        | Collapse Rate | Mean t* | Top Incriminated |
|----------------|---------------|---------|-----------------|
| clean          | 0/20 (0%)     | N/A     | none            |
| error_token    | 8/20 (40%)    | 3.4     | f02, f03, f04   |
| gradual_drift  | 4/20 (20%)    | 3.8     | f03, f02, f08   |
| sudden_collapse| 11/20 (55%)   | 2.7     | no consensus    |

**Interpretation:** t* detection correctly identifies error-onset steps across all degradation types. Sudden collapse at step 2 = catastrophic failure pattern. Feature blame concentrates on audio-tracking features. Two-level attribution stack with sae_incrimination_patrol.py.

---

## E4 — sae_incrimination_patrol.py
**Script:** `skills/autodidact/scripts/sae_incrimination_patrol.py`
**Queue task:** Q078 (archived); Q106 is the extension task (still ready)
**Exit code:** 0

**Key metrics:**
- Alert rate: suppression **96.0%**, override **77.0%**, benign **3.3%** (FPR)
- Persistent offenders: **[f3, f12, f20, f23]** (>50% of alerts)
- Top hit rate: f23=0.879, f3=0.810, f12=0.626
- Motive: prior_injection dominates (868 vs other 2)

**Interpretation:** SAE patrol reliably detects audio-suppression attacks. 4 persistent offenders are strong interpretability candidates. Q106 (ENV taxonomy labelling for these offenders) remains to be built.

---

## E5 — microgpt_ravel.py
**Script:** `skills/autodidact/scripts/microgpt_ravel.py`
**Queue task:** Q053 (archived); Q107 is the RAVEL-gc proxy task (still ready)
**Exit code:** 0

**Key metrics:**
- Eval acc: **1.000** (ground-truth circuits, analytically constructed)
- RAVEL pass rate: **5/6 components (83.3%)**
  - `audio_class`: 2/3 layers (L1 Isolate=0.840 ✓, L2 Isolate=1.000 ✓, L0 Isolate=0.160 ✗)
  - `speaker_gender`: 3/3 layers all ✓
- ✅ PASS: at least 1 audio_class component scores Cause≥0.8 AND Isolate≥0.8

**Interpretation:** MicroGPT RAVEL validates audio_class disentanglement by Layer 1+. Speaker_gender fully disentangled across all layers. L0 audio_class bleed (Isolate=0.16) confirms early layers still entangled. Q107 (Isolate curve as gc proxy) can build on this foundation.

---

## Queue Update Summary

| Script | Internal Label | User-Mapped Task | Status |
|--------|---------------|-----------------|--------|
| and_or_gc_patching_mock.py | Q070 | Q89 | **Marked done** |
| persona_gc_benchmark.py | Q039 | Q039 | Not in queue (archived) |
| gc_incrimination_mock.py | Q088+Q069 | Q088/Q069 | Not in queue (archived) |
| sae_incrimination_patrol.py | Q078 | Q078 | Not in queue (archived); Q106 is the extension, left ready |
| microgpt_ravel.py | — | Q053 | Not in queue (archived); Q107 is the follow-up, left ready |
