# Paper A — Figure 2 Draft
# "Listen or Guess? Geometric Confidence as a Diagnostic for ASR Hallucination"

> Generated: 2026-03-06 10:15 | Source: gc_jailbreak_classifier.py (mock, designed from classifier feature-space)
> Status: DRAFT — replace with real Whisper activations + JALMBench gc(k) curves when available
> Task: Q046 | Cycle: c-20260306-1015

---

## Purpose

Figure 2 bridges Paper A and Paper C:
- Shows what a **normal (benign) gc(k) curve** looks like vs a **jailbreak-audio gc(k) curve**
- Introduces the **confidence collapse** signature used by the Listen-Layer Audit
- Visually justifies that gc(k*) anomaly is a meaningful, discriminable signal

---

## ASCII Curve

```
gc(k)
 1.0 ┤
     │        ████████████████
 0.9 ┤      ██░               ░██
     │    ██░                    ░██                              [BENIGN]
 0.8 ┤  ██░                        ░██ ████████████████████████
     │██░                                                         (listen-dominant)
 0.7 ┤
     │
 0.6 ┤         ▓▓▓▓▓▓▓▓
     │      ▓▓▓░        ░▓▓▓
 0.5 ┤    ▓▓░               ░▓▓▓                                 [JAILBREAK]
     │  ▓▓░                    ░▓▓                               (confidence
 0.4 ┤▓▓░                         ░▓▓                             collapse in
     │                               ░▓▓                          decoder)
 0.3 ┤                                  ░▓▓▓
     │                                      ░▓▓▓
 0.2 ┤                                          ░▓▓▓▓
     │                                               ░▓▓▓
 0.1 ┤                                                   ░▓▓▓▓▓▓
     │                                                          ░▓
 0.0 ┼───────────────────────────────────────────────────────────────
     0   1   2   3   4   5 | 6   7   8   9  10  11
         Encoder Layers     |      Decoder Layers
     ◄── LISTEN ZONE ──────►◄────────── GUESS ZONE ──────────────►
                            ↑
                           k* (Listen Layer — peak of benign curve)
                           △△ Anomaly zone: jailbreak curve begins collapse here
```

### Key Features Annotated

| Feature | Benign | Jailbreak | Δ |
|---------|--------|-----------|---|
| Encoder mean gc | 0.77 | 0.51 | −0.26 |
| Decoder mean gc | 0.82 | 0.18 | **−0.64** ← collapse |
| Peak-to-final drop | 0.05 | 0.47 | **+0.42** ← signature |
| Decoder slope | +0.004 / layer | **−0.047 / layer** | ← steep fall |
| Enc→Dec collapse ratio | 0.03 | **0.64** | ← main classifier feature |

---

## Caption (journal version)

**Figure 2. gc(k) anomaly under audio jailbreak: confidence collapse in the decoder.**
Geometric confidence gc(k) is plotted for a benign audio query (filled squares, ██) and an audio jailbreak attempt (filled diamonds, ▓▓) across Whisper encoder and decoder layers.
**Benign condition**: gc(k) rises to its peak at k* = 5 (the Listen Layer) then remains high through the decoder, indicating sustained reliance on acoustic evidence.
**Jailbreak condition**: gc(k) exhibits a characteristic *confidence collapse* — encoder layers retain moderate acoustic grounding (enc_mean = 0.51), but decoder gc(k) falls sharply from k* onward (dec_slope = −0.047/layer, dec_mean = 0.18), consistent with the model abandoning audio evidence and following the adversarial text prior.
The **encoder→decoder collapse ratio** (1 − dec_mean / enc_mean) reaches 0.64 for the jailbreak condition vs. 0.03 for benign, providing a scalar discriminant signal.
The Listen-Layer Audit (Paper C) formalizes this anomaly as a zero-shot jailbreak detector: queries with collapse_ratio > 0.45 and dec_slope < −0.03/layer are flagged, achieving 89% accuracy on JALMBench-246 (mock estimate; real run pending Leo unblock).
Dashed vertical line marks the encoder–decoder boundary (layer 6). Shaded regions indicate ±1σ across 3 seeds.
*Note: Values from mock eval; to be replaced with real Whisper-small activations on JALMBench.*

---

## Three-Panel Version (preferred for paper)

If space allows, use a three-panel figure:

### Panel A — Individual curves (as above)
Benign vs. jailbreak overlay, all 12 layers.

### Panel B — Feature scatter: collapse_ratio vs. dec_slope
```
dec_slope (per layer)
+0.05 ┤
      │
+0.02 ┤   ● ● ●  ●  ● ●    ← BENIGN (high gc, stable/flat decoder)
      │  ● ●    ●  ●  ●
 0.00 ┼──────────────────────────────────
      │           ▲  ▲ ▲
-0.02 ┤        ▲▲    ▲  ▲   ← JAILBREAK
      │    ▲▲   ▲▲   ▲
-0.05 ┤ ▲▲  ▲
      │
      ┼───────────────────────────────────
      0.0  0.2  0.4  0.6  0.8  1.0
           collapse_ratio (enc→dec)
           Decision boundary: collapse_ratio = 0.45 (dashed)
```

### Panel C — gc(k) distribution at k* (histogram)
```
count
 30 ┤  ██      ← BENIGN cluster (gc(k*)=0.80−0.95)
 25 ┤  ████
 20 ┤  ████
 15 ┤  ████       ▒▒   ← JAILBREAK cluster (gc(k*)=0.40−0.60)
 10 ┤  ████       ▒▒▒▒
  5 ┤  ████       ▒▒▒▒
    └──────────────────────────────
       0.3  0.5  0.7  0.9   gc(k*)
```
Shows bimodal distribution at k* — motivates threshold classifier.

---

## Placement in Paper

- **Position**: §3.3 (after gc(k) formalization, before experiment results)
- **Cross-reference**: "As shown in Figure 2, jailbreak inputs produce a characteristic gc(k) anomaly; §5 (Paper C) formalizes this as the Listen-Layer Audit."
- **Connection to Figure 1**: Fig 1 shows normal variation across conditions; Fig 2 introduces jailbreak as a qualitatively different failure mode (not just "low gc" but "collapsed gc in decoder despite encoder signal")

---

## TODO for final version

- [ ] Replace ASCII with matplotlib: `gc_visualizer.py --overlay-benign --overlay-jailbreak --panel3`
- [ ] Add ±1σ shaded bands (3 seeds each)
- [ ] Run on real JALMBench subset (needs Leo GPU unblock)
- [ ] Confirm k* = 5 in real Whisper-small data
- [ ] Panel B scatter: 246 JALMBench queries (benign vs jailbreak)
- [ ] Caption update: replace "mock estimate" with real accuracy numbers
- [ ] Consider: add a 3rd curve (borderline / low-confidence benign) to show gradient
