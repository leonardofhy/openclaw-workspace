# Listen Layer Localization — MVP Plan (from GPT-5.2 Pro note)

Source archive:
- `memory/research/2026-02-27-gpt52pro-listen-layer-localization.md`

## Operational claim

Prefer weak/realistic hypothesis over strong one:
- Not necessarily a single "listen layer"
- More likely a **listen range / interface zone** (early alignment + mid fusion + possible late specialization)

## Evidence stance

- Support for localizable ranges: MATA, VOX-KRIKRI, MOSS-Speech, AI-STA
- Counter-signal against single-layer claim: architecture/task dependence, prepend-vs-cross-attn parity

## 3 MVP experiments (single GPU, 3–6h)

1) Layer-wise audio attention suppression curve (inference-time, no training)
- Sweep layer index and suppress text->audio attention.
- Output: `ΔAcc(layer)` or `ΔWER(layer)` sensitivity curve.

2) Activation patching causal tracing (clean vs corrupted audio)
- Patch candidate layers and measure probability/logit recovery.
- Output: recovery peak layer(s), necessity/sufficiency evidence.

3) Layer-restricted LoRA sweep
- Train LoRA only on Early vs Middle vs Late groups.
- Output: which layer group yields most gain per trainable parameter.

## Recommended order

- Run Exp1 for fast coarse localization
- Run Exp2 for stronger causal evidence
- Run Exp3 for trainability/parameter localization validation

## Minimal reporting template

- Model + task + sample count
- Metric baseline / corrupted / intervened
- Best layer(s) or best layer-range
- Failure mode observed
- Next action
