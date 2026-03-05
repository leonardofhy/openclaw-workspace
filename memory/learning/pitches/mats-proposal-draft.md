# 📄 MATS Research Task Proposal: "Listen-Layer Audit for Audio Jailbreak Detection"

> Version: 0.2 | Updated: 2026-03-02 10:45 (cycle c-20260302-1045, Q021)
> Track: T5 (Listen-Layer Audit / Paper C)
> Status: Draft v2 — JALMBench integration + mechanistic defense section expanded
> Depends on: Paper A (Listen Layer localization) for theoretical foundation

---

## 1-Sentence Pitch

> We use causal mechanistic interpretability to identify the layer-specific "Listen Layer" in speech LLMs and show its gc(L) anomaly score serves as a **zero-shot, attack-agnostic jailbreak detector** — evaluated on the JALMBench 246-query standardized benchmark.

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
- Now grounded in JALMBench: standardized, reproducible, comparable to prior work

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

**Hypothesis**: When an audio jailbreak is active, the Listen Layer's gc(L) pattern is detectably *abnormal*:
- Legitimate audio queries: gc peaks sharply at L*, then decays (model "consulted" audio, returned to text processing)
- Jailbreak audio: gc(L) pattern is shifted, suppressed, or shows anomalous cross-layer coupling

If this holds, the Listen Layer can serve as a **zero-shot jailbreak detector** — no training on attack examples needed.

---

## Evaluation Corpus: JALMBench

### Why JALMBench
JALMBench (ICLR 2026) is the first comprehensive jailbreak evaluation benchmark for audio-language models:
- **246 curated queries** spanning harmful content categories (violence, self-harm, fraud, CSAM-adjacent, illegal acts)
- **5 attack paradigms** covered: text-to-speech injection, prosodic manipulation, audio steganography, multimodal conflict, adversarial audio perturbation
- **Models evaluated**: Qwen2-Audio, SALMONN, Gemini-Audio, Whisper-LLaMA variants
- **Metrics**: Attack Success Rate (ASR), Semantic Preservation Score (SPS), Detection F1

### How We Use It
| JALMBench Component | Our Use |
|--------------------|---------|
| 246 harmful queries | Compute gc(L) anomaly score on each |
| 5 attack paradigms | Stratify ROC analysis by attack type |
| ASR per model | Correlate attack success with gc(L) suppression |
| Clean (benign) baseline | Set gc(L) reference distribution |

**Key advantage**: By using JALMBench as our eval corpus, our method is directly comparable to SALMONN-Guard, SPIRIT, and ALMGuard results reported in the same benchmark. We can show which attack types our method catches that prior defenses miss.

---

## Research Tasks (Concrete)

### Task 1: Listen-Layer baseline characterization (CPU, Tier 0-1)
- Input: JALMBench benign queries (subset ~50) + ALME 57K audio-text conflict pairs
- Measure: gc(L) curve shape for each conflict type (phonological, semantic, prosodic)
- Output: gc(L) shape taxonomy (sharp peak, diffuse, suppressed, absent)
- Timeline: ~2 days with `listen_layer_audit.py` scaffold (already built, Q006)

### Task 2: Safety probe direction (CPU, Tier 0)
- Input: JALMBench harmful vs. benign query pairs (matched for topic)
- Method: MMProbe (diff-of-means) at Listen Layer L* → extract `safety_direction`
- Output: Is there a linear "safe vs. unsafe audio" direction at L*? If yes → probe accuracy on JALMBench held-out set
- Connects to: SPIRIT (Q008), ALMGuard (Q010) for attack taxonomy

### Task 3: gc(L) anomaly score + JALMBench ROC (CPU, Tier 0)
- Define: `anomaly_score(x) = KL-divergence(gc(L | x), gc(L | baseline))`
- Test on: Full JALMBench 246-query set (harmful) + matched benign set
- Output: ROC curve stratified by JALMBench attack paradigm
- Key question: Which attack paradigms show strongest gc(L) anomaly signal?

### Task 4: Comparison to baselines (write-up, Tier 0)
- Compare directly using JALMBench F1 metric against: SALMONN-Guard, SPIRIT, ALMGuard, perplexity detector
- **Expected finding**: Listen-Layer probe catches *audio-specific* attacks (prosodic manipulation, multimodal conflict) that text-only probes miss — because those attacks *suppress* the Listen Layer rather than triggering text-side filters
- Evidence needed: Attack-paradigm breakdown table (our F1 vs. baselines per attack type)

---

