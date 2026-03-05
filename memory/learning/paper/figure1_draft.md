# Paper A — Figure 1 Draft
# "Listen or Guess? Geometric Confidence as a Diagnostic for ASR Hallucination"

> Generated: 2026-03-05 19:15 | Source: gc_experiment_runner.py (mock, n=3 seeds)
> Status: DRAFT — replace with real Whisper activations when available

---

## ASCII Curve

```
gc(k)
 1.0 ┤
     │                   ██████████████████████████████████
 0.9 ┤              ████░                                  ░████
     │         ████░                                            ░
 0.8 ┤        █░                                                ░    [Clean vs Noise]
     │      ██░
 0.7 ┤     █░
     │    █                 ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
 0.6 ┤   █             ▒▒▒▒░                        ░▒▒▒
     │  █          ▒▒▒▒                                  ▒▒▒▒▒   [Clean vs Silence]
 0.5 ┤ █         ▒▒░                                         ▒▒
     │█       ▒▒▒                                              ▒
 0.4 ┤      ▒▒░
     │   ▒▒▒          ░░░░░░░░░░░░░░░░
 0.3 ┤  ▒░         ░░░                ░░░░░░░
     │           ░░                         ░░░░░░             [Clean vs Masked 50%]
 0.2 ┤         ░░
     │        ░
 0.1 ┤       ░░
     │
 0.0 ┼───────────────────────────────────────────────────────────
     0   1   2   3   4   5 | 6   7   8   9  10  11
         Encoder Layers     |      Decoder Layers
                 ◄── LISTEN ZONE ──►◄── GUESS ZONE ──►
```

## Data Table

| Condition | Peak Layer | Peak gc(k) | Mean Enc | Mean Dec | Regime |
|-----------|-----------|-----------|----------|----------|--------|
| Clean vs Gaussian Noise | 5 | 0.876 | 0.529 | 0.781 | Listen-dominant |
| Clean vs Full Silence | 5 | 0.633 | 0.355 | 0.229 | Listen→Guess transition |
| Clean vs 50% Masked | 5 | 0.569 | 0.344 | 0.508 | Mixed / partial listen |

## Caption (journal version)

**Figure 1. gc(k) as a listen/guess diagnostic across Whisper encoder–decoder layers.**
Geometric confidence gc(k) is plotted for three input conditions (k = softmax temperature sweep at each layer).
**Listen mode** (high, stable gc(k)): the model has access to clear audio evidence and sustains internal agreement through the decoder (condition: clean vs. Gaussian noise, gc(k) ≥ 0.70 at all decoder layers).
**Guess mode** (gc(k) collapse in decoder): the model peaks at the encoder–decoder junction then loses internal consistency as it substitutes prior-driven guesses for acoustic evidence (condition: clean vs. silence, mean decoder gc(k) = 0.23 vs. 0.78 in listen condition).
A 50% masked condition yields an intermediate trajectory, suggesting gc(k) tracks *degree* of audio availability, not merely its presence.
Shaded regions indicate ±1 σ across 3 random seeds.
Vertical dashed line marks the encoder–decoder boundary (layer 6).
*Note: All values from mock eval harness; to be replaced with real Whisper-small activations.*

## TODO for final version
- [ ] Run `gc_experiment_runner.py --plot` → get matplotlib PNG
- [ ] Add ±1σ shaded bands
- [ ] Replace mock activations with real Whisper-small activations (needs Leo unblock)
- [ ] Consider inset: gc(k) distribution histogram at layer 5 (listen vs guess — bimodal?)
- [ ] Add 4th condition: adversarial audio (for T5 safety probe connection)
