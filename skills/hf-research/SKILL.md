---
name: hf-research
description: >
  Hugging Face research operations — upload, download, search, fine-tune, and track HF Hub assets.
  Use when (1) uploading a model checkpoint or dataset to HF Hub, (2) searching or downloading
  models/datasets from HF Hub, (3) launching fine-tuning jobs via HF Jobs, (4) checking status of
  an HF model/Space, (5) pushing experiment results to HF after training, (6) Leo says "推上去 HF",
  "從 HF 下載", "跑 fine-tuning", "HF Hub 上傳", "HF 狀態", "把結果推到 hub".
  NOT for: general experiment tracking (use experiment-manager), reading papers (use paper-tracker),
  or non-HF cloud storage.
---

# HF Research

Unified interface for Hugging Face Hub operations. Wraps three installed plugins:
- **hf-cli** — Hub uploads/downloads (the `hf` CLI)
- **hugging-face-model-trainer** — TRL fine-tuning via HF Jobs
- **hugging-face-datasets** — Dataset creation and management

All push/pull operations are logged to `memory/hf-research/pushes.jsonl` and can be linked
to experiment-manager entries via `EXP-ID`.

## Quick Start

```bash
# Upload model checkpoint to HF Hub
python3 skills/hf-research/scripts/hf_research.py upload \
  --repo myuser/whisper-finetuned \
  --path ./outputs/checkpoint-1000 \
  --commit-msg "checkpoint after 1k steps" \
  --exp EXP-007

# Search for models
python3 skills/hf-research/scripts/hf_research.py search "whisper speech" --type model --limit 5

# Search for datasets
python3 skills/hf-research/scripts/hf_research.py search "librispeech" --type dataset --limit 5

# Download a model
python3 skills/hf-research/scripts/hf_research.py download \
  --repo openai/whisper-base \
  --out ./models/whisper-base

# Download a dataset
python3 skills/hf-research/scripts/hf_research.py download \
  --repo mozilla-foundation/common_voice_13_0 \
  --type dataset \
  --out ./data/cv13

# Check model/space status
python3 skills/hf-research/scripts/hf_research.py status openai/whisper-base
python3 skills/hf-research/scripts/hf_research.py status username/my-demo --type space

# Push experiment result to HF (links EXP entry + uploads checkpoint)
python3 skills/hf-research/scripts/hf_research.py push-exp EXP-007 \
  --repo myuser/whisper-finetuned \
  --checkpoint ./outputs/checkpoint-1000 \
  --note "best checkpoint, WER 8.3%"

# View push history
python3 skills/hf-research/scripts/hf_research.py log
python3 skills/hf-research/scripts/hf_research.py log --exp EXP-007
python3 skills/hf-research/scripts/hf_research.py log --limit 5
```

## Fine-Tuning via HF Jobs

Fine-tuning is handled by the **hugging-face-model-trainer** skill. Use this skill to prepare
the context, then hand off to the trainer:

1. Register the experiment in experiment-manager first:
   ```bash
   python3 skills/experiment-manager/scripts/exp_tracker.py add \
     --name "whisper-base SFT on CV13" --task "sft" --model "whisper-base" --machine battleship \
     --command "hf job run train.py" --tags hf-jobs,asr
   ```

2. Launch training (use hugging-face-model-trainer skill for the UV script):
   ```
   /hugging-face-model-trainer: SFT on openai/whisper-base using common_voice_13_0 dataset
   ```

3. After training completes, push the best checkpoint:
   ```bash
   python3 skills/hf-research/scripts/hf_research.py push-exp EXP-001 \
     --repo myuser/whisper-cv13-sft \
     --checkpoint ./outputs/best \
     --note "final model after SFT"
   ```

## Dataset Operations

For creating and managing HF datasets, use the **hugging-face-datasets** skill:
```
/hugging-face-datasets: initialize a new dataset repo myuser/my-asr-dataset
```

For downloading existing datasets, use this skill's `download` command with `--type dataset`.

## Data Storage

- **Push log**: `memory/hf-research/pushes.jsonl` (append-only, one JSON per line)
- **ID format**: `HFP-001`, `HFP-002`... (auto-increment)
- **Each record contains**: id, repo, type, local_path, commit_msg, exp_id, note, pushed_at

## Usage Scenarios

### After a training run
1. `exp_tracker.py result EXP-xxx --status success --metrics '{"wer": 8.3}'` — record results
2. `hf_research.py push-exp EXP-xxx --repo user/model --checkpoint ./best` — upload + link
3. `hf_research.py status user/model` — verify the model is live on Hub

### Before starting a new fine-tune
1. `hf_research.py search "whisper base" --type model` — find base models
2. `hf_research.py download --repo openai/whisper-base --out ./models/` — pull locally
3. Register experiment → launch via hugging-face-model-trainer

### Dataset preparation
1. `hf_research.py search "common voice zh" --type dataset` — find suitable datasets
2. `hf_research.py download --repo mozilla-foundation/common_voice_13_0 --type dataset` — pull
3. Use hugging-face-datasets skill to create a custom dataset repo

## Integration with Other Skills

- **experiment-manager**: `push-exp` reads EXP records and writes back `hf_repo` field; always
  register an experiment before pushing so results stay linked
- **hugging-face-model-trainer**: handles TRL training scripts and HF Jobs submission; use this
  skill for pre/post-training Hub operations
- **hugging-face-datasets**: handles dataset repo creation and row streaming; use this skill to
  download existing datasets
- **paper-tracker**: after pushing a model, note the HF repo URL in the related paper entry
