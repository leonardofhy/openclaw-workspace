下面我把「**Localizing the Listen Layer in Speech LLMs**」拆成一個可被檢驗的命題，先做文獻證據盤點（支持 / 反駁），再把「行為證據 vs 因果定位」切清楚，最後給你 3 個 **3–6 小時、單機/單 GPU 可做**的 MVP 實驗卡（可直接貼到計畫書）。

---

## 我對命題的操作性定義

**Speech LLM / Speech-Enabled LLM**：能直接吃「語音/音訊特徵或音訊 token」並輸出文字（或語音）的 LLM 系統（典型是 speech encoder + adapter/projector + LLM，或在 LLM 內插 cross-attention / 分支）。 ([arXiv][1])

**Listen Layer（可被定位的「聽覺層」）**：在 LLM 內部的某個 layer（或一小段 layer 區間 / 某些注入層），其對「語音條件輸入」的整合是**因果關鍵**：

* 若在該 layer 做定向干預（mask/scale cross-modal attention、patch activation、改注入深度），模型在語音任務上的輸出會顯著改變（性能掉或恢復）。
* 若只是看到 attention 比較高、或 hidden state 相似度比較高，那是**行為線索**，不等於因果。

---

## Evidence for / Against 對照表（含「行為 vs 因果」標註）

> 註：同一篇常同時有行為與因果；「因果定位」我只算 **layer/模組/注入深度可干預、且性能跟著變** 的證據（不是純相關）。

