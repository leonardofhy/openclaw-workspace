# UniWhisper Cross-Task gc(k) Consistency Spec

> Q073 | Track T3 | Created: 2026-03-08 | Status: READY FOR LEO REVIEW  
> Tier: 0 (spec only — no GPU, no Whisper needed; mock eval via existing harness)

---

## Research Question

> Does the gc(k) "listen boundary" (the layer at which Whisper stops integrating audio evidence and commits to language prior) stay consistent across fundamentally different tasks — ASR, ST, and QA — or does the task objective shift the boundary?

**Why it matters**: If gc(k) is task-invariant, it reflects a structural property of Whisper's encoder, independent of what the model is "trying to do." This would strengthen Paper A's core claim: the listen-vs-guess boundary is an intrinsic acoustic grounding mechanism, not a task-specific heuristic. If it shifts, we must control for task type in all experiments.

---

## Background: What is gc(k)?

`gc(k)` (grounding-confidence at layer k) measures how much the model's output probability changes when audio-encoder activations at layer k are patched vs. ablated. High gc(k) = model is still using acoustic evidence at layer k. The "listen boundary" is the last layer where gc(k) > threshold (e.g., 0.3).

Prior T3 work established gc(k) for ASR on clean/noisy speech pairs (see `experiment-spec-T3-cpu.md`). This spec extends that to multi-task.

---

## Three-Task Protocol

For each task, we define a **stimulus set** of N=5 samples, each with:
- A clean audio version (acts as "listen" anchor)
- A noise-corrupted/masked version (acts as "guess" probe)

### Task 1: ASR (English → English transcript)
- Stimulus: 5 short English sentences (2-5 words each)
- Model mode: `transcribe` (default Whisper behavior)
- gc(k) measurement: ΔP(correct English token) when patching layer k
- Expected listen boundary: **encoder layer 3–5** (mid-encoder, consistent with T3 prior results)

### Task 2: ST — Speech Translation (Non-English audio → English transcript)
- Stimulus: 5 sentences spoken in French or Mandarin (use synthetic TTS via espeak or mock activations)
- Model mode: `translate` (Whisper's built-in translation task)
- gc(k) measurement: ΔP(correct English translation token) when patching layer k
- Key question: Does cross-lingual demand push the listen boundary **earlier** (less time for acoustic processing before committing to translation) or **later** (more audio grounding needed to disambiguate phonology across languages)?
- Hypothesis: boundary shifts **earlier by 1-2 layers** (ST needs language switch decision sooner)

### Task 3: QA — Instruction-Following ("listen to audio, answer question")
- Stimulus: 5 audio clips + a fixed question (e.g., "What word was repeated most?")
- Model mode: Whisper with custom prompt prefix embedding (inject question as initial decoder tokens)
- gc(k) measurement: ΔP(correct answer token) when patching layer k
- Key question: Does a higher-level semantic task require **deeper audio integration** (later listen boundary)?
- Hypothesis: boundary shifts **later by 1-3 layers** (model needs semantics, not just phonemes)
- Caveat: Whisper-tiny may not generalize to QA well — use mock or MicroGPT surrogate

---

## Expected Divergence Table

| Task | Expected listen boundary (layer) | Direction from ASR baseline | Reason |
|------|----------------------------------|-----------------------------|--------|
| ASR  | Encoder 3–5                      | baseline (0)                | Clean phoneme-to-token mapping |
| ST   | Encoder 2–4                      | −1 to −2 (earlier)          | Language-switch decision needed before semantic decoding |
| QA   | Encoder 4–7                      | +1 to +3 (later)            | Semantic content integration requires deeper acoustic grounding |

**Divergence threshold**: If max shift across tasks > 2 layers, gc(k) is task-sensitive → must control for task in all Paper A experiments. If ≤ 2 layers, gc(k) is approximately task-invariant → report as robustness evidence.

---

## Null Hypothesis

> H0: The gc(k) boundary does not systematically shift across tasks (< 1.5 layer mean difference).

Falsification criterion: Any pairwise task comparison with |Δboundary| ≥ 2 layers (p < 0.05 across N=5 samples) rejects H0.

---

## Mock Execution Plan (Tier 0 — No GPU)

Use existing `gc_eval.py --mock` harness. Inject synthetic activation patterns that simulate task-specific decoder priming:

```bash
# ASR baseline (already exists from Q005 results)
python3 skills/autodidact/scripts/gc_eval.py --mock --task asr

# ST surrogate: prime decoder with "translation" token embedding (shift cross-attention by +0.2)
python3 skills/autodidact/scripts/gc_eval.py --mock --task st --decoder-prime translation

# QA surrogate: prime decoder with "question" token embedding (shift cross-attention by +0.4)  
python3 skills/autodidact/scripts/gc_eval.py --mock --task qa --decoder-prime question
```

**Required gc_eval.py changes** (Tier 0 build — next cycle):
1. Add `--task {asr,st,qa}` flag
2. Add `--decoder-prime {none,translation,question}` flag — shifts decoder initial hidden state by a synthetic offset to simulate task conditioning
3. Output: per-task gc(k) curves + boundary summary table

---

## Paper A Implication

If H0 is supported (task-invariant gc(k)):
→ Add as Section 4.3 "Task Robustness of gc(k)" — strong claim for generalization.

If H0 is rejected (task-sensitive gc(k)):
→ Reframe: gc(k) is a *task-conditioned* grounding measure. Add task as a covariate in all experiments. Could be a richer finding: "the model allocates audio grounding budget dynamically based on task."

Either outcome is publishable. The divergence table is the key artifact.

---

## Definition of Done

- [x] Spec written (this file)
- [ ] gc_eval.py updated with `--task` and `--decoder-prime` flags
- [ ] Mock runs for all 3 tasks → divergence table filled in with actual numbers
- [ ] Q073 marked complete; next task (gc_eval update) queued as Q074 (Tier 1 build)

---

*Spec by autodidact cycle c-20260308-1045 | Estimated Tier 1 execution time: ~3 min CPU*
