# LALM-KE Synthesis Notes
> Bot-maintained: updated after each reading session
> Format: running synthesis, newest at top

---

## 2026-03-24 — Field Initialized

**Status:** Survey phase started. No papers read yet.

**Initial framing:**
The field of LALM Knowledge Editing sits at the intersection of two mature-but-separate areas:
1. Knowledge Editing for LLMs (2021-present; ROME, MEMIT, MEND, SERAC, GRACE, IKE)
2. Large Audio Language Models (2023-present; SALMONN, Qwen-Audio, WavLLM, SpeechGPT)

No paper has systematically studied KE in audio-conditioned LLMs as of 2026-03-24 (needs verification via literature search).

**Closest work:** KE in vision-language models (Cheng et al. 2023, "Can We Edit Multimodal LLMs?") — must read first.

**Key open question to verify this week:**
Has anyone done LALM-KE already? Search: "knowledge editing" + ("audio" OR "speech" OR "SALMONN" OR "Qwen-Audio")

**Hypothesis to test (experiment #1):**
ROME/MEMIT work on the LLM backbone of SALMONN for text-queried edits, but reliability drops when the *same query* is delivered via audio input due to modality gap in the bridge/encoder.

---
<!-- Bot will prepend new synthesis entries here after each reading session -->
