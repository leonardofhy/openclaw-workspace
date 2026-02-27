## 一頁 paper blueprint（NeurIPS/ICLR 敘事骨架）

**Working title**
**Causal Pathways from Waveforms to Words: Temporal Attribution Patching for Mechanistic Interpretability of Speech LLMs**

**1–2 句貢獻（放在 Introduction 最後一段）**
我們提出 **Temporal Attribution Patching (TAP)**：把 text-LMM 常用的 activation patching / causal tracing 以「**可擴展**、**時間對齊**」的方式移植到 Speech LLM（AudioLLM / SLM），先用梯度近似（attribution patching）快速縮小可疑元件，再以精確 patching + causal scrubbing 驗證，產出 **layer×time 的因果地圖**，並用「子空間介入」證明語音→文字內容的關鍵表徵是**緊緻且可轉移**的。 ([Neel Nanda][1])

---

### 1) Problem framing（為何重要、現有缺口）

**為何重要（兩個角度：可靠性 + 安全/部署）**

* Speech LLM 近兩年快速變成主流互動介面：從「整合 audio encoder + LLM」的通用聽覺模型（如 SALMONN、Qwen2-Audio）到低延遲 speech-to-speech / full-duplex 對話系統（如 Moshi、LLaMA-Omni 等），都在把語音作為第一等輸入/輸出。 ([arXiv][2])
* 但 **可用 ≠ 可理解**：語音是連續高維訊號，錯誤型態（幻覺、重複、對噪音/口音敏感）與 text-only LLM 不同。更關鍵的是安全面：EMNLP’25 的 SPIRIT 顯示 speech language models 在白箱音訊 jailbreak 下可達到極高（部分情境 100%）攻擊成功率，而推論期 activation patching 介入可在**不重訓**下把 robustness 拉到很高。這直接說明：**理解內部因果機制**不只是「解釋」，也能導向「可部署的修補」。 ([ACL Anthology][3])

**現有缺口（把 related work 分三塊，然後指出空白）**

1. **Text LLM 的 mech interp 工具箱很強，但 speech 端缺「對齊到時間的因果 protocol」**：activation patching 的結果會受 corruption 方式、metric、patch 粒度影響，ICLR’24 已系統化整理「最佳實務」與陷阱；speech domain 若照搬，常會遇到序列長度不一致、時間對齊不明確等問題。 ([ICLR Proceedings][4])
2. **Speech 端開始有人做 mech interp，但多聚焦 ASR 或 feature discovery，尚未形成「端到端 speech-instruction-following 的因果敘事」**：

   * *Beyond Transcription* (2025) 把 logit lens / probing / activation patching 系統化搬到 ASR（Whisper、Qwen2-Audio），是重要起點，但主要仍在「轉錄與失效模式」層級。 ([arXiv][5])
   * *AR&D* (2026) 用 SAE 把 AudioLLM 的 polysemantic activation 分解成較單義的音訊概念，並用代表片段+自動描述+steering 驗證，偏向「概念字典」而非「語音→token 的因果路徑」。 ([arXiv][6])
3. **跨條件/跨模態的因果轉移是機會點**：2026 的 brain-to-speech 研究用 cross-mode activation patching + coarse-to-fine tracing + causal scrubbing 找到「共享的因果流形與緊緻子空間」——這個思路非常適合移植到「同一句話不同 speaker/noise/prosody」的語音條件。 ([arXiv][7])

**因此，你的 paper gap 可寫成一句話**

> 現有工作要嘛在語音系統做描述性分析（probes/attention/ASR failure），要嘛做概念發現（SAE features），但缺少一個 **可擴展、可重現、以因果介入為核心** 的方法，去回答：Speech LLM 何時、在哪裡、用哪些內部表徵把連續語音變成可供 LLM 推理/遵循指令的文字內容？

---

### 2) Method novelty（最小但有力）

**核心最小新意：把「activation patching」變成 speech 可用的三段式 protocol**
我們提出 **TAP = (Attribution search → Confirmatory patching → Subspace verification)**：

**(A) Attribution Search（快）**

* 以 Neel Nanda 2026 的 **attribution patching** 作為「activation patching 的線性近似」：兩次 forward + 一次 backward 同時計算大量候選元件的重要性，讓你能在 speech LLM（超大、序列超長）做**粗搜**。 ([Neel Nanda][1])
* 針對 speech：候選介入點不只 layer/head/neuron，還包含 **time window（音訊 frame 區段）** 與 **audio–text connector**（projector / cross-attention key-value 等）。

**(B) Confirmatory Activation Patching（準）**

