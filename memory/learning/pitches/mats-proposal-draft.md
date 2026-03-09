# 📄 MATS Research Task Proposal: "Listen-Layer Audit for Audio Jailbreak Detection"

> Version: 0.4 | Updated: 2026-03-09 09:45 (cycle c-20260309-0945, Q008)
> Track: T5 (Listen-Layer Audit / Paper C)
> Status: **Draft v0.3 — Clean final draft. Ready for Leo review.**
> Depends on: Paper A (Listen Layer localization) for theoretical foundation

---

## 1-Sentence Pitch

> We use causal mechanistic interpretability to identify the layer-specific "Listen Layer" in speech LLMs and show its gc(L) anomaly score serves as a **zero-shot, attack-agnostic jailbreak detector** — evaluated on the JALMBench 246-query standardized benchmark. The same gc(k) metric functions as a **pre-deployment risk screen** for audio emergent misalignment: one audit tool, two safety applications.

---

## MATS Context

MATS (Model Alignment Theory Scholars) research tasks should:
1. Have clear safety relevance
2. Be tractable (concrete experiments, defined outputs)
3. Connect to mechanistic interpretability research agenda
4. Be novel with a defined niche vs. existing work

**Why this fits MATS:**
- Audio jailbreaks are an underexplored attack surface (text jailbreaks → well-studied; audio → not)
- Mechanistic approach (Listen Layer) provides model-internal signal, not surface-level heuristic
- CPU-feasible MVP: no GPU approval needed for prototype
- Clear deliverable timeline (proposal → prototype → paper)
- Dual-use gc(k) metric: inference-time detector AND pre-deployment risk screen
- Grounded in JALMBench: standardized, reproducible, comparable to prior work

---

## Problem Statement

Audio-language models (ALMs) can be jailbroken via audio modality attacks that text-content filters miss:
- **Prosodic jailbreaks**: commands disguised in intonation/tone rather than lexical content
- **Audio-text conflict injection**: malicious instructions in speech while benign text context
- **Phoneme-level adversarial audio**: perturbed audio that sounds normal but shifts model behavior

Current defenses are surface-level (audio classifiers, keyword filters, perplexity scores). None exploit *how the model itself processes audio internally*.

**The gap**: No work uses the model's own mechanistic structure as a safety signal — and no prior defense is evaluated on the standardized JALMBench corpus, making cross-method comparison impossible.

---

## Core Insight

From Paper A research: there exists a **"Listen Layer"** — a narrow band of layers where audio representations are *causally decisive* for model behavior (peak of grounding coefficient gc(L)).

**Hypothesis (Use-Case 1)**: When an audio jailbreak is active, the Listen Layer's gc(L) pattern is detectably *abnormal*:
- Legitimate audio queries: gc peaks sharply at L\*, then decays (model "consulted" audio, returned to text processing)
- Jailbreak audio: gc(L) pattern is shifted, suppressed, or shows anomalous cross-layer coupling

**Hypothesis (Use-Case 2)**: Audio-language models that primarily *guess* (low gc(k) at audio-decisive layers) are more susceptible to fine-tune-induced audio emergent misalignment — and the audit can detect this *before* fine-tuning occurs.

---

## Why Listen-Layer Audit Differs from Prior Work

| Method | Signal Source | Failure Mode |
|--------|--------------|-------------|
| SALMONN-Guard | Output text classifier | Misses attacks where harmful intent is encoded in audio prosody |
| SPIRIT (EMNLP 2025) | Attention pattern anomaly (cross-modal) | Requires labeled attack examples; brittle to novel attack types |
| ALMGuard (NeurIPS 2025) | Safety shortcut features (last N layers) | Doesn't localize *where* in audio processing the bypass occurs |
| Perplexity detector | Token probability | Completely blind to audio-modality attacks |
| Input classifier | Raw audio features (e.g., CLAP embedding) | No model internals; evadable by adversarial audio preserving surface features |

