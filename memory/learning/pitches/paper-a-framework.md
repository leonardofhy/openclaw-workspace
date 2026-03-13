# Paper A — The Listening Geometry: §3 Framework Scaffold
**Track:** T3 | **Version:** v0.1 | **Date:** 2026-03-13 | **Created:** Q097

---

## The Listening Geometry — 5-Dimension Framework

An ALM's relationship to its audio input is characterized along five orthogonal dimensions:

---

### D1: gc Peak (k*) — "Where does listening peak?"

**Definition:**
```
k* = argmax_k gc(k)
     gc(k) = causal_patching_IIA_at_layer_k  (linear DAS, acoustic→text intervention)
```

**Section:** §3.1 (Primary metric; all experiments anchor on k*)

**Connects to tasks:** Q075 (Phonological DAS × instruction tuning), Q085 (collapse onset step), Q086 (behavioral benchmark)

**Predicted pattern:** Sigmoid curve across layers; sharp transition at k*

---

### D2: AND-Gate Fraction α_AND(k*) — "What kind of listening?"

**Definition:**
```
α_AND(k) = |{f ∈ F_causal(k) : IIA_f(A+T) >> max(IIA_f(A), IIA_f(T))}| / |F_causal(k)|
```
where F_causal(k) = top-IIA features at layer k; A = audio only; T = text only; A+T = both

**Section:** §3.2 (Mechanistic decomposition: AND-gate = genuine multimodal dependence)

**Connects to tasks:** Q080 (AND-gate Schelling stability), Q091 (persona × gate), Q092 (Schelling × gate), Q093 (collapse × gate), Q096 (FAD bias × gate)

**Prediction:** α_AND inversely correlates with hallucination rate on biased stimuli

---

### D3: Schelling Stability σ — "How structurally necessary is this listening?"

**Definition:**
```
σ = |{f : f ∈ top-k% IIA features across ALL S model seeds}| / |top-k% IIA features|
    where k=10, S≥3 (training randomness, init, data order variants)
```

**Section:** §3.3 (Validity: separates core circuit from incidental features)

**Connects to tasks:** Q082 (phoneme Schelling across 5 MicroGPT seeds), Q092 (Schelling × gate type)

**Prediction:** AND-gate features have higher σ than OR-gate/passthrough features

---

### D4: Collapse Onset t* — "How long does listening last?"

**Definition:**
```
t* = min{t : Isolate_in(t) < τ}
     Isolate_in(t) = causal isolation of audio representations at decoder step t
     τ = 0.1 (threshold; tunable)
```

**Section:** §3.4 (Decoder dimension; extends Listen Layer from encoder to full forward pass)

**Connects to tasks:** Q085 (collapse onset step script), Q093 (collapse × gate), Q094 (T-SAE × gc incrimination)

**Prediction:** t* correlates with ALME error rate; models with early t* more vulnerable

---

### D5: Codec Stratification CS — "How stable is listening across audio conditions?"

**Definition:**
```
CS = max_{c1,c2 ∈ C} |k*(c1) - k*(c2)| / L
     where C = {lossless, MP3-128, OGG-128, G.711}, L = total encoder layers
```

**Section:** §3.5 (Robustness / generalization; deployment implications)

**Prediction:** Models with high CS are deployment-fragile; adversary can shift k* via codec choice

---

## Joint Profile — Strong Listener vs. Sophisticated Guesser

| Profile | k* | α_AND | σ | t* | CS | Description |
|---------|-----|-------|---|----|----|-------------|
| Strong listener | Deep | High | High | Late | Low | Audio genuinely drives output; robust |
| Shallow listener | Shallow | Mid | Mid | Mid | Low | Audio used but vulnerable to early override |
| Sophisticated guesser | Deep (fake) | Low | Low | Early | High | Does complex audio processing but ignores it |
| Fragile listener | Deep | High | High | Late | High | Listens well but only on training-distribution audio |

---

## Paper A → Paper B Split (proposed)

- **Paper A (current):** D1 + D2 + D3 on Whisper-small/medium (encoder geometry + mechanistic validity)
- **Paper B (future):** D4 + D5 on Whisper + Qwen2-Audio; robustness applications; safety monitoring (T5/Paper C uses all 5D for anomaly detection)

---

## T5 Safety Connection

An audio jailbreak modifies input to suppress gc(k*) → shifts model from strong-listener profile toward sophisticated-guesser profile at safety-critical decision layer. Detection signature:
- Suppressed gc(k*) relative to baseline
- Increased OR-gate fraction (audio evidence appears less causal)  
- Early collapse onset t* (decoder stops consulting audio earlier)
- M7 + M9 dual-factor detector = operationalized safety check of 5D Listening Geometry (Q083, Q090, Q095)
