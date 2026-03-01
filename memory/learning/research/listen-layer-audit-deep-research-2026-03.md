## Interpreting your direction (so the comparisons are fair)

I’m going to interpret **“Safety-Critical Listen-Layer Audit for speech LLMs via gc(k)”** as:

* **Listen-layer audit:** instrument the **audio front-end** (audio encoder + audio→token projector / adapter) of a speech/audio-language model and **measure safety-relevant signals before the text decoder produces an answer**.
* **gc(k):** a **layer-indexed safety score** at layer *k* (e.g., **gradient-based** “safety-critical gradient/cosine” score per layer, or a **lightweight guard classifier/probe** applied to layer-*k* hidden states).
  If you meant a different gc(k), the closest-paper set below will still be relevant (audio jailbreak + mechanistic/guardrail methods), but the MVP details would shift slightly.

---

## 1) Top-8 closest papers (last 12 months) + overlap matrix

### Legend for overlap matrix (0–3)

* **Question overlap:** Does it ask essentially the same research question?
* **Method overlap:** Does it use a similar *mechanistic / layer-wise / gradient / probe* approach?
* **Output overlap:** Does it produce similar artifacts (layer-localized safety signal, auditors/guards, intervention points), not just “a benchmark”?

0 = none, 1 = low, 2 = medium, 3 = high.

### Overlap matrix (paper ↔ your proposed direction)

|  # | Paper (≈ date/venue)                                              | Question overlap | Method overlap | Output overlap |
| -: | ----------------------------------------------------------------- | :--------------: | :------------: | :------------: |
|  1 | **JALMBench** (ICLR 2026 poster; Jan–Feb 2026)                    |         2        |        1       |        2       |
|  2 | **AJailBench / Audio Jailbreak benchmark** (arXiv; May 2025)      |         2        |        1       |        2       |
|  3 | **AudioJailbreak** (TDSC-accepted; May 2025 / rev Feb 2026)       |         2        |        1       |        1       |
|  4 | **Multi-AudioJail** (arXiv; Apr 2025)                             |         2        |        1       |        1       |
|  5 | **SPIRIT** (EMNLP 2025)                                           |         3        |        3       |        2       |
|  6 | **ALMGuard** (NeurIPS 2025 poster)                                |         3        |        2       |        2       |
|  7 | **SACRED-Bench + SALMONN-Guard** (arXiv; Nov 2025 / rev Feb 2026) |         3        |        2       |        3       |
|  8 | **LALM-as-a-Judge** (arXiv; Feb 2026)                             |         3        |       1–2      |       2–3      |

Below I summarize why each is “closest” and where it diverges from your listen-layer + gc(k) audit framing.

---

### 1) JALMBench: Benchmarking Jailbreak Vulnerabilities in Audio Language Models (ICLR 2026 Poster)

* **What it overlaps:** Strongly overlaps on **threat model + evaluation target**: jailbreak risk for audio-language models, multiple attack families, and defense assessment at scale.
* **Key details:** Introduces a benchmark with **11,316 text samples and 245,355 audio samples (>1,000 hours)**; supports **12 LALMs, 8 attack methods, and 5 defenses**, and reports that general-purpose moderation yields only modest gains, pushing toward **LALM-specific defenses**. ([OpenReview][1])
* **Where it diverges:** It’s primarily **benchmarking**, not a mechanistic **listen-layer audit** method.

### 2) Audio Jailbreak: AJailBench + Audio Perturbation Toolkit (APT) (arXiv May 2025)

* **What it overlaps:** Overlaps on **safety-critical audio attack surface** and on needing robustness under **semantics-preserving perturbations** (the audit should remain reliable under these).
* **Key details:** Builds **AJailBench-Base** with **1,495 adversarial audio prompts** across **10 policy-violating categories**, and extends with **AJailBench-APT** via perturbations in time/frequency/amplitude while enforcing **semantic consistency** and using **Bayesian optimization** to find subtle but effective distortions. ([arXiv][2])
* **Where it diverges:** Output is **a benchmark + perturbation generator**, not a layer-local audit score—though it’s exactly what you’d want as stress tests.

### 3) AudioJailbreak: Jailbreak Attacks against End-to-End Large Audio-Language Models (TDSC accepted; rev Feb 2026)

