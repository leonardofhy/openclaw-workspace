# 🔧 TransformerLens + pyvene Cheat Sheet
> For mechanistic interpretability experiments on Whisper / audio-LLMs
> Created: 2026-02-26 (Cycle #9 skill-up)

---

## TransformerLens

### What it does
- Load GPT-2 style LMs (decoder-only), expose **all internal activations**
- Cache any activation, **hook** to edit/replace/read mid-forward
- Core class: `HookedTransformer`
- Limitation: built for decoder-only LMs (GPT-2, Llama, etc.) — does NOT natively support encoder-only models like Whisper

### Install
```bash
pip install transformer_lens circuitsvis
```

### Core API Pattern
```python
import transformer_lens.utils as utils
from transformer_lens import HookedTransformer

# Load model
model = HookedTransformer.from_pretrained("gpt2")

# Forward + cache ALL activations
tokens = model.to_tokens("Hello world")
logits, cache = model.run_with_cache(tokens)

# Access any activation (e.g., residual stream at layer 3)
resid_mid = cache["resid_post", 3]   # shape: [batch, seq, d_model]
attn_out = cache["attn_out", 3]      # attention output at layer 3

# Hook names convention
# "resid_pre", "resid_mid", "resid_post" — residual stream
# "attn_out", "mlp_out"
# "hook_q", "hook_k", "hook_v" — within attention
# Full list: utils.get_act_name("resid_post", 3)
```

### Hook-based Intervention (Activation Patching)
```python
def patch_hook(value, hook, new_value):
    return new_value  # replace activation with stored value

# Run clean first, store activations
_, clean_cache = model.run_with_cache(clean_tokens)
target_activation = clean_cache["resid_post", layer_idx]

# Run corrupted with patch from clean
patched_logits = model.run_with_hooks(
    corrupted_tokens,
    fwd_hooks=[(utils.get_act_name("resid_post", layer_idx),
                partial(patch_hook, new_value=target_activation))]
)
```

### logit_lens (Decoder Only)
```python
# Project residual stream at each layer through unembed
# → "what would model output be if it stopped here?"
def logit_lens(cache, layer_idx):
    resid = cache["resid_post", layer_idx]   # [batch, seq, d_model]
    logits = model.unembed(model.ln_final(resid))
    return logits
```

### For Audio/Speech Models (Workaround)
TransformerLens does NOT support Whisper natively. Options:
1. **Manual hooks** — use HuggingFace `.register_forward_hook()` on each layer (lower-level but works)
2. **AudioLens pattern** — directly patch HuggingFace Whisper using custom forward functions
3. **pyvene** (preferred for patching) — model-agnostic, works on any PyTorch model including Whisper/HuBERT

---

## pyvene

### What it does
- **Model-agnostic** activation patching/intervention on **any PyTorch model**
- Key concept: `Intervention` objects = serializable dicts → shareable via HuggingFace
- Works on: encoder-only (Whisper, HuBERT), decoder-only (GPT), seq2seq (T5), CNNs, etc.
- Supports: causal patching, distributed alignment search (DAS), linear representations

### Install
```bash
pip install pyvene
```

### Core API Pattern
```python
import pyvene as pv

# 1. Wrap any PyTorch model
intervenable_config = pv.IntervenableConfig(
    representations=[{
        "layer": 3,
        "component": "block_output",  # or "head_attention_value_output"
        "intervention_type": pv.VanillaIntervention
    }]
)
intervenable_model = pv.IntervenableModel(intervenable_config, model)

# 2. Run with intervention (patch base -> source)
# base = corrupted input, source = clean input
_, output = intervenable_model(
    base={"input_ids": corrupted_tokens},
    sources=[{"input_ids": clean_tokens}],
    unit_locations={"sources->base": (None, [[0, 1, 2]])}  # token positions
)
```

### Activation Patching for Audio (Whisper)
```python
import pyvene as pv
from transformers import WhisperModel

whisper = WhisperModel.from_pretrained("openai/whisper-base")

# Wrap encoder
config = pv.IntervenableConfig(
    representations=[{
        "layer": 6,
        "component": "block_output",
        "intervention_type": pv.VanillaIntervention
    }]
)
iv_model = pv.IntervenableModel(config, whisper.encoder)

# base = corrupted audio, source = clean audio
_, patched_output = iv_model(
    base={"input_features": corrupted_features},
    sources=[{"input_features": clean_features}],
    unit_locations={"sources->base": (None, None)}  # all positions
)
```

### Distributed Alignment Search (DAS)
- Find **which subspace** of activations encodes a concept
- Useful for: locating where "phoneme X" / "speaker gender" / "hallucination signal" lives
- Algorithm: learn rotation matrix R such that R @ activation → interpretable direction
```python
intervention_type = pv.RotatedSpaceIntervention  # DAS intervention
# Train with gradients enabled — find causal subspace
```

---

## Whisper Hook Strategy (Manual HuggingFace)

For quick experiments without pyvene:
```python
from transformers import WhisperModel
import torch

whisper = WhisperModel.from_pretrained("openai/whisper-base")

# Store activation cache
cache = {}
def make_hook(layer_idx):
    def hook(module, input, output):
        cache[f"encoder_layer_{layer_idx}"] = output[0].detach()  # [batch, time, d_model]
    return hook

# Register hooks on all encoder layers
for i, layer in enumerate(whisper.encoder.layers):
    layer.register_forward_hook(make_hook(i))

# Run forward
with torch.no_grad():
    out = whisper.encoder(input_features=audio_features)

# Access layer activations
layer6_acts = cache["encoder_layer_6"]  # shape: [1, T, 512] for whisper-base
```

---

## MacBook-Feasible Models

| Model | Params | RAM | Notes |
|-------|--------|-----|-------|
| Whisper-tiny | 39M | ~200MB | Fast, for prototyping |
| Whisper-base | 74M | ~400MB | Good balance |
| Whisper-small | 244M | ~1.2GB | Full English quality |
| GPT-2 (text) | 117M | ~600MB | For TransformerLens practice |
| HuBERT-base | 94M | ~500MB | Good for SSL speech MI |

---

## Recommended First Experiments (ordered by difficulty)

1. **[Text first] IOI on GPT-2** — run TransformerLens IOI demo notebook → verify patching logic
2. **[Audio] Whisper encoder cache** — extract all 12 layer activations on same audio → plot CKA
3. **[Audio] Probe for phoneme/gender** — linear probe on layer 6 vs layer 25 (replicate Beyond Transcription)
4. **[Audio] Manual patching** — clean vs. corrupted audio → patch layer 6 → measure WER change
5. **[Audio] pyvene on Whisper** — systematic layer-wise patching → generate patching curves

---

## Key Resources

| Resource | Link | Priority |
|----------|------|----------|
| TransformerLens main demo | https://github.com/TransformerLensOrg/TransformerLens/tree/main/demos | **Start here** |
| Callum's TL tutorial | https://transformerlens-intro.streamlit.app | Structured intro |
| pyvene tutorials | https://github.com/stanfordnlp/pyvene/tree/main/tutorials | pv basics |
| Activation patching tutorial | https://colab.research.google.com/drive/1hhd9LIl2Xo55rQEsmHrCT4n-GDHxnMuY | Neel Nanda |
| AudioSAE code | https://github.com/audiosae/audiosae_demo | Speech SAE reference |
| AudioLens code | https://github.com/ckyang1124/AudioLens | Track 3 reference |

---

## Gotchas & Pitfalls

- **TransformerLens = decoder-only only** → use pyvene for encoder (Whisper, HuBERT)
- **Patching OOD states**: patching activations from clean→corrupted can create out-of-distribution residuals (especially large magnitude patches). Use caution.
- **Whisper hook output**: `layer.register_forward_hook` receives `output[0]` (tensor) not full tuple — check shape
- **Batch size = 1** for audio: most Whisper inference is single-sample. Broadcasting clean→batch may fail.
- **TransformerLens `torch.set_grad_enabled(False)`** by default — remember to re-enable if you want DAS training
- **pyvene unit_locations**: `None` = all positions; `(src, base)` tuple for position-specific matching

---

## Next Steps After This Cheat Sheet

1. Run `pip install transformer_lens` + sanity test on GPT-2 (text) → feel the API
2. Run Whisper-base on a sample audio → verify hook captures layer 6 activations
3. Add `skills/autodidact/scripts/whisper_hook_demo.py` (starter script)
