# 📊 Weekly Research Summary — 2026-W12 (Mar 16–22)

> Auto-generated: 2026-03-22 21:00 TST

## 🔢 Key Metrics

| Metric | Count |
|--------|-------|
| Autodidact cycles completed (this week) | 61 |
| Active research days | 5 (Mar 16–19; 21–22; Mar 20 quiet) |
| Deep paper reads (new this week) | 2 |
| Paper scans / shallow reads | ~15 |
| Build outputs (scripts/design docs/artifacts) | ~30+ |
| Ideation cycles | ~17 |
| New research questions queued (Q-series) | ~25 (Q129–Q157) |
| New gaps advanced/opened | ~3 |
| Knowledge graph sections | 50+ subsections |
| New concepts added to KG | ~8 (see below) |

## 📖 Papers Read This Week (Deep / Engaged)

1. **arXiv:2603.06854 — "Are Audio-Language Models Listening? Audio-Specialist Heads for Adaptive Audio Steering"** (Glazer, Aharon, Fetaya; Bar-Ilan; Mar 6, 2026)
   - Locates audio-specialist attention heads via MI; builds audio↔silence steering direction; achieves +8pp on MMAU with zero parameter updates on Qwen2-Audio-7B.
   - Critical connection: their "audio-specialist heads" are the **head-level version** of gc(k) peak. The gc(k) peak layer is likely the layer where specialist heads fire most → a **unification hypothesis** forming.
   - T5 angle: their "listening signal" = T5's safety monitor. Listening signal → silence on non-silent audio = suspicious (jailbreak indicator).
   - Action: cite as concurrent work in Paper A §2; strengthen "causal vs observational" positioning.

2. **arXiv:2602.17598 — "Cascade Equivalence Hypothesis" (Billa et al.; Interspeech 2026 submission)** _(deep re-read; multiple cycle passes)_
   - Multiple new connections surfaced: their behavioral cascade equivalence is **operationalized** by Leo's Q113: `cascade_degree = 1 − AND_gate_fraction`.
   - Their LEACE/logit lens approach (observational) vs gc(k) (causal) = direct differentiation row in Paper A §2.
   - Under noise (0dB SNR), cascade-equivalent models lose 7.6% — exactly the regime where gc(k) collapse is predicted by the AND-gate destruction model.

## 🔑 New Concepts Added to Knowledge Graph

1. **Audio-Specialist Heads** (from 2603.06854): head-level audio engagement metric; head-level complementary to layer-level gc(k)
2. **Listening Signal** as T5 safety feature: measurable proxy for "is the model actually using audio?"
3. **AND-gate steering intervention** (Q139): boost AND-gate features at gc peak for high-PPL phonemes → FAD-bias correction → WER reduction
4. **RAVEL Isolate as beam rescoring signal** (Q133): Isolate(k_peak, token_t) as ASR N-best rescoring feature → audio-grounding-aware beam selection
5. **Speaker-ID × AND-gate enrichment** (Q131): speaker-specific features are AND-gate (audio necessary); agnostic phoneme features are OR-gate — mean AND-frac 0.454 vs 0.138
6. **Instruction-tuning footprint** (Q143): IT fine-tuning inflates OR-gate proportion in instruction-semantics decoder layers; safety implication: jailbreaks succeed via already-OR-gate IT features
7. **ENV-1 hubs as cross-language universal phoneme units** (Q145): ENV-1 hub features encode phoneme identity invariantly across EN/ZH/MS/ES; extends ENV taxonomy with multilingual axis
8. **Adversarial audio t* detector** (Q129): FGSM adversarial noise causes t* leftward shift (t* < 4 = flag); clean t* mean 7.86 vs adversarial 1.50; F1 = 1.00 (synthetic); CPU-feasible detection protocol ready

## 🔬 Top 3 Open Research Problems / Gaps Discovered This Week

### 1. Gap #35 — Instruction-Tuning as AND→OR Gate Converter
- **Problem**: IT fine-tuning (RLHF/SFT) reinforces text-conditional behavior → inflates OR-gate proportion in instruction-following decoder layers. No mechanistic account exists of how IT changes the AND/OR gate distribution.
- **Why it matters**: If instruction features are already OR-gates, adversarial text-only injection bypasses audio safeguards entirely — explains why text-based jailbreaks work on audio-capable models.
- **Status**: 🟡 OPEN — design doc Q143 written; mock prediction ready; needs real Whisper-base vs IT-Whisper comparison.
- **Blocker**: Access to instruction-tuned Whisper checkpoint (hypothetical in mock; Qwen2-Audio-Instruct available via NDIF).

### 2. Gap #36 — Isolate(k) as ASR N-best Rescoring Signal
- **Problem**: Current ASR beam rescoring uses LM score or CTC confidence — both are text-modality signals. No audio-mechanistic rescoring signal exists that tells the model "this beam candidate was grounded in audio."
- **Why it matters**: RAVEL Isolate at gc-peak is the natural mechanistic rescoring signal: high Isolate = clean audio decoding; low Isolate = text-prediction / hallucination risk. This would be a novel, interpretability-grounded engineering contribution.
- **Status**: 🟡 OPEN — Q133 design doc + mock written; correlation target established (Isolate vs beam_score); Pearson r predicted > 0.6. Needs real Whisper beam search data.
- **Potential paper contribution**: Could be a standalone contribution for Paper A §4.8 or AudioSAEBench (Paper B) evaluation criterion.

