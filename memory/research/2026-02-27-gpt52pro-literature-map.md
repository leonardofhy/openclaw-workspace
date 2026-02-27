輸出格式：
- 先給 executive summary（10行內）
- 再給 markdown 表格（paper / method / causal level / reusable idea / gap）
- 最後列出 Top-5 最值得深讀與理由

以下是「**speech LLM（AudioLLM/SLM）mechanistic interpretability**」的**文獻地圖**（以 **2024/08–2026/02** 近 18 個月優先；少數經典方法 paper 回溯補齊）。  
我把範圍定義成：**以語音/音訊作為主要輸入或關鍵模態**（Whisper/HuBERT/codec + LLM 等），並且**主張或可支撐 mechanistic / causal-level 解釋**（例如 activation patching、causal tracing、可驗證的 feature steering、SAE feature ablation 等）。

---

## 主題分群（快速索引）

> 我先用「你指定的五個主題」分群列出 paper 編號；**每篇 paper 的完整卡片**在下一節（20 篇、每篇含核心貢獻/方法可轉用性/claim 類型/限制與 gap）。

### A) Causal intervention（因果介入/編輯/trace）
- #3 Brain-to-Speech MI（patching / scrubbing / decoding）
- #4 SonoEdit（pronunciation 的 knowledge editing + causal tracing）
- #13 MINT（fusion causal tracing）
- #14 Multi-Modal Causal Tracing（MULTIMODALCAUSALTRACE）
- #16 Object representation causal tracing（LVLM hallucination mitigation）
- #17 V-SEAM（semantic editing + attention modulating）
- #20 Transcoders（feature-level circuit、可做可驗證因果子圖）

### B) Patching（activation/path/back patching、steering）
- #8 SPIRIT（SLM jailbreak 的 post-hoc patching defense）
- #10 Music generation activation patching steering
- #11 Same Task, Different Circuits（back-patching）
- #12 Too Late to Recall（patching 證明兩跳失敗機制）
- #18 Patchscopes（patching 作為表示檢視框架）
- #19 Activation patching best practices（方法論）

### C) SAE（sparse autoencoder / dictionary learning / feature disentanglement）
- #1 AudioSAE（Whisper/HuBERT encoder 全層 SAE + steering）
- #2 AR&D（AudioLLM 的 SAE feature retrieval + auto-caption naming）
- #5 Group-sparse multimodal SAE（CLIP/CLAP 的 aligned dictionary）
- #9 Voice embedding SAE（聲紋/語者 embedding 的可解釋 feature）
- #20 Transcoders（與 SAE 同一脈絡：可解釋 feature + circuit）

### D) Modality grounding（模態特定機制、衝突處理、grounding/幻覺）
- #11 Same Task, Different Circuits
- #12 Too Late to Recall
- #14 Multi-Modal Causal Tracing
- #15 Conflicting vision vs text processing
- #16 Object representation causal tracing
- #17 V-SEAM

### E) Audio-text alignment（音訊-文字對齊/融合、bridge 設計與可解釋化）
- #5 Group-sparse multimodal SAE（含 CLAP）
- #6 Beyond Transcription（ASR 的 MI：聲學→語言映射）
- #7 PAL（audio token 如何進 LLM、哪裡注入最有效）
- #8 SPIRIT（speech 對齊與安全漏洞：patching 可修）
- #14 Multi-Modal Causal Tracing（把 vision 換成 audio 的可移植框架）

---

## 20 篇 paper cards（每篇：核心貢獻 / 方法可否轉用 speech LLM / behavior-only vs causal claim / 限制與 research gap）

> 標籤：**[Causal] [Patching] [SAE] [Grounding] [Alignment]**（一篇可多標籤）

---

### #1 AudioSAE: Towards Understanding of Audio-Processing Models with Sparse AutoEncoders  
**Year/Venue**：2026，arXiv preprint  
**arXiv**：2602.05027  
**Code**：GitHub `audiosae/audiosae_demo` citeturn19view0  
**Tags**：[SAE] [Causal] [Alignment]

