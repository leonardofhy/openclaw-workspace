# 學生論文寫作教學指南

## 由小金整理，供宏毅老師指導學生用

### 建立日期：2026-02-15

---

## 🎯 教學目標

讓學生能寫出 Interspeech/ACL 水準的論文，重點培養：

1. 結構化思考能力（先想清楚再寫）  
2. 為讀者寫作的意識  
3. 每個 section 的具體寫作技巧

---

## 第一課：論文的本質

### 核心觀念（來自四大寫作導師）

**論文是你的大使** — 你不在場時，它替你說話。（SPJ） **寫作 \= 思考** — 寫不清楚代表你沒想清楚。（SPJ \+ Ernst） **目標是改變讀者行為** — 讓他們相信你的方法值得嘗試。（Ernst）

### Ernst 的三件事框架（最簡潔的自我檢查）

讀者必須相信：

1. ✅ **問題很重要**（有影響力、有後果）  
2. ✅ **問題很難**（現有方法都不夠好）  
3. ✅ **你解決了這個問題**（有實驗證明）

💡 **教學建議**：讓學生在寫論文前先用三句話回答這三個問題。如果答不出來，還沒準備好寫。

---

## 第二課：Abstract 怎麼寫

### 公式：問題 → 不足 → 方法 → 結果（4-6 句）

| 句子 | 功能 | 信號詞 |
| :---- | :---- | :---- |
| 第 1-2 句 | 背景 \+ 現有方法 | "X methods aim to..." |
| 第 3 句 | Gap（不足） | "However," "Nevertheless," "Despite," |
| 第 4 句 | 你的方法 | "We propose X, which..." / "In this work, we..." |
| 第 5 句 | 結果 | "Experiments show..." \+ 具體數字 |
| 第 6 句（選填） | 額外亮點 | "Notably," "Furthermore," |

### 好範例分析：EFFUSE (Interspeech 2024 Best Paper)

\[背景\] SSL models have demonstrated exceptional performance in various speech tasks.

\[趨勢\] Recent works show that fusing diverse SSL models could achieve superior performance.

\[Gap\] However, fusing models increases the overall parameter size, leading to higher computational costs.

\[方法\] We propose EFFUSE, ...uses a single SSL model to mimic the features of multiple SSL models via prediction.

\[結果\] Our best model achieves an average SUPERB score increase of 63.5 (6.3%)...

      while decreasing parameter size by 317M (49%).

**為什麼好？** 三段論法（好→更好→但貴→我們的解法）；結果同時報 absolute \+ relative。

### 常見錯誤

- ❌ 太長（\>250 字）→ 應 150-200 字  
- ❌ 沒有具體數字  
- ❌ 放 references（abstract 要能獨立存在）  
- ❌ 說 "In this paper"（Schulzrinne：還能是什麼 paper？）  
- ❌ 只說 "significant improvement" 不給數字

💡 **練習**：找三篇 Interspeech best paper，標記每句話的功能（背景/gap/方法/結果）。

---

## 第三課：Introduction 怎麼寫

### 結構：倒三角 \+ Contributions

**第 1 段：大背景**（為什麼這個領域重要）

- 1-2 句即可，不要寫太多 general motivation

**第 2-3 段：建立 Gap**

- 描述現有方法（cite 相關工作）  
- 用轉折詞指出不足：However, Despite, Unfortunately  
- Gap 要具體到讓讀者覺得「對，這確實是問題」

**第 4 段：你的方法（overview）**

- "In this work, we propose X, which..."  
- 給 high-level intuition，不要進入技術細節

**第 5 段（或第 4 段末）：Contributions**

- 用 bullet points 明確列出  
- 每個 contribution 要具體、可驗證  
- ❌ "We propose a novel method" → ✅ "We propose X that achieves Y by doing Z"

### 關鍵技巧

- **Gap 決定論文價值**：Gap 不 convincing \= 論文不 convincing  
- **不要在 Introduction 寫太多 related work**（SPJ \#5）  
- **Introduction 結尾 \= 讀者的 mental map**：告訴他們接下來會看到什麼

