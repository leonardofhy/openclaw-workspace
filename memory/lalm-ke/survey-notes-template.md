# Paper Survey Notes Template — LALM-KE
> Copy this file to: `memory/lalm-ke/survey-notes/YYYY-MM-DD-[short-slug].md`
> Fill all sections. "N/A" is OK for non-applicable fields. Don't skip "LALM-KE relevance."

---

## Citation

```
Title: 
Authors: 
Year: 
Venue: 
arXiv: https://arxiv.org/abs/XXXX.XXXXX
Code: https://github.com/...  (or: not released)
Read date: YYYY-MM-DD
Read by: Leo / bot
```

---

## 1. Problem

> What problem does this paper solve? Be specific.
> (2-4 sentences)



**Problem type** (check all that apply):
- [ ] Knowledge Editing method
- [ ] Knowledge Editing benchmark/eval
- [ ] LALM architecture
- [ ] LALM benchmark
- [ ] Mechanistic Interpretability
- [ ] Audio encoder / speech model
- [ ] Multimodal KE
- [ ] Other: ___

---

## 2. Background & Motivation

> What is the gap in prior work they're addressing?
> What assumptions do they make?



---

## 3. Method

> How do they solve it? Be concrete.
> (3-6 sentences; include key equations/figures if helpful)

**Method category:**
- [ ] Locate-then-Edit (e.g., ROME-style)
- [ ] Meta-learning / hypernetwork (e.g., MEND-style)
- [ ] Memory-augmented / retrieval (e.g., SERAC/GRACE-style)
- [ ] Fine-tuning with constraints
- [ ] In-context / prompting
- [ ] Probing / interpretability
- [ ] Architecture / training method
- [ ] Other: ___

**Key components:**
1. 
2. 
3. 

---

## 4. Key Results

> What did they show? Quantitative numbers where possible.

| Metric | This paper | Baseline | Notes |
|--------|-----------|----------|-------|
| Reliability (edit success rate) | | | |
| Generality (paraphrase success) | | | |
| Locality (unrelated facts preserved) | | | |
| [Other key metric] | | | |

**Main takeaway in 1 sentence:**


---

## 5. Limitations & Critiques

> What does this paper NOT do well? What are the known failure modes?



---

## 6. LALM-KE Relevance

> This is the most important section. Think carefully.

**Relevance score:** ☐ 0 (tangential) ☐ 1 (background) ☐ 2 (directly relevant) ☐ 3 (core paper)

**Why relevant to LALM-KE:**


**What can we directly borrow/adapt:**
- Method: 
- Benchmark/eval: 
- Insights about knowledge localization: 

**What DOESN'T transfer (and why):**


**Gap this paper reveals for LALM-KE:**


---

## 7. Connections to Other Papers

> How does this relate to other papers you've read?

| Related Paper | Relationship | Notes |
|--------------|--------------|-------|
| | extends / improves / contradicts / uses benchmark from | |
| | | |
| | | |

**Position in the literature:**


---

## 8. Open Questions

> Questions this paper raises, or things you don't understand yet.

1. 
2. 
3. 

**Questions to bring to Monday meeting:**
- 

---

## 9. Experiment Ideas

> Any concrete experiment ideas this paper inspires for LALM-KE?

- [ ] **Idea:** [description] | Feasibility: High/Med/Low | Effort: ~[N] days

---

## 10. Key Quotes / Passages

> Copy important sentences verbatim (with page/section numbers).

> "[quote]" — Section X, p.Y

---

## Tags

`#ke-method` `#ke-benchmark` `#lalm-arch` `#lalm-benchmark` `#interp` `#audio-encoder` `#multimodal-ke` `#survey`

(delete tags that don't apply, add others as needed)
