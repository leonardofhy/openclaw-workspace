# Paper A — Status Tracker

> 最後更新：2026-03-19

## Overview
**Title:** The Listening Geometry: Where Audio-Language Models Listen, Guess, and Collapse
**Target:** Interspeech 2026 (already submitted) / arXiv preprint
**Word count:** ~7,300 words

---

## Section Status

| Section | Status | Notes |
|---------|--------|-------|
| §1 Introduction | ✅ Complete | 4 paragraphs, contributions list |
| §2 Related Work | ✅ Complete | 4 subsections |
| §3 Method | ✅ Polished | 2 TODOs remain (ALME citation) |
| §4 Results | ✅ Prose done | Tables have [PENDING] for GPU data |
| §5 Discussion | ✅ Written | gc(k) unification, AND-gate safety, limitations, future work |
| Abstract | ✅ Complete | 200 words, cites mock r=0.877 |
| References | ✅ Complete | refs.bib + results_table.tex |

---

## Experiments

### Real (GPU required)
| Exp | Description | Status |
|-----|-------------|--------|
| Q001 | Voicing geometry, Whisper-base | ⚠️ Partial (layer 5 only) |
| Q002 | Causal contribution ablation, Whisper-base | ⏳ Pending GPU |
| Q001-small | Same, Whisper-small | ⏳ Pending GPU |
| Q002-small | Same, Whisper-small | ⏳ Pending GPU |

### Mock (Validated)
- 27 experiments, median |r| = 0.877, all deterministic
- Validates algebraic logic of gc(k), AND/OR gates, Listening Geometry

---

## Pre-registered Predictions

1. **Scale-up**: k* should occur at ~50% encoder depth across Whisper-base/small/medium
2. **ALME conflict**: Models with low α_AND should fail ALME conflict items at higher rate
3. **MPAR² RL shift**: RL training should increase gc(k) and α_AND at the listen layer

---

## Pending (GPU / Data)

- [ ] Q001/Q002 full run on Whisper-base (battleship GPU)
- [ ] Scale up to Whisper-small/medium
- [ ] ALME conflict item validation (~500 items)
- [ ] Qwen2-Audio full pipeline (NDIF cluster or local GPU)

---

## Next Action

Battleship GPU → `python3 skills/shared/experiment_dispatch.py --queue Q001-base Q002-base`
