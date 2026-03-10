# Audio-RAVEL Benchmark Protocol Spec
# AudioSAEBench Category 0 — Causal Disentanglement via Cause/Isolate Scoring

> Created: 2026-03-06 (cycle Q047, autodidact c-20260306-0501)
> Track: T2 (AudioSAEBench — Paper B)
> Status: Draft specification — Tier 0 doc (no GPU required to write)
> Depends on: RAVEL (Huang et al. ACL 2024), Choi et al. 2602.18899, AudioSAE (EACL 2026)
> Definition of Done: Stimulus design + MDAS baseline + Cause/Isolate implementation plan

---

## 1. What is Audio-RAVEL?

**RAVEL (Huang et al. ACL 2024)** introduced a two-score metric for evaluating whether text LM
representations truly disentangle entity attributes:

- **Cause(F, A)** = does patching feature F cause attribute A to change as predicted? (localization)
- **Isolate(F, A)** = does patching feature F leave all OTHER attributes unchanged? (isolation)
- **RAVEL score** = harmonic mean of Cause and Isolate (penalizes both non-localization and leakage)

**Audio-RAVEL** is the speech analogue:
- Entity → audio stimulus (spoken word/utterance)
- Attribute → phonological feature (voicing, manner, place, ...)
- Interchange intervention → patch an SAE feature during Whisper encoder pass
- Score → same Cause/Isolate/RAVEL formula

**Why it matters**: AudioSAE (Aparin et al. EACL 2026) shows >50% feature consistency across seeds
but NEVER measures Isolate. RAVEL showed that in text LMs, SAEs score well on Cause but FAIL on
Isolate. Audio SAEs are expected to fail Isolate even MORE due to acoustic co-occurrence (voiced
stops co-occur with gender markers; pitch co-occurs with affect) — audio attributes are physically
correlated at the signal level in ways text attributes are not.

---

## 2. Stimulus Design

### 2.1 Phonological Attribute Set (starter: 3 attributes, 2 levels each)

| Attribute    | Level 0        | Level 1         | Example contrast   |
|-------------|-----------------|------------------|--------------------|
| Voicing      | Voiceless [t,p,k] | Voiced [d,b,g] | /t/ vs /d/ |
| Manner       | Plosive [t,d,p,b,k,g] | Fricative [s,z,f,v] | /t/ vs /s/ |
| Place        | Labial [p,b,m,f,v] | Alveolar [t,d,n,s,z] | /p/ vs /t/ |

### 2.2 Primary Stimulus Source: Choi et al. 2602.18899
- Validated minimal pairs across 96 languages (phonological vector arithmetic confirmed linear)
- Stimuli already designed to isolate single phonological features
- Available: `github.com/[choi-lab]/phonological-minimal-pairs` (check repo in cycle prep)
- Selection: English subset; match for speaker identity, duration, recording conditions
- **Target**: 100 minimal pairs per attribute (300 total for starter spec)

### 2.3 Backup: TTS-Augmented Pairs
If Choi et al. corpus not fully accessible:
1. Use CMU Pronouncing Dictionary to identify minimal pairs (e.g., /t/ vs /d/ in "tip" vs "dip")
2. Synthesize with Coqui-TTS or pyttsx3 (CPU-only) at consistent speaker identity
3. Match duration via time-stretching (Sox or librosa)
4. Trade-off: synthetic audio less naturalistic; TCS(F) results may be easier (no background noise)

### 2.4 RVQ-Layer Selective Corruption (Gap #21 integration)
For attribute-specific corruption (clean/corrupt axis in Cause measurement):
- Use **SpeechTokenizer** RVQ Layer 1 = semantic content; Layers 2-8 = acoustic details
- **Content corruption**: swap Layer 1 token to opposite phoneme class; keep Layers 2-8 fixed
  → changes phonological content while preserving voice quality, speaking rate, affect
- **Acoustic corruption** (control): swap Layers 2-8 only; keep Layer 1 fixed
  → changes acoustic quality but preserves phoneme identity (control for Cause test)
- This gives the CLEANEST possible minimal pair stimuli available for audio patching

---

## 3. SAE Feature Patching Protocol

### 3.1 Cause(F, A) — Localization Test

```
Algorithm Cause(F, A):
  For each stimulus pair (clean_stim, corrupt_stim) s.t. stim_A(clean) ≠ stim_A(corrupt):
    
    1. Run clean_stim through Whisper encoder; cache all layer activations
    2. Run corrupt_stim through Whisper encoder; cache all layer activations
    
    3. At layer L (sweep L in {0..11} for Whisper-large, {0..5} for Whisper-small):
       a. Decompose clean activation a_L using the SAE: a_L ≈ Σ_i c_i * f_i
       b. Find features F_A = {f_i | f_i has high alignment with attribute A}
          (alignment criterion: cosine(f_i, A_direction) > threshold θ, default θ=0.3)
       c. Patch: replace a_L[F_A] with values from corrupt activation a_L_corrupt[F_A]
       d. Run decoder from layer L+1 onward on patched activation
       e. Measure behavior change: does phoneme classification of output match corrupt label?
    
    4. Cause(F_A, A) = P(behavior matches corrupt | F_A patched)
       — averaged over all (clean, corrupt) pairs for attribute A
```