| 文獻                                                 | Evidence **for**（支持「可定位」）                                                                                                                                                                       | Evidence **against / 限制**（反駁或削弱）                                                                                                                              | 證據型態                                                             | 定位粒度                                |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- | ----------------------------------- |
| **MATA (2025)**：推理時放大 audio attention              | 觀察到在 **decoder 的 intermediate layers**，audio attention 長期偏低、而這些層被視為多模態融合關鍵；並且「只在 intermediate layers 干預」效果最好，早/晚層干預較差（早層甚至崩）。→ 指向「融合/聽覺關鍵區段」可被定位。([arXiv][2])                                   | 「最佳」是某段 *intermediate range* 而非單一層；早層崩可能是「上下文編碼被破壞」而非聽覺機制本身，表示層功能高度耦合。([arXiv][2])                                                                            | 行為（attention 分佈）+ **因果**（layer 指定干預→性能變）([arXiv][2])             | LLM 中間層區段（layer range）              |
| **VOX-KRIKRI (2025)**：指定「注入層 I」做 cross-attn 融合     | 明確把 cross-modal attention **插在 LLM 的某一層 I**，並 sweep I={1,9,15,21,30}：結果 **intermediate-to-late（15/21/30）普遍優於 early（1/9）**，且 21 常最好。→ 「聽覺融合發生在某些深度更有效」具可定位性。([arXiv][3])                         | 任務是 ASR（希臘語）；可能把「listen layer」定位成「ASR 融合最佳深度」而不等於「通用語音推理 listen layer」。作者也提到未來想做 multi-layer injection，暗示單點注入未必最終。([arXiv][3])                                | **因果**（注入深度 ablation）+ 行為（CCA/對齊分析）([arXiv][3])                  | 單一注入層（injection depth）              |
| **MOSS-Speech (2025)**：模態分支 split at block 32      | layer-wise speech/text hidden-state cosine similarity：前段逐步融合、最後幾層下降（再分化）；因此在 **36-layer transformer 的第 32 層做 modality-based layer split**：前 N 層共享融合、最後層做模態專屬生成。→ 支持「存在可定位的融合→分化邊界」。([arXiv][4]) | 相似度曲線本身是相關（行為）；split 點（32/36）也高度架構依賴，不保證可移植到其他 speech LLM。([arXiv][4])                                                                                        | 行為（相似度）+ **因果**（架構層分支設計）([arXiv][4])                             | 「融合/分化邊界」+ 頂層模態專屬堆疊                 |
| **Understanding Modality Gap (EMNLP 2025)**        | 顯示 speech/text 在深層方向（cosine）更對齊、但幅度（Euclidean）發散；並且提出 **token-level 介入**（把最不對齊的 speech token 做 angle projection）能提升 speech QA 正確率。→ 支持「至少有可干預的關鍵位置」。([ACL Anthology][5])                        | 他們觀察是「cosine 隨深度普遍上升」而非某單一層峰值 → 更像分佈式；而且介入是 token-level，不直接告訴你「哪一層是 listen layer」。([ACL Anthology][5])                                                        | 行為（layer-wise 相似度/相關）+ **因果**（token 干預→QA 變）([ACL Anthology][5]) | 分佈式 across layers + token-level 關鍵點 |
| **AI-STA (2025)**：選層做 speech-text alignment        | 明確主張「在 selected layers 對齊 speech/text」；且實驗顯示**選哪幾層差很大**：只對齊 layer0 有小幅增益；對齊更多內層反而降；不對齊 layer0 甚至 loss 不收斂（catastrophic failure）；最佳是（例）selected layers 0–1。→ 支持「關鍵層可定位」。([arXiv][6])             | 這個結果把「關鍵」推向**極早層（embedding/前幾層）**，與 MATA / VoxKrikri 指向中間層作融合「看起來衝突」→ 暗示 listen layer **可能不是單一位置、而是任務/訓練目標依賴**（ST vs 推理/QA vs ASR）。([arXiv][6])               | **因果**（把 loss 掛在某些層→性能/收斂變）+ 行為（layer-wise MRR 趨勢）([arXiv][6])   | 早層（embedding/Layer 0–1）             |
| **BESTOW (2024)**：把「聽」放在 LLM 之前的小模組                | 把 speech modality 用「cross-attention feature extractor」在進 LLM 前處理；並指出 cross-attention layer 可重複 X 次、且 ablation 找到 **X=2** 合理。→ 支持「listen 功能可被壓縮/定位到小模組」，不必擴散到 LLM 全部層。([arXiv][7])               | 這其實是在說「listen layer 不一定在 LLM 裡」：把聽覺抽出去做 adapter，反而削弱了「要在 LLM 內定位」的必要性。([arXiv][7])                                                                            | **因果**（架構/模組深度 ablation）([arXiv][7])                             | LLM 前端模組（非 LLM 內層）                  |
| **How to Connect SFM+LLM (2024/2025)**             | 系統性比較 SFM/adapter/LLM：adapter 的確有影響、且不同組合最優不同 → 支持「某些連接模組是有效槓桿」。([arXiv][1])                                                                                                                    | 更強的訊息是：**SFM（speech foundation model）影響最關鍵**，adapter 影響較中等。→ 反過來說，「聽覺能力可能主要在 speech encoder/前端」，而不是 LLM 內某一 listen layer。([arXiv][1])                         | **因果**（組件 ablation）([arXiv][1])                                  | 組件級（SFM vs adapter vs LLM），非 LLM 層級 |
| **NAACL 2025：Cross-attn vs Decoder-Prepend (S2T)** | 直接比較「cross-attention」與「speech embeddings prepending」：兩者在多設定下結果相近，且在壓縮/速度/記憶體上互有利弊。→ 支持「listen 機制可以被不同方式承載」，不必限定成單一 listen layer。([ACL Anthology][8])                                            | 若 prepend（不加 LLM 內 cross-attn）也能做到相近品質，則「必有一個 LLM 內 listen layer」的強版本命題被削弱：listen 可能是**分佈式 self-attention 的自然結果**（只要把 speech tokens 丟進去）。([ACL Anthology][8]) | **因果**（架構比較）([ACL Anthology][8])                                 | 架構級（prepend vs cross-attn）          |
| **TARS (2026)**：Closing modality reasoning gap     | 明確把 speech 推理弱點歸因於 **跨層 hidden-state drift**，並用 layer-wise cosine similarity 做 representation alignment signal；layer-wise 分析顯示加入 alignment 會整體抬升相似度曲線。→ 支持「層級結構可被度量與干預」。([arXiv][9])            | 但它更像「跨多層的軌跡/表徵漂移」問題，而不是能縮成單一 listen layer；也表示定位可能需要看「多層」而非單層。([arXiv][9])                                                                                     | 行為（layer-wise 相似度）+ **因果**（對齊訓練→漂移減/性能增）([arXiv][9])             | 分佈式 across layers（trajectory-level） |

