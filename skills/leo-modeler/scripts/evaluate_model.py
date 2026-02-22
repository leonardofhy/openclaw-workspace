#!/usr/bin/env python3
import json
from pathlib import Path

PROFILE = Path('/Users/leonardo/.openclaw/workspace/memory/leo-profile.json')
STATE = Path('/Users/leonardo/.openclaw/workspace/memory/leo-state-weekly.json')
OUT = Path('/Users/leonardo/.openclaw/workspace/memory/leo-model-eval.md')


def main():
    profile = json.loads(PROFILE.read_text(encoding='utf-8')) if PROFILE.exists() else {}
    state = json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {}

    flags = (state.get('flags') or {})
    mood = ((state.get('status') or {}).get('moodAvg'))
    energy = ((state.get('status') or {}).get('energyAvg'))

    lines = [
        '# Leo Model Evaluation',
        '',
        f"- moodAvg: {mood}",
        f"- energyAvg: {energy}",
        f"- flags: {flags}",
        '',
        '## Suggested Model Tweaks',
    ]

    if flags.get('highLateSleepRisk'):
        lines.append('- 提升「晚睡風險」權重：主動教練訊息優先給睡眠保底建議。')
    if flags.get('lowMoodRisk'):
        lines.append('- 啟用情緒守護語氣：先共情再給最小行動，不直接堆疊任務。')
    if not lines[-1].startswith('-'):
        lines.append('- 本週模型穩定，維持當前規則。')

    lines += [
        '',
        '## Notes',
        '- 這是規則評估，不是黑盒訓練。',
        '- 若使用者手動更正（例如近期行為已改善），人工修正優先。'
    ]

    OUT.write_text('\n'.join(lines), encoding='utf-8')
    print(f'Wrote {OUT}')


if __name__ == '__main__':
    main()
