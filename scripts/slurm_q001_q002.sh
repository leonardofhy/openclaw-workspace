#!/bin/bash
#SBATCH --job-name=q001_q002_scaleup
#SBATCH --output=memory/learning/slurm-scaleup.log
#SBATCH --error=memory/learning/slurm-scaleup.log
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --mail-type=END,FAIL

# ===========================================================================
# Q001/Q002 Scale-Up — Whisper-small & Whisper-medium
# Target: Battleship cluster (RTX PRO 6000)
# ===========================================================================

set -euo pipefail

echo "============================================"
echo "  Q001/Q002 Scale-Up Job"
echo "  Host: $(hostname)"
echo "  Date: $(date -Iseconds)"
echo "  GPU:  $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo 'N/A')"
echo "============================================"

# --- Environment setup ---
# Try conda first, fall back to venv
if command -v conda &>/dev/null; then
    eval "$(conda shell.bash hook)"
    conda activate whisper 2>/dev/null || conda activate base
elif [ -d "$HOME/venv/whisper/bin" ]; then
    source "$HOME/venv/whisper/bin/activate"
elif [ -d "$HOME/.venv/bin" ]; then
    source "$HOME/.venv/bin/activate"
fi

# Verify deps
python -c "import torch; import whisper; import numpy; print(f'torch={torch.__version__}, cuda={torch.cuda.is_available()}')"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
SCALEUP="$REPO_DIR/skills/autodidact/scripts/q001_q002_scaleup.py"
OUTPUT_DIR="$REPO_DIR/memory/learning"

mkdir -p "$OUTPUT_DIR"

echo ""
echo ">>> Running whisper-small..."
echo ""
python "$SCALEUP" --model whisper-small --output-dir "$OUTPUT_DIR"

echo ""
echo ">>> Running whisper-medium..."
echo ""
python "$SCALEUP" --model whisper-medium --output-dir "$OUTPUT_DIR"

echo ""
echo "============================================"
echo "  All runs complete: $(date -Iseconds)"
echo "============================================"
