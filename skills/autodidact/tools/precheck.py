#!/usr/bin/env python3
"""Autodidact v2 precheck — decide if an LLM cycle should run.

Reads only state files (cheap, no LLM needed).
Outputs: RUN or SKIP + 1-line reason to stdout.

Usage:
    python3 skills/autodidact/tools/precheck.py
"""

import json
import sys
import os
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))  # Asia/Taipei

def find_workspace():
    """Walk up from script location to find .git root."""
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        if os.path.isdir(os.path.join(d, '.git')):
            return d
        d = os.path.dirname(d)
    return os.path.expanduser('~/.openclaw/workspace')

def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"WARN: {path}: {e}", file=sys.stderr)
        return None

def main():
    ws = find_workspace()
    state_dir = os.path.join(ws, 'memory', 'learning', 'state')

    active = load_json(os.path.join(state_dir, 'active.json'))
    queue = load_json(os.path.join(state_dir, 'queue.json'))
    blockers = load_json(os.path.join(state_dir, 'blockers.json'))

    if not active or not queue:
        print("RUN state files missing or corrupt — run to self-heal")
        return

    now = datetime.now(TZ)

    # --- Check 1: Any READY tasks in queue? ---
    ready_tasks = [t for t in queue.get('tasks', []) if t.get('status') == 'ready']
    if ready_tasks:
        print(f"RUN {len(ready_tasks)} READY tasks in queue (top: {ready_tasks[0]['id']} {ready_tasks[0]['title'][:50]})")
        return

    # --- Check 2: Blocker cooldown expired? (time to reassess) ---
    if blockers and blockers.get('blocked'):
        unblock_at = blockers.get('unblock_check_at')
        if unblock_at:
            try:
                check_time = datetime.fromisoformat(unblock_at)
                if now >= check_time:
                    print("RUN blocker cooldown expired — reassess blockers")
                    return
            except ValueError:
                pass
        # Note: fallback tasks are already caught by Check 1 (READY tasks).
        # No separate fallback check needed here.

    # --- Check 3: New news digest? ---
    news_dir = os.path.join(ws, 'memory', 'learning', 'news')
    if os.path.isdir(news_dir):
        today = now.strftime('%Y-%m-%d')
        today_digest = os.path.join(news_dir, f'{today}.md')
        if os.path.exists(today_digest):
            # Check if any queue tasks reference this digest (already processed)
            news_tasks = [t for t in queue.get('tasks', [])
                          if t.get('title', '').startswith('News:') and t.get('created') == today]
            if not news_tasks:
                print(f"RUN new news digest found for {today}")
                return

    # --- Check 4: GC overdue? ---
    last_gc = active.get('last_gc')
    if not last_gc:
        # Never GC'd — check if there are cycle files to clean
        cycles_dir = os.path.join(ws, 'memory', 'learning', 'cycles')
        if os.path.isdir(cycles_dir) and len(os.listdir(cycles_dir)) > 10:
            print("RUN GC overdue — cycle files accumulating")
            return
    else:
        try:
            gc_time = datetime.fromisoformat(last_gc)
            if (now - gc_time).total_seconds() > 86400:  # >24h
                print("RUN GC overdue (>24h since last)")
                return
        except ValueError:
            pass

    # --- Check 5: Budget reset needed? ---
    reset_date = active.get('budgets', {}).get('budget_reset_date')
    if reset_date and reset_date != now.strftime('%Y-%m-%d'):
        print("RUN new day — budget reset needed")
        return

    # --- Check 6: Forced run every 6 hours (anti-false-negative) ---
    last_cycle = active.get('last_cycle', {})
    last_id = last_cycle.get('id', '')
    if last_id:
        # Parse timestamp from cycle_id format: c-YYYYMMDD-HHMM
        try:
            parts = last_id.split('-')
            if len(parts) >= 3:
                date_str = parts[1]
                time_str = parts[2]
                last_time = datetime(
                    int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]),
                    int(time_str[:2]), int(time_str[2:4]),
                    tzinfo=TZ
                )
                hours_since = (now - last_time).total_seconds() / 3600
                if hours_since >= 6:
                    print(f"RUN forced run — {hours_since:.1f}h since last cycle")
                    return
        except (ValueError, IndexError):
            pass

    # --- All checks passed: SKIP ---
    print("SKIP no READY tasks, blockers active with cooldown, GC current")

if __name__ == '__main__':
    main()