- **一句核心貢獻**：在 Whisper 與 HuBERT 的 encoder 各層訓練 SAEs，系統化量化 audio feature 的穩定性/可解釋性，並用 feature-level 介入做出可驗證的行為改變（如減少 false speech detection）。citeturn19view0  
- **方法（可否轉用 speech LLM）**：  
  - SAE on activations（逐層、跨 seed 穩定性評估）、feature steering、concept erasure（移除部分 features 來抹除概念）。citeturn19view0  
  - **可轉用**：很高。直接套到「Whisper encoder + projector + LLM」或 codec encoder；也能把 SAE 放在 **adapter/LLM 前幾層**追蹤語意進入點。  
- **Claim 類型**：**causal claim**（有 feature 介入與效果量）。citeturn19view0  
- **限制 / 漏洞（research gap）**：  
  - 主要在 **audio encoder**（Whisper/HuBERT），對「audio → LLM reasoning → text/speech output」的全鏈路因果仍不夠。→ **Gap：把 SAE feature 與下游 LLM 行為（QA、對話、工具使用）做 causal linkage**。  
  - feature 命名/語意對齊仍偏「事件/聲學」；跨語言/跨口音與更抽象語用（情緒、諷刺、意圖）需要更強的對齊與評估。

---

### #2 AR&D: A Framework for Retrieving and Describing Concepts for Interpreting AudioLLMs  
**Year/Venue**：2026，ICASSP 2026（arXiv）  
**arXiv**：2602.22253  
**Code/Project**：arXiv 提供 project URL（未在 arXiv 直接標 GitHub）citeturn21view0turn20search7  
**Tags**：[SAE] [Causal] [Alignment]

- **一句核心貢獻**：提出（作者稱）首個面向 AudioLLM 的 mechanistic interpretability pipeline：用 SAE 把 polysemantic neuron 拆成 monosemantic features，並以「代表音訊檢索→自動描述命名→人類驗證→steering」閉環讓概念可用。citeturn21view0turn20search7  
- **方法（可否轉用 speech LLM）**：  
  - Stage1 SAE disentanglement；Stage2 找每個 feature 的代表音訊片段；Stage3 用自動 captioning 命名，再做人類評估與 steering 驗證。citeturn21view0  
  - **可轉用**：很高，特別適合你要做「speech LLM 的 feature naming / audit / controllability」。  
- **Claim 類型**：**causal claim**（以 steering/驗證形成可測介入）。citeturn21view0  
- **限制 / 漏洞（research gap）**：  
  - 概念命名依賴 captioning（可能偏向資料集與 captioner 的偏誤）。→ **Gap：用 text-side 或任務導向的對比驗證（例如最小對比對、counterfactual prompts）來提高命名信度**。  
  - 沒有直接解決「audio token ↔ text token」的對齊細粒度（phoneme/word/semantic frame）。→ **Gap：把 retrieval 單位從 audio clip 擴展到 time-aligned token span，結合 patching 做對齊因果測試**。

---

### #3 Mechanistic Interpretability of Brain-to-Speech Models: Investigating Alignment, Composition, and Decoding  
**Year/Venue**：2026，arXiv preprint  
**arXiv**：2602.01247  
**Code**：未在我蒐到的摘要頁面明示 citeturn11search23turn0search3  
**Tags**：[Causal] [Patching] [Alignment]

- **一句核心貢獻**：把 mechanistic interpretability（如 patching / causal tracing 類思路）帶到 brain-to-speech 生成模型，分析表示對齊、組合與解碼機制。citeturn11search23turn0search3  
- **方法（可否轉用 speech LLM）**：  
  - 以「可介入」的方式定位對齊與解碼資訊流（常見會用 activation patching / tracing / scrubbing 類工具）。citeturn11search23  
  - **可轉用**：中到高。雖然 domain 是 neural data→speech，但核心是「連續訊號 encoder → 生成 decoder」的因果分析，與 speech LLM 架構相近。  
- **Claim 類型**：**causal claim**（以介入式 MI 為主張）。citeturn11search23  
- **限制 / 漏洞（research gap）**：  
  - brain-to-speech 的訊號與一般語音不同；方法遷移到「自然語音→LLM」需要重新處理 tokenization / alignment。  
  - **Gap：把這類 alignment/composition 的因果分析用在 speech LLM 的「語音語用（prosody）→意圖/語氣→回覆策略」**，目前幾乎沒人做。