* **What it overlaps:** Overlaps on **realistic attacker models** and on the need to defend systems where audio is the entry point.
* **Key details:** Proposes an attack emphasizing **asynchrony, universality, stealthiness, and over-the-air robustness**, and explicitly targets a **“weak adversary”** setting where the attacker can’t fully control prompts; reports effectiveness including claims of jailbreaking **GPT‑4o‑Audio** and bypassing **Llama‑Guard‑3** in that weak-adversary scenario. ([arXiv][3])
* **Where it diverges:** It’s an **attack paper**; it doesn’t directly propose a listen-layer audit. But it defines a key **evaluation regime** your auditor should handle (weak adversary + over-the-air).

### 4) Multilingual and Multi-Accent Jailbreaking of Audio LLMs (Multi-AudioJail; arXiv Apr 2025)

* **What it overlaps:** Overlaps on **cross-lingual / paralinguistic** attack surfaces—critical for any listen-layer safety audit.
* **Key details:** Introduces **Multi-AudioJail** and reports that **accent/language + acoustic effects** (reverb/echo/whisper-like) can increase jailbreak success substantially (e.g., reports up to **+57.25 pp** in some settings), and that audio-only multilingual attacks can outperform text-only by large factors. ([arXiv][4])
* **Where it diverges:** Mostly **threat characterization + dataset**, not internal auditing.

### 5) SPIRIT: Patching Speech Language Models against Jailbreak Attacks (EMNLP 2025)

* **What it overlaps:** This is the closest on **mechanistic interpretability and layer-level intervention**.
* **Key details:** Shows speech LMs can be jailbroken by **imperceptible noise**, then proposes **post-hoc inference-time defenses** that modify internal activations (activation patching, bias addition, neuron pruning), reporting robustness gains “up to **99%**” without retraining and with negligible utility loss. ([ACL Anthology][5])
* **Why it’s very close:** Your “listen-layer audit” is the *audit* side of exactly what SPIRIT begins to do (identify which internal representations are “dangerous” and alter them).

### 6) ALMGuard: Safety Shortcuts and Where to Find Them as Guardrails for Audio–Language Models (NeurIPS 2025 Poster)

* **What it overlaps:** Strong overlap on **audio-specific defenses** and “where in the pipeline” safety can be activated.
* **Key details:** Assumes safety-aligned models contain “**safety shortcuts**,” identifies **universal Shortcut Activation Perturbations (SAP)** to trigger safety behaviors, and proposes a **mel-gradient sparse mask** to constrain perturbations; reports cutting average jailbreak success to **4.6%** across four models. ([NeurIPS][6])
* **Where it diverges:** It’s an **intervention/guardrail** approach (input perturbation trigger), not a diagnostic per-layer audit—though the “shortcut localization” framing is adjacent to your goal.

### 7) Speech-Audio Compositional Attacks + SACRED-Bench + SALMONN-Guard (arXiv Nov 2025 / rev Feb 2026)

* **What it overlaps:** Very close to your “listen-layer” focus because the attacks rely on **complex auditory scenes** where harmful and benign cues co-occur—exactly where a “listen-layer auditor” should shine.
* **Key details:** Introduces **SACRED-Bench**, a **black-box** attack suite based on **speech-audio composition** (overlapping harmful+benign speech, mixing benign speech with harmful non-speech audio, multi-speaker dialogue). Reports that even with guardrails enabled, **Gemini 2.5 Pro** shows **66% attack success**, and proposes **SALMONN-Guard**, a guard model that jointly inspects **speech, audio, and text**, reducing ASR to **20%**. ([arXiv][7])
* **Why it’s very close:** The paper’s threat model explicitly targets failures of “text-only” safety cues—your approach can contribute by pinpointing *which listen layers encode the co-occurrence*.

### 8) LALM-as-a-Judge: Benchmarking Safety Evaluation Capabilities of Audio-Language Models in Multi-turn Spoken Dialogues (arXiv Feb 2026)

* **What it overlaps:** Overlaps strongly on **oversight and auditing**: using audio-language models to judge safety, and analyzing reliability dimensions.
* **Key details:** Builds a benchmark of ~**24,000 dialogues** and evaluates multiple LALMs as safety judges, emphasizing **sensitivity, specificity, and stability**; also mentions grounding evaluation in audio content-safety data sources. ([arXiv][8])
* **Where it diverges:** It’s judge-based oversight (output-level), not internal layer auditing; but it anchors what “good auditing” should measure (stability, error modes).

---

### Two “very close but not in the top-8” (still worth reading)

