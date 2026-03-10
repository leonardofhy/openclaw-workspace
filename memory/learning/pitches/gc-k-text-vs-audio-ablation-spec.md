# Ablation Spec: gc(k) Text-vs-Audio Modality Test

> Q050 | Track T3 | Created: 2026-03-06 | Status: READY → done

## Hypothesis

**gc(k) confidence collapse is audio-specific** — it arises because audio models must "listen" (ground predictions in acoustic signal) rather than "guess" (rely on text prior). If true:
- Audio inputs: gc(k) curve drops at the listen-layer boundary when grounding is disrupted
- Identical-content text inputs: gc(k) stays flat (no acoustic grounding to lose)

This would prove the collapse is not a general LLM phenomenon but an **audio modality property** — the core causal claim of Paper A.

---

## Experimental Design

### Stimulus Pairs (N=10 pairs)
For each pair, same semantic content, two modalities:
1. **Audio version**: synthetic speech (TTS or existing fixture from `synthetic_stimuli.py`)
2. **Text version**: transcript string, passed as text token sequence to the same model

**Conflict condition** (the key test): Provide audio that says X but text says Y.
- Audio-conflict: audio says "the cat sat" but transcript/prior says "the dog barked"
- Text-only: no audio input — pure text tokens
- Audio-only: standard audio with blank/dummy text prior

### Model
- **Primary**: MicroGPT (transparent, autograd activations) — already validated in `microgpt_gc_eval.py`
- **Surrogate audio signal**: inject synthetic activation pattern at audio-encoder position

### gc(k) Measurement
For each input condition, compute gc(k) at every layer k:
```
gc(k) = confidence_if_audio_encoder_present[k] - confidence_if_audio_encoder_ablated[k]
```
Ablation: zero out or mean-substitute the audio encoder output at layer k.

### Expected Divergence Pattern

| Condition | Expected gc(k) shape |
|-----------|---------------------|
| Audio (normal) | Peaks at listen-layer (L_listen), drops after |
| Audio (conflict) | Collapse at L_listen (≥20% drop vs normal) |
| Text-only | Flat near zero — no audio grounding contribution |
| Audio + matched transcript | Near-normal, slight smoothing |

**What it proves**: If text-only shows flat gc(k) while audio-conflict shows collapse → collapse is causal to audio grounding, not text statistics.

---

## Implementation Plan (Tier 0/1, CPU)

### Files to create/extend
1. **`skills/autodidact/scripts/text_vs_audio_ablation.py`**
   - Load/generate 10 stimulus pairs
   - Compute gc(k) for each condition using `microgpt_gc_eval.py` hooks
   - Output: JSON with per-condition curves + divergence delta
2. **`skills/autodidact/scripts/plot_ablation_ascii.py`**
   - Render ASCII comparison plot: audio vs text-only gc(k) curves side-by-side
3. **Test**: unit test passes if `mean(gc_audio_conflict) - mean(gc_text_only) > 0.15` on synthetic data

### Runtime
- Tier 1 (CPU, <5 min) — no Leo approval needed
- Builds on: `microgpt_gc_eval.py`, `synthetic_stimuli.py`, `gc_eval.py`

---

## Success Criteria

- [ ] 10 stimulus pairs generated (audio + text versions)
- [ ] gc(k) curves computed for all 4 conditions
- [ ] Divergence confirmed: audio-conflict collapse is ≥15pp larger than text-only
- [ ] ASCII plot generated and saved to `memory/learning/pitches/figure-ablation-draft.md`
- [ ] Unit test passes

---

## Connection to Paper A

This ablation is **Table 1 / Figure 3 material** — the modality-control experiment that rules out "gc(k) collapse = general LLM uncertainty" alternative hypothesis. Without this, reviewers will ask "how do you know it's the audio?".

Direct connection to T3 DoD: "experiment spec reviewed by Leo" — this spec should be surfaced to Leo for sign-off before Tier 1 run.

---

## Open Questions
- Should we test on a real Whisper tiny (CPU-safe) instead of MicroGPT for ecological validity?
- At what divergence threshold (Δgc) should we declare "audio-specific"? 0.15 is provisional.
- Confound: text tokenization changes seq length vs audio — need to control for that.
