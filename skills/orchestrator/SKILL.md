# Orchestrator — DAG-Based Agent Pipeline

Multi-step task orchestration with dependency resolution, wave-based execution, and git worktree isolation.

## When to Use

- Multi-step pipelines where tasks have dependencies (e.g., "write results after viz is done")
- Parallel agent execution with sequential merging
- Any workflow that can be modeled as a DAG (directed acyclic graph)

## Quick Start

```bash
cd /path/to/workspace

# 1. Create pipeline
python3 skills/orchestrator/scripts/orchestrator.py init --name paper-v2

# 2. Add tasks
python3 skills/orchestrator/scripts/orchestrator.py add \
  --id CC-data --prompt 'Clean and prepare dataset'

python3 skills/orchestrator/scripts/orchestrator.py add \
  --id CC-viz --prompt 'Create visualizations' --depends-on CC-data

python3 skills/orchestrator/scripts/orchestrator.py add \
  --id CC-results --prompt 'Write results section' --depends-on CC-viz

# 3. Review plan
python3 skills/orchestrator/scripts/orchestrator.py plan

# 4. Execute
python3 skills/orchestrator/scripts/orchestrator.py run
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `init --name NAME` | Create empty manifest |
| `add --id ID --prompt TEXT [--depends-on A,B] [--model MODEL] [--timeout N] [--retries N]` | Add task |
| `plan` | Show execution plan (waves + deps) |
| `run [--wave N]` | Execute pipeline (optionally one wave) |
| `status` | Show current status |
| `retry --id ID` | Reset a failed task to pending |
| `clean` | Remove worktrees + reset manifest |

All commands accept `--manifest PATH` (default: `./manifest.json`).

## Manifest Schema

```json
{
  "version": 1,
  "pipeline_name": "paper-v2",
  "tasks": {
    "CC-viz": {
      "prompt": "Create visualization...",
      "depends_on": [],
      "status": "pending|running|completed|failed|skipped",
      "model": "claude-sonnet-4-20250514",
      "timeout": 300,
      "retries": 3,
      "retry_count": 0,
      "artifacts": [],
      "workdir": null,
      "started_at": null,
      "completed_at": null,
      "error": null,
      "session_id": null
    }
  },
  "waves": [["CC-viz"], ["CC-results"]]
}
```

## How It Works

1. **Manifest** defines tasks as a DAG (tasks + dependencies)
2. **Wave computation** — topological sort groups tasks into execution waves
3. **For each wave**: create git worktrees, spawn CC agents in parallel
4. **Poll** for COMPLETED.txt / FAILED.txt in each worktree
5. **Merge** completed worktrees sequentially into main branch
6. **Retry** failed tasks up to `retries` times before marking as failed

## Best Practices

- Keep tasks independent within a wave — they run in parallel
- Use `artifacts` to pass data between tasks, not stdout
- Set reasonable `timeout` values (default 300s)
- Use `prompt_file` for complex prompts (keeps manifest clean)
- Run `plan` before `run` to verify wave structure
- Use `clean` to reset after a failed run
