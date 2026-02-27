#!/usr/bin/env python3
"""AudioMatters experiment template.

Usage:
    python3 am_experiment_template.py --config config.yaml --output results/
    # Or override:
    python3 am_experiment_template.py --model gpt2 --dataset openwebtext --seed 42
"""

import argparse
import json
import logging
import torch
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def setup_gpu():
    """Check GPU availability and log status."""
    cuda_available = torch.cuda.is_available()
    if cuda_available:
        device = torch.device("cuda:0")
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
        logger.info(f"GPU: {gpu_name} ({gpu_memory:.1f}GB)")
    else:
        device = torch.device("cpu")
        logger.warning("CUDA not available, using CPU (slow)")
    return device


def load_model(model_name: str, device):
    """Load model using transformer-lens."""
    try:
        from transformer_lens import HookedTransformer
        logger.info(f"Loading model: {model_name}")
        model = HookedTransformer.from_pretrained(model_name, device=device)
        return model
    except ImportError:
        logger.error("transformer-lens not installed. Install with: pip install transformer-lens")
        raise


def run_experiment(args):
    """Main experiment loop."""
    # Setup
    device = setup_gpu()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save config
    config = {
        "model": args.model,
        "dataset": args.dataset,
        "seed": args.seed,
        "device": str(device),
        "timestamp": datetime.now().isoformat(),
    }
    config_path = output_dir / "config.json"
    config_path.write_text(json.dumps(config, indent=2))
    logger.info(f"Config saved to {config_path}")
    
    # Load model
    model = load_model(args.model, device)
    logger.info(f"Model loaded. Params: {sum(p.numel() for p in model.parameters()) / 1e6:.1f}M")
    
    # Example: Run forward pass
    test_input = "Hello world"
    logger.info(f"Running forward pass on: '{test_input}'")
    logits = model(test_input)
    logger.info(f"Output shape: {logits.shape}")
    
    # Save results
    results = {
        "model": args.model,
        "input_text": test_input,
        "output_shape": str(logits.shape),
        "status": "success",
    }
    results_path = output_dir / "results.json"
    results_path.write_text(json.dumps(results, indent=2))
    logger.info(f"Results saved to {results_path}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="AudioMatters experiment template")
    parser.add_argument("--model", default="gpt2", help="Model name (gpt2, gpt2-medium, etc.)")
    parser.add_argument("--dataset", default="openwebtext", help="Dataset name")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", default="results/", help="Output directory")
    
    args = parser.parse_args()
    
    logger.info(f"AudioMatters Experiment | Model: {args.model}, Seed: {args.seed}")
    
    try:
        results = run_experiment(args)
        logger.info("✅ Experiment completed successfully")
    except Exception as e:
        logger.error(f"❌ Experiment failed: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
