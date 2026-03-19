# §5 Discussion

## 5.1 gc(k) as a Unifying Metric

The grounding coefficient subsumes and extends two prior observational metrics, providing the first causal account of layer-wise audio dependency in audio-language models:

**AudioLens critical layer** (Ho et al., 2025): AudioLens identifies layers where auditory attribute information peaks via logit lens probing—a Pearl Level 1 analysis that measures statistical association between representations and behavioral outputs. gc(k) provides the causal counterpart at Pearl Level 3: the critical layer identified by AudioLens should coincide with or be near k*, but gc(k) additionally proves that this layer *causes* the model's output rather than merely correlating with it. We term this upgrade "Causal AudioLens"—gc(k) operates at the same representational level as AudioLens but answers the stronger question of causal necessity rather than informational presence.

**Beyond Transcription saturation layer** (Glazer et al., 2025): The saturation layer marks where the encoder "commits" to its transcription in encoder-only architectures. gc(k) extends this concept beyond encoder-only models to the full encoder → connector → LLM pipeline, replacing white-noise reference patching with phonologically minimal-pair corruption that preserves linguistic structure. Where Glazer et al. identify a single saturation point, gc(k) reveals the full causal profile across the audio-language processing pipeline.

The **Triple Convergence hypothesis** provides a scaling prediction: if the "semantic crystallization" phenomenon observed in text transformers extends to audio-language models, then k* should occur at approximately 50% network depth regardless of model scale. Our mock experiments place k* at layer 3 in a 6-layer model (~50% depth), consistent with this prediction. If k* ≈ layer 6 in Whisper-small (12 layers) and k* ≈ layer 12 in Whisper-medium (24 layers), this would constitute evidence for depth-proportional crystallization of audio grounding—a fundamental architectural constraint on how ALMs process multimodal information.

The connection between gc(k) and Pearl's causal hierarchy is precise: while logit lens analysis operates at Level 1 (pure observation of layer-outcome associations), gc(k) implements Level 3 causal analysis by asking "what would happen if we intervened to change the audio representation at layer k?" This distinction is critical for deployment: a layer might contain audio-related information (detectable by AudioLens) while contributing negligibly to audio-dependent outputs (detectable only by gc).

## 5.2 AND-Gate Insight: Genuine Multimodal Processing

The AND/OR gate framework reveals a qualitative distinction between two modes of multimodal processing that standard benchmarks cannot detect:

**AND-gate dominance** (high α_AND): The model performs genuine audio-text integration where neither modality alone suffices to reconstruct the relevant features. This is the hallmark of a "strong listener"—the model cannot produce correct outputs without consulting the audio signal, implementing true multimodal fusion rather than independent processing streams.

**OR-gate dominance** (high cascade degree κ): The model can recover relevant features from either modality alone, enabling text priors to fully substitute for audio input. This is the mechanism behind "sophisticated guessing"—the model may appear to listen (achieving high task accuracy) while relying entirely on text context when audio conflicts with expectations.

The cascade degree κ = 1 − α_AND provides a **quantitative text-override vulnerability score** with direct safety implications. Models deployed in safety-critical applications—medical transcription, legal proceedings, emergency response systems—should be required to demonstrate high α_AND at their listen layer. OR-gate dominance represents a failure mode where adversarial text context can fully override audio evidence, potentially causing the model to "hear" what the text context suggests rather than what the audio contains.

**Deployment screening criterion**: We propose that the 4-profile taxonomy (strong listener, shallow listener, sophisticated guesser, fragile listener) serve as a deployment readiness framework. Models classified as "sophisticated guessers" or "fragile listeners" should receive additional scrutiny before deployment in audio-critical applications, regardless of their performance on standard accuracy benchmarks.

**Training objective implications**: An open question is whether α_AND can be differentiated and used as a training objective. Penalizing OR-gates during fine-tuning could potentially produce models that genuinely integrate audio rather than defaulting to text priors—though this requires careful balance to avoid degrading performance on tasks where text context should appropriately dominate.

## 5.3 Limitations and Scope

We acknowledge several fundamental limitations that constrain the interpretation and generalizability of our findings:

**Mock experiment validation**: 25 of our 27 experiments use mock numpy circuits that validate internal consistency of the gc formalism but do not test whether real neural networks exhibit the predicted patterns. While these experiments confirm mathematical coherence and establish baseline expectations (e.g., r = 0.984 correlation between AND-gate fraction and gc), they represent framework validation rather than empirical discovery about neural computation. The transition from mock to real experiments constitutes the critical empirical test of our theoretical predictions.

**Limited model scope**: Our real experiments are constrained to Whisper-base (74M parameters, encoder-only architecture) due to computational limitations. This scope restriction has two implications: (1) we cannot yet validate the framework on complete audio-language models where encoder-decoder interactions create the theoretical "listen vs. guess" tension, and (2) the smallest model scale may not exhibit the representational structure assumed by our framework. The full Listening Geometry framework requires testing on speech LLMs like Qwen2-Audio where both encoder and LLM backbone layers are present, and where text priors from the language model create genuine audio-text competition.

**Linearity assumptions**: The gc(k) metric captures linear causal influence through DAS-based interchange interventions, which identify linear subspaces that faithfully represent high-level causal variables. This approach may systematically miss nonlinear causal contributions where audio information influences model behavior through complex, superposition-based interactions that cannot be decomposed into orthogonal subspaces. While linear decomposition has proven effective for phonological features (Choi et al., 2026), higher-order multimodal interactions may require extensions beyond our current framework.

**Generalization uncertainty**: Our findings are based on English Whisper models trained on a specific distribution of speech data. The patterns we observe may not extend to multilingual models, instruction-tuned audio-language systems, or models trained with different architectural choices. The phonological minimal-pair approach assumes that speech models organize acoustic information along linguistically meaningful dimensions, but this may not hold for models optimized for different tasks or trained on different data distributions.

## 5.4 Future Work

Several concrete directions extend the Listening Geometry framework toward broader empirical validation and practical application:

**Scale validation across Whisper architectures**: The most immediate priority is scaling Q001 and Q002 experiments from Whisper-base to Whisper-small and Whisper-medium. These experiments will test whether the Triple Convergence prediction holds (k* at ~50% depth) and whether gc magnitude scales with model capacity. This validation requires minimal new methodology but substantial computational resources—estimated 100+ GPU-hours for full layer-wise gc(k) sweeps across phonological minimal pairs.

**Full audio-language model analysis**: Testing gc(k) on Qwen2-Audio or similar complete ALMs will reveal whether our theoretical three-phase profile (rising gc through encoder, potential connector drop, declining gc through LLM) manifests in practice. This extension is crucial because encoder-only experiments cannot capture the text-prior override mechanisms that operate at the language model level, where our framework predicts the strongest "listening vs. guessing" dynamics.

**Pre-registered prediction validation**: Our ALME conflict item predictions (P1-P3) await empirical testing to determine whether behavioral "follows text" items exhibit the predicted late-layer gc drop, and whether rare phoneme contrasts are more vulnerable to text-prior override. These pre-registered tests provide the strongest potential falsification of the framework, as they specify exact effect sizes (Cohen's d ≥ 0.3) and directions that could definitively reject our theoretical predictions.

**Mechanistic intervention development**: If α_AND proves differentiable, exploring its use as a training objective could enable engineering models that perform genuine multimodal integration rather than defaulting to unimodal processing. This direction bridges interpretability research with practical model improvement, potentially producing ALMs that are more robust to audio-text conflicts and less vulnerable to sophisticated guessing failure modes.