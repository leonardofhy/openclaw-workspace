
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

## 2026-03-21 Ideation Cycle c-20260321-1415 (FREEZE — 20 ideas)

**Seeds used**: T3/T5 tracks, AND/OR gate (PPL×AND-frac, temporal t*, gate lifetime), FAD bias × RAVEL Cause/Isolate, ENV taxonomy × GSAE, RVQ codec hierarchy, stress × AND-gate, hallucination signature (Q134), jailbreak dual-signal (Q141), Schmidt Sciences RFP, t* backdoor detection, predictive coding frame

---

**I01** [T3] **RVQ-layer x AND-gate polarity: semantic RVQ-1 tokens → AND-gate, acoustic RVQ-N → OR-gate**
Novelty 5, Feasibility 4. Extend Q142 (RVQ×t*) to gate polarity. Hypothesis: RVQ-1 features that encode semantic content are AND-gated (audio+LM both required), while RVQ-N fine-grained acoustic features are OR-gated (audio alone sufficient). Testable with codec-feature mock + AND-frac by RVQ-layer stratification.

**I02** [T3] **Prosodic stress × t*: stressed syllables show later collapse onset (higher t*)**
Novelty 4, Feasibility 5. Q127 tests AND-frac for stress; this extends to temporal dimension. Stressed phonemes need more deliberate acoustic integration → longer t*. CMU ARPABET stress labels × t* across decoder steps. Pure CPU mock, minimal data.

**I03** [T3] **Early-warning hallucination: PPL spike → AND→OR transition prediction 2-3 steps ahead**
Novelty 5, Feasibility 4. Combine Q134 (hallucination=AND-dropout) + Q132 (PPL×gc). High PPL at t predicts AND→OR transition at t+2 or t+3. Proactive hallucination suppression: detect risk early, inject acoustic re-grounding. Design doc + mock.

**I04** [T5] **Cross-lingual hub transfer: ENV-1 hub features from English Whisper activate for Mandarin/Arabic phonemes**
Novelty 5, Feasibility 4. Extends Q145. Multilingual universal phoneme features are AND-gated (audio-dependent) because they must generalize beyond any one language's LM statistics. Test via synthetic multilingual audio pairs. Connects to cross-lingual transfer in interpretability.

**I05** [T3] **Isolate(k) as training regularizer: low-Isolate features as noise targets for fine-tuning**
Novelty 5, Feasibility 3. Novel application: use Isolate(k) computed on a pretrained Whisper to identify entangled features → add regularization loss to disentangle them during fine-tuning. Expected: lower WER on accent-heavy speech. Design doc only (CPU), no fine-tuning needed to specify.

**I06** [T3] **Dialect robustness x AND-gate compression: non-standard accent speakers → lower AND-frac**
Novelty 4, Feasibility 5. Speakers with accents deviating from training distribution produce lower AND-frac (model falls back to LM prior). Mechanistic account of accent bias. Mock: simulate accent shift by altering phoneme conditional entropy; measure AND-frac drop. Builds on FAD-bias × AND-OR quadrant.

**I07** [T5] **Real-time jailbreak monitor: streaming AND→OR ratio velocity (dAND-frac/dt) as safety signal**
Novelty 5, Feasibility 4. Extends Q141 (dual-signal detector) to streaming inference. Monitor the rate of change of AND-frac per decoder step; a sudden drop (high negative velocity) triggers early intervention before jailbreak completes. CPU-only, integrates with persona probe.

**I08** [T3] **gc(k) as gradient flow proxy: high gc features have largest gradient magnitude**
Novelty 5, Feasibility 3. Mechanistic hypothesis: features at gc peak = maximum information bottleneck = highest gradient. Test via hook-based gradient extraction at encoder layers × gc(k) values. If confirmed, gc(k) becomes a zero-cost gradient signal for saliency/attribution.

**I09** [T3] **AND-gate fatigue: sustained speech → AND-frac decay over utterance duration**
Novelty 4, Feasibility 5. Longer utterances → model increasingly relies on LM prior → AND→OR drift over time. Practical: call center ASR degrades for long calls. Mock: synthetic variable-length audio × AND-frac at end vs start of utterance. Slice into 30s windows.

**I10** [T3] **Phoneme co-articulation x GSAE edge weight: co-articulated phoneme pairs share GSAE graph neighbors**
Novelty 5, Feasibility 4. Phonological co-articulation (e.g., /p/ before /b/ nasalizes) should manifest as shared GSAE neighbors. Predict edge weight from phonological distance matrix. CPU-testable with existing GSAE mock infrastructure.

**I11** [T3] **t* as onset detection algorithm: compare to mel-filterbank onset detector**
Novelty 4, Feasibility 5. Use t* cliff (GSAE boundary mock, Q137) as an unsupervised acoustic onset detector. Benchmark against librosa onset_detect. No audio needed — mock via synthetic activations. Could be a paper contribution on Whisper's implicit onset tracking.

**I12** [T5] **Multimodal jailbreak hardness: vision+audio simultaneous AND-gate suppression harder to execute**
Novelty 5, Feasibility 3. Hypothesis: a successful multimodal jailbreak must suppress AND-gate features in BOTH vision and audio streams simultaneously. This structural constraint makes multimodal jailbreaks harder. Design doc argument + theoretical framing for MATS proposal.