---

## 綜合判讀：這個命題「哪一種版本」比較站得住腳？

* **強版本（存在單一 listen layer）**：目前證據不夠一致。

  * VoxKrikri 的最佳注入深度偏中後層。([arXiv][3])
  * MATA 指向 intermediate fusion layers。([arXiv][2])
  * AI-STA 卻顯示 early layers（0–1）對齊最關鍵，內層反而害。([arXiv][6])

* **弱版本（存在可定位的 listen “區段/介面”）**：證據更強。常見模式是：

  1. **早層**：做模態對齊/尺度校正（embedding/前幾層）。([arXiv][6])
  2. **中層**：做語音-文本融合與證據提取（fusion heavy）。([arXiv][2])
  3. **頂層**：可能走向模態專屬生成/表面化（可分支）。([arXiv][4])

因此，如果你要做「localization」，我建議你的研究問題寫成：

> **在特定 Speech LLM 架構下，listen function 是否集中於一小段 layer（或單點注入層），並可用因果干預找出「最敏感區段」？**

---

## Experiment Cards x3（3–6 小時、單機/單 GPU、少依賴私有模型）

> 我會把每張卡都設計成「能跑出一條 layer→敏感度曲線」或「能給出明確因果定位結論」。

---

### Experiment Card 1 — Layer-wise Audio Attention Suppression Curve（推理時、零訓練）

**假設**
在一個 speech-enabled LLM 中，存在一段 transformer layers 是「audio→text 融合」的主要因果位置；在這些層把「文字 token 對 audio tokens 的注意力」抑制掉，speech 任務性能會急遽下降；其他層抑制的影響較小或僅平滑下降。

**變因與對照組**

* 自變因：干預的 layer index `l`（逐層 sweep）
* 干預方式（選一種即可 MVP）：

  * **Mask**：在 layer `l` 的 self-attn，把 query（當前生成 token）對 audio token positions 的 attention logits 設為 `-inf`（或直接置零權重）。
  * **Scale**：把對 audio token 的 attention weight 乘上一個 β（例如 0.0=全關、0.5、1.0=不變、2.0）。
* 對照組：

  1. 不干預（baseline）
  2. **Audio corrupted**（把音訊換成靜音或隨機片段）但不干預，用來估計模型原本的「音訊依賴度」。
  3. （可選）只 mask text-to-text attention（同等幅度），檢查是否只是一般干預造成的退化。

**指標**

* 任務指標：

  * Audio QA / Audio MC：Accuracy（建議只抽 50–200 題就夠做曲線）
  * 若是 ASR 類：WER/CER（抽 50–100 句）
* 「音訊依賴」指標：

  * `Audio Reliance = Acc(clean audio) - Acc(corrupted audio)`
  * 觀察干預後 Reliance 是否大幅縮小（表示模型不再用音訊）。
* 「層敏感度」曲線：`ΔAcc(l) = Acc_baseline - Acc_with_mask_at_layer_l`

**預期觀察**

* 若 listen layer 可被定位：

  * `ΔAcc(l)` 會在某段 layer 出現尖峰（或明顯 plateau），對應「融合層區段」。
  * 常見猜測：中間層敏感度較高（與 MATA 對 intermediate layers 的結論一致）。([arXiv][2])
* 若 listen 分佈式：

  * `ΔAcc(l)` 會平滑、沒有明顯峰值；或需要同時抑制多層才會掉。

**失敗模式與替代方案**

* 失敗模式 A：模型輸出太不穩定（開放式生成，難評分）

  * 替代：把任務改成 **multiple-choice** 或 forced decoding（計算正確選項 logit）。
