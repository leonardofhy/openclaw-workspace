# 📊 Weekly Research Summary — 2026-W11 (Mar 9–15)

> Auto-generated: 2026-03-15 21:02 TST

## 🔢 Key Metrics

| Metric | Count |
|--------|-------|
| Autodidact cycles completed | 62 |
| Active research days | 5 (Mar 9–13; 14–15 quiet) |
| Deep paper reads (new this week) | 3 |
| Paper scans / shallow reads | ~10+ |
| Build outputs (scripts/specs) | ~8 |
| Ideation cycles | ~12 |
| New research gaps identified | 3 (Gap #32, #33, #34) |
| Total gaps tracked | 35 |
| AI Safety radar picks logged | ~50+ |
| Knowledge graph sections | 50 subsections, 764 lines |
| New concepts added to KG | ~5 (SCD, AG-REPA, SGPA, MPAR², Gap #34 AAPE) |

## 📖 Papers Read This Week (Deep)

1. **AudioLens (Ho, Lee, Hung-yi Lee — NTU, ASRU 2025)** — Mar 12 cycle
   - Logit Lens applied to LALMs; critical layer discovery; models query audio tokens directly
   - → Gap #33: Logit Lens is observational, gc(k) is the causal test → Paper A as mechanistic sequel
   
2. **Maghsoudi & Mishra 2602.01247 — Brain-to-Speech MI** — Mar 11 cycle
   - Cross-mode activation patching in brain-to-speech decoders
   - KEY: compact layer-specific causal subspaces; speech modes = continuous manifold → gc(L) should be smooth
   - → Gap #26: no equivalent for large speech LLMs; Paper A fills this

3. **Billa et al. 2602.17598 — Cascade Equivalence** — Mar 12 cycle
   - Matched-backbone testing shows speech LLMs = behaviorally equivalent to cascades on text tasks
   - → Gap #32: no layer-level mechanistic account; Paper A gc(L) fills this exactly

## 🔑 Top 3 Research Gaps Discovered

### 1. Gap #32 — No Mechanistic Account of Cascade Equivalence Transition
- Billa (2026) shows behavioral cascade equivalence but no layer-level mechanism
- Paper A gc(L) provides the first mechanistic "when does audio hand off to text" account
- **Status**: 🟢 GREEN — high-impact, Paper A §1 motivation

### 2. Gap #33 — Logit Lens ≠ Causal (AudioLens)
- AudioLens shows models query audio tokens (observational)
- gc(k) = first causal test of whether audio tokens CAUSE predictions
- **Status**: 🟢 GREEN — positions Paper A as explicit causal sequel to labmate's work

### 3. Gap #34 — AAPE Neuron Atlas × gc(k) Causal Gap
- Kawamura et al. identify class-specific audio neurons via AAPE (observational)
- gc(k) patching validates whether these neurons are causally necessary
- **Status**: 🟢 GREEN — Paper B §2 baseline + Paper A causal chain

## 🛠️ Key Build Outputs

- `gc_divergence_thermometer.py` — per-layer JSD between benign/jailbreak gc(k) populations
- `sae_listen_layer.py` — SAE on MicroGPT listen-layer (50% feature correlation at d_model=8)
- `gc_text_probe.py` — cross-modal GPT-2 text probe scaffold
- `t3_readiness_check.py` — end-to-end T3 experiment harness (5/5 checks pass)
- `t5_safety_probe_v1.py` — safety probe integrating gc_eval + gc_jailbreak_classifier
- `microgpt_ravel.py` — RAVEL benchmark on MicroGPT (5/6 components PASS)
- `microgpt_sae.py` — SAE on TinyPhonDASModel (12 features; voicing alignment 0.715)
- MATS proposal v0.4 with gc(k) policy hook
- Joint pre-registration doc (5 hypotheses, 3 JFCs)

## 📡 AI Safety Radar Highlights

Major themes this week:
1. **Anthropic vs DoW escalation**: Hegseth supply-chain-risk designation → legal analysis shows it's untenable; OpenAI/Anthropic aligned on lethal autonomy red lines
2. **Model motives & scheming**: Split Personality Training detects alignment faking cross-domain; Physics of RL formalizes when reward-seeking emerges
3. **Eval crisis**: METR trend inflection point; WoFBench saturated at creation; Petri audit realism bottleneck is structural not prompt-level
4. **Mech interp**: activation oracles are hard to use (negative result); attractor states in multi-agent conversations; Constitutional black-box monitoring

## 📅 Conference Pipeline (no new deadlines found)

| Conference | Deadline | Target Paper | Status |
|-----------|----------|-------------|--------|
| Interspeech 2026 | ~~2026-03-05~~ | AudioMatters | ✅ Submitted |
| NeurIPS 2026 | ~2026-05 | Listen vs Guess (Paper A) | In progress |
| EMNLP 2026 | ~2026-06 | AudioSAEBench (Paper B) | In progress |
| Interspeech 2027 / ICASSP 2027 | TBD | Audio T-SAE (Idea #7) | Backlog |

## 📈 Progress vs Last Week

- **Must-read list**: 10/11 → 11/11 (AudioLens deep read completed ✅)
- **Papers A/B**: v2.0/v1.6 → AudioLens integration strengthens both; Gap #33 = Paper A's strongest positioning argument
- **Methodology convergence map**: 5 papers → confirms Paper A fills ALL prior gaps (non-causal, non-speech-LLM, neuron-level only, generation domain)
- **Execution status**: still blocked on Leo unblock (P0 Gap #18 phonological geometry experiment + venv setup + real speech file)
- **Phase**: explore-fallback → running out of theory-only work; need experiment approval

## ⚠️ Blockers

1. **Leo unblock needed**: venv setup + first .wav file + Gap #18 phonological geometry experiment approval
2. **Pre-experiment writing budget EXHAUSTED**: no more paper section drafting until experiments run
3. **Autodidact went quiet Mar 14–15**: likely due to exhausted explore-fallback material; needs experiment phase transition

## 🎯 Next Week Priorities

1. **Get Leo to approve CPU experiment** — t3_readiness_check.py is 5/5; everything is ready
2. **Run Gap #18 phonological geometry test** — MacBook feasible, pyvene ready
3. **Transition to experiment phase** — theory/writing budget exhausted; need real data
4. **Thursday arXiv batch** — cs.SD + eess.AS + cs.CL + cs.AI scan

---
_Generated by Little Leo (Lab) • Weekly Research Summary cron_
