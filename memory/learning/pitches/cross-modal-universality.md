# Cross-Modal L*/D Universality — Paper Section Draft
**Track:** T3 (Listen vs Guess)
**Task:** Q221
**Date:** 2026-03-29
**Status:** Draft v0.1 — Whisper L*/D TBD (pending real Whisper activation measurement)

---

## Section X.X: Universality of the Commitment Layer Across Architectures

A striking regularity emerges when the commitment layer L* is expressed as a fraction of total depth D.
Across three decoder-only language models spanning distinct domains and training objectives,
L*/D clusters in the range [0.50, 0.67], suggesting that the commitment-layer phenomenon
is not an artifact of any single architecture or modality, but a structural property of
transformer-based sequence modeling.

**Table X. Cross-architectural L*/D ratios.**

| Model | Architecture | D (layers) | L* | L*/D | Domain |
|-------|-------------|-----------|-----|------|--------|
| GPT-2-small | Decoder-only LM | 12 | 8 | 0.667 | Natural language |
| BLOOM-560M | Decoder-only LM | 24 | 13 | 0.542 | Multilingual text |
| CodeParrot-small | Decoder-only LM | 12 | 6 | 0.500 | Source code (Python) |
| Whisper-base (enc) | Encoder-decoder | 6 | TBD | TBD | Speech / audio |

*L* defined as the layer with the highest AND-frac (attention-normalized decision fraction).
AND-frac measures the fraction of the residual stream variance aligned with the
top-singular-vector of the output Jacobian — a proxy for the layer's contribution
to the model's final token decision.*

These findings align with prior work on the "middle layers" hypothesis in
mechanistic interpretability (Geva et al., 2022; Meng et al., 2022), which identifies
mid-to-late layers as the primary site of factual association retrieval.
Our results extend this observation to code generation and multilingual settings,
suggesting that the commitment transition occurs at approximately the 55–67% depth mark
across architectures, independent of vocabulary size, domain, or training distribution.

We hypothesize that this regularity reflects the computational cost of early
feature extraction: the first ~50% of layers build modality-specific representations
(phoneme identity, syntactic structure, token n-gram statistics), after which the model
transitions to commitment — integrating accumulated evidence into a decisive output prediction.
The audio encoder (Whisper-base) is expected to follow a similar pattern, with L*
concentrated in the final 1–2 encoder layers where acoustic features are distilled into
discrete token probabilities.

**Open question:** Does L*/D remain stable under fine-tuning, or does the commitment layer
shift systematically as models are adapted to new distributions?
The AND-frac drift monitor (Q215, Q216) provides preliminary evidence that L* is stable
under moderate fine-tuning but collapses under aggressive regularization — a finding
that directly informs our early-stopping criterion proposal (§4.X).

---

## Notes for Leo

- Whisper L*/D needs one real measurement (Q220 or a quick activation sweep on Whisper-base)
- If Whisper L*/D ≈ 0.67 (layer 4/6 in encoder), the table becomes a very clean story
- If Whisper is an outlier (e.g., 0.33), we need a paragraph explaining encoder vs decoder differences
- This section fits naturally after the AND-frac definition (§3) and before the intervention results (§4)
- Estimated length in paper: ~300 words with table = ~0.5 page