---

### #4 SonoEdit: Null-Space Constrained Knowledge Editing for Pronunciation Correction in LLM-Based TTS  
**Year/Venue**：2026，arXiv preprint  
**arXiv**：2601.17086  
**Code**：未在我蒐到的 arXiv 摘要頁面明示 citeturn21view3turn2search0  
**Tags**：[Causal] [Patching] [Alignment]

- **一句核心貢獻**：針對 LLM-based TTS 的**特定發音錯誤**，提出「null-space constrained」的 knowledge editing，力求只改發音、不破壞其他語言能力。citeturn2search0turn21view3  
- **方法（可否轉用 speech LLM）**：  
  - 把「知識編輯/模型編輯」搬到 pronunciation correction；（資料提到）搭配 acoustic causal tracing 來找可編輯的內部子空間/位置。citeturn2search0  
  - **可轉用**：高。speech LLM/語音 agent 常見需求是「專有名詞/外來語/人名」修正；此類方法可作為 **可控、局部的語音行為編輯**。  
- **Claim 類型**：**causal claim**（模型參數/表示的編輯屬介入）。citeturn2search0  
- **限制 / 漏洞（research gap）**：  
  - 聚焦在發音；對更高層語用（情緒、禮貌、語速、韻律）尚未系統化。→ **Gap：把 null-space editing 擴到 prosody control，並建立可驗證的 causal eval**。  
  - 需要更通用的「定位目標行為的內部座標系」；否則每個錯誤要重新 tracing。

---

### #5 Decomposing Multimodal Embedding Spaces with Group-Sparse Autoencoders  
**Year/Venue**：2026，ICLR 2026 Poster（亦有 arXiv 版本）  
**arXiv**：2601.20028  
**Code**：未在我蒐到的頁面明示 citeturn16search1turn13view0  
**Tags**：[SAE] [Alignment] [Causal]

- **一句核心貢獻**：針對多模態 embedding 用 SAE 時常出現的 **split dictionary（feature 只對單一模態活化）**問題，提出 cross-modal random masking + group-sparse regularization，學到更「跨模態對齊」的字典，並在 CLIP（image/text）與 CLAP（audio/text）驗證。citeturn16search1turn13view0  
- **方法（可否轉用 speech LLM）**：  
  - 對齊 embedding space 的 SAE 訓練改造（paired samples 的 group sparsity + shared mask）；定義多模態 monosemanticity/對齊度量；用 sparse code 介入做控制示例。citeturn16search1turn14view0  
  - **可轉用**：很高，尤其對你想做的 **audio-text alignment 的 mechanistic feature space**（例如：把 speech encoder 輸出/adapter 輸出當成 joint embedding）。  
- **Claim 類型**：偏 **causal claim**（至少在表示層可做介入/控制；且提出理論論證）。citeturn16search1  
- **限制 / 漏洞（research gap）**：  
  - 工作在「embedding space」層級；對 end-to-end speech LLM 的 token-level fusion、attention routing 的因果仍未覆蓋。→ **Gap：把 group-sparse SAE 擴到 transformer 中間層（residual stream）並做 patching 驗證**。  
  - 需要更強的語義標註/概念命名流程，避免「看似對齊但其實只是 dataset bias」。

---

### #6 Beyond Transcription: Mechanistic Interpretability in ASR  
**Year/Venue**：2025（arXiv），（作者註記）AAAI 2026 citeturn1search5turn21view2  
**arXiv**：2508.15882  
**Code**：未在我蒐到的摘要頁面明示 citeturn21view2turn1search5  
**Tags**：[Alignment] [Patching]（偏方法整合）

- **一句核心貢獻**：把 mechanistic interpretability 的常用工具（在 ASR/語音模型上）系統化整理/移植，讓「不只看轉寫結果」而能分析 ASR 內部如何形成字詞。citeturn1search5turn21view2  
- **方法（可否轉用 speech LLM）**：  
  - 典型會包含：logit-lens 類分析、attention/representation probing、（可能）activation patching 等，用於定位 phonetic → lexical → semantic 的層次。citeturn1search5  
  - **可轉用**：中到高。若你的 speech LLM 前段包含 ASR/Whisper encoder，這篇提供「怎麼把 LLM 的 MI 工具移到語音」的模板。  