💡 **練習**：讓學生只寫 Introduction 的最後一段（contributions），然後互相評。

---

## 第四課：Method 怎麼寫

### 三層結構

1. **Problem Formulation**：用數學或清晰語言定義問題  
2. **Key Insight**：為什麼你的方法能解決這個問題？（**最容易被跳過！**）  
3. **Technical Details**：具體實現

### DiffATR 示範

- Layer 1: 定義 discriminative (p(y|x)) vs generative (p(x,y))  
- Layer 2: "如果我們把 retrieval 重新建模為 joint distribution，就自然考慮了 data distribution"  
- Layer 3: Diffusion process、loss function、training procedure

### 常見錯誤

- ❌ 只寫 **how**，不寫 **why**（學生最常犯！）  
- ❌ 跳過 intuition 直接進 formalism  
- ❌ 沒有 pipeline 圖示  
- ❌ 數學符號不一致

💡 **教學建議**：讓學生寫完 Method 後，問他們：「如果去掉所有數學，用三句話解釋你的方法，你會怎麼說？」這三句話就是 Key Insight。

---

## 第五課：Experiments 怎麼寫

### 必備元素

1. **Setup**：數據集、baseline、評估指標、實現細節  
2. **Main Results**：與 baseline 的比較（table \+ 文字解讀）  
3. **Ablation Study**：每個 component 的貢獻  
4. **Analysis**：error analysis、case study、visualization

### 寫作技巧

- 每個 table/figure 都要有文字解讀  
  - ❌ "As shown in Table 1"  
  - ✅ "Table 1 shows that X outperforms Y by 3.2% on WER, suggesting that \[insight\]"  
- Bold 最好的結果  
- 報告 mean ± std（尤其是差距小的時候）  
- 主動討論負面結果（你的方法在哪裡不行？為什麼？）

### Ablation 的邏輯

- 逐一去掉 component，看 performance drop  
- 讓讀者知道 biggest drop 在哪裡 \= 最重要的 component  
- 如果某個 component 去掉後沒差，要解釋（或考慮移除）

💡 **練習**：給學生一張 results table，讓他們寫一段解讀。然後比較誰的解讀最有 insight。

---

## 第六課：Related Work 怎麼寫

### 核心原則

- **不是 list，是對比**  
- 要解釋你的方法與每類 related work 的差異  
- 要 generous（承認他人貢獻）但 clear（說明差異）

### 結構建議

- 按主題分組（不是按時間）  
- 每組 2-3 段，最後一句點出與你的方法的差異  
- ❌ "X et al. proposed..." 流水帳  
- ✅ "While X approaches this problem from \[angle\], our work differs in \[aspect\]"

---

## 第七課：寫作風格

### 來自四大導師的共同建議

1. **每段第一句 \= topic sentence**（reviewer 常只讀第一句）  
2. **用 active voice**："We train the model" 而非 "The model is trained"  
3. **避免 puffery words**：novel, clearly, obviously, significant（無數據支持的）  
4. **全篇術語一致**：一個概念只用一個詞  
5. **先說結論，再給證據**（give away the punchline）  
6. **Ruthlessly cut**：不支持主論點的就刪

### 過渡詞速查表

| 功能 | 詞彙 |
| :---- | :---- |
| 轉折 | However, Nevertheless, Despite, Yet, Unfortunately |
| 因此 | Therefore, Consequently, As a result, Thus |
| 此外 | Furthermore, Moreover, Additionally, In addition |
| 具體來說 | Specifically, In particular, Concretely |
| 對比 | In contrast, Unlike, While, Whereas |

---

## 第八課：提交前 Checklist（精簡版）

### 必查項目

- [ ] Abstract 有具體數字嗎？  
- [ ] Introduction 有明確的 contributions（bullet points）嗎？  
- [ ] Method 有解釋 **why** 而不只是 **how** 嗎？  
- [ ] 每個 table/figure 都有文字解讀嗎？  
- [ ] 有 ablation study 嗎？  
- [ ] Related work 是對比而非 list 嗎？  
- [ ] 全文沒有 "novel"、"clearly"、"obviously" 等 puffery？  
- [ ] 格式符合目標會議要求？  
- [ ] 頁數沒超過限制？  
- [ ] 有 Limitations section？（ACL 系列必備）

