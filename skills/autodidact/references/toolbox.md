# 🧰 MI × Audio Toolbox

> 方法、工具、數據集速查。autodidact 做 learn/build 時參考。

## MI 方法（按因果嚴格度排序）

| 方法 | 能回答什麼 | Audio 特有陷阱 | 工具 |
|------|-----------|---------------|------|
| Linear probing | 某層是否「包含」某資訊 | ≠ 模型真的用了；time alignment 影響結論 | sklearn, custom |
| CKA / representation similarity | 資訊在哪裡轉化 | 對 pooling/time aggregation 敏感 | custom |
| Attribution (IG, TCAV) | 哪些輸入影響輸出 | spectrogram vs waveform 結果不同；長序列不穩定 | Captum |
| Activation patching | 哪些 components 因果上必要 | **audio corruption 設計難**（noise? gap? pitch shift?）；patch 可能造成 OOD 內部狀態 | TransformerLens, pyvene |
| SAE feature discovery | 潛在的 monosemantic features | features 可能是 dataset artifact；deadness/splitting；需多指標評估 | 自建 / AudioSAE code |
| Feature steering/erasure | 干預是否改變行為 | WER 等 metric 是 sequence-level，可能掩蓋局部效果 | SAE-based |
| Circuit tracing | 自動化的因果計算圖 | Audio 尚無成功案例；需先有穩定的 SAE features | Anthropic attribution graphs |

## Compute Tiers（每 tier 要產出 artifact，不只跑實驗）

| Tier | 硬體 | 能做什麼 | 應產出的 artifact |
|------|------|---------|------------------|
| 0 (CPU) | MacBook Air | probing, CKA, dataset prep, attribution | 可重複 notebook + activation cache (小規模) |
| 1 (1 GPU) | 戰艦 1x | activation extraction, 單層 SAE, pyvene patching | 可因果介入的小任務 + patching pipeline + steering demo |
| 2 (multi-GPU) | 戰艦 multi | 多層 SAE, audio-LLM end-to-end | 跨層 feature dictionary + evaluation harness |

## 核心工具

| 工具 | 用途 | 安裝 |
|------|------|------|
| TransformerLens | activation cache + patching | `pip install transformer-lens` |
| pyvene | structured interventions / interchange | `pip install pyvene` |
| Captum | input attribution (IG, etc.) | `pip install captum` |
| S3PRL | speech SSL encoder access | `pip install s3prl` |
| Neuronpedia | feature dashboard 瀏覽 | web: neuronpedia.org |
| SAEBench | SAE evaluation metrics | GitHub |
| AudioCraft | EnCodec + MusicGen/AudioGen | `pip install audiocraft` |

## 數據集速查

| Dataset | 大小 | 適合什麼 MI 實驗 |
|---------|------|-----------------|
| Speech Commands | 小，keyword | **最適合入門** — task 局部、metric 簡單、corruption 好設計 |
| ESC-50 | 小，50 class env sounds | 快速 debug interpretability methods |
| LibriSpeech | 1000h read speech | clean/corrupt patching, layerwise probing |
| FSD50K | 中，開放 AudioSet ontology | open-source 友好，feature visualization |
| Common Voice | 大，多語言 | cross-language/accent invariance |
| SUPERB | benchmark suite | 多任務「行為電池」驗證 mechanistic claims |

## Starter Experiments（漸進式）

1. **Layerwise probing map** — HuBERT 逐層 phonetic probe (CPU/Tier 0)
2. **CKA anatomy** — Wav2Vec2 的 acoustic→articulatory 資訊轉化 (CPU)
3. **Whisper neuron atlas** — max-activating clips + interactive notebook (Tier 0-1)
4. **Single-layer SAE on Whisper** — L1/TopK, feature interp + one steering demo (Tier 1)
5. **Intervention on Speech Commands** — pyvene interchange, minimal-pair audio (Tier 1)
6. **SAE evaluation discipline** — SAEBench-inspired multi-metric reporting (Tier 1)
