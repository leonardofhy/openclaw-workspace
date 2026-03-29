# KG: Accent Power Steering — Q217 Implementation Plan

**Created:** 2026-03-29  
**Cycle:** c-20260329-1545  
**Serves:** Q217 (power steering at L* for accent robustness)  
**Status:** Ready for tomorrow's build (build budget resets 2026-03-30)

---

## What Q206 Proved (Baseline to Extend)

Q206 tested Jacobian SV power steering on L2-ARCTIC mock for **hallucination suppression**:
- Task: suppress hallucination direction at L*=8 via α · steering_vec subtraction
- Best α = 0.7 → WER 0.1087→0.1015 (−6.6% vs baseline)
- AND-frac restored: 0.094→0.181 (+0.087)
- Hallucination direction quality: 0.833 (cosine similarity of CAA direction)
- Temp-scaling (1.2) was slightly better overall (−9.2%) but less mechanistically targeted
- **Key insight**: steering at L* causally reduces OR-gate hallucination; targeted mechanism confirmed

---

## How Q217 Differs: Accent Direction vs Hallucination Direction

**Same architecture**: Whisper-base, L*=8, subtract at residual stream before L*→L*+1 block.

**Different direction**: Q217 uses **accent bias direction** (native vs accented activations at L*)
- In Q206: CAA direction = hallucination activations minus clean activations at L*
- In Q217: CAA direction = native-speech activations minus accented-speech activations at L*
- Interpretation: steering "toward native" re-routes accent OR-gate → AND-gate pathway

**Why accent direction should work better than Q206**:
1. Accent bias is more systematic (not sample-level noise, but distributional shift)
2. AND-frac gap for accented: expected Δ ≈ 0.10–0.15 (vs 0.087 in Q206's hallu case)
3. Accent bias direction has higher SNR across samples (L1 phoneme patterns are consistent)
4. **Prediction**: α sweet spot at 0.5–0.8 (similar to Q206, may skew lower if direction is entangled with phoneme identity)

---

## Expected Results (Theory-Grounded Predictions)

From KG note `accent-andfrac-fairness-theory.md`:
| Metric | Predicted | Q206 Baseline |
|--------|-----------|---------------|
| Baseline WER (accented) | 0.18–0.25 | 0.109 (L2-ARCTIC native-ish) |
| WER improvement w/ steering | 8–14% | 6.6% |
| AND-frac delta | ≥0.09 | +0.087 |
| α sweet spot | 0.5–0.8 | 0.7 |
| Steering vs temp-scale | Closer to parity | temp-scale slightly wins |

**Strong hypothesis**: For accented speech, mechanistic steering will beat temp-scaling because the accent direction is distributional (not sample noise) — temp-scale can't fix a systematic AND-frac deficit.

---

## Implementation Plan

### Mock Data
```python
# L2 accent mock: simulate 6 L1 groups (ZH, KO, HI, ES, VI, AR)
# Each group: 10 samples, phoneme confusion injected per L1 profile
# Native reference: 20 samples baseline (same vocab, no confusion)
n_accented = 60  # 6 groups × 10
n_native = 20
n_total = 80
```

### Steering Pipeline (extend q206_power_steering_wer.py)
```python
# 1. Extract L* activations for native vs accented (calibration set)
# 2. Compute CAA accent direction: mean(native_acts) - mean(accented_acts) at L*
# 3. Alpha sweep: [0.0, 0.3, 0.5, 0.7, 0.9, 1.2, 1.5]
# 4. Apply: acts_steered = acts + alpha * accent_direction
# 5. Measure: WER, AND-frac, per-L1 WER breakdown
```

### Key Metrics
- `wer_native` (no steering, native speech)
- `wer_accented_baseline` (no steering, accented speech)
- `wer_accented_steered` (best alpha)
- `and_frac_before/after` at L* for accented samples
- Per-L1 WER breakdown (ZH, KO, HI, ES, VI, AR)
- WER Fairness Gap = `wer_accented_steered − wer_native` (should narrow vs baseline)

### Definition of Done
```
✓ Mock accented WER baseline measured (expected 0.18-0.25)
✓ Alpha sweep complete ([0.0, 0.3, 0.5, 0.7, 0.9, 1.2, 1.5])  
✓ Best alpha identified (WER minimum)
✓ AND-frac delta reported (expected ≥0.09)
✓ Per-L1 WER breakdown showing differential improvement
✓ Summary table: native / accented-base / accented-steered / temp-scale
✓ Conclusion: does steering close the accent fairness gap?
```

---

## File Structure (reuse Q206)
- Input: extend `memory/learning/artifacts/q206_power_steering_wer.py`
- Output: `memory/learning/artifacts/q217_accent_steering.py`
- Results: `memory/learning/artifacts/q217_results.json`
- Log: append to `events.jsonl` with task_id Q217

---

## Connections
- `accent-andfrac-fairness-theory.md` → theoretical grounding (AND-frac gap mechanism)
- `q206_results.json` → baseline numbers, alpha grid, architecture reference
- `q202_acoustic_restoration.py` → restore AND-frac under noise (different perturbation, same L*)
- `ravel-isolate-beam-rescoring.md` → future extension: use Isolate score to validate no speaker bleed

---

## Open Questions for the Build
1. Should the accent CAA direction be computed per-L1 (6 directions) or averaged? → Start averaged; per-L1 breakdown in metrics.
2. Do we need orthogonal projection to prevent speaker identity bleed? → RAVEL Isolate score will reveal this; fix in follow-up if Isolate < 0.5.
3. Does the AND-frac restoration correlate with WER improvement per sample? → Report Pearson r to validate causality.
