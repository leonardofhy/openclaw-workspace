# Paper A Submission Checklist + 智凱哥 Email Draft
*Cycle: c-20260306-1301 | Task: Q060 | Track: T3*

---

## Part 1: Paper A Section Status

| Section | Status | Notes |
|---------|--------|-------|
| Abstract v0.7 | ✅ LaTeX-ready | ~156 words; Gap #28 + MPAR² + §4.7 diagnostic protocol added |
| §1 Introduction | ✅ LaTeX-ready | 3 paragraphs; MPAR² v1.9 upgrade; all cite keys confirmed |
| §2 Related Work | ✅ LaTeX-ready | 3 subsections; Pearl Level hierarchy explicit; gap matrix confirms 2×2 positioning |
| §3 Method (§3.1–§3.8) | ✅ LaTeX-ready | 8 subsections ~1250 words; §3.8 Eval Protocol complete |
| §4 Experiments/Results (§4.1–§4.7) | ✅ LaTeX-ready | §4.6 3-Tier Taxonomy + §4.7 Diagnostic Protocol complete |
| §5 Discussion | 🏗️ SKELETON | 5 headers + 2-sentence stubs; **blocked until experimental results** |
| Figures | ⏳ PENDING | Fig 1 (gc curve), Fig 2 (phonological geometry), Fig 3 (2D IIA heatmap), Fig 4 (Qwen2-Audio sweep) — require E1/E2 results |
| Tables | ⏳ PENDING | Table 1 (related work), Table 2 (connector transfer), Table 3 (3-tier taxonomy), Table 4 (diagnostic tests) — Tables 3+4 LaTeX-ready from pitch; Tables 1+2 need results |

---

## Part 2: Open Decisions for Leo

### 🔴 Decision 1: Venue + Scope
**Choose NOW — this determines E1 timeline urgency.**

| Option | Deadline | Scope Required |
|--------|----------|---------------|
| **Interspeech 2026** | Abstract ~March 31; Full paper ~April | E1 (Whisper-small, MacBook 3h) ONLY sufficient for submission |
| **NeurIPS 2026** | ~May 2026 | E1 + E2 (Qwen2-Audio-7B, NDIF/GPU) |
| **EMNLP 2026** | ~June 2026 | E1 + E2 + optional E3 (LoRA) |

**Recommendation:** Interspeech 2026 (E1 alone is publishable as "phonological causal localization in Whisper encoder"; add Qwen2-Audio-7B as camera-ready upgrade or NeurIPS extended version).

---

### 🔴 Decision 2: Co-authorship with 智凱哥

**Two options:**
- **Option A (solo):** Leo is first + corresponding author. 智凱哥 cited for AudioLens code/data access and acknowledged. Faster.
- **Option B (co-author):** 智凱哥 contributes AudioLens codebase + possibly joint experimental design. Paper is stronger but needs alignment on contributions.

**Pre-conditions for Option B:** 智凱哥 confirms access + timeline compatible + contribution scope agreed.

**Action:** Send email below (see Part 3). Decide within 1 week based on response.

---

### 🟡 Decision 3: Minimum Viable Experiment (E1 Scope)

Currently: E1 = Whisper-small, phonological minimal pairs (Choi et al.), MacBook CPU ~3h.
**Blocker:** Need real speech `.wav` file + Python venv setup.

**Minimal unblocking steps (Leo, ~10 min):**
```bash
python3 -m venv ~/audio-mi-env
source ~/audio-mi-env/bin/activate
pip install nnsight openai-whisper torch numpy
# Download LibriSpeech sample:
wget https://www.openslr.org/resources/12/dev-clean.tar.gz
# OR generate synthetic TTS minimal pairs:
python3 -c "import subprocess; subprocess.run(['say', '-o', '/tmp/ba.aiff', 'ba'])"
```

**Phonological minimal pairs source:** `git clone https://github.com/google-research/phonological-arithmetic` (Choi et al. 2602.18899 stimuli).

---

## Part 3: 智凱哥 Email Draft

**Subject:** Paper A collaboration — extending AudioLens with causal patching (gc(k) metric)

---

Hi 智凱哥,

I've been working on a paper building directly on AudioLens, and I'd love to chat about whether collaboration makes sense.

**The idea:** AudioLens shows that audio-language models consult audio at a "critical layer" — but it uses logit-lens observation (no interventions). I want to do the causal version: use DAS-IIT interchange interventions on phonological minimal pairs to measure where patching audio-stream states most strongly shifts model outputs. The metric is gc(L) = DAS accuracy at layer L; the Listen Layer is argmax gc(L).

**What I've built so far:**
- Full 5-section paper draft (§1–§4 LaTeX-ready, §5 pending results)
- gc(k) eval harness scaffold on Whisper-small (MacBook-feasible, ~3h CPU)
- 3-tier grounding failure taxonomy (codec/connector/LLM backbone) with falsifiable gc(k) signatures
- Diagnostic protocol (Steps 1–4, CPU-feasible for Tier 1/2 triage)

**The ask:**
1. Would you be willing to share the AudioLens codebase? Even the NNsight hooks and LALM eval infrastructure would save weeks.
2. Are you interested in co-authoring? I think our work is complementary — AudioLens = observational; this paper = causal. Together it becomes a strong story.
3. If not co-authorship, can I cite AudioLens and mention we discussed the connection?

**Quick context:** I'm targeting Interspeech 2026 (if E1 Whisper results are enough) or NeurIPS 2026 (with Qwen2-Audio-7B E2). The minimal pair experiment (E1) is MacBook-runnable in ~3h once I have a real speech .wav.

Let me know if you want to meet this week — 15 min would be enough to align on scope.

Leo

---

## Part 4: 3 Additional Action Items

1. **Fix Paper B §1 citation inconsistency** — pitch says "4-category benchmark" in §3 outline but "6-metric" in old abstract. Need to reconcile before sharing with Leo. (See Q053 §3 outline for the canonical 4 categories: Audio-RAVEL, TCS-F, causal consistency, grounding sensitivity.)

2. **Register NDIF account** — E2 (Qwen2-Audio-7B) requires GPU. NDIF offers free academic access. URL: `https://ndif.us`. Leo should register with NTU email.

3. **Add Gap #28 (Lee et al. 2603.03855) to Paper A §1** — behavioral degradation under scene complexity motivates the mechanistic account. Already in abstract v0.7; needs to appear in §1 Para 1 as well (currently §1 cites MPAR² and modality collapse, but not Lee et al. explicitly).

---

*Cycle c-20260306-1301 | Duration ~70s | Task: Q060 complete | Next: Q059 (LaTeX assembly) or Q061 (SAELens audio plugin design)*
