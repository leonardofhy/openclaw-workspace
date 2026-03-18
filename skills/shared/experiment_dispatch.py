#!/usr/bin/env python3
"""Cross-machine experiment orchestrator.

Dispatches experiments from MacBook (control plane) to Battleship cluster
(compute plane) via SSH/SCP, tracks status, and collects results.

Usage:
    python3 experiment_dispatch.py dispatch --script <path> --model <model> --name <name> [--dry-run]
    python3 experiment_dispatch.py status --job-id <id> | --all
    python3 experiment_dispatch.py collect --job-id <id>
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REMOTE_HOST = "battleship"
REMOTE_EXPERIMENT_DIR = "~/experiments"
REMOTE_OUTPUT_DIR = "~/experiments/results"
REMOTE_LOG_DIR = "~/experiments/logs"

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATE_PATH = REPO_ROOT / "skills" / "shared" / "templates" / "slurm_template.sh"
DISPATCHES_LOG = REPO_ROOT / "memory" / "learning" / "dispatches.jsonl"
EXPERIMENTS_LOG = REPO_ROOT / "memory" / "learning" / "experiments" / "experiments.jsonl"
RESULTS_DIR = REPO_ROOT / "memory" / "learning" / "results"

VALID_MODELS = ("whisper-base", "whisper-small", "whisper-medium")

SLURM_DEFAULTS = {
    "partition": "gpu",
    "gpu_count": 1,
    "cpus": 4,
    "memory": "32G",
    "walltime": "04:00:00",
    "conda_env": "whisper",
}


def run_cmd(cmd: list[str], *, dry_run: bool = False, capture: bool = True) -> str:
    """Run a shell command, or print it in dry-run mode."""
    cmd_str = " ".join(cmd)
    if dry_run:
        print(f"[DRY RUN] {cmd_str}")
        return ""
    result = subprocess.run(cmd, capture_output=capture, text=True, check=True)
    return result.stdout.strip() if capture else ""


def ssh_cmd(remote_cmd: str, *, dry_run: bool = False) -> str:
    """Run a command on the remote host via SSH."""
    return run_cmd(["ssh", REMOTE_HOST, remote_cmd], dry_run=dry_run)


def scp_to(local_path: str, remote_path: str, *, dry_run: bool = False) -> str:
    """SCP a file to the remote host."""
    return run_cmd(["scp", local_path, f"{REMOTE_HOST}:{remote_path}"], dry_run=dry_run)


def scp_from(remote_path: str, local_path: str, *, dry_run: bool = False) -> str:
    """SCP a file from the remote host."""
    return run_cmd(["scp", f"{REMOTE_HOST}:{remote_path}", local_path], dry_run=dry_run)


def append_jsonl(path: Path, record: dict) -> None:
    """Append a JSON record to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


def generate_slurm_script(
    job_name: str,
    model: str,
    script_basename: str,
    **overrides: str,
) -> str:
    """Generate a Slurm job script from the template."""
    template = TEMPLATE_PATH.read_text()
    params = {**SLURM_DEFAULTS, **overrides}
    return template.format(
        job_name=job_name,
        model=model,
        script_basename=script_basename,
        log_dir=REMOTE_LOG_DIR,
        remote_output_dir=REMOTE_OUTPUT_DIR,
        extra_args="",
        **params,
    )


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------

def cmd_dispatch(args: argparse.Namespace) -> None:
    script_path = Path(args.script).resolve()
    if not script_path.exists():
        sys.exit(f"Error: script not found: {script_path}")
    if args.model not in VALID_MODELS:
        sys.exit(f"Error: model must be one of {VALID_MODELS}")

    job_name = args.name
    script_basename = script_path.name
    dry = args.dry_run

    print(f"=== Dispatching experiment: {job_name} ===")
    print(f"  Script: {script_path}")
    print(f"  Model:  {args.model}")
    print(f"  Remote: {REMOTE_HOST}:{REMOTE_EXPERIMENT_DIR}")
    print()

    # 1. Ensure remote directories exist
    ssh_cmd(f"mkdir -p {REMOTE_EXPERIMENT_DIR} {REMOTE_OUTPUT_DIR} {REMOTE_LOG_DIR}", dry_run=dry)

    # 2. SCP the experiment script
    scp_to(str(script_path), f"{REMOTE_EXPERIMENT_DIR}/{script_basename}", dry_run=dry)

    # 3. Generate and upload slurm job script
    slurm_content = generate_slurm_script(
        job_name=job_name,
        model=args.model,
        script_basename=script_basename,
        gpu_count=str(args.gpus),
        walltime=args.walltime,
        memory=args.mem,
    )
    slurm_filename = f"slurm_{job_name}.sh"
    local_tmp = Path(f"/tmp/{slurm_filename}")

    if dry:
        print(f"[DRY RUN] Would write slurm script to {local_tmp}:")
        print("--- slurm script ---")
        print(slurm_content)
        print("--- end ---")
    else:
        local_tmp.write_text(slurm_content)

    scp_to(str(local_tmp), f"{REMOTE_EXPERIMENT_DIR}/{slurm_filename}", dry_run=dry)

    # 4. Submit via sbatch
    job_id = ""
    if dry:
        print(f"[DRY RUN] ssh {REMOTE_HOST} 'sbatch {REMOTE_EXPERIMENT_DIR}/{slurm_filename}'")
        job_id = "DRY-RUN-12345"
    else:
        output = ssh_cmd(f"sbatch {REMOTE_EXPERIMENT_DIR}/{slurm_filename}")
        # sbatch output: "Submitted batch job 12345"
        job_id = output.strip().split()[-1]

    print(f"\nJob submitted: {job_id}")

    # 5. Log dispatch
    record = {
        "job_id": job_id,
        "job_name": job_name,
        "model": args.model,
        "script": str(script_path),
        "remote_host": REMOTE_HOST,
        "gpus": args.gpus,
        "walltime": args.walltime,
        "dispatched_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry,
    }
    if not dry:
        append_jsonl(DISPATCHES_LOG, record)
    else:
        print(f"\n[DRY RUN] Would log to {DISPATCHES_LOG}:")
        print(f"  {json.dumps(record, indent=2)}")

    print(f"\nDone. Track with: python3 {__file__} status --job-id {job_id}")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

