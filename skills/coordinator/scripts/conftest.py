"""Ensure correct module resolution for coordinator tests.

When running all tests in batch, modules like 'orchestrator', 'common',
and 'jsonl_store' must resolve to the coordinator's own copies, not to
identically-named modules in other skill directories.
"""
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SHARED = _HERE.parent.parent / "shared"
_LIB = _HERE.parent.parent / "lib"

for _p in [str(_HERE), str(_SHARED), str(_LIB)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
