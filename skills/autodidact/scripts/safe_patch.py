#!/usr/bin/env python3
"""Race-safe exact patch utility for text files.

Use this when multiple cron/session writers may touch the same file (e.g. SKILL.md).
Features:
- process lock (fcntl) with timeout
- read-latest-before-patch
- exact-match replace (single occurrence by default)
- atomic write (tempfile + os.replace)
- post-write verification strings

Example:
  python3 skills/autodidact/scripts/safe_patch.py \
    --file skills/autodidact/SKILL.md \
    --find-file /tmp/old.txt \
    --replace-file /tmp/new.txt \
    --verify "Dead-zone guard exception" \
    --verify "Q33"
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import tempfile
import time
from pathlib import Path


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _atomic_write(path: Path, content: str) -> None:
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="Target text file to patch")
    ap.add_argument("--find-file", required=True, help="File containing exact old text")
    ap.add_argument("--replace-file", required=True, help="File containing new text")
    ap.add_argument("--lock-file", default=None, help="Custom lock file path")
    ap.add_argument("--timeout-sec", type=float, default=20.0)
    ap.add_argument("--verify", action="append", default=[], help="String that must exist after write (repeatable)")
    args = ap.parse_args()

    target = Path(args.file).resolve()
    old_text = _read_text(Path(args.find_file).resolve())
    new_text = _read_text(Path(args.replace_file).resolve())

    if old_text == new_text:
        print(json.dumps({"ok": True, "changed": False, "reason": "no-op"}, ensure_ascii=False))
        return 0

    lock_path = Path(args.lock_file).resolve() if args.lock_file else target.with_suffix(target.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    start = time.time()
    with open(lock_path, "a+", encoding="utf-8") as lockf:
        while True:
            try:
                fcntl.flock(lockf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.time() - start > args.timeout_sec:
                    print(json.dumps({"ok": False, "error": "lock-timeout", "file": str(target)}, ensure_ascii=False))
                    return 3
                time.sleep(0.25)

        try:
            cur = _read_text(target)
            if old_text not in cur:
                print(json.dumps({
                    "ok": False,
                    "error": "old-text-not-found",
                    "file": str(target),
                }, ensure_ascii=False))
                return 2

            patched = cur.replace(old_text, new_text, 1)
            _atomic_write(target, patched)

            written = _read_text(target)
            missing = [s for s in args.verify if s not in written]
            if missing:
                print(json.dumps({"ok": False, "error": "verify-failed", "missing": missing}, ensure_ascii=False))
                return 4

            print(json.dumps({
                "ok": True,
                "changed": True,
                "file": str(target),
                "verifications": len(args.verify),
            }, ensure_ascii=False))
            return 0
        finally:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)


if __name__ == "__main__":
    raise SystemExit(main())
