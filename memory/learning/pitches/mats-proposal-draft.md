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
