# §5 Discussion

## 5.1 gc(k) as a Unifying Metric

The grounding coefficient subsumes and extends two prior observational metrics:

- **AudioLens critical layer** (Ho et al., 2025): AudioLens identifies layers where auditory attribute information peaks via logit lens probing (Pearl Level 1). gc(k) provides the causal counterpart (Pearl Level 3) — the critical layer identified by AudioLens should coincide with or be near k*, but gc(k) additionally proves that this layer *causes* the model's output rather than merely correlating with it.

- **Beyond Transcription saturation layer** (Glazer et al., 2025): The saturation layer marks where the encoder "commits" to its transcription. gc(k) extends this concept beyond encoder-only models to the full encoder → connector → LLM pipeline, and replaces white-noise reference patching with phonological minimal-pair corruption.

[TODO: Formalize "Causal AudioLens" framing — gc(k) as the causal upgrade to logit-lens-based information scores]

The connection to the Triple Convergence hypothesis is suggestive: our mock experiments place k* at layer 3 in a 6-layer model (~50% depth), consistent with the prediction that semantic crystallization occurs at intermediate depth. If this holds in larger models (Whisper-small: layer ~6; Whisper-medium: layer ~12), it would support depth-proportional scaling of the listen layer.

[TODO: Verify Triple Convergence prediction with real gc(k) data across model scales]


## 5.2 AND-Gate Insight: Genuine Multimodal Processing

The AND/OR gate framework reveals a qualitative distinction between two modes of multimodal processing:

- **AND-gate dominance** (high α_AND): The model performs genuine audio-text integration. Neither modality alone suffices to reconstruct the relevant features. This is the hallmark of a "strong listener" — the model cannot produce correct outputs without consulting the audio signal.

- **OR-gate dominance** (high cascade degree κ): The model can recover relevant features from either modality alone. Text priors can fully substitute for audio input. This is the mechanism behind "sophisticated guessing" — the model may appear to listen (high task accuracy) while relying entirely on text context.

Key implications:

- Models with low α_AND at the listen layer are "sophisticated guessers" despite potentially high behavioral accuracy. Standard benchmarks cannot detect this failure mode; gc(k) + α_AND can.
- The cascade degree κ = 1 − α_AND provides a quantitative text-override vulnerability score. Models deployed in safety-critical applications (medical transcription, legal proceedings) should be required to demonstrate high α_AND at their listen layer.
- [TODO: Can α_AND be used as a training objective? Would penalizing OR-gates during fine-tuning improve genuine audio grounding?]


## 5.3 Safety Implications

The Listening Geometry framework has direct implications for ALM safety:

- **Jailbreak attacks as gc suppression.** SPIRIT (Djanibekov et al., 2025) defends against adversarial audio jailbreaks by substituting clean activations at noise-sensitive MLP neurons. Our framework explains *why* those specific neurons matter: they likely correspond to AND-gate features at or near k* whose suppression forces the model from "strong listener" to "sophisticated guesser" — shifting the gc profile rather than injecting new information.

- **Persona-conditioned grounding shifts.** Our mock experiments (Q039) show that anti-grounding system prompts shift k* earlier and boost peak gc. In a real model, this would mean that prompt injection could deliberately degrade audio grounding — a novel attack vector where the adversary manipulates *how* the model processes audio, not *what* audio it receives.
  - [TODO: Test this on real models — is gc shift via persona prompt practically achievable?]
  - [TODO: Can gc monitoring serve as a runtime detection mechanism for prompt injection?]

