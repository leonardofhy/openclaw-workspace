# AudioMatters Toolkit — Complete Research Pipeline

Everything you need to run AudioMatters experiments and generate Method section results.

## Quick Start

```bash
# On Battleship login node
cd ~/Workspace/little-leo

# Run evaluation experiment
TIME=0-0:10:00 CPU=4 MEM=16 GPU=3090 ./run_gpu_interp.sh am_whisper_eval \
  'python3 am_eval.py --model whisper-base --dataset common-voice --task asr --output results/'

# Check results
cat logs/am_whisper_eval_*.log
cat results/*/summary.json
```

## Components

### 1. **research_logger.py** — Experiment Tracking
Auto-logs metrics with config, summaries, and statistics.

```python
from research_logger import ExperimentLogger

logger = ExperimentLogger("my_exp", model="gpt2", seed=42)
logger.log_scalar("loss", 0.5, step=0)
logger.log_dict({"acc": 0.9, "f1": 0.85})
logger.save()
```

Outputs:
- `config.json` — full config
- `metrics.jsonl` — step-by-step metrics
- `summary.json` — min/max/mean stats
- `experiment.log` — text log

### 2. **am_experiment_template.py** — Base Experiment
Template for any AudioMatters experiment. Handles:
- GPU setup and logging
- Model loading (transformer-lens)
- Config/results auto-save

### 3. **am_eval.py** — AudioMatters Evaluation Pipeline
Full evaluation for speech models (Whisper, S3PRL).

```bash
python3 am_eval.py \
  --model whisper-base \
  --dataset common-voice \
  --task asr \
  --output results/
```

Supports tasks: `asr`, `speaker_id`, `emotion`

### 4. **Compute Workflow Scripts**
Run on cluster via SLURM.

#### CPU Job
```bash
./run_cpu.sh job_name "python3 script.py"
TIME=0-0:05:00 CPU=8 MEM=32 ./run_cpu.sh big_job "..."
```

#### GPU Job (system Python)
```bash
./run_gpu.sh job_name "python3 script.py"
GPU=RTX6000Ada GPU_COUNT=2 ./run_gpu.sh big_gpu_job "..."
```

#### GPU Job (with interp env)
**Recommended for AudioMatters!**
```bash
./run_gpu_interp.sh am_job "python3 am_eval.py ..."
```

Includes:
- PyTorch 2.10 + CUDA 12.8
- transformer-lens
- pyvene (intervention)
- s3prl (speech representations)
- transformers, datasets, accelerate

### 5. **GPU Environment** (Conda)
Pre-installed `interp` environment on Battleship.

```bash
# Manual activation (for development)
source ~/miniforge3/bin/activate && conda activate interp

# Full path (for SLURM)
~/miniforge3/envs/interp/bin/python3 script.py
```

Install custom packages:
```bash
source ~/miniforge3/bin/activate
conda activate interp
pip install -r requirements.txt
```

## Benchmark Results (From Setup)

- **GPU**: RTX 3090 (25.3 GB VRAM)
- **Model Loading**: gpt2 (163M params) → ~17 sec
- **Forward Pass**: "Hello world" → torch.Size([1, 3, 50257])
- **Status**: ✅ All packages verified

## Full Workflow Example

```bash
# 1. Write experiment script (using am_eval.py as template)
cat > my_am_exp.py << 'EOF'
from research_logger import ExperimentLogger
...
EOF

# 2. Copy to Battleship
scp my_am_exp.py battleship:~/Workspace/little-leo/

# 3. Run via workflow script
ssh battleship "cd ~/Workspace/little-leo && \
  GPU=3090 GPU_COUNT=1 TIME=0-0:30:00 CPU=4 MEM=16 \
  ./run_gpu_interp.sh my_exp 'python3 my_am_exp.py --output results/exp1'"

# 4. Check results immediately
ssh battleship "cat ~/Workspace/little-leo/results/exp1/summary.json"

# 5. Aggregate results from multiple runs
ls ~/Workspace/little-leo/results/*/summary.json | xargs cat
```

## File Structure on Battleship

```
~/Workspace/little-leo/
├── run_cpu.sh                    # CPU job launcher
├── run_gpu.sh                    # GPU job launcher (system python)
├── run_gpu_interp.sh             # GPU job launcher (interp env)
├── am_experiment_template.py     # Start here for new experiments
├── am_eval.py                    # Full evaluation pipeline
├── research_logger.py            # Metric logging utility
├── WORKFLOW.md                   # Detailed usage
├── logs/                         # Job output logs
└── results/
    ├── exp1/
    │   ├── config.json
    │   ├── metrics.jsonl
    │   ├── summary.json
    │   └── experiment.log
    └── exp2/
        └── ...
```

## Integration with OpenClaw

Lab bot runs:
- **Heartbeat** (every 30 min): Monitors tasks, git, tunnels
- **System Scanner** (06:00): Daily health check
- **Daily Merge** (08:00): Auto-merge macbook-m3 branch
- **Tunnel Watchdog** (every 2h): Restore SSH tunnels if down

All jobs logged in Discord for visibility.

## Tips

1. **Quick test**: `./run_gpu_interp.sh test 'python3 -c "import torch; print(torch.cuda.is_available())"'`
2. **Monitor jobs**: `squeue -u leonardo298` on login node
3. **Check logs**: `tail -f logs/job_name_*.log`
4. **Long jobs**: Use `TIME=1-0` (1 day) for big experiments
5. **Multi-GPU**: `GPU_COUNT=2 GPU=3090` for parallel processing

## Next Steps

1. **Create Method section experiments** using am_eval.py as base
2. **Log metrics** with research_logger (loss, accuracy, interpretability scores)
3. **Run on GPU** via run_gpu_interp.sh for fast iteration
4. **Aggregate results** from multiple runs for statistical robustness
5. **Save summary.json** for paper figures + tables

## Support

- All tools are Python 3.11 compatible
- SLURM job logs: `logs/<job-name>_<JOBID>.log`
- Experiment logs: `results/<exp-name>/experiment.log`
- Questions? Check WORKFLOW.md or ask Lab bot
