
## 2026-03-19 Q109 follow-up

- **phoneme_mdas.py**: CPU build. Load Whisper-base, extract SAE activations at each encoder layer for minimal-pair audio (/p/–/b/, /t/–/d/, /k/–/g/). Compute per-feature Cause(voicing) and Isolate(voicing|place) via regression. Output: layer×feature (Cause, Isolate) matrix. Add to queue when slots free up (currently at 29/25 — needs cleanup).

## 2026-03-19 Ideation Cycle c-20260319-1645 (FREEZE — 20 ideas)

**Seeds used**: T3/T5 tracks, AND/OR gate results, RAVEL/MDAS, T-SAE, Phoneme-MDAS, GSAE, Codec Probe, Schelling stability, collapse onset, Jacobian SVD, emotion neurons, persona analysis, ENV taxonomy, AudioSAE, SPIRIT, RAVEL, Power Steering

---

### I-BL-001 [novelty:5, feasibility:4] — T-SAE × Phoneme-MDAS: ID component disentangles phoneme categories
**Cross**: T-SAE (Bhalla ICLR 2026) × Phoneme-MDAS × RAVEL Cause/Isolate  
**Hypothesis**: T-SAE input-invariant (ID) component at peak gc layer has lower phoneme Cause but higher voicing Isolate than input-dependent component. ID component = phoneme-class agnostic "carrier"; input-dep = contrastive discriminator.  
**Mock**: Split T-SAE components; measure Cause(voicing)/Isolate(voicing|place) per component; expect ID: low-Cause, high-Isolate.  
**Why novel**: Connects T-SAE decomposition to phonological feature geometry — not done in any known paper.

### I-BL-002 [novelty:5, feasibility:4] — SPIRIT-Style Intervention × AND-Gate Features: causal steering of audio behavior
**Cross**: SPIRIT (Djanibekov et al., EMNLP 2025) × AND/OR gate × persona analysis  
**Hypothesis**: SPIRIT-style contrastive steering vectors applied only to AND-gate features (audio+text conjunctive) produce stronger causal behavior change than full-feature steering, because AND-gates are the "decision bottlenecks" where audio and text evidence must co-activate.  
**Mock**: Select AND-gate features at gc peak layer; compute contrastive direction; measure WER delta vs random steering.  
**Why novel**: SPIRIT doesn't distinguish gate type; AND-gate targeting is a principled improvement.

### I-BL-003 [novelty:4, feasibility:5] — collapse_onset_step × phoneme-MDAS: do poorly-disentangled features cause earlier t*?
**Cross**: collapse_onset_step (Q085) × Phoneme-MDAS bleed metric  
**Hypothesis**: Features with high bleed (low-D, mixed phoneme selectivity) are causally upstream of early t* collapse. High-bleed features are "confused" AND-gates that trigger cascade prematurely.  
**Mock**: Correlate per-feature bleed D vs earliest layer where feature deactivates. Pearson r expected < 0 (high bleed → earlier deactivation).  
**Why novel**: Connects two novel metrics; first mechanistic link between feature disentanglement quality and collapse onset.

### I-BL-004 [novelty:5, feasibility:3] — AudioSAE × ENV Taxonomy on Real Whisper: validate ENV-1/2/3 with real SAE features
**Cross**: AudioSAE v1 (EACL 2026) × ENV taxonomy × GSAE topology  
**Hypothesis**: Using a real AudioSAE trained on Whisper-base, ENV-1 hub features are semantically interpretable (phoneme/word level), ENV-3 isolated features encode spectral details, ENV-2 features encode prosodic context.  
**Build**: Load AudioSAE weights; compute feature co-activation graph; apply ENV taxonomy; manually inspect top-activating examples per ENV type.  
**Why novel**: ENV taxonomy not yet validated on audio domain; first empirical test.

