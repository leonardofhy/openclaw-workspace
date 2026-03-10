# Paper A — Figure 2 Draft
**Track:** T3 (Listen vs Guess)
**Task:** Q046
**Version:** v0.1 | **Date:** 2026-03-06

---

## Title
**Figure 2: Connector Phonological Arithmetic — Does Linear Phonological Geometry Survive the Modality Interface?**

---

## Conceptual Diagram (ASCII)

```
SPEECH ENCODER (Whisper-small)
─────────────────────────────────────────────────────────────────
Input frames:  [d]        [t]        [b]        [p]
               ↓          ↓          ↓          ↓
Encoder layer 0-5 (Whisper)

              h_enc([d])  h_enc([t])  h_enc([b])  h_enc([p])

Phonological arithmetic in encoder space:
   voicing_vector = h_enc([d]) − h_enc([t])
   ✓ CHECK: h_enc([b]) + voicing_vector ≈ h_enc([d])?  (VOT minimal pair)

                          ↓  CONNECTOR  ↓
                   (linear projection W_conn ∈ R^{d_enc × d_llm})

SPEECH-LLM RESIDUAL STREAM (Qwen2-Audio / SALMONN)
─────────────────────────────────────────────────────────────────
              h_llm([d])  h_llm([t])  h_llm([b])  h_llm([p])

Phonological arithmetic in LLM space:
   voicing_vector_LLM = h_llm([d]) − h_llm([t])
   ✓ CHECK: h_llm([b]) + voicing_vector_LLM ≈ h_llm([d])?

Three possible outcomes (Panel B):
   ─────────────────────────────────────────
   Outcome A: Linear phonological geometry PRESERVED
     cos(projected_voicing, h_llm([d]) − h_llm([t])) ≈ 1.0
     → Connector = lossless modality bridge
     → "Listen" regime: LLM has direct phonological access

   Outcome B: Geometry COLLAPSED
     cos(projected_voicing, h_llm([d]) − h_llm([t])) ≈ 0.0
     → Connector = modality bottleneck (Gap #14: Modality Collapse)
     → "Guess" regime: LLM cannot access phonological distinctions

   Outcome C: Partial preservation
     0.2 < cos < 0.8
     → Connector = soft gate; which features survive ↔ gc(k) profile
```

---

## Panel Layout (for LaTeX)

```
┌──────────────────────┬─────────────────────────────────────┐
│      Panel A         │            Panel B                  │
│  Architecture        │    Phonological Geometry Test       │
│                      │                                     │
│  [d] [t] [b] [p]     │  1.0 ─ ─ ─ ─ ─ ─ ─ ─ ─  Outcome A│
│       ↓              │                                     │
│   Whisper enc        │  cos │   ·──────────────────       │
│       ↓              │      │  /                          │
│   CONNECTOR          │  0.5 │ /   Outcome C               │
│       ↓              │      │                             │
│  LLM residual        │  0.0 ─ ─ ─ ─ ─ ─ ─ ─ ─  Outcome B│
│                      │       Layer 0   Layer 5            │
│  arithmetic check    │       (Encoder)  (LLM)             │
│  at each stage       │                                     │
└──────────────────────┴─────────────────────────────────────┘
```

**Caption (draft):**
> **Figure 2: Connector phonological arithmetic test.**
> *(Panel A)* We extract representation vectors for minimal phoneme pairs ([d]/[t], [b]/[p]) at each stage of a speech-LLM pipeline: the Whisper encoder, the cross-modal connector, and the LLM residual stream. We test whether the voicing vector `v = h([d]) − h([t])` satisfies phonological arithmetic `h([b]) + v ≈ h([d])` at each stage (cosine similarity, following Choi et al. 2025). *(Panel B)* Three predicted outcomes: (A) preserved geometry indicates the connector acts as a lossless bridge; (B) collapsed geometry indicates a modality bottleneck where phonological structure is destroyed at the connector; (C) partial preservation defines a soft gate whose per-layer profile matches the gc(k) curve from Figure 1.

---

## LaTeX Code (Figure Placeholder)

```latex
\begin{figure}[t]
  \centering
  \begin{subfigure}[t]{0.45\textwidth}
    \centering
    % TODO: replace with actual architecture diagram
    \includegraphics[width=\textwidth]{figures/fig2a_connector_arch.pdf}
    \caption{Pipeline stages: encoder, connector, LLM residual stream.}
    \label{fig:fig2a}
  \end{subfigure}
  \hfill
  \begin{subfigure}[t]{0.50\textwidth}
    \centering
    % TODO: replace with actual cosine similarity curves when experiment runs
    \includegraphics[width=\textwidth]{figures/fig2b_phonological_geometry.pdf}
    \caption{Voicing vector cosine similarity across pipeline stages.}
    \label{fig:fig2b}
  \end{subfigure}
  \caption{
    \textbf{Connector phonological arithmetic test.}
    We test whether voicing direction $\mathbf{v} = \mathbf{h}([\text{d}]) - \mathbf{h}([\text{t}])$,
    confirmed linear in speech encoder representations~\cite{choi2025phonological},
    survives projection through the connector into the LLM residual stream.
    Outcome A (preserved, $\cos \approx 1$) supports direct phonological access;
    Outcome B (collapsed, $\cos \approx 0$) supports modality bottleneck~\cite{zhao2025modality};
    Outcome C (partial) predicts a gc(k) soft-gate signature.
    Full experiment: see Appendix~\ref{app:phonological-geometry}.
  }
  \label{fig:connector-arithmetic}
\end{figure}
```

---

## Connection to Paper A Narrative

- **§1 (Introduction)**: Figure 2 motivates WHY the connector is the critical stage — the Listen Layer transition may coincide with where phonological geometry collapses.
- **§2 (Related Work)**: Cite Choi et al. 2602.18899 (linear phonological geometry in S3M encoders); Zhao et al. 2602.23136 (modality collapse).
- **§3 (Method)**: Figure 2 = visualization of Step 3 in the experiment spec (Gap #18 phonological geometry test). The voicing_vector arithmetic is the *geometric prerequisite check* before running the full IIT/DAS experiment (Q001/Q002).
- **§4 (Results)**: Panel B will be filled from Q001 experiment (currently blocked on real speech .wav + Leo approval).

---

## Prediction for Experiment (Q001)

Based on prior work:
- **Encoder layers 0-5** (Whisper): voicing arithmetic expected to hold (cos > 0.85), consistent with Choi et al.
- **After connector**: expect degradation (cos drops). DeSTA2/Qwen2-Audio connectors are linear projections → affine transformations *preserve* cosine similarity in theory, but if the connector also compresses/rotates the space (e.g., via learned gates), phonological geometry may be distorted.
- **Predicted null result**: if affine-only connector, cos stays high → phonological geometry survives → motivates DAS experiment (Q002) to check if LLM *uses* this information.
- **Predicted positive result (gap-confirming)**: if cos drops, connector = gap for Paper A §4 and AudioSAEBench Category 0 (Audio-RAVEL).

---

## Status
- [x] ASCII diagram complete
- [x] Panel layout specified
- [x] Caption draft ready
- [x] LaTeX placeholder ready
- [ ] Actual figures: BLOCKED on Q001 (real speech .wav + Leo approval)
- Next: When Q001 unblocked, fill figures from `whisper_hook_demo.py` output