* **StyleBreak: Revealing Alignment Vulnerabilities in Large Audio-Language Models** (arXiv Nov 2025) — style/voice/conditioned attacks are highly relevant to listen-layer auditing. ([arXiv][9])
* **Defending speech-enabled LLMs against adversarial jailbreaks via adversarial training** (Interspeech 2025) — shows a defense path using PGD-style adversarial training, and provides a concrete speech-LLM architecture description (conformer audio encoder → downsampler → LLM). ([ISCA Archive][10])

---

## 2) Novelty verdict: **Yellow** (promising, but reviewers will demand a sharper “what’s new?”)

### Why Yellow (not Red)

Existing work is rich on:

* **Benchmarks & attacks** (AJailBench, Multi-AudioJail, AudioJailbreak, SACRED-Bench, JALMBench). ([arXiv][2])
* **Some defenses** that are audio-specific and sometimes implicitly “mechanistic” (SPIRIT’s activation patching; ALMGuard’s shortcut triggers; SALMONN-Guard’s multimodal guard). ([ACL Anthology][5])
* **Oversight/judging** for audio dialogues (LALM-as-a-Judge). ([arXiv][8])

But there is still room for a paper whose *center of gravity* is:

> “A **layer-by-layer safety audit** of the **audio encoder/listen pipeline** that yields interpretable **gc(k)** curves, identifies safety-critical subspaces/circuits, and supports oversight (monitoring + targeted intervention).”

That combination (layer-local + audit-first + speech-specific + jailbreak/scene-composition stress tests) is not yet the “main thesis” of any one paper above.

### Why not Green (what you must prove to avoid “incremental adaptation”)

A reviewer could easily say:

* “This is just applying gradient/probe-based jailbreak detection to audio” (incremental),
* “SPIRIT already shows layer-level patching; ALMGuard already finds safety shortcuts” (novelty squeezed).

To push this into **Green**, you likely need **one or two crisp new claims**, e.g.:

1. **Safety signal emergence:** the harmful-intent representation becomes linearly separable at specific audio layers **before** transcription/decoder stages, and this is stable across perturbations (reverb, accent, multi-speaker composition).
2. **Audit → intervention bridge:** gc(k) not only detects but reliably identifies **where to intervene** (patch / prune / gating) with small utility loss, improving on or complementing SPIRIT/ALMGuard/SALMONN-Guard. ([ACL Anthology][5])

---

## 3) 1-week MVP experiment plan

This MVP is designed to produce a **publishable “core figure”** quickly: a **gc(k) safety curve** across listen layers + an evaluation showing it catches real audio jailbreaks better than transcript-only heuristics.

### MVP Hypotheses (exact, testable)

Let the model have audio encoder layers (k=1..K). Let (gc(k)) be your per-layer safety score (gradient-based or probe-based). Define overall audit score (GC = \max_k gc(k)) (or a learned weighted sum).

**H1 — Layer-local separability:**
There exists a layer (k^*) such that a lightweight classifier on layer-(k^*) features (or a threshold on (gc(k^*))) detects jailbreak audio vs benign audio with:

* **AUROC ≥ 0.85** on held-out attacks, and
* **FPR ≤ 5% at TPR ≥ 90%** (choose one operating point and report it).

**H2 — Robustness to audio perturbations:**
Under semantically-preserving perturbations (e.g., AJailBench APT-like transforms), the audit score degrades by **≤ 0.05 AUROC** compared to clean audio.

**H3 — Added value over transcript-only guards:**
When the transcript is passed to a text-only safety filter (baseline), the listen-layer audit achieves **≥ +15 pp recall** at the same FPR (e.g., 1% or 5%) on at least one hard subset:

* weak-adversary / asynchronous attacks (AudioJailbreak-like), or
* compositional auditory scenes (SACRED-Bench-like). ([arXiv][3])

If you have bandwidth for a small intervention demo:

**H4 — Audit-guided mitigation (optional):**
A minimal intervention triggered by (GC) (e.g., route to SALMONN-Guard-like judge or apply SPIRIT-like patching at top-ranked layer(s)) reduces attack success rate by **≥ 30% relative** with **≤ 5% utility drop** on benign tasks. ([ACL Anthology][5])

---

### Required data format (minimal but sufficient)

Use a **JSONL manifest** + audio files.

**Audio files**

* Format: **WAV**, PCM16 (or float32), mono.
* Sample rate: whatever your model expects (store in metadata; resample in loader).

**JSONL schema (one record per example)**