* 失敗模式 B：你 mask 的位置不是模型真正的「audio tokens」位置（有些模型把音訊先投影成 prefix embeddings、或經過 Q-Former）

  * 替代：先印出 input embedding 序列的 segment 邊界（audio span / text span），或改用「mask cross-attn module」的模型。
* 失敗模式 C：一 mask 就全崩（可能早層承擔 general context）

  * 替代：只對「最後一個生成 token」做 mask（類似 MATA 只針對最後 token 干預的做法）。([arXiv][2])

---

### Experiment Card 2 — Causal Tracing by Activation Patching（乾淨 vs 破壞音訊）

**假設**
存在一段 layers 的 hidden states 是「音訊資訊影響答案」的關鍵因果通道：
把「乾淨音訊」在該 layer 的 activation patch 到「破壞音訊」的 forward pass 中，可以顯著恢復正確答案機率（logit/prob）。

**變因與對照組**

* 自變因 1：patch 的 layer `l`
* 自變因 2：patch 的部位：

  * residual stream（pre-attn / post-attn / post-mlp 任選一個做 MVP）
  * token positions：只 patch audio-span、只 patch最後生成前的 query token、或 patch全部
* 對照組：

  1. 不 patch（corrupted audio baseline）
  2. patch 來自「另一個樣本」的 clean activation（控制「只是 patch 造成擾動」）
  3. patch noise（零向量或亂數）

**指標**

* `Recovery(l) = P_correct(patched at l) - P_correct(corrupted baseline)`

  * 若是 multiple-choice：用「正確選項」的 logit 或 softmax prob。
* `Peak layer(s)`：Recovery 最大的 layer 區段（就是你要的因果定位候選）

**預期觀察**

* 若 listen 層集中：Recovery 會在某段 layer 出現明顯峰值（patch 那段最能救回）。
* 若 listen 分佈式：Recovery 分散，需要 patch 多段 layer 才能救回。
* 額外可做的診斷：

  * 只 patch audio-span vs 只 patch text-span：若 audio-span patch 更有效，表示「音訊資訊確實在該層以某種表徵形式存在」。

**失敗模式與替代方案**

* 失敗模式 A：corrupted audio 仍然答對（沒有差異就無法 patch）

  * 替代：選更「純聽覺」的題（例如語者說了哪個數字/關鍵詞），或把 prompt 設計成必須依賴音訊（把文字提示拿掉）。
* 失敗模式 B：patch 後生成不穩定、解碼漂移

  * 替代：改成只看 **第一個答案 token** 的 logit（例如 A/B/C/D），不要整段生成。
* 失敗模式 C：量化/Flash-attn 讓 hook 很難插

  * 替代：用較小模型或關閉某些 fused kernel；或改做「attention masking」(Experiment 1) 先得到粗定位，再做 patch 的少量 layer。

---

### Experiment Card 3 — Layer-Restricted LoRA Sweep（小資料、少步數、直接回答「哪一段層需要學」）

> 這張卡的核心：**用“只讓某一段 layers 可訓練”來做因果定位**。如果「聽覺能力/融合能力」主要集中在某段 layers，那只訓練那段就會得到大部分增益。

**假設**
在 speech LLM（或 speech+adapter+LLM）上，語音任務的提升主要來自某段 transformer layers（early 對齊 vs mid 融合 vs late 決策）。只對那段做 LoRA（其餘全 freeze）就能取得接近全量 LoRA 的效果；其他段效果顯著較差或不收斂（類似 AI-STA 對「選錯層」會掉甚至崩的現象）。([arXiv][6])

**變因與對照組**

* 自變因：LoRA 的層範圍（保持 trainable 參數量相近）

  * Group E（Early）：layers 0–3（含 embedding/前幾層）
  * Group M（Middle）：layers 8–11（中間段）
  * Group L（Late）：layers 16–19（後段）
  * （依模型總層數線性縮放）
