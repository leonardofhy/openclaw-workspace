#!/usr/bin/env python3
"""Daily AI Safety & Research Briefing — email + file output.

Combines:
  1. News digest (memory/learning/news/YYYY-MM-DD.md)
  2. Autodidact cycle summaries (memory/learning/logs/events.jsonl)
  3. New artifacts/pitches produced today
  4. Research relevance notes for Leo's active tracks

Usage:
  python3 daily_briefing.py                # today, print to stdout
  python3 daily_briefing.py --send         # today, send email + save file
  python3 daily_briefing.py --date 2026-03-01 --send
"""

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

TZ = timezone(timedelta(hours=8))
WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
NEWS_DIR = WORKSPACE / "memory" / "learning" / "news"
EVENTS_LOG = WORKSPACE / "memory" / "learning" / "logs" / "events.jsonl"
PITCHES_DIR = WORKSPACE / "memory" / "learning" / "pitches"
BRIEFING_DIR = WORKSPACE / "memory" / "learning" / "briefings"
ACTIVE_STATE = WORKSPACE / "memory" / "learning" / "state" / "active.json"

# Leo's active research tracks for relevance tagging
TRACKS = {
    "T3": "Listen vs Guess (Paper A)",
    "T5": "Listen-Layer Audit / AI Safety",
    "AudioMatters": "Interspeech 2026",
    "MATS": "MATS Autumn 2026 Neel Nanda",
}


def load_news(date_str: str) -> str:
    """Load news digest for the given date."""
    p = NEWS_DIR / f"{date_str}.md"
    if not p.exists():
        return ""
    return p.read_text().strip()


def load_events(date_str: str) -> list[dict]:
    """Load autodidact events for the given date."""
    events = []
    if not EVENTS_LOG.exists():
        return events
    for line in EVENTS_LOG.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
            ts = ev.get("ts", "")
            if ts.startswith(date_str):
                events.append(ev)
        except json.JSONDecodeError:
            continue
    return events


def load_active_state() -> dict:
    """Load active.json for phase + track info."""
    if not ACTIVE_STATE.exists():
        return {}
    try:
        return json.loads(ACTIVE_STATE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def find_new_artifacts(date_str: str, events: list[dict]) -> list[str]:
    """Extract artifact paths from today's events."""
    artifacts = []
    for ev in events:
        for a in ev.get("artifacts", []):
            if a not in artifacts:
                artifacts.append(a)
    # Also check pitches dir for files modified today
    if PITCHES_DIR.exists():
        for f in PITCHES_DIR.iterdir():
            if f.is_file() and f.suffix == ".md":
                mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=TZ)
                if mtime.strftime("%Y-%m-%d") == date_str:
                    rel = str(f.relative_to(WORKSPACE))
                    if rel not in artifacts:
                        artifacts.append(rel)
    return artifacts


def format_events_section(events: list[dict]) -> str:
    """Format autodidact events into briefing section."""
    if not events:
        return "（今天 Autodidact 沒有完成的 cycle）"

    lines = []
    for ev in events:
        action = ev.get("action", "?")
        task = ev.get("task_id", "")
        summary = ev.get("summary", "")
        icon = {"learn": "📖", "build": "🔨", "reflect": "🪞",
                "plan": "📋", "skill-up": "⚡", "report": "📊",
                "test": "🧪"}.get(action, "▪️")
        cycle = ev.get("cycle_id", "")
        time_part = cycle.split("-")[-1] if cycle else ""
        if len(time_part) == 4:
            time_part = f"{time_part[:2]}:{time_part[2:]}"
        line = f"  {icon} [{time_part}] **{action}** {task}: {summary}"
        lines.append(line)

    return "\n".join(lines)


