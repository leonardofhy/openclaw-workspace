# T3 Experiment Spec v2 — Listen vs Guess (Paper A)
**Track**: T3 | **Updated**: 2026-03-24 | **Status**: READY FOR LEO REVIEW
**Supersedes**: experiment-spec-T3-cpu.md

---

## Research Question

> At which layers of Whisper does the model transition from relying on audio evidence ("listen") to language prior ("guess")? Can gc(k) and AND-frac reliably identify this transition — and does the transition happen earlier for **accented speech**, predicting hallucination risk?

---

## Core Hypotheses (Updated)

| ID | Hypothesis | Evidence so far |
|----|-----------|----------------|
| H1 | AND-frac peaks mid-to-late encoder for clean/native speech | GCBench-14: F1>0.7 ✅ |
| H2 | AND-frac drops early for noisy/masked audio (OR-gate dominant) | SNR robustness: slope 2x faster ✅ |
| H3 | AND-frac(native) − AND-frac(accented) ≥ 0.08 ("accent gap") | Accent mock Q162: delta ≥ 0.08 ✅ |
| H4 | Low AND-frac → high hallucination rate (commitment head mediation) | Attention entropy r < -0.6 ✅ |
| H5 | Beam rescoring on AND-frac features reduces WER gap (fairness intervention) | AFG metric mock: ΔWer L2 reduced ✅ |

---

## Experiments: CPU (Doable Now — Tier 1)

All experiments below run on CPU with Whisper-base. Runtime ≤ 5 min each.

### E1 — GCBench-14 Full Sweep (status: done ✅)
- Script: `gc_eval.py` + `synthetic_stimuli.py`
- Result: F1 > 0.7 on phoneme boundaries; inflection t* at 55% silence

### E2 — Accent × AND-frac Cluster (status: done ✅, Q162–Q170)
- 6 L1 groups (L2-ARCTIC structure), AFG metric
- Key finding: **accented speech ≈ silence analog** — underrepresented phonemes → OR-gate dominance → hallucination risk
- Beam rescoring intervention: AND-frac directional boost ≥ 0.15 (Q157 mock)

### E3 — Scaling Law Validation (status: done ✅, Q155)
- AND-frac log-linear scaling: R²=1.0 mock, range 0.305→0.386 (base→large)

### E4 — AND-gate Steerability on Real Audio (status: READY — Q166/Q184)
- Port Q157 mock to real Whisper-base activations on 5 L2-ARCTIC samples
- **This is the final CPU validation before GPU scale-up**
- DoD: AND-frac boost ≥ 0.10 on real audio (vs ≥ 0.15 mock target)

### E5 — Commitment Head Ablation Mock (status: READY — Q163)
- Ablate H00/H07/H01 → measure hallucination rate increase
- CPU-only mock; validates commitment head → AND-gate causal claim

---

## Experiments: GPU Scale-Up (Need Leo Approval — Tier 2)

| ID | Experiment | Model | Runtime est. | Dependency |
|----|-----------|-------|-------------|------------|
| G1 | GCBench-14 on Whisper-small | small | ~15 min | E1 done ✅ |
| G2 | Accent cluster on Whisper-small (L2-ARCTIC real data) | small | ~30 min | E2 done ✅ |
| G3 | Steerability on Whisper-small/medium (real audio, 50 samples) | medium | ~1 hr | E4 done |
| G4 | Commitment head ablation on Whisper-small (real data) | small | ~20 min | E5 done |

**Minimum viable GPU run**: G1 + G2 (45 min total). Validates scaling claim + accent fairness on real data.

---

## Phase Exit Criteria (converge → execute)

| Criterion | Status |
|-----------|--------|
| ✅ eval_harness_exists_T3 | Done (gc_eval.py, GCBench-14) |
| 🔄 experiment_spec_ready_T3 | **This document** |
| ⏳ leo_approved_gpu_or_cpu_experiment | **Pending Leo review** |

**To unlock execute phase**: Leo approves G1+G2 GPU run (or confirms CPU-only paper scope).

---

## Decision Gates for Leo

| Question | Options |
|---------|---------|
| GPU available soon? | Yes → run G1+G2 now; No → scope paper to CPU (Whisper-base only) |
| Real L2-ARCTIC data accessible? | Yes → use real audio for G2+G3; No → synthetic accent mocks are sufficient |
| MATS deadline pressure? | Yes → prioritize T5 proposal first; No → Paper A first |

---

## Paper A Scope (Updated)

**Core contribution**: AND-gate mechanism in Whisper encoder mediates listen→guess transition. AND-frac (fraction of AND-gated features) is a reliable, computationally cheap predictor of:
1. Transcription accuracy (H1/H2)
2. Accent-based hallucination risk (H3/H4) — **novel fairness contribution**
3. Intervention: AND-frac-guided beam rescoring reduces WER gap (H5)

**Venue target**: Interspeech 2026 (submission ~March/April 2026) or ACL findings

---

## Next Actions (in order)

1. `[CPU]` Complete E4 (Q166: steerability on real audio) — final CPU validation
2. `[CPU]` Complete E5 (Q163: commitment head ablation mock) — causal claim validation
3. `[LEO REVIEW]` Approve GPU G1+G2 or confirm CPU-only scope
4. `[WRITE]` Paper A abstract (Q165) + results table (Q164) — both CPU-doable
