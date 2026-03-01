#!/usr/bin/env python3
"""Autodidact v2 queue operations.

Manage the task queue (memory/learning/state/queue.json).

Usage:
    python3 queue_ops.py list                         # show all tasks
    python3 queue_ops.py list --status ready           # filter by status
    python3 queue_ops.py list --track T3               # filter by track
    python3 queue_ops.py add --title "..." --type build --track T3 --priority 2
    python3 queue_ops.py complete Q005                  # mark done
    python3 queue_ops.py block Q005 --reason "..."      # mark blocked
    python3 queue_ops.py unblock Q005                   # mark ready
    python3 queue_ops.py ready                          # show READY tasks sorted by priority
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))
MAX_TASKS = 25

def find_workspace():
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        if os.path.isdir(os.path.join(d, '.git')):
            return d
        d = os.path.dirname(d)
    return os.path.expanduser('~/.openclaw/workspace')

def queue_path():
    return os.path.join(find_workspace(), 'memory', 'learning', 'state', 'queue.json')

def load_queue():
    try:
        with open(queue_path()) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"version": 1, "max_tasks": MAX_TASKS, "tasks": []}

def save_queue(data):
    p = queue_path()
    tmp = p + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')
    os.replace(tmp, p)

def next_id(tasks):
    max_num = 0
    for t in tasks:
        tid = t.get('id', '')
        if tid.startswith('Q') and tid[1:].isdigit():
            max_num = max(max_num, int(tid[1:]))
    return f"Q{max_num + 1:03d}"

def cmd_list(args, data):
    tasks = data.get('tasks', [])
    if args.status:
        tasks = [t for t in tasks if t.get('status') == args.status]
    if args.track:
        tasks = [t for t in tasks if t.get('track') == args.track]

    tasks.sort(key=lambda t: (t.get('priority', 99), t.get('id', '')))

    if not tasks:
        print("No tasks matching filter.")
        return

    for t in tasks:
        status_icon = {'ready': '🟢', 'blocked': '🔴', 'in_progress': '🟡', 'done': '✅'}.get(t['status'], '⚪')
        blocked = f" [blocked: {t['blocked_by']}]" if t.get('blocked_by') else ""
        print(f"  {status_icon} {t['id']} P{t.get('priority', '?')} [{t.get('track', '?')}] {t['title']}{blocked}")

    print(f"\nTotal: {len(tasks)} | Ready: {sum(1 for t in tasks if t['status'] == 'ready')} | Blocked: {sum(1 for t in tasks if t['status'] == 'blocked')}")

def cmd_ready(args, data):
    args.status = 'ready'
    args.track = None
    cmd_list(args, data)

def cmd_add(args, data):
    tasks = data.get('tasks', [])
    if len(tasks) >= MAX_TASKS:
        print(f"ERROR: Queue full ({len(tasks)}/{MAX_TASKS}). Complete or remove tasks first.", file=sys.stderr)
        sys.exit(1)

    new_task = {
        "id": next_id(tasks),
        "type": args.type,
        "track": args.track,
        "title": args.title,
        "status": "ready",
        "priority": args.priority,
        "blocked_by": None,
        "definition_of_done": args.dod or "",
        "created": datetime.now(TZ).strftime('%Y-%m-%d'),
        "due": args.due
    }
    tasks.append(new_task)
    data['tasks'] = tasks
    save_queue(data)
    print(f"Added: {new_task['id']} — {new_task['title']}")

def cmd_complete(args, data):
    for t in data.get('tasks', []):
        if t['id'] == args.task_id:
            t['status'] = 'done'
            t['completed'] = datetime.now(TZ).strftime('%Y-%m-%d')
            save_queue(data)
            print(f"Completed: {t['id']} — {t['title']}")
            return
    print(f"ERROR: Task {args.task_id} not found", file=sys.stderr)
    sys.exit(1)

def cmd_block(args, data):
    for t in data.get('tasks', []):
        if t['id'] == args.task_id:
            t['status'] = 'blocked'
            t['blocked_by'] = args.reason or 'unspecified'
            save_queue(data)
            print(f"Blocked: {t['id']} — {t['title']}")
            return
    print(f"ERROR: Task {args.task_id} not found", file=sys.stderr)
    sys.exit(1)

def cmd_unblock(args, data):
    for t in data.get('tasks', []):
        if t['id'] == args.task_id:
            t['status'] = 'ready'
            t['blocked_by'] = None
            save_queue(data)
            print(f"Unblocked: {t['id']} — {t['title']}")
            return
    print(f"ERROR: Task {args.task_id} not found", file=sys.stderr)
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Autodidact queue operations')
    sub = parser.add_subparsers(dest='command')

    # list
    p_list = sub.add_parser('list', help='List tasks')
    p_list.add_argument('--status', help='Filter by status')
    p_list.add_argument('--track', help='Filter by track')

    # ready
    sub.add_parser('ready', help='Show READY tasks')

    # add
    p_add = sub.add_parser('add', help='Add a task')
    p_add.add_argument('--title', required=True)
    p_add.add_argument('--type', default='build', choices=['build', 'read', 'experiment', 'design', 'write'])
    p_add.add_argument('--track', default='T3')
    p_add.add_argument('--priority', type=int, default=3)
    p_add.add_argument('--dod', help='Definition of done')
    p_add.add_argument('--due', help='Due date YYYY-MM-DD')

    # complete
    p_complete = sub.add_parser('complete', help='Mark task done')
    p_complete.add_argument('task_id')

    # block
    p_block = sub.add_parser('block', help='Mark task blocked')
    p_block.add_argument('task_id')
    p_block.add_argument('--reason', default='')

    # unblock
    p_unblock = sub.add_parser('unblock', help='Mark task ready')
    p_unblock.add_argument('task_id')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    data = load_queue()

    if args.command == 'list':
        cmd_list(args, data)
    elif args.command == 'ready':
        cmd_ready(args, data)
    elif args.command == 'add':
        cmd_add(args, data)
    elif args.command == 'complete':
        cmd_complete(args, data)
    elif args.command == 'block':
        cmd_block(args, data)
    elif args.command == 'unblock':
        cmd_unblock(args, data)

if __name__ == '__main__':
    main()