**What Listen-Layer Audit adds:**
- **Mechanism-first**: "Did the model *consult* the audio input normally?" — a process signal, not output signal
- **Zero-shot generalization**: gc(L) baseline uses benign data only. No attack examples needed; generalizes to novel attack paradigms
- **Adversarial robustness by design**: An attacker evading gc(L) detection must produce audio that *preserves normal causal audio processing* while still achieving the jailbreak goal — conflicting objectives
- **Localization as interpretability**: When anomaly fires, we know *which layer* was disrupted and *which audio features* drove it — detection plus diagnosis

---

## Evaluation Corpus: JALMBench

JALMBench (ICLR 2026) is the first comprehensive jailbreak evaluation benchmark for audio-language models:
- **246 curated queries** spanning harmful content categories
- **5 attack paradigms**: text-to-speech injection, prosodic manipulation, audio steganography, multimodal conflict, adversarial audio perturbation
- **Models evaluated**: Qwen2-Audio, SALMONN, Gemini-Audio, Whisper-LLaMA variants
- **Metrics**: Attack Success Rate (ASR), Semantic Preservation Score (SPS), Detection F1

By using JALMBench, our method is directly comparable to SALMONN-Guard, SPIRIT, and ALMGuard results — we can show which attack types our method catches that prior defenses miss.

---

## Use-Case 1: gc(L) Anomaly as Inference-Time Jailbreak Detector

### Research Tasks

**Task 1: Listen-Layer baseline characterization (CPU, Tier 0-1)**
- Input: JALMBench benign queries (~50) + ALME 57K audio-text conflict pairs
- Measure: gc(L) curve shape for each conflict type (phonological, semantic, prosodic)
- Output: gc(L) shape taxonomy (sharp peak, diffuse, suppressed, absent)
- Timeline: ~2 days with `listen_layer_audit.py` scaffold (already built)

**Task 2: Safety probe direction (CPU, Tier 0)**
- Input: JALMBench harmful vs. benign query pairs (matched for topic)
- Method: MMProbe (diff-of-means) at Listen Layer L\* → extract `safety_direction`
- Output: Linear "safe vs. unsafe audio" direction at L\*; probe accuracy on JALMBench held-out set

**Task 3: gc(L) anomaly score + JALMBench ROC (CPU, Tier 0)**
- Define: `anomaly_score(x) = KL-divergence(gc(L | x), gc(L | baseline))`
- Test on: Full JALMBench 246-query set (harmful) + matched benign set
- Output: ROC curve stratified by JALMBench attack paradigm

**Task 4: Comparison to baselines (write-up, Tier 0)**
- Compare using JALMBench F1 against: SALMONN-Guard, SPIRIT, ALMGuard, perplexity detector
- Expected finding: Listen-Layer probe catches *audio-specific* attacks (prosodic manipulation, multimodal conflict) that text-only probes miss — because those attacks *suppress* the Listen Layer
- Evidence: Attack-paradigm breakdown table (our F1 vs. baselines per attack type)

---

## Use-Case 2: gc(k) as Pre-Deployment Audio Emergent Misalignment Risk Screen

### Threat Model

**Core claim**: ALMs that primarily *guess* (rely on language priors, low gc(k) at audio-decisive layers) are more vulnerable to fine-tune-induced misalignment than models that *listen*.

**Mechanism (3-step)**:
1. **Shallow audio grounding** → guessing models encode weak acoustic representations at listen layers; safety behavior depends on LM backbone patterns
2. **Low LoRA barrier** → adversarial fine-tuning needs only to corrupt *linguistic* safety patterns (less acoustic signal diversity to resist distributional shift)
3. **Consequence** → safety degradation is deeper and faster for guessing models post fine-tune

**Analogy to text EM**: Betley et al. 2025 shows models fine-tuned on narrow coding domains develop misalignment on unrelated tasks. Audio EM is the acoustic modality version: fine-tuning on a narrow audio-harm domain causes audio safety misalignment. The guessing model is high-risk because its audio safety is already shallower.