---

## 第九課：從審稿角度反看寫作

### Reviewer 看什麼？（ACL Rolling Review 五大維度）

1. **Soundness**：你的 claims 有足夠的 evidence 支持嗎？  
2. **Excitement**：這個工作有多令人興奮？多有影響力？  
3. **Reproducibility**：別人能重現你的結果嗎？  
4. **Overall**：該接受嗎？

### 常見拒稿原因（及對應寫作策略）

| 拒稿原因 | 寫作對策 |
| :---- | :---- |
| Novelty 不足 | Introduction 清楚建立 gap；explicitly 對比 prior work |
| 實驗不充分 | 多 dataset、ablation、error analysis |
| 寫作不清楚 | Topic sentences、pipeline 圖、consistent terminology |
| Motivation 不 convincing | 用具體例子說明問題的嚴重性 |
| Overclaiming | 用 "our results suggest" 而非 "our method proves" |

---

## Interspeech 4 頁空間分配指南

### 空間預算表

| Section | 佔比 | 字數 | 備註 |
| :---- | :---- | :---- | :---- |
| Abstract | 固定 | \~150 字 | 5 句公式 |
| Introduction | 25-30% | 800-950 | **最重要**，含 gap \+ contribution |
| Related Work | 10-15% | 300-450 | 可融入 Intro |
| Method | 25-30% | 800-950 | 重 insight 不重 detail |
| Experiments | 25-30% | 800-950 | Setup \+ Results \+ Ablation |
| Conclusion | 5-8% | 150-250 | 3-4 句即可 |

### 版面模板

Page 1: Title \+ Abstract \+ Intro(前半) \+ Figure 1

Page 2: Intro(後半) \+ Related Work \+ Method(前半)

Page 3: Method(後半) \+ Exp Setup \+ Main Results(Table 1\)

Page 4: Ablation(Table 2\) \+ Analysis \+ Conclusion

Page 5: References only

### 三個鐵律

1. **Figure 1 必須在第一頁** — reviewer 30 秒內要看懂你的方法  
2. **寧可砍 Method 文字，不可砍 Figure 1 和 Results Table**  
3. **Related Work 不超過半欄** — 融入 Intro 的 gap-building 更好

### 空間不夠時的砍稿順序

1. 砍 Related Work（融入 Intro）  
2. 砍 Training Details（移到 footnote）  
3. 砍 Baseline Descriptions（讓 table 自明）  
4. 砍 Conclusion（壓到 3 句）  
5. ❌ 絕不砍：Intro gap、Main Results、Figure 1

### Reviewer 注意力分配（按此順序優化）

Abstract(30s) → Figure 1(30s) → Results Table(60s) → Intro(2min) → Method(2min)

---

## 📊 實驗結果呈現（Experiments Section）

### MOS 必備清單

- [ ] 評分人數 ≥ 15（寫進文中）  
- [ ] 95% CI 或 error bar（不能只報平均）  
- [ ] 評分量表說明（引用 ITU-T P.800 或自述）  
- [ ] 評審者來源（MTurk/lab/Prolific）及 screening 方式  
- [ ] 每系統測試句數（通常 20-50）  
- [ ] Ground truth MOS（上界校準）  
- [ ] 統計顯著性檢驗（Wilcoxon / Mann-Whitney，標 \*p\<0.05）

### WER/CER 必備清單

- [ ] ≥ 2 個 test set（含 in-domain \+ out-of-domain）  
- [ ] Relative improvement %（不只報 absolute）  
- [ ] 粗體標示最佳結果  
- [ ] 說明 LM、beam size 等影響結果的設定  
- [ ] 統計顯著性（paired bootstrap / MAPSSWE）

### Ablation Study 設計

