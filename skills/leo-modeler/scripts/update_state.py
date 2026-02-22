#!/usr/bin/env python3
import json
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'leo-diary' / 'scripts'))
from read_diary import load_diary  # noqa

OUT = Path(__file__).parent.parent.parent.parent / 'memory' / 'leo-state-weekly.json'


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
    today = date.today()
    start = (today - timedelta(days=14)).isoformat()
    entries = load_diary(start_date=start, has_diary_only=False)

    moods = [int(e['mood']) for e in entries if str(e.get('mood', '')).isdigit()]
    energies = [int(e['energy']) for e in entries if str(e.get('energy', '')).isdigit()]
    sleeps = [parse_sleep(e.get('sleep_in')) for e in entries]
    sleeps = [s for s in sleeps if s is not None]

    state = {
        'weekOf': today.isoformat(),
        'generatedBy': 'leo-modeler/update_state.py',
        'windowDays': 14,
        'entries': len(entries),
        'status': {
            'moodAvg': round(statistics.mean(moods), 2) if moods else None,
            'energyAvg': round(statistics.mean(energies), 2) if energies else None,
            'sleep': {
                'avgSleepInMinutes': round(statistics.mean(sleeps), 1) if sleeps else None,
                'lateAfter4amDays': sum(1 for s in sleeps if (s % 1440) >= 240),
                'totalSleepRecords': len(sleeps)
            }
        },
        'flags': {
            'highLateSleepRisk': bool(sleeps and (sum(1 for s in sleeps if (s % 1440) >= 240) / len(sleeps)) > 0.5),
            'lowMoodRisk': bool(moods and min(moods) <= 3)
        }
    }

    OUT.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {OUT}')


if __name__ == '__main__':
    main()
