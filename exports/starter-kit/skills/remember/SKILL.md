---
name: remember
description: Append facts, ideas, or decisions to long-term memory files.
---

# Remember Skill

Use this to store information permanently in the file system.

## Usage

```bash
python3 skills/remember/scripts/append_memory.py --target <filename> --text "<content>" [--tag <tag>]
```

## Targets
- `core` -> `memory/core.md` (General preferences, identity)
- `projects/my-project` -> `memory/projects/my-project.md` (Specific project)
- `knowledge` -> `memory/knowledge.md` (Random facts)
- `MEMORY.md` -> `MEMORY.md` (High-level profile, *use carefully*)

## Examples

**Store a project decision:**
```bash
python3 skills/remember/scripts/append_memory.py --target projects/my-project --text "Meeting moved to Fridays at 15:00." --tag decision
```

**Store a user preference:**
```bash
python3 skills/remember/scripts/append_memory.py --target core --text "{{NICKNAME}} prefers concise summaries over long texts." --tag preference
```

**Store a technical fact:**
```bash
python3 skills/remember/scripts/append_memory.py --target knowledge --text "API v1 uses different auth header than v2." --tag fact
```