**I13** [T3] **CTC spike × AND-frac alignment: CTC probability peak aligns with AND-gate activation at t***
Novelty 5, Feasibility 4. Mechanistic link: Whisper's CTC alignment head spikes at phoneme boundaries → these are also t* points. If AND-frac is high at CTC peaks, it confirms t* = acoustic integration completeness point. CPU: extract CTC probs via forward pass on mock data.

**I14** [T5] **ENV-1 hub attention flow: hub features receive disproportionate cross-layer attention**
Novelty 4, Feasibility 4. Use Whisper's attention maps to trace which features get the most cross-layer attention weight. Hypothesis: ENV-1 hub features (high out-degree in GSAE) also have highest incoming attention → dual centrality (graph + attention). Testable via attention pattern mock.

**I15** [T3] **MFCC baseline x AND-OR gate: traditional acoustic features are OR-gated (audio-sufficient)**
Novelty 4, Feasibility 5. Traditional MFCC features don't use LM context → they're pure acoustic → OR-gate. Use this as a ground-truth baseline for the AND/OR framework: verify that a linear probe trained on MFCCs gives 0% AND-gate features. Validates the framework's discriminative power.

**I16** [T5] **Schmidt RFP alignment doc: T5 = Aim 2 prototype (mechanisms of failure in AI)**
Novelty 3, Feasibility 5. Write an explicit alignment document: how Q129/Q141/Q134 + ENV taxonomy form a "mechanistic AI safety" prototype matching Schmidt Sciences RFP Aim 2. Key argument: T5 doesn't just detect jailbreaks, it localizes the failure mechanism. Deadline May 17 — timely.

**I17** [T3] **Jacobian sparsity × AND-gate: AND-gate features have sparse layer-to-layer Jacobian**
Novelty 5, Feasibility 3. Connection to Power Steering paper (Q147): stable, audio-grounded AND-gate features should have sparse Jacobian (low sensitivity to perturbation) → good steering targets. OR-gate features = dense Jacobian = unstable steering. Design doc; computation needs real model.

**I18** [T3] **AND-frac temporal slope as accent severity proxy: steepness of decay encodes speaker OOD-ness**
Novelty 5, Feasibility 5. The rate of AND→OR drift over an utterance encodes how much the model relies on LM (because acoustic features were insufficient). Steep negative slope = heavy accent deviation from training. Zero-cost OOD/accent detector. Mock: vary synthetic entropy per phoneme; measure slope.

**I19** [T3] **FAD-bias correction loop: AND-frac feedback signal to boost audio attention for high-entropy phonemes**
Novelty 5, Feasibility 4. Extends Q139 (AND-gate steering for FAD correction). Full feedback loop: monitor AND-frac in real-time → when it drops below threshold for high-PPL token → inject cross-attention boost toward audio encoder. Design spec for CPU-only intervention.

**I20** [T5] **Jailbreak trajectory analysis: temporal path of AND→OR transition across 10 decoder steps**
Novelty 4, Feasibility 5. Characterize not just the endpoint (AND-frac at final step) but the full trajectory. Clean audio: monotone AND-gate. Jailbreak: rapid drop at step 3-5. Adversarial: gradual erosion. Three trajectory signatures → classification via DTW. CPU mock, extends Q141.

---
**Top picks (novelty+feasibility ≥ 8):** I01, I03, I04, I07, I08, I10, I11, I13, I18, I19
**Note:** IDEATION FREEZE active (12 READY). All ideas held in backlog. Lift when READY < 10 or Leo approves.

## c-20260323-1345 Ideation Cycle (accent bias × AND-gate follow-ups)

Ideas that didn't make queue cut (queue full or N+F < 8):

10. **and_gate_intervention_eval_mock.py** (N=3, F=5, total=8): full eval pipeline connecting Q157+Q162+Q167 — steer AND-frac, measure WER+fairness delta per L1 group
11. **accent_isolation_mock.py** (N=4, F=5, total=9): Isolate curve shape classification for accented phonemes; expect more plateau-shaped = less audio-grounded
12. **l2arctic_full_pipeline_mock.py** (N=3, F=4, total=7): end-to-end: L2-ARCTIC utterance → gc(k) → AND-frac per phoneme → FAD score → WER prediction
13. **gc_whisper_size_accent.py** (N=3, F=4, total=7): does larger Whisper reduce accent AND-frac gap? fairness-via-scale hypothesis
14. **gsae_accent_boundary_mock.py** (N=3, F=4, total=7): GSAE boundary detector F1 drop for accented phoneme transitions
15. **temporal_and_gate_drift.py** (N=4, F=4, total=8): AND-frac drift across utterance for accented vs native; does commitment decay faster for accented speakers?
16. **multi_accent_cluster_mock.py** (N=4, F=4, total=8): ENV-3 style clustering for accented speech; L1 groups cluster by accent strength via AND-frac signature
17. **vcbench_accent_extension.py** (N=4, F=3, total=7): VLM fairness extension — do visual AND-gate features drop for minority-group images? (cross-modal FAD)
18. **t5_jailbreak_accent_mock.py** (N=4, F=3, total=7): accent as covert jailbreak vector — accented audio reduces AND-frac → safety probe misfires?
19. **speaker_aware_gc_mock.py** (N=3, F=3, total=6): gc(k) conditioned on speaker embedding; speaker-ID AND-gate shifts gc_peak
20. **accent_wer_cascade_mock.py** (N=3, F=5, total=8): cascade mock: AND-frac(accented) → phoneme confusion → WER; quantify each stage's contribution to FAD bias gap