```json
{
  "id": "unique_string",
  "audio_path": "relative/or/absolute/path.wav",
  "sample_rate": 16000,
  "split": "train|dev|test",
  "label": "benign|jailbreak",
  "policy_category": "optional_string",
  "attack_family": "none|tts_transfer|apt_perturb|async_suffix|composition|multilingual_accent|over_the_air",
  "language": "en|es|... (optional)",
  "accent": "optional",
  "transcript": "optional (if you have ASR or ground truth)",
  "prompt_text": "optional (if your model also takes text)",
  "notes": "optional"
}
```

**Where to source quickly (no new collection needed)**

* **Jailbreak audio:** Start with **AJailBench-Base (1,495 samples)** and optionally their perturbation variants. ([arXiv][2])
* **Hard subsets:** Add a small slice of **composition attacks** (SACRED-Bench) and/or **weak-adversary** style attacks if accessible. ([arXiv][7])
* **Benign audio:** Use any public speech dataset or TTS benign prompts; ensure diversity of speakers to avoid “TTS artifact detection.”

---

### Metrics

**Detection / auditing**

* AUROC, AUPRC
* FPR@TPR (e.g., FPR at 90% TPR; and TPR at 1% FPR)
* Calibration: ECE or Brier score (optional but reviewer-friendly)

**Layer diagnostics (the “mechanistic” part)**

* (gc(k)) curve across layers: mean ± CI per class
* “Earliest reliable layer”: smallest k where AUROC(k) ≥ 0.80
* Stability across perturbations: correlation of (gc(k)) ranks between clean and perturbed

**Attack outcome linkage**

* Correlation between audit score (GC) and actual **attack success rate** of the model (per attack family), especially for composition attacks where text prompt alone looks benign. ([arXiv][7])

**If doing intervention**

* Attack Success Rate (ASR) after mitigation (SACRED reports ASR numbers; use same idea) ([arXiv][7])
* Utility: task accuracy / WER / answer quality on benign prompts (SPIRIT reports “negligible utility loss” and uses standard utility checks—mirror that framing). ([ACL Anthology][5])

---

### Failure criteria (so the MVP is falsifiable)

Call the MVP a failure (and pivot) if any of these happen:

1. **No layer signal:** For all k, AUROC(k) < 0.75 on held-out attacks.
2. **Not robust:** AUROC drop > 0.10 under perturbations (clean → perturbed).
3. **No incremental value:** Audit does not beat transcript-only baseline by at least **+5 pp** recall at fixed FPR on *any* hard subset.
4. **Operationally too slow:** Computing gc(k) requires >2× realtime per sample on a single GPU (for an audit tool you might tolerate more, but reviewers will ask).
5. **Overfits artifacts:** Performance collapses when you swap voices / accents (Multi-AudioJail style shift). ([arXiv][4])

---

### 7-day execution schedule (practical MVP)

**Day 1 — Setup + baselines**

* Choose an open model where you can access internal activations (e.g., speech/audio LLM used in prior defense work).
* Baselines:

  * transcript-only safety filter (ASR → text safety model)
  * output-based refusal rate (does model refuse)
* Prepare AJailBench subset + benign subset. ([arXiv][2])

**Day 2 — Implement listen-layer feature extraction**

* For each layer k in the audio encoder (and optionally adapter):

  * extract hidden states
  * pool to fixed vector (mean/max over time, or attention pooling)
* Save features to disk for fast iteration.

**Day 3 — Implement gc(k) (two variants)**

* Variant A (probe): train logistic regression / linear probe per layer k on small training set.
* Variant B (gradient-style): compute a per-layer gradient signature for a fixed target behavior tokenization (careful: this is compute-heavy; keep few-shot).

**Day 4 — Robustness suite**

* Evaluate on:

  * clean vs perturbed (AJailBench perturbation variants if available) ([arXiv][2])
  * multilingual/accent shift if you have it (Multi-AudioJail slice) ([arXiv][4])
  * composition attacks slice (SACRED-Bench) ([arXiv][7])

**Day 5 — Mechanistic readout**

* Produce the “main figure”:

  * AUROC(k) vs layer k
  * gc(k) distributions by class
  * identify top-1 / top-3 layers, and which attack families spike where

**Day 6 — (Optional) Small mitigation demo**

* If (GC > \tau):

  * route to stricter guard/judge (e.g., multimodal guard model conceptually like SALMONN-Guard), or
  * do a single SPIRIT-style activation patch at the most predictive layer. ([arXiv][7])
* Measure ASR reduction + utility drop.

**Day 7 — Write-up + reviewer-proofing**

* Summarize:

  * which layers carry safety signal
  * which attacks bypass transcript-only
  * how stable gc(k) is under perturbations