- **Claim 類型**：偏 **behavior-only + 部分 causal**（取決於其案例是否做 patching/ablation；就題目與定位而言，通常是方法論/分析導向）。citeturn1search5  
- **限制 / 漏洞（research gap）**：  
  - 多數 ASR MI 偏向「音素/字詞」層；speech LLM 的核心挑戰常在「語用/對話策略/指令遵循」。→ **Gap：把 ASR MI 連到 LLM decision layer（例如 refusal、tool-use、safety）**。  

---

### #7 PAL: Probing Audio Encoders via LLMs — Audio Information Transfer into LLMs  
**Year/Venue**：2025（arXiv；v3 更新到 2026/02）  
**arXiv**：2506.10423  
**Code**：未在 arXiv 摘要頁面標示 citeturn21view1  
**Tags**：[Alignment] [Grounding]

- **一句核心貢獻**：系統比較「audio encoder token 如何餵進 LLM」：提出只在注意力機制注入 audio 的 LAL，以及混合式 PAL，用更低成本達到與傳統 prepend/projector 類方法相近或更好表現。citeturn21view1  
- **方法（可否轉用 speech LLM）**：  
  - PLITS（prepend 到 LLM token space）vs LAL（只透過 attention 在選定層注入，避開 FFN）vs PAL（summary tokens 用 PLITS，其餘用 LAL）。citeturn21view1  
  - **可轉用**：高（作為你做 MI 的「介入把手」）。LAL/PAL 把「音訊資訊進入 LLM 的位置」變得可控，利於後續做 patching/causal tracing。  
- **Claim 類型**：**偏 causal（架構介入/ablation）**，但不是傳統 MI（它更像 integration 設計 + 以效能指標驗證）。citeturn21view1  
- **限制 / 漏洞（research gap）**：  
  - 主要用任務表現衡量「哪些層注入好」；缺少「注入後形成哪些內部表徵/回路」的 mechanistic 證據。→ **Gap：結合 activation patching + SAE，在 PAL 的注入層做 feature-level tracing**。  

---

### #8 SPIRIT: Patching Speech Language Models against Jailbreak Attacks  
**Year/Venue**：2025，EMNLP 2025 Main（arXiv） citeturn20search22turn20search25  
**arXiv**：2505.13541  
**Code**：未在 arXiv 摘要頁面標示 citeturn20search6turn20search10  
**Tags**：[Patching] [Causal] [Alignment]

- **一句核心貢獻**：指出 SLM（speech instruction）比 text LLM 更易被 jailbreak，並提出**推理時 post-hoc activation patching 防禦**，在不重訓的情況下大幅提升魯棒性、且維持效用。citeturn20search6turn20search10  
- **方法（可否轉用 speech LLM）**：  
  - 在 inference 時對特定層/元件 activations 做 patching/修補；大量 ablation 尋找效用-安全權衡。citeturn20search6  
  - **可轉用**：很高。你若研究「speech LLM 的 safety/拒答/越獄」的機制，這篇提供一個非常實用的因果介入範例。  
- **Claim 類型**：**causal claim**（直接介入 activations 並測量攻擊成功率變化）。citeturn20search6  
- **限制 / 漏洞（research gap）**：  
  - 偏防禦導向：patching 找到「有效位置」≠ 解釋「為何該位置代表某個語義/意圖」。→ **Gap：用 SAE/feature attribution 把 patching 位置對應到可解釋概念（例如：惡意意圖、隱蔽指令、prosody cue）**。  
  - 主要針對 jailbreak；對一般能力（ASR、QA、對話策略）機制的正向解釋仍不足。

---

### #9 Sparse Autoencoder Insights on Voice Embeddings  
**Year/Venue**：2025，arXiv preprint  
**arXiv**：2502.00127  
**Code**：未在我蒐到的摘要頁面明示 citeturn7search1  
**Tags**：[SAE] [Alignment]

- **一句核心貢獻**：用 SAE 解構 voice/speaker embeddings，提取更可解釋的聲紋因素（可能含身份、音色、錄音條件等）。citeturn7search1  
- **方法（可否轉用 speech LLM）**：  
  - SAE on embedding space + feature interpretation（常見會搭配概念標註、檢索例子、或簡單介入）。citeturn7search1  
  - **可轉用**：中。若你的 speech LLM 涉及「說話者身份」或「隱私去識別」，這類 feature 拆解可當作前置模組或分析工具。  
