# MicroGPT Audio Testbed: gc(k) + Jailbreak on Minimal Model

> Task: Q063 | Track: T3 | Status: Tier 0 design doc | Created: 2026-03-07

## Motivation

Whisper-small has ~244M parameters and requires real speech .wav data (currently blocked). A minimal trainable model allows:
1. **Full observability** — we control weights and training dynamics
2. **CPU-feasibility** — train + probe in <30 min on CPU
3. **Ground-truth causal structure** — we can plant known circuits and verify gc(k) finds them
4. **Jailbreak testing** — inject adversarial acoustic tokens in a controlled corpus

This is a **falsification-first** testbed: if gc(k) can't localize listen-layers in a model where we know the answer, the method is broken.

---

## Architecture Spec

### Model: MicroGPT-Audio

| Component | Spec | Rationale |
|-----------|------|-----------|
| Architecture | GPT-2-style transformer (decoder only) | Simple, well-understood |
| Vocab | 512 discrete acoustic tokens | Representable by a small codebook |
| Layers | 4 transformer blocks | gc(k) boundary should appear in layers 1-2 |
| Heads | 4 attention heads | Enough for polyphonic features |
| d_model | 128 | CPU-trainable (<30 min) |
| Parameters | ~2M | Fast iteration |
| Input | Sequence of discrete acoustic tokens (mel-bin quantized) | Avoids raw audio pipeline |
| Output | Next-token prediction (acoustic LM) | Enables Listen-Layer localization |

### Acoustic Tokenizer (Tier 0 simulation)

- **No real audio needed**: simulate tokens via mel-filterbank buckets (log-mel → argmax per frame → integer token)
- Synthetic corpus: generate tones, noise, simple phoneme-like patterns via `scipy.signal`
- Two token classes: "safe" (periodic tones) and "adversarial" (high-frequency noise bursts mimicking jailbreak acoustic signatures)
- Vocabulary split: tokens 0-399 = safe, 400-511 = adversarial (known ground truth)

---

## Corpus Design

| Split | Size | Content |
|-------|------|---------|
| Train | 10,000 sequences × 64 tokens | 90% safe, 10% adversarial |
| Validation | 1,000 sequences | Balanced 50/50 |
| Jailbreak probe | 200 sequences | Adversarial-only with known injection points |

**Generation**: `scipy.signal.chirp` for safe patterns; Gaussian noise bursts for adversarial. All CPU-generated in <1 min.

---

## gc(k) Expected Behavior

Based on the Listen-Layer hypothesis (layers 1-2 integrate acoustic evidence before committing to linguistic representation):

| Layer | Expected gc(k) Signal | Interpretation |
|-------|-----------------------|----------------|
| 0 (embed) | ~0.0 | No integration yet |
| 1 | 0.3–0.6 | Early acoustic binding — **predicted listen-layer** |
| 2 | 0.5–0.8 | Peak integration, safe/adversarial divergence |
| 3 (final) | ~0.2 | Post-decision; residual stream already committed |

**Falsification criterion**: if gc(k) is flat across layers (variance <0.05), the metric is uninformative → method fails on controlled testbed.

**Success criterion**: gc(k) peak at layer 1-2, AND safe/adversarial token sequences produce statistically different gc(k) profiles at the peak layer (Cohen's d > 0.5).

---

## Feasibility Table: MicroGPT vs Whisper

| Dimension | MicroGPT-Audio | Whisper-small |
|-----------|----------------|---------------|
| Parameters | ~2M | 244M |
| Train from scratch | ✅ Yes (<30 min CPU) | ❌ No (pretrained only) |
| Real audio required | ❌ No (synthetic) | ✅ Yes (.wav blocked) |
| gc(k) harness | ✅ Plug in directly | ✅ Already scaffolded |
| Ground-truth circuits | ✅ Plantable | ❌ Unknown |
| Jailbreak injection control | ✅ Full | ⚠️ Approximate |
| Transfer to real model | ❌ Not direct | ✅ Yes |
| Suitable for pre-registration | ✅ Ideal (known answer) | ✅ Yes (but blocked) |

**Verdict**: MicroGPT testbed is the right CPU-only entry point. It provides falsification-first validation of gc(k) without real audio. Whisper experiments remain the target for execute phase.

---

## Implementation Plan (Tier 0 → Tier 1)

### Tier 0 (this doc — no code runs)
- [x] Architecture spec
- [x] Corpus design
- [x] Expected gc(k) behavior
- [x] Feasibility table

### Tier 1 (next — CPU, <5 min)
- [ ] `skills/autodidact/scripts/microgpt_train.py`: train 2M param model on synthetic corpus
- [ ] Plug into existing `unified_eval.py` + `integration_test.py` pipeline
- [ ] Run gc(k) probe, plot layer profiles, check falsification criteria

### Tier 2 (Leo approval)
- [ ] Train with larger corpus (100k sequences)
- [ ] Plant known circuits (forced attention patterns) to validate gc(k) localization

---

## Open Questions

1. Should the acoustic tokenizer use log-mel buckets or a learned VQ-VAE codebook? (VQ-VAE = better, but out of scope for Tier 0)
2. Is 4 layers enough to see a clear listen-layer boundary, or do we need 6?
3. How do we define "adversarial" tokens in a way that transfers to real jailbreak audio signatures?

---

## Connection to Tracks

- **T3 (Paper A)**: This testbed is the CPU-feasible entry point for the gc(k) eval harness before Whisper real-speech unblocks
- **T5 (Paper C / MATS)**: Adversarial token injection maps directly to audio jailbreak threat model in Q062 incrimination design

**Next action**: Implement `microgpt_train.py` (Tier 1 build) → validate falsification criterion → unblock T3 eval harness.
