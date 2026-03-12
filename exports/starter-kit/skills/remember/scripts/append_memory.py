#!/usr/bin/env python3
import argparse
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Find workspace
def find_workspace():
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        if os.path.isdir(os.path.join(d, '.git')):
            return Path(d)
        d = os.path.dirname(d)
    return Path.home() / '.openclaw' / 'workspace'

WORKSPACE = find_workspace()
MEMORY_DIR = WORKSPACE / 'memory'

# Default timezone — change to match your location
TZ = timezone(timedelta(hours=8), name='Asia/Taipei')

def now():
    return datetime.now(TZ)

def main():
    parser = argparse.ArgumentParser(description="Append a memory snippet to a markdown file.")
    parser.add_argument('--target', type=str, required=True, help="Target category/file (e.g. 'core', 'knowledge', 'projects/my-project').")
    parser.add_argument('--text', type=str, required=True, help="The content to remember.")
    parser.add_argument('--tag', type=str, default=None, help="Optional tag (e.g. 'decision', 'idea').")
    
    args = parser.parse_args()
    
    target = args.target
    if not target.endswith('.md'):
        target += '.md'
        
    # Smart routing
    if target == 'MEMORY.md':
        file_path = WORKSPACE / 'MEMORY.md'
    else:
        file_path = MEMORY_DIR / target
        
    # Create parent dir if needed
    if not file_path.parent.exists():
        file_path.parent.mkdir(parents=True)
        
    # Timestamp
    timestamp = now().strftime('%Y-%m-%d %H:%M')
    
    # Format entry
    tag_str = f" `[{args.tag.upper()}]`" if args.tag else ""
    entry = f"- `{timestamp}`{tag_str} {args.text}\n"
    
    # Append
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(entry)
        
    print(f"✅ Remembered in `{file_path.name}`: {args.text[:50]}...")

if __name__ == "__main__":
    main()