- **Claim 類型**：我會保守標 **behavior-only 為主**（除非全文有做 feature-level steering/ablation；僅從摘要資訊不足以確定）。citeturn7search1  
- **限制 / 漏洞（research gap）**：  
  - voice embedding 的可解釋 feature 不等於 speech LLM 的「語意/推理」feature。→ **Gap：把 speaker/content 的 disentanglement 接到 AudioLLM 的 instruction-following 行為，驗證哪些 speaker features 會干擾語意或 safety**。

---

### #10 Activation Patching for Interpretable Steering in Music Generation  
**Year/Venue**：2025，arXiv preprint  
**arXiv**：2504.04479  
**Code**：未在 arXiv 摘要頁面標示 citeturn17view0  
**Tags**：[Patching] [Causal]

- **一句核心貢獻**：在大型 audio 生成模型上，首次系統研究「latent direction vectors」並用 activation injection 連續控制音樂屬性（tempo、timbre）。citeturn17view0  
- **方法（可否轉用 speech LLM）**：  
  - difference-in-means 求 steering vector；在不同層注入 residual 方向；比較注入策略與層敏感性。citeturn17view0  
  - **可轉用**：中。雖是音樂生成，但「方向向量 + 層級注入」可遷移到 **TTS prosody** 或 speech style 控制；也可做為 speech LLM 的可控生成介入。  
- **Claim 類型**：**causal claim**（以注入介入造成可預期輸出改變）。citeturn17view0  
- **限制 / 漏洞（research gap）**：  
  - binary 概念（快/慢、亮/暗）相對容易；speech 的語用屬性（諷刺、情緒、禮貌）更複雜。→ **Gap：把 steering vector 與可解釋 feature（SAE/字典）結合，讓方向更「語意可驗證」**。  

---

### #11 Same Task, Different Circuits: Disentangling Modality-Specific Mechanisms in Vision-Language Models  
**Year/Venue**：2025（arXiv；NeurIPS 2025）  
**arXiv**：2506.09047  
**Code**：GitHub `technion-cs-nlp/vlm-circuits-analysis` citeturn10view0  
**Tags**：[Grounding] [Patching] [Causal] [Alignment]

- **一句核心貢獻**：證明 VLM 在「看起來同一個任務」下，其實依賴**模態特定、彼此分離的 circuits**；並用 back-patching 類介入方法把 cross-modal 表現補回來。citeturn10view0  
- **方法（可否轉用 speech LLM）**：  
  - circuit 分析 +（back-）patching / ablation 來驗證「哪條路徑在處理哪個模態」。citeturn10view0  
  - **可轉用**：很高。把 image token 換成 audio token，你會面對同樣問題：**模型是否真的把語音語意融合進 LLM，或只是走了捷徑（例如 prompt bias / ASR text shortcut）**。  
- **Claim 類型**：**causal claim**（以介入驗證 circuits）。citeturn10view0  
- **限制 / 漏洞（research gap）**：  
  - 域在 vision-language；speech 的時間結構與 token 對齊更難。→ **Gap：發展 time-aligned patching（跨 frame/token）或用 attention map 導引的 patching**。  

---

### #12 Too Late to Recall: Explaining the Two-Hop Problem in Multimodal Knowledge Retrieval  
**Year/Venue**：NeurIPS 2025  
**OpenReview/PDF**：OpenReview PDF（NeurIPS 2025）  
**Code**：GitHub `cvenhoff/vlm-two-hop` citeturn9view0  
**Tags**：[Grounding] [Patching] [Causal] [Alignment]

- **一句核心貢獻**：用 mechanistic 分析指出 VLM 的「兩跳 retrieval」常失敗，是因為模型**太晚才辨識出關鍵實體**，導致檢索階段抓不到正確知識；並提出修補策略。citeturn9view0  
- **方法（可否轉用 speech LLM）**：  
  - activation patching/causal tracing 式驗證：把「早期正確實體表示」補回去，看 retrieval 是否恢復。citeturn9view0  
  - **可轉用**：高。speech LLM 做 spoken QA / agentic retrieval 時，也會遇到「**ASR/語音理解晚到**」造成檢索錯誤。  
