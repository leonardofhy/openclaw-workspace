#!/usr/bin/env python3
"""Ensure required state files exist with proper defaults.

Run at boot or during heartbeat. Idempotent — only creates missing files.
Exit 0 = all OK, Exit 1 = created files (informational).

Usage:
    python3 skills/shared/ensure_state.py
"""

import json
import os
import sys

def find_workspace():
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        if os.path.isdir(os.path.join(d, '.git')):
            return d
        d = os.path.dirname(d)
    return os.path.expanduser('~/.openclaw/workspace')

DEFAULTS = {
    "memory/heartbeat-state.json": {
        "recent_alerts": {},
        "lastChecks": {
            "email": None,
            "calendar": None,
            "weather": None,
            "learnings": None,
            "boot_budget": None
        }
    },
    "memory/growth-metrics.json": {},
}

def main():
    ws = find_workspace()
    created = []

    for rel_path, default_data in DEFAULTS.items():
        full_path = os.path.join(ws, rel_path)
        if not os.path.exists(full_path):
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                json.dump(default_data, f, indent=2)
                f.write('\n')
            created.append(rel_path)
            print(f"CREATED {rel_path}")

    if created:
        print(f"Created {len(created)} missing state file(s)")
        sys.exit(1)
    else:
        print("OK all state files exist")

if __name__ == '__main__':
    main()
