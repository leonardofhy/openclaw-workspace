# System-Wide Code Review — 2026-03-18

**Reviewer:** Claude (automated audit)
**Branch:** `macbook-m3`
**Scope:** 184 Python files, ~57k LOC across 19 skill directories

---

## 1. Executive Summary

The OpenClaw workspace is a well-architected personal AI assistant with strong modular isolation, no circular dependencies, and solid security practices (no secrets in source, no `shell=True`, no deserialization risks). The boot-budget system (AGENTS.md) enforcing ≤300 lines of kernel context is a standout design choice. The autodidact subsystem (29.7k LOC, 91 files) dominates the codebase and contains ~49 orphaned experimental scripts that should be archived. Test coverage is respectable (1,180 tests) but unevenly distributed — shared utilities that mutate data (`task_sync.py`, `ensure_state.py`) and the entire autodidact tools/ surface are untested. The most critical bugs are: a dead-code branch in `task_sync.py:create_task`, O(N) full-file parses in its `do_pull` loop, and a logic error in `precheck.py` where missing state files produce `RUN` instead of `SKIP`.

---

## 2. Critical Issues (Must Fix)

### C1. `task_sync.py:123` — Dead-code branch: `label_id` parameter never used
```python
labels = [label_name] if label_id is None else [label_name]
# Both branches are identical — label_id has no effect
```
**Impact:** Todoist tasks may be created with wrong labels. The second branch likely should use `label_id` directly.

### C2. `task_sync.py:358–370` — O(N) full-file parse in `do_pull` loop
For every completed Todoist item, `parse_task_board` is called twice (once for `last_touched`, once for `progress`), re-reading and re-parsing the entire `task-board.md` each time. This is O(N x file_size) and could corrupt progress data if line indices shift between parses.
**Fix:** Single parse, batch write.

### C3. `precheck.py:73` — Missing state files produce `RUN` instead of `SKIP`
```python
if not active or not queue:
    print("RUN")  # Should be SKIP or ERROR
```
**Impact:** When state files are missing or corrupt, the autodidact cycle runs when it should abort.

### C4. `gc_eval.py:524–529` — O(N) full encoder passes in causal patching
Each patched-layer evaluation re-runs the full encoder from scratch instead of caching the noisy baseline. For a 32-layer model this is 32x redundant compute.

### C5. `scan.py:209–215` — Auto-push in `--fix` mode without confirmation
The `check_git` fix closure runs `git add -u && git commit && git push` automatically, staging **all** tracked modified files including potentially sensitive changes. No dry-run or confirmation prompt exists.

---

## 3. Warnings (Should Fix)

| ID | File:Line | Issue |
|---|---|---|
| W1 | `jsonl_store.py:63` | `split("-")[1]` breaks for hyphenated prefixes — use `rsplit("-", 1)` |
| W2 | `jsonl_store.py:32` | `find_workspace()` shells out to `git` at import time — module-level side effect |
| W3 | `task_sync.py:29` | Hardcoded `TZ = timezone(timedelta(hours=8))` — use `zoneinfo.ZoneInfo("Asia/Taipei")` |
| W4 | `task_sync.py:43–46` | Secrets read from `secrets/todoist.env` with no `.gitignore` verification |
| W5 | `task_sync.py:153` | Merge conflict detection matches `=======` which appears in normal markdown HR |
| W6 | `diary_utils.py:83` | `gspread.authorize(creds)` deprecated since gspread 5.x |
| W7 | `diary_utils.py:15` | Four `.parent` calls to find workspace root — fragile if restructured |
| W8 | `schedule_engine.py:117` | Loop variable `l` visually ambiguous with digit `1` |
| W9 | `schedule_engine.py:266` | `now_str` parsing with `[:2]`/`[3:5]` slicing — no format validation |
| W10 | `precheck.py:115–133` | `TypeError` not caught when timestamp values are non-string |
| W11 | `kg_query.py:84–85` | Dead outer `or` branch — heading match never contributes to results |
| W12 | `kg_query.py:69–71` | `while i < len` with `i += 2` — fragile; `IndexError` risk on files without headings |
| W13 | `scan.py:455–463` | `save_cron_jobs` return value not checked — reports "Fixed" on failed save |
| W14 | `scan.py:82–88` | `load_env` quote-stripping doesn't match shell semantics |
| W15 | `learn.py:27–28` | Relative path strings — resolve against wrong CWD if run from different dir |
| W16 | `learn.py:43–44` | `SequenceMatcher` is O(n^2) per item, called for entire store on every `cmd_log` |
| W17 | `gc_eval.py:190` | `threshold = self.x or 0.1` — falsy `0.0` silently becomes `0.1` |
| W18 | `unified_results_dashboard.py:370–383` | Hardcoded date `"2026-03-18"` in path and banner — must be manually updated |
| W19 | Multiple files | `read_text()` without `encoding="utf-8"` (jsonl_store:46, task_sync:150,221) |
| W20 | Multiple files | `sys.path.insert(0, ...)` at module level makes files non-importable from other locations |

