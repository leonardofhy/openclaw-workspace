#!/usr/bin/env python3
"""session_analytics.py — Track productivity patterns from OpenClaw sessions.

Usage:
    python3 skills/shared/session_analytics.py              # human-readable report
    python3 skills/shared/session_analytics.py --json       # machine-readable
    python3 skills/shared/session_analytics.py --chart      # save matplotlib chart
    python3 skills/shared/session_analytics.py --days 7     # last 7 days only
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent


# ── Git log parsing ──────────────────────────────────────────────────────

def parse_git_log(since_days: int = 14) -> list[dict]:
    """Parse git log into structured entries."""
    since = (date.today() - timedelta(days=since_days)).isoformat()
    try:
        out = subprocess.run(
            ["git", "log", f"--since={since}", "--format=%ai\t%s"],
            capture_output=True, text=True, cwd=WORKSPACE,
        )
        if out.returncode != 0:
            return []
    except FileNotFoundError:
        return []

    entries = []
    for line in out.stdout.strip().splitlines():
        if "\t" not in line:
            continue
        ts_str, subject = line.split("\t", 1)
        try:
            dt = datetime.strptime(ts_str[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue

        # Categorise by prefix
        cat = "other"
        lower = subject.lower()
        for prefix in ("feat", "fix", "refactor", "chore", "experiment",
                        "batch", "memory", "audit", "retire", "heartbeat"):
            if lower.startswith(prefix):
                cat = prefix
                break

        entries.append({"datetime": dt, "date": dt.date().isoformat(),
                        "hour": dt.hour, "subject": subject, "category": cat})
    return entries


def git_stats(entries: list[dict]) -> dict:
    """Aggregate git log entries into stats."""
    commits_per_day: Counter = Counter()
    cats: Counter = Counter()
    hours: Counter = Counter()

    for e in entries:
        commits_per_day[e["date"]] += 1
        cats[e["category"]] += 1
        hours[e["hour"]] += 1

    peak_hour = hours.most_common(1)[0] if hours else (0, 0)
    return {
        "total_commits": len(entries),
        "commits_per_day": dict(sorted(commits_per_day.items())),
        "categories": dict(cats.most_common()),
        "peak_hour": peak_hour[0],
        "peak_hour_count": peak_hour[1],
    }


# ── Memory file parsing ─────────────────────────────────────────────────

CC_SPAWN_RE = re.compile(r"CC#\d+", re.IGNORECASE)
EXPERIMENT_RE = re.compile(r"\b[QE]\d{3}\b")
SUCCESS_RE = re.compile(r"[✅✓]|pass|success", re.IGNORECASE)
FAIL_RE = re.compile(r"[❌✗]|fail|blocked", re.IGNORECASE)
HEARTBEAT_RE = re.compile(r"##\s+\d{2}:\d{2}\s+Heartbeat")
SECTION_TIME_RE = re.compile(r"##\s+(\d{2}:\d{2})[–-](\d{2}:\d{2})\s+(.*)")


def _classify_section(title: str) -> str:
    """Classify a work section into a mode."""
    t = title.lower()
    if any(w in t for w in ("paper", "abstract", "latex", "writing", "outline")):
        return "paper"
    if any(w in t for w in ("experiment", "batch", "autodidact", "研究")):
        return "research"
    if any(w in t for w in ("fix", "refactor", "clean", "merge", "掃除", "retire")):
        return "maintenance"
    if any(w in t for w in ("plan", "review", "audit", "sprint")):
        return "planning"
    return "engineering"


def parse_memory_file(path: Path) -> dict:
    """Extract structured data from a daily memory file."""
    text = path.read_text(encoding="utf-8")
    day = path.stem  # e.g. "2026-03-18"

    agents = CC_SPAWN_RE.findall(text)
    experiments = set(EXPERIMENT_RE.findall(text))
    successes = len(SUCCESS_RE.findall(text))
    failures = len(FAIL_RE.findall(text))
    heartbeats = len(HEARTBEAT_RE.findall(text))

    # Parse timed sections for mode tracking
    modes: dict[str, float] = defaultdict(float)
    for m in SECTION_TIME_RE.finditer(text):
        start_h, start_m = map(int, m.group(1).split(":"))
        end_h, end_m = map(int, m.group(2).split(":"))
        hours = (end_h * 60 + end_m - start_h * 60 - start_m) / 60
        if hours < 0:
            hours += 24
        mode = _classify_section(m.group(3))
        modes[mode] += round(hours, 2)

    # Look for explicit stats in text
    lines_added = 0
    lines_deleted = 0
    for m_stat in re.finditer(r"~?(\d[\d,]+)\s*(?:行|lines?)\s*(?:新增|added)", text):
        lines_added += int(m_stat.group(1).replace(",", ""))
    for m_stat in re.finditer(r"~?(\d[\d,]+)\s*(?:行|lines?)\s*(?:刪除|deleted)", text):
        lines_deleted += int(m_stat.group(1).replace(",", ""))

    return {
        "date": day,
        "agents_spawned": len(agents),
        "unique_agents": sorted(set(agents)),
        "experiments": len(experiments),
        "successes": successes,
        "failures": failures,
        "heartbeats": heartbeats,
        "modes_hours": dict(modes),
        "lines_added": lines_added,
        "lines_deleted": lines_deleted,
    }


def parse_all_memory(days: int | None = None) -> list[dict]:
    """Parse all daily memory files, optionally limited to recent N days."""
    mem_dir = WORKSPACE / "memory"
    pattern = "2026-03-*.md"  # extend as needed
    files = sorted(mem_dir.glob(pattern))

    if days:
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        files = [f for f in files if f.stem >= cutoff]

    return [parse_memory_file(f) for f in files]


# ── Aggregation ──────────────────────────────────────────────────────────

def aggregate(memory_data: list[dict], git_data: dict) -> dict:
    """Combine memory and git data into a productivity report."""
    total_agents = sum(d["agents_spawned"] for d in memory_data)
    total_experiments = sum(d["experiments"] for d in memory_data)
    total_successes = sum(d["successes"] for d in memory_data)
    total_failures = sum(d["failures"] for d in memory_data)
    total_heartbeats = sum(d["heartbeats"] for d in memory_data)

    # Mode hours aggregation
    mode_totals: dict[str, float] = defaultdict(float)
    for d in memory_data:
        for mode, hrs in d["modes_hours"].items():
            mode_totals[mode] += hrs

    # Trend: compare first half vs second half of period
    n = len(memory_data)
    if n >= 4:
        first_half = memory_data[:n // 2]
        second_half = memory_data[n // 2:]
        first_avg = git_data["total_commits"] / max(len(first_half), 1)
        second_avg = git_data["total_commits"] / max(len(second_half), 1)
        # Use per-day agent counts as proxy
        first_agents = sum(d["agents_spawned"] for d in first_half) / len(first_half)
        second_agents = sum(d["agents_spawned"] for d in second_half) / len(second_half)
        trend = "accelerating" if second_agents > first_agents * 1.1 else (
            "decelerating" if second_agents < first_agents * 0.9 else "steady")
    else:
        first_avg = second_avg = 0
        trend = "insufficient data"

    # Most productive day
    day_scores = []
    cpd = git_data["commits_per_day"]
    for d in memory_data:
        score = cpd.get(d["date"], 0) + d["agents_spawned"] * 2 + d["experiments"]
        day_scores.append((d["date"], score))
    day_scores.sort(key=lambda x: x[1], reverse=True)
    best_day = day_scores[0] if day_scores else ("N/A", 0)

    success_total = total_successes + total_failures
    success_rate = (total_successes / success_total * 100) if success_total else 0

    return {
        "period": {
            "start": memory_data[0]["date"] if memory_data else "N/A",
            "end": memory_data[-1]["date"] if memory_data else "N/A",
            "days_tracked": n,
        },
        "agents": {
            "total_spawned": total_agents,
            "success_rate_pct": round(success_rate, 1),
        },
        "experiments": {"total": total_experiments},
        "heartbeats": total_heartbeats,
        "git": git_data,
        "modes_hours": dict(mode_totals),
        "trend": trend,
        "best_day": {"date": best_day[0], "score": best_day[1]},
        "peak_coding_hour": git_data["peak_hour"],
        "daily": memory_data,
    }


# ── Display ──────────────────────────────────────────────────────────────

def _bar(val: int, max_val: int, width: int = 30) -> str:
    if max_val <= 0:
        return ""
    filled = int(width * val / max_val)
    return "█" * filled + "░" * (width - filled)


def print_report(report: dict) -> None:
    p = report["period"]
    print(f"\n{'═' * 60}")
    print(f"  SESSION ANALYTICS — {p['start']} to {p['end']}")
    print(f"  ({p['days_tracked']} days tracked)")
    print(f"{'═' * 60}")

    # Git activity heatmap
    print(f"\n{'─' * 60}")
    print("  GIT ACTIVITY HEATMAP")
    print(f"{'─' * 60}")
    cpd = report["git"]["commits_per_day"]
    max_c = max(cpd.values()) if cpd else 1
    for day, count in cpd.items():
        weekday = datetime.strptime(day, "%Y-%m-%d").strftime("%a")
        print(f"  {day} {weekday}  {_bar(count, max_c, 25)} {count:>3}")
    print(f"  Total: {report['git']['total_commits']} commits")

    # Commit categories
    print(f"\n{'─' * 60}")
    print("  COMMIT CATEGORIES")
    print(f"{'─' * 60}")
    cats = report["git"]["categories"]
    max_cat = max(cats.values()) if cats else 1
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat:<12} {_bar(count, max_cat, 20)} {count:>3}")

    # Agent & experiment stats
    print(f"\n{'─' * 60}")
    print("  CC AGENT & EXPERIMENT STATS")
    print(f"{'─' * 60}")
    a = report["agents"]
    print(f"  Agents spawned:     {a['total_spawned']}")
    print(f"  Success rate:       {a['success_rate_pct']:.1f}%")
    print(f"  Experiments run:    {report['experiments']['total']}")
    print(f"  Heartbeat checks:   {report['heartbeats']}")

    # Mode time split
    modes = report["modes_hours"]
    if modes:
        print(f"\n{'─' * 60}")
        print("  TIME SPLIT (from timed sessions)")
        print(f"{'─' * 60}")
        total_h = sum(modes.values())
        for mode, hrs in sorted(modes.items(), key=lambda x: -x[1]):
            pct = hrs / total_h * 100 if total_h else 0
            print(f"  {mode:<14} {hrs:5.1f}h  ({pct:4.1f}%)")
        print(f"  {'Total':<14} {total_h:5.1f}h")

    # Trend & insights
    print(f"\n{'─' * 60}")
    print("  INSIGHTS")
    print(f"{'─' * 60}")
    print(f"  Trend:              {report['trend']}")
    print(f"  Best day:           {report['best_day']['date']} (score {report['best_day']['score']})")
    print(f"  Peak commit hour:   {report['peak_coding_hour']}:00")

    # Per-day detail (top 5 busiest)
    daily = sorted(report["daily"], key=lambda d: d["experiments"] + d["agents_spawned"], reverse=True)[:5]
    if daily and any(d["agents_spawned"] + d["experiments"] > 0 for d in daily):
        print(f"\n{'─' * 60}")
        print("  TOP DAYS (by activity)")
        print(f"{'─' * 60}")
        print(f"  {'Date':<12} {'Agents':>7} {'Exps':>5} {'HBs':>4} {'Lines+':>7} {'Lines-':>7}")
        for d in daily:
            print(f"  {d['date']:<12} {d['agents_spawned']:>7} {d['experiments']:>5} "
                  f"{d['heartbeats']:>4} {d['lines_added']:>7} {d['lines_deleted']:>7}")

    print(f"\n{'═' * 60}\n")


# ── Chart generation ─────────────────────────────────────────────────────

def save_chart(report: dict) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    fig.suptitle("OpenClaw Session Analytics", fontsize=14, fontweight="bold")

    cpd = report["git"]["commits_per_day"]
    dates = [datetime.strptime(d, "%Y-%m-%d") for d in cpd]
    counts = list(cpd.values())

    # 1: Commits per day
    ax = axes[0, 0]
    ax.bar(dates, counts, color="#4a90d9", width=0.7)
    ax.set_title("Commits per Day")
    ax.set_ylabel("Commits")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    ax.tick_params(axis="x", rotation=45)

    # 2: Commit categories pie
    ax = axes[0, 1]
    cats = report["git"]["categories"]
    if cats:
        ax.pie(cats.values(), labels=cats.keys(), autopct="%1.0f%%", startangle=90)
    ax.set_title("Commit Categories")

    # 3: Mode time split
    ax = axes[1, 0]
    modes = report["modes_hours"]
    if modes:
        ax.barh(list(modes.keys()), list(modes.values()), color="#6ab04c")
        ax.set_xlabel("Hours")
    ax.set_title("Time by Mode")

    # 4: Daily activity (agents + experiments)
    ax = axes[1, 1]
    daily = report["daily"]
    d_dates = [datetime.strptime(d["date"], "%Y-%m-%d") for d in daily]
    agents = [d["agents_spawned"] for d in daily]
    exps = [d["experiments"] for d in daily]
    ax.bar(d_dates, agents, label="Agents", color="#e55039", width=0.4, align="edge")
    ax.bar(d_dates, exps, label="Experiments", color="#f6b93b", width=-0.4, align="edge")
    ax.set_title("Daily Agents & Experiments")
    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    ax.tick_params(axis="x", rotation=45)

    fig.tight_layout()
    out_path = WORKSPACE / "memory" / "learning" / "figures" / "productivity.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# ── Main ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyse OpenClaw session logs for productivity patterns.")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--chart", action="store_true",
                        help="Save matplotlib chart to memory/learning/figures/productivity.png")
    parser.add_argument("--days", type=int, default=None,
                        help="Limit to last N days (default: all available)")
    args = parser.parse_args()

    since_days = args.days or 30
    memory_data = parse_all_memory(args.days)
    git_entries = parse_git_log(since_days)
    git_data = git_stats(git_entries)
    report = aggregate(memory_data, git_data)

    if args.json:
        # Strip non-serialisable daily details for cleaner JSON
        out = {k: v for k, v in report.items()}
        print(json.dumps(out, indent=2, default=str))
    else:
        print_report(report)

    if args.chart:
        path = save_chart(report)
        print(f"Chart saved to {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
