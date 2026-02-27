#!/usr/bin/env python3
"""Unified research logging for AudioMatters and other experiments.

Usage:
    from research_logger import ExperimentLogger
    logger = ExperimentLogger("my_exp", output_dir="results/")
    
    for step in range(100):
        loss = ...
        logger.log_scalar("loss", loss, step)
        logger.log_scalar("accuracy", acc, step)
    
    logger.save()
    # Generates: config.json, metrics.jsonl, summary.json
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Union
from collections import defaultdict


class ExperimentLogger:
    """Log experiments with automatic config, metrics, and summary."""
    
    def __init__(self, name: str, output_dir: Union[str, Path] = "results/", **config):
        self.name = name
        self.output_dir = Path(output_dir) / name
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.config = {
            "name": name,
            "timestamp": datetime.now().isoformat(),
            **config
        }
        self.metrics = defaultdict(list)
        self._step_count = 0
        
        # Setup logging
        self.logger = logging.getLogger(f"exp.{name}")
        handler = logging.FileHandler(self.output_dir / "experiment.log")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        
        self.logger.info(f"Experiment started: {name}")
        self._save_config()
    
    def _save_config(self):
        """Save config to file."""
        config_path = self.output_dir / "config.json"
        config_path.write_text(json.dumps(self.config, indent=2))
    
    def log_scalar(self, name: str, value: float, step: Optional[int] = None):
        """Log a scalar metric."""
        if step is None:
            step = self._step_count
            self._step_count += 1
        
        self.metrics[name].append({"step": step, "value": value})
    
    def log_dict(self, data: Dict[str, float], step: Optional[int] = None):
        """Log multiple metrics at once."""
        for key, value in data.items():
            self.log_scalar(key, value, step)
    
    def log_info(self, msg: str):
        """Log an info message."""
        self.logger.info(msg)
    
    def log_warning(self, msg: str):
        """Log a warning message."""
        self.logger.warning(msg)
    
    def save(self):
        """Save metrics and generate summary."""
        # Save metrics as JSONL
        metrics_path = self.output_dir / "metrics.jsonl"
        with open(metrics_path, "w") as f:
            for metric_name, values in self.metrics.items():
                for entry in values:
                    f.write(json.dumps({
                        "metric": metric_name,
                        **entry
                    }) + "\n")
        
        # Generate summary
        summary = {
            "name": self.name,
            "config": self.config,
            "metrics": {
                name: {
                    "count": len(values),
                    "last_value": values[-1]["value"] if values else None,
                    "min": min(v["value"] for v in values) if values else None,
                    "max": max(v["value"] for v in values) if values else None,
                    "mean": sum(v["value"] for v in values) / len(values) if values else None,
                }
                for name, values in self.metrics.items()
            }
        }
        
        summary_path = self.output_dir / "summary.json"
        summary_path.write_text(json.dumps(summary, indent=2))
        
        self.logger.info(f"Experiment saved to {self.output_dir}")
        self.logger.info(f"Summary:\n{json.dumps(summary['metrics'], indent=2)}")


if __name__ == "__main__":
    # Example usage
    import random
    
    logger = ExperimentLogger("demo_exp", output_dir="results/", model="gpt2", seed=42)
    
    # Simulate training
    for step in range(10):
        loss = 10 * (0.95 ** step) + random.gauss(0, 0.1)
        acc = 0.3 + 0.5 * (1 - (0.95 ** step)) + random.gauss(0, 0.01)
        
        logger.log_dict({
            "loss": loss,
            "accuracy": acc,
            "learning_rate": 1e-3 * (0.95 ** step)
        }, step=step)
        
        if step % 3 == 0:
            logger.log_info(f"Step {step}: loss={loss:.4f}, acc={acc:.4f}")
    
    logger.save()
    print(f"Results saved to {logger.output_dir}")
