# LALM Knowledge Editing — Research Landscape Map
> Created: 2026-03-24 | Status: Living document

---

## 1. What Is LALM Knowledge Editing?

**Definition:** The study of techniques to selectively update, correct, or insert factual knowledge into Large Audio Language Models (LALMs) without full retraining — and to understand what happens when you do.

A LALM (e.g., SALMONN, Qwen-Audio, WavLLM, Gemini audio mode) is a multimodal system where:
- An **audio encoder** (Whisper, HuBERT, etc.) processes speech/audio signals
- A **pretrained LLM backbone** (LLaMA, Vicuna, Qwen, etc.) handles reasoning and generation
- A **bridging module** (Q-Former, linear projector, etc.) connects the two

Knowledge Editing (KE) for LLMs asks: *given a factual update (e.g., "The CEO of OpenAI is now X"), how do we make the model know this without catastrophic forgetting or breaking unrelated capabilities?*

**LALM-KE** specifically asks:
1. Do KE methods that work for text LLMs transfer to audio-conditioned models?
2. Where does "factual knowledge" live in a LALM — in the audio encoder, bridge, or LLM backbone?
3. When a fact is updated via audio (speech question), does the model retrieve the edited fact correctly?
4. Can we exploit mechanistic understanding of LALMs to do more targeted editing?

---

## 2. Why Does It Matter?

### Practical motivation
- LALMs are deployed in voice assistants, customer service bots, transcription+QA systems
- Models go stale: facts change (leaders, prices, policies, events)
- Retraining a 7B+ LALM is expensive; targeted editing is cheap
- Audio-grounded errors are harder to audit than text errors — users may not notice

### Scientific motivation
- KE is a probe for *knowledge localization* — understanding where facts are stored
- In multimodal models, knowledge may be distributed across modalities (text vs. audio representation space)
- LALM-KE is a largely **unexplored intersection** — opportunity for a first-mover paper

### Safety motivation (connects to Leo's AI Safety angle)
- Misinformation injected via audio is hard to detect
- Adversarial KE (poisoning) vs. beneficial KE (correction) — dual-use concern
- Understanding knowledge structure in audio models helps auditing pipelines

---

## 3. Key Sub-Areas

### (a) Knowledge Editing for LLMs

**Core paradigm:** Given a model `f`, original fact `(s, r, o)` (subject, relation, object), and new fact `(s, r, o*)`, find minimal parameter change (or external memory) so `f'(s, r) = o*`.

**Evaluation axes:**
- **Reliability**: does the edit succeed?
- **Generality**: does it generalize to paraphrased queries?
- **Locality**: do unrelated facts remain unchanged?
- **Portability**: does the edit propagate through reasoning chains?

**Key method families:**
| Family | Examples | Core Idea |
|--------|----------|-----------|
| Locate-then-Edit | ROME, MEMIT | Identify "fact storage" layers via causal tracing; directly update MLP weights |
| Meta-Learning | MEND, MALMEN | Train a hypernetwork to predict weight updates from (fact, grad) tuples |
| Memory-Augmented | SERAC, IKE, GRACE | External memory/retrieval; don't touch weights |
| Fine-tuning | KN, Constrained FT | Fine-tune with KL penalty to preserve locality |

**Key benchmarks:** COUNTERFACT, ZsRE, MQuAKE (multi-hop), RippleEdits

### (b) Large Audio Language Models (LALMs)

**Architecture taxonomy:**
1. **Cascaded systems**: ASR → LLM (e.g., Whisper + GPT-4); modular, brittle
2. **End-to-end audio LLMs**: single model processes raw audio + generates text
   - SALMONN (Tsinghua, 2023) — dual encoder (Whisper + BEATs) + Vicuna
   - Qwen-Audio (Alibaba, 2023) — Qwen backbone + audio encoder
   - WavLLM (Microsoft, 2024) — Whisper + Llama
   - LLaSA, AudioPaLM, SpeechGPT, VoxtLM
   - Gemini 1.5 / GPT-4o (proprietary, native audio)

