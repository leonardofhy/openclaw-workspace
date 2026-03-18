#!/usr/bin/env python3
"""Migrate existing HN recommender data to multi-source feed system.

Copies:
  memory/hn/seen.jsonl       → memory/feeds/seen.jsonl       (adds source field)
  memory/hn/preferences.json → memory/feeds/preferences.json
  memory/hn/feedback.jsonl   → memory/feeds/feedback.jsonl   (adds source field)

Non-destructive: original HN files are preserved.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'shared'))
from jsonl_store import find_workspace

WS = find_workspace()
HN_DIR = os.path.join(WS, 'memory', 'hn')
FEEDS_DIR = os.path.join(WS, 'memory', 'feeds')


def migrate_seen() -> int:
    """Migrate seen.jsonl, adding source='hn' to each entry."""
    src = os.path.join(HN_DIR, 'seen.jsonl')
    dst = os.path.join(FEEDS_DIR, 'seen.jsonl')

    if not os.path.exists(src):
        print(f"  SKIP: {src} not found")
        return 0

    # Collect existing IDs in destination to avoid duplicates
    existing = set()
    if os.path.exists(dst):
        with open(dst) as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    existing.add(entry.get('id', ''))
                except (json.JSONDecodeError, KeyError):
                    continue

    count = 0
    with open(src) as fin, open(dst, 'a') as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                # Convert HN ID to feed UID format
                hn_id = entry.get('id', '')
                uid = f"hn:{hn_id}"
                if uid in existing or hn_id in existing:
                    continue
                entry['id'] = uid
                entry['source'] = 'hn'
                fout.write(json.dumps(entry) + '\n')
                count += 1
            except json.JSONDecodeError:
                continue

    print(f"  seen.jsonl: migrated {count} entries")
    return count


def migrate_feedback() -> int:
    """Migrate feedback.jsonl, adding source='hn'."""
    src = os.path.join(HN_DIR, 'feedback.jsonl')
    dst = os.path.join(FEEDS_DIR, 'feedback.jsonl')

    if not os.path.exists(src):
        print(f"  SKIP: {src} not found")
        return 0

    existing = set()
    if os.path.exists(dst):
        with open(dst) as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    existing.add((entry.get('id', ''), entry.get('ts', '')))
                except (json.JSONDecodeError, KeyError):
                    continue

    count = 0
    with open(src) as fin, open(dst, 'a') as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                hn_id = entry.get('id', '')
                uid = f"hn:{hn_id}"
                ts = entry.get('ts', '')
                if (uid, ts) in existing or (hn_id, ts) in existing:
                    continue
                entry['id'] = uid
                entry['source'] = 'hn'
                fout.write(json.dumps(entry) + '\n')
                count += 1
            except json.JSONDecodeError:
                continue

    print(f"  feedback.jsonl: migrated {count} entries")
    return count


def migrate_preferences() -> bool:
    """Copy preferences.json to feeds directory."""
    src = os.path.join(HN_DIR, 'preferences.json')
    dst = os.path.join(FEEDS_DIR, 'preferences.json')

    if not os.path.exists(src):
        print(f"  SKIP: {src} not found")
        return False

    if os.path.exists(dst):
        print(f"  SKIP: {dst} already exists")
        return False

    with open(src) as f:
        data = json.load(f)

    with open(dst, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')

    print(f"  preferences.json: copied")
    return True


def main() -> None:
    print(f"Migrating HN data → multi-source feeds")
    print(f"  HN dir:    {HN_DIR}")
    print(f"  Feeds dir: {FEEDS_DIR}")
    print()

    os.makedirs(FEEDS_DIR, exist_ok=True)

    migrate_preferences()
    migrate_seen()
    migrate_feedback()

    print()
    print("Migration complete. Original HN files preserved.")


if __name__ == '__main__':
    main()