### I-BL-005 [novelty:4, feasibility:5] — Schelling × Phoneme-MDAS: IIA-stable features are phoneme-disentangled (low bleed)
**Cross**: Schelling IIA stability × Phoneme-MDAS bleed (D metric)  
**Hypothesis**: Features stable across SAE training seeds (Schelling Focal Points) have significantly lower bleed D, i.e., they consistently specialize in one phoneme class across seeds. Unstable features = confused, high-bleed.  
**Mock**: Compute mock IIA stability scores and D scores per feature; Pearson r(stability, D) expected > 0.6.  
**Why novel**: Connects seed stability (robustness) to phonological specialization quality.

### I-BL-006 [novelty:5, feasibility:4] — FAD Bias × T* Early Warning: text-predictable phonemes trigger earlier T-SAE deactivation
**Cross**: FAD encoder bias (Gui et al., Interspeech 2026) × T-SAE early warning × collapse onset  
**Hypothesis**: When the model encounters text-predictable phonemes (high FAD bias), T-SAE ID component deactivates earlier (lead_ahead > 2 steps) because the model "decides" to ignore audio before full processing. Audio-dependent phonemes (low bias) show lead_ahead ≤ 1.  
**Mock**: Stratify utterances by text-predictability score; measure lead_ahead per stratum.  
**Why novel**: Mechanistic explanation for why FAD bias manifests as different gc collapse timing.

### I-BL-007 [novelty:4, feasibility:5] — ENV-3 pruning × persona manipulation: removing isolated features suppresses jailbreak-induced persona shift
**Cross**: ENV-3 pruning × persona analysis (Q121 design) × emotion neurons  
**Hypothesis**: Jailbreak persona injection primarily hijacks ENV-3 isolated features (low GSAE connectivity). Pruning ENV-3 at persona tokens restores neutral AND/OR gate ratio without damaging clean speech performance.  
**Mock**: Simulate persona token → ENV-3 activation → AND→OR ratio drop; apply ENV-3 mask → measure recovery.  
**Why novel**: ENV-3 pruning as a targeted persona defense; more precise than Q128's Isolate shift recovery.

### I-BL-008 [novelty:5, feasibility:3] — RVQ Codec × gc(k) Profile: semantic tokens (RVQ-1) have higher gc peak than acoustic tokens (RVQ-N)
**Cross**: Codec Probe RVQ (Q124) × gc(k) evaluation harness × RAVEL Isolate  
**Hypothesis**: When audio input is represented via RVQ tokens, RVQ-1 (semantic) tokens show higher gc(k) peak and higher argmin(Isolate) (later collapse) than RVQ-N (acoustic) tokens. Semantic tokens are harder to "ignore."  
**Mock**: Simulate RVQ-1/N activations with different Isolate profiles; compute gc proxy; compare collapse t* per token type.  
**Why novel**: First mechanistic link between codec layer and gc profile in speech-language models.

### I-BL-009 [novelty:4, feasibility:5] — Jacobian SVD direction × Phoneme-MDAS: top singular vector points toward low-bleed features
**Cross**: Jacobian SVD (Q122/Q127) × Phoneme-MDAS bleed D  
**Hypothesis**: The top Jacobian singular vector at gc peak layer aligns (high cosine-sim) with features that have low bleed D (well-disentangled phoneme features). High-bleed features are orthogonal to the principal manipulation direction — they're noise, not signal.  
**Mock**: Sample mock Jacobian; compute cosine-sim vs bleed quartile; expect monotone decrease with bleed.  
**Why novel**: Connects gradient-based feature importance to phonological disentanglement quality.

### I-BL-010 [novelty:5, feasibility:4] — AND-gate × AAPE neuron: are speech-specific AAPE neurons AND-gates?
**Cross**: AAPE neuron dissection (Kawamura, 2602.15307) × AND/OR gate classification × AudioSAE  
**Hypothesis**: AAPE (Audio-Aligned Prediction Error) neurons, which activate when audio contradicts text prediction, are predominantly AND-gates — they require both an audio signal AND a text prediction to compare. OR-gate AAPE neurons don't exist because the comparison function inherently needs both modalities.  
**Mock**: Label mock neuron set as AAPE vs non-AAPE; measure AND fraction; expect AAPE AND-frac > 0.85.  
**Why novel**: AAPE paper doesn't characterize gate type; AND-gate interpretation gives mechanistic explanation for AAPE function.

