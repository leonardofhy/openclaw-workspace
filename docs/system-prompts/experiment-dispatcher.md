# Task: Build Experiment Dispatcher for Battleship GPU

Build a robust experiment dispatch system for running ML experiments on the lab's
GPU machine (battleship) via SSH.

## Context

Read these files first:
- `TOOLS.md` — SSH connection details for battleship/lab
- `skills/coordinator/scripts/orchestrator.py` — existing cross-machine dispatch
- `memory/task-board.md` — see M-06 (Q001/Q002 scale-up) for what experiments need running
- `skills/autodidact/scripts/` — see how experiments are currently queued

## What to Build

### `skills/shared/experiment_dispatch.py`

A CLI and importable module for dispatching experiments to battleship GPU.

```
python3 experiment_dispatch.py run --exp Q001 --model whisper-small
python3 experiment_dispatch.py run --exp Q001 --model whisper-medium
python3 experiment_dispatch.py status
python3 experiment_dispatch.py queue --list
python3 experiment_dispatch.py queue --add Q002 --model whisper-small --priority high
python3 experiment_dispatch.py results --exp Q001 --model whisper-small
```

**Core functions:**

1. `dispatch(exp_id, model, priority='normal', dry_run=False) -> str`
   - SSH to battleship: `ssh -J iso_leo -p 2222 leonardo@localhost`
   - Navigate to the experiment script location
   - Submit job via nohup or screen/tmux if available
   - Return job_id string
   - Write to `memory/experiments/queue.jsonl` (status: queued/running/done/failed)

2. `check_status(job_id=None) -> list[dict]`
   - SSH to battleship, check process status
   - Update `memory/experiments/queue.jsonl` with current status
   - Return list of job status dicts

3. `fetch_results(exp_id, model) -> dict | None`
   - SSH to battleship, cat results file
   - Parse and return structured dict
   - Cache to `memory/experiments/results/<exp_id>_<model>.json`

**Job schema for queue.jsonl:**
```json
{
  "job_id": "Q001-whisper-small-20260319-0330",
  "exp_id": "Q001",
  "model": "whisper-small",
  "priority": "high",
  "status": "queued",
  "submitted_at": "2026-03-19T03:30:00+08:00",
  "started_at": null,
  "completed_at": null,
  "result_path": null,
  "error": null
}
```

2. **Dry-run mode**: `--dry-run` prints the SSH command without executing
3. **Graceful SSH failure**: if SSH fails, mark job as failed with error, don't crash

### `skills/shared/test_experiment_dispatch.py`

Tests (mock SSH, no real network calls):
- test_dispatch_dry_run: verify correct SSH command constructed
- test_queue_write: dispatch adds entry to queue.jsonl
- test_status_update: check_status updates queue correctly
- test_results_caching: fetch_results caches to correct path
- test_priority_ordering: high priority jobs sorted first in queue list

### Also create: `memory/experiments/` directory structure

```
memory/experiments/
  queue.jsonl          # active + recent jobs
  results/             # cached result files
  README.md            # brief docs
```

### Pre-queue the critical experiments

After building the dispatcher, pre-queue these jobs in queue.jsonl (status: queued):
1. Q001 whisper-small (high priority)
2. Q002 whisper-small (high priority)
3. Q001 whisper-medium (normal)
4. Q002 whisper-medium (normal)

## Constraints
- SSH is via: `ssh -J iso_leo -p 2222 leonardo@localhost`
- Lab Python env: `~/miniconda3/bin/python3`
- Experiment scripts are under: `~/.openclaw/workspace/skills/autodidact/`
- No external dependencies — stdlib only (subprocess, json, pathlib)
- Timeout for SSH commands: 30 seconds
