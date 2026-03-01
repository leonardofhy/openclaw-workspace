#!/usr/bin/env python3
"""Autodidact v2 Garbage Collector.

Responsibilities:
1. Consolidate cycle files >48h into daily digests
2. Delete consolidated cycle files
3. Validate state file sizes (fail loudly if over caps)
4. Trim queue.json to max 25 tasks

Usage:
    python3 skills/autodidact/tools/gc.py              # dry-run (default)
    python3 skills/autodidact/tools/gc.py --apply       # actually delete/consolidate
    python3 skills/autodidact/tools/gc.py --validate    # only check caps, no changes
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from collections import defaultdict

TZ = timezone(timedelta(hours=8))

# --- Caps ---
MAX_ACTIVE_JSON_LINES = 120
MAX_QUEUE_TASKS = 25
MAX_BOOT_LINES = 200
MAX_CYCLE_FILES_RETAINED = 30  # fail loudly above this
CYCLE_MAX_AGE_HOURS = 48

def find_workspace():
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        if os.path.isdir(os.path.join(d, '.git')):
            return d
        d = os.path.dirname(d)
    return os.path.expanduser('~/.openclaw/workspace')

def count_lines(path):
    try:
        with open(path) as f:
            return sum(1 for _ in f)
    except FileNotFoundError:
        return 0

def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def save_json(path, data):
    import tempfile
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')
    os.replace(tmp, path)

def find_cycle_files(cycles_dir):
    """Find all cycle markdown files, return list of (path, date_str, mtime)."""
    results = []
    if not os.path.isdir(cycles_dir):
        return results
    for fname in os.listdir(cycles_dir):
        if fname.endswith('.md'):
            fpath = os.path.join(cycles_dir, fname)
            mtime = os.path.getmtime(fpath)
            # Extract date from filename patterns:
            #   Legacy: YYYY-MM-DD_cycleNN.md (fname[4] == '-')
            #   v2:     c-YYYYMMDD-HHMM.md   (fname[0] == 'c', date at fname[2:10])
            if len(fname) >= 10 and fname[4] == '-':
                date_str = fname[:10]  # YYYY-MM-DD
            elif fname.startswith('c-') and len(fname) >= 10:
                raw = fname[2:10]  # YYYYMMDD
                date_str = f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}" if len(raw) == 8 and raw.isdigit() else None
            else:
                date_str = None
            results.append((fpath, date_str, mtime))
    return results

def find_legacy_cycle_files(learning_dir):
    """Find cycle files in the legacy location (memory/learning/ root)."""
    results = []
    for fname in os.listdir(learning_dir):
        if fname.endswith('.md') and '_cycle' in fname and fname[:4].isdigit():
            fpath = os.path.join(learning_dir, fname)
            mtime = os.path.getmtime(fpath)
            date_str = fname[:10]
            results.append((fpath, date_str, mtime))
    return results

def main():
    parser = argparse.ArgumentParser(description='Autodidact GC')
    parser.add_argument('--apply', action='store_true', help='Actually delete/consolidate')
    parser.add_argument('--validate', action='store_true', help='Only check caps, no changes')
    args = parser.parse_args()

    if args.validate:
        args.apply = False  # validate mode = read-only

    ws = find_workspace()
    learning_dir = os.path.join(ws, 'memory', 'learning')
    cycles_dir = os.path.join(learning_dir, 'cycles')
    digests_dir = os.path.join(learning_dir, 'digests', 'daily')
    state_dir = os.path.join(learning_dir, 'state')

    issues = []
    actions = []

    # --- 1. Validate state file caps ---
    boot_path = os.path.join(ws, 'skills', 'autodidact', 'BOOT.md')
    active_path = os.path.join(state_dir, 'active.json')
    queue_path = os.path.join(state_dir, 'queue.json')

    boot_lines = count_lines(boot_path)
    active_lines = count_lines(active_path)
    queue_lines = count_lines(queue_path)

    if boot_lines > MAX_BOOT_LINES:
        issues.append(f"🔴 BOOT.md: {boot_lines} lines (cap: {MAX_BOOT_LINES})")
    if active_lines > MAX_ACTIVE_JSON_LINES:
        issues.append(f"🔴 active.json: {active_lines} lines (cap: {MAX_ACTIVE_JSON_LINES})")

    # --- 2. Trim queue.json ---
    queue_data = load_json(queue_path)
    if queue_data:
        tasks = queue_data.get('tasks', [])
        if len(tasks) > MAX_QUEUE_TASKS:
            # Remove oldest completed tasks first, then oldest low-priority
            completed = [t for t in tasks if t.get('status') == 'done']
            active = [t for t in tasks if t.get('status') != 'done']
            if len(active) > MAX_QUEUE_TASKS:
                active.sort(key=lambda t: t.get('priority', 99))
                overflow = active[MAX_QUEUE_TASKS:]
                active = active[:MAX_QUEUE_TASKS]
                actions.append(f"Trim queue: remove {len(completed)} done + {len(overflow)} low-priority tasks")
                if args.apply:
                    queue_data['tasks'] = active
                    save_json(queue_path, queue_data)
            else:
                actions.append(f"Trim queue: remove {len(completed)} done tasks")
                if args.apply:
                    queue_data['tasks'] = active
                    save_json(queue_path, queue_data)

    # --- 3. Find cycle files to consolidate ---
    now = datetime.now(TZ)
    cutoff = now - timedelta(hours=CYCLE_MAX_AGE_HOURS)
    cutoff_ts = cutoff.timestamp()

    # Check both legacy location and new cycles/ dir
    all_cycles = find_cycle_files(cycles_dir) + find_legacy_cycle_files(learning_dir)

    # Use filename date (not mtime) to determine age — git operations update mtime
    today_str = now.strftime('%Y-%m-%d')
    yesterday = (now - timedelta(hours=CYCLE_MAX_AGE_HOURS)).strftime('%Y-%m-%d')
    recent_dates = {today_str, yesterday}
    # Also keep files with dates within 48h window
    for i in range(3):  # today, yesterday, day before yesterday
        d = (now - timedelta(days=i)).strftime('%Y-%m-%d')
        recent_dates.add(d)

    old_cycles = [(p, d, m) for p, d, m in all_cycles if d and d not in recent_dates]
    recent_cycles = [(p, d, m) for p, d, m in all_cycles if not d or d in recent_dates]

    if len(all_cycles) > MAX_CYCLE_FILES_RETAINED:
        issues.append(f"⚠️ {len(all_cycles)} cycle files (cap: {MAX_CYCLE_FILES_RETAINED})")

    # Group old cycles by date for digest
    by_date = defaultdict(list)
    for path, date_str, mtime in old_cycles:
        if date_str:
            by_date[date_str].append(path)

    handled_legacy_digests = set()
    for date_str, paths in sorted(by_date.items()):
        digest_path = os.path.join(digests_dir, f'{date_str}.md')
        legacy_digest = os.path.join(learning_dir, f'{date_str}-digest.md')

        if os.path.exists(digest_path):
            actions.append(f"Delete {len(paths)} cycle files for {date_str} (digest exists)")
            if args.apply:
                for p in paths:
                    os.remove(p)
                    print(f"  Deleted: {os.path.basename(p)}", file=sys.stderr)
        elif os.path.exists(legacy_digest):
            handled_legacy_digests.add(date_str)
            actions.append(f"Move {date_str}-digest.md → digests/daily/ + delete {len(paths)} cycle files")
            if args.apply:
                os.makedirs(digests_dir, exist_ok=True)
                os.rename(legacy_digest, digest_path)
                for p in paths:
                    os.remove(p)
                    print(f"  Deleted: {os.path.basename(p)}", file=sys.stderr)
        else:
            actions.append(f"⚠️ {len(paths)} cycle files for {date_str} but NO digest — need LLM to consolidate")

    # --- 4. Move remaining legacy digests not already handled above ---
    for fname in os.listdir(learning_dir):
        if fname.endswith('-digest.md') and fname[:4].isdigit():
            date_str = fname.replace('-digest.md', '')
            if date_str in handled_legacy_digests:
                continue
            legacy_path = os.path.join(learning_dir, fname)
            new_path = os.path.join(digests_dir, f'{date_str}.md')
            if not os.path.exists(new_path):
                actions.append(f"Move legacy digest: {fname} → digests/daily/{date_str}.md")
                if args.apply:
                    os.makedirs(digests_dir, exist_ok=True)
                    os.rename(legacy_path, new_path)

    # --- 5. Update active.json last_gc ---
    if args.apply:
        active_data = load_json(active_path)
        if active_data:
            active_data['last_gc'] = now.isoformat()
            save_json(active_path, active_data)

    # --- Report ---
    print(f"\n{'=' * 50}")
    print(f"Autodidact GC Report ({'DRY RUN' if not args.apply else 'APPLIED'})")
    print(f"{'=' * 50}")
    print(f"Total cycle files: {len(all_cycles)} (old: {len(old_cycles)}, recent: {len(recent_cycles)})")
    print(f"Boot set: BOOT.md={boot_lines}L active.json={active_lines}L queue={queue_lines}L")

    if issues:
        print(f"\n🔴 ISSUES ({len(issues)}):")
        for i in issues:
            print(f"  {i}")

    if actions:
        print(f"\n📋 ACTIONS ({len(actions)}):")
        for a in actions:
            print(f"  {a}")
    else:
        print("\n✅ Nothing to clean up.")

    if issues:
        # Write GC_ALERT if critical
        alert_path = os.path.join(learning_dir, 'GC_ALERT.md')
        if args.apply:
            with open(alert_path, 'w') as f:
                f.write(f"# GC Alert — {now.strftime('%Y-%m-%d %H:%M')}\n\n")
                for i in issues:
                    f.write(f"- {i}\n")
            print(f"\n⚠️ GC_ALERT.md written — next cycle must prioritize cleanup")

    return 1 if issues else 0

if __name__ == '__main__':
    sys.exit(main())