* 對 attribution 搜出來的 top-K 元件，做精確 activation patching（clean→corrupt）並遵守 ICLR’24 的 patching best practices（多 corruption、metric 對照、random controls、normalization）。 ([ICLR Proceedings][4])
* 產出 **Layer×Time Causal Map**：像 brain-to-speech 的 sliding window tracing 一樣，回答「哪一段聲音、在模型哪個深度，對哪個輸出 token 是必要/充分」。 ([arXiv][7])

**(C) Subspace Verification（把 mech claim 變可被攻擊、也可被守住的“硬證據”）**

* 提出一個可檢驗假說：**lexical content** 在 audio→LLM 的接口上落在「緊緻子空間」，而 paralinguistics（emotion、speaker、prosody）在可分離的子空間。
* 做法最小化：

  * 方案 1（輕量）：在 connector residual stream 上做 PCA / CCA / linear subspace search，然後做 subspace patching + random subspace 對照。
  * 方案 2（更強）：沿用 AR&D/SAE 思路把特徵稀疏化，但你不只“命名概念”，還要用 **patching** 證明它對「正確回答」的因果性。 ([arXiv][6])
* 用 **causal scrubbing** 做最終驗證：只保留你聲稱的子空間，其他表徵 resample/ablate，行為仍保持 → 這是 mech interp 社群熟悉且強的「可證偽」框架。 ([Lawrence Chan][8])

> 你的「最小但有力」賣點：**不是發明全新工具**，而是把已有工具（attribution patching + activation patching + causal scrubbing）組成一個 speech 可落地、可重現、可做出強因果主張的 protocol。

---

### 3) Evidence design（主實驗 + ablation + sanity checks）

#### 主實驗（3 個主結果，對應 3 張 figure）

**E1. Layer×Time Causal Map（定位“語音變成文字”的 bottleneck）**

* Models：至少 2 個開源 SLM（建議 Qwen2-Audio-7B-Instruct + SALMONN；若想更貼近 speech-to-speech，可加 LLaMA-Omni）。 ([arXiv][9])
* Tasks：

  1. **短答案 spoken instruction following**（可用 AIR-Bench 的 speech 子任務或自建可自動評分的指令集）。 ([arXiv][10])
  2. **ASR / speech translation**（有明確字串或 BLEU/WER 指標，降低 judge 爭議）。
* Data：**controlled minimal-pairs**（TTS 或音訊編輯產生）

  * phoneme minimal pair（/b/→/p/、同音異義）
  * speaker swap（同文本不同 speaker）
  * prosody/emotion edit（同文本不同情緒/語氣）
  * noise/distractor mix（同文本加背景干擾）
* Output：對每個 pair，做 TAP→得到 “哪些 layer/time/component 對正確 token 的 logit diff 是必要/充分”。

**E2. Causal Transfer（證明你找到的是“可移植的因果表徵”，不是相關性）**

* 證據型態要做成「雙向」：

  * Sufficiency：把 clean 的關鍵子空間 patch 到 corrupt → 表現恢復
  * Necessity：把 corrupt 的關鍵子空間 patch 到 clean → 表現崩壞
* 再做「跨條件」：speaker A 的 lexical subspace patch 到 speaker B → 文字內容跟 A 對齊、但 speaker/prosody 指標盡量不變（或反之）。
* 這裡可以借用 brain-to-speech 那篇的敘事（shared causal manifold / compact subspaces / saturation curves）。 ([arXiv][7])

**E3. Practical payoff（把 mech interp 變成“可用”）**

* 兩個選擇其一（或兩者都做）：

  * **Robustness**：針對 distractor/noise，對 identified bottleneck 做推論期 patch/regularize，展示不重訓的提升（可與 SPIRIT 的 patching-defense 敘事呼應，但你的重點是“機制定位”而非 defense 本身）。 ([ACL Anthology][3])
  * **Data efficiency insight**：把你找到的 bottleneck/子空間視為 alignment 關鍵，連結到 speech-text alignment 挑戰（Soundwave 指出 representation gap 與 sequence length inconsistency，且用更少資料達到更好表現），主張你提供「為何對齊方法有效」的 mechanistic 解釋。 ([arXiv][11])

#### Ablations（讓 reviewer 沒話說）

* **Patching hyperparameters**：corruption 類型（noise vs substitution vs distractor）、metric（prob/logit-diff/KL）、patch 粒度（residual vs head output vs neuron）、window size（時間窗大小/步長）——並引用 ICLR’24 best practices 作為設計原則。 ([ICLR Proceedings][4])
* **Attribution vs exact patching**：展示 attribution 排名與精確 patching 的一致性（例如 top-50 的 overlap / rank correlation），把 attribution 定位為 *hypothesis generator*。 ([Neel Nanda][1])
* **Across models / across tasks / across languages**：至少跨 2 模型 + 2 任務；若做 speech translation 可自然跨語言。 ([arXiv][9])
* **Subspace method ablation**：PCA vs SAE；SAE expansion factor；layer 選擇（淺層 vs 深層）。可對照 AR&D 的設定與發現（深層更語意化、特徵較可解釋）。 ([arXiv][6])

