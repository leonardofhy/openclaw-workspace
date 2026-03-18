# CLAUDE.md — Workspace Conventions for All CC Agents

> This file is auto-inherited by all Claude Code agents spawned in this workspace.
> Keep it concise — every line burns tokens on every CC invocation.

## Test Conventions
- Framework: `pytest` (not unittest, unless extending existing test files)
- File naming: `test_*.py` in same directory as source
- Pattern: `sys.path.insert(0, os.path.dirname(__file__))` for imports
- Mock external APIs/SSH/network calls — tests must work offline
- Use `tempfile.TemporaryDirectory()` for file operations, never touch real workspace files
- Subprocess tests: use `[sys.executable, script_path]`, check returncode

## Code Style
- Python 3.10+ (use `|` union types, not `Union[]`)
- Docstrings on public functions (one-liner OK)
- `argparse` for CLI scripts with `--help` support
- `--json` flag for machine-readable output where applicable
- `--dry-run` for destructive operations

## File Organization
- Scripts: `skills/{skill-name}/scripts/`
- Tests: same directory as source (`test_*.py`)
- Docs: `docs/`
- Memory/state: `memory/`
- Never write to `secrets/`

## Git
- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`
- One commit per logical change
- Don't commit `__pycache__/`, `.pyc`, or temp files

## Common Pitfalls
- `openclaw.json`: NEVER edit directly, use `openclaw config set`
- Discord targets: use channel IDs, not user IDs
- File locking: use `fcntl.flock` for shared state files (e.g., manifest.json)
- Error handling: always catch and report, never silently swallow