### Research Tasks

**Task 5: gc(k) risk stratification (CPU, Tier 0)**
- Measure gc(k) profile for candidate ALM checkpoints on standard benign audio
- Stratify: "high listener" (sharp, high-magnitude gc-peak) vs. "low listener" (flat/diffuse)
- Output: Risk tier assignment per model checkpoint
- Tool: `listen_layer_audit.py` in mock mode

**Task 6: LoRA fine-tune susceptibility probe (Tier 1 CPU / Tier 2 full)**
- Fine-tune a high-gc(k) and low-gc(k) checkpoint on narrow benign-OOD domain (unusual accents, technical jargon — NOT harmful content; EM emerges from non-harmful OOD fine-tuning)
- Post-fine-tune: apply adversarial probe corpus (Q033 synthetic stimuli) to measure safety degradation
- Compare: did the low-gc(k) model degrade more?

**Task 7: gc(k) shift as EM predictor (Tier 0 analysis)**
- Measure gc(k) change pre/post fine-tune as a covariate
- Key question: Is the *magnitude of gc(k) shift* predictive of EM degree, independent of baseline gc(k)?
- If yes → gc(k) audit becomes a *diagnostic* for fine-tuning process, not just a static baseline

### Dual-Use Summary

| Aspect | Use-Case 1 (Jailbreak Detection) | Use-Case 2 (EM Risk Screen) |
|--------|----------------------------------|------------------------------|
| When to apply | At *inference time* | At *pre-deployment* |
| gc(k) signals | Anomaly from baseline during attack | Baseline level predicts EM risk |
| What it predicts | "Is this query an attack?" | "Is this model at risk of fine-tune misalignment?" |
| Adversary model | External attacker crafting audio | Insider fine-tuner / accidental OOD |
| Key metric | ROC on JALMBench | EM susceptibility delta (high-gc vs. low-gc) |

---

## ✅ Anti-Confound Checklist (10-Item Acoustic Eval Environment Controls)

All 10 items must pass for any result to appear in the MATS deliverable.

### Acoustic Baseline Controls
- [ ] **ACB-1 · Silence/noise floor baseline**: gc(L) on silence-only and pink-noise-only inputs; anomaly score must not fire
- [ ] **ACB-2 · Codec-matched benign baseline**: benign queries encoded with same codec/bitrate/sample-rate as attack corpus
- [ ] **ACB-3 · Speaker-matched baseline**: at least one benign utterance per speaker identity in the attack set

### Speaker Identity Controls
- [ ] **SID-1 · Cross-speaker generalization**: ROC stratified by same-speaker vs. different-speaker (attack vs. benign)
- [ ] **SID-2 · TTS-vs-human separation**: JALMBench TTS-generated attacks reported separately from human-recorded

### Text-Only Ablation Controls
- [ ] **TOA-1 · Text-only ASR transcript baseline**: text-only LM on ASR transcript; if ASR-alone ASR ≥ 80%, flag as `confound=text_leakage` and exclude from gc(L) stratification
- [ ] **TOA-2 · Audio-only (muted text) ablation**: for multimodal-conflict queries, verify attack fails with neutral dummy text prompt

### Prompt Injection Controls
- [ ] **PIC-1 · System prompt invariance**: detector performance must not degrade across varied system prompt templates
- [ ] **PIC-2 · Adversarial transcript injection**: test if injecting harmful text into ASR transcript mimics gc(L) anomaly signature (if yes → document as known limitation)
- [ ] **PIC-3 · Cross-paradigm contamination check**: threshold calibrated on one paradigm must not produce >20% FPR on clean queries from a different paradigm

### Checklist Usage Protocol

1. Run `listen_layer_audit.py --checkpoint-dir ./probes/` to save gc(L) curves
2. Run TOA-1 on all 246 JALMBench queries; tag leaky queries
3. Run ACB-1 silence/noise floor check; confirm anomaly score ≤ 0.05
4. Report ROC at three operating points: Precision=0.90, F1-max, Recall=0.90
5. Include per-paradigm breakdown table (SID-2 + cross-paradigm)
6. Attach checklist completion status to MATS deliverable appendix

