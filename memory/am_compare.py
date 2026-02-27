#!/usr/bin/env python3
"""Compare AudioMatters experiments side-by-side.

Usage:
    python3 am_compare.py results/exp1 results/exp2 results/exp3
    python3 am_compare.py --glob results/*/summary.json --metric wer
    python3 am_compare.py results/ --model whisper --output comparison.csv
"""

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any
import sys


class ExperimentComparison:
    """Load and compare multiple experiment results."""
    
    def __init__(self, exp_dirs: List[Path]):
        self.experiments = {}
        for exp_dir in exp_dirs:
            exp_dir = Path(exp_dir)
            if not exp_dir.is_dir():
                print(f"Warning: {exp_dir} is not a directory", file=sys.stderr)
                continue
            
            name = exp_dir.name
            summary_path = exp_dir / "summary.json"
            
            if not summary_path.exists():
                print(f"Warning: No summary.json in {exp_dir}", file=sys.stderr)
                continue
            
            summary = json.loads(summary_path.read_text())
            self.experiments[name] = {
                "path": exp_dir,
                "summary": summary,
                "config": summary.get("config", {}),
                "metrics": summary.get("metrics", {}),
            }
    
    def print_table(self, metric_keys: List[str] = None):
        """Print comparison table."""
        if not self.experiments:
            print("No experiments loaded", file=sys.stderr)
            return
        
        # Collect all metric keys
        all_metrics = set()
        for exp in self.experiments.values():
            all_metrics.update(exp["metrics"].keys())
        
        if metric_keys:
            all_metrics = [m for m in all_metrics if any(k in m for k in metric_keys)]
        else:
            all_metrics = sorted(all_metrics)
        
        # Print header
        header = ["Experiment"] + all_metrics
        col_widths = {}
        col_widths["Experiment"] = max(len("Experiment"), max(len(e) for e in self.experiments.keys()))
        for metric in all_metrics:
            col_widths[metric] = max(len(metric), 12)
        
        # Print rows
        def fmt(h, w=None):
            width = w or col_widths.get(h, len(str(h)))
            return f"{str(h):<{width}}"
        
        print(" | ".join(fmt(h, col_widths[h]) for h in header))
        print("-" * (sum(col_widths.values()) + 3 * len(header)))
        
        for exp_name in sorted(self.experiments.keys()):
            exp = self.experiments[exp_name]
            row = [fmt(exp_name, col_widths["Experiment"])]
            for metric in all_metrics:
                val = exp["metrics"].get(metric, {})
                val_str = f"{val.get('last_value', '?'):.4f}" if isinstance(val.get('last_value'), float) else "?"
                row.append(fmt(val_str, col_widths[metric]))
            print(" | ".join(row))
    
    def print_configs(self):
        """Print config differences."""
        if not self.experiments:
            print("No experiments loaded")
            return
        
        print("\n=== Configurations ===\n")
        for exp_name in sorted(self.experiments.keys()):
            config = self.experiments[exp_name]["config"]
            print(f"{exp_name}:")
            for key in sorted(config.keys()):
                if key != "timestamp":
                    print(f"  {key}: {config[key]}")
            print()
    
    def export_csv(self, output_path: Path):
        """Export comparison to CSV."""
        import csv
        
        # Collect all metrics
        all_metrics = set()
        for exp in self.experiments.values():
            all_metrics.update(exp["metrics"].keys())
        all_metrics = sorted(all_metrics)
        
        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow(["Experiment", "Model", "Dataset", "Task"] + all_metrics)
            
            # Rows
            for exp_name in sorted(self.experiments.keys()):
                exp = self.experiments[exp_name]
                config = exp["config"]
                row = [
                    exp_name,
                    config.get("model", "?"),
                    config.get("dataset", "?"),
                    config.get("task", "?"),
                ]
                for metric in all_metrics:
                    val = exp["metrics"].get(metric, {}).get("last_value", "")
                    row.append(f"{val:.6f}" if isinstance(val, float) else val)
                writer.writerow(row)
        
        print(f"✅ Exported to {output_path}")


def find_experiments(root_dir: Path) -> List[Path]:
    """Find all experiment directories with summary.json."""
    exp_dirs = []
    for summary_path in root_dir.rglob("summary.json"):
        exp_dir = summary_path.parent
        exp_dirs.append(exp_dir)
    return sorted(exp_dirs)


def main():
    parser = argparse.ArgumentParser(description="Compare AudioMatters experiments")
    parser.add_argument("experiments", nargs="*", help="Experiment directories (or root dir for auto-discovery)")
    parser.add_argument("--glob", help="Glob pattern for experiment summary files")
    parser.add_argument("--metric", help="Filter metrics containing this keyword")
    parser.add_argument("--output", help="Export to CSV file")
    parser.add_argument("--configs", action="store_true", help="Show config differences")
    
    args = parser.parse_args()
    
    # Load experiments
    exp_dirs = []
    
    if args.glob:
        exp_dirs = [Path(p).parent for p in Path(".").glob(args.glob)]
    elif args.experiments:
        for path in args.experiments:
            path = Path(path)
            if path.is_dir() and (path / "summary.json").exists():
                exp_dirs.append(path)
            elif path.is_dir():
                # Auto-discover
                found = find_experiments(path)
                if found:
                    exp_dirs.extend(found)
    
    if not exp_dirs:
        print("No experiments found", file=sys.stderr)
        parser.print_help()
        return 1
    
    # Compare
    comparison = ExperimentComparison(exp_dirs)
    
    if not comparison.experiments:
        print("No valid experiments loaded", file=sys.stderr)
        return 1
    
    # Output
    metric_filter = args.metric.split(",") if args.metric else None
    comparison.print_table(metric_filter)
    
    if args.configs:
        comparison.print_configs()
    
    if args.output:
        comparison.export_csv(Path(args.output))
    
    return 0


if __name__ == "__main__":
    exit(main())