- **Claim 類型**：**causal claim**。citeturn9view0  
- **限制 / 漏洞（research gap）**：  
  - 主要談 vision；speech 會多一層「語音→詞」的不確定性。→ **Gap：把“too late to recall”機制改寫成“too late to transcribe/segment/ground”**，並建立對應基準集（speech constraints / spoken entity grounding）。  

---

### #13 MINT: Causally Tracing Information Fusion  
**Year/Venue**：ICLR 2026 submission（OpenReview）  
**OpenReview/PDF**：OpenReview PDF citeturn8view0  
**Code**：未在我蒐到的頁面明示 citeturn8view0  
**Tags**：[Causal] [Grounding] [Alignment]

- **一句核心貢獻**：把「資訊融合（fusion）」視為可被因果追蹤的過程，提出 MINT 框架去定位多模態訊息在 transformer 中何時、如何融合並影響輸出。citeturn8view0  
- **方法（可否轉用 speech LLM）**：  
  - causal tracing / layer-wise intervention 去找 fusion band（常見是某些層開始 cross-modal influence 變強）。citeturn8view0  
  - **可轉用**：很高。speech LLM 的關鍵問題正是：**語音資訊在哪些層進入語言推理**、是否被 prompt shortcut 覆蓋。  
- **Claim 類型**：**causal claim**（以 tracing/intervention 為核心）。citeturn8view0  
- **限制 / 漏洞（research gap）**：  
  - 多半先在 vision-language 驗證；speech 的 token 對齊更困難。→ **Gap：建立 audio-text 的“fusion tracing”基準與可重現介入 protocol**（例如：同一句話改 prosody、同一段音訊加干擾，觀察 fusion band 是否移動）。  

---

### #14 Understanding Information Storage and Transfer in Multi-Modal LLMs with Multi-Modal Causal Tracing  
**Year/Venue**：NeurIPS 2024（亦有 arXiv）  
**arXiv**：2406.04236  
**PDF**：NeurIPS proceedings PDF citeturn20search5turn20search1  
**Code**：未在我蒐到的摘要/論文片段明示 citeturn20search1turn20search5  
**Tags**：[Causal] [Grounding] [Alignment]

- **一句核心貢獻**：提出 **MULTIMODALCAUSALTRACE** 與 constraint-based 分析框架，研究 MLLM 中圖像與文字資訊如何在層間儲存與傳遞，並提供對應資料集/分析。citeturn20search5turn20search1  
- **方法（可否轉用 speech LLM）**：  
  - multi-modal causal tracing（把某模態訊息污染/替換，再逐層 patch 回去測因果恢復）。citeturn20search5  
  - **可轉用**：很高。把 image token 換成 audio token，你就得到「speech→LLM」的 causal trace 工具箱。  
- **Claim 類型**：**causal claim**。citeturn20search5  
- **限制 / 漏洞（research gap）**：  
  - 工具對 speech 的最大障礙是「時間對齊」：音訊 corruption/patching 要怎麼選 span 才可比對。→ **Gap：發展 speech-specific corruption 與 alignment-aware patching（例如 DTW、CTC 對齊、attention 對齊）**。  

---

### #15 How Do Vision-Language Models Process Conflicting Visual and Textual Information?  
**Year/Venue**：2025，arXiv preprint  
**arXiv**：2507.01790  
**Code**：未在我蒐到的摘要頁面明示 citeturn1search0  
**Tags**：[Grounding] [Alignment]

- **一句核心貢獻**：研究 VLM 面對「視覺與文字互相矛盾」時，內部如何決定信任哪個模態與如何整合衝突訊息。citeturn1search0  
- **方法（可否轉用 speech LLM）**：  
  - 通常會做 head/layer 分析與對衝突輸入的系統化實驗（可能搭配 ablation/patching）。citeturn1search0  
  - **可轉用**：高。speech LLM 常見衝突是「語音內容 vs prosody/語氣」或「語音 vs 系統 prompt」。  
