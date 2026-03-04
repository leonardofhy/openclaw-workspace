# 🗣️ 智凱哥 Conversation Talking Points
> Created: 2026-03-03 11:01 (cycle #212)
> Purpose: Concise ammunition for Leo → 智凱哥 conversation about research collaboration
> Status: Ready to use

---

## One-Sentence Pitches

**Paper A ("Localizing the Listen Layer"):**
> "AudioLens observes *where* models look (logit lens, Level 1); we prove *causally* where speech representations are consulted using DAS interchange interventions at Pearl's Level 3 — and we find a single concentrated layer that doubles as the semantic bottleneck."

**Paper B ("AudioSAEBench"):**
> "All five existing audio SAE papers evaluate features observationally — we build the first benchmark that tests whether audio SAE features are *causally disentangled* (Cause+Isolate metric from RAVEL), and we add gc(F): a novel metric measuring whether each SAE feature grounds in *audio* rather than text-prediction context."

**Two-paper thesis (30-second version):**
> "One metric (grounding coefficient gc), two granularities: Paper A localizes the *layer* where audio is causally consulted; Paper B identifies the *features* that do the consulting. Same DAS-IIT infrastructure, same ALME conflict stimuli, same Pearl Level 3 standard — they cite each other."

---

## Pearl Hierarchy Comparison Table

| Work | Pearl Level | Method | Claim |
|------|-------------|--------|-------|
| AudioLens (智凱哥, 2025) | Level 1 | Logit lens (observational) | "Model attends to audio at layer k" |
| FCCT (vision, 2025) | Level 2 | Causal tracing (distributional) | "Vision token causally affects output" |
| **Paper A (Leo)** | **Level 3** | **DAS + controlled phonological minimal pairs** | **"Audio phonological geometry causally localizes to layer k*"** |

**Key point**: This is NOT "adding patching to AudioLens." It's the same scientific question at a higher epistemological standard (Joshi et al. 2602.16698 — "Causality is Key" — explicitly requires Level 3 for publishable causal MI claims).

---

## Conversation Agenda

1. **Opening**: "I read your AudioLens paper — really clean work. I have an idea for a causal extension. 3 minutes?"

2. **Paper A pitch** (2 min):
   - Draw the 3-tier table above
   - "We use DAS (distributed alignment search) with Choi et al.'s phonological minimal pairs as controlled stimuli → provably causal, Pearl Level 3"
   - "The key metric is gc(k) = DAS-IIA at each layer — peaks at the Listen Layer"
   - "Phase 1 is MacBook-feasible (Whisper-small + NNsight) — I can start this week"

3. **Key questions for 智凱哥**:
   - "Does your AudioLens codebase have NNsight hooks for Qwen2-Audio cross-attention? Can I adapt them?"
   - "Has your lab worked with ALME stimuli (2602.11488, 57K audio-text conflicts)? That's the perfect Phase 2 test set."
   - "AudioLens focused on attention weights — I'm patching the audio token activations themselves. Is there overlap in what you've tried?"

4. **Paper B mention** (1 min):
   - "I'm also building AudioSAEBench — standardized evaluation for audio SAEs"
   - "Uses Audio-RAVEL (Cause+Isolate) — would benchmark future NTU lab audio MI papers automatically"
   - "Are you or your labmates doing any SAE work on speech/audio models?"

5. **Collaboration ask**:
   - "Would you be co-author on Paper A given AudioLens is the direct prior?"
   - "Or at minimum, acknowledgment + feedback on Phase 1 results?"

---

## Infrastructure Leo Already Has

| Asset | Status | Used For |
|-------|--------|----------|
| `whisper_hook_demo.py` | ✅ Verified | Phase 1 norm heatmap (layer sweep pre-screen) |
| `whisper_logit_lens.py` | ✅ Verified | Phase 1 LIS curve (progressive refinement) |
| Choi et al. stimuli | 📥 Need to clone `juice500ml/phonetic-arithmetic` | Phase 1 minimal pairs |
| NNsight | 📦 Need venv install | All patching experiments |
| ALME stimuli | 🌐 Public dataset (2602.11488) | Phase 2 audio-text conflict patching |

**20-minute unblock checklist for Leo:**
```bash
python3 -m venv ~/audio-mi-env
source ~/audio-mi-env/bin/activate
pip install nnsight openai-whisper torch
git clone https://github.com/juice500ml/phonetic-arithmetic
python skills/autodidact/scripts/whisper_hook_demo.py --no-plot
```

---

## Key Papers to Have Ready for the Conversation

| Paper | Why relevant |
|-------|-------------|
| AudioLens (arXiv:2506.05140) | 智凱哥's own paper — know it cold |
| Joshi et al. 2602.16698 "Causality is Key" | Epistemic justification for Level 3 |
| ALME (2602.11488) | 57K conflict stimuli = shared test set |
| Choi et al. 2602.18899 | Phonological minimal pairs = Phase 1 stimuli |
| Geiger et al. 2303.02536 (DAS) | The method — 2-sentence explainer ready |

---

## Risk / If They're Skeptical

**"Why not just extend AudioLens with regular activation patching?"**
→ "Regular patching assumes neurons are localist. AudioSAE shows Whisper has ~2000 features per layer — extreme polysemanticity. DAS finds the relevant *subspace* despite polysemanticity. That's why IIA is the right metric, not logit contribution."

**"Isn't this just AudioLens 2.0? How is it a new paper?"**
→ "AudioLens is observational. We're doing controlled causal experiments with guaranteed stimuli pairs. The *claim* is categorically stronger — it's the difference between 'the model looks at audio here' and 'the model's behavior changes because of the audio phonological representation at this layer.'"

**"Is there enough for a full paper?"**
→ "Table 1 in the pitch has 4 experiments: (1) gc(k) layer sweep on phonological contrasts, (2) cross-generalization (voicing → nasality → manner → place), (3) decomposability test (voicing ⊥ identity), (4) ALME conflict stimuli. Each is a new finding. NeurIPS 2026 dataset+benchmark track or main track."
