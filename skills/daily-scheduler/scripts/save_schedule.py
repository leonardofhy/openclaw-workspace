#!/usr/bin/env python3
"""Save or update daily schedule to memory/schedules/YYYY-MM-DD.md.

Usage:
  python3 save_schedule.py "schedule text here"
  python3 save_schedule.py --note "決定提早休息"
  python3 save_schedule.py --done "19:40 開始研究"
"""
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR.parent.parent / 'lib'))
from common import now, today_str, WORKSPACE

SCHEDULES_DIR = WORKSPACE / 'memory' / 'schedules'
SCHEDULES_DIR.mkdir(parents=True, exist_ok=True)


def get_file() -> Path:
    return SCHEDULES_DIR / f'{today_str()}.md'


def get_version(content: str) -> int:
    """Count existing versions in file."""
    return content.count('## v')


def create_new(schedule: str, note: str = '') -> str:
    """Create a new schedule file."""
    ts = now().strftime('%H:%M')
    weekday = ['一', '二', '三', '四', '五', '六', '日'][now().weekday()]
    header = f'# 📅 {today_str()} ({weekday}) Daily Schedule\n\n'
    body = f'## v1 — 初版 ({ts})\n```\n{schedule.strip()}\n```\n'
    if note:
        body += f'> {note}\n'
    body += '\n## 實際紀錄\n'
    return header + body


def append_version(content: str, schedule: str, note: str = '') -> str:
    """Append a new version before 實際紀錄 section."""
    v = get_version(content) + 1
    ts = now().strftime('%H:%M')
    new_section = f'\n## v{v} — 更新 ({ts})\n```\n{schedule.strip()}\n```\n'
    if note:
        new_section += f'> {note}\n'

    # Insert before 實際紀錄
    if '## 實際紀錄' in content:
        idx = content.index('## 實際紀錄')
        return content[:idx] + new_section + '\n' + content[idx:]
    else:
        return content + new_section


def append_done(content: str, item: str) -> str:
    """Append a completed item to 實際紀錄."""
    ts = now().strftime('%H:%M')
    line = f'- ✅ {ts} {item}\n'
    if '## 實際紀錄' in content:
        return content.rstrip() + '\n' + line
    else:
        return content.rstrip() + '\n\n## 實際紀錄\n' + line


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Save daily schedule')
    parser.add_argument('schedule', nargs='?', help='Schedule text')
    parser.add_argument('--note', help='Add a note to the version')
    parser.add_argument('--done', help='Log a completed item')
    args = parser.parse_args()

    f = get_file()

    if args.done:
        if f.exists():
            content = f.read_text()
        else:
            content = create_new('(no schedule yet)')
        content = append_done(content, args.done)
        f.write_text(content)
        print(f'✅ Logged: {args.done}')
        return

    if not args.schedule:
        if f.exists():
            print(f.read_text())
        else:
            print(f'No schedule for {today_str()} yet.')
        return

    if f.exists():
        content = f.read_text()
        content = append_version(content, args.schedule, args.note or '')
    else:
        content = create_new(args.schedule, args.note or '')

    f.write_text(content)
    v = get_version(content)
    print(f'📅 Schedule saved: {f.name} (v{v})')


if __name__ == '__main__':
    main()
