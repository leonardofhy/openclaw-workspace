# Paper Reading List (Leo)

Last updated: 2026-02-27
Purpose: shared list for quick-scan candidates, deep-read queue, and completed reads.

## A) Quick-scan queue (Triage)
- (empty)

## B) Deep-read queue (High priority)
(empty)

## C) Completed deep reads (selected)
- **Maghsoudi & Mishra 2602.01247** (2026) — Brain-to-speech MI: compact layer-specific causal subspaces mediate cross-mode transfer; continuous shared manifold; direction asymmetry (vocalized→imagined recovers, reverse catastrophic). Cited in Paper A §2.2. Gap #32 candidate: do analogous compact subspaces exist in audio-LLMs? Cycle c-20260311-1215.
- Geiger et al. — Causal Abstraction / IIT foundations
- Lin (2025) — Multimodal MI Survey
- Zhao et al. (2601.03115) — Emotion-sensitive neurons in LALMs
- Kawamura (2602.15307) — AAPE neuron dissection
- Mariotte (2509.24793) — Temporal SAE limitations

## C2) Deep reads completed week of Feb 26 – Mar 2 (autodidact cycles #6-#181)
Last updated: 2026-03-02 cycle #182

| Paper | arXiv | Cycle | Key output |
|-------|-------|-------|-----------|
| Glazer "Beyond Transcription" (2025) | 2508.15882 | #6 | Encoder Lens, hallucination from residual stream, saturation layer |
| AudioLens (NTU, ASRU 2025) | (lab-internal) | #7 | Logit Lens on LALMs, critical layer +16.3%, Gap #3 (no causal patching) |
| AudioSAE v1 (2026, EACL) | 2602.05027 | #8 | SAE all-12-layers, layer 6-7 transition, 70% hallucination FPR reduction |
| Kawamura / AAPE (2026) | 2602.15307 | #26 | Class-specific neurons in SSL, necessity patching, Gap #11 |
| Mariotte et al. (Sep 2025, ICASSP 2026) | 2509.24793 | #27 | Temporal mean-pooled = Gap #12, completeness metric |
| Zhao et al. (2601.03115) | 2601.03115 | #28 | ESNs in LALMs, emotion-sensitive SwiGLU neurons |
| UniWhisper (2026) | (scan) | #1 | 20-task eval, MLP probe NWA, benchmark design |
| pyvene / NNsight (docs) | (skill-up) | #9 | Patching tool selection: pyvene for audio, TL = decoder-only |
| SAEBench (Karvonen, Nanda et al. ICML 2025) | cycle #38 | #38 | 8-metric evaluation, Matryoshka SAE wins, proxy ≠ quality, AudioSAEBench template |
| Choi et al. "Phonological Vector Arithmetic" | 2602.18899 | #81 | Phonological linearity/compositionality in 96 langs; Gap #18 |
| Bhalla T-SAE (ICLR 2026 Oral) | 2511.05541 | #72 | Temporal contrastive SAE; Gap #17, Paper Idea #7 |
| Zhao et al. "Modality Collapse" | 2602.23136 | ~#83 | LALMs default to text even when audio conflicts; Gap #14 |
| ALME conflict benchmark (Li et al.) | 2602.11488 | ~#90 | 57K audio-text conflict pairs; gc(F) stimuli source |
| Sadok et al. "Codec Probe" (Interspeech 2025) | 2506.04492 | #163 | RVQ Layer 1 = semantic, 2+ = acoustic; Gap #21 codec causal patching |
| DashengTokenizer (2026) | 2602.23765 | #167 | 1 semantic layer sufficient for 22 audio tasks; supports Listen Layer Hypothesis |
| FAD encoder bias / Gui et al. (Interspeech 2026) | 2602.23958 | #167 | Whisper biased toward text-predictable; motivates multi-model AudioSAEBench |
| Heimersheim & Nanda patching best practices (2024) | (lesswrong) | #178 | AND/OR gate, denoising preference, Hydra 0.7x, AtP, top-k aggregate |
| RAVEL (Huang et al., ACL 2024) | (ACL 2024) | #179 | Cause/Isolate two-score, MDAS SOTA, SAEs fail isolation; Gap #23 = Audio-RAVEL |
| AudioSAE full re-read (Aparin et al. 2026) | 2602.05027 | #177 | 50% feature stability, cross-seed consistency, Gap #22 causal utility vs consistency |
| SPIRIT (Djanibekov et al., EMNLP 2025) | 2505.13541 | #181 | 100% ASR via PGD waveform, 99% robustness via patching, Gap #24 SAE-guided defense |

## D) Candidate paper angles from current synthesis
- Listen Layer Hypothesis (Track 3)
- Thinker–Talker emotional bottleneck (Gap #13)
- Class-specific Neuron Grounding
- Temporal Audio SAE

## Update protocol (for Autodidact cycles)
1. New paper found → add to A) with one-line reason.
2. If worth deep read → move to B).
3. After deep read → move to C) with 1-line takeaway.
4. If it creates a new gap/idea → append to D) and knowledge-graph.
