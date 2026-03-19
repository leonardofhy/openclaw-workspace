# Autodidact Cycle Summary — 2026-03-18

## Real Experiments (first ever on this system)

### Q001: Voicing Vector Geometry (Whisper-base)
- **Script**: `q001_voicing_geometry.py`
- **Method**: Extract voicing direction vectors from minimal pairs (t/d, p/b, k/g, s/z) at each encoder layer
- **Result**: Layer 5 peak (cos_sim=0.155). Stop-stop weak alignment (+0.25), stop-fricative orthogonal (+0.06)
- **Interpretation**: Whisper-base has partial linear phonological structure, but too small for strong results. Needs larger model (Whisper-small/medium multilingual).
- **Paper A relevance**: Direct evidence for encoder layer analysis methodology

### Q002: Layer-wise Causal Contribution (Activation Patching)
- **Script**: `q002_causal_contribution.py`
- **Method**: Zero/noise/mean ablation of each encoder layer, measure WER degradation
- **Result**: ALL layers critical — WER=1.0 on any single-layer ablation
- **Interpretation**: Whisper distributes information across all layers; no redundant layers. Differs from text LLMs where middle layers can be ablated.
- **Paper A relevance**: Confirms distributed encoding hypothesis

## Mock Experiments (batch run)

### E1-E5 (existing scripts, first formal execution)
| ID | Script | Key Finding |
|----|--------|------------|
| Q089 | and_or_gc_patching_mock | AND% × gc(k) r=0.9836, peak at L3 |
| Q039 | persona_gc_benchmark | Anti-ground shifts 2 layers early (H2+H3 ✅) |
| Q069 | gc_incrimination_mock | t* detection: error_token=3.4, sudden_collapse=2.7 |
| Q078 | sae_incrimination_patrol | Suppression 96%, override 77% detection |
| Q053 | microgpt_ravel | RAVEL 5/6 pass (83.3%), speaker_gender fully disentangled |

## System Milestones
- **Phase transition**: Criteria 1/3 unlocked (leo_approved_gpu_or_cpu_experiment)
- **Ideation freeze**: Activated (READY queue at 22, threshold <10 to resume)
- **Total completed today**: 7 experiments (2 real + 5 mock)
