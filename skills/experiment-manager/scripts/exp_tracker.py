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

# Shared module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "shared"))
from jsonl_store import JsonlStore

store = JsonlStore("memory/experiments/experiments.jsonl", prefix="EXP")


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def parse_json_arg(val: str, name: str) -> dict:
    try:
        return json.loads(val)
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON for --{name}: {val}", file=sys.stderr)
        sys.exit(1)


def cmd_add(args):
    params = parse_json_arg(args.params, "params") if args.params else None
    tags = args.tags.split(",") if args.tags else []

    exp = store.append({
        "name": args.name, "task": args.task, "model": args.model,
        "params": params, "command": args.command, "machine": args.machine,
        "status": "queued", "created": now_iso(),
        "started": None, "completed": None, "metrics": None,
        "summary": None, "failed_reason": None,
        "tags": tags, "parent_id": args.parent, "notes": args.notes,
    })
    print(f"✅ Created {exp['id']}: {args.name}")
    print(f"   Task: {args.task} | Model: {args.model} | Machine: {args.machine}")
    if args.command:
        print(f"   Command: {args.command}")


def cmd_list(args):
    experiments = store.load()
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
        icon = {"queued": "⏳", "running": "🔄", "success": "✅", "failed": "❌", "cancelled": "🚫"}.get(e["status"], "❓")
        summary = f" — {e['summary']}" if e.get("summary") else ""
        machine = f" [{e.get('machine', '?')}]" if e.get("machine") else ""
        print(f"  {icon} {e['id']} | {e['name']}{machine}")
        print(f"     {e['task']} · {e['model']} · {e['status']}{summary}")
        if e.get("metrics"):
            print(f"     📊 {', '.join(f'{k}={v}' for k, v in e['metrics'].items())}")
        print()


def cmd_show(args):
    exp = store.find(args.exp_id)
    if not exp:
        print(f"❌ {args.exp_id} not found", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(exp, indent=2, ensure_ascii=False))


def cmd_start(args):
    exp = store.find(args.exp_id)
    if not exp:
        print(f"❌ {args.exp_id} not found", file=sys.stderr)
        sys.exit(1)
    if exp["status"] != "queued":
        print(f"⚠️ {args.exp_id} is {exp['status']}, not queued", file=sys.stderr)
        sys.exit(1)
    store.update(args.exp_id, {"status": "running", "started": now_iso()})
    print(f"🔄 Started {args.exp_id}")


def cmd_result(args):
    exp = store.find(args.exp_id)
    if not exp:
        print(f"❌ {args.exp_id} not found", file=sys.stderr)
        sys.exit(1)

    updates = {"status": args.status, "completed": now_iso()}
    if not exp.get("started"):
        updates["started"] = updates["completed"]
    if args.summary:
        updates["summary"] = args.summary
    if args.metrics:
        updates["metrics"] = parse_json_arg(args.metrics, "metrics")
    if args.status == "failed" and args.summary:
        updates["failed_reason"] = args.summary

    store.update(args.exp_id, updates)
    icon = "✅" if args.status == "success" else "❌"
    print(f"{icon} {args.exp_id} → {args.status}")
    if args.summary:
        print(f"   {args.summary}")


def cmd_compare(args):
    e1, e2 = store.find(args.id1), store.find(args.id2)
    for eid, e in [(args.id1, e1), (args.id2, e2)]:
        if not e:
            print(f"❌ {eid} not found", file=sys.stderr)
            sys.exit(1)

    print(f"🔍 Comparing {e1['id']} vs {e2['id']}\n")
    for f in ["name", "task", "model", "machine", "status", "params", "metrics", "summary"]:
        v1, v2 = e1.get(f), e2.get(f)
        if isinstance(v1, dict): v1 = json.dumps(v1, ensure_ascii=False)
        if isinstance(v2, dict): v2 = json.dumps(v2, ensure_ascii=False)
        print(f"  {'≠' if v1 != v2 else '='} {f}:")
        print(f"    {e1['id']}: {v1}")
        print(f"    {e2['id']}: {v2}\n")


def cmd_queue(args):
    queued = store.filter(status="queued")
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

    p = sub.add_parser("add")
    p.add_argument("--name", required=True); p.add_argument("--task", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--machine", required=True, choices=["lab", "mac", "battleship"])
    p.add_argument("--params"); p.add_argument("--command"); p.add_argument("--tags")
    p.add_argument("--parent"); p.add_argument("--notes")

    p = sub.add_parser("list")
    p.add_argument("--status", choices=["queued", "running", "success", "failed", "cancelled"])
    p.add_argument("--task"); p.add_argument("--machine", choices=["lab", "mac", "battleship"])
    p.add_argument("--limit", type=int)

    p = sub.add_parser("show"); p.add_argument("exp_id")
    p = sub.add_parser("start"); p.add_argument("exp_id")

    p = sub.add_parser("result"); p.add_argument("exp_id")
    p.add_argument("--status", required=True, choices=["success", "failed", "cancelled"])
    p.add_argument("--metrics"); p.add_argument("--summary")

    p = sub.add_parser("compare"); p.add_argument("id1"); p.add_argument("id2")
    p = sub.add_parser("queue"); p.add_argument("--machine", choices=["lab", "mac", "battleship"])

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help(); sys.exit(1)

    {"add": cmd_add, "list": cmd_list, "show": cmd_show, "start": cmd_start,
     "result": cmd_result, "compare": cmd_compare, "queue": cmd_queue}[args.cmd](args)


if __name__ == "__main__":
    main()
