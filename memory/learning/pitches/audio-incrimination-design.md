# Audio Jailbreak Incrimination Design
*Track T5 — Listen-Layer Audit (Paper C / MATS)*
*Created: 2026-03-07 | Q062*

**Framing:** Following Nanda's "model incrimination" heuristic — each experiment should have a clear prosecutorial intent (we know what crime we're looking for) and an investigative surprise possibility (the model might be innocent in an unexpected way). gc(k) serves as the causal intervention probe.

---

## Experiment 1: Acoustic Jailbreak Activates Listen-Layer Features

**Intent (crime we suspect):** Safety-violating audio instructions bypass the model's refusal circuits by exploiting the acoustic processing stage — the model "guesses" the command rather than "listening" to the semantic content, causing safety-relevant tokens to be decoded outside the supervised text pathway.

**Hypothesis:** gc(k) diverges (high) on jailbreak audio vs. benign audio at the listen-layer boundary, indicating the model processes jailbreak inputs via a different mechanistic route.

**Method:**
- Input: 50 benign speech + 50 audio jailbreak prompts (GCG-audio or PAIR-audio)
- Hook activations at listen-layer boundary (detected via gc(k) inflection point)
- Measure gc(k) divergence score per input
- Prediction: jailbreak inputs cluster in high-gc(k) region

**Investigative surprise:** If jailbreak inputs show *low* gc(k) (highly semantically integrated), then the safety failure is not at the acoustic boundary but deeper in the LLM — incriminating the text-token reasoning stage, not audio encoding.

---

## Experiment 2: Causal Intervention via gc(k) Steering Ablates Jailbreak Compliance

**Intent (crime we suspect):** The listen-layer boundary is causally necessary for jailbreak compliance — patching activations at this boundary should disrupt the harmful output even if the acoustic input is adversarial.

**Hypothesis:** Causal patching of gc(k)-identified features (replacing listen-layer activations with benign-condition means) reduces jailbreak compliance rate by ≥40%.

**Method:**
- Identify top-k listen-layer features via gc(k) probe
- Run activation patching (benign mean → injected into jailbreak forward pass)
- Measure compliance rate before/after patching
- Control: random feature ablation (non-gc(k)-identified)

**Investigative surprise:** If random ablation is equally effective, gc(k) features are not specifically causal — the listen-layer boundary contributes via general capacity, not jailbreak-specific mechanisms. This would redirect investigation toward semantic composition layers.

---

## Experiment 3: gc(k) Probe Generalizes Across Jailbreak Families (Transfer Incrimination)

**Intent (crime we suspect):** The mechanism exploited by audio jailbreaks is a shared structural vulnerability — the listen-layer boundary is not semantically checking intent during acoustic processing, regardless of attack type.

**Hypothesis:** A gc(k)-based classifier trained on one jailbreak family (e.g., GCG-audio) transfers with ≥70% AUC to unseen families (e.g., PAIR-audio, emotional manipulation attacks).

**Method:**
- Train logistic probe on gc(k) features for Family A jailbreaks
- Evaluate zero-shot on Family B and C
- Compare to text-token-level baseline classifier
- Prediction: gc(k) probe > text-token probe on transfer (better mechanistic generalization)

**Investigative surprise:** If text-token baseline outperforms gc(k) probe on transfer, the jailbreak exploitation is in the language modeling stage rather than acoustic boundary — meaning audio jailbreaks are primarily a semantic alignment failure, not an audio perception failure.

---

## Design Rationale

All three experiments use Tier 1 CPU inference (Whisper small/medium) on synthetic or public jailbreak corpora. No GPU required for probe training or gc(k) measurement. Experiments build on each other: Exp 1 establishes the signal, Exp 2 establishes causality, Exp 3 establishes generality — a standard mechanistic interpretability triptych.

**Artifacts needed:** gc(k) eval harness (Q005), audio jailbreak sample set (~100 examples), Whisper hook infrastructure (exists in scripts/).