**Primary behavior metric**: phoneme classification accuracy delta
- Use Whisper's internal token probabilities (logit lens) at final decoder output
- Prefer `logit_diff` over `logprob` for stability (Heimersheim & Nanda recommendation)
- Report per-phoneme-class breakdown (voicing may be easier than manner)

### 3.2 Isolate(F, A) — Isolation Test

```
Algorithm Isolate(F, A):
  For each "orthogonal" attribute B ≠ A:
    For each stimulus pair (stim1, stim2) that DIFFERS on A but is MATCHED on B:
      
      1. Patch F_A as above
      2. Measure: does patching F_A change the model's classification of attribute B?
      
  Isolate(F_A, A) = 1 - P(attribute B changes | F_A patched)
                  -- averaged over all orthogonal attribute pairs (A, B)
```

**Key challenge**: finding stimulus pairs that differ on A but are matched on B
- /t/ vs /d/ (voicing contrast): matched on manner (both plosive), matched on place (both alveolar)
- /p/ vs /b/ (voicing contrast): matched on manner (both plosive), matched on place (both labial)
- /s/ vs /z/ (voicing contrast): matched on manner (both fricative), matched on place (both alveolar)
- The Choi et al. corpus is specifically designed for this: phonological vector arithmetic = attributes vary independently

### 3.3 RAVEL Score Computation

```python
def ravel_audio(cause_score: float, isolate_score: float) -> float:
    """RAVEL score = harmonic mean of Cause and Isolate."""
    if cause_score + isolate_score == 0:
        return 0.0
    return 2 * (cause_score * isolate_score) / (cause_score + isolate_score)
```

**Report structure (per SAE × per attribute)**:
```
SAE: AudioSAE-Whisper-L12   Attribute: Voicing
Cause(F_voicing, voicing): 0.75
Isolate(F_voicing, voicing): 0.31   ← expected to be low for audio
RAVEL-audio: 0.44
Cross-attribute leakage: manner=0.18, place=0.12  ← which attributes leak
```

---

## 4. MDAS Ceiling Baseline

**MDAS (Multi-task DAS, from RAVEL paper)** = simultaneously optimizes all attribute subspaces
to be orthogonal → achieved RAVEL≈0.85 for text LMs = theoretical ceiling.

**Audio-RAVEL MDAS setup**:
1. Define K = 3 phonological attributes (voicing, manner, place)
2. For each attribute k, find direction d_k in Whisper encoder layer L via DAS
   - Objective: d_k maximally predicts attribute k, minimally predicts attributes j≠k
   - Use pyvene `RotatedSpaceIntervention` with K-dimensional rotation matrix
   - Multivariate DAS loss = IIA loss summed over all K attributes + orthogonality penalty:
     `L = -Σ_k IIA(d_k, A_k) + λ * Σ_{k≠j} |d_k · d_j|`
3. The MDAS ceiling = RAVEL score achieved by this optimal linear disentanglement
4. Report: actual SAE RAVEL / MDAS ceiling ratio = "disentanglement efficiency"

**Prediction**: MDAS ceiling for audio ≈ 0.85 (same as text, since linear phonological geometry
is confirmed by Choi et al.). SAEs will achieve ≈ 0.44 (51% of ceiling). Matryoshka SAEs ≈ 0.60
(70% of ceiling). This efficiency gap is the primary finding.

---

## 5. SAE Scope for Category 0

**SAEs to benchmark in initial run**:
| SAE | Model | Architecture | Source |
|-----|-------|-------------|--------|
| AudioSAE-L1 | Whisper-small | TopK | Aparin EACL 2026 |
| AudioSAE-L6 | Whisper-small | TopK | Aparin EACL 2026 |
| AudioSAE-L12 | Whisper-small | TopK | Aparin EACL 2026 |
| HuBERT-SAE-L6 | HuBERT-base | TopK | Mariotte ICASSP 2026 |
| WavLM-SAE-L6 | WavLM-base | TopK | Mariotte ICASSP 2026 |
| AudioSAE-Matryoshka* | Whisper-small | Matryoshka | Paper B contribution |
| AudioSAE-T-SAE* | Whisper-small | T-SAE | Idea #7 contribution |

