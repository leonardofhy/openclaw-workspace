"""schedule_formatter.py — display and review rendering for daily schedules."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'lib'))
from common import now as _now

sys.path.insert(0, str(Path(__file__).resolve().parent))
from schedule_parser import DaySchedule
from schedule_generator import get_spillover


# ── Rendering ──

def render_display(schedule: DaySchedule, now_str: str | None = None) -> str:
    """Render schedule with ✅/▶/⏳ markers based on current time."""
    if now_str is None:
        now_str = _now().strftime('%H:%M')

    now_min = int(now_str[:2]) * 60 + int(now_str[3:5])
    lines = []

    lines.append(f"📅 {schedule.date}（{schedule.weekday}）")
    lines.append("")

    # Completed items
    for log_entry in schedule.actual_log:
        if log_entry.startswith('✅'):
            lines.append(f"- {log_entry}")

    # Current + future blocks
    now_printed = False
    for block in sorted(schedule.blocks, key=lambda b: b.start_minutes):
        if not now_printed and block.start_minutes > now_min:
            lines.append(f"▶ **{now_str} ← 現在**")
            now_printed = True

        end_min = block.end_minutes
        if block.start_minutes <= now_min < end_min:
            icon = "🔵"
            remaining = end_min - now_min
            suffix = f" ({remaining}m 後結束)"
        elif now_min >= end_min:
            icon = "✅"
            suffix = ""
        else:
            icon = "⏳"
            suffix = ""

        lines.append(f"• {icon} {block.start}–{block.end} {block.emoji} {block.title}{suffix}")

    if not now_printed:
        lines.append(f"▶ **{now_str} ← 現在（行程已結束）**")

    # Unscheduled
    if schedule.unscheduled:
        lines.append("")
        lines.append(f"⚠️ 未排入：{'、'.join(schedule.unscheduled)}")

    return '\n'.join(lines)


def render_review(schedule: DaySchedule) -> str:
    """Generate day-end review section."""
    total_blocks = len(schedule.blocks)
    completed = len([l for l in schedule.actual_log if '✅' in l])
    skipped = len([l for l in schedule.actual_log if '❌' in l])

    rate = int(completed / total_blocks * 100) if total_blocks else 0

    lines = [
        f"## 日終回顧 (auto, {_now().strftime('%H:%M')})",
        f"- 完成率: {completed}/{total_blocks} ({rate}%)",
    ]

    # Find unfinished items
    spillover = get_spillover(schedule.date)
    if spillover:
        spill_titles = [s['title'][:30] for s in spillover[:3]]
        lines.append(f"- 未完成 → 明日: {', '.join(spill_titles)}")

    return '\n'.join(lines)