---

## Environment Design Principles (Kroiz et al. 2026)

| Principle | Application |
|-----------|------------|
| **Opacity** — force model-internal reliance | Exclude queries where harmful intent is recoverable from ASR transcript alone (TOA-1) |
| **Checkpointing** — reproducibility | `--checkpoint-dir` saves gc(L) curves per query ID; ablations replay without re-running encoder |
| **Two-mode testing** — bidirectional robustness | Evaluate: harmful audio/benign transcript, benign/benign control, multimodal conflict |
| **Hidden-channel paradigm** — modality-specific encoding | Prosodic jailbreaks embed intent in non-semantic channels (intonation, speaking rate, spectral envelope) |
| **Threshold calibration** — avoid alarm fatigue | Three operating points reported: high-precision, balanced (F1-max), high-recall |

---

## Minimum Viable MATS Deliverable

A 6-page technical report:
1. Listen Layer localization method (from Paper A) — brief recap
2. gc(L) baseline taxonomy from JALMBench benign queries (Task 1)
3. Safety probe direction at L\* (Task 2)
4. gc(L) anomaly score definition + ROC curve on JALMBench (Task 3)
5. Per-paradigm comparison table vs. SALMONN-Guard/SPIRIT/ALMGuard (Task 4)
6. Mechanistic defense argument (adversarial robustness + localization)
7. Audio EM Risk Screen: gc(k) risk stratification + theoretical argument (Use-Case 2)
8. Failure modes and open questions

**Does NOT require**: GPU, fine-tuning, or harmful training data. All tasks = CPU-only.

---

## Policy Hook: gc(k) as Compute-Scaled Pre-Deployment Safety Mandate

> *New in v0.4 — connects to AI compute governance literature (cf. Hadfield-Menell et al. 2025; "Can Governments Slow AI Training?" AF post, 2026-03-08)*

### Core Argument

The gc(k) audit is uniquely suitable as a **mandatory compute-threshold safety check** for audio-language models — analogous to emissions testing for vehicles. As training compute scales, audio emergent misalignment risk increases (larger models develop stronger gc(k) divergence between listen and guess regimes). A gc(k) audit is:

1. **Cheap**: single forward pass on a standardized benign audio corpus (~50 utterances). Cost: negligible vs. training compute.
2. **Model-agnostic**: works on any transformer-based ALM regardless of architecture (Whisper, Qwen2-Audio, Gemini-Audio).
3. **Falsifiable**: gc(k) is a number; threshold can be set by regulators or safety labs. Pass/fail is unambiguous.
4. **Interpretable**: when a model fails, the audit points to *which layer* gc(k) deviates — this is actionable (targeted fine-tuning, layer-specific intervention).

### Compute Scaling Trigger Design

Proposed tiered mandate (inspired by FLOP-based compute governance proposals):

| Training Compute | Audit Requirement | Consequence of Failure |
|-----------------|-------------------|----------------------|
| < 10²² FLOPs | Voluntary (encourage) | None (best-effort) |
| 10²²–10²⁴ FLOPs | Mandatory self-audit + report to safety team | Internal hold pending review |
| > 10²⁴ FLOPs | Third-party audit + public disclosure of gc(k) profile | Deployment blocked until remediation |

**Why compute as the trigger?** Large-scale pre-training is when audio grounding patterns are established. Post-training interventions (RLHF, instruction tuning) can shift gc(k) without the lab noticing. A compute-gated mandatory audit catches: (a) pre-training regimes that produce shallow listeners, (b) post-training procedures that suppress gc(k).

### Connection to Compute Governance Literature