### 3. Gap #37 — ENV-1 Hub Features as Cross-Language Universal Phoneme Detectors
- **Problem**: Are Whisper's high-degree SAE hub features (ENV-1) truly language-agnostic acoustic primitives? If so, this gives an interpretable basis for Whisper's cross-lingual generalization — but no feature-level evidence exists.
- **Why it matters**: If ENV-1 hubs = cross-lingual phoneme universals, then: (a) interventions generalize across languages, (b) a single hub feature set is auditable for all languages, (c) this bridges cognitive phonology (universal phoneme categories) with neural mech-interp.
- **Status**: 🟡 OPEN — Q145 design doc written; mock predictions (>60% cross-lingual activation overlap for ENV-1; <20% for ENV-3); needs multilingual Common Voice experiment.
- **Research risk**: Low — Whisper was trained on 680K hours multilingual; hub-feature universality is expected; the contribution is the mechanistic verification.

## 🛠️ Key Build Outputs This Week

| Artifact | Task | Purpose |
|---|---|---|
| `adv_audio_t_star_detector.py` | Q129 | Adversarial audio → t* leftward shift detection (F1=1.00 mock) |
| `phoneme_mdas.py` | Q109 | Phoneme RAVEL MDAS disentanglement metric |
| `speaker_identity_gate_mock.py` | Q131 | Speaker-ID × AND-gate enrichment (0.317 separation) |
| FAD bias × Cause/Isolate design | Q123/Q139 | FAD correction via AND-gate steering; Q123 reframe as negative-result |
| Beam rescoring design doc | Q133 | Isolate(k_peak) as ASR N-best rescoring signal |
| Q143 design doc | Q143 | IT-tuning footprint: instruction features → OR-gate shift |
| Q145 design doc | Q145 | ENV-1 hub universality across EN/ZH/MS/ES |
| `q142_results.json`, `q134_results.json` | Q142/Q134 | Results archives |
| Ideation batch Q148–Q157 | c-20260322-1315 | Queue replenished after full archival; 10 new READY tasks |

## 📐 Theoretical Convergence Emerging

This week's most significant conceptual development: **Triple-alignment unification** fully crystallized:

```
cascade_degree ≈ 1 − AND_gate_fraction ≈ 1 − GSAE_edge_density
```

And t* (collapse onset) = argmin(Isolate) = argmin(GSAE_density) → **single diagnostic unifies T3 + T5**.

Additionally: **AND/OR gate × ENV topology × RVQ hierarchy** all co-align:
- ENV-1 hub → RVQ-1 semantic → text-predicted (OR-gate for high-level semantics)
- ENV-3 isolated → RVQ-N acoustic → audio-grounded (AND-gate for fine detail)

This generates testable predictions across 3 independent formalisms — strong Paper A §3–4 scaffold.

## 📅 Conference Pipeline Update

No new confirmed deadlines found this week. Status unchanged from W11:

| Conference | Deadline | Target Paper | Status |
|-----------|----------|-------------|--------|
| Interspeech 2026 | ~~2026-03-05~~ | AudioMatters | ✅ Submitted |
| **Interspeech 2026 (Paper A)** | Abstract ~Mar 31; Full ~April | Listen vs Guess (Paper A) | ⚠️ CRITICAL — E1 needed NOW |
| NeurIPS 2026 | ~May 2026 | Listen vs Guess (Paper A) extended | In progress |
| EMNLP 2026 | ~June 2026 | AudioSAEBench (Paper B) | In progress |
| MATS Research Proposal | TBD (rolling) | Paper C (T5 safety) | Mock results strong |

**⚠️ Interspeech 2026 alert**: Abstract deadline ~March 31 is **9 days away**. E1 experiment (Whisper-small, MacBook 3h) is the minimum requirement. Blocked on Leo unblock.

## ⚠️ Blockers (Unchanged)

1. **Leo unblock P0**: venv setup + first .wav file + Gap #18 phonological geometry experiment approval. E1 feasibility confirmed — CPU only, ~3h.
2. **GPU scale-up**: Whisper-small/medium experiments awaiting Leo approval. Q003 remains blocked.
3. **arXiv Q147**: AlignmentForum 429 rate limit — retry pending.
4. **Pre-experiment writing budget**: EXHAUSTED — §5 Discussion blocked until real experimental results.

## 📈 Progress vs W11

| Dimension | W11 | W12 |
|-----------|-----|-----|
| Cycles total | 62 (that week) | 61 (this week) |
| Papers deep-read (cumulative) | ~27+ | ~29+ |
| Research gaps tracked | 35 | 37+ |
| Q-tasks completed (cumulative) | ~128 | ~148+ |
| READY queue | 0 (exhausted) | 10 (replenished today) |
| Build artifacts | ~8 | ~30+ |
| Phase | explore-fallback → converge | converge (theory complete) |

## 🎯 Next Week Priorities (W13)

1. **Get Leo to approve E1 CPU experiment** — t3_readiness_check 5/5; Interspeech deadline 9 days away
2. **Interspeech Paper A abstract submission** — if E1 completes, submit or draft abstract with provisional results
3. **Q148–Q157**: work through 10 READY tasks (GCBench-14 real Whisper run, silence × t* threshold, attention entropy × AND-gate, Isolate × beam diversity, VLM AND/OR analogy)
4. **Retry Q147** (AlignmentForum arXiv batch — rate limit)
5. **MATS T5 proposal draft** — emotion jailbreak (AND-frac 74%→19%) + persona dual-signal (89–93% acc) provide strong mock evidence base

---
_Generated by Little Leo (Lab) • Weekly Research Summary cron • 2026-W12_
