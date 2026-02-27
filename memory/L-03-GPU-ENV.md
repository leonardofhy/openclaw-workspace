# L-03: GPU 實驗環境 — 完成報告

**Status**: ✅ DONE  
**Date**: 2026-02-27  
**Deadline**: 2026-03-01

## 環境

- **機器**: Battleship（實驗室登入節點）
- **Cluster**: SLURM（s03/s04/s06 都有 GPU）
- **計算資源**: RTX 3090 (25.3GB VRAM)、RTX 6000 Ada、others
- **Package Manager**: Miniforge (Python 3.11)

## 已安裝

### Conda 環境
```
Name: interp
Location: ~/miniforge3/envs/interp
Python: 3.11
```

### Core Packages
- **torch** 2.10.0+cu128
- **transformer-lens** — mechanistic interpretability
- **pyvene** 0.1.8 — intervention and steering
- **s3prl** 0.4.18 — self-supervised speech representations
- **transformers** 4.57.6
- **datasets** 4.6.0
- **accelerate** 1.12.0
- **torchaudio**, **torchvision**, **scipy**, **pandas**, **matplotlib**, etc.

## 驗證

✅ CUDA available: True  
✅ GPU: NVIDIA GeForce RTX 3090  
✅ VRAM: 25.3 GB  
✅ transformer_lens: loads gpt2 on cuda  
✅ All packages importable  

## 使用方式

### 在 Login Node 激活環境
```bash
source ~/miniforge3/bin/activate
conda activate interp
```

### 在 Compute Node 運行 (推薦)
```bash
srun --gres=gpu:3090:1 --time=0-4 --mem=16G \
  ~/miniforge3/envs/interp/bin/python3 script.py
```

或使用 `run_gpu.sh` wrapper（需要 `hrun` 工具）

### 快速驗證
```bash
srun --gres=gpu:3090:1 --time=0-0:10:00 --mem=16G \
  ~/miniforge3/envs/interp/bin/python3 -c \
  'import torch; print(f"CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0)}")'
```

## Next Steps

1. **Lab bot access**: SSH key 配置讓 Lab bot 可以遠端執行
2. **Integration**: AudioMatters 項目可以用這個環境跑實驗
3. **Benchmarking**: Mechanistic interp 實驗在 RTX 3090 上的性能測試

## 注意

- `srun` 需要 SLURM 分配時間，預設 5 分鐘內的 job 秒級分配
- Conda 環境在 srun 中需要使用完整路徑 (`~/miniforge3/envs/interp/bin/python3`) 而非 `conda activate`
- GPU 記憶體 25.3GB 足以訓練小到中型 interpretability 實驗
