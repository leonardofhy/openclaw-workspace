#!/usr/bin/env python3
"""Create a cross-bot task handoff from a one-line instruction.

Examples:
  python3 skills/coordinator/scripts/one_liner_handoff.py \
    "移交給lab：HN雙時段推薦，每天13:30與20:30，各3-5篇，含why+link+action"

  python3 skills/coordinator/scripts/one_liner_handoff.py \
    "handoff to mac: merge lab-desktop changes and publish sync report"
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "shared"))
from jsonl_store import find_workspace


WORKSPACE = find_workspace()
TASK_BOARD = WORKSPACE / "memory" / "task-board.md"


def infer_target(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["lab", "移交給lab", "給lab", "to lab"]):
        return "L"
    if any(k in t for k in ["mac", "macbook", "移交給mac", "給mac", "to mac"]):
        return "M"
    raise ValueError("Could not infer target. Include 'lab' or 'mac' in your sentence.")


def parse_priority(text: str) -> str:
    t = text.upper()
    for p in ["P0", "P1", "P2", "P3"]:
        if p in t:
            return p
    return "P1"


def parse_title_and_desc(text: str) -> tuple[str, str]:
    # Prefer content after ':' or '：'
    m = re.split(r"[:：]", text, maxsplit=1)
    body = m[1].strip() if len(m) == 2 else text.strip()

    # Title: first phrase before comma/，/; up to 28 chars
    title = re.split(r"[,，;；]", body, maxsplit=1)[0].strip()
    title = re.sub(r"\s+", " ", title)
    if len(title) > 28:
        title = title[:28].rstrip() + "…"
    if not title:
        title = "One-line handoff task"

    desc = body
    return title, desc


def next_task_id(prefix: str, text: str) -> str:
    nums = []
    for m in re.finditer(rf"^### {prefix}-(\d+)\b", text, flags=re.MULTILINE):
        nums.append(int(m.group(1)))
    n = max(nums, default=0) + 1
    return f"{prefix}-{n:02d}"


def insert_active_task(task_block: str, text: str) -> str:
    marker_active = "## ACTIVE"
    marker_waiting = "## WAITING"

    i = text.find(marker_active)
    j = text.find(marker_waiting)
    if i == -1 or j == -1 or j <= i:
        raise ValueError("task-board.md format unexpected (ACTIVE/WAITING not found).")

    before = text[:j].rstrip() + "\n\n"
    after = text[j:]
    return before + task_block + "\n" + after


def main() -> int:
    parser = argparse.ArgumentParser(description="One-line Lab/Mac handoff to task-board")
    parser.add_argument("text", help="One-line handoff instruction")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing task-board")
    args = parser.parse_args()

    if not TASK_BOARD.exists():
        raise SystemExit(f"task-board not found: {TASK_BOARD}")

    raw = TASK_BOARD.read_text(encoding="utf-8")
    prefix = infer_target(args.text)
    task_id = next_task_id(prefix, raw)
    title, desc = parse_title_and_desc(args.text)
    priority = parse_priority(args.text)

    owner = "Lab" if prefix == "L" else "MacBook"
    today = datetime.now().strftime("%Y-%m-%d")

    block = (
        f"### {task_id} | {title}\n"
        f"- **owner**: {owner}\n"
        f"- **priority**: {priority}\n"
        f"- **created**: {today}\n"
        f"- **last_touched**: {today}\n"
        f"- **描述**: {desc}\n"
        f"- **next_action**: Acknowledge handoff and execute first concrete step\n"
    )

    if args.dry_run:
        print(f"DRY-RUN {task_id} ({owner})")
        print(block)
        return 0

    updated = insert_active_task(block, raw)
    TASK_BOARD.write_text(updated, encoding="utf-8")

    print(f"CREATED {task_id} ({owner})")
    print(block)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
