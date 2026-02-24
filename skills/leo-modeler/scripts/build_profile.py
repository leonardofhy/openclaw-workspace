#!/usr/bin/env python3
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'leo-diary' / 'scripts'))
from read_diary import load_diary  # noqa

OUT = Path(__file__).parent.parent.parent.parent / 'memory' / 'leo-profile.json'

KEYWORDS = [
    '焦慮', '壓力', '拖延', '西洋棋', '會議', '報告', '運動', '媽媽', '爸爸', '實驗室', '睡', '咖啡廳'
]


def parse_sleep(t):
    t = str(t).strip().replace(':', '')
    if not t or not t.isdigit():
        return None
    t = t.zfill(4)
    h, m = int(t[:2]), int(t[2:])
    mins = h * 60 + m
    if mins < 12 * 60:
        mins += 24 * 60
    return mins


def main():
    entries = load_diary(has_diary_only=False)
    if not entries:
        raise SystemExit('No diary entries found')

    moods = [int(e['mood']) for e in entries if str(e.get('mood', '')).isdigit()]
    energies = [int(e['energy']) for e in entries if str(e.get('energy', '')).isdigit()]
    sleeps = [parse_sleep(e.get('sleep_in')) for e in entries]
    sleeps = [s for s in sleeps if s is not None]

    text = '\n'.join((e.get('diary') or '') for e in entries)
    freq = Counter({k: text.count(k) for k in KEYWORDS})

    profile = {
        'version': 'v2',
        'generatedBy': 'leo-modeler/build_profile.py',
        'entries': len(entries),
        'metrics': {
            'avgMood': round(statistics.mean(moods), 2) if moods else None,
            'avgEnergy': round(statistics.mean(energies), 2) if energies else None,
            'avgSleepInMinutes': round(statistics.mean(sleeps), 1) if sleeps else None,
            'lateSleepRatioAfter4am': round(sum(1 for s in sleeps if (s % 1440) >= 240) / len(sleeps), 3) if sleeps else None,
        },
        'keywordSignals': dict(freq.most_common()),
        'notes': [
            '此檔為自動生成的個人化建模摘要，供 leo-diary / daily coach 使用。',
            '若使用者提供更正（例如近期習慣已改變），應優先採用近期資料與人工修正。'
        ]
    }

    # Merge with existing manual profile fields if present
    if OUT.exists():
        try:
            existing = json.loads(OUT.read_text(encoding='utf-8'))
            for k, v in existing.items():
                if k not in profile:
                    profile[k] = v
        except (json.JSONDecodeError, OSError) as e:
            print(f"warn: could not merge existing profile: {e}", file=sys.stderr)

    OUT.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {OUT}')


if __name__ == '__main__':
    main()
