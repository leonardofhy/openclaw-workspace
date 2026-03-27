# MATS Research Task Proposal v1
## "Listen-Layer Audit for Audio Jailbreak Detection & Emergent Misalignment Screening"

> Version: 1.0 | Created: 2026-03-24 | Track: T5
> Status: **Ready for Leo review / MATS submission**

---

## One-Sentence Pitch

We use causal mechanistic interpretability to locate the **Listen Layer** in speech LLMs — the narrow band of layers where audio representations are causally decisive for model behavior — and show that its grounding coefficient anomaly (gc-anomaly) serves as a **zero-shot, attack-agnostic jailbreak detector** evaluated on JALMBench (246 queries), while the baseline gc(k) profile functions as a **pre-deployment risk screen for audio emergent misalignment**.

---

## Motivation

Audio-language models (ALMs) face jailbreak attacks that bypass text-level safety filters: prosodic command injection, multimodal conflict attacks, and adversarial audio perturbations. Current defenses (SALMONN-Guard, SPIRIT, ALMGuard) classify *outputs* or *surface-level attention patterns*; **none exploit the model's own internal audio-processing structure as a safety signal**, and none are evaluated on a shared benchmark, making comparison impossible.

A parallel threat is audio emergent misalignment (EM): ALMs fine-tuned on narrow domains can develop safety failures in acoustic modalities. Betley et al. 2025 established this for text EM; audio EM is unstudied. We believe models that "guess" (low audio grounding) are disproportionately vulnerable to fine-tune-induced audio EM.

---

## Core Insight

Paper A established: there exists a **Listen Layer** — a peak in the grounding coefficient gc(L) — where audio representations causally determine model behavior.

**Hypothesis 1 (Jailbreak):** Under audio jailbreaks, the Listen Layer gc(L) pattern becomes detectably abnormal:
- *Legitimate query*: gc(L) peaks sharply at L\*, then decays (model consulted audio, returned to text processing)
- *Jailbreak query*: gc(L) suppressed, shifted, or anomalously coupled cross-layer

**Hypothesis 2 (EM Risk):** Models with low baseline gc(k) ("guessers") encode shallow acoustic representations at safety-critical layers, making them more susceptible to fine-tune-induced audio EM — measurable *before* fine-tuning via a single inference-time audit.

**Key adversarial robustness argument:** An attacker evading gc(L) detection must craft audio that *preserves normal causal audio processing* while achieving the jailbreak — conflicting objectives make evasion structurally hard.

---

## Method

### Use-Case 1: Inference-Time Jailbreak Detector

| Task | Description | Tier | Output |
|------|-------------|------|--------|
| T1 | gc(L) baseline taxonomy on JALMBench benign queries | 0 | Shape taxonomy (sharp/diffuse/suppressed) |
| T2 | Safety probe direction (MMProbe diff-of-means at L\*) | 0 | Linear safety direction + probe accuracy |
| T3 | gc-anomaly score = KL-div(gc(L|x), gc(L|baseline)); JALMBench ROC | 0 | ROC stratified by 5 attack paradigms |
| T4 | Per-paradigm F1 vs. SALMONN-Guard / SPIRIT / ALMGuard | 0 | Comparison table |

### Use-Case 2: Pre-Deployment EM Risk Screen

| Task | Description | Tier | Output |
|------|-------------|------|--------|
| T5 | gc(k) risk stratification across model checkpoints | 0 | "High listener" vs. "low listener" tier labels |
| T6 | LoRA fine-tune susceptibility: high-gc vs. low-gc checkpoint, OOD benign domain | 1/2 | EM delta: safety degradation comparison |

**All Tasks T1–T5 are CPU-only.** T6 requires GPU for full validation; a CPU mock is sufficient for MATS proposal stage.

### Anti-Confound Checklist (10 items)
Acoustic baseline controls (ACB-1/2/3), speaker identity controls (SID-1/2), text-only ablations (TOA-1/2), prompt injection controls (PIC-1/2/3). All 10 must pass before any result enters the deliverable.

---

## Expected Results

- gc-anomaly ROC achieves **F1 ≥ 0.75 on JALMBench** total; specifically outperforms all baselines on prosodic manipulation and multimodal-conflict paradigms (predicted: +10–20% F1 vs. SPIRIT on those paradigms)
- Low-gc(k) models show **≥20% higher safety degradation** post narrow fine-tune vs. high-gc(k) models (Task T6 CPU mock already coded: `audio_jailbreak_andfrac_mock.py`)
- gc-anomaly does **not fire** on silence, pink noise, or clean benign queries (ACB-1 confirms < 0.05 anomaly score)

---

## Timeline

| Week | Deliverable |
|------|-------------|
| W1 | Task T1: gc(L) baseline taxonomy (JALMBench benign, `listen_layer_audit.py`) |
| W1 | Task T2: safety probe direction at L\* (MMProbe) |
| W2 | Task T3: gc-anomaly score + JALMBench ROC curve |
| W2 | Task T4: comparison table (F1 per paradigm vs. baselines) |
| W3 | Task T5: gc(k) risk stratification across Whisper checkpoints |
| W3 | Task T6 (CPU mock): LoRA susceptibility delta (high-gc vs. low-gc) |
| W4 | Final 6-page MATS technical report |

---

## Why MATS

| Criterion | ✅ |
|-----------|---|
| Safety relevance | Audio jailbreaks = underexplored; detection is mechanistic, not heuristic |
| Mechanistic interpretability | gc(L) is a causal quantity; Listen Layer = core MI methodology |
| Tractable | CPU-feasible MVP; defined deliverables + timeline |
| Novel niche | First work using model-internal mechanisms as safety signal for audio attacks |
| Reproducible | JALMBench provides standardized benchmark → direct F1 comparison to prior work |
| Zero-shot | Calibrated on benign data only; no labeled attack examples needed |
| Dual-use | One audit tool: inference-time detector + pre-deployment EM risk screen |

---

## Open Questions for Leo

1. **MATS track**: MI track or AI safety track — which to lead with?
2. **Prototype model**: Prototype on Whisper-base (CPU) + extrapolate to Qwen2-Audio, or await GPU?
3. **Submission format**: Full research task proposal vs. short pitch (≤1 page)?
4. **Framing**: Standalone MATS project vs. extension of Paper A?
5. **Task T6**: Stage as Tier 1 CPU mock for MATS, flag GPU scale-up as future work?

---

## Relationship to Research Agenda

```
Paper A (Listen vs. Guess — gc framework)
  └─→ Paper C / MATS (this proposal)
        ├─→ Use-Case 1: gc(L) anomaly = inference-time jailbreak detector
        └─→ Use-Case 2: gc(k) baseline = pre-deployment EM risk screen
  └─→ Paper B (AudioSAEBench — feature-level gc attribution)
```

*Full methodology, anti-confound checklist protocol, policy hook (compute-threshold gc(k) mandate), and prior work table: `mats-proposal-draft.md`*
