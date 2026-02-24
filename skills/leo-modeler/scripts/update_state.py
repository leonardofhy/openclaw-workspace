#!/usr/bin/env python3
import json
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'leo-diary' / 'scripts'))
from read_diary import load_diary  # noqa
from sleep_calc import sleep_duration_minutes  # noqa

OUT = Path(__file__).parent.parent.parent.parent / 'memory' / 'leo-state-weekly.json'


def parse_sleep_onset(t):
    """Return sleep onset as minutes from noon (36h clock).

    Values < 1440 mean slept before midnight; >= 1440 mean after midnight.
    Used internally for late-sleep detection only — NOT a duration.
    e.g. 02:00 → 120 + 1440 = 1560, 23:30 → 1410
    """
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

    # Sleep onset times (for late-sleep detection)
    sleep_onsets = [parse_sleep_onset(e.get('sleep_in')) for e in entries]
    sleep_onsets = [s for s in sleep_onsets if s is not None]

    # Actual sleep durations in minutes (sleep_in → wake_up)
    durations = [
        sleep_duration_minutes(e.get('sleep_in'), e.get('wake_up'))
        for e in entries
    ]
    durations = [d for d in durations if d is not None]

    state = {
        'weekOf': today.isoformat(),
        'generatedBy': 'leo-modeler/update_state.py',
        'windowDays': 14,
        'entries': len(entries),
        'status': {
            'moodAvg': round(statistics.mean(moods), 2) if moods else None,
            'energyAvg': round(statistics.mean(energies), 2) if energies else None,
            'sleep': {
                # avgSleepOnsetNormalized: sleep-in time in "36h clock" minutes.
                # e.g. 1560 = 02:00 AM next day. Use for late-sleep detection only.
                'avgSleepOnsetNormalized': round(statistics.mean(sleep_onsets), 1) if sleep_onsets else None,
                # avgSleepDurationMinutes: actual duration from sleep_in to wake_up.
                # e.g. 420 = 7 hours. This is the real sleep quality metric.
                'avgSleepDurationMinutes': round(statistics.mean(durations), 1) if durations else None,
                'lateAfter4amDays': sum(1 for s in sleep_onsets if (s % 1440) >= 240),
                'totalSleepRecords': len(sleep_onsets)
            }
        },
        'flags': {
            'highLateSleepRisk': bool(sleep_onsets and (
                sum(1 for s in sleep_onsets if (s % 1440) >= 240) / len(sleep_onsets)
            ) > 0.5),
            'lowMoodRisk': bool(moods and min(moods) <= 3)
        }
    }

    OUT.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {OUT}')


if __name__ == '__main__':
    main()
