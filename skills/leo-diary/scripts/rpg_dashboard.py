#!/usr/bin/env python3
"""Leo's RPG status dashboard — generates a character sheet from daily data.

Usage:
  python3 rpg_dashboard.py              # Discord text → stdout
  python3 rpg_dashboard.py --email      # HTML → stdout
  python3 rpg_dashboard.py --send-email # send via SMTP
"""

import argparse
import json
import sys
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPTS   = Path(__file__).parent
WORKSPACE = SCRIPTS.parent.parent.parent
MEMORY    = WORKSPACE / 'memory'
TZ        = timezone(timedelta(hours=8))
NOW       = datetime.now(TZ)
TODAY     = NOW.strftime('%Y-%m-%d')


# ── data model ────────────────────────────────────────────────────────────

@dataclass
class Status:
    date: str         = TODAY
    energy: int       = 50    # 0–100
    mood: int         = 50    # 0–100
    sleep_hours: float = 0.0
    sleep_quality: int = 50   # 0–100
    tasks_today: int  = 0
    tasks_overdue: int = 0
    quests: list      = field(default_factory=list)   # top P1 task names
    status_effects: list = field(default_factory=list)
    streak: int       = 0


# ── data collection ───────────────────────────────────────────────────────

def load_diary_entry() -> dict:
    """Return the most recent diary entry (today preferred). Returns {} if unavailable."""
    sys.path.insert(0, str(SCRIPTS))
    try:
        from read_diary import load_diary
        entries = load_diary()
        if not entries:
            return {}
        # prefer today; fall back to most recent available
        today = [e for e in entries if e.get('date') == TODAY]
        return today[-1] if today else sorted(entries, key=lambda e: e.get('date', ''))[-1]
    except Exception:
        return {}


def parse_sleep_hours(sleep_in: str, wake_up: str) -> float:
    """Convert 'HHMM' strings to sleep duration in hours."""
    def to_min(t: str) -> int:
        t = str(t).zfill(4)
        return int(t[:2]) * 60 + int(t[2:])
    try:
        s, w = to_min(sleep_in), to_min(wake_up)
        if w < s:      # crossed midnight
            w += 24 * 60
        return round((w - s) / 60, 1)
    except Exception:
        return 0.0


def load_todoist() -> tuple[int, int, list[str]]:
    """Return (tasks_today, tasks_overdue, p1_names)."""
    try:
        env = WORKSPACE / 'secrets' / 'todoist.env'
        token = next(
            (line.split('=', 1)[1].strip().strip('"')
             for line in env.read_text().splitlines()
             if line.startswith('TODOIST_API_TOKEN')),
            ''
        )
        if not token:
            return 0, 0, []

        req = urllib.request.Request(
            'https://api.todoist.com/api/v1/tasks?limit=200',
            headers={'Authorization': f'Bearer {token}'}
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read())
        tasks = data.get('results', data) if isinstance(data, dict) else data

        today = NOW.date()
        tasks_today = tasks_overdue = 0

        for t in tasks:
            due_str = (t.get('due') or {}).get('date', '')
            if due_str:
                due = datetime.strptime(due_str[:10], '%Y-%m-%d').date()
                if due < today:
                    tasks_overdue += 1
                elif due == today:
                    tasks_today += 1

        # Quests: tasks with a due date, sorted by urgency (soonest + highest priority)
        # Todoist API: priority 4=P1, 3=P2, 2=P3, 1=P4
        def urgency_key(t):
            due_str = (t.get('due') or {}).get('date', '')
            due_score = due_str[:10] if due_str else '9999-99-99'
            return (due_score, -t.get('priority', 1))

        with_due = [t for t in tasks if (t.get('due') or {}).get('date') and t.get('priority', 1) >= 3]
        quests = [t.get('content', '')[:50] for t in sorted(with_due, key=urgency_key)[:3]]

        return tasks_today, tasks_overdue, quests

    except Exception:
        return 0, 0, []


def compute_streak() -> int:
    """Count consecutive days with a memory file, ending today."""
    streak = 0
    d = NOW.date()
    while (MEMORY / f'{d.strftime("%Y-%m-%d")}.md').exists() and streak < 365:
        streak += 1
        d -= timedelta(days=1)
    return streak


def detect_status_effects(diary_text: str, s: Status) -> list[str]:
    """Derive status effects from diary text + computed values."""
    effects = []
    if any(w in diary_text for w in ['感冒', '生病', '咳嗽', '頭痛', '鼻塞', '喉嚨', '藥', '看診', '保健']):
        effects.append('🤒 生病中')
    if s.sleep_hours > 0 and s.sleep_hours < 6:
        effects.append('🌙 睡眠不足')
    if any(w in diary_text for w in ['論文', 'paper', 'AudioMatters', 'Interspeech', '截止', 'deadline']):
        effects.append('🔥 論文衝刺')
    if s.tasks_overdue >= 5:
        effects.append('📌 任務積壓')
    return effects


