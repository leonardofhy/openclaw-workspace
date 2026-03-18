# Task: Write CLAUDE.md — Workspace-Level Conventions for CC Agents

You are writing `CLAUDE.md` for this workspace. This file is automatically read by every
Claude Code agent spawned here, so it must be precise, actionable, and complete.

## What to Analyze First

Read these files to understand the workspace:
- `AGENTS.md` — workspace rules (authoritative)
- `pyproject.toml` — test config, paths
- `conftest.py` — root pytest fixtures and sys.path setup
- `skills/orchestrator/scripts/dag_orchestrator.py` — how CCs are spawned
- Any 3 test files of your choice under skills/ to understand test patterns
- Any 3 scripts of your choice to understand code patterns

Also check:
- What Python version is in use
- How imports are structured (relative vs absolute, sys.path.insert patterns)
- How tests handle temp dirs and fixtures
- What linting/formatting tools are configured

## CLAUDE.md Must Cover

### 1. Project Structure
- Workspace root layout
- Where skills live, where scripts live, where tests live
- `memory/` directory purpose
- `skills/shared/` common utilities

### 2. Python Conventions
- Python version and virtualenv situation
- Import style: how to import from `skills/shared/`, `skills/lib/`
- No relative imports across skill boundaries (use sys.path.insert)
- Type hints: use modern Python 3.10+ syntax (X | Y, list[X], etc.)
- No bare `except:` — always `except SpecificError`

### 3. Testing Conventions
- Test file naming: `test_<module>.py` must be unique across all skills (no two files with same name)
- How to run tests: `python3 -m pytest <file> -v`
- Required: every new script gets a test file
- Fixtures: use `tmp_path` for temp dirs, not `/tmp/` hardcoded
- Mock external calls (HTTP, subprocess) in tests

### 4. Git Conventions
- Always `git add -A && git commit -m "type: description"` after completing work
- Commit message types: feat/fix/docs/refactor/test/chore
- NEVER commit secrets (check for .env, .json with tokens, passwords)
- Push only when tests pass

### 5. File Output Rules
- New scripts go in `skills/<skill-name>/scripts/`
- New tests go alongside scripts: `skills/<skill-name>/scripts/test_<name>.py`
- Test file names MUST be globally unique (add skill prefix if needed)
- Do NOT create files in workspace root unless explicitly asked

### 6. COMPLETED.txt Convention (CRITICAL)
- When a CC task completes, create `COMPLETED.txt` in the working directory
- But ONLY if the working dir is a worktree (`.worktrees/` in path), NOT in workspace root
- Check: `if '.worktrees' in str(Path.cwd()): write COMPLETED.txt`
- This prevents merge conflicts when multiple CCs run in parallel

### 7. Common Pitfalls to Avoid
- Do NOT use `json.load(open(...))` without `with` statement
- Do NOT hardcode absolute paths — use `Path(__file__).resolve().parent`
- Do NOT import from `skills/lib/` without adding it to sys.path first
- Do NOT create `orchestrator.py` as a filename (collides with coordinator)
- Do NOT assume cwd is the workspace root when running in worktrees

### 8. Shared Utilities
List and briefly describe what's in:
- `skills/shared/jsonl_store.py`
- `skills/shared/ensure_state.py`
- `skills/lib/common.py`

## Output

Write the complete `CLAUDE.md` file in the workspace root.
Keep it under 150 lines — dense but scannable.
Use headers and bullet points.
This file must be immediately useful for a fresh CC agent.
