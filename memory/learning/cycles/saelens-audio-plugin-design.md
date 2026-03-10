# SAELens Audio Plugin Design
**Task:** Q061 | **Track:** T2 | **Tier:** 0 (design doc)
**Date:** 2026-03-10 | **Gap:** #19 (no SAELens support for audio encoders)

---

## Research Motivation

SAELens (EleutherAI) is the leading open-source SAE training library — but it only
ships with text LM hooks (GPT-2, Pythia, Llama, Gemma). No audio encoder support.

**Gap #19:** Nobody has trained SAEs on Whisper or HuBERT residual-stream activations
using a well-maintained, reproducible framework. Our existing `sae_listen_layer.py`
(MicroGPT toy) proves the concept works. SAELens integration = reproducibility + community
visibility + Paper B benchmark substrate.

**Why this matters for the thesis:**
- gc(k) tells us *where* (the listen layer)
- SAE tells us *what features* are there
- SAELens audio plugin = the bridge between behavioral localization and mechanistic understanding

---

## 3-File Implementation Plan

### File 1: `audio_model_hook.py` (~120 LOC)
**Purpose:** Model wrapper that makes Whisper/HuBERT look like a SAELens-compatible
`HookedModel`. SAELens expects a `run_with_cache(tokens)` interface.

**Key design decisions:**

```python
class WhisperHookedEncoder:
    """
    Wraps openai/whisper-small (or HuBERT) to expose:
      - run_with_cache(mel_input) → (logits, cache)
      - cache: Dict[str, torch.Tensor]  # "hook_resid_post.{layer}" keys
    """
    HOOK_POINTS = [f"hook_resid_post.{L}" for L in range(n_layers)]
    
    def forward_with_hooks(self, mel: Tensor) -> Dict[str, Tensor]:
        activations = {}
        handles = []
        for name, layer in self._get_layer_modules():
            h = layer.register_forward_hook(
                lambda m, i, o, n=name: activations.__setitem__(n, o)
            )
            handles.append(h)
        out = self.model(mel)
        [h.remove() for h in handles]
        return out, activations
```

**What it hooks:** Encoder residual stream post-LayerNorm (matching SAELens convention
for text models: `hook_resid_post` after each transformer block).

**Whisper-specific:** Mel spectrogram input (80 bins × T frames). The hook captures
post-block residuals of shape `(batch, T_frames, d_model)` — we pool over T_frames
(mean-pool) to get `(batch, d_model)` per sample for SAE training.

**HuBERT variant:** Same structure; swaps mel→waveform input and Whisper encoder→HuBERT
encoder. Parametrize via `model_type: Literal["whisper", "hubert"]`.

**LOC breakdown:** ~40 WhisperHookedEncoder, ~40 HuBERT variant, ~20 pooling utils, ~20 tests.

---

### File 2: `audio_sae_trainer.py` (~150 LOC)
**Purpose:** Configuration + activation dataset builder that feeds into SAELens' existing
`SparseAutoencoder.train()` loop. Doesn't re-implement training — just plumbs our audio
activations into SAELens' standard pipeline.

**Key design decisions:**

```python
class AudioActivationDataset(IterableDataset):
    """
    Streams activations from audio model hook → SAELens training buffer.
    Each sample: pooled residual at hook_point L for one audio clip.
    
    Input: list of .wav files (or TTS-generated clips)
    Output: torch.Tensor of shape (N, d_model)
    """
    def __init__(self, wav_files, model_hook, hook_layer, device="cpu"):
        ...

    def __iter__(self):
        for wav in self.wav_files:
            mel = load_mel(wav)           # Whisper mel extraction
            _, cache = self.model_hook.run_with_cache(mel)
            act = cache[f"hook_resid_post.{self.hook_layer}"]
            yield pool_frames(act)        # (1, d_model)
```

**SAELens integration point:**
```python
# SAELens expects this interface:
from sae_lens import SparseAutoencoder, LanguageModelSAERunnerConfig

cfg = LanguageModelSAERunnerConfig(
    model_name="whisper-small",         # custom name
    hook_name="hook_resid_post.18",     # gc(k) listen-layer peak
    hook_layer=18,
    d_in=512,                           # Whisper-small d_model
    expansion_factor=8,                 # d_sae = 4096
    ...
)
# We provide a custom ActivationStore subclass
```

**Why not retrain SAELens from scratch?** SAELens already has: TopK/ReLU loss variants,
wandb logging, checkpointing, feature analysis (DFA/EAP). We add audio = 3 files not 300.

**LOC breakdown:** ~60 AudioActivationDataset, ~50 SAELensAudioConfig, ~40 CLI.

---

### File 3: `audio_sae_probe.py` (~100 LOC)
**Purpose:** Post-training analysis — correlate learned SAE features with gc(k) signal
(the "listen-layer feature identification" step for Paper B Figure 1).

