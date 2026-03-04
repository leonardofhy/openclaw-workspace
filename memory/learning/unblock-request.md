# 🚧 Unblock Request

> Last updated: 2026-03-01 11:31 (cycle #120 — timestamp refresh)
> Status: PENDING (awaiting Leo acknowledgment)
> Original block start: 2026-02-27 16:01 (cycle #42)

## Execution-Blocked Duration: ~43 hours

**Blocked since:** Feb 27, 4 PM Taipei → now March 1, 11:31 AM (~43h, ~78 cycles)
**0 experiments run** despite 16 deep reads, 7 paper ideas, 2 paper pitches, 19 gaps documented.

---

## Unblock Steps (~20 min Leo's time)

```bash
# Step 0: Priority 0 pre-experiment (Gap #18 — 5 min)
git clone https://github.com/juice500ml/phonetic-arithmetic /tmp/phonetic-arithmetic
# This is the prerequisite for Paper A (tests phonological geometry through connector)

# Step 1: Create venv (5 min)
python3 -m venv ~/audio-mi-env
source ~/audio-mi-env/bin/activate
pip install nnsight openai-whisper torch pyvene

# Step 2: Get a real speech .wav — ANY option (2 min):
#   A: curl -L "https://github.com/librosa/librosa/raw/main/tests/data/libri1.wav" -o /tmp/test.wav
#   B: Record yourself saying anything 5-10s
#   C: Drop any .wav in workspace/

# Step 3: Run validation (2 min)
python skills/autodidact/scripts/whisper_hook_demo.py /tmp/test.wav
# Expected: CKA clusters 0-2 (acoustic) and 3-5 (semantic), norm jump at layer 3

# Step 4: Approve IIT experiment (yes/no — see experiment-queue.md Priority 1)
# If YES: system is fully unblocked and can start the 3h experiment autonomously
```

---

## What's Ready for Leo (overnight Feb 28 → Mar 1)

### Paper Pitches (both updated to latest)
- 📄 **`memory/learning/paper-a-pitch.md`** v0.2 — "Localizing the Listen Layer in Speech LLMs"
  - Full abstract draft, 4-experiment plan, NeurIPS/Interspeech venue comparison
  - ✅ DAS gc(k) method (theoretically grounded via IIT/pyvene)
  - ✅ Statistical significance protocol (bootstrap 95% CI — cycle #104)
  - ✅ Figure 3 prediction: "lower-triangular stripe" in 2D IIA heatmap (new testable prediction — cycle #104)
  - ✅ Known Risks checklist (5 DAS assumptions, mitigations)
  - 4 open questions for Leo's decision

- 📄 **`memory/learning/paper-b-pitch.md`** — "AudioSAEBench"
  - 5-category evaluation framework + novel `gc(F)` Grounding Sensitivity metric
  - SAELens ecosystem gap confirmed (zero audio SAEs on HuggingFace)

### System Improvements (cycles #50-104)
- 16 system improvements applied during execution-blocked period
- Weekend Protocol rule (no shutdown during arXiv weekend gap)
- All 16 meta-board Qs answered
- experiment-queue.md with priority ranking + unblock checklist

### Also Flag for Leo
- ⚠️ **Delete dead cron job:** `提醒-SL-Weekly-Meeting` — disabled, past, error state
- 📚 **ARENA recommendation:** [1.3.1] Linear Probes + [1.4.2] SAE Circuits before running IIT experiment (1 day investment, saves 6h debugging)
  - Linear Probes Colab: https://colab.research.google.com/github/callummcdougall/arena-pragmatic-interp/blob/main/chapter1_transformer_interp/exercises/part31_linear_probes/1.3.1_Linear_Probes_exercises.ipynb

---

## Priority Queue (ordered)

| # | Action | Time | Who |
|---|--------|------|-----|
| P0 | `git clone phonetic-arithmetic` | 2 min | Leo |
| P1 | Create venv + install libs | 5 min | Leo |
| P2 | Real speech .wav test | 5 min | Leo |
| P3 | Approve IIT experiment | 1 min | Leo |
| P4 | ARENA [1.3.1] Linear Probes | 3-4h | Leo |
| P5 | IIT Whisper-small experiment | ~3h | Autonomous after approval |
| P6 | Contact 智凱哥 re: AudioLens collaboration | 5 min | Leo |
| P7 | Paper A/B review + venue decision | 20 min | Leo |

---
*This file should be relayed to Leo by the main session. Delete or mark RESOLVED after Leo acknowledges.*