#### Sanity checks（mechanistic paper 必備）

* **Random-pair negative control**：把不相干樣本的 activations patch 過來，應該不會系統性恢復正確答案。
* **Counterfactual directionality**：把「錯 transcript」的子空間 patch 過來，模型輸出應朝錯誤方向偏移（證明你的介入真在控制內容）。
* **Causal scrubbing**：在你聲稱“不重要”的子空間做 resample/ablate，行為不變；在你聲稱“重要”的子空間做介入，行為改變。 ([Lawrence Chan][8])
* **Judge sanity（若用 LLM-as-a-judge）**：AIR-Bench 用 GPT-4 評分且報告與人工一致性，但你仍應補一個小規模人工標註或多 judge 對照。 ([arXiv][10])

---

### 4) Main claim 與可被攻擊點（reviewer 可能質疑處）

**Main claim（建議寫得“可證偽”）**

> 在多個開源 Speech LLM 中，語音的 lexical content 主要透過 **audio–text connector 與 early LM layers 的緊緻、時間局部化子空間** 進入文字生成；對該子空間做 patching 具備 **sufficiency + necessity**，可在 speaker/noise/prosody 變化下轉移/恢復內容，而 paralinguistic cues 主要落在可分離子空間。 ([arXiv][7])

**Reviewer 可能攻擊點（你要主動寫在 Limitation / Discussion）**

1. **“Patching 很脆弱、結論依賴你怎麼 corrupt/選 metric”** ([ICLR Proceedings][4])
2. **“你只是在找相關性（probes/attention-style），不是真因果機制”**
3. **“Speech 的 patching 造成 distribution shift；你 patch 的 activation 不自然”**
4. **“跟 Beyond Transcription / AR&D / SPIRIT 相比，你的 novelty 在哪？”** ([arXiv][5])
5. **“只在單一模型/單一資料集有效，泛化性不足”**
6. **“Open-ended 評分不可靠（LLM judge bias）”** ([arXiv][10])
7. **“你說 ‘compact subspace’ 是不是事後挑出來的？top-K 怎麼訂？”**

---

### 5) 對每個質疑給 rebuttal strategy（逐條對應）

1. **Patching 脆弱 / 依賴設計**

   * 在主文就把 ICLR’24 best practices 當作 protocol：至少兩種 corruption、兩種 metric、matched random controls、報告敏感度分析；把所有自由度當作 ablation 章節，而不是藏在 appendix。 ([ICLR Proceedings][4])

2. **因果性不足**

   * 把證據層級寫清楚：

     * attribution patching 只用於 *search*（不當作 claim） ([Neel Nanda][1])
     * 最終 claim 只建立在 **雙向 patching（sufficiency/necessity）+ causal scrubbing** 上 ([Lawrence Chan][8])

3. **Distribution shift / 不自然 patching**

   * 兩招：

     * 用 **in-distribution minimal pairs（TTS + 真實噪音/干擾混音）** 取代純對抗性 corruption
     * 用 **subspace patching**（只 patch 你聲稱的內容子空間）降低“整段 residual 被硬換掉”的不自然性；並用 random subspace 對照證明不是單純注入能量。 ([arXiv][7])

4. **Novelty 被質疑（你只是把 patching 用到 speech）**

   * 明確對比：

     * Beyond Transcription：主要在 ASR / failure-mode 分析，你的貢獻是 **可擴展的因果定位 protocol + 跨條件內容轉移機制** ([arXiv][5])
     * AR&D：偏 feature discovery + naming/steering，你的貢獻是 **feature/子空間與“特定語言行為”的因果連結（token-level）** ([arXiv][6])
     * SPIRIT：把 patching 當 defense 介入，你的貢獻是 **找出哪些內部表徵是 jailbreak/robustness 的 bottleneck（機制解釋）** ([ACL Anthology][3])
     * 另外你採用 attribution patching 使大模型可行，這點在 speech setting 特別關鍵（序列長、search space 大）。 ([Neel Nanda][1])

5. **泛化性不足**

   * 最低配置：2 模型（Qwen2-Audio + SALMONN）× 2 任務（短答案指令 + ASR/translation）
   * 加分配置：再補一個 data-efficient 的新架構（Soundwave）或 speech-to-speech（LLaMA-Omni/Moshi）做 “sanity generalization”。 ([arXiv][9])