---

## 4. Suggestions (Nice to Have)

| ID | Area | Suggestion |
|---|---|---|
| S1 | Autodidact | Archive ~49 orphaned experimental scripts to `autodidact/.archive/` to reduce cognitive load |
| S2 | Project config | Add `pyproject.toml` with `[tool.pytest.ini_options]` setting `pythonpath = ["skills"]` — eliminates all `importlib.util.spec_from_file_location` workarounds in tests |
| S3 | Shared | Add root `conftest.py` with shared `tmp_workspace` and `mock_token` fixtures |
| S4 | Testing | Write tests for `task_sync.py` — highest-risk data mutation code with zero coverage |
| S5 | Testing | Add contract tests for `feed-recommend/scripts/sources/` HTTP adapters |
| S6 | Naming | Rename `jsonl_store.py:filter()` to `filter_by()` to avoid shadowing builtin |
| S7 | CLI | Add `KeyError` guard on command dispatch dicts (`schedule_engine.py:513`, `feed.py:232`) |
| S8 | Docs | Add `SKILL.md` for `lib/`, `shared/`, and `memory/` directories |
| S9 | Constants | Extract magic numbers: `END_OF_DAY=23*60` (schedule_engine:312), `PROMOTION_THRESHOLD=3` (learn:34), `86400` (precheck:168) |
| S10 | .gitignore | Add preemptive exclusions for `*.pem`, `*.key`, `*.log`, `*.db`, `*.tmp` |
| S11 | feed.py:54–73 | `cmd_enable`/`cmd_disable` are identical — extract `_set_source_enabled(name, bool)` |
| S12 | Type annotations | Add `-> None` return types on all `cmd_*` functions project-wide |

---

## 5. Strengths

- **No circular imports** — excellent modular isolation across all 19 skills
- **Boot budget system** (AGENTS.md) — kernel context capped at <=300 lines with `boot_budget_check.py` guardian script
- **Zero security vulnerabilities** — no `shell=True`, no deserialization risks, no secrets in source, all credentials in gitignored `secrets/` directory
- **1,180 tests collected** with zero collection errors — solid testing culture
- **Consistent subprocess usage** — all calls use list-form with `capture_output=True` and `timeout=` parameters
- **State machine design** in autodidact (BOOT.md + active.json + queue.json) with clear phase transitions
- **Built-in credential scanner** in `system_health.py` — defense-in-depth
- **Well-maintained documentation** — 16 of 18 skills have SKILL.md, daily-scheduler has a full DESIGN.md
- **`jsonl_store.py` atomic writes** — temp-file + rename pattern prevents data corruption
- **Clean separation of concerns** — shared/ for cross-cutting utilities, lib/ for core constants, each skill self-contained

---

## 6. File-Level Findings

| File | LOC | Risk | Key Finding | Lines |
|---|---|---|---|---|
| `shared/jsonl_store.py` | 135 | Med | `split("-")[1]` ID parsing bug, module-level git subprocess | 63, 32 |
| `shared/task_sync.py` | 470 | **High** | Dead `label_id` param, O(N) parse loop, merge-conflict false positive | 123, 358, 153 |
| `shared/ensure_state.py` | ~100 | **High** | Zero tests, writes state files at boot | — |
| `lib/common.py` | 504 | Low | Good reference implementation for path resolution | — |
| `autodidact/scripts/gc_eval.py` | 620 | **High** | O(N) encoder passes, hardcoded `/tmp`, `or 0.1` falsy bug | 524, 591, 190 |
| `autodidact/scripts/unified_results_dashboard.py` | 390 | Med | Hardcoded date, `os.makedirs('')` crash, no schema validation | 370, 346 |
| `autodidact/tools/precheck.py` | 200 | **High** | Missing state -> RUN logic error, uncaught TypeError | 73, 115 |
| `autodidact/tools/kg_query.py` | 160 | Med | Dead or-branch, full-file memory doubling, IndexError risk | 84, 54, 69 |
| `leo-diary/scripts/diary_utils.py` | 90 | Med | Deprecated gspread API, hardcoded Sheet ID, fragile `.parent` chain | 83, 16, 15 |
| `daily-scheduler/scripts/schedule_engine.py` | 520 | Med | Variable `l` ambiguity, no `now_str` validation, dispatch KeyError | 117, 266, 513 |
| `feed-recommend/scripts/feed.py` | 235 | Low | Duplicate enable/disable, dispatch KeyError, empty string source | 54, 232, 155 |
| `system-scanner/scripts/scan.py` | 814 | **High** | Auto-push without confirmation, `sys.path.insert` in checks, `write_text is None` logic | 209, 163, 247 |
| `self-improve/scripts/learn.py` | 510 | Med | O(n^2) similarity, relative paths, dead migration code | 43, 27, 388 |
| `experiment-manager/scripts/exp_tracker.py` | 198 | Med | Zero test coverage, wraps JsonlStore with mutation ops | — |
| `paper-writing/scripts/paper_cli.py` | 363 | Low | Zero test coverage, file-locking and regex parsing | — |