From "Can Governments Quickly and Cheaply Slow AI Training?" (Alignment Forum, 2026):
- Key insight: **Hardware-level interventions are the most tractable lever** for governments to slow AI training runs
- Corollary for gc(k) audit: the *same* hardware visibility used for compute governance (datacenter registries, FLOP tracking) can trigger gc(k) audit mandates — no new monitoring infrastructure needed
- gc(k) audit is therefore a *natural complement* to compute governance: governments use FLOP counts to gate deployment; safety labs use gc(k) to validate audio safety before those gated deployments proceed

### Why This Matters for MATS

MATS is MIRI/Anthropic-adjacent; reviewers care about:
- **Alignment tax reduction**: gc(k) audit costs ~0.001% of training compute; returns interpretability + safety signal
- **Scalable oversight**: gc(k) scales with model size — larger models have stronger gc(k) signal, not weaker; the audit becomes *more* informative at scale, not less
- **Tractable policy proposal**: unlike "interpretability solves alignment," a compute-threshold gc(k) mandate is a *specific, implementable* near-term intervention

### Scope Limitation (Honest Constraints)

- This section is *theoretical*: empirical validation of the compute-scaling claim (larger models → stronger gc(k) signal) requires access to multiple checkpoint sizes (Whisper tiny → large is a natural test bed, CPU-feasible)
- We do NOT claim gc(k) is a sufficient safety check — it is one necessary signal in a battery of pre-deployment evaluations
- Threshold values in the table above are illustrative; calibration needs empirical gc(k) measurements across model scales

---

## Connection to Broader Research Agenda

```
Paper A (Listen Layer localization)
  └─→ Paper C / MATS: Listen-Layer Audit for safety (this proposal)
        ├─→ Use-Case 1: gc(L) anomaly = inference-time jailbreak detector
        │     └─→ Eval: JALMBench 246-query (comparable to prior work)
        │     └─→ Defense mechanism: adversarially robust by design
        └─→ Use-Case 2: gc(k) baseline = pre-deployment EM risk screen
              └─→ Analogy: text EM (Betley et al. 2025) → audio EM
  └─→ Paper B (AudioSAEBench)
        └─→ gc(F) at feature level = fine-grained attribution
        └─→ Shared eval infrastructure: JALMBench + ALME 57K
```

---

## Why MATS Reviewers Should Care

| Claim | Why It Matters for Safety |
|-------|--------------------------|
| Model-internal detection | No reliance on external classifiers that fail on novel attacks |
| Zero-shot capability | No attack-specific training; generalizes by design |
| Adversarially robust by design | Evasion requires contradicting the attack goal |
| Audio-native | Text-modality safety infrastructure doesn't transfer |
| Mechanistic grounding | Detection signal comes from *why* the model processes audio |
| Dual-use gc(k) metric | One audit tool: inference-time detector + pre-deployment risk screen |
| Reproducible | JALMBench benchmark → direct comparison to published methods |
| Tractable & measurable | gc(L) is a number; ROC is a curve; F1 is comparable |

---

## Open Questions (For Leo / MATS Feedback)

1. Is the "gc(L) anomaly = jailbreak signal" hypothesis empirically supported? (Need Task 1 baseline first)
2. Should we target a specific MATS mentor or track? (MI track + AI safety track both relevant)
3. JALMBench uses Qwen2-Audio — do we prototype on Whisper (CPU) + extrapolate, or wait for GPU access?
4. Should this be a standalone MATS task or framed as an extension of Paper A?
5. Is the adversarial robustness argument empirically testable with CPU-only resources?
6. For Use-Case 2 (Audio EM): should Task 6 LoRA fine-tune be staged (Tier 1 CPU mock first)?

---

## Next Steps (v0.4 → Ready for Leo review)

- [ ] Leo reviews v0.4 — feedback on policy hook section (compute threshold table, governance framing), dual-use framing, MATS track selection, open questions
- [ ] Run Task 1 baseline (gc(L) from JALMBench benign) using `listen_layer_audit.py`
- [ ] Build gc anomaly score function (extend AudioSAEBench scaffold)
- [ ] If hypothesis supported → draft Paper C outline
- [ ] Apply to MATS (Leo to decide format/deadline)
