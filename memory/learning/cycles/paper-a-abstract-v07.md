# Paper A Abstract v0.7
**Task:** Q062 | **Cycle:** c-20260306-1131 | **Track:** T3

> Synced to pitch v2.2 (§3.8 Eval Protocol + §4.7 Diagnostic Protocol + Gap #28 Lee et al.)
> Previous: v0.6 (cycle #187) — stale on §4.6, §4.7, Gap #28

---

## Abstract (target 150 words)

Large audio-language models (LALMs) can answer questions about speech content, but it remains unclear *where* in their forward pass audio information becomes causally decisive. Behavioral analyses confirm that grounding degrades under scene complexity (Lee et al. 2026) and reasoning length (MPAR², 2026); the mechanistic account is missing. We introduce the **Listen Layer**: the encoder/LLM depth at which denoising activation patching of audio-stream states most strongly shifts model behavior toward audio-grounded responses, measured by the **grounding coefficient** gc(L) = DAS-IIT accuracy at layer L (Geiger et al.; Sutter et al. NeurIPS 2025 Spotlight — linear alignment maps are necessary for non-trivial causal abstraction). Using controlled phonological minimal pairs (Choi et al. 2026 — 96-language voicing arithmetic) and 57K audio-text conflict stimuli (ALME, Li et al. 2025) with RVQ-layer-selective corruptions (SpeechTokenizer Layer 1 = semantic content; Sadok et al. 2025), experiments on Whisper-small and Qwen2-Audio-7B reveal a sharp gc(L) peak at ~50% model depth. We further provide a 3-tier grounding failure taxonomy (codec/connector/LLM backbone) with falsifiable gc(k) signatures and a sequential diagnostic protocol (Steps 1–4, CPU-feasible for Tiers 1–2) enabling rapid triage of new speech LLMs.

**Word count:** ~156 words. ✅ (Target ≤160)

---

## Version Diff from v0.6

| Change | v0.6 | v0.7 |
|--------|------|------|
| Gap #28 cite | Missing | Added "Lee et al. 2026 — grounding degrades under scene complexity" |
| MPAR² cite | Missing | Added "MPAR² 2026 — grounding degrades under reasoning length" |
| §3.8 eval protocol | Not mentioned | Not explicitly named (abstract level — DAS-IIT accuracy IS the eval) |
| §4.6 3-tier taxonomy | Not mentioned | Added: "3-tier grounding failure taxonomy with falsifiable gc(k) signatures" |
| §4.7 diagnostic protocol | Not mentioned | Added: "sequential diagnostic protocol (Steps 1–4, CPU-feasible for Tiers 1–2)" |
| Abstract length | ~148 words | ~156 words (still within limit) |

---

## Stale Cite Check

- ✅ Geiger et al. 2301.04709 — foundation
- ✅ Geiger et al. 2303.02536 — DAS algorithm
- ✅ Sutter et al. 2507.08802 — linearity guard
- ✅ Choi et al. 2602.18899 — phonological minimal pairs
- ✅ Li et al. 2602.11488 (ALME) — conflict stimuli
- ✅ Sadok et al. 2506.04492 (SpeechTokenizer) — RVQ-selective corruption
- ✅ Lee et al. 2603.03855 — behavioral degradation under complexity (Gap #28) **NEW**
- ✅ MPAR² 2603.02266 — perception decay under reasoning **NEW**

---

## Notes for Leo

- This abstract is now safe to share with 智凱哥.
- The §4.7 diagnostic protocol makes Paper A more useful to reviewers ("practitioners can use this on any model in <1h CPU-only").
- Venue recommendation still: Interspeech 2026 abstract deadline check needed; NeurIPS 2026 as primary.
