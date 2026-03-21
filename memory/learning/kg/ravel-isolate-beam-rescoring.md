# RAVEL Isolate(k) as Beam Rescoring Signal

**Created:** 2026-03-21 (Cycle c-20260321-1515, Q133 learn)  
**Tracks:** T3  
**Status:** Design complete — ready for build (q133_alignment_mock.py)

---

## Core Claim

**AND-frac at gc-peak layer is a deployable soft intervention for ASR beam rescoring.**

Tokens decoded during low-AND% encoder windows are more likely to be text-predicted (hallucinated). Penalizing these in beam rescoring improves hallucination selectivity without model retraining.

---

## Theoretical Basis

| Result | Correlation | Implication |
|--------|------------|-------------|
| Q107 Isolate ≈ gc proxy | r=0.904 | Don't compute Isolate separately — AND-frac suffices |
| Q096 FAD × AND% | r=−0.960 | OR-gate = text-predictable = poor grounding |
| Q134 AND→OR at t* | structural | AND-drop detects hallucination onset |

**Isolate(k) at gc-peak ≈ AND-frac at gc-peak** (per Q107). Both measure the same underlying property: audio-groundedness at the most critical layer.

---

## Mechanism

```
Audio → Whisper encoder → gc-peak layer (max gc(k))
                              ↓
                    AND-frac(t) per timestep  ← Q001 harness computes this
                              ↓
Forced alignment: encoder timestep t → decoder token position p
                              ↓
Rescoring signal: score(beam_i) += α × mean(AND-frac at positions in beam_i)
```

**High AND-frac** → audio-grounded → trustworthy → boost score  
**Low AND-frac** → text-predicted → hallucination risk → penalize score

---

## Key Design Issues

1. **Alignment**: Need encoder-t → decoder-token mapping. Use CTC alignment or cross-attention max from Whisper decoder.
2. **Per-timestep vs global**: Q107 showed global Isolate≈gc. Need per-timestep version. Hypothesis: per-timestep AND-frac tracks gc per-timestep as well (plausible, needs verification).
3. **Threshold**: AND-frac < 0.3 at gc-peak → high-risk token. Calibrate on LibriSpeech.

---

## Relation to Other Interventions

| Intervention | Type | Q-ref |
|---|---|---|
| AND-gate steering (activation patching) | Hard | Q139 |
| Beam rescoring via AND-frac | **Soft** | **Q133** |
| Hallucination detection at t* | Detection | Q134 |

Soft intervention (Q133) is more deployment-practical: no model edits, just rescoring.

---

## Build Plan

**Script:** `q133_alignment_mock.py`  
**Tier:** 0 (scaffold) → 1 (CPU mock with Q001 data)  
**Inputs:** Q001 eval harness outputs (AND-frac per layer per timestep, attention maps)  
**Outputs:** Per-token AND-frac at gc-peak, oracle rescoring WER gain  
**Dependencies:** Q001/Q002 data in `memory/learning/artifacts/` or `cycles/`

---

## Open Questions

1. Does per-timestep AND-frac correlate with per-token hallucination ground truth?
2. What is the coverage? (Only ~23% phoneme space is FAD-biased — is this enough signal?)
3. Can AND-frac be computed in real-time (streaming rescoring)?