- **Backdoor detection via gc.** Mock experiment Q116 shows that backdoor triggers shift t* (collapse onset) leftward, causing earlier audio abandonment. This suggests gc/t* monitoring as a backdoor detection signal.
  - [TODO: Connect to Gap #24 (SAE-guided safety patching) — can we patch AND-gate features to neutralize backdoors?]

- **Deployment screening.** The 4-profile taxonomy (strong/shallow/fragile listener, sophisticated guesser) could serve as a deployment readiness criterion: models classified as "sophisticated guessers" or "fragile listeners" should receive additional scrutiny before deployment in audio-critical applications.


## 5.4 Cross-Paper Predictions

The gc(k) framework generates testable predictions that bridge our work with concurrent studies:

- **MPAR² prediction** [CITE: Chen 2603.02266]: RL training that improves audio perception accuracy (31.7% → 63.5%) should produce one of two gc signatures: (a) raised gc at late layers (audio information persists deeper into the LLM backbone), or (b) shifted k* to a shallower layer (audio is consulted earlier and more decisively). If neither signature is observed, MPAR²'s improvement operates through a mechanism outside the gc framework.
  - [TODO: If falsified, what does it mean? Possibly that RL affects text-side processing rather than audio grounding.]

- **Modality Collapse prediction** [CITE: Zhao 2602.23136]: Items where the model "follows text" despite audio-text conflict should exhibit the Tier 3 gc profile — mid-peak followed by late-layer drop. Items where the model correctly follows audio should maintain high gc through late layers.
  - [TODO: Test on ALME conflict items with known follows_text/follows_audio labels]

- **AudioSAEBench bridge**: gc at the feature level (Paper B) is the micro-scale complement of gc at the layer level (this paper). Feature-level gc should decompose the layer-level signal, with AND-gate features contributing disproportionately to layer gc.
  - [TODO: Formal relationship: is layer gc(k) = weighted mean of feature gc(f, k)?]


## 5.5 Limitations

We acknowledge several limitations of the current work:

- **Mock validation only.** 20 of our 22 experiments use the mock framework, which validates internal consistency of the gc formalism but does not test whether real neural networks exhibit the predicted patterns. The two real experiments (Q001, Q002) on Whisper-base provide preliminary evidence but use the smallest model scale.
  - [TODO: Priority 1 — real gc(k) sweep on Whisper-small to validate core claims]

- **Model scope.** Our real experiments are limited to Whisper-base (74M parameters, encoder-only). The full Listening Geometry framework requires testing on speech LLMs (Qwen2-Audio) where both encoder and decoder layers are present, and where text priors from the LLM backbone create the listen-vs-guess tension.
  - [TODO: GPU access blocker — Qwen2-Audio experiments deferred pending NDIF cluster allocation]

- **Deferred dimensions.** Two of the five Listening Geometry dimensions — codec stratification (CS) and collapse onset (t*) — are deferred to Paper B scope. This means the current paper validates only a 3-dimensional subspace (k*, α_AND, σ) of the full framework.
  - [TODO: Confirm Paper A vs B scope boundary is clean — no circular dependencies]

- **AND/OR threshold sensitivity.** The AND/OR gate classification depends on the threshold δ, which we calibrate via bootstrap but have not tested for robustness across different δ values in real models.
  - [TODO: Sensitivity analysis of δ on real SAE features]

- **Blocked experiments.** Q117 (GSAE density) and Q123 (FAD-RAVEL direction) represent genuine framework failures that may indicate deeper limitations of the gc approach for graph-structured or frequency-domain features.


## 5.6 Future Work

Several directions extend the Listening Geometry framework:

- **Paper B (AudioSAEBench).** Dimensions D4 (collapse onset) and D5 (codec stratification) will be fully validated on Whisper and Qwen2-Audio, with feature-level gc providing the bridge between layer-level and feature-level analysis.

- **Audio T-SAE.** Adapting temporal SAEs (Bhalla et al., 2025) from text to audio would enable temporal coherence as a gc proxy: features coherent at phoneme timescale (~5–10 frames) indicate listening; features coherent at text-token timescale indicate guessing.

- **Cross-lingual gc.** Do phonological vectors survive the connector across languages? Testing gc(k) on multilingual speech (building on Choi et al.'s 96-language results) would reveal whether the listen layer is language-universal or language-specific.

- **gc as a training objective.** If α_AND can be differentiated, penalizing OR-gates during fine-tuning could produce models that genuinely integrate audio rather than defaulting to text priors.

- **Real-time gc monitoring.** Deploying gc(k) as a runtime monitoring signal could detect when a model shifts from listening to guessing during inference — enabling dynamic safety interventions.
