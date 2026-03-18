#!/usr/bin/env python3
"""Todoist Hygiene: Clean duplicates, flag stale, update heartbeat state."""
import os, json, sys, requests, argparse
from pathlib import Path
from datetime import datetime, timezone
from difflib import SequenceMatcher

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'lib'))
from common import TZ, load_todoist_token, WORKSPACE

API_BASE = 'https://api.todoist.com/api/v1'

def get_tasks(token: str) -> list[dict]:
    """Fetch all active tasks."""
    r = requests.get(f'{API_BASE}/tasks', 
                     headers={'Authorization': f'Bearer {token}'}, 
                     timeout=20)
    r.raise_for_status()
    data = r.json()
    return data.get('results', []) if isinstance(data, dict) else data

def delete_task(task_id: str, token: str) -> bool:
    """Delete a task by ID."""
    r = requests.delete(f'{API_BASE}/tasks/{task_id}',
                       headers={'Authorization': f'Bearer {token}'},
                       timeout=20)
    r.raise_for_status()
    return True

def similarity(a: str, b: str) -> float:
    """String similarity ratio (0-1)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def is_overdue(task: dict) -> bool:
    """Check if task is overdue by >3 days."""
    due = task.get('due')
    if not due:
        return False
    
    try:
        # Due can be a dict with 'date' key or just a string
        if isinstance(due, dict):
            due_date_str = due.get('date')
        else:
            due_date_str = due
        
        if not due_date_str:
            return False
        
        # Parse date (format: YYYY-MM-DD or with time)
        due_date = datetime.fromisoformat(due_date_str.split('T')[0])  # Take only date part
        due_date = due_date.replace(tzinfo=TZ)
        now = datetime.now(TZ)
        days_past = (now - due_date).days
        return days_past > 3
    except (TypeError, ValueError, AttributeError):
        return False

def main() -> None:
    parser = argparse.ArgumentParser(description='Todoist hygiene cleanup')
    parser.add_argument('--dry-run', action='store_true', help='Report without deleting')
    parser.add_argument('--similarity-threshold', type=float, default=0.80, 
                       help='Similarity threshold for duplicates (default 0.80)')
    args = parser.parse_args()
    
    token = load_todoist_token()
    
    print(f'🧹 Todoist Hygiene Cleanup (dry-run={args.dry_run})')
    print('=' * 60)
    
    tasks = get_tasks(token)
    print(f'📋 Loaded {len(tasks)} tasks')
    
    deleted_count = 0
    flagged = []
    overdue_flagged = []
    
    # ── Detect duplicates (multi-pass) ──
    # Pass 1: Find exact duplicates
    content_to_ids = {}
    for task in tasks:
        content = task['content']
        if content not in content_to_ids:
            content_to_ids[content] = []
        content_to_ids[content].append(task['id'])
    
    # If multiple tasks have same content, mark all but first for deletion
    exact_dupes_marked = set()
    for content, ids in content_to_ids.items():
        if len(ids) > 1:
            # Keep first, delete rest
            for task_id in ids[1:]:
                if task_id not in exact_dupes_marked:
                    flagged.append({
                        'id': task_id,
                        'content': content,
                        'reason': f'Exact duplicate (first: {ids[0]})',
                        'action': 'AUTO_DELETE'
                    })
                    exact_dupes_marked.add(task_id)
    
    # Pass 2: Find similar duplicates (optional, only if similarity_threshold < 1.0)
    if args.similarity_threshold < 1.0:
        for i, task1 in enumerate(tasks):
            if task1['id'] in exact_dupes_marked:
                continue
            for task2 in tasks[i+1:]:
                if task2['id'] in exact_dupes_marked:
                    continue
                sim = similarity(task1['content'], task2['content'])
                if sim >= args.similarity_threshold:
                    flagged.append({
                        'id': task2['id'],
                        'content': task2['content'],
                        'reason': f'Similar to "{task1["content"][:50]}" (score: {sim:.2f})',
                        'action': 'MAYBE_DELETE'
                    })
    
    # ── Detect overdue ──
    for task in tasks:
        if is_overdue(task):
            due = task.get('due', {})
            due_date = due.get('date') if isinstance(due, dict) else due
            overdue_flagged.append({
                'id': task['id'],
                'content': task['content'],
                'due_date': due_date,
                'reason': 'Overdue >3 days'
            })
    
    # ── Execute deletions ──
    for item in flagged:
        if item['action'] == 'AUTO_DELETE':
            try:
                if not args.dry_run:
                    delete_task(item['id'], token)
                    deleted_count += 1
                print(f"  ✂️  [{item['id']}] {item['content'][:60]}")
                print(f"      Reason: {item['reason']}")
            except Exception as e:
                print(f"  ❌ Failed to delete {item['id']}: {e}", file=sys.stderr)
    
    # ── Report flagged items ──
    if flagged or overdue_flagged:
        print(f'\n⚠️  Flagged for review:')
        for item in flagged:
            print(f"  [{item['id']}] {item['content'][:60]}")
            print(f"      {item['reason']}")
        
        for item in overdue_flagged:
            print(f"  [O] {item['content'][:60]}")
            print(f"      Due: {item['due_date']} ({item['reason']})")
    
    # ── Update heartbeat state ──
    state_path = WORKSPACE / 'memory' / 'heartbeat-state.json'
    if state_path.exists():
        with open(state_path) as f:
            state = json.load(f)
    else:
        state = {'lastChecks': {}, 'recent_alerts': {}}
    
    now = int(datetime.now(timezone.utc).timestamp())
    state['lastChecks']['todoist_cleanup'] = now
    state['todoist_hygiene_report'] = {
        'timestamp': now,
        'auto_deleted': deleted_count,
        'flagged_for_review': len(flagged),
        'overdue_count': len(overdue_flagged),
        'dry_run': args.dry_run
    }
    
    with open(state_path, 'w') as f:
        json.dump(state, f, indent=2)
    
    print(f'\n✅ Summary:')
    print(f'   Auto-deleted: {deleted_count}')
    print(f'   Flagged for review: {len(flagged)}')
    print(f'   Overdue (>3 days): {len(overdue_flagged)}')
    
    if args.dry_run:
        print(f'\n⚠️  DRY-RUN mode: no changes applied')

if __name__ == '__main__':
    main()