---

## 7. Recommended Refactoring Priorities

| Priority | Action | Effort | Impact |
|---|---|---|---|
| **P0** | Fix `precheck.py:73` — missing state -> SKIP not RUN | 5 min | Prevents runaway autodidact cycles |
| **P0** | Fix `task_sync.py:123` — dead `label_id` branch | 10 min | Correct Todoist label handling |
| **P1** | Refactor `task_sync.py:do_pull` — single parse + batch write | 1 hr | Performance + correctness |
| **P1** | Add tests for `task_sync.py` | 2 hr | Highest-risk untested data mutation |
| **P1** | Fix `scan.py:209` — add `--dry-run` or confirmation for auto-push | 30 min | Prevent unreviewed pushes |
| **P2** | Add `pyproject.toml` with pytest config | 30 min | Eliminates all importlib test workarounds |
| **P2** | Archive ~49 orphaned autodidact scripts | 30 min | Reduce cognitive load by ~15k LOC |
| **P2** | Replace hardcoded TZ with `zoneinfo.ZoneInfo("Asia/Taipei")` | 15 min | Correctness on DST-aware systems |
| **P2** | Fix `gc_eval.py` causal patching to cache noisy baseline | 2 hr | ~32x speedup on patching experiments |
| **P3** | Add `encoding="utf-8"` to all `read_text()` calls | 20 min | Portability |
| **P3** | Add SKILL.md for lib/, shared/, memory/ | 30 min | Documentation completeness |
| **P3** | Update `diary_utils.py` to non-deprecated gspread API | 30 min | Future compatibility |
| **P3** | Consolidate `sys.path.insert` patterns into root conftest | 1 hr | Cleaner import system |

---

## Test Coverage Summary

| Skill | Source Files | Test Files | Test Cases | File Coverage |
|---|---|---|---|---|
| shared/ | 6 | 5 | 141 | 83% |
| lib/ | 1 | 1 | 55 | 100% |
| autodidact/ | 81 | 10 | 133 | 12% |
| leo-diary/ | 18 | 5 | 219 | 28% |
| daily-scheduler/ | 9 | 3 | 142 | 33% |
| feed-recommend/ | 11 | 2 | 110 | 18% |
| paper-tracker/ | 4 | 2 | 73 | 50% |
| financial-advisor/ | 3 | 2 | 78 | 67% |
| self-improve/ | 1 | 1 | 79 | 100% |
| coordinator/ | 3 | 1 | 44 | 33% |
| system-scanner/ | 1 | 1 | 35 | 100% |
| tavily-search/ | 1 | 1 | 25 | 100% |
| ask-me-anything/ | 1 | 1 | 34 | 100% |
| remember/ | 1 | 1 | 12 | 100% |
| experiment-manager/ | 1 | 0 | 0 | 0% |
| paper-writing/ | 1 | 0 | 0 | 0% |
| **TOTAL** | **~144** | **36** | **1,180** | **~25% file** |

---

## Security Audit Summary

| Check | Status | Notes |
|---|---|---|
| Secrets in source | PASS | No API keys, tokens, or passwords in .py files |
| .gitignore coverage | PASS | `secrets/`, `.env`, `.openclaw/` all excluded |
| shell=True usage | PASS | Zero instances — all subprocess uses list-form |
| Deserialization risks | PASS | No unsafe deserialization found |
| Hardcoded paths | WARN | 7 .py files contain `/Users/leonardo` absolute paths |
| Missing .gitignore entries | LOW | No preemptive `*.pem`, `*.key`, `*.log` exclusions |

---

*Generated by automated code review. All line numbers reference the `macbook-m3` branch at commit `51124fb`.*