*= to be trained (GPU/workstation, Leo-gated). Starter run uses first 5 (pre-existing checkpoints).

---

## 6. Implementation Plan

### Phase 1: Stimulus Preparation (CPU, MacBook-feasible)
1. [ ] Download Choi et al. minimal pairs corpus (English subset)
2. [ ] Select 100 pairs × 3 attributes = 300 pairs; log metadata (phoneme, speaker, duration)
3. [ ] Generate RVQ-selective corruptions via SpeechTokenizer (CPU-feasible, <1h)
4. [ ] Validate: run Whisper ASR on all pairs; verify correct phoneme recognized

### Phase 2: SAE Feature Identification (CPU, MacBook-feasible)
1. [ ] Load AudioSAE L6/L12 weights (check if public release available in paper repo)
2. [ ] Run all 300 pairs through Whisper-small encoder; cache layer activations
3. [ ] Compute SAE decomposition: for each pair, identify top-k active features
4. [ ] Build attribute-feature alignment map: which features have cosine > 0.3 with known phoneme directions?
   - Phoneme directions: from Choi et al. voicing_vector = h([d]) - h([t]) at each layer
   - This step requires Choi et al. repo OR recompute from Choi et al. stimuli

### Phase 3: Cause/Isolate Scoring (CPU, MacBook-feasible)
1. [ ] Implement Cause algorithm (Section 3.1) in Python using pyvene hooks
2. [ ] Implement Isolate algorithm (Section 3.2) using matched pairs from corpus
3. [ ] Run scoring over 3 SAE checkpoints (AudioSAE L1, L6, L12) × 3 attributes
4. [ ] Compute RAVEL scores + leakage heatmap
5. [ ] Total compute: ~2-3 hours on MacBook (Whisper-small = 74M params, CPU-feasible)

### Phase 4: MDAS Ceiling (CPU, ~30min)
1. [ ] Implement MDAS objective in pyvene (K=3 attributes, orthogonality penalty λ=0.1)
2. [ ] Run DAS optimization per layer (5 layers × ~5 min/layer = 25 min total)
3. [ ] Report efficiency ratio = SAE RAVEL / MDAS ceiling

### Phase 5: Comparison Table
Produce Table 1 for Paper B:
- Rows: SAEs (5+ models)
- Columns: Cause, Isolate, RAVEL-audio, MDAS-efficiency, Leakage (top-1 attribute)
- Expected result: TopK SAEs all below 0.50 on RAVEL-audio; MDAS ceiling ~0.85

---

## 7. Connection to Paper B §3 (AudioSAEBench Category 0)

This protocol spec is the concrete implementation of §3 "Category 0: Audio-RAVEL" in paper-b-pitch.md §3 (v1.3+).

Key mappings:
- §3 "Cause(F, A)" equation → Section 3.1 above (algorithm specified)
- §3 "Isolate(F, A)" equation → Section 3.2 above (matched-pairs design)
- §3 "MDAS ceiling baseline" → Section 4 above (multivariate DAS loss formula)
- §3 "Choi et al. stimuli + RVQ Layer 1 corpus corruption" → Section 2.3+2.4 above
- §3 "audio leakage hypothesis (acoustic co-occurrence > text SAEs)" → Section 4 expected results

**Expected additions to Paper B from this protocol:**
1. Algorithm box for Cause/Isolate implementation (ready from Section 3 above)
2. Stimulus selection details (Appendix A — from Section 2)
3. MDAS implementation details (Appendix B — from Section 4)
4. Table 1 structure (ready from Section 6 Phase 5)

---

## 8. Open Questions (Leo-gated)

1. **AudioSAE checkpoint access**: Are the Aparin et al. EACL 2026 SAE checkpoints public?
   Check: paper repo / HuggingFace `aparin` author page. If not public, need to train from scratch.

2. **Choi et al. corpus access**: Is the minimal pairs corpus (2602.18899) publicly released?
   Check: paper repo / supplementary. If not, use CMU Dict + TTS fallback (Section 2.3 backup).

3. **Threshold θ for feature-attribute alignment** (Section 3.1): default θ=0.3 needs calibration.
   Validate: run θ ∈ {0.1, 0.2, 0.3, 0.5} and check stability of Cause scores. Report best θ.

4. **Layer sweep for Cause/Isolate**: which layer gives the highest Cause for voicing features?
   Prediction (from AudioSAE): layer 12 for Whisper-large (layer 6 for Whisper-small).
   Run full sweep and report layer-wise Cause/Isolate heatmap as Figure 1 of Paper B.

5. **Leakage direction specificity**: do features leak specifically to PHONOLOGICALLY RELATED
   attributes (e.g., voicing → manner) or randomly? If structured leakage → suggests shared
   neural pathways for co-articulation features → new insight about speech representation geometry.
