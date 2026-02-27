# AudioMatters Results v0 Writing Pack (2026-02-28)

## Deliverables (tomorrow)
1. Main Results narrative (table-level insight)
2. One key ablation paragraph (component contribution)

## Main Results paragraph template
- Opening claim: "Table X shows [ours] outperforms [best baseline] by [absolute] ([relative]%) on [metric]."
- Insight sentence: "This suggests [mechanistic/behavioral interpretation], not only raw gain."
- Robustness sentence: "The improvement is consistent across [subsets/settings], with mean±std [value]."
- Boundary sentence: "However, gains shrink on [hard case], indicating [limitation]."

## Ablation paragraph template
- Setup: remove/disable one component at a time.
- Core sentence: "Removing [component A] causes the largest drop ([x] on [metric]), indicating it is the primary contributor."
- Secondary sentence: "Removing [component B] yields minor change ([y]), suggesting redundancy or weak contribution."
- Conclusion: "These results validate the design choice that [A] is essential while [B] can be simplified."

## Evidence hygiene checklist
- [ ] Each table has 2–4 interpretation sentences (not only 'As shown in Table').
- [ ] Best numbers bolded.
- [ ] Mean±std reported where variance matters.
- [ ] At least one negative finding explicitly discussed.
- [ ] No puffery words without evidence (novel/clearly/obviously/significant).

## 40-minute kickoff plan (first slot)
- [ ] Fill Table X with final numbers: ours / best baseline / abs diff / relative diff.
- [ ] Mark one hardest subset where gains shrink (for limitation sentence).
- [ ] Draft 4-sentence Main Results paragraph directly under Table X.
- [ ] Select one ablation with largest drop and draft 3-sentence ablation paragraph.
