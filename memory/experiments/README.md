# memory/experiments/

Experiment dispatch tracking for battleship GPU jobs.

## Files

- `queue.jsonl` — Active + recent job records (one JSON object per line)
- `results/` — Cached result files fetched from battleship (`<exp_id>_<model>.json`)

## Job Schema

Each line in `queue.jsonl`:

```json
{
  "job_id": "Q001-whisper-small-20260319-0330",
  "exp_id": "Q001",
  "model": "whisper-small",
  "priority": "high",
  "status": "queued|running|done|failed",
  "submitted_at": "2026-03-19T03:30:00+08:00",
  "started_at": null,
  "completed_at": null,
  "result_path": null,
  "error": null
}
```

## Usage

```bash
# Dispatch
python3 skills/shared/experiment_dispatch.py run --exp Q001 --model whisper-small

# Check status
python3 skills/shared/experiment_dispatch.py status

# List queue
python3 skills/shared/experiment_dispatch.py queue --list

# Fetch results
python3 skills/shared/experiment_dispatch.py results --exp Q001 --model whisper-small
```
