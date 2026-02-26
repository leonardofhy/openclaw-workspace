# 🎯 Research Goals

> Last updated: 2026-02-26 by Leo (direct feedback)

## Primary Direction
**Mechanistic Interpretability for Speech/Multimodal Language Models**
- How do multimodal LMs (Qwen-Audio, Gemini, GPT-4o) internally process speech?
- What circuits/features handle phonetics vs semantics vs emotion vs speaker identity?
- Can we build interp tools for the speech modality (analogous to TransformerLens for text, Prisma for vision)?

## Secondary Interest
**AI Safety × Speech**
- Audio adversarial attacks: why do they work mechanistically?
- Speech-based jailbreaks: are there "safety neurons" in the speech pathway?
- Alignment of speech modality with text safety training

## Active Projects
1. **AudioMatters** — Interspeech 2026 (1st author, CMT deadline TODAY 19:00)
   - Status: experiments done, writing phase
   - After submission: pivot attention to mech interp direction

## Paper Ideas (ranked)
1. 🥇 Mech interp of speech understanding in Omni-LLMs → NeurIPS/ICLR
2. 🥈 SpeechLens toolkit for speech model interpretability → EMNLP Demo
3. 🥉 Audio adversarial × mech interp = safety → Workshop paper

## Knowledge Gaps (to fill via learning cycles)
- [ ] TransformerLens / activation patching methodology
- [ ] SAE (Sparse Autoencoder) training and analysis
- [ ] How Whisper/HuBERT encoder internals work layer-by-layer
- [ ] Qwen-Audio / SALMONN architecture details
- [ ] Multimodal token alignment mechanisms

## Leo's Preferences
- Interested in mech interp, especially speech-related multimodal LM
- Interested in AI Safety research
- Not limited to AudioMatters — broader research vision
- Values depth over breadth
