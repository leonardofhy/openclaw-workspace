# Experiment Record Format

每筆實驗記錄是一個 JSON object，存在 `memory/experiments/experiments.jsonl`。

## 欄位定義

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| id | string | ✅ | `EXP-001` 格式，自動遞增 |
| name | string | ✅ | 人類可讀的實驗名稱 |
| task | string | ✅ | 實驗類別（如 layer-analysis, probing, sae-training, patching） |
| model | string | ✅ | 使用的模型（如 whisper-base, whisper-large-v3, qwen2-audio） |
| params | object | ❌ | 超參數 dict |
| command | string | ❌ | 完整可復現的指令 |
| machine | string | ✅ | 執行機器：`lab` / `mac` / `battleship` |
| status | string | ✅ | `queued` / `running` / `success` / `failed` / `cancelled` |
| created | string | ✅ | ISO 8601 建立時間 |
| started | string | ❌ | ISO 8601 開始時間 |
| completed | string | ❌ | ISO 8601 完成時間 |
| metrics | object | ❌ | 量化結果 dict（如 accuracy, loss, num_features） |
| summary | string | ❌ | 一句話結論（寫論文時可直接引用） |
| failed_reason | string | ❌ | 失敗原因（僅 status=failed 時填） |
| tags | list | ❌ | 標籤（如 ["audiomatters", "causal-audiolens", "exploratory"]） |
| parent_id | string | ❌ | 如果是基於某個實驗改的，記錄 parent |
| notes | string | ❌ | 自由備註 |

## 範例

```json
{
  "id": "EXP-001",
  "name": "Whisper-base hook demo",
  "task": "layer-analysis",
  "model": "whisper-base",
  "params": {"layers": 6, "method": "CKA"},
  "command": "python3 skills/autodidact/scripts/whisper_hook_demo.py",
  "machine": "mac",
  "status": "success",
  "created": "2026-02-26T20:30:00+08:00",
  "started": "2026-02-26T20:30:05+08:00",
  "completed": "2026-02-26T20:31:12+08:00",
  "metrics": {"clusters": 2, "transition_layer": 3, "norm_jump": 4.2},
  "summary": "Whisper-base has 6 layers; transition zone at layer 3 (4.2x norm jump); CKA confirms 2 distinct clusters (acoustic 0-2, semantic 3-5)",
  "tags": ["causal-audiolens", "toolchain-verification"],
  "parent_id": null,
  "notes": "First successful toolchain run. whisper-base has 6 layers not 12."
}
```

## Task 分類建議

| task | 說明 |
|------|------|
| layer-analysis | Logit lens, CKA, activation norms |
| probing | Linear probing, classifier probes |
| sae-training | Sparse Autoencoder training |
| patching | Activation patching, causal intervention |
| steering | Feature steering, inference-time intervention |
| safety | Adversarial attack, jailbreak detection |
| baseline | Baseline comparison experiments |
| ablation | Ablation studies |
| data-prep | Data collection, preprocessing |
