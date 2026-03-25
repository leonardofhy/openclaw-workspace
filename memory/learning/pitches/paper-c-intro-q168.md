# Paper C — Introduction v1.0 (~800 words)
**Task:** Q168 | **Track:** T5 (Listen-Layer Audit / Audio Jailbreak)
**Date:** 2026-03-25 | **Status:** DRAFT v1.0

---

## §1 Introduction (~800 words, LaTeX-ready)

Audio-language models (ALMs) have expanded the attack surface for adversarial inputs beyond
the text domain. Where text jailbreaks exploit linguistic structure — token-level injections,
role-play framings, encoded instructions — audio jailbreaks exploit the model's acoustic
processing stage: commands buried in prosody, phoneme-level adversarial perturbations, and
audio-text conflict injections that direct model behaviour via the audio channel while a benign
text context suppresses refusal. These attacks are qualitatively distinct from their text
counterparts, yet current defences treat them as instances of the same problem, applying
surface-level classifiers trained on audio features or text-token perplexity scores. The
fundamental limitation of this approach is that it ignores the model's \emph{internal}
processing: a defence built on output behaviour or raw acoustic features cannot tell whether
a given audio input caused the model to consult its acoustic evidence at all.

\paragraph{The Gap: Model Internals Are Unexploited.}
Three recent results establish the severity of the problem. The SPIRIT benchmark
\citep{spirit2025} demonstrates that attention-based anomaly detectors require labelled attack
examples at training time and fail to transfer to novel attack paradigms —
adversaries can craft audio that mimics benign attention patterns while preserving the
jailbreak goal. ALMGuard \citep{almguard2025neurips} locates safety shortcut features in the
final layers of the ALM backbone, achieving state-of-the-art detection on seen attacks but
showing 30–40\% AUC degradation on held-out attack families. SALMONN-Guard
\citep{liang2025salmonn} applies a secondary LLM as output classifier and provides strong
empirical results on JALMBench \citep{jalmbench2026}, yet it is trivially evadable by attacks
that encode harmful intent in acoustic prosody while keeping the decoded text benign — a known
failure mode documented in JALMBench Category III (prosodic embedding attacks).
The shared limitation: all prior methods observe the model from \emph{outside}. No existing
defence asks the mechanistic question — \emph{did this audio input alter the model's internal
causal processing in the way a jailbreak attack must?}

\paragraph{Our Approach: Listen-Layer Audit.}
We exploit the \textbf{Listen Layer} structure identified in Paper A
\citep{chen2026listenlayer} to build a zero-shot, attack-agnostic jailbreak detector. Paper A
introduces the \textbf{grounding coefficient} $\text{gc}(L)$: the interchange-intervention
accuracy (IIA) of a learned linear alignment at layer $L$, measuring whether the audio-stream
state at $L$ is causally decisive for model output. The gc$(L)$ profile peaks sharply at a
characteristic depth $L^* \approx 0.5 \times$ model depth — the \emph{Listen Layer} — and
decays thereafter. This peak is an internal signature of healthy audio consultation: when the
model \emph{listens}, gc$(L^*)$ is high; when it \emph{guesses} from linguistic priors, gc$(L^*)$
collapses.

Our central hypothesis is that audio jailbreak attacks systematically perturb the gc$(L)$
profile. A jailbreak must route malicious content through the model's acoustic processing stage
without triggering safety circuits tuned on text-domain patterns. This requires either
\emph{suppressing} normal listen-layer consultation (low gc$(L^*)$, the model never properly
encodes the acoustic content) or \emph{hijacking} it (anomalous cross-layer coupling, the
listen-layer subspace is activated by non-linguistic acoustic features). Both scenarios
produce a measurable deviation from the benign-audio gc$(L)$ baseline. The key insight is that
an adversary cannot simultaneously (1) preserve a normal-looking gc$(L)$ profile — which
requires the model to faithfully process the acoustic signal — and (2) achieve a jailbreak
outcome, which requires circumventing the aligned reasoning pathway. These are conflicting
objectives, making gc$(L)$-based detection inherently adversarially robust by design.

\paragraph{The Listen-Layer Audit.}
We operationalise this hypothesis as a two-stage procedure. First, we compute a benign
gc$(L)$ baseline from clean, labelled speech inputs. Second, at inference time, we estimate
$\hat{\text{gc}}(L^*)$ for the incoming audio query and compute an \textbf{anomaly score}
$\delta = |\hat{\text{gc}}(L^*) - \bar{\text{gc}}(L^*)|$ relative to the benign baseline. Inputs
with $\delta > \tau$ are flagged as potential jailbreak attempts. The threshold $\tau$ is
calibrated on the benign validation split; no attack examples are used in calibration.
The baseline is constructed entirely from clean data — making the detector zero-shot with
respect to attack types.

\paragraph{Contributions.}
This paper makes three contributions:
\begin{enumerate}
  \item \textbf{Listen-Layer Audit}: a mechanistic jailbreak detector based on gc$(L)$
    anomaly scoring, requiring no attack examples and providing attack-agnostic detection
    with a theoretical adversarial robustness argument grounded in the conflicting-objectives
    structure of jailbreak attacks.
  \item \textbf{JALMBench Evaluation}: systematic evaluation on JALMBench's 246-query
    standardised benchmark across all four attack families (prosodic embedding, audio-text
    conflict, phoneme-level adversarial, and indirect jailbreak), with ablations isolating
    the contribution of listen-layer vs. last-layer features.
  \item \textbf{Pre-deployment Risk Screening}: a second application of gc$(L)$ as a
    pre-deployment audit tool — models with low $\overline{\text{gc}}(L^*)$ on benign speech
    are more vulnerable to audio emergent misalignment after fine-tuning, enabling risk
    stratification before deployment without requiring adversarial test cases.
\end{enumerate}

---

## Word count estimate: ~790 words

## Notes for v1.1
- Need to add 2026 citation keys for JALMBench, SPIRIT, ALMGuard once BibTeX confirmed
- §1 could expand the "conflicting objectives" argument with 1 equation (delta formulation)
- Consider adding a figure-pointer sentence: "Figure 1 shows the gc(L) profile shift..."
- Cross-reference Paper A intro §1 to avoid duplication on Listen Layer background
