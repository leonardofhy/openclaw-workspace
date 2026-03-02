# 🧪 Experiment Execution Queue

> Purpose: 把 idea/gap 庫轉成「可執行實驗隊列」，解決 meta-awareness-board Q6。
> Created: 2026-02-28 01:07 (cycle #51)
> Update: after each execution; sort by priority

---

## 🆕 Cross-Cutting Preprocessing: Codec-Grounded Causal Patching (Gap #21 — cycle #163)

> Applies as a preprocessing option to ALL experiments below (P0–P5). Not a standalone paper — an engineering contribution.

**Insight (Sadok et al. 2506.04492, Interspeech 2025 + Gap #21 synthesis):**
SpeechTokenizer maps RVQ layers to specific attributes:
- **Layer 1 tokens** = semantic content (phonetic/linguistic, via HuBERT supervision)
- **Layers 2+ tokens** = acoustic attributes (speaker identity, pitch, timbre, prosody)

This enables *attribute-selective* audio corruption — far superior to white noise (Gap #6):

| Corruption Goal | Method |
|----------------|--------|
| Isolate semantic pathway | Replace Layer 1 tokens from clean audio with different-content tokens (same speaker) |
| Isolate acoustic/identity pathway | Replace Layers 2+ tokens (keep Layer 1 = content unchanged) |
| Full replacement (baseline) | Replace all RVQ layers (current standard = naive approach) |

**Connection to Core Research Q#1:** "Audio 的 'clean/corrupt' 怎麼設計才只破壞你要隔離的因素?" → ANSWERED via RVQ layer semantics.

**Integration targets:**
- **P0 (Gap #18 phonological geometry):** Patch Layer 1 tokens only → tests phonological geometry without acoustic confound. Layer 2+ fixed = speaker identity unchanged → cleanest phonological isolation.
- **P1 (Triple Convergence IIT):** Layer 1 replacement = content corruption; Layer 2+ = acoustic corruption. Can disambiguate whether transition layer is phonetic or paralinguistic processing.
- **P2 (Listen Layer Paper):** ALME conflict stimuli can be augmented: replace Layer 1 tokens with semantically conflicting content while keeping speaker voice (Layer 2+) identical → sharper audio-text conflict signal.
- **P4 (Class-specific Neuron Grounding):** For emotion ESN analysis (Zhao et al. Qwen2.5-Omni): patch Layer 2+ tokens (prosody/energy) while keeping content fixed → cleaner test of whether ESNs respond to acoustic or linguistic emotion signals.
- **P5 (AudioSAEBench):** RVQ layers = natural partition for Category 1 (Acoustic Concept Detection) — validate whether SAE features extracted from SpeechTokenizer align with the designed Layer 1 / Layer 2+ disentanglement.

**Prerequisite:** SpeechTokenizer installed (`pip install speechtokenizer`). MacBook-feasible — CPU inference for tokenization.

**Gap #21 status:** Confirmed fully open (6 arXiv queries, 0 results on causal patching of codec token streams in LALM inference). Adding codec causal patching to Paper A or B scope = incremental, not primary.

---

## Queue Status
- Total ideas: 6 (crystallized in knowledge-graph + goals)
- Experiments proposed: 2 (ready for Leo approval)
- Experiments executed: 0 (execution-blocked)
- Blocker: Leo approval + real speech .wav file + venv setup

---

## Priority 0 — Phonological Geometry Prerequisite Check (NEW — Gap #18)

**Hypothesis:** The linear phonological geometry confirmed in S3M encoders (Choi et al. 2602.18899: `[b]=[d]-[t]+[p]` works) survives through the connector into speech LLMs. This is a prerequisite for Paper A's grounding_coefficient and Paper B's TCS(F) metric to be meaningful.

**Method (2-4h, partial MacBook feasible):**
1. Reuse Choi et al. code (github.com/juice500ml/phonetic-arithmetic) to extract phonological direction vectors from Whisper-small encoder output (e.g., voicing_vector = h([d]) - h([t]))
2. Hook connector module via NNsight on a small LALM (DeSTA2 or NDIF-accessible Qwen2-Audio)
3. Test arithmetic in LLM residual stream: `projected_h([b]) ≈ projected_h([d]) - projected_h([t]) + projected_h([p])?`
4. Layer-wise linear probe for voicing direction across all LLM layers
5. **[NEW — cycle #106 Q18]** Extract top-k PCA directions of phonological subspace → use as DAS rotation initializer in Paper A IIT experiment ("Phono Init vs Random Init" ablation)

**Expected outcomes:**
- Geometry SURVIVES (cosine > 0.5): LLM has structured phonological access → supports Paper A listen layer claim
- Geometry DEGRADES (cosine < 0.2): connector is phonological bottleneck → motivates Modality Collapse frame (2602.23136)
- Both outcomes publishable as Figure 2 of Paper A or Category 0 prerequisite in AudioSAEBench

**Prerequisites:**
- [ ] Real speech minimal pair .wav files (or Choi et al. stimuli — public code exists)
- [ ] NNsight venv + small LALM (DeSTA2) OR NDIF for Qwen2-Audio
- [ ] ~2-4h

**Connects to:** Paper A (prerequisite validation), Paper B (TCS(F) metric foundation), Idea #7 (Audio T-SAE phoneme priors), Gap #14 (Modality Collapse)

---

## ⭐ Priority 1 — IIT Experiment: Triple Convergence Causal Test

**Hypothesis:** Whisper's transition layer (~50% depth) is causally responsible for semantic crystallization, not just correlational.

**Method (MacBook-feasible):**
1. `source ~/audio-mi-env/bin/activate` (after venv created)
2. Use NNsight to patch Whisper-small encoder hidden states at each layer
3. Denoising: run with clean audio, patch corrupt audio's internal state at layer L → measure WER Δ
4. Find which layer L gives maximum WER recovery = "Listen Layer"
5. Compare result vs norm transition (layer 3 in base, predicted layer 3-4 in small)

**Prerequisites:**
- [ ] Leo approves IIT experiment
- [ ] Real speech .wav file (any English utterance)
- [ ] `python3 -m venv ~/audio-mi-env && pip install nnsight openai-whisper`
- [ ] ~3 hours (MacBook, Whisper-small)

**Expected output:** Layer-wise causal contribution plot → "Triple Convergence IIT" figure for paper.

**Connects to:** Track 3 (Listen vs Guess), Track 2 (AudioSAEBench), "Listen Layer Hypothesis"

---

## ⭐ Priority 2 — Listen Layer Paper Experiment

**Hypothesis (Listen Layer Hypothesis):** There exists a small set of attention heads/layers in audio-LLMs where audio representations are *causally* consulted. Current ALME, Cascade Equivalence, Modality Collapse papers all show behavioral evidence; none do layer-wise causal patching.

**Method:**
1. Use ALME conflict stimuli (57K audio-text conflicts, arXiv:2602.11488 — already built)
2. Denoising patching sweep on Qwen2-Audio: for each layer L, patch audio-stream hidden states from text-dominant → audio-dominant input
3. Identify which layer L flips model behavior from "text-dominated" to "audio-attended"
4. That L = "Listen Layer"

**Prerequisites:**
- [ ] NDIF account or local GPU (Qwen2-Audio-7B too big for MacBook)
- [ ] NNsight venv
- [ ] Needs Leo to decide: GPU via NDIF vs 戰艦

**Expected output:** Listen Layer localization for Qwen2-Audio → Track 3 paper foundation.

---

## Priority 3 — Real Speech Test (validation, not discovery)

**Goal:** Validate that whisper_hook_demo.py shows real acoustic→semantic transition with real speech (not synthetic sine wave).

**Method:**
1. Grab any short English .wav (LibriSpeech sample, or record "hello, this is a test")
2. Run: `python skills/autodidact/scripts/whisper_hook_demo.py path/to/test.wav`
3. Expect: CKA clusters [0-2] and [3-5] more distinct; norm jump at layer 3 sharpens

**Prerequisites:**
- [ ] Real speech .wav (any English, 5-10s)
- [ ] pip install openai-whisper (or already installed)

**Time:** 5 minutes. Lowest barrier to entry.

---

## Priority 4 — Class-specific Neuron Grounding

**Hypothesis:** Emotion/gender neurons found by AAPE or SwiGLU-hook analysis in LALMs (Qwen2.5-Omni) respond to *audio* cues, not just linguistic context. Nobody has tested this.

**Method:**
1. Replicate Zhao et al. ESN detection (SwiGLU hook, MAD/CAS selectors) on Qwen2.5-Omni
2. For each ESN: measure activation with audio emotion input vs text emotion input (minimal pair)
3. Compute grounding_coefficient at neuron level

**Prerequisites:**
- [ ] Leo approval (this extends Zhao et al. significantly)
- [ ] GPU (Qwen2.5-Omni is large)
- [ ] Contact: are Zhao et al. code available?

---

## Priority 5 — AudioSAEBench Design (no code, just protocol)

**Goal:** Design AudioSAEBench evaluation framework analogous to SAEBench (Karvonen, Nanda et al., ICML 2025) but for speech/audio SAEs.

**Method (no GPU needed, pure design work):**
1. Map SAEBench's 8 metrics to audio equivalents (what does "concept detection" mean for phonemes? for environmental sounds?)
2. Define "Grounding Sensitivity" = novel metric: gc per SAE feature (which features are audio-grounded vs text-predicted?)
3. Draft benchmark protocol document

**Prerequisites:**
- [ ] None (Leo can approve or expand)
- [ ] Time: ~2h reading + writing

---

## Priority 6 — Temporal SAE Analysis (concept/design)

**Gap:** All audio SAE papers (AudioSAE, Mariotte, AR&D) use mean-pooled temporal features → lose *when* features fire during utterance.

**Idea:** Apply SAE at each timestep → animate feature activation over time → "what does the model notice and when?"

**Prerequisites:**
- [ ] AudioSAE codebase (available: github.com/audiosae/audiosae_demo)
- [ ] GPU (Whisper-large)
- [ ] Needs Leo approval

---

## Unblock Checklist (for Leo, when ready)

The minimal steps to unblock ALL experiments above:

```bash
# Step 0 (NEW — Priority 0 prerequisite, Gap #18):
git clone https://github.com/juice500ml/phonetic-arithmetic /tmp/phonetic-arithmetic
# No GPU needed; uses Choi et al. stimuli + Whisper-small encoder only

# Step 1: Create venv
python3 -m venv ~/audio-mi-env
source ~/audio-mi-env/bin/activate
pip install nnsight openai-whisper torch

# Step 2: Get real speech file (any option)
# Option A: LibriSpeech sample (1 command):
curl -sL "https://www.openslr.org/resources/12/dev-other.tar.gz" | tar xz --strip-components=5 -C /tmp/ --wildcards "*.flac" 2>/dev/null
# Option B: Record 5-10s English sentence → /tmp/test.wav
# Option C: Ask Leo to drop any .wav in workspace

# Step 3: Run validation
python skills/autodidact/scripts/whisper_hook_demo.py /tmp/test.wav

# Step 4 (optional): Approve IIT experiment → start Priority 1
```

**Expected time to unblock:** 15-20 minutes of Leo's time (added git clone for Priority 0).

---

## Done Queue

*(empty — no experiments executed yet)*

---

## Completion Rate Tracking

| Week | Queued | Executed | Ratio |
|------|--------|----------|-------|
| 2026-W09 (Feb 23-28) | 6 | 0 | 0% |

**Target:** ≥1 experiment per week starting Week 10 (after Leo unblock).
