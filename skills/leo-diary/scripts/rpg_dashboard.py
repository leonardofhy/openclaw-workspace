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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'lib'))
from common import TZ, now as _now, today_str as _today_str, WORKSPACE, MEMORY

SCRIPTS   = Path(__file__).parent
NOW       = _now()
TODAY     = _today_str()


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
    # Weekly trends (new)
    sleep_trend: str  = ''    # ↑ ↓ →
    mood_trend: str   = ''
    energy_trend: str = ''
    research_days_7d: int = 0
    late_sleep_7d: int = 0


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


def _avg_field(entries: list[dict], field: str) -> float | None:
    """Average of a numeric field across entries, ignoring None/non-numeric."""
    vals = []
    for e in entries:
        v = e.get(field)
        if v is not None:
            try:
                vals.append(float(v))
            except (ValueError, TypeError):
                continue
    return sum(vals) / len(vals) if vals else None


def _trend_arrow(current: float | None, previous: float | None) -> str:
    """Return ↑/↓/→ comparing current vs previous, or '' if data missing."""
    if current is None or previous is None:
        return ''
    diff = current - previous
    if abs(diff) < 0.1:
        return '→'
    return '↑' if diff > 0 else '↓'


def _compute_trends(s: Status) -> None:
    """Fill sleep/mood/energy trends + late_sleep count from sleep_calc."""
    try:
        from sleep_calc import analyze_sleep
        week = analyze_sleep(7)
        prev = analyze_sleep(14)
        if not week or not prev:
            return
        s.late_sleep_7d = week.get('late_sleep_days', 0)

        w_entries = week.get('entries', [])[:7]
        p_entries = prev.get('entries', [])[7:14]

        s.sleep_trend  = _trend_arrow(_avg_field(w_entries, 'duration_min'),
                                      _avg_field(p_entries, 'duration_min'))
        s.mood_trend   = _trend_arrow(_avg_field(w_entries, 'mood'),
                                      _avg_field(p_entries, 'mood'))
        s.energy_trend = _trend_arrow(_avg_field(w_entries, 'energy'),
                                      _avg_field(p_entries, 'energy'))
    except (ImportError, KeyError, TypeError, ZeroDivisionError) as e:
        print(f"warn: trend computation failed: {e}", file=sys.stderr)


def _compute_research_momentum(s: Status) -> None:
    """Count research days in last 7 days from tag files."""
    try:
        tags_dir = MEMORY / 'tags'
        research_count = 0
        for i in range(7):
            d = (NOW.date() - timedelta(days=i)).strftime('%Y-%m-%d')
            tag_file = tags_dir / f'{d}.json'
            if tag_file.exists():
                tag = json.loads(tag_file.read_text())
                topics = tag.get('topics', [])
                if '研究/實驗' in topics or 'AudioMatters' in topics:
                    research_count += 1
        s.research_days_7d = research_count
    except (json.JSONDecodeError, OSError) as e:
        print(f"warn: research momentum failed: {e}", file=sys.stderr)


def build_status(todoist_prefetch: tuple | None = None) -> Status:
    """Collect all data sources and return a Status object.

    Args:
        todoist_prefetch: optional (tasks_today, tasks_overdue, quests) to skip API call.
    """
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

    # If diary is stale (not today), try sleep_calc for fresher sleep data
    if s.date != TODAY:
        try:
            from sleep_calc import analyze_sleep
            recent = analyze_sleep(1)
            if recent and recent.get('entries'):
                latest = recent['entries'][0]
                if latest.get('date') == TODAY and latest.get('duration_min'):
                    s.sleep_hours = round(latest['duration_min'] / 60, 1)
                    if latest.get('sleep_quality'):
                        s.sleep_quality = latest['sleep_quality'] * 20
        except Exception:
            pass  # sleep_calc unavailable, keep diary values

    if todoist_prefetch is not None:
        s.tasks_today, s.tasks_overdue, s.quests = todoist_prefetch
    else:
        s.tasks_today, s.tasks_overdue, s.quests = load_todoist()
    s.streak       = compute_streak()
    s.status_effects = detect_status_effects(entry.get('diary', ''), s)

    _compute_trends(s)
    _compute_research_momentum(s)

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
    date_label = s.date
    if s.date != TODAY:
        date_label += '（昨日數據）'
    lines = [
        div,
        f'🦁 Leo  ·  台大電信所碩一  ·  {date_label}',
        div,
        '',
        f'❤️  精力   {bar(s.energy)}  {s.energy}%' + (f' {s.energy_trend}' if s.energy_trend else ''),
        f'💙  心情   {bar(s.mood)}  {s.mood}%' + (f' {s.mood_trend}' if s.mood_trend else ''),
        f'😴  睡眠   {s.sleep_hours}h  {stars(s.sleep_quality)}' + (f' {s.sleep_trend}' if s.sleep_trend else ''),
        '',
    ]

    # Research momentum
    if s.research_days_7d > 0:
        r_bar = '🟩' * s.research_days_7d + '⬜' * (7 - s.research_days_7d)
        lines.append(f'🔬  研究   {r_bar}  {s.research_days_7d}/7d')
    lines.append(f'📋  任務   ⏳ 今日 {s.tasks_today}  ·  🔴 逾期 {s.tasks_overdue}')

    if s.status_effects or s.streak:
        lines.append('')
        parts = list(s.status_effects)
        if s.late_sleep_7d >= 5:
            parts.append(f'⚠️ 本週 {s.late_sleep_7d}/7 晚睡')
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
