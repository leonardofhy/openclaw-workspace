# 📄 MATS Research Task Proposal: "Listen-Layer Audit for Audio Jailbreak Detection"

> Version: 0.1 | Created: 2026-03-01 14:15 (cycle c-20260301-1415, Q007)
> Track: T5 (Listen-Layer Audit / Paper C)
> Status: Draft — for Leo's review before submission.
> Depends on: Paper A (Listen Layer localization) for theoretical foundation

---

## 1-Sentence Pitch

> We use causal mechanistic interpretability to identify the layer-specific audio processing "Listen Layer" in speech LLMs and show it can serve as a lightweight, model-internal signal for detecting audio jailbreak attacks — without any attack-specific training.

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

---

## Problem Statement

Audio-language models (ALMs) can be jailbroken via audio modality attacks that text-content filters miss:
- **Prosodic jailbreaks**: commands disguised in intonation/tone rather than lexical content
- **Audio-text conflict injection**: malicious instructions in speech while benign text context
- **Phoneme-level adversarial audio**: perturbed audio that sounds normal but shifts model behavior

Current defenses are surface-level (audio classifiers, keyword filters). None exploit *how the model itself processes audio internally*.

**The gap**: No work uses the model's own mechanistic structure as a safety signal.

---

## Core Insight

From Paper A research: there exists a **"Listen Layer"** — a narrow band of layers where audio representations are *causally decisive* for model behavior (peak of grounding coefficient gc(L)).

**Hypothesis**: When an audio jailbreak is active, the Listen Layer's gc(L) pattern is detectably *abnormal*:
- Legitimate audio queries: gc peaks sharply at L*, then decays (model "consulted" audio, returned to text processing)
- Jailbreak audio: gc(L) pattern is shifted, suppressed, or shows anomalous cross-layer coupling

If this holds, the Listen Layer can serve as a **zero-shot jailbreak detector** — no training on attack examples needed.

---

## Research Tasks (Concrete)

### Task 1: Listen-Layer baseline characterization (CPU, Tier 0-1)
- Input: ALME 57K audio-text conflict pairs (clean stimuli, known gc pattern)
- Measure: gc(L) curve shape for each conflict type (phonological, semantic, prosodic)
- Output: gc(L) shape taxonomy (sharp peak, diffuse, suppressed, absent)
- Timeline: ~2 days with `listen_layer_audit.py` scaffold (already built, Q006)

### Task 2: Safety probe direction (CPU, Tier 0)
- Input: Subset of audio instruction pairs (safe vs. harmful content)
- Method: MMProbe (diff-of-means) at Listen Layer L* → extract `safety_direction`
- Output: Is there a linear "safe vs. unsafe audio" direction at L*? If yes → probe accuracy
- Connects to: SPIRIT (Q008), ALMGuard (Q010) for attack taxonomy

### Task 3: Listen-Layer anomaly score (CPU, Tier 0)
- Define: `anomaly_score(x) = KL-divergence(gc(L | x), gc(L | baseline))`
- Test on: (a) ALME conflict pairs with injected random shift, (b) simulated prosodic attack
- Output: ROC curve for anomaly score as jailbreak detector
- Key question: Does abnormal gc(L) pattern correlate with jailbreak success?

### Task 4: Comparison to baselines (write-up)
- Compare to: text-side safety probes (Zou et al.), input-level filters, perplexity detectors
- Expected finding: Listen-Layer probe catches *audio-specific* attacks that text-only probes miss
- Evidence needed: 1-2 attack examples where text probe fails but gc-anomaly succeeds

---

## Minimum Viable MATS Deliverable

A 6-page technical report containing:
1. Listen Layer localization method (from Paper A) — brief recap
2. Safety probe direction at L* (Task 2 result)
3. gc(L) anomaly score definition + ROC curve on simulated attacks (Task 3)
4. Failure modes and open questions

**Does NOT require:** GPU, real jailbreak dataset, fine-tuning. All tasks above = CPU-only.

---

## Connection to Broader Research Agenda

```
Paper A (Listen Layer)
  └─→ Paper C / MATS: Listen-Layer Audit for safety
        └─→ gc(L) anomaly = zero-shot jailbreak detection signal
  └─→ Paper B (AudioSAEBench)
        └─→ gc(F) at feature level = fine-grained attribution
```

The gc(L) metric is **reused across all three papers** — same code, same stimuli (ALME), different research question.

---

## Why MATS Reviewers Should Care

| Claim | Why It Matters for Safety |
|-------|--------------------------|
| Model-internal detection | No reliance on external classifiers that fail on novel attacks |
| Zero-shot capability | No attack-specific training needed; generalizes by design |
| Audio-native | Text-modality safety infrastructure doesn't transfer; this is the first audio-native approach |
| Mechanistic grounding | The detection signal comes from *why the model processes audio* — harder to adversarially evade |
| Tractable & measurable | gc(L) is a number; ROC curve is a number; easy to compare across methods |

---

## Open Questions (For Leo / MATS Feedback)

1. Is the "gc(L) anomaly = jailbreak signal" hypothesis empirically supported? (Need Task 1 baseline first)
2. Should we target a specific MATS mentor or track? (MI track seems natural)
3. Do we need real jailbreak audio examples, or are ALME conflict pairs sufficient as proxy?
4. Should this be a standalone MATS task or framed as an extension of Paper A?

---

## Next Steps (After Leo Reviews)

- [ ] Run Task 1 (baseline gc characterization) using existing `listen_layer_audit.py`
- [ ] Deep-read SPIRIT + ALMGuard (Q008-Q010) to ground attack taxonomy
- [ ] Write MATS application (Leo to decide format/deadline)
- [ ] If hypothesis supported → draft Paper C outline
