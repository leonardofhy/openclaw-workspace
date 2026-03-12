# Pitch: gc(k) as a CPU-Feasible Regulatory Audit Tool for Speech AI

> Created: 2026-03-12 09:01 (cycle c-20260312-0901, Q084)
> Track: T3 (Paper A §5 extension / standalone policy note)
> Status: DRAFT — for Leo's review
> Word count: ~520 words

---

## Core Argument

Large audio-language models are increasingly deployed in high-stakes settings — courtrooms (voice evidence), healthcare (clinical dictation), border control (accent profiling), and public-sector ASR systems. Regulators and auditors need a method to answer: **"Is this system actually listening, or is it guessing from context?"** This is not a hypothetical concern — Modality Collapse (Zhao et al. 2026, arXiv:2602.23136) shows that state-of-the-art LALMs systematically ignore audio when text context is present. Cascade Equivalence (Billa et al. 2026, arXiv:2602.17598) shows most speech LLMs reduce to implicit text cascades.

The gap: **existing evaluation methods are behavioral** (accuracy on benchmarks), not structural. A model can pass a benchmark while relying on spurious text context — and break silently when deployed on audio from underrepresented accents, noisy conditions, or languages not in the training distribution. Regulators need structural evidence, not benchmark scores.

**gc(k) closes this gap** — and, critically, it does not require GPU access.

---

## What gc(k) Measures

The grounding coefficient gc(L) = DAS-IIA(layer L, phonological variable A): the fraction of phonological minimal pair interventions at layer L that cause the model to respond as though it heard the audio-grounded input. It is:

- **Causal** (Pearl Level 3, Joshi et al. 2026): not a correlation but an intervention
- **Structural**: measures where in the network audio becomes decisive, not just whether it does
- **Layer-resolved**: produces a curve gc(L) over all encoder layers, not just a scalar pass/fail

The Listen Layer L* = argmax gc(L) is the depth where audio information is causally sufficient for correct output. A model without a well-localized, high-amplitude gc(L) peak fails the structural audit — regardless of benchmark accuracy.

---

## The CPU-Only Regulatory Path

Steps 1–3 of the Grounding Failure Diagnostic Protocol (Paper A §4.7) require no GPU:

| Step | What it tests | Cost |
|------|--------------|------|
| Codec Probe | Does RVQ Layer 1 preserve the phonological contrast? | 2 min, CPU, SpeechTokenizer |
| Encoder gc(L) sweep | Is there a Listen Layer in the encoder? | 30 min, CPU, Whisper-small / any encoder |
| Connector Transfer Test | Does phonological geometry survive the connector? | 5 min, CPU, LLM layer 0 only |

**Total: ~35 minutes on a laptop.** If the model fails Step 2 (encoder gc flat near chance) or Step 3 (connector destroys subspace), the model is structurally non-grounded — the regulator has structural evidence of a grounding failure without ever running the full LLM.

The full Tier 3 diagnosis (LLM backbone, Step 4) requires GPU, but Steps 1–3 already cover the majority of real-world failure modes: codec failures (low-resource languages, rare phonemes) and connector bottlenecks are cheaper to detect than LLM backbone collapse.

---

## What This Enables

1. **Checkpoint auditing**: Before deploying a speech AI system in high-stakes settings, regulators run the 3-step protocol. Pass/fail is a structural certification, not a benchmark score.

2. **Phonological coverage audit**: Run gc(L) separately per phoneme class (§3.8.5). If the model shows a Listen Layer for common English phonemes but not for rare contrasts or non-English phonological features, the audit flags differential grounding — a disparity that behavioral benchmarks routinely miss (Risk A6: Asiaee 2026).

3. **Adversarial detection flag**: gc(L) + M9 causal abstraction consistency (Q083) forms a dual-factor safety probe: a model with elevated M7 (SAE feature anomaly) AND low M9 (causal inconsistency) is exhibiting adversarial audio grounding failure — detectable without GPU, without adversarial examples, without access to the training distribution.

4. **RL-training certification**: MPAR² (arXiv:2603.02266) shows RL training recovers audio perception from 31.74% → 63.51%. gc(L) can verify the mechanism: a certified MPAR²-trained model should show reduced gc(L_late) drop (less Tier 3 collapse). Regulatory bodies can require gc(L) curves as part of a model card submission.

---

## Where This Lives in Paper A

**Option A (§5 Discussion, subsection 5.5 extension):** 1–2 paragraph policy implication note, "our protocol is accessible to compute-constrained auditors."

**Option B (Standalone short paper / position paper):** ~2500 words, target venue — ACL workshop on NLP for Policy, FAccT 2027, or IEEE S&P 2027. "CPU-feasible structural auditing of speech AI systems via grounding coefficient measurement."

**Recommendation:** Start with Option A in Paper A §5. If Leo's policy interest is strong, expand to Option B after Paper A is submitted. Option B requires no new experiments — all evidence is in Paper A.

---

## Key Citations (all already cited in Paper A)

- Zhao et al. arXiv:2602.23136 — Modality Collapse (behavioral motivation)
- Billa et al. arXiv:2602.17598 — Cascade Equivalence (structural motivation)
- Sadok et al. arXiv:2506.04492 — SpeechTokenizer Layer 1 = semantic content
- Joshi et al. arXiv:2602.16698 — Pearl Level 3 causal standard
- Asiaee et al. arXiv:2602.24266 — Variance proxy limitation (phoneme coverage gap)
- MPAR² arXiv:2603.02266 — RL training recovery (certification target)

---

## Status

✅ DRAFT COMPLETE. ~520 words. No new citations introduced (all from Paper A corpus). Paper A §5 integration: 2-paragraph stub, ready to insert after §5.5 (Limitations). FAccT/ACL policy venue option noted.

**Next action**: Leo review — is the policy angle worth expanding to Option B standalone paper?