### I-BL-011 [novelty:4, feasibility:4] — Causal Abstraction × Phoneme-MDAS: verify abstract phoneme graph maps to concrete SAE feature graph
**Cross**: Causal Abstraction / IIT (Geiger et al.) × Phoneme-MDAS × GSAE  
**Hypothesis**: The abstract causal graph of phonological features (voicing → stop/fricative → phoneme identity) maps to a concrete SAE feature subgraph via causal abstraction. Features with low bleed D are the concrete variables of this abstract phonology model.  
**Build**: Define 3-node abstract causal graph (voicing, place, phoneme); run IIT alignment test with mock SAE features; measure tau-score.  
**Why novel**: Applies causal abstraction framework to phonology in speech models — novel application domain.

### I-BL-012 [novelty:5, feasibility:4] — T* collapse × multimodal modality collapse (Zhao et al.): same phenomenon, different framing?
**Cross**: collapse_onset_step t* × Zhao et al. "Modality Collapse" [lm, multimodal] × ALME conflict benchmark  
**Hypothesis**: The t* collapse phenomenon in audio LMs is a fine-grained, token-level manifestation of modality collapse (Zhao et al.). Specifically, t* corresponds to the decoder step where the audio modality stops contributing — the collapse is not global but step-wise. This unifies two literatures.  
**Build**: Design a bridge experiment: measure t* distribution on ALME conflict benchmark items; expect high-conflict items → earlier t*.  
**Why novel**: First mechanistic link between token-level audio collapse and modality collapse literature.

### I-BL-013 [novelty:4, feasibility:5] — GSAE edge density × phoneme pair similarity: phonologically similar phonemes share denser feature subgraphs
**Cross**: GSAE topology × phoneme analysis × Phonological Vector Arithmetic (Choi et al.)  
**Hypothesis**: Phonologically similar phoneme pairs (e.g., /p/–/b/ = minimal pair, 1 feature diff) share a denser GSAE subgraph (more shared edges) than dissimilar pairs (e.g., /p/–/s/). GSAE graph topology encodes the phonological feature space.  
**Mock**: Construct mock GSAE per phoneme pair; compute shared edge density; correlate with phonological distance.  
**Why novel**: Grounds the abstract phonological feature space in a concrete mechanistic graph structure.

### I-BL-014 [novelty:5, feasibility:3] — SAEBench × Phoneme-MDAS: disentanglement score as SAEBench metric #9
**Cross**: SAEBench (Karvonen, Nanda et al. ICML 2025) × Phoneme-MDAS bleed D × RAVEL  
**Hypothesis**: The Phoneme-MDAS bleed metric D (mean disentanglement across phoneme pairs) is a principled addition to SAEBench as a speech-domain disentanglement score. Define D-score per SAE, compute on Whisper SAEs, show variance across SAE hyperparameters.  
**Build**: Define D-score API compatible with SAEBench interface; run on mock SAE configs; show D correlates with other SAEBench metrics (expected: moderate correlation with absorption, not with loss).  
**Why novel**: First domain-specific (speech) disentanglement metric for SAEBench; publishable benchmark contribution.

### I-BL-015 [novelty:4, feasibility:5] — Schelling × AND-gate × T-SAE: triple stability = AND-gate + IIA stable + T-SAE ID component
**Cross**: Schelling stability × AND/OR gate × T-SAE ID component  
**Hypothesis**: Features satisfying all three: (1) AND-gate (requires both modalities), (2) IIA-stable across seeds, (3) T-SAE ID-component (input-invariant direction) — are the most "canonical" audio-language features. These triple-stable features likely encode phoneme-class-level abstractions.  
**Mock**: Assign random binary labels to 100 features for each property; compute overlap; expect AND ∩ IIA ∩ ID has AND-fraction > 0.9, low bleed D.  
**Why novel**: First characterization of triply-stable features; proposes a principled canonicalization of audio features.

