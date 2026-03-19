# Archived Autodidact Scripts

**Archived:** 2026-03-18
**Reason:** Code review (docs/code-review-2026-03-18.md, S1) identified ~49 orphaned experimental scripts no longer referenced by any queue task, test, or active import chain.

**Method:** Cross-referenced every `.py` in `scripts/` against:
1. Active + archived queue tasks (`queue.json`)
2. Inter-script imports (grep for `import`/`from` across all scripts)
3. Test file imports (`test_*.py`)
4. Core utility list: `gc_eval.py`, `synthetic_stimuli.py`, `unified_eval.py`, `unified_results_dashboard.py`, `plot_*.py`

Scripts that were NOT referenced by any of the above were moved here.

## Stats

- **53 files**, **18,819 LOC** archived
- Conservative approach: scripts with results data, active queue references, or test imports were kept

## Archived Files

| File | Description |
|---|---|
| and_gate_schelling_stability.py | AND-gate Schelling stability experiment |
| and_or_gc_patching_mock.py | AND/OR GC patching mock |
| audio_incrimination_graph.py | Audio incrimination graph analysis |
| audio_sae_bench.py | Audio SAE benchmark |
| audiosaebench_integration.py | AudioSAEBench integration |
| backdoor_cascade.py | Backdoor cascade experiment |
| codec_probe_and_or.py | Codec probe AND/OR gate |
| collapse_onset_and_or.py | Collapse onset AND/OR analysis |
| delta_gs_single_layer.py | Delta-GS single layer experiment |
| directed_isolate_mock.py | Directed isolate mock |
| emotion_and_or_gate.py | Emotion AND/OR gate experiment |
| env_codec_rvq.py | Environment codec RVQ |
| env_gsae_topology.py | Environment GSAE topology |
| fad_and_or_gate.py | FAD AND/OR gate experiment |
| gc_divergence_thermometer.py | GC divergence thermometer |
| gc_hallucination_mock.py | GC hallucination mock |
| gc_incrimination_env3.py | GC incrimination env3 |
| gc_incrimination_mock.py | GC incrimination mock |
| gc_probe_v1.py | GC probe v1 |
| gc_schelling_mock.py | GC Schelling mock |
| gc_text_probe.py | GC text probe |
| gc_visualizer.py | GC visualizer |
| incrimination_jacobian.py | Incrimination Jacobian analysis |
| jailbreak_isolate_env.py | Jailbreak isolate environment |
| jalmsbench_eval_harness.py | JALMS benchmark eval harness |
| m4_pcds.py | Milestone 4 PCDS experiment |
| m7_spurious.py | Milestone 7 spurious features |
| m8_geometry.py | Milestone 8 geometry experiment |
| m9_delta_gs_cross_correlation.py | M9 delta-GS cross correlation |
| m9_gated_dual_detector.py | M9 gated dual detector |
| m9_online_consistency_monitor.py | M9 online consistency monitor |
| microgpt_phon_das_suite.py | MicroGPT phoneme DAS suite |
| microgpt_ravel.py | MicroGPT RAVEL experiment |
| microgpt_sae.py | MicroGPT SAE experiment |
| online_delta_gs_monitor.py | Online delta-GS monitor |
| persona_and_or_gate.py | Persona AND/OR gate |
| persona_emotion_and_or.py | Persona emotion AND/OR |
| persona_gc_benchmark.py | Persona GC benchmark |
| persona_gc_temporal.py | Persona GC temporal |
| phoneme_mdas.py | Phoneme MDAS experiment |
| phoneme_schelling_iia.py | Phoneme Schelling IIA |
| power_steering_and_or.py | Power steering AND/OR gate |
| ravel_isolate_gc_proxy.py | RAVEL isolate GC proxy |
| ravel_mdas_and_or.py | RAVEL MDAS AND/OR |
| sae_adversarial_calibrator.py | SAE adversarial calibrator |
| sae_adversarial_detector.py | SAE adversarial detector |
| sae_incrimination_env_taxonomy.py | SAE incrimination env taxonomy |
| sae_incrimination_patrol.py | SAE incrimination patrol |
| schelling_and_or_gate.py | Schelling AND/OR gate |
| schelling_tsae.py | Schelling TSAE |
| tsae_gc_incrimination.py | TSAE GC incrimination |
| whisper_hook_demo.py | Whisper hook demo |
| whisper_logit_lens.py | Whisper logit lens |

## Restoring

To restore a script: `mv archive/<script>.py ../`
