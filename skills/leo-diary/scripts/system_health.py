#!/usr/bin/env python3
"""System health check - verify all Little Leo infrastructure is working."""
import json
import importlib
import sys
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'lib'))
from common import TZ, now as _now, WORKSPACE, MEMORY as MEMORY_DIR, SECRETS as SECRETS_DIR, SCRIPTS as SCRIPTS_DIR

sys.path.insert(0, str(SCRIPTS_DIR))

CHECKS = []
PASS = 0
FAIL = 0
WARN = 0


def check(name, fn):
    global PASS, FAIL, WARN
    try:
        result = fn()
        if result is True:
            CHECKS.append(('✅', name, ''))
            PASS += 1
        elif result is False:
            CHECKS.append(('❌', name, ''))
            FAIL += 1
        elif isinstance(result, str):
            if result.startswith('WARN:'):
                CHECKS.append(('⚠️', name, result[5:].strip()))
                WARN += 1
            else:
                CHECKS.append(('✅', name, result))
                PASS += 1
    except Exception as e:
        CHECKS.append(('❌', name, str(e)[:100]))
        FAIL += 1


def check_secrets():
    """Verify all secret files exist."""
    files = ['email_ops.env', 'todoist.env', 'google-service-account.json']
    missing = [f for f in files if not (SECRETS_DIR / f).exists()]
    if missing:
        return f"WARN: Missing: {', '.join(missing)}"
    return True


def check_imports():
    """Verify all critical Python modules import correctly."""
    modules = ['read_diary', 'email_utils', 'todoist_sync', 'gcal_today', 'sleep_calc']
    failed = []
    for m in modules:
        try:
            importlib.import_module(m)
        except Exception as e:
            failed.append(f"{m}: {e}")
    if failed:
        return False
    return f"{len(modules)} modules OK"


def check_diary():
    """Verify diary data is accessible and recent."""
    from read_diary import load_diary
    entries = load_diary()
    if not entries:
        return False
    latest = max(e.get('date', '') for e in entries)
    today = _now().strftime('%Y-%m-%d')
    yesterday = (_now() - timedelta(days=1)).strftime('%Y-%m-%d')
    if latest < yesterday:
        return f"WARN: Latest diary is {latest} (>1 day old)"
    return f"{len(entries)} entries, latest: {latest}"


def check_todoist():
    """Verify Todoist API is reachable."""
    from todoist_sync import load_token, get
    token = load_token()
    tasks = get('/tasks', token, params={'limit': 1})
    count = len(tasks.get('results', []))
    return f"API OK, tasks accessible"


def check_calendar():
    """Verify Google Calendar API works."""
    from gcal_today import get_events
    events = get_events(days_ahead=0, days_range=7)
    return f"API OK, {len(events)} events in next 7 days"


def check_email():
    """Verify email config is loadable (does NOT send)."""
    from email_utils import _load_config
    cfg = _load_config()
    if not cfg.get('EMAIL_SENDER') or not cfg.get('EMAIL_PASSWORD'):
        return False
    return f"Config OK: {cfg['EMAIL_SENDER']}"


def check_memory_today():
    """Check if today's memory file exists."""
    today = _now().strftime('%Y-%m-%d')
    f = MEMORY_DIR / f"{today}.md"
    if f.exists():
        size = f.stat().st_size
        return f"Exists ({size} bytes)"
    return "WARN: Today's memory file not created yet"


def check_memory_gaps():
    """Check for gaps in recent memory files (last 7 days)."""
    today = _now()
    missing = []
    for i in range(7):
        d = (today - timedelta(days=i)).strftime('%Y-%m-%d')
        if not (MEMORY_DIR / f"{d}.md").exists():
            missing.append(d)
    if len(missing) > 3:
        return f"WARN: {len(missing)}/7 recent days missing: {missing[:3]}..."
    elif missing:
        return f"{7-len(missing)}/7 days present (missing: {', '.join(missing)})"
    return "All 7 recent days present"


def check_sleep_patterns():
    """Quick sleep health check."""
    from sleep_calc import analyze_sleep
    result = analyze_sleep(7)
    if not result:
        return "WARN: No sleep data"
    late_ratio = result['late_sleep_ratio']
    avg = result['avg_duration_fmt']
    if late_ratio > 0.7:
        return f"WARN: {late_ratio*100:.0f}% late sleep, avg {avg}"
    return f"Avg {avg}, {result['late_sleep_days']}/{result['entries_analyzed']} late days"


def check_no_hardcoded_creds():
    """Scan for hardcoded credentials outside secrets/."""
    # Build patterns dynamically to avoid self-matching
    p1 = 'sbyp' + ' hams'
    p2 = 'gzns' + ' swbq'
    patterns = [p1, p2]
    found = []
    for pattern in patterns:
        for ext in ['*.py', '*.md']:
            for f in WORKSPACE.rglob(ext):
                skip_dirs = {'secrets', 'venv', '__pycache__'}
                if any(s in str(f) for s in skip_dirs):
                    continue
                if f.name == 'system_health.py':
                    continue  # skip self
                try:
                    if pattern in f.read_text():
                        found.append(str(f.relative_to(WORKSPACE)))
                except (OSError, UnicodeDecodeError):
                    pass
    if found:
        return f"WARN: Credentials found in: {', '.join(found[:3])}"
    return True


def main():
    print(f"\n🏥 Little Leo System Health Check")
    print(f"{'='*55}")
    print(f"Time: {_now().strftime('%Y-%m-%d %H:%M:%S')} (Asia/Taipei)\n")

    check("Secrets files", check_secrets)
    check("Python module imports", check_imports)
    check("Diary data access", check_diary)
    check("Todoist API", check_todoist)
    check("Google Calendar API", check_calendar)
    check("Email config", check_email)
    check("Today's memory file", check_memory_today)
    check("Recent memory coverage", check_memory_gaps)
    check("Sleep patterns", check_sleep_patterns)
    check("No hardcoded credentials", check_no_hardcoded_creds)

    print(f"{'Status':<4s} {'Check':<30s} {'Details'}")
    print(f"{'-'*4} {'-'*30} {'-'*40}")
    for icon, name, detail in CHECKS:
        print(f"{icon:<4s} {name:<30s} {detail}")

    print(f"\n{'='*55}")
    print(f"Results: {PASS} ✅  {WARN} ⚠️  {FAIL} ❌")

    if FAIL > 0:
        print("⛔ CRITICAL ISSUES FOUND — fix before next cron cycle!")
        return 1
    elif WARN > 0:
        print("⚠️ Some warnings — review when convenient.")
        return 0
    else:
        print("💚 All systems nominal!")
        return 0


if __name__ == '__main__':
    sys.exit(main())