**Knowledge in LALMs:**
- Factual knowledge primarily lives in the **LLM backbone** (inherited from text pretraining)
- Audio encoder encodes acoustic/phonetic features, not facts
- Bridge module (Q-Former) may encode some cross-modal bindings

### (c) The Intersection: LALM-KE

**Key research questions:**

1. **Transfer question**: Do ROME/MEMIT work on the LLM backbone of a LALM? Does editing the backbone propagate correctly when input comes through the audio pathway?

2. **Modality gap question**: When the same fact is queried via speech vs. text, does the model show the edit? Is there a representation alignment failure?

3. **Localization in multimodal context**: Causal tracing in pure LLMs shows facts in specific MLP layers. In LALMs, where does the cross-modal fact retrieval happen?

4. **Audio-specific editing scenarios**:
   - Editing speaker identity facts ("Who is speaking?")
   - Editing acoustic knowledge ("What key is this music in?")
   - Editing factual claims delivered via speech

5. **Benchmark gap**: No clean LALM-KE benchmark exists yet — building one is a paper in itself.

---

## 4. Open Problems & Opportunities

| Problem | Why Hard | Opportunity |
|---------|----------|-------------|
| No LALM-KE benchmark | Need audio versions of COUNTERFACT-style queries | **Build one** (low-hanging fruit paper) |
| Transfer of text KE methods to audio input | Modality gap; query paraphrase across modalities | Systematic empirical study |
| Knowledge localization in audio-conditioned models | Multi-component architecture complicates causal tracing | Mechanistic interp × LALM paper |
| Audio-specific facts (speaker, acoustics) | Not covered by text KE literature | Novel problem formulation |
| Sequential editing (many facts) | Catastrophic interference, more severe in multimodal | LALM-specific continual editing study |
| Evaluation: generality across audio paraphrases | "Same speaker", "different accent", "noisy audio" | Robustness dimension of LALM-KE |

**Most tractable entry point for Leo's group:**
→ **Empirical transfer study**: Take existing LALM (SALMONN or Qwen-Audio) + existing KE method (ROME/MEMIT/GRACE) + adapt text KE benchmark to audio input → measure reliability/generality/locality. This is a concrete, publishable experiment doable in weeks.

---

## 5. Connection to Leo's Expertise

### Mechanistic Interpretability × LALM-KE
- **Leo's angle**: MI asks "where does the model store/compute X?" — directly relevant to locating knowledge in LALMs
- ROME/MEMIT are built on MI insights (causal tracing = MI tool). Leo can extend this to audio-conditioned settings
- **Unique contribution**: causal tracing on LALM inference paths (audio encoder → bridge → LLM) to find modality-specific knowledge circuits

### Speech ML × KE
- Understanding how speech representations align with factual representations in the LLM
- Audio paraphrase robustness of edits: same fact, different speakers/accents
- Potentially: editing speaker-associated facts (what a speaker "knows" vs. what the model "knows")

### AI Safety × LALM-KE
- Adversarial editing via audio (voice-based fact injection)
- Detecting unintended edits / knowledge drift in deployed audio assistants
- Alignment angle: ensuring audio-grounded reasoning is fact-consistent

### Prof. Hung-yi Lee's Group Context
- Strong speech + LLM background → well-positioned for audio-LLM intersection
- History of audio LM benchmarks (SUPERB, DYNAMIC-SUPERB) → benchmark-building DNA
- LALM-KE benchmark could be "Dynamic-SUPERB for Knowledge Editing"

---

## 6. Positioning Statement (for Monday meeting)

> "We're entering an unexplored intersection: how do knowledge editing techniques for LLMs behave when the model is multimodal and queries arrive via audio? The field has KE benchmarks for text and LALM benchmarks for audio tasks, but no systematic study of their intersection. Our group's strength in speech + interpretability positions us to (a) run the first empirical transfer study, (b) build a LALM-KE benchmark, and (c) bring mechanistic interpretability tools to understand where audio-conditioned knowledge lives."
