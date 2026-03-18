#!/usr/bin/env python3
"""Cron health monitor — detect silent failures across all openclaw cron jobs.

Reads ~/.openclaw/cron/jobs.json and run history to detect:
  MISSED  — job hasn't run in 2x its expected interval
  FAILING — last 3 runs exited non-zero
  STALE   — output unchanged across 3+ consecutive runs
  SLOW    — last run took >2x median duration

Usage:
    python3 skills/shared/cron_monitor.py              # human-readable table
    python3 skills/shared/cron_monitor.py --json        # machine output
    python3 skills/shared/cron_monitor.py --alert       # only show problems

Exit codes: 0 = all healthy, 1 = warnings/alerts, 2 = errors
"""

import argparse
import json
import os
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

TZ = timezone(timedelta(hours=8), name="Asia/Taipei")

# ── Cron expression → interval (seconds) ──

WEEKDAY_MAP = {"0": 0, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 0}


def _cron_interval_seconds(expr: str) -> int | None:
    """Estimate the repeat interval from a cron expression.

    Returns seconds between expected runs, or None if unparseable.
    Handles common patterns; not a full cron parser.
    """
    parts = expr.strip().split()
    if len(parts) != 5:
        return None

    minute, hour, dom, month, dow = parts

    # Every N minutes: */N * * * *
    if minute.startswith("*/") and hour == "*" and dom == "*" and dow == "*":
        try:
            return int(minute[2:]) * 60
        except ValueError:
            return None

    # Every N hours: 0 */N * * *
    if hour.startswith("*/") and dom == "*":
        try:
            return int(hour[2:]) * 3600
        except ValueError:
            return None

    # Multiple times per hour: M1,M2 H-H * * *
    if "," in minute and dom == "*":
        mins = minute.split(",")
        if len(mins) >= 2:
            try:
                interval_min = int(mins[1]) - int(mins[0])
                if interval_min > 0:
                    return interval_min * 60
            except ValueError:
                pass

    # Multiple fixed hours: M H1,H2 * * *
    if "," in hour and dom == "*":
        hours = hour.split(",")
        if len(hours) >= 2:
            try:
                interval_h = int(hours[1]) - int(hours[0])
                if interval_h > 0:
                    return interval_h * 3600
            except ValueError:
                pass

    # Daily: specific minute + specific hour, * dom, * month, any dow pattern
    if minute.isdigit() and hour.isdigit() and dom == "*" and month == "*":
        if dow == "*":
            return 86400  # daily
        # Weekday range like 1-5 → still roughly daily
        if "-" in dow:
            return 86400
        # Specific day of week → weekly
        return 7 * 86400

    # Weekly: specific day of week
    if dom == "*" and month == "*" and dow not in ("*",):
        return 7 * 86400

    # Monthly
    if dom.isdigit() and month == "*":
        return 30 * 86400

    # Fallback: daily
    return 86400


# ── Data loading ──

def _find_cron_dir() -> Path:
    return Path.home() / ".openclaw" / "cron"


def _find_workspace() -> Path:
    d = Path(__file__).resolve().parent
    for _ in range(10):
        if (d / ".git").is_dir():
            return d
        d = d.parent
    return Path.home() / ".openclaw" / "workspace"


def load_jobs(cron_dir: Path) -> list[dict]:
    """Load jobs from jobs.json, return only enabled recurring jobs."""
    jobs_file = cron_dir / "jobs.json"
    if not jobs_file.exists():
        return []
    with open(jobs_file) as f:
        data = json.load(f)
    jobs = data.get("jobs", [])
    # Filter: enabled + recurring (cron kind, not one-time 'at')
    return [j for j in jobs if j.get("enabled") and j.get("schedule", {}).get("kind") == "cron"]