- **Claim 類型**：我會標 **偏 behavior-only + 可能含局部因果**（僅從摘要片段不足以確認其介入強度）。citeturn1search0  
- **限制 / 漏洞（research gap）**：  
  - 多數衝突研究先在 vision/text；speech 的衝突可更細（語速、重音、情緒）。→ **Gap：構造 speech-specific conflict suites（語意不變、prosody 變；或反之）並做因果頭/層定位**。

---

### #16 Causal Tracing of Object Representations in Large Vision-Language Models: Mechanistic Interpretability and Hallucination Mitigation  
**Year/Venue**：2025，arXiv preprint  
**arXiv**：2511.05923  
**Code**：未在我蒐到的摘要頁面明示 citeturn1search2  
**Tags**：[Causal] [Grounding]

- **一句核心貢獻**：用 causal tracing 追蹤 LVLM 中「物體表示」如何形成並導致幻覺，並提出減緩 hallucination 的介入策略。citeturn1search2  
- **方法（可否轉用 speech LLM）**：  
  - object representation 的 causal tracing（定位哪些層/元件承載關鍵表示），再做介入降低幻覺。citeturn1search2  
  - **可轉用**：中到高。把 object 換成「語音中的實體（人名、地名、數字）」或「語音事件（笑、哭、嘆氣）」即可。  
- **Claim 類型**：**causal claim**。citeturn1search2  
- **限制 / 漏洞（research gap）**：  
  - 幻覺在 speech LLM 可能來源更多（ASR 誤聽、prosody 誤解、retrieval 失敗）。→ **Gap：建立 speech hallucination 的因果分類（ASR-driven vs reasoning-driven vs retrieval-driven）並對應 tracing 方法**。

---

### #17 V-SEAM: Visual Semantic Editing and Attention Modulating for Large Vision-Language Models  
**Year/Venue**：2025，EMNLP 2025（arXiv）  
**arXiv**：2509.14837  
**Code**：未在我蒐到的摘要頁面明示 citeturn1search4  
**Tags**：[Causal] [Grounding] [Patching]

- **一句核心貢獻**：提出對 LVLM 的「語義/注意力」做可控編輯（semantic editing + attention modulating），以修正錯誤/減少幻覺。citeturn1search4  
- **方法（可否轉用 speech LLM）**：  
  - 介入注意力或語義表示以改變輸出；屬可操作的內部編輯手段。citeturn1search4  
  - **可轉用**：中。speech LLM 若有 cross-attn（audio→text）或 adapter-attn，可類比做「語音關鍵片段權重調整」以矯正理解。  
- **Claim 類型**：**causal claim**。citeturn1search4  
- **限制 / 漏洞（research gap）**：  
  - 編輯方法若缺少機制保證，可能引入副作用。→ **Gap：在 speech LLM 上加入“minimality/orthogonality”約束（類 SonoEdit）並用 patching 驗證副作用邊界**。

---

### #18 Patchscopes: A Unifying Framework for Inspecting Hidden Representations of Language Models  
**Year/Venue**：2024，arXiv（常見引用為 ICML 2024）  
**arXiv**：2401.06102  
**Code**：未在我蒐到的摘要片段明示 citeturn11search0  
**Tags**：[Patching] [Causal]

- **一句核心貢獻**：把「patching hidden states」提升成通用框架，用於**檢視/解碼中間表示**（不只是找 circuit，也能問“這層到底表示了什麼”）。citeturn11search0  
- **方法（可否轉用 speech LLM）**：  
  - 核心是：把某層表示 patch 到可讀出的環境（或 proxy head）去觀察可解碼資訊。citeturn11search0  
  - **可轉用**：很高。speech LLM 最缺的常是「audio encoder/adapter 的表示到底 encode 了哪些語意」；Patchscopes 提供可重現的檢視 protocol。  
- **Claim 類型**：**causal claim**（patching 介入）。citeturn11search0  
- **限制 / 漏洞（research gap）**：  
  - speech 的 token 對齊與可讀出 head 設計更難。→ **Gap：設計 speech-native 的 probe/decoder（phoneme head、prosody head、intent head）來配合 patchscope**。

---

