# Autodidact System Audit
**Date**: 2026-03-18
**Period covered**: ~10 days (2026-03-08 to 2026-03-18)
**Scope**: skills/autodidact/scripts/, memory/learning/cycles/, memory/learning/state/

---

## 1. Script Inventory

**Total scripts**: 54 .py files
**Total lines**: ~20,600

### Full Inventory Table

| Filename | Category | Track | Lines | Notes |
|---|---|---|---|---|
| `and_gate_schelling_stability.py` | mock | T3 | 512 | Q080. 5-seed MicroGPT mock. AND-gate features = Schelling points cross-seed. numpy only. |
| `and_or_gc_patching_mock.py` | mock | T3 | 386 | Q070. AND/OR gate taxonomy via 3-run denoising patching. gc(k) peak vs AND-gate fraction r=0.98. numpy only. |
| `audio_incrimination_graph.py` | mock | T5 | 300 | Q090. Causal blame graph over SAE features at gc(k) collapse step t*. Bridges T3+T5. numpy only. |
| `audio_sae_bench.py` | mock | T5 | 450 | T5 AudioSAEBench scaffold with 8 interpretability metrics (M1-M8). Mock mode only. numpy only. |
| `audiosaebench_integration.py` | mock | T2 | 705 | Q048. Runs all 8 AudioSAEBench metrics (M1-M8) on unified mock corpus. Pass/fail table. numpy only. |
| `delta_gs_single_layer.py` | mock | T5 | 460 | Q071. ΔGS (Cohen's d) as GPU-free single-layer proxy for adversarial anomaly detection. numpy only. |
| `directed_isolate_mock.py` | mock | T3 | 449 | Q068. Directed Isolate_in/Isolate_out protocol; asymmetry across 4 persona conditions. numpy only. |
| `gc_divergence_thermometer.py` | mock | T3+T5 | 301 | Per-layer Jensen-Shannon divergence between benign vs jailbreak gc(k) populations. numpy only. |
| `gc_eval.py` | tool | T3 | 653 | Core gc(k) eval harness. Mock and real Whisper modes. Anti-confound checker. Central dependency. |
| `gc_experiment_runner.py` | tool | T3 | 293 | Orchestrates gc_eval.py across 3 conditions (listen/mid/guess). Imports gc_eval. |
| `gc_hallucination_mock.py` | mock | T3 | 369 | Q110. gc(k) predicts hallucination onset (CORRECT/REPEAT/CONFAB). AUC > 0.80 hypothesis. numpy only. |
| `gc_incrimination_env3.py` | mock | T3 | 493 | Q101. Extends gc_incrimination_mock with ENV-1/2/3 motive taxonomy. Imports gc_incrimination_mock. |
| `gc_incrimination_mock.py` | mock | T3 | 552 | Q088+Q069. Temporal gc(k,t) + t* error-onset + feature-level blame attribution. numpy only. |
| `gc_jailbreak_classifier.py` | tool | T5 | 260 | Time-series classifier on gc(k) curve → benign/jailbreak label with confidence. numpy only. |
| `gc_probe_v1.py` | mock | T5 | 198 | Q067. MVP audio jailbreak probe. Outputs listen_layer, gc_curve, verdict JSON. numpy only. |
| `gc_regression_test.py` | tool | T3 | 300 | Parameterized regression tests on listen-layer boundary stability. Imports gc_eval. CI-ready. |
| `gc_schelling_mock.py` | mock | T3 | 381 | Q087. gc-critical layers = Schelling-stable SAE layers. Pearson r=0.96. numpy only. |
| `gc_text_probe.py` | real | T3 | 163 | Cross-modal gc(k) for text LLMs (GPT-2). Requires: transformers + torch (~500MB). Tier 1. |
| `gc_visualizer.py` | tool | T3 | 501 | Generates 4 paper-ready figures for gc(k) experiments. Optionally uses matplotlib. |
| `jalmsbench_eval_harness.py` | mock | T5 | 210 | JALMBench 246-query mock evaluation. Computes P/R/F1/AUROC. Tier 0. |
| `listen_layer_audit.py` | mock | T5 | 341 | Per-layer safety score MVP. Real mode needs openai/whisper-tiny. numpy only for mock. |
| `m4_pcds.py` | mock | T2 | 616 | AudioSAEBench M4. PCDS = Cause × Isolate (audio-RAVEL port). Tier 0 mock; Tier 1 needs SAE activations. |
| `m7_spurious.py` | mock | T2 | 461 | AudioSAEBench M7. Spurious correlation via chi² + articulatory coherence. numpy only. |
| `m8_geometry.py` | mock | T2 | 477 | AudioSAEBench M8. Feature geometry: cluster score, anti-podal pairs, superposition index. numpy only. |
| `m9_delta_gs_cross_correlation.py` | mock | T3+T5 | 474 | Q081. M7(ΔGS) vs M9(causal consistency) cross-correlation per layer. numpy only. |
| `m9_gated_dual_detector.py` | mock | T5 | 586 | Q083. Two-factor alert: M7 AND NOT M9 reduces FPR vs single-factor. numpy only. |
| `m9_online_consistency_monitor.py` | mock | T5 | 593 | Q112. Online M9 CCS gating for ΔGS streaming monitor. Dual-gate FPR reduction. numpy only. |
| `microgpt_gc_eval.py` | mock | T3 | 338 | Q048. MicroGPT transparent validator for gc(k) pipeline. Pure numpy, deterministic. |
| `microgpt_phon_das_suite.py` | mock | T3 | 172 | Q038. TinyPhonDASModel, 6-phoneme task, IIA/Cause/Isolate scores. numpy only. |
| `microgpt_ravel.py` | mock | T3 | 478 | Q053. Tier-1 RAVEL validation on microgpt audio-semantic task (CPU training <60s). numpy only. |
| `microgpt_sae.py` | mock | T3 | 426 | Q052. First transparent phoneme SAE on microgpt activations. Sparse autoencoder training. numpy only. |
| `online_delta_gs_monitor.py` | mock | T5 | 486 | Q079. Sliding-window streaming ΔGS monitor (Cohen's d per utterance). numpy only. |
| `persona_gc_benchmark.py` | mock | T3 | 423 | Q039. Persona-conditioned gc(k) across 3 system-prompt conditions. numpy only. |
| `persona_gc_temporal.py` | mock | T3 | 494 | Q073. 2D gc(k,t) heatmap per persona condition. numpy only. |
| `phoneme_schelling_iia.py` | mock | T3 | 570 | Q082. IIA-optimal features vs coincidental features cross-seed stability. numpy only. |
| `sae_adversarial_calibrator.py` | mock | T5 | 257 | Q041. Threshold calibration for SAE-based adversarial detector. No docstring. stdlib only. |
| `sae_adversarial_detector.py` | mock | T5 | 729 | Q041. Full SAE adversarial detector with 3 scoring methods + PR curve calibration. numpy only. |
| `sae_incrimination_patrol.py` | mock | T5 | 647 | Q078. Feature-level blame for adversarial alerts: top-K incrimination + persistent offenders. numpy only. |
| `sae_listen_layer.py` | mock | T3+T5 | 589 | Q077. SAE on MicroGPT listen-layer; correlates features with gc(0). numpy only. |
| `safe_patch.py` | tool | general | 116 | Race-safe atomic file patcher using fcntl locking. Utility for SKILL.md updates. |
| `synthetic_stimuli.py` | tool | T3+T5 | 900 | Phoneme-contrastive activation pair generator + adversarial corpus + JALMBench mock. numpy only. Largest file. |
| `t3_readiness_check.py` | tool | T3 | 158 | End-to-end demo/readiness check. Imports gc_eval, synthetic_stimuli, listen_layer_audit. |
| `t5_safety_probe_v1.py` | mock | T5 | 241 | T5 MVP: gc_eval + gc_jailbreak_classifier pipeline. Tier 1 mode requires Whisper + .wav. |
| `test_e2e_pipeline.py` | tool | T3+T5 | 293 | Q055. End-to-end integration test: microgpt_gc_eval + unified_eval + gc_jailbreak_classifier. |
| `test_gc_eval.py` | tool | T3 | 317 | Unit tests for gc_eval.py. No model required. pytest-compatible. |
| `test_gc_jailbreak_classifier.py` | tool | T5 | 165 | Q045. Unit tests for gc_jailbreak_classifier.py. pytest-compatible. |
| `test_listen_layer_audit.py` | tool | T5 | 91 | Unit tests for listen_layer_audit.py mock mode. Subprocess-based. |
| `test_synthetic_stimuli.py` | tool | T3+T5 | 185 | Unit tests for synthetic_stimuli.py. Verifies shapes + gc integration. |
| `test_unified_eval.py` | tool | T3+T5 | 115 | Unit tests for unified_eval.py. Verifies JSON schema. |
| `unified_eval.py` | tool | T3+T5 | 305 | Combined gc(k) + safety audit in single pass. JSON schema output. |
| `whisper_hook_demo.py` | real | T3 | 247 | Starter script for Whisper encoder activation hooks + CKA heatmap. Requires openai-whisper + torch. |
| `whisper_logit_lens.py` | real | T3 | 372 | Logit-Lens on Whisper encoder layers. Tests Triple Convergence Hypothesis. Requires openai-whisper + torch. |

### Category Breakdown

| Category | Count | % |
|---|---|---|
| mock | 32 | 59% |
| tool | 14 | 26% |
| real | 3 | 6% |
| dead | 0 | 0% |

### Track Breakdown

| Track | Count |
|---|---|
| T3 (Listen vs Guess / Paper A) | 23 |
| T5 (Safety probes / MATS) | 14 |
| T2 (AudioSAEBench / Paper B) | 5 |
| T3+T5 (dual-track) | 7 |
| General | 2 |

### Dependency Notes

- **Tier 0 (numpy only, no downloads)**: 47/54 scripts — all runnable on M3 MacBook today
- **Tier 1 (openai-whisper + torch, CPU)**: whisper_hook_demo, whisper_logit_lens, gc_text_probe (GPT-2)
- **Tier 2 (GPU needed)**: Q001-Q003 (blocked) requiring Qwen2-Audio-7B or large Whisper
- **Key central dependency**: gc_eval.py is imported by gc_experiment_runner, gc_regression_test, t3_readiness_check, test_e2e_pipeline, test_gc_eval
- **Fragile dynamic import**: gc_incrimination_env3.py loads gc_incrimination_mock.py via `importlib.util.spec_from_file_location` — path-sensitive

---

## 2. Cycle Docs Summary

**Total cycle files**: 144 (c-*.md files in memory/learning/cycles/)
**Period**: 2026-03-08 to 2026-03-18
**active.json reports**: 221 total cycles, 43 total skips (19.5% skip rate)

### Count by Action Type

| Action | Count | Notes |
|---|---|---|
| learn | 57 | Paper reads, design syntheses, concept analysis |
| ideate | 41 | Combinatorial ideation, 20-idea tables |
| build | 18 | Script creation or design doc writing |
| plan | 8 | Experiment specification, protocol design |
| reflect | 3 | End-of-day summaries |
| skip/unlabeled | ~17 | Budget-exhausted cycles, inconsistent headers |

### Most Impactful Build Cycles

| Cycle | Output | Key Result |
|---|---|---|
| c-20260309-2345 | `microgpt_phon_das_suite.py` | Q038. First DAS-style phoneme circuit; IIA=1.000, Cause=1.000, Isolate≈0.992 |
| c-20260310-1145 | `critical-layer-patching-checklist.md` | Q042. Reproducible LALMs patching checklist. Foundation document |
| c-20260311-0001 | ΔGS metric definition (Paper B §3.7) | Q065. ΔGS metric defined; added as M7 to AudioSAEBench |
| c-20260311-0031 | Interpret-Then-Defend spec | Q066. SAE feature-level defense framework; precursor to sae_adversarial_detector |
| c-20260311-1345 | `microgpt_sae.py` | Q052. First transparent phoneme SAE; validates sparse feature selectivity |
| c-20260312-0231 | `persona_gc_temporal.py` | Q072/073. 2D gc(k,t) × persona heatmap; M9 Causal Abstraction Consistency defined |
| c-20260312-2101 | `gc_schelling_mock.py` | Q087. gc-critical layers = Schelling-stable (r=0.96–0.98). Major T3 confirmation |
| c-20260312-2201 | `and_or_gc_patching_mock.py` | Q070. AND-gate% vs gc(k) Pearson r=0.98. AND-gate peak = gc peak confirmed |
| c-20260313-0037 | `delta_gs_single_layer.py` | Q071. GPU-free ΔGS proxy; 27/32 features shift under attack |
| c-20260314-2145 | `gc_incrimination_env3.py` + `sae_incrimination_patrol.py` | ENV-1/2/3 taxonomy implemented; 96% suppression recall on patrol |

### Patterns

1. **Ideate-heavy (28%)**: 41/144 cycles are ideation. Each generates ~9 new queue tasks. This creates a widening gap between idea generation and execution.

2. **Budget exhaustion cascade**: Build budget (4/day) frequently depletes by ~10 AM, triggering ideate-only afternoons. March 14 daily reflect noted "13 skips = budgets burning fast" with 23 READY tasks already queued.

3. **Rapid theory convergence**: 10 days produced a coherent framework — gc(k) → AND/OR gates → Schelling stability → ENV taxonomy → two-level attribution stack. Two ideation cycles on 2026-03-13 morning crystallized this into a Paper A §2-§4 structure.

4. **Phase lock**: active.json shows `phase = explore-fallback` since 2026-03-09. Exit requires `leo_approved_gpu_or_cpu_experiment` — still pending. All downstream build cycles are pre-execution theory work.

---

## 3. Design Docs Inventory

**Total non-cycle docs in cycles/**: 7 files

| Filename | Track | Description |
|---|---|---|
| `audio-ravel-stimuli-plan.md` | T2 | Q063. 400-pair stimulus table for Audio-RAVEL: 5 phonological contrasts × 4 languages × 20 pairs. TTS sources specified per language. |
| `critical-layer-patching-checklist.md` | T3 | Q042. Reproducible 6-phase checklist for causal patching sweeps on LALMs: prerequisites → AtP baseline → AND/OR gate protocol → denoising correction → top-k aggregation → write-up. |
| `gap31-tier-taxonomy-predictions.md` | T3 | Q057. 3-tier grounding failure taxonomy (Codec/Connector/LLM backbone) with predicted gc(k) signatures per tier. Falsifiable predictions for Paper A §4. |
| `paper-a-abstract-v07.md` | T3 | Q062. Paper A abstract v0.7 (~156 words). Includes Gap #28 (Lee et al.), MPAR², 3-tier taxonomy, diagnostic protocol. LaTeX-ready. |
| `paper-a-gap-matrix.md` | T3 | Q058. Related work gap matrix: 8 prior papers × 5 dimensions. Confirms Paper A's 2×2 positioning. |
| `paper-a-submission-checklist.md` | T3 | Q060. Section status + venue decision table (Interspeech 2026 vs NeurIPS vs EMNLP). §1-§4 LaTeX-ready; §5 blocked on experimental results; figures pending E1/E2. |
| `saelens-audio-plugin-design.md` | T2 | Q061. Design doc for SAELens audio plugin (Whisper/HuBERT support). 3-file implementation plan: audio_model_hook.py, audio_dataset.py, audio_sae_runner.py. Addresses Gap #19. |

---

## 4. Queue Health

### Status Counts

| Status | Count |
|---|---|
| ready | 26 |
| blocked | 3 |
| **Total active** | **29** |
| Archived | 77 |
| Max tasks (configured) | 28 |

**Note**: Queue is over max_tasks by 1 (29 vs 28 cap). Last updated: 2026-03-18.

### Blocked Tasks

| ID | Track | Title | Blocker |
|---|---|---|---|
| Q001 | T3 | Phonological geometry through connector | Leo approval + real speech .wav + venv setup |
| Q002 | T3 | IIT experiment: Triple Convergence Causal Test | Leo approval + real speech .wav + venv |
| Q003 | T3 | Listen Layer Paper: ALME conflict patching on Qwen2-Audio | GPU access (Qwen2-Audio-7B) |

All blocked tasks require real model execution. Q001/Q002 could run on CPU (Whisper-tiny); Q003 needs GPU.

### Ready Task Breakdown

- **T3**: Q085, Q089, Q091, Q092, Q093, Q094, Q096, Q105, Q107, Q109, Q111, Q113, Q116, Q117, Q118, Q119, Q121, Q122, Q123, Q124, Q125, Q127 (22 tasks)
- **T5**: Q106, Q120, Q126, Q128 (4 tasks)

### Consolidation Candidates

| Tasks | Relationship | Recommendation |
|---|---|---|
| Q085, Q089, Q093 | Overlapping: collapse onset, temporal gc × AND/OR gate, collapse onset × AND-gate | Q093 supersedes Q085 in scope; consider archiving Q085 |
| Q111, Q116 | Q116 ("Backdoor=cascade induction") supersedes Q111 ("t* backdoor detection") | Archive Q111 |
| Q117, Q119 | Same day, both address GSAE graph density and edge density | Merge into single design doc task |
| Q092 | Synthesis of Q080+Q082 outputs (both scripts already built) | Scope as quick synthesis, not full build |

### active.json Health

- **Phase**: explore-fallback (since 2026-03-09)
- **Build budget today**: 0 (exhausted)
- **Learn remaining**: 3 | **Reflect remaining**: 2
- **Phase exit criteria**: `eval_harness_exists_T3` ✓ | `experiment_spec_ready_T3` (partial) | `leo_approved_gpu_or_cpu_experiment` ✗
- **Total cycles**: 221 | **Total skips**: 43 (19.5%)

---

## 5. Cleanup Candidates

The following scripts have issues worth flagging. **Do NOT delete — review and decide.**

| Script | Issue | Reasoning |
|---|---|---|
| `sae_adversarial_calibrator.py` | Likely superseded | Both this (257 lines, no docstring, stdlib only) and `sae_adversarial_detector.py` (729 lines, full docstring, numpy) address Q041. The calibrator appears to be an earlier lightweight version. |
| `gc_text_probe.py` | Orphaned / low priority | Only script targeting text LLMs (GPT-2). Not referenced by any test or runner. No linked cycle creation doc found. Cross-modal gc universality (Q010) not actively queued. |
| `gc_incrimination_env3.py` | Fragile import | Uses `importlib.util.spec_from_file_location` to load gc_incrimination_mock.py — breaks on path change. Not broken now but worth fixing if either file moves. |

No scripts are truly dead (empty or broken imports). The codebase is in good shape structurally.

---

## 6. Recommendations

### Immediate (unblocks the critical path)
1. **Run Q001 or Q002 on CPU** — whisper-tiny runs on MacBook M3 with no GPU. Both tasks have `real speech .wav` as a blocker but `t3_readiness_check.py` can verify the environment in minutes. Completing either unlocks the `converge → execute` phase transition and exits explore-fallback.

2. **Freeze new ideation** until ≥10 ready tasks are built or explicitly scoped out. At 26 READY and 0 build budget, continued ideation only deepens the backlog without advancing the paper.

### Short-term (this week)
3. **Archive Q085, Q111** — both superseded by newer tasks (Q093, Q116). Keeps the queue meaningful.

4. **Merge Q117+Q119** into a single GSAE design doc task. They address the same graph-density question from different angles and were created the same day.

5. **Add docstring to `sae_adversarial_calibrator.py`** or mark it explicitly as superseded by sae_adversarial_detector.py. The missing docstring is the only script in the corpus without one.

### Medium-term (paper A milestone)
6. **Run E1 and E2** (the two experiments listed as blocking §5 and figures in paper-a-submission-checklist.md). These are the actual gap between the current all-mock state and a submittable paper.

7. **Add tests for high-complexity mocks**: gc_incrimination_mock (552 lines), sae_adversarial_detector (729 lines), sae_incrimination_patrol (647 lines), synthetic_stimuli (900 lines) — these are the largest scripts with no test coverage and the most regression risk.

8. **Fix dynamic import in gc_incrimination_env3.py** — convert `importlib.util.spec_from_file_location` to a standard relative import or add gc_incrimination_mock to a package.

### What to keep (everything essential)
- `gc_eval.py` — central harness, do not modify without running test_gc_eval.py
- `synthetic_stimuli.py` — largest file, core data generator for all T3+T5 experiments
- `unified_eval.py` — JSON schema output consumed by downstream scripts
- All 7 design docs — paper-ready artifacts
- All test_*.py files — CI foundation

---

*Report generated: 2026-03-18 | Read-only audit — no files modified or deleted*
