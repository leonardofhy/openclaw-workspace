#!/usr/bin/env python3
"""Experiment tracker CLI — add, list, result, compare, queue experiments.

Usage:
    exp_tracker.py add --name NAME --task TASK --model MODEL --machine MACHINE [--params JSON] [--command CMD] [--tags t1,t2]
    exp_tracker.py list [--status STATUS] [--task TASK] [--machine MACHINE] [--limit N]
    exp_tracker.py show EXP-ID
    exp_tracker.py result EXP-ID --status STATUS [--metrics JSON] [--summary TEXT]
    exp_tracker.py compare EXP-ID1 EXP-ID2
    exp_tracker.py queue [--machine MACHINE]
    exp_tracker.py start EXP-ID
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
EXPERIMENTS_DIR = WORKSPACE / "memory" / "experiments"
EXPERIMENTS_FILE = EXPERIMENTS_DIR / "experiments.jsonl"


def load_experiments() -> list[dict]:
    if not EXPERIMENTS_FILE.exists():
        return []
    experiments = []
    for line in EXPERIMENTS_FILE.read_text().strip().splitlines():
        if line.strip():
            try:
                experiments.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"⚠️ Skipping malformed line: {line[:50]}...", file=sys.stderr)
    return experiments


def save_experiment(exp: dict):
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(EXPERIMENTS_FILE, "a") as f:
        f.write(json.dumps(exp, ensure_ascii=False) + "\n")


def rewrite_all(experiments: list[dict]):
    """Rewrite entire file (used for status updates)."""
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(EXPERIMENTS_FILE, "w") as f:
        for exp in experiments:
            f.write(json.dumps(exp, ensure_ascii=False) + "\n")


def next_id(experiments: list[dict]) -> str:
    if not experiments:
        return "EXP-001"
    max_num = 0
    for e in experiments:
        try:
            num = int(e["id"].split("-")[1])
            max_num = max(max_num, num)
        except (IndexError, ValueError):
            pass
    return f"EXP-{max_num + 1:03d}"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def cmd_add(args):
    experiments = load_experiments()
    exp_id = next_id(experiments)

    params = None
    if args.params:
        try:
            params = json.loads(args.params)
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON for --params: {args.params}", file=sys.stderr)
            sys.exit(1)

    tags = args.tags.split(",") if args.tags else []

    exp = {
        "id": exp_id,
        "name": args.name,
        "task": args.task,
        "model": args.model,
        "params": params,
        "command": args.command,
        "machine": args.machine,
        "status": "queued",
        "created": now_iso(),
        "started": None,
        "completed": None,
        "metrics": None,
        "summary": None,
        "failed_reason": None,
        "tags": tags,
        "parent_id": args.parent,
        "notes": args.notes,
    }

    save_experiment(exp)
    print(f"✅ Created {exp_id}: {args.name}")
    print(f"   Task: {args.task} | Model: {args.model} | Machine: {args.machine}")
    if args.command:
        print(f"   Command: {args.command}")


def cmd_list(args):
    experiments = load_experiments()

    # Filters
    if args.status:
        experiments = [e for e in experiments if e["status"] == args.status]
    if args.task:
        experiments = [e for e in experiments if e.get("task") == args.task]
    if args.machine:
        experiments = [e for e in experiments if e.get("machine") == args.machine]

    if args.limit:
        experiments = experiments[-args.limit:]

    if not experiments:
        print("📋 No experiments found.")
        return

    print(f"📋 Experiments ({len(experiments)}):\n")
    for e in experiments:
        status_icon = {
            "queued": "⏳", "running": "🔄", "success": "✅",
            "failed": "❌", "cancelled": "🚫"
        }.get(e["status"], "❓")
        summary = f" — {e['summary']}" if e.get("summary") else ""
        machine = f" [{e.get('machine', '?')}]" if e.get("machine") else ""
        print(f"  {status_icon} {e['id']} | {e['name']}{machine}")
        print(f"     {e['task']} · {e['model']} · {e['status']}{summary}")
        if e.get("metrics"):
            metrics_str = ", ".join(f"{k}={v}" for k, v in e["metrics"].items())
            print(f"     📊 {metrics_str}")
        print()


def cmd_show(args):
    experiments = load_experiments()
    exp = next((e for e in experiments if e["id"] == args.exp_id), None)
    if not exp:
        print(f"❌ Experiment {args.exp_id} not found", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(exp, indent=2, ensure_ascii=False))


def cmd_start(args):
    experiments = load_experiments()
    found = False
    for e in experiments:
        if e["id"] == args.exp_id:
            if e["status"] != "queued":
                print(f"⚠️ {args.exp_id} is {e['status']}, not queued", file=sys.stderr)
                sys.exit(1)
            e["status"] = "running"
            e["started"] = now_iso()
            found = True
            break
    if not found:
        print(f"❌ Experiment {args.exp_id} not found", file=sys.stderr)
        sys.exit(1)
    rewrite_all(experiments)
    print(f"🔄 Started {args.exp_id}")


def cmd_result(args):
    experiments = load_experiments()
    found = False
    for e in experiments:
        if e["id"] == args.exp_id:
            e["status"] = args.status
            e["completed"] = now_iso()
            if not e.get("started"):
                e["started"] = e["completed"]
            if args.summary:
                e["summary"] = args.summary
            if args.metrics:
                try:
                    e["metrics"] = json.loads(args.metrics)
                except json.JSONDecodeError:
                    print(f"❌ Invalid JSON for --metrics", file=sys.stderr)
                    sys.exit(1)
            if args.status == "failed" and args.summary:
                e["failed_reason"] = args.summary
            found = True
            break
    if not found:
        print(f"❌ Experiment {args.exp_id} not found", file=sys.stderr)
        sys.exit(1)
    rewrite_all(experiments)
    icon = "✅" if args.status == "success" else "❌"
    print(f"{icon} {args.exp_id} → {args.status}")
    if args.summary:
        print(f"   {args.summary}")


def cmd_compare(args):
    experiments = load_experiments()
    e1 = next((e for e in experiments if e["id"] == args.id1), None)
    e2 = next((e for e in experiments if e["id"] == args.id2), None)

    if not e1:
        print(f"❌ {args.id1} not found", file=sys.stderr)
        sys.exit(1)
    if not e2:
        print(f"❌ {args.id2} not found", file=sys.stderr)
        sys.exit(1)

    print(f"🔍 Comparing {e1['id']} vs {e2['id']}\n")
    fields = ["name", "task", "model", "machine", "status", "params", "metrics", "summary"]
    for f in fields:
        v1 = e1.get(f)
        v2 = e2.get(f)
        if isinstance(v1, dict):
            v1 = json.dumps(v1, ensure_ascii=False)
        if isinstance(v2, dict):
            v2 = json.dumps(v2, ensure_ascii=False)
        marker = "≠" if v1 != v2 else "="
        print(f"  {marker} {f}:")
        print(f"    {e1['id']}: {v1}")
        print(f"    {e2['id']}: {v2}")
        print()


def cmd_queue(args):
    experiments = load_experiments()
    queued = [e for e in experiments if e["status"] == "queued"]
    if args.machine:
        queued = [e for e in queued if e.get("machine") == args.machine]

    if not queued:
        print("📋 No experiments in queue.")
        return

    print(f"⏳ Queue ({len(queued)}):\n")
    for e in queued:
        machine = f" [{e.get('machine', '?')}]" if e.get("machine") else ""
        print(f"  {e['id']} | {e['name']}{machine}")
        print(f"     {e['task']} · {e['model']}")
        if e.get("command"):
            print(f"     $ {e['command']}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Experiment Tracker")
    sub = parser.add_subparsers(dest="cmd")

    # add
    p_add = sub.add_parser("add")
    p_add.add_argument("--name", required=True)
    p_add.add_argument("--task", required=True)
    p_add.add_argument("--model", required=True)
    p_add.add_argument("--machine", required=True, choices=["lab", "mac", "battleship"])
    p_add.add_argument("--params", help="JSON string of hyperparams")
    p_add.add_argument("--command", help="Full reproducible command")
    p_add.add_argument("--tags", help="Comma-separated tags")
    p_add.add_argument("--parent", help="Parent experiment ID")
    p_add.add_argument("--notes", help="Free-form notes")

    # list
    p_list = sub.add_parser("list")
    p_list.add_argument("--status", choices=["queued", "running", "success", "failed", "cancelled"])
    p_list.add_argument("--task")
    p_list.add_argument("--machine", choices=["lab", "mac", "battleship"])
    p_list.add_argument("--limit", type=int)

    # show
    p_show = sub.add_parser("show")
    p_show.add_argument("exp_id")

    # start
    p_start = sub.add_parser("start")
    p_start.add_argument("exp_id")

    # result
    p_result = sub.add_parser("result")
    p_result.add_argument("exp_id")
    p_result.add_argument("--status", required=True, choices=["success", "failed", "cancelled"])
    p_result.add_argument("--metrics", help="JSON string of metrics")
    p_result.add_argument("--summary", help="One-line conclusion")

    # compare
    p_compare = sub.add_parser("compare")
    p_compare.add_argument("id1")
    p_compare.add_argument("id2")

    # queue
    p_queue = sub.add_parser("queue")
    p_queue.add_argument("--machine", choices=["lab", "mac", "battleship"])

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    {
        "add": cmd_add,
        "list": cmd_list,
        "show": cmd_show,
        "start": cmd_start,
        "result": cmd_result,
        "compare": cmd_compare,
        "queue": cmd_queue,
    }[args.cmd](args)


if __name__ == "__main__":
    main()