## Mechanistic Defense: How Listen-Layer Audit Differs from Prior Work

This section addresses the core reviewer objection: *"You're just another safety probe — why is this different?"*

### Prior defenses and their failure modes

| Method | Signal Source | Failure Mode |
|--------|--------------|-------------|
| SALMONN-Guard | Output text classifier | Misses attacks where harmful intent is implicit / encoded in audio prosody |
| SPIRIT (EMNLP 2025) | Attention pattern anomaly (cross-modal) | Requires labeled attack examples for calibration; brittle to novel attack types |
| ALMGuard (NeurIPS 2025) | Safety shortcut features (last N layers) | Detects "safety shortcut bypass" but doesn't localize *where* in the audio processing pipeline the bypass occurs |
| Perplexity detector | Token probability | Completely blind to audio-modality attacks (only sees output tokens) |
| Input classifier | Raw audio features (e.g., CLAP embedding) | No access to model internals; can be evaded by adversarial audio that preserves surface features |

### What Listen-Layer Audit adds

**Mechanism-first**: Instead of asking "does the output look harmful?", we ask "did the model *consult* the audio input in the way it normally does for benign queries?" The gc(L) curve is a model-internal *process* signal, not an output signal.

**Zero-shot generalization**: gc(L) baseline characterization uses benign data only. No attack examples needed for calibration. This matters because novel attack paradigms (e.g., future steganographic audio) will not match any training distribution — but they *will* perturb gc(L).

**Localization as interpretability**: When gc(L) anomaly fires, we can say *which layer* was disrupted and *which audio features* drove the disruption (via Feature Attribution at L*). This is not just detection — it's diagnosis. MATS reviewers care about mechanistic insight, not just F1 scores.

**Adversarial robustness argument**: An attacker who wants to evade gc(L) detection must produce audio that *preserves the model's normal causal audio processing pattern* while still achieving the jailbreak goal. These are conflicting objectives — unlike evading an input classifier (just preserve surface features) or a text-output filter (just paraphrase). This adversarial-resistance argument should be a key claim in the paper.

---

## Minimum Viable MATS Deliverable

A 6-page technical report containing:
1. Listen Layer localization method (from Paper A) — brief recap
2. gc(L) baseline taxonomy from JALMBench benign queries (Task 1)
3. Safety probe direction at L* (Task 2 result)
4. gc(L) anomaly score definition + ROC curve on JALMBench 246-query set (Task 3)
5. Per-paradigm comparison table vs. SALMONN-Guard/SPIRIT/ALMGuard (Task 4)
6. Mechanistic defense argument (adversarial robustness + localization)
7. Failure modes and open questions

**Does NOT require:** GPU, fine-tuning, real-time inference. All tasks = CPU-only (using cached model activations or toy-model proxies for MVP).

---

## Connection to Broader Research Agenda

```
Paper A (Listen Layer localization)
  └─→ Paper C / MATS: Listen-Layer Audit for safety
        └─→ gc(L) anomaly = zero-shot jailbreak detection signal
        └─→ Eval: JALMBench 246-query (comparable to prior work)
        └─→ Defense mechanism: adversarially robust by design
  └─→ Paper B (AudioSAEBench)
        └─→ gc(F) at feature level = fine-grained attribution
        └─→ Eval: JALMBench + ALME 57K as joint corpus
```

The gc(L) metric and JALMBench corpus are **shared across Papers B and C** — same eval infrastructure, different research question.

---

## Why MATS Reviewers Should Care

| Claim | Why It Matters for Safety |
|-------|--------------------------|
| Model-internal detection | No reliance on external classifiers that fail on novel attacks |
| Zero-shot capability | No attack-specific training needed; generalizes by design |
| Adversarially robust by design | Evasion requires contradicting the attack goal |
| Audio-native | Text-modality safety infrastructure doesn't transfer |
| Mechanistic grounding | Detection signal comes from *why* the model processes audio |
| Reproducible | JALMBench benchmark → direct comparison to published methods |
| Tractable & measurable | gc(L) is a number; ROC curve is a number; F1 is comparable |

---

---

## Environment Design for JALMBench Evaluation (Kroiz et al. 2026 Principles)

> Section added: cycle c-20260303-0845, Q031
> Based on: agent-interp-envs repo scan (Q030) + Designing Environments for Understanding Model Motives (Q028)