- 每行移除一個 component（one-at-a-time）  
- 3-6 行為佳（太少不 convincing，太多佔空間）  
- 加 Δ 欄位顯示貢獻量  
- 好的 ablation 回答「為什麼有效」，不只是「每個都有用」  
- 設計 ablation 時回答：你 propose 什麼，就 ablate 什麼

### 圖表 10 條規則

1. Table caption 上方、Figure caption 下方  
2. 每個圖表都要在正文 reference  
3. 圖中字體 ≥ 正文 80%  
4. 用向量圖（PDF），spectrogram 除外  
5. Colorblind-friendly 配色  
6. Bar chart y-axis 從零開始（除非標示 break）  
7. Spectrogram 標 axis label（Time, Freq, dB）  
8. MOS bar chart 附 error bar  
9. 用 ↓↑ 標示 metric 方向（WER↓、PESQ↑）  
10. Radar chart 適合多維度比較

### Baseline 選擇原則

- 必含：(1) 經典方法 (2) 當前 SOTA (3) 你方法的簡化版  
- 只跟自己舊方法比 \= contribution 不明確  
- Speech 常用 baseline：  
  - TTS: Tacotron2, VITS, FastSpeech2, NaturalSpeech  
  - ASR: Whisper, wav2vec2.0, HuBERT, Conformer-T  
  - SE: DCCRN, MetricGAN+, CMGAN  
  - VC: AutoVC, VQVC+, kNN-VC

---

## 第十課：Before/After 改寫範例集

💡 **教學建議**：這些範例可直接用於課堂教學。讓學生先判斷 Before 版有什麼問題，再看 After 版，最後讓他們用同樣原則改自己的稿子。

### A. Abstract 改寫

**Before ❌**

In this paper, we propose a novel method for speech enhancement. Our method uses a deep learning model to process noisy speech signals. We conduct extensive experiments on various datasets. The experimental results demonstrate that our proposed method significantly outperforms existing methods and achieves state-of-the-art performance.

**Problems**: "In this paper" 冗餘、"novel" 空洞 puffery、"significantly" 無數據支持、無 gap、無具體數字、無 insight。

**After ✅**

Diffusion-based speech enhancement methods have achieved strong denoising performance, but their iterative sampling process incurs high latency, limiting real-time deployment. We propose FastDiff-SE, which replaces the standard reverse diffusion with a one-step consistency distillation, reducing inference time by 50× while preserving enhancement quality. On VoiceBank-DEMAND, FastDiff-SE achieves 3.42 PESQ and 0.95 STOI with a real-time factor of 0.03, outperforming DCCRN (3.27 PESQ) and matching CMGAN (3.41 PESQ) at 1/20th the computational cost.

**Why better**: 有具體 gap（latency）、有 insight（consistency distillation）、有數字（PESQ、RTF）、有 baseline 對比。

---

### B. Introduction Gap 改寫

**Before ❌**

Many methods have been proposed for text-to-speech synthesis. However, there are still some problems. Therefore, we propose our method to address these issues.

**Problems**: Gap 完全不具體——什麼 problems？哪些 issues？Reviewer 看完不知道你要解什麼。

**After ✅**

Recent zero-shot TTS systems (VALL-E, NaturalSpeech 2\) achieve impressive speaker similarity from a 3-second prompt, but they rely on autoregressive token generation, requiring 200+ decoding steps per utterance. This makes them impractical for interactive applications where latency below 500ms is expected. We address this gap by reformulating zero-shot TTS as a single-step flow matching problem, reducing synthesis latency from 4.2s to 0.08s while maintaining comparable speaker similarity (cosine sim: 0.82 vs. 0.85).

**Why better**: 具體指出誰做了什麼（VALL-E, NaturalSpeech 2）、為什麼不夠好（200+ steps, high latency）、gap 的後果（impractical for interactive apps）、你的解法和數字。

---

### C. Contribution 改寫

**Before ❌**

Our contributions are as follows:

- We propose a novel framework for automatic speech recognition.  
- We conduct comprehensive experiments.  
- We achieve state-of-the-art results.