### #19 Towards Best Practices of Activation Patching in Language Models: Metrics and Methods  
**Year/Venue**：ICLR 2024（arXiv 版本較早）  
**arXiv**：2309.16042  
**Code**：未在我蒐到的 PDF 摘要片段明示 citeturn11search20  
**Tags**：[Patching] [Causal]

- **一句核心貢獻**：系統整理 activation patching 的**度量與方法陷阱**，提供更可靠的 patching 實作與解讀方式（避免錯把 artifact 當機制）。citeturn11search20  
- **方法（可否轉用 speech LLM）**：  
  - 定義 patching 指標、比較不同 patching 設定、提出較穩健 protocol。citeturn11search20  
  - **可轉用**：非常高。speech LLM 更容易出現「對齊不良導致 patching 假象」，這篇是你做任何 speech patching 前的必讀。  
- **Claim 類型**：**causal claim（方法論）**。citeturn11search20  
- **限制 / 漏洞（research gap）**：  
  - 主要以 text LM 為背景。→ **Gap：建立 speech patching 的最佳實務（time alignment、CTC/attention 對齊、跨模態 token mapping、噪聲魯棒性）**。

---

### #20 Transcoders Find Interpretable LLM Feature Circuits  
**Year/Venue**：NeurIPS 2024（亦有 arXiv）  
**arXiv**：2406.11944  
**Code**：GitHub `jacobdunefsky/transcoder_circuits` citeturn20search4turn20search14  
**Tags**：[SAE] [Causal]

- **一句核心貢獻**：用「transcoder」把難以做 circuit 分析的 MLP 子層替換成更寬、稀疏可解釋的 proxy，讓 feature-level circuit analysis 能穿越 MLP 非線性並得到更可讀的子圖。citeturn20search4turn20search14  
- **方法（可否轉用 speech LLM）**：  
  - 訓練 transcoder 近似 MLP；以權重與 feature 互動建構 circuit；並在 GPT2-small 的 greater-than circuit 做 reverse-engineering。citeturn20search4  
  - **可轉用**：高。speech LLM 常卡在「audio adapter/MLP block」難解；transcoder 提供一條把 MLP 變得可分析的路。  
- **Claim 類型**：**causal claim**（以 proxy + circuit 驗證為主）。citeturn20search4  
- **限制 / 漏洞（research gap）**：  
  - 多在 text LM 驗證。→ **Gap：把 transcoder/feature-circuit 帶到“audio→text projector/adapter”與“cross-modal MLP”**，檢驗是否能找出「語音語意進入 LLM 的關鍵 feature」並做可控介入。

---

## 你可以直接拿來開題的「共通 research gaps」（跨上述 20 篇的交集）

1. **Speech token 對齊是所有 causal MI 的硬點**  
   vision token 還能靠位置；speech 有時間軸、速率變動、噪聲與韻律。→ 你若能提出一套「alignment-aware patching / causal tracing」標準流程（例如結合 CTC/attention 對齊或 DTW），會非常有貢獻。（對應 #11/#12/#14/#19）

2. **把 SAE feature 與 end-to-end speech LLM 行為連起來**  
   目前多停在 encoder（#1/#2）或 embedding（#5/#9）；但 speech LLM 的價值在「理解→推理→對話/工具/安全」。→ 做「feature→circuit→behavior」閉環（SAE + patching + behavior eval）會是漂亮的 gap。

3. **Audio-text alignment 的“可解釋共同字典”仍稀缺**  
   #5 是很好的起點（還直接做 CLAP）；你可把它擴到「speech encoder output ↔ text hidden state」或「adapter residual stream」的 joint dictionary，並用 #12/#14 的 tracing 方式做因果驗證。

4. **Safety / jailbreak 的 mechanistic 解釋仍不足**  
   #8 證明 patching 可防；但“被 patch 掉的到底是什麼概念/路徑”還不清楚。→ 結合 #2 的自動概念命名、#1 的 feature steering、#20 的 feature-circuit，是很自然的研究路線。

---

如果你接下來要把這份地圖變成「可實作的研究計畫」，我也可以把這 20 篇再整理成：  
- 一個 **speech LLM MI pipeline**（從選模型、抽 activation、alignment、SAE 訓練、patching 設計、到 causal eval 指標），  
- 以及 2–3 個可投稿的具體題目（含最小可行實驗與資料需求）。