def format_briefing(date_str: str) -> str:
    """Compose the full daily briefing."""
    news = load_news(date_str)
    events = load_events(date_str)
    state = load_active_state()
    artifacts = find_new_artifacts(date_str, events)

    phase = state.get("phase", "?")
    tracks = state.get("active_tracks", [])
    if tracks and isinstance(tracks[0], dict):
        track_str = ", ".join(t.get("id", "?") + ": " + t.get("name", "") for t in tracks)
    elif tracks:
        track_str = ", ".join(str(t) for t in tracks)
    else:
        track_str = "none"

    # Count actions
    action_counts = {}
    for ev in events:
        a = ev.get("action", "other")
        action_counts[a] = action_counts.get(a, 0) + 1
    action_summary = ", ".join(f"{v}×{k}" for k, v in sorted(action_counts.items()))
    if not action_summary:
        action_summary = "no cycles"

    # --- Build email body ---
    sections = []

    # Header
    sections.append(f"# 🦁 Daily Research Briefing — {date_str}")
    sections.append(f"> Phase: {phase} | Tracks: {track_str} | Cycles: {action_summary}")
    sections.append("")

    # Section 1: News
    sections.append("## 📰 今日 AI Safety & ML 動態")
    sections.append("")
    if news:
        # Strip the original header, keep just the items
        news_lines = news.split("\n")
        content_started = False
        for line in news_lines:
            if line.startswith("## "):
                content_started = True
                sections.append(line)
            elif content_started or line.startswith("**"):
                sections.append(line)
            elif line.startswith(">") and "relevant" in line:
                sections.append(line)
    else:
        sections.append("今天沒有高相關性的新文章。")
    sections.append("")

    # Section 2: Autodidact progress
    sections.append("## 🤖 Autodidact 進展")
    sections.append("")
    sections.append(format_events_section(events))
    sections.append("")

    # Section 3: Artifacts
    if artifacts:
        sections.append("## 📦 新產出")
        sections.append("")
        for a in artifacts:
            sections.append(f"  - `{a}`")
        sections.append("")

    # Section 4: Research relevance (brief)
    next_actions = set()
    for ev in events:
        n = ev.get("next", "")
        if n:
            next_actions.add(n)

    if next_actions:
        sections.append("## 🎯 下一步")
        sections.append("")
        for n in list(next_actions)[:3]:
            sections.append(f"  - {n}")
        sections.append("")

    # Footer
    sections.append("---")
    sections.append("_Auto-generated by Little Leo (Lab) • Autodidact + News Scout_")

    return "\n".join(sections)


def save_briefing(date_str: str, content: str) -> Path:
    """Save briefing to file."""
    BRIEFING_DIR.mkdir(parents=True, exist_ok=True)
    p = BRIEFING_DIR / f"{date_str}.md"
    p.write_text(content)
    return p


def send_briefing(date_str: str, content: str) -> bool:
    """Send briefing via email."""
    # Import from workspace
    sys.path.insert(0, str(WORKSPACE / "skills" / "leo-diary" / "scripts"))
    try:
        from email_utils import send_email
        subject = f"🦁 Daily Research Briefing — {date_str}"
        return send_email(subject, content, sender_label="Little Leo (Lab)")
    except Exception as e:
        print(f"❌ Email send failed: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Daily AI Safety & Research Briefing")
    parser.add_argument("--date", default=None, help="Date (YYYY-MM-DD), default today")
    parser.add_argument("--send", action="store_true", help="Send email + save file")
    parser.add_argument("--no-save", action="store_true", help="Don't save to file")
    args = parser.parse_args()

    date_str = args.date or datetime.now(TZ).strftime("%Y-%m-%d")

    content = format_briefing(date_str)

    if args.send:
        # Save
        if not args.no_save:
            p = save_briefing(date_str, content)
            print(f"💾 Saved: {p}", file=sys.stderr)
        # Email
        ok = send_briefing(date_str, content)
        if ok:
            print(f"📧 Briefing sent for {date_str}", file=sys.stderr)
        else:
            print(f"❌ Email failed for {date_str}", file=sys.stderr)
            sys.exit(1)
        # Also print
        print(content)
    else:
        print(content)


if __name__ == "__main__":
    main()
