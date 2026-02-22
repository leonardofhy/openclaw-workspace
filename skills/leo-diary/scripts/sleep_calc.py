#!/usr/bin/env python3
"""Calculate sleep duration and patterns from diary data.

sleep_in/wake_up are in HHMM format (e.g., 305 = 03:05, 2334 = 23:34).
"""
import json
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from read_diary import load_diary


def parse_hhmm(val):
    """Parse HHMM integer to (hour, minute). Returns None on failure."""
    try:
        v = int(str(val).strip().replace(':', ''))
        if v < 0:
            return None
        h = v // 100
        m = v % 100
        if h > 23 or m > 59:
            return None
        return (h, m)
    except (ValueError, TypeError):
        return None


def sleep_duration_minutes(sleep_in, wake_up):
    """Calculate sleep duration in minutes given HHMM values.
    
    Handles cross-midnight sleep (e.g., sleep at 02:00, wake at 10:00 = 8h).
    Assumes sleep_in is always "last night" and wake_up is "this morning".
    """
    s = parse_hhmm(sleep_in)
    w = parse_hhmm(wake_up)
    if not s or not w:
        return None
    
    sh, sm = s
    wh, wm = w
    
    # Convert to minutes from midnight
    s_min = sh * 60 + sm
    w_min = wh * 60 + wm
    
    # If sleep time is in the evening (before midnight), add 24h to wake time
    # If sleep time is after midnight (early morning), wake is same day
    if s_min > 12 * 60:  # Slept before midnight (e.g., 23:00)
        duration = (24 * 60 - s_min) + w_min
    else:  # Slept after midnight (e.g., 02:00)
        duration = w_min - s_min
    
    # Sanity check: sleep duration should be 1-16 hours
    if duration < 60 or duration > 16 * 60:
        return None
    
    return duration


def format_duration(minutes):
    """Format duration in minutes to Xh Ym string."""
    if minutes is None:
        return "?"
    h = minutes // 60
    m = minutes % 60
    return f"{h}h {m:02d}m"


def analyze_sleep(days=7):
    """Analyze recent sleep patterns."""
    entries = load_diary()
    if not entries:
        return None
    
    entries.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    # Deduplicate by date (keep the latest entry per date)
    seen_dates = set()
    unique_entries = []
    for e in entries:
        d = e.get('date', '')
        if d not in seen_dates:
            seen_dates.add(d)
            unique_entries.append(e)
    
    recent = unique_entries[:days]
    
    results = []
    for e in recent:
        si = e.get('sleep_in', '')
        wu = e.get('wake_up', '')
        duration = sleep_duration_minutes(si, wu)
        
        s_parsed = parse_hhmm(si)
        sleep_hour = s_parsed[0] if s_parsed else None
        is_late = sleep_hour is not None and 2 <= sleep_hour < 8
        
        results.append({
            'date': e.get('date', ''),
            'sleep_in': f"{s_parsed[0]:02d}:{s_parsed[1]:02d}" if s_parsed else str(si),
            'wake_up': f"{parse_hhmm(wu)[0]:02d}:{parse_hhmm(wu)[1]:02d}" if parse_hhmm(wu) else str(wu),
            'duration_min': duration,
            'duration_fmt': format_duration(duration),
            'is_late': is_late,
            'mood': e.get('mood', ''),
            'energy': e.get('energy', ''),
        })
    
    durations = [r['duration_min'] for r in results if r['duration_min'] is not None]
    late_count = sum(1 for r in results if r['is_late'])
    
    summary = {
        'period_days': days,
        'entries_analyzed': len(results),
        'avg_duration_min': round(statistics.mean(durations), 1) if durations else None,
        'avg_duration_fmt': format_duration(round(statistics.mean(durations))) if durations else '?',
        'min_duration_fmt': format_duration(min(durations)) if durations else '?',
        'max_duration_fmt': format_duration(max(durations)) if durations else '?',
        'late_sleep_days': late_count,
        'late_sleep_ratio': round(late_count / len(results), 2) if results else 0,
        'entries': results,
    }
    
    return summary


def main():
    import argparse
    ap = argparse.ArgumentParser(description='Analyze Leo\'s sleep patterns')
    ap.add_argument('--days', type=int, default=7, help='Number of days to analyze')
    ap.add_argument('--format', choices=['json', 'text'], default='text')
    args = ap.parse_args()
    
    result = analyze_sleep(args.days)
    
    if args.format == 'json':
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if not result:
            print("No sleep data available.")
            return
        
        print(f"\n🌙 睡眠分析（最近 {result['period_days']} 天）")
        print(f"{'='*50}")
        print(f"平均睡眠時長：{result['avg_duration_fmt']}")
        print(f"最短：{result['min_duration_fmt']}  最長：{result['max_duration_fmt']}")
        print(f"晚睡天數：{result['late_sleep_days']}/{result['entries_analyzed']} "
              f"({result['late_sleep_ratio']*100:.0f}%)")
        print()
        print(f"{'日期':<12s} {'入睡':>6s} {'起床':>6s} {'時長':>8s} {'晚睡':>4s} {'心情':>4s}")
        print(f"{'-'*12} {'-'*6} {'-'*6} {'-'*8} {'-'*4} {'-'*4}")
        for r in result['entries']:
            late_icon = '⚠️' if r['is_late'] else '✅'
            print(f"{r['date']:<12s} {r['sleep_in']:>6s} {r['wake_up']:>6s} "
                  f"{r['duration_fmt']:>8s} {late_icon:>4s} {r['mood']:>4s}")


if __name__ == '__main__':
    main()