Evaluating a mechanistic safety probe on audio jailbreaks requires careful environment design to avoid confounds. We follow five principles extracted from Kroiz et al. 2026 ([agent-interp-envs](https://github.com/gkroiz/agent-interp-envs)) and Nanda (LessWrong, 2026).

### Principle 1: Opacity — force model-internal reliance

**Problem**: If harmful intent in audio queries is trivially recoverable from the text transcript, the text pathway (not the Listen Layer) drives behavior. The detector would measure text-side artifacts, not audio-modality processing.

**Solution**: For each JALMBench query, we require that the harmful signal *must be encoded in the audio modality* — not recoverable from the Whisper ASR transcript alone. Queries where transcript alone exposes intent are tagged `confound=text_leakage` and excluded from the gc(L) stratification analysis (but kept in aggregate F1 comparison).

**Anti-confound check**: Run a text-only LM (no audio) on the ASR transcript. If it achieves >80% Attack Success Rate → flag as text-leakage confound.

### Principle 2: Checkpointing — reproducibility and ablation

**Solution**: The `listen_layer_audit.py` harness saves gc(L) curves per sample (JSON, keyed by JALMBench query ID). Ablations (different probe thresholds, different baselines) can replay without re-running the encoder. This is essential for JALMBench's 246-query scale — full re-runs are expensive.

**Implementation**: `--checkpoint-dir ./probes/` flag on `listen_layer_audit.py` (to be added in Q031 follow-up build task).

### Principle 3: Two-mode testing — bidirectional robustness

**From agent-interp-envs**: Sandbagging environments test *both* normal and reverse modes to catch intentional underperformance.

**Application**: Our eval must cover both confound directions:
- **Harmful audio / benign transcript**: attack uses prosody/intonation to encode harmful instruction
- **Benign audio / benign transcript**: control condition — gc(L) should *not* fire
- **Benign-sounding audio / explicit harmful text (multimodal conflict)**: tests whether model suppresses audio Listen Layer when text dominates

ROC curves must be stratified by these three conditions. A detector that fires on all three equally is useless; we want it specific to the first case.

### Principle 4: Hidden-channel paradigm — test modality-specific encoding

**From agent-interp-envs**: Funding Email env embeds ethically problematic content in an optional side document — tests if model *seeks out* hidden harmful information.

**Application**: We adapt this to audio: prosodic jailbreaks embed harmful instructions in *non-semantic* channels (intonation, speaking rate, spectral envelope) while the lexical content is benign. The Listen Layer audit tests whether the model's internal causal structure was influenced by this hidden channel — even when surface behavior looks clean.

This maps to JALMBench's "prosodic manipulation" attack paradigm, which prior text-based defenses miss entirely.

### Principle 5: Threshold calibration — avoid alarm fatigue

**From agent-interp-envs**: Sandbagging env tests agent behavior under varying consequence signals.

**Application**: gc(L) anomaly detection has a sensitivity parameter (KL-divergence threshold). We validate at three operating points:
- **High precision** (P=0.90): low false alarm rate — suitable for flagging in production inference
- **Balanced** (F1-maximizing): best overall JALMBench score — fair comparison to baselines
- **High recall** (R=0.90): catch all attacks — acceptable for offline auditing

Table of metrics at all three operating points should be included in the MATS deliverable to demonstrate we are not cherry-picking a threshold.

---

## ✅ Anti-Confound Checklist (Acoustic Eval Environment Controls)

> Added: cycle c-20260305-1015, Q037
> Use before reporting any JALMBench gc(L) result. All 10 items must pass for a result to be included in the MATS deliverable.

### Acoustic Baseline Controls

- [ ] **ACB-1 · Silence/noise floor baseline**: gc(L) measured on silence-only and pink-noise-only inputs; confirm anomaly score does not fire. Sets the floor; prevents the detector from triggering on low-energy audio artifacts.
- [ ] **ACB-2 · Codec-matched benign baseline**: benign queries encoded with the *same* codec/bitrate/sample-rate as the attack corpus. Eliminates codec-induced spectral artifacts as confound (different bitrate = different gc(L) bias).
- [ ] **ACB-3 · Speaker-matched baseline**: benign baseline must include at least one benign utterance per speaker identity present in the attack set. Prevents the detector from learning "attacker voice" rather than "attack content."

### Speaker Identity Controls

- [ ] **SID-1 · Cross-speaker generalization**: report ROC stratified by whether the attack and benign utterances were same speaker or different speaker. A detector that fires only on specific speaker characteristics is not a safety probe — it's a speaker classifier.
- [ ] **SID-2 · TTS-vs-human speaker separation**: JALMBench contains both human-recorded and TTS-generated attacks. Report metrics separately; if TTS attacks dominate the signal, the probe may be detecting TTS artifacts, not the attack pattern.

### Text-Only Ablation Controls

- [ ] **TOA-1 · Text-only ASR transcript baseline**: run a text-only LM (no audio encoder) on the Whisper ASR transcript of each attack. If text-only ASR attack success rate ≥ 80%, flag query as `confound=text_leakage` and exclude from gc(L) stratification. Prevents measuring text-pathway artifacts as audio-modality detection.
- [ ] **TOA-2 · Audio-only (muted text) ablation**: for multimodal-conflict JALMBench queries, verify the attack fails when the text prompt is replaced with a neutral dummy prompt. Confirms the attack requires the *audio* modality, not just the text channel.

### Prompt Injection Controls

- [ ] **PIC-1 · System prompt invariance**: detector performance must not degrade if the system prompt is varied (e.g., changed instruction template, added/removed safety preamble). A prompt-injection-sensitive probe is fragile in deployment.
- [ ] **PIC-2 · Adversarial transcript injection**: test whether an attacker who *injects* harmful content into the Whisper ASR transcript (text channel) can mimic the gc(L) anomaly signature. If yes, the probe can be spoofed without audio manipulation → document as a known limitation.
- [ ] **PIC-3 · Cross-paradigm contamination check**: for each of JALMBench's 5 attack paradigms, verify that the gc(L) threshold calibrated on one paradigm does not produce >20% false positive rate on clean queries from a *different* paradigm. Prevents the threshold from being over-fit to a single attack style.

---

### Checklist Usage Protocol

Before any result table is finalized:

1. Run `listen_layer_audit.py --checkpoint-dir ./probes/` to save gc(L) curves.
2. Run the text-only ablation (TOA-1) on all 246 JALMBench queries; tag leaky queries.
3. Run silence/noise floor check (ACB-1); confirm anomaly score ≤ 0.05 for both.
4. Report ROC at three operating points (Precision=0.90, F1-max, Recall=0.90).
5. Include per-paradigm breakdown table (SID-2 + cross-paradigm).
6. Attach checklist completion status to the MATS deliverable appendix.

---

---

## Use-Case 2: Audio Emergent Misalignment (EM) — gc(k) as Pre-Deployment Risk Screen

> Section added: cycle c-20260305-1115, Q038
> Based on: Q036 hypothesis note (c-20260305-1045), text EM analogy (Betley et al. 2025)

### One-Sentence Framing

> gc(k)-low "guessing" models are more susceptible to fine-tune-induced audio safety misalignment than gc(k)-high "listening" models — and the audit can detect this *before* fine-tuning occurs.

---

### Threat Model

**Core claim**: Audio-language models that primarily *guess* (rely on language priors, low gc(k) at audio-decisive layers) are more vulnerable to fine-tune-induced misalignment than models that *listen* (grounding predictions in acoustic features, high gc(k)).

**Mechanism** (3-step):
1. **Shallow audio grounding** → guessing models encode weak acoustic representations at listen layers; safety behavior depends almost entirely on LM backbone linguistic patterns.
2. **Low LoRA barrier** → adversarial fine-tuning on a narrow audio-harm domain only needs to corrupt *linguistic* safety patterns (fewer audio-grounded features to overwrite; less acoustic signal diversity to resist distributional shift).
3. **Consequence** → safety degradation is deeper and faster for guessing models post fine-tune.

**Analogy**: In text EM (Betley et al. 2025), models fine-tuned on narrow coding domains show misalignment on unrelated tasks — a generalization failure from shallow task specialization. Audio EM is the acoustic modality version: fine-tuning on a narrow audio-harm domain causes misalignment in audio safety behavior. The guessing model is the high-risk case because its audio safety is already shallower.

---

### Research Tasks for Use-Case 2

**Task 5: gc(k) risk stratification (CPU, Tier 0)**
- Measure gc(k) profile for a set of candidate ALM checkpoints on standard benign audio
- Stratify into "high listener" (gc-peak sharp, high magnitude) vs. "low listener" (gc flat/diffuse)
- Output: Risk tier assignment per model checkpoint
- Tool: existing `listen_layer_audit.py` in Tier 0 mock mode

**Task 6: LoRA fine-tune susceptibility probe (CPU / Tier 1 for actual LoRA, Tier 2 for full run)**
- Fine-tune a high-gc(k) and low-gc(k) checkpoint on a narrow benign-OOD domain (unusual accents, technical jargon — NOT harmful content; EM emerges even from non-harmful OOD fine-tuning)
- Post-fine-tune: apply existing audio adversarial probe corpus (from Q033 synthetic stimuli) to measure safety degradation
- Compare: did the low-gc(k) model degrade more?
- Approximate Tier 1 cost: CPU mock extraction; actual LoRA = Tier 2 (Leo approval)

**Task 7: gc(k) shift as EM predictor (Tier 0 analysis)**
- Measure gc(k) change pre/post fine-tune as a covariate
- Key question: Is the *magnitude of gc(k) shift* predictive of EM degree, independent of baseline gc(k)?
- If yes → gc(k) audit becomes a *diagnostic* for fine-tuning process, not just a static baseline

---

### Key Signals to Monitor

| Signal | Expected pattern in guessing model |
|--------|------------------------------------|
| gc(k) pre-fine-tune | Flat/diffuse (low magnitude at listen layers) |
| gc(k) shift post fine-tune | Larger drop than in listening model |
| Safety probe accuracy pre-fine-tune | Already lower baseline |
| Safety probe degradation rate | Faster degradation per epoch |
| Layer-wise activation shift (L2) | Larger in audio-encoding layers |
| Gradient flow to audio encoder | Lower (LM backbone dominates) |

---

### Expected Failure Modes

1. **No EM effect**: Fine-tune dataset too small/benign — no degradation in either model. Fix: scale fine-tune set.
2. **Both degrade equally**: Safety fully in LM backbone (shared pathway), gc(k) level irrelevant. Would imply safety is LM-prior-driven, not audio-grounded — itself an important finding.
3. **High-gc(k) model degrades MORE**: Listening models more brittle if safety depends on acoustic cues fine-tuning disrupts. Would falsify hypothesis; suggests linguistic redundancy in guessing models protects them.
4. **gc(k) shift confounds baseline**: Fine-tuning changes gc(k) — need pre-fine-tune measurement as fixed baseline, gc(k) change as separate covariate.
5. **Evaluation saturation**: Safety probes too easy pre-fine-tune → no signal. Fix: use adversarial audio probes near decision boundary (existing Q033 corpus).

---

### Connection to Use-Case 1 (Jailbreak Detection)

| Aspect | Use-Case 1 (Jailbreak Detection) | Use-Case 2 (EM Risk Screen) |
|--------|----------------------------------|------------------------------|
| When to apply | At *inference time* | At *pre-deployment* |
| What gc(k) signals | Anomaly from baseline during attack | Baseline level predicts EM risk |
| What it predicts | "Is this query an attack?" | "Is this model at risk of fine-tune misalignment?" |
| Adversary model | External attacker crafting audio | Insider fine-tuner / accidental OOD |
| Key metric | ROC on JALMBench | EM susceptibility delta (high-gc vs. low-gc checkpoint) |

**Unified framing**: The gc(k) metric serves *two roles* — an **inference-time detector** (Use-Case 1) and a **pre-deployment risk screen** (Use-Case 2). This dual-use argument is a strong MATS differentiator: one audit tool, two safety applications.

---

### MATS Deliverable Addition (Use-Case 2)

For the 6-page MATS technical report, add:

**Section 8**: Audio EM Risk Screen
- gc(k) risk stratification method + prototype results (Task 5, mock data)
- Theoretical argument for why gc(k)-low = higher EM risk (3-step mechanism above)
- Connection to text EM literature (Betley et al. 2025 comparison)
- Failure modes and open questions

**Does NOT require**: Real fine-tuning, GPU, or harmful training data. All can be demonstrated on mock activations from existing `synthetic_stimuli.py` + `unified_eval.py` infrastructure.

---

## Open Questions (For Leo / MATS Feedback)

1. Is the "gc(L) anomaly = jailbreak signal" hypothesis empirically supported? (Need Task 1 baseline first)
2. Should we target a specific MATS mentor or track? (MI track + AI safety track both relevant)
3. JALMBench uses Qwen2-Audio as primary model — do we prototype on Whisper (CPU) + extrapolate, or wait for GPU access?
4. Should this be a standalone MATS task or framed as an extension of Paper A?
5. Is the adversarial robustness argument (Section above) empirically testable with CPU-only resources?

---

## Next Steps (After Leo Reviews)

- [ ] Run Task 1 (gc baseline from JALMBench benign) using existing `listen_layer_audit.py`
- [ ] Build gc anomaly score function (extend AudioSAEBench scaffold from Q020)
- [ ] Write MATS application (Leo to decide format/deadline)
- [ ] If hypothesis supported → draft Paper C outline
