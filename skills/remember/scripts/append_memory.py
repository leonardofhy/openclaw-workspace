#!/usr/bin/env python3
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'lib'))
from common import now as _now, WORKSPACE, MEMORY as MEMORY_DIR

def main():
    parser = argparse.ArgumentParser(description="Append a memory snippet to a markdown file.")
    parser.add_argument('--target', type=str, required=True, help="Target category/file (e.g. 'core', 'audiomatters', 'knowledge').")
    parser.add_argument('--text', type=str, required=True, help="The content to remember.")
    parser.add_argument('--tag', type=str, default=None, help="Optional tag (e.g. 'decision', 'idea').")
    
    args = parser.parse_args()
    
    # Determine file path
    # If target has no extension, assume .md and look in memory/ or memory/projects/
    target = args.target
    if not target.endswith('.md'):
        target += '.md'
        
    # Smart routing
    if target in ['MEMORY.md', 'core.md']:
        # Core memory (root of workspace or memory dir?)
        # Let's stick to memory/ dir for safety, except MEMORY.md which is special
        if target == 'MEMORY.md':
            file_path = WORKSPACE / 'MEMORY.md'
        else:
            file_path = MEMORY_DIR / target
    else:
        # Check if it looks like a project
        # Default to memory/ folder
        file_path = MEMORY_DIR / target
        
        # If user explicitly wants projects, they can pass 'projects/audiomatters'
        # But let's be smart: if the file doesn't exist in memory/, check if we should put it in projects/
        # For now, flat structure in memory/ is simplest, or allow relative paths.
        
    # Create parent dir if needed
    if not file_path.parent.exists():
        file_path.parent.mkdir(parents=True)
        
    # Timestamp
    now = _now().strftime('%Y-%m-%d %H:%M')
    
    # Format entry
    tag_str = f" `[{args.tag.upper()}]`" if args.tag else ""
    entry = f"- `{now}`{tag_str} {args.text}\n"
    
    # Write (Append)
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(entry)
        
    print(f"✅ Remembered in `{file_path.name}`: {args.text[:50]}...")

if __name__ == "__main__":
    main()