### I-BL-016 [novelty:5, feasibility:4] — Collapse onset × ALME conflict grading: t* as difficulty predictor for audio-text conflicts
**Cross**: collapse_onset_step (Q085) × ALME conflict benchmark × FAD bias  
**Hypothesis**: On ALME benchmark items, t* (audio info collapse step) is an accurate predictor of item difficulty — easy conflicts (salient audio–text mismatch) have late t* (audio is processed longer), hard conflicts (subtle mismatch) have early t*. t* could be used as an automatic difficulty grader.  
**Build**: Simulate ALME-style items with varying conflict salience; compute t* per item; correlate with human error rate proxy.  
**Why novel**: t* as automatic benchmark difficulty metric — first such use of mechanistic diagnostic for benchmark calibration.

### I-BL-017 [novelty:4, feasibility:5] — Backdoor detection pipeline: t* < 3 → flag → ENV-3 pruning → t* recovery
**Cross**: Backdoor detection (Q116) × ENV-3 pruning (Q128) × collapse onset  
**Hypothesis**: Full pipeline: (1) detect early t* collapse (t* < threshold), (2) identify anomalous ENV-3 features active at t*, (3) prune those features, (4) verify t* recovery. If recovery successful, confirms backdoor was mediated by ENV-3 isolated features.  
**Build**: mock_backdoor_pipeline.py: 4-step pipeline; measure precision/recall on synthetic clean/poisoned examples.  
**Why novel**: First end-to-end mechanistic backdoor detection + mitigation pipeline; connects Q116 and Q128.

### I-BL-018 [novelty:5, feasibility:4] — UniWhisper NWA probe × gc(k): does NWA probe accuracy track gc(k) across layers?
**Cross**: UniWhisper NWA (No-Word-Audio) probe × gc(k) evaluation harness × RAVEL Isolate  
**Hypothesis**: The NWA probe accuracy (which predicts whether audio contains a word) mirrors the gc(k) profile across encoder layers — both peak at the same layer. gc(k) = mechanistic substrate of NWA probe success.  
**Mock**: Simulate NWA probe accuracy and Isolate(k) per layer; compute Pearson r; expect r > 0.8.  
**Why novel**: Connects behavioral probe (NWA) to mechanistic measure (gc); first bridge between UniWhisper and MI × Speech agenda.

### I-BL-019 [novelty:4, feasibility:5] — Emotion neurons × AND-gate × ENV taxonomy: emotion AND-gates = ENV-2 (contextual hub)?
**Cross**: Emotion neurons (Zhao et al. 2601.03115) × AND/OR gate × ENV taxonomy × GSAE  
**Hypothesis**: Emotion-coding features that are AND-gates (Q118: AND-frac=77.5%) map to ENV-2 in the GSAE taxonomy — they are contextual intermediaries connecting audio ENV-3 (acoustic fine features) to language ENV-1 (semantic hubs). ENV-2 position explains why both audio and language input is required.  
**Mock**: Assign GSAE connectivity scores to mock emotion features; compute ENV type distribution; expect ENV-2 enrichment among AND-gate emotion features.  
**Why novel**: Proposes mechanistic topology explanation for emotion feature gate type; connects Q119 and Q118.

### I-BL-020 [novelty:5, feasibility:3] — SAEBench audio × DashengTokenizer: best SAE hyperparams differ between codec tokens and raw audio
**Cross**: SAEBench metrics × DashengTokenizer (2026) × AudioSAE v1 × RVQ Codec Probe  
**Hypothesis**: The optimal SAE width and L1 coefficient differ when training SAEs on Dasheng semantic tokens vs Whisper raw encoder activations. Dasheng tokens (discrete, semantic) favor narrower, sparser SAEs; Whisper activations (continuous, mixed) favor wider, denser SAEs. This can be verified via SAEBench score comparison.  
**Build**: Design experiment spec: SAE hyperparameter sweep on mock Dasheng vs Whisper-style activations; measure D-score (I-BL-014) and absorption as primary metrics.  
**Why novel**: First comparative SAE architecture study for speech-domain — addresses a real gap in SAEBench's speech coverage.

---
*Cycle: c-20260319-1645 | Phase: converge | FREEZE: all 20 → backlog only*