def build_status() -> Status:
    """Collect all data sources and return a Status object."""
    entry = load_diary_entry()

    s = Status()
    s.date         = entry.get('date', TODAY)
    s.energy       = int(entry.get('energy', '5') or '5') * 20   # 1–5 → 0–100
    s.mood         = int(entry.get('mood', '5') or '5') * 20
    s.sleep_quality = int(entry.get('sleep_quality', '3') or '3') * 20
    s.sleep_hours  = parse_sleep_hours(
        str(entry.get('sleep_in', '0')),
        str(entry.get('wake_up', '0')),
    )
    s.tasks_today, s.tasks_overdue, s.quests = load_todoist()
    s.streak       = compute_streak()
    s.status_effects = detect_status_effects(entry.get('diary', ''), s)
    return s


# ── rendering ─────────────────────────────────────────────────────────────

def bar(pct: int, width: int = 10) -> str:
    filled = round(max(0, min(100, pct)) / 100 * width)
    return '█' * filled + '░' * (width - filled)


def stars(pct: int, count: int = 5) -> str:
    filled = round(max(0, min(100, pct)) / 100 * count)
    return '★' * filled + '☆' * (count - filled)


def render_discord(s: Status) -> str:
    div = '━' * 32
    lines = [
        div,
        f'🦁 Leo  ·  台大電信所碩一  ·  {s.date}',
        div,
        '',
        f'❤️  精力   {bar(s.energy)}  {s.energy}%',
        f'💙  心情   {bar(s.mood)}  {s.mood}%',
        f'😴  睡眠   {s.sleep_hours}h  {stars(s.sleep_quality)}',
        '',
    ]

    lines.append(f'📋 任務   ⏳ 今日 {s.tasks_today}  ·  🔴 逾期 {s.tasks_overdue}')

    if s.quests:
        lines.append('')
        lines.append('⚔️  主線任務')
        for q in s.quests:
            lines.append(f'   › {q}')

    if s.status_effects or s.streak:
        lines.append('')
        parts = list(s.status_effects)
        if s.streak:
            parts.append(f'🔗 連打 {s.streak} 天')
        lines.append('🌡️  狀態   ' + '  ·  '.join(parts))

    lines += ['', div]
    return '\n'.join(lines)


def render_email(s: Status) -> str:
    def html_bar(pct: int) -> str:
        color = '#4caf50' if pct >= 60 else ('#ff9800' if pct >= 35 else '#f44336')
        return (
            f'<div style="background:#eee;border-radius:4px;height:16px;width:200px;display:inline-block">'
            f'<div style="background:{color};width:{pct}%;height:100%;border-radius:4px"></div>'
            f'</div> {pct}%'
        )

    quest_rows = ''.join(
        f'<li style="margin:4px 0">{q}</li>' for q in s.quests
    ) or '<li>—</li>'

    effect_str = '  ·  '.join(s.status_effects) or '正常'
    if s.streak:
        effect_str += f'  ·  🔗 連打 {s.streak} 天'

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body {{ font-family: sans-serif; max-width: 500px; margin: 30px auto; color: #333; }}
  h1   {{ font-size: 1.2em; border-bottom: 2px solid #eee; padding-bottom: 8px; }}
  table {{ border-collapse: collapse; width: 100%; }}
  td   {{ padding: 8px 4px; vertical-align: middle; }}
  .label {{ width: 60px; color: #666; font-size: .9em; }}
</style>
</head><body>
<h1>🦁 Leo · 台大電信所碩一 · {s.date}</h1>

<table>
  <tr><td class="label">❤️ 精力</td><td>{html_bar(s.energy)}</td></tr>
  <tr><td class="label">💙 心情</td><td>{html_bar(s.mood)}</td></tr>
  <tr><td class="label">😴 睡眠</td><td>{s.sleep_hours}h &nbsp; {stars(s.sleep_quality)}</td></tr>
</table>

<p>📋 <strong>任務</strong> &nbsp; ⏳ 今日 {s.tasks_today} &nbsp;·&nbsp; 🔴 逾期 {s.tasks_overdue}</p>

<p>⚔️ <strong>主線任務</strong></p>
<ul style="margin:4px 0 16px 20px">{quest_rows}</ul>

<p>🌡️ <strong>狀態</strong> &nbsp; {effect_str}</p>
</body></html>"""


# ── sending ───────────────────────────────────────────────────────────────

def send_email(html: str):
    sys.path.insert(0, str(SCRIPTS))
    from email_utils import send_email as _send
    _send(
        subject=f'🦁 Leo 今日狀態 · {TODAY}',
        body=html,
        is_html=True,
    )
    print('Email sent.')


# ── main ──────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Leo's RPG status dashboard")
    parser.add_argument('--email',      action='store_true', help='Output HTML instead of Discord text')
    parser.add_argument('--send-email', action='store_true', help='Send via SMTP')
    args = parser.parse_args()

    s = build_status()

    if args.send_email:
        send_email(render_email(s))
    elif args.email:
        print(render_email(s))
    else:
        print(render_discord(s))