**Problems**: 每一條都是 activity（我做了什麼），不是 claim（我證明了什麼）。"Novel" 和 "comprehensive" 是空話。

**After ✅**

Our contributions are:

- We propose CTC-Align, a non-autoregressive ASR model that decouples alignment prediction from token prediction, enabling 12× faster inference than autoregressive baselines with \<1% WER degradation.  
- We show that alignment-conditioned decoding eliminates the "peaky" CTC distribution problem, improving WER by 8.3% relative on LibriSpeech-other compared to vanilla CTC.  
- We release pretrained models and training code for reproducibility.

**Why better**: 每條都有 What \+ How much \+ Why it matters。Reviewer 可以直接驗證。

---

### D. Method 描述改寫（Why \> How）

**Before ❌**

We first extract features using a pretrained model. Then we feed the features into a transformer encoder. The output is passed through a linear layer to get the final prediction.

**Problems**: 只有 how（步驟流水帳），沒有 why。Reviewer 看完不知道為什麼這樣設計。

**After ✅**

We build on the observation that pretrained SSL features capture complementary information at different layers: lower layers encode acoustic details while upper layers encode linguistic content (Pasad et al., 2021). Rather than using only the final-layer representation, we introduce a learnable weighted sum across all layers, allowing the model to adaptively select the most relevant features for each downstream task. The fused representation is processed by a 6-layer Transformer encoder, chosen to balance model capacity with the 4-page Interspeech constraint on training compute.

**Why better**: 每個設計選擇都有理由。讀者理解 why weighted sum（complementary info）、why Transformer（capacity）、why 6 layers（compute constraint）。

---

### E. Results 解讀改寫

**Before ❌**

As shown in Table 1, our method achieves the best performance on all datasets.

**Problems**: 沒有 insight。哪些 dataset？好多少？為什麼好？

**After ✅**

Table 1 shows that CTC-Align outperforms all baselines on LibriSpeech test-clean (2.8% WER, −12.5% relative vs. Conformer-T) and test-other (6.9% WER, −11.5% relative). The improvement is more pronounced on the noisier test-other split, suggesting that the explicit alignment module is particularly beneficial when acoustic conditions are challenging. On WSJ, the gap narrows to 4.5% vs. 5.1% for the baseline, likely because WSJ's read speech provides clearer alignment cues even without our module.

**Why better**: 有數字、有 relative improvement、有 insight（noisier \= bigger gap）、主動解釋 negative/weaker result（WSJ gap narrows）。

---

### F. Related Work 改寫（從列舉到定位）

**Before ❌**

Smith et al. (2023) proposed method A. Jones et al. (2024) proposed method B. Lee et al. (2024) proposed method C. Our method is different from these methods.

**Problems**: 流水帳、沒有比較、"different" 沒說怎麼 different。

**After ✅**

SSL-based ASR methods can be categorized by how they leverage pretrained representations. Fine-tuning approaches (Baevski et al., 2020; Hsu et al., 2021\) adapt the entire model to downstream data, achieving strong results but requiring substantial compute per task. Adapter-based methods (Thomas et al., 2022; Chen et al., 2023\) reduce trainable parameters by inserting lightweight modules, but they still depend on autoregressive decoding, limiting inference speed. Our work combines the parameter efficiency of adapters with non-autoregressive decoding, achieving comparable accuracy at 12× lower latency—a trade-off not explored in prior work.

**Why better**: 按主題分組（fine-tuning vs adapter）、每類指出優缺點、最後清楚定位自己的差異和獨特貢獻。

---

### G. 模糊表達改寫（Precision）