* 對照組：

  1. LoRA-All（全層 LoRA，作為上限）
  2. Adapter-only（只訓練 speech projector / Q-Former，LLM 全凍結）
  3. No-train baseline

**指標**

* Speech 任務：

  * ASR：WER/CER（抽 100–500 句即可 MVP）
  * Audio QA：Accuracy（抽 50–200 題即可）
* Text 能力保留（避免「為了聽而忘了說」）：

  * Text-only QA 小集合 accuracy 或 ppl（用一個固定小集合即可）
* 訓練穩定性：loss 是否收斂、是否出現 mode collapse

**預期觀察**

* 若 listen layer 可被定位：

  * 某一組（E/M/L）會明顯領先其他組，且接近 LoRA-All。
  * 可能出現「E 組幫助對齊/收斂」、「M 組幫助融合推理」、「L 組幫助決策輸出」的分工（與多篇文獻的“早/中/頂層角色不同”相容）。([arXiv][2])
* 若 listen 分佈式：

  * 單一組增益有限，LoRA-All 才明顯。

**失敗模式與替代方案**

* 失敗模式 A：LoRA 訓練太慢（7B 仍吃緊）

  * 替代：用 1–3B 級 backbone（或 7B 但 QLoRA + 低 rank + 小 batch），或把資料量縮到 1k steps 內只看趨勢。
* 失敗模式 B：只訓練 early layers 造成 text 能力掉太多（catastrophic forgetting）

  * 替代：加上「text-only regularization」：每 N steps 混一小批 text 指令資料，或只訓練 layernorm/adapter。
* 失敗模式 C：任務太簡單（例如純 ASR），不同層都差不多

  * 替代：換成需要「聽 + 推理」的題（如 audio QA / audio entailment），或加入干擾（噪音、口音）放大融合需求。

---

## 你可以怎麼把這三個 MVP 串成 1 個「定位→驗證」流程（建議順序）

1. **Experiment 1** 先跑：最省事，直接得到「層敏感度曲線」，快速猜測 listen layer range。
2. **Experiment 2** 再跑：用 activation patching 把「敏感區段」變成更像因果證據（能救回 logit）。
3. **Experiment 3** 最後跑：用「只訓練某段層」驗證這段層是否真的是可學、可承載 listen 的關鍵參數區。

這樣你就同時滿足：

* 文獻中「intermediate fusion」(MATA / VoxKrikri) ([arXiv][2])
* 文獻中「early alignment critical」(AI-STA) ([arXiv][6])
* 文獻中「頂層可分支/專屬生成」(MOSS-Speech) ([arXiv][4])

---

如果你願意把你目前想用的 **模型名稱（HF repo 或 checkpoint）** 與 **任務類型（ASR / ST / audio QA / speech reasoning）** 告訴我，我可以把三張卡的「layer 分組方式、audio token span 的抓法、以及最小資料集選擇」直接替你落成更貼近你系統的版本（不需要再查資料）。

[1]: https://www.arxiv.org/pdf/2409.17044 "https://www.arxiv.org/pdf/2409.17044"
[2]: https://arxiv.org/pdf/2509.18816 "https://arxiv.org/pdf/2509.18816"
[3]: https://arxiv.org/pdf/2509.15667 "https://arxiv.org/pdf/2509.15667"
[4]: https://arxiv.org/pdf/2510.00499 "https://arxiv.org/pdf/2510.00499"
[5]: https://aclanthology.org/2025.emnlp-main.262.pdf "https://aclanthology.org/2025.emnlp-main.262.pdf"
[6]: https://arxiv.org/pdf/2503.10211 "https://arxiv.org/pdf/2503.10211"
[7]: https://arxiv.org/pdf/2406.19954 "https://arxiv.org/pdf/2406.19954"
[8]: https://aclanthology.org/2025.naacl-long.153.pdf "https://aclanthology.org/2025.naacl-long.153.pdf"
[9]: https://arxiv.org/pdf/2601.05543 "https://arxiv.org/pdf/2601.05543"