def cmd_status(args: argparse.Namespace) -> None:
    if args.all:
        output = ssh_cmd("squeue --me --format='%.10i %.30j %.8T %.10M %.4C %.6b %R'")
        if output:
            print(output)
        else:
            print("No active jobs.")
        return

    if not args.job_id:
        sys.exit("Error: provide --job-id or --all")

    output = ssh_cmd(f"squeue -j {args.job_id} --format='%.10i %.30j %.8T %.10M %.4C %.6b %R' 2>&1 || true")
    if "Invalid job id" in output or not output.strip():
        print(f"Job {args.job_id} not in queue (likely completed or failed).")
        # Check sacct for final status
        acct = ssh_cmd(
            f"sacct -j {args.job_id} --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS --noheader 2>&1 || true"
        )
        if acct.strip():
            print(f"Accounting info:\n{acct}")

        # Check for completion signal
        done_files = ssh_cmd(f"ls {REMOTE_OUTPUT_DIR}/*.done 2>/dev/null || true")
        if done_files:
            print(f"\nCompletion signals found:\n{done_files}")
            print(f"\nCollect results with: python3 {__file__} collect --job-id {args.job_id}")
    else:
        print(output)


# ---------------------------------------------------------------------------
# collect
# ---------------------------------------------------------------------------

def cmd_collect(args: argparse.Namespace) -> None:
    if not args.job_id:
        sys.exit("Error: provide --job-id")

    job_id = args.job_id
    dry = args.dry_run
    local_results = RESULTS_DIR / job_id
    local_results.mkdir(parents=True, exist_ok=True)

    print(f"=== Collecting results for job {job_id} ===")

    # 1. Collect stdout/stderr logs
    for ext in ("out", "err"):
        remote_log = f"{REMOTE_LOG_DIR}/*-{job_id}.{ext}"
        try:
            scp_from(remote_log, str(local_results) + "/", dry_run=dry)
            print(f"  Collected .{ext} log")
        except subprocess.CalledProcessError:
            print(f"  No .{ext} log found for job {job_id}")

    # 2. Collect output files (.json, .csv)
    for pattern in ("*.json", "*.csv"):
        try:
            scp_from(f"{REMOTE_OUTPUT_DIR}/{pattern}", str(local_results) + "/", dry_run=dry)
            print(f"  Collected {pattern} files")
        except subprocess.CalledProcessError:
            print(f"  No {pattern} files found")

    # 3. Collect completion signals
    try:
        scp_from(f"{REMOTE_OUTPUT_DIR}/*.done", str(local_results) + "/", dry_run=dry)
        print("  Collected .done signals")
    except subprocess.CalledProcessError:
        pass

    # 4. Parse results into experiments.jsonl
    if not dry:
        collected_files = list(local_results.glob("*.json"))
        for f in collected_files:
            if f.suffix == ".json" and f.stem.endswith(".done"):
                continue
            try:
                data = json.loads(f.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            record = {
                "job_id": job_id,
                "source_file": f.name,
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "data": data,
            }
            append_jsonl(EXPERIMENTS_LOG, record)
            print(f"  Parsed {f.name} -> experiments.jsonl")

    print(f"\nResults saved to: {local_results}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cross-machine experiment orchestrator (MacBook -> Battleship)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # dispatch
    p_dispatch = sub.add_parser("dispatch", help="Dispatch an experiment to Battleship")
    p_dispatch.add_argument("--script", required=True, help="Path to experiment script")
    p_dispatch.add_argument("--model", required=True, choices=VALID_MODELS, help="Whisper model size")
    p_dispatch.add_argument("--name", required=True, help="Experiment name (used as job name)")
    p_dispatch.add_argument("--gpus", type=int, default=1, help="Number of GPUs (default: 1)")
    p_dispatch.add_argument("--walltime", default="04:00:00", help="Walltime (default: 04:00:00)")
    p_dispatch.add_argument("--mem", default="32G", help="Memory (default: 32G)")
    p_dispatch.add_argument("--dry-run", action="store_true", help="Print commands without executing")

    # status
    p_status = sub.add_parser("status", help="Check job status on Battleship")
    p_status.add_argument("--job-id", help="Slurm job ID")
    p_status.add_argument("--all", action="store_true", help="Show all active jobs")

    # collect
    p_collect = sub.add_parser("collect", help="Collect results from Battleship")
    p_collect.add_argument("--job-id", required=True, help="Slurm job ID")
    p_collect.add_argument("--dry-run", action="store_true", help="Print commands without executing")

    args = parser.parse_args()

    if args.command == "dispatch":
        cmd_dispatch(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "collect":
        cmd_collect(args)


if __name__ == "__main__":
    main()