| Before ❌ | After ✅ | 問題 |
| :---- | :---- | :---- |
| significantly outperforms | outperforms by 3.2% WER (p\<0.01) | 無數據 → 有數據 |
| various datasets | 4 benchmark datasets (LS, WSJ, AISHELL, CV) | 模糊 → 具體 |
| a large improvement | \+6.3 SUPERB score (12.8% relative) | 形容詞 → 數字 |
| our method is efficient | RTF=0.03 on a single V100 GPU | 空話 → 可量化 |
| we use a deep model | 12-layer Conformer (110M params) | 模糊 → 精確 |
| extensive experiments | experiments on 4 datasets with 3 metrics | 空話 → 範圍 |
| SOTA results | lowest WER among non-AR models on LS test-other | 過度宣稱 → scoped claim |
| promising results | competitive with SOTA (within 0.3% WER) with 5× speedup | 模糊 → trade-off |
| our novel approach | our approach (刪掉 novel) | puffery → 讓結果說話 |
| clearly demonstrates | the results indicate / the data suggest | overclaim → hedged |

---

### H. Transition 改寫

**Before ❌**

Our method performs well. And we also test on another dataset. The results are good.

**After ✅**

While the results on LibriSpeech confirm our method's effectiveness on read English speech, a natural question is whether these gains transfer to more challenging conditions. To investigate this, we evaluate on CommonVoice, which includes accented and noisy recordings. As shown in Table 2, the improvements persist (+2.1% WER), though the margin decreases—suggesting that our alignment module's benefit is partially redundant with the robustness already captured by the SSL backbone.

**Why better**: 有邏輯連接（while → natural question → to investigate → as shown → suggesting）、有 insight、有 honest analysis。

---

### I. Conclusion 改寫

**Before ❌**

In this paper, we proposed a method for ASR. The experimental results show our method is effective. In the future, we will extend our method to more languages.

**After ✅**

We presented CTC-Align, demonstrating that decoupling alignment from token prediction enables non-autoregressive ASR to close the gap with autoregressive models while providing 12× inference speedup. Our analysis reveals that explicit alignment is most impactful under noisy conditions, suggesting a complementary role to SSL pretraining. Current limitations include degraded performance on code-switched speech, where alignment boundaries are ambiguous. Future work will explore multilingual alignment strategies that handle intra-utterance language switches.

**Why better**: 有核心 insight（decoupling \= key）、有 finding（noisy \= most impactful）、limitation 具體且附 reason、future work 具體且承接 limitation。

---

## 從 Best Paper 學精準英文（EFFUSE, Interspeech 2024 Best Paper）

### 動詞精準度 Cheat Sheet

| 場景 | ❌ 模糊 | ✅ 精準 |
| :---- | :---- | :---- |
| 提出方法 | "We use/apply" | "We propose... that employs..." |
| 比較結果 | "is better than" | "outperforms... while decreasing..." |
| 描述近似 | "approximates" | "mimics"（更生動且精確） |
| 建立假設 | "So we think..." | "Thus, we hypothesize that..." |

### 數字表達黃金法則

- 永遠同時給 **absolute \+ relative** improvement  
- 例：❌ "significantly improves" → ✅ "reduces CER by 4.5 absolute (20% relative)"

### 4 頁結構技巧

- 不需要獨立 Related Work section — 整合進 Introduction  
- 如果 method 基於假設，花半頁做 pilot study 先證明假設（比口頭 "we hypothesize" 有力 100 倍）  
- Table caption 要寫結論，不只描述內容

### Contribution 列表平行結構

(1) we extensively explore...    ← 調查

(2) we propose a novel...       ← 提出

(3) we demonstrate that...      ← 驗證

三條文法結構一致、抽象程度一致、邏輯遞進。

---

## 第十一課：中文母語者 30 個常見學術英文錯誤

### 🎯 為什麼這很重要

Language polishing 不只是 cosmetic——寫作品質差會讓 reviewer 質疑 soundness。Schulzrinne 說：「Consider the rules as mental rumble strips.」

### 六大類錯誤速查表

**A. 冠詞（最大重災區）**

- 可數名詞首次出現用 a/an：❌ "We propose method" → ✅ "We propose **a** method"  
- 已定義對象用 the：❌ "model achieves" → ✅ "**the** model achieves"  
- 泛指概念不加 the：❌ "**The** speech recognition is..." → ✅ "Speech recognition is..."  
- 縮寫不加 the：❌ "**The** ASR model" → ✅ "ASR model"（除非指 the ASR-based model）