6. **評分不可靠（LLM judge bias）**

   * 優先用可自動評分任務（WER/EM/MCQ）。
   * 若必須 open-ended：沿用 AIR-Bench 的 judge 設計並加上（i）人工小樣本一致性（ii）多 judge / position bias 檢查。 ([arXiv][10])

7. **“compact subspace” 可能是 cherry-picking**

   * 事前規則化：top-K 的 K 用 validation set 決定；報告 saturation curve（K=1,2,5,10,20…）並與 matched random K 對照。這在 brain-to-speech 的 neuron saturation/子空間集中度敘事中很自然。 ([arXiv][7])

---

## 圖表建議（Figure 1~3 放什麼）

**Figure 1：Method overview + counterfactual setup（最重要的一張）**

* 左：Speech LLM 架構（audio encoder → connector/projector → LLM；標出可介入點：encoder layers、connector、early LM layers、cross-attention）。
* 中：minimal-pair 設計（clean vs corrupt：只變一個因素）與 TAP 三段式流程（attribution search → confirmatory patching → subspace/causal scrubbing）。
* 右：輸出（正確 token 的 logit diff 恢復、以及 layer×time causal map 的示意）。

**Figure 2：Layer×Time Causal Map（結果視覺化）**

* 熱力圖：x 軸 audio time windows、y 軸 layer（或 layer×module），顏色=patching effect（normalized logit diff 恢復率）。
* 疊加：top-K components 標註（例如某些 cross-attn heads / connector MLP）。
* 旁邊放 1–2 個例子：同一句話 speaker/noise 改變，bottleneck 的位置是否穩定。

**Figure 3：Subspace transfer + robustness payoff（把“可用性”釘死）**

* 左：content subspace patching（只 patch 子空間即可恢復 transcript/答案）vs random subspace（無效）
* 中：雙向性（necessity/sufficiency）與 saturation curve（K 越大恢復越好，但很快飽和 → “compact”）
* 右：應用：在 distractor/noise 或 jailbreak-style corruption 上，針對 identified bottleneck 的推論期介入帶來穩健性提升（不重訓）。

---

## 150-word abstract draft（英文，150 words）

Speech language models (SLMs) couple an audio encoder with a large language model to follow spoken instructions, but the internal mechanisms that map waveforms to linguistic tokens remain opaque. We propose Temporal Attribution Patching (TAP), a scalable causal tracing protocol that adapts activation patching to continuous audio by combining gradient-based attribution patching with confirmatory activation patching and causal scrubbing. Using a new suite of controlled minimal-pair utterances (phoneme swaps, speaker changes, prosody edits, and noise/distractor mixes), TAP produces layer–time mechanistic maps that localize where and when speech information becomes text. Across Qwen2-Audio, SALMONN, and Soundwave, we find that lexical content is mediated by compact, temporally localized subspaces at the audio–text connector and early LM layers; patching only these subspaces transfers transcript content across conditions while largely preserving paralinguistic attributes. The discovered sites predict failure modes and enable targeted, inference-time robustness improvements without retraining. We release code, datasets, and analysis artifacts.

[1]: https://www.neelnanda.io/mechanistic-interpretability/attribution-patching "https://www.neelnanda.io/mechanistic-interpretability/attribution-patching"
[2]: https://arxiv.org/abs/2310.13289 "https://arxiv.org/abs/2310.13289"
[3]: https://aclanthology.org/2025.emnlp-main.734.pdf "https://aclanthology.org/2025.emnlp-main.734.pdf"
[4]: https://proceedings.iclr.cc/paper_files/paper/2024/file/06a52a54c8ee03cd86771136bc91eb1f-Paper-Conference.pdf "https://proceedings.iclr.cc/paper_files/paper/2024/file/06a52a54c8ee03cd86771136bc91eb1f-Paper-Conference.pdf"
[5]: https://arxiv.org/pdf/2508.15882 "https://arxiv.org/pdf/2508.15882"
[6]: https://arxiv.org/html/2602.22253v1 "https://arxiv.org/html/2602.22253v1"
[7]: https://arxiv.org/html/2602.01247v1 "https://arxiv.org/html/2602.01247v1"
[8]: https://chanlawrence.me/publication/chan-2022-causal/ "https://chanlawrence.me/publication/chan-2022-causal/"
[9]: https://arxiv.org/abs/2407.10759 "https://arxiv.org/abs/2407.10759"
[10]: https://arxiv.org/abs/2402.07729 "https://arxiv.org/abs/2402.07729"
[11]: https://arxiv.org/abs/2502.12900 "https://arxiv.org/abs/2502.12900"
