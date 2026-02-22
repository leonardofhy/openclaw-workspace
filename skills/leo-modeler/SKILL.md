---
name: leo-modeler
description: Build and maintain Leo's personalized decision model from diary data. Use when creating/updating `memory/leo-profile.json`, `memory/leo-state-weekly.json`, or evaluating whether coaching rules should be adjusted based on recent mood, energy, and sleep signals.
---

# Leo Modeler

Build, update, and evaluate Leo's personal model as a deterministic workflow.

## Quick Start

Run these in order:

1. Build/refresh profile (slow-changing traits)
```bash
python3 /Users/leonardo/.openclaw/workspace/skills/leo-modeler/scripts/build_profile.py
```

2. Update recent state (14-day signals)
```bash
python3 /Users/leonardo/.openclaw/workspace/skills/leo-modeler/scripts/update_state.py
```

3. Evaluate and suggest rule tweaks
```bash
python3 /Users/leonardo/.openclaw/workspace/skills/leo-modeler/scripts/evaluate_model.py
```

## Workflow Rules

- Prefer recent data when user says habits changed.
- Keep user corrections as source of truth over historical inference.
- Separate outputs by role:
  - `leo-profile.json`: long-term traits and tendencies
  - `leo-state-weekly.json`: recent status and risk flags
  - `leo-model-eval.md`: tuning notes for coaching/guardian behavior

## Output Contracts

### `memory/leo-profile.json`
- Contains durable signals and baseline metrics.
- Keep manually curated fields unless explicitly replaced.

### `memory/leo-state-weekly.json`
- Represents rolling 14-day status.
- Include mood/energy averages and late-sleep risk.

### `memory/leo-model-eval.md`
- Human-readable weekly model health check.
- Include concrete tuning suggestions.

## References

- See `references/modeling_principles.md` for design principles.