def load_run_history(cron_dir: Path, job_id: str, max_lines: int = 50) -> list[dict]:
    """Load recent run history for a job from its JSONL file."""
    run_file = cron_dir / "runs" / f"{job_id}.jsonl"
    if not run_file.exists():
        return []
    lines = []
    try:
        with open(run_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        lines.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except OSError:
        return []
    # Return most recent runs (file is append-only, newest last)
    return lines[-max_lines:]


# ── Anomaly detection ──

def analyze_job(job: dict, runs: list[dict], now_ms: int) -> dict:
    """Analyze a single job and return health status.

    Returns dict with: id, name, schedule, last_run, status, anomalies[], notes
    """
    jid = job["id"]
    name = job["name"]
    sched = job.get("schedule", {})
    expr = sched.get("expr", "")
    state = job.get("state", {})

    last_run_ms = state.get("lastRunAtMs")
    last_status = state.get("lastStatus") or state.get("lastRunStatus")
    last_duration_ms = state.get("lastDurationMs")
    consecutive_errors = state.get("consecutiveErrors", 0)
    next_run_ms = state.get("nextRunAtMs")

    interval_s = _cron_interval_seconds(expr)
    anomalies = []
    notes = []

    # -- MISSED: hasn't run in 2x interval --
    if last_run_ms and interval_s:
        elapsed_s = (now_ms - last_run_ms) / 1000
        threshold = interval_s * 2
        if elapsed_s > threshold:
            hours_late = (elapsed_s - interval_s) / 3600
            anomalies.append("MISSED")
            notes.append(f"overdue by {hours_late:.1f}h")
    elif not last_run_ms:
        anomalies.append("MISSED")
        notes.append("never ran")

    # -- FAILING: last 3 runs non-zero / error --
    finished_runs = [r for r in runs if r.get("action") == "finished"]
    if len(finished_runs) >= 3:
        last_3 = finished_runs[-3:]
        if all(r.get("status") != "ok" for r in last_3):
            anomalies.append("FAILING")
            errors = [r.get("error", r.get("status", "?"))[:40] for r in last_3]
            notes.append(f"3 consecutive failures: {errors[-1]}")
    elif consecutive_errors >= 3:
        anomalies.append("FAILING")
        notes.append(f"{consecutive_errors} consecutive errors")

    # -- STALE: output hasn't changed in 3+ runs --
    summaries = [r.get("summary", "") for r in finished_runs if r.get("summary")]
    if len(summaries) >= 3:
        last_3_summaries = summaries[-3:]
        if len(set(last_3_summaries)) == 1:
            anomalies.append("STALE")
            notes.append("identical output 3 runs")

    # -- SLOW: last run > 2x median duration --
    durations = [r.get("durationMs", 0) for r in finished_runs if r.get("durationMs")]
    if len(durations) >= 3 and last_duration_ms:
        median_dur = statistics.median(durations)
        if median_dur > 0 and last_duration_ms > median_dur * 2:
            anomalies.append("SLOW")
            notes.append(f"last={last_duration_ms/1000:.0f}s median={median_dur/1000:.0f}s")

    # Determine overall status
    if anomalies:
        status = "ALERT"
    elif last_status == "ok":
        status = "OK"
    elif last_status:
        status = last_status.upper()
    else:
        status = "UNKNOWN"

    # Format last_run as human readable
    last_run_str = ""
    if last_run_ms:
        dt = datetime.fromtimestamp(last_run_ms / 1000, tz=TZ)
        age_h = (now_ms - last_run_ms) / 1000 / 3600
        if age_h < 24:
            last_run_str = f"{dt.strftime('%H:%M')} ({age_h:.1f}h ago)"
        else:
            last_run_str = f"{dt.strftime('%m-%d %H:%M')} ({age_h/24:.1f}d ago)"

    return {
        "id": jid,
        "name": name,
        "schedule": expr,
        "interval_s": interval_s,
        "last_run": last_run_str,
        "last_run_ms": last_run_ms,
        "last_duration_ms": last_duration_ms,
        "status": status,
        "anomalies": anomalies,
        "notes": "; ".join(notes) if notes else "",
    }


# ── State persistence ──

def save_state(workspace: Path, results: list[dict], now_ms: int) -> None:
    """Save cron health snapshot to memory/cron-health.json."""
    state_file = workspace / "memory" / "cron-health.json"
    state = {
        "last_check_ms": now_ms,
        "last_check": datetime.fromtimestamp(now_ms / 1000, tz=TZ).isoformat(),
        "total_jobs": len(results),
        "alerts": sum(1 for r in results if r["anomalies"]),
        "jobs": {
            r["id"]: {
                "name": r["name"],
                "status": r["status"],
                "anomalies": r["anomalies"],
                "notes": r["notes"],
                "last_run_ms": r["last_run_ms"],
                "last_duration_ms": r["last_duration_ms"],
            }
            for r in results
        },
    }
    os.makedirs(state_file.parent, exist_ok=True)
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")


# ── Output formatting ──

def format_table(results: list[dict]) -> str:
    """Format results as a human-readable table."""
    if not results:
        return "No enabled cron jobs found."

    # Column widths
    name_w = min(max(len(r["name"]) for r in results), 35)
    lines = []
    header = f"{'Job':<{name_w}} | {'Last Run':<20} | {'Status':<7} | Notes"
    lines.append(header)
    lines.append("-" * len(header))

    for r in results:
        name = r["name"][:name_w]
        status = r["status"]
        if r["anomalies"]:
            status = ",".join(r["anomalies"])
        lines.append(f"{name:<{name_w}} | {r['last_run']:<20} | {status:<7} | {r['notes']}")

    # Summary
    total = len(results)
    ok = sum(1 for r in results if r["status"] == "OK")
    alerts = sum(1 for r in results if r["anomalies"])
    lines.append("")
    lines.append(f"Total: {total} jobs | {ok} healthy | {alerts} alerts")

    return "\n".join(lines)


def format_alert_only(results: list[dict]) -> str:
    """Format only anomalous jobs for heartbeat integration."""
    alerts = [r for r in results if r["anomalies"]]
    if not alerts:
        return ""
    lines = []
    for r in alerts:
        tags = ",".join(r["anomalies"])
        lines.append(f"[{tags}] {r['name']}: {r['notes']}")
    return "\n".join(lines)


# ── Main ──

def main() -> None:
    parser = argparse.ArgumentParser(description="Cron health monitor")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--alert", action="store_true", help="Only show problems")
    args = parser.parse_args()

    cron_dir = _find_cron_dir()
    workspace = _find_workspace()
    now_ms = int(time.time() * 1000)

    jobs = load_jobs(cron_dir)
    if not jobs and not args.json:
        print("No enabled cron jobs found in", cron_dir / "jobs.json")
        sys.exit(0)

    results = []
    for job in jobs:
        runs = load_run_history(cron_dir, job["id"])
        results.append(analyze_job(job, runs, now_ms))

    # Sort: alerts first, then by name
    results.sort(key=lambda r: (0 if r["anomalies"] else 1, r["name"]))

    # Persist state
    save_state(workspace, results, now_ms)

    has_alerts = any(r["anomalies"] for r in results)

    if args.json:
        out = {
            "timestamp": datetime.fromtimestamp(now_ms / 1000, tz=TZ).isoformat(),
            "total": len(results),
            "alerts": sum(1 for r in results if r["anomalies"]),
            "jobs": results,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    elif args.alert:
        text = format_alert_only(results)
        if text:
            print(text)
        else:
            print("CRON_OK")
    else:
        print(format_table(results))

    sys.exit(1 if has_alerts else 0)


if __name__ == "__main__":
    main()