**Protocol:**
1. Load trained SAE checkpoint + audio hook
2. Run N audio clips through model → collect (activations, gc_score) pairs
   - gc_score from `gc_eval.py` (already built) 
3. For each SAE feature dimension i, compute:
   - `corr[i] = pearson(feature_activations[:, i], gc_scores[:])`
4. Report top-k features by |corr|
5. Decode feature i's direction: `W_dec[:, i]` → project onto PCA components of
   residual stream → semantic label attempt

**Output:** `saelens-audio-probe-results.json` with:
```json
{
  "model": "whisper-small",
  "hook_layer": 18,
  "top_gc_features": [
    {"feature_idx": 341, "gc_corr": 0.71, "activation_rate": 0.23, "label": "?"},
    ...
  ],
  "bottom_gc_features": [...],
  "total_features": 4096,
  "n_samples": 2000
}
```

**LOC breakdown:** ~50 feature correlation engine, ~30 decoder projection, ~20 CLI.

---

## SAELens PR Scope

What changes to SAELens upstream (if we PR):

| Component | Change | LOC |
|-----------|--------|-----|
| `pretrained_model_config.py` | Add WhisperConfig + HuBERTConfig | ~30 |
| `activation_store.py` | AudioActivationStore subclass | ~80 |
| `README.md` | Audio encoder usage section | ~20 |
| Tests | audio_hook tests | ~40 |

**Total PR scope:** ~170 LOC + tests. Feasible as a self-contained PR.
Not changing training loop, loss, or analysis code.

---

## Test Plan

### Unit tests (Tier 0 — mock tensors, no model download):
```python
def test_whisper_hook_shape():
    mock_mel = torch.randn(1, 80, 3000)  # standard Whisper input
    hook = WhisperHookedEncoder.__new__(WhisperHookedEncoder)
    # inject mock residuals
    cache = {"hook_resid_post.18": torch.randn(1, 150, 512)}
    pooled = pool_frames(cache["hook_resid_post.18"])
    assert pooled.shape == (1, 512)

def test_activation_dataset_yields():
    ds = AudioActivationDataset(mock_wav_files, mock_hook, layer=18)
    batch = next(iter(ds))
    assert batch.shape[-1] == 512  # d_model for whisper-small
```

### Integration test (Tier 1 — CPU, <5 min):
- Use `synthetic_stimuli.py` (already built) to generate 200 synthetic audio clips
- Run `audio_sae_trainer.py` with d_sae=64, 50 epochs on CPU → SAE trains without crash
- Run `audio_sae_probe.py` → top-3 gc-correlated features identified

### System test (Tier 2 — needs Leo approval):
- Real Whisper-small + real speech .wav files (LibriSpeech subset)
- d_sae=4096, 500 epochs → publishable SAE checkpoint

---

## ~LOC Estimate Summary

| File | Est. LOC | Status |
|------|----------|--------|
| `audio_model_hook.py` | ~120 | Not started |
| `audio_sae_trainer.py` | ~150 | Not started |
| `audio_sae_probe.py` | ~100 | Partial (logic exists in sae_listen_layer.py) |
| **Total plugin** | **~370** | |
| SAELens PR diff | ~170 | After plugin validated |

**Existing reusable code:**
- `gc_eval.py` → gc(k) scores (Step 3 of probe)
- `synthetic_stimuli.py` → audio clips for Tier 1 test
- `sae_listen_layer.py` → SAE training logic (port core math to trainer)
- `whisper_hook_demo.py` → hook architecture pattern

---

## Open Questions for Leo

1. **Which layer to hook?** gc(k) peak at ~layer 18/32 for Whisper-small — but do we
   train SAE on ONE layer (listen layer) or all layers (memory expensive)?
   → Recommendation: one layer (18) first, sweep later.

2. **Expansion factor?** SAELens default = 8× (d_sae = 4096 for Whisper-small 512).
   Smaller models (MicroGPT) need smaller SAE (8× still fine for d_model=128, d_sae=1024).

3. **PR vs standalone?** Option A: upstream SAELens PR (visibility, maintenance burden).
   Option B: standalone `skills/autodidact/scripts/saelens_audio/` package (faster, private).
   → Recommendation: prototype standalone, PR when Paper B is accepted.

---

## Connection to Paper B (AudioSAEBench)

This plugin IS the infrastructure for Paper B:
- Audio-RAVEL Category 0 benchmark needs SAE features at listen layer
- TCS-F (Transcript-Causal Stability Fraction) needs SAE feature isolation per token
- Without SAELens audio support, AudioSAEBench benchmarks only text LLM SAEs

**Priority:** Once Tier 1 test passes, we have the substrate for all 4 Paper B benchmark
categories. Unblocks Q063 (Audio-RAVEL stimuli plan) as a downstream consumer.

---

*Generated: 2026-03-10 by Little Leo (autodidact cycle c-20260310-2201)*
*Next: Implement `audio_model_hook.py` Tier 0 scaffold (Q→new task)*
