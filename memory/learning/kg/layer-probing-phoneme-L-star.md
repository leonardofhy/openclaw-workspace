# Layer-wise Probing ↔ AND-frac ↔ Listen Layer L*

**Created:** 2026-03-25 (Cycle c-20260325-2015, Q174 learn)
**Tracks:** T3
**Status:** Design synthesis — ready to implement in Q174

---

## Core Claim

**Linear probe accuracy should peak at L* (AND-frac transition layer)**, confirming L* is
the information bottleneck where audio-phoneme correspondence is maximized before text-driven
OR-gate prediction takes over.

---

## Evidence (theoretical, to be validated by Q174)

| Layer Region | AND-frac | Phone Probe Acc | Interpretation |
|---|---|---|---|
| 0 → L* | Rising | Rising | Phoneme crystallization zone |
| L* | Peak | Peak | Listen layer — audio evidence max |
| L* → L_max | Falling | Falling | Text prior takes over (OR-gate) |

**Dual confirmation**: AND-frac (causal/geometric) + probe accuracy (information-theoretic)
both point to the SAME layer as L*. This is a convergent validity argument for the theory.

---

## Implementation Key Points

- Probe type: sklearn LogisticRegression (linear), C=1.0
- Features: mean(hidden_states[l][center-2:center+2], axis=0)  # per phone
- Labels: broad IPA class (20 categories)
- Data: L2-ARCTIC, speaker-stratified split (8 train / 2 test)
- Whisper-base: 6 encoder layers (expect L* at layer 3-4)

---

## New Fairness Finding (hypothesis)

Accented speakers → AND-frac drops earlier → probe accuracy peak is EARLIER and LOWER.
This would show that the accent WER gap originates at the phone-crystallization stage —
a mechanistic, layer-resolved explanation of accent bias.

---

## Paper A §3 subplot

Figure: dual-axis (AND-frac per layer ∥ probe acc per layer).
Key point: L* is where BOTH curves peak. Natural language: "The listen layer is the point
at which the encoder has maximally crystallized audio evidence into phonemic representations,
before the decoder begins substituting text-prior predictions."

---

## Connections

- → Q174 build (implement and validate)
- → Q175 (gc(k) as epistemic uncertainty — probe entropy at L* as uncertainty signal)
- → Paper A §3 (layer information profile section)
- → AND/OR gate KG entry (L* = peak AND-frac = peak phone probe = same layer)
