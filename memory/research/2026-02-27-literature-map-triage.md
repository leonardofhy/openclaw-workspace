# 2026-02-27 Literature Map Triage (Speech LLM MI)

Source: `memory/research/2026-02-27-gpt52pro-literature-map.md`

## Top-5 deep reads (for immediate paper shaping)

1. **#19 Toward Best Practices of Activation Patching (ICLR 2024)**
   - Why first: establishes robust protocol + pitfalls; prevents invalid causal claims.
2. **#1 AudioSAE (2026)**
   - Why: strongest speech-native SAE evidence with intervention hooks.
3. **#2 AR&D (2026)**
   - Why: practical concept retrieval/naming pipeline for AudioLLM features.
4. **#14 Multi-Modal Causal Tracing (NeurIPS 2024)**
   - Why: reusable causal tracing frame; can be adapted from vision-text to audio-text.
5. **#8 SPIRIT (EMNLP 2025)**
   - Why: demonstrates inference-time activation patching utility for safety robustness.

## Candidate paper gap (current best)

- **Alignment-aware causal tracing for speech LLMs**:
  - handle time/token alignment explicitly (CTC/attention/DTW variants)
  - validate with feature -> circuit -> behavior chain
  - report necessity/sufficiency + random controls + causal scrubbing

## Immediate next actions

- [ ] Build citation sanity sheet (claim -> source sentence -> confidence)
- [ ] Draft Related Work skeleton with 5 clusters: Causal / Patching / SAE / Grounding / Alignment
- [ ] Lock first experiment on DeSTA (+ one comparator)
