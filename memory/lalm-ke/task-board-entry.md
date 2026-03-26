# Task Board Entry — LALM Knowledge Editing Research
> Ready to paste into task-board.md

---

## Paste into task-board.md:

```markdown
## 🎯 LALM Knowledge Editing Research
**Status:** 🟡 Active — Survey Phase
**Started:** 2026-03-24
**Checkpoint:** Weekly Monday PM (with 智凱 and 彥廷)
**Advisor:** Prof. Hung-yi Lee
**Phase:** 1 of 4 (Survey → Design → Experiment → Write)

### Context
Exploring the intersection of Knowledge Editing (KE) for LLMs and Large Audio Language Models (LALMs).
Goal: establish Leo's group as first to study KE in audio-conditioned multimodal models.

### Current Phase: Survey (Weeks 1-4)
- [ ] **[W1]** Read Phase 1 P0 papers (ROME, MEMIT, SALMONN, Qwen-Audio, multimodal KE survey)
  → See: `memory/lalm-ke/reading-roadmap.md`
- [ ] **[W1]** Monday meeting #1: align on direction with 智凱 + 彥廷
- [ ] **[W2]** Read Phase 2 methods (MEND, SERAC, GRACE, IKE, RippleEdits)
- [ ] **[W2]** Choose target LALM (SALMONN or Qwen-Audio) for first experiments
- [ ] **[W2]** Choose target KE method to adapt (ROME or GRACE recommended)
- [ ] **[W3]** Complete landscape survey; confirm the gap exists
- [ ] **[W4]** Draft experiment proposal (setup, metrics, expected outcomes)
- [ ] **[W4]** Present to Prof. Lee — get go/no-go on direction

### Upcoming Phases (plan after W4)
- **Phase 2 (Design):** Adapt chosen KE method for LALM; design LALM-KE benchmark
- **Phase 3 (Experiments):** Run on SALMONN/Qwen-Audio; measure reliability/generality/locality
- **Phase 4 (Write):** Paper targeting ACL/EMNLP/Interspeech

### Resources
- Landscape: `memory/lalm-ke/landscape.md`
- Reading roadmap: `memory/lalm-ke/reading-roadmap.md`
- Daily workflow: `memory/lalm-ke/daily-workflow.md`
- Notes template: `memory/lalm-ke/survey-notes-template.md`
- Survey notes: `memory/lalm-ke/survey-notes/`

### Bot Tasks (automated)
- 📰 Daily arXiv scan (14:30 TPE) → Discord DM if score ≥ 2
- 📋 Sunday 20:00: weekly synthesis → `memory/lalm-ke/weekly-synthesis.md` + DM
- 🔔 Monday 09:00: meeting prep reminder

### Blockers / Risks
- [ ] Confirm: has anyone published LALM-KE? (search arXiv before committing)
- [ ] GPU access for SALMONN experiments (lab desktop RTX PRO 6000 ✓)
- [ ] SALMONN/Qwen-Audio model weights availability on HuggingFace

### Notes
- Entry point recommended: empirical transfer study (ROME/MEMIT on SALMONN backbone, audio-prompted queries)
- Interpretability angle (Leo's strength): causal tracing on LALM inference path
- Benchmark building angle: audio-version of COUNTERFACT (LALM-COUNTERFACT)
- Safety angle: adversarial KE via audio injection
```

---

## Quick Reference Card (for Monday meetings)

```
LALM-KE in 3 bullets:
1. CAN we edit knowledge in audio LLMs using text KE methods? (empirical question)
2. WHERE does cross-modal knowledge live in LALM architecture? (MI question)  
3. What's the right benchmark to measure this? (benchmark question)

Target models: SALMONN, Qwen-Audio
Target methods: ROME, MEMIT, GRACE
Target benchmarks: COUNTERFACT → audio-ify it
Leo's edge: Mechanistic Interpretability + Speech expertise
```