**B. 動詞**

- 主動 \> 被動：❌ "It is shown that..." → ✅ "We show that..." / "Our results show..."  
- 強動詞 \> 弱名詞：❌ "make an assumption" → ✅ "assume"；❌ "perform training" → ✅ "train"  
- et al. 用複數動詞：❌ "Smith et al. shows" → ✅ "Smith et al. **show**"  
- 時態：描述本文 \= 現在式；引用他人已完成工作 \= 過去式

**C. 句型**

- 一句不超過 30 字，否則拆開  
- Dangling modifier：❌ "Using X, the WER was reduced." → ✅ "Using X, **we** reduced the WER."  
- 避免 "There is/are" 開頭  
- 名詞堆疊 ≤3：❌ "speech recognition error rate reduction method" → ✅ "a method for reducing the error rate"

**D. 用詞**

- 刪 "novel"（讓方法自己展現新穎性）  
- "significantly" 必須附 p-value 或具體數字  
- "utilize" → "use"  
- "etc." → 具體列舉  
- "various/several" → 具體數字  
- which（非限定，加逗號）vs that（限定，不加逗號）

**E. 標點格式**

- Oxford comma：✅ "A, B\*\*,\*\* and C"  
- 數字 ≤10 拼出來（除了跟單位一起）  
- 數字和單位之間有空格：✅ "16 kHz"、"0.5 s"  
- kHz 的 k 小寫  
- 引用用作者名：❌ "\[1\] shows" → ✅ "Smith et al. \[1\] show"

**F. 邏輯連接**

- 連續句子必須有邏輯連接詞（however / thus / in contrast / specifically）  
- 不以 "And" 開頭  
- this/that 後面跟名詞：❌ "This is important." → ✅ "This **finding** is important."

### 🔧 5 分鐘自查（用搜尋）

grep \-i "novel" → 考慮刪除

grep \-i "utilize" → 改成 use

grep \-i "etc\\." → 改成具體列舉

grep \-i "significant" → 確認有數字

grep \-i "there is\\|there are" → 改主動句

grep \-i "in this paper" → 不超過 2 次

💡 **教學建議**：讓學生交稿前跑一遍這 6 個 grep，5 分鐘內可以抓出 80% 常見問題。冠詞問題建議另外跑一遍專門的「冠詞校稿」——讀每個名詞，問自己：需要 a/the/零冠詞？

---

## 附錄：推薦資源

1. Simon Peyton Jones, "How to Write a Great Research Paper" — [Microsoft Research](https://www.microsoft.com/en-us/research/academic-program/write-great-research-paper/)  
2. Derek Dreyer, "How to Write Papers So People Can Read Them" — [YouTube](https://www.youtube.com/watch?v=PM1Atui30qU)  
3. Henning Schulzrinne, "Writing Technical Articles" — [Columbia CS](https://www.cs.columbia.edu/~hgs/etc/writing-style.html)  
4. Michael Ernst, "How to Write a Technical Paper" — [UW](https://homes.cs.washington.edu/~mernst/advice/write-technical-paper.html)  
5. ACL Rolling Review Reviewer Guidelines — [ARR](https://aclrollingreview.org/reviewerguidelines)

---

## ⚠️ Interspeech 2026 新制度：Long Paper Track

Interspeech 2026（Sydney, 9/28-10/1）首次引入 Long Paper track：

- **Regular Paper**：4 pages \+ 1 ref（傳統格式）  
- **Long Paper**：8 pages \+ 2 ref/ack（**新增**，目標接受率 \<30%）  
- 截止日相同：2/25 AoE（Paper Update: 3/04 AoE）  
- Long Paper 定位：extended, high-impact contributions

### 建議

- 多數學生應投 **Regular 4-page**（首次投稿，4 頁限制反而是保護）  
- 只有研究深度足夠（有 pilot study \+ 完整 ablation \+ error analysis）才考慮 Long Paper  
- 新增主題 "Generative AI for Speech and Language Processing" 適合 LALM 相關研究