* Add ablations:

  * pooling method
  * number of training examples for probes (few-shot curve)
  * model size if possible

---

## 4) Reviewer-style top-5 objections + rebuttal suggestions

### Objection 1: “This is just adapting existing jailbreak detection (or probing) to audio.”

**Why they’ll say it:** The field already has benchmarks (AJailBench/JALMBench) and defenses (SPIRIT/ALMGuard/SALMONN-Guard). ([arXiv][2])
**Rebuttal:** Make the contribution *mechanistic + speech-specific*:

* Show **where** safety-relevant information appears in the audio pipeline (layer emergence).
* Show **mismatch**: transcript-only looks benign but listen-layer flags risk (especially SACRED’s “implicit reference” design). ([arXiv][7])
* Provide a **causal intervention**: patch/prune the implicated layer(s) to reduce jailbreak success (even a tiny demo helps).

### Objection 2: “White-box gradients/activations aren’t available for proprietary models.”

**Rebuttal options:**

* Position as a **developer/regulator audit tool** for pre-deployment evaluation (white-box is reasonable there).
* Add a **distillation path**: train a small external auditor that mimics gc(k) using only embeddings or shallow features, then evaluate black-box transfer.
* Use benchmarks that already evaluate proprietary systems at the behavior level (SACRED reports Gemini numbers; your audit can be validated on open models and *then* behavior-validated on closed). ([arXiv][7])

### Objection 3: “Your detector is learning dataset artifacts (TTS voices, perturbation signatures), not ‘safety intent’.”

**Rebuttal:**

* Explicitly test **voice diversity** (JALMBench emphasizes it) and accent/language shift (Multi-AudioJail). ([OpenReview][1])
* Hold out speakers/voices entirely.
* Include over-the-air / reverberation shifts (AudioJailbreak explicitly targets over-the-air robustness). ([arXiv][3])

### Objection 4: “Adaptive attackers will evade your gc(k) auditor.”

**Rebuttal:**

* Evaluate against the most relevant adaptive families:

  * asynchronous/weak-adversary settings (AudioJailbreak) ([arXiv][3])
  * composition attacks where harmful and benign cues co-occur (SACRED) ([arXiv][7])
* Use **ensembles across layers** and randomization (harder to optimize against).
* If your method is gradient-based, explicitly test **gradient obfuscation** failure modes by using transfer attacks / expectation over transformations.

### Objection 5: “Even if you detect risk early, you haven’t shown actionable oversight value.”

**Rebuttal:**

* Tie audit outputs to **actions**:

  * route to multimodal guard/judge (SALMONN-Guard style) ([arXiv][7])
  * apply layer patching/pruning (SPIRIT style) ([ACL Anthology][5])
  * apply safety-shortcut triggering (ALMGuard style) ([NeurIPS][6])
* Quantify the tradeoff: ASR reduction vs utility loss, and calibration/stability (echoing LALM-as-a-Judge concerns about judge reliability). ([arXiv][8])

---

If you tell me what you specifically mean by **gc(k)** (gradient cosine? guard classifier? something else), I can tighten the MVP to exactly match that formalism and suggest the cleanest “one figure + one table” package that reviewers tend to accept for this slice of AI Safety × Speech/NLP.

[1]: https://openreview.net/forum?id=DJkQ236C8B "https://openreview.net/forum?id=DJkQ236C8B"
[2]: https://arxiv.org/abs/2505.15406 "https://arxiv.org/abs/2505.15406"
[3]: https://arxiv.org/abs/2505.14103 "https://arxiv.org/abs/2505.14103"
[4]: https://arxiv.org/abs/2504.01094 "https://arxiv.org/abs/2504.01094"
[5]: https://aclanthology.org/2025.emnlp-main.734.pdf "https://aclanthology.org/2025.emnlp-main.734.pdf"
[6]: https://neurips.cc/virtual/2025/poster/115978 "https://neurips.cc/virtual/2025/poster/115978"
[7]: https://arxiv.org/abs/2511.10222 "[2511.10222] Speech-Audio Compositional Attacks on Multimodal LLMs and Their Mitigation with SALMONN-Guard"
[8]: https://arxiv.org/pdf/2602.04796 "https://arxiv.org/pdf/2602.04796"
[9]: https://arxiv.org/html/2511.10692v1 "https://arxiv.org/html/2511.10692v1"
[10]: https://www.isca-archive.org/interspeech_2025/alexos25_interspeech.pdf "https://www.isca-archive.org/interspeech_2025/alexos25_interspeech.pdf"
