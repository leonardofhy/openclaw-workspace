#!/usr/bin/env python3
"""System Scanner — scans OpenClaw workspace for critical issues and improvement opportunities.

Checks:
  - Secrets & credentials
  - API connectivity (Todoist, Google Calendar, Email)
  - Python script imports
  - Git status
  - Memory file coverage
  - Delivery queue
  - Gateway log errors
  - OpenClaw config (cron, channels, compaction)
  - Disk space
  - Sleep pattern warnings (from tags)
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent.parent.parent  # workspace root
SECRETS = WORKSPACE / 'secrets'
MEMORY = WORKSPACE / 'memory'
TAGS = MEMORY / 'tags'
SCRIPTS = WORKSPACE / 'skills' / 'leo-diary' / 'scripts'
OPENCLAW_DIR = Path.home() / '.openclaw'
LOGS = OPENCLAW_DIR / 'logs'
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ)

# ─────────────────────────── helpers ────────────────────────────

results = []

def check(label, status, detail='', fix=''):
    """status: 'ok' | 'warn' | 'crit' | 'info'"""
    results.append({'label': label, 'status': status, 'detail': detail, 'fix': fix})

def run(cmd, **kw):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10, **kw)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return -1, '', str(e)

# ─────────────────────────── checks ─────────────────────────────

def check_secrets():
    required = [
        'secrets/email_ops.env',
        'secrets/todoist.env',
        'secrets/google-service-account.json',
    ]
    for rel in required:
        p = WORKSPACE / rel
        if not p.exists():
            check(f'Secret: {rel}', 'crit', 'File missing', f'Restore {rel}')
        elif p.stat().st_size < 10:
            check(f'Secret: {rel}', 'warn', 'File is empty/tiny', f'Check {rel} content')
        else:
            check(f'Secret: {rel}', 'ok')


def check_apis():
    sys.path.insert(0, str(SCRIPTS))

    # Todoist
    try:
        import importlib.util, sys as _sys
        spec = importlib.util.spec_from_file_location('todoist_sync', str(SCRIPTS / 'todoist_sync.py'))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        result = mod.main(['--limit', '1'])
        check('Todoist API', 'ok', 'Reachable')
    except SystemExit:
        check('Todoist API', 'ok', 'Reachable')
    except Exception as e:
        # Fallback: try direct API call
        try:
            env_path = WORKSPACE / 'secrets' / 'todoist.env'
            token = None
            for line in env_path.read_text().splitlines():
                if 'TODOIST_API_TOKEN' in line:
                    token = line.split('=', 1)[-1].strip()
            if token:
                import urllib.request
                req = urllib.request.Request('https://api.todoist.com/api/v1/tasks?limit=1',
                                             headers={'Authorization': f'Bearer {token}'})
                urllib.request.urlopen(req, timeout=5)
                check('Todoist API', 'ok', 'Reachable')
            else:
                check('Todoist API', 'crit', 'Token not found in env', 'Check secrets/todoist.env')
        except Exception as e2:
            check('Todoist API', 'crit', str(e2)[:80], 'Check secrets/todoist.env')

    # Google Calendar
    try:
        from gcal_today import get_events
        evts = get_events(days_ahead=0, days_range=1)
        check('Google Calendar API', 'ok', f'{len(evts)} events today')
    except Exception as e:
        check('Google Calendar API', 'crit', str(e)[:80], 'Check secrets/google-service-account.json')

    # Diary (Google Sheets)
    try:
        from read_diary import load_diary
        entries = load_diary()
        if entries:
            latest = max(e.get('date', '') for e in entries)
            days_ago = (NOW.date() - datetime.strptime(latest, '%Y-%m-%d').date()).days
            if days_ago > 3:
                check('Diary data', 'warn', f'Latest entry {days_ago} days ago ({latest})', 'Check sync script / Google Sheets access')
            else:
                check('Diary data', 'ok', f'{len(entries)} entries, latest {latest}')
        else:
            check('Diary data', 'crit', 'No entries loaded', 'Check read_diary.py and Google Sheets credentials')
    except Exception as e:
        check('Diary data', 'crit', str(e)[:80])


def check_git():
    code, out, err = run(['git', 'status', '--short'], cwd=str(WORKSPACE))
    if code != 0:
        check('Git status', 'warn', f'git error: {err[:60]}')
        return
    if out:
        lines = out.strip().splitlines()
        check('Git uncommitted changes', 'warn', f'{len(lines)} changed files', 'git add -A && git commit && git push')
    else:
        check('Git status', 'ok', 'Clean')

    # Check remote sync
    code2, out2, _ = run(['git', 'log', 'origin/main..HEAD', '--oneline'], cwd=str(WORKSPACE))
    if code2 == 0 and out2:
        n = len(out2.strip().splitlines())
        check('Git unpushed commits', 'warn', f'{n} commits not pushed', 'git push')
    elif code2 == 0:
        check('Git remote sync', 'ok', 'Up to date')


def check_memory():
    today = NOW.date()
    missing = []
    for i in range(7):
        d = (today - timedelta(days=i)).strftime('%Y-%m-%d')
        if not (MEMORY / f'{d}.md').exists():
            missing.append(d)
    if missing:
        check('Memory file coverage', 'warn', f'Missing: {", ".join(missing[:3])}{"..." if len(missing)>3 else ""}',
              'Run diary sync or create missing memory files')
    else:
        check('Memory file coverage', 'ok', '7 recent days present')

    # Check MEMORY.md freshness
    mm = WORKSPACE / 'MEMORY.md'
    if mm.exists():
        age_days = (NOW.timestamp() - mm.stat().st_mtime) / 86400
        if age_days > 14:
            check('MEMORY.md freshness', 'info', f'Last updated {int(age_days)} days ago', 'Consider updating long-term memory')
        else:
            check('MEMORY.md freshness', 'ok', f'Updated {int(age_days)} days ago')


def check_delivery_queue():
    dq = OPENCLAW_DIR / 'delivery-queue'
    if dq.exists():
        items = [f for f in dq.iterdir() if f.is_file()]
        if items:
            check('Delivery queue', 'warn', f'{len(items)} items stuck in queue', 'Check gateway logs for delivery errors')
        else:
            check('Delivery queue', 'ok', 'Empty')
    else:
        check('Delivery queue', 'ok', 'No queue dir')


def check_gateway_logs():
    log = LOGS / 'gateway.log'
    if not log.exists():
        check('Gateway log', 'warn', 'Log file not found')
        return

    # Read last 200 lines
    code, out, _ = run(['tail', '-200', str(log)])
    lines = out.splitlines()

    errors = [l for l in lines if ' error ' in l.lower() or '[error]' in l.lower()]
    # Only count recent disconnects (last 1 hour, log timestamps are UTC)
    cutoff_utc = (NOW.astimezone(timezone.utc) - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')
    disconnects = [l for l in lines if 'WebSocket connection closed with code 1006' in l
                   and len(l) >= 16 and l[:16] >= cutoff_utc]
    config_errors = [l for l in lines if 'INVALID_REQUEST' in l or 'invalid config' in l.lower()]

    if config_errors:
        check('Gateway config errors', 'crit', f'{len(config_errors)} config error(s) in recent logs',
              'Run: openclaw status to check config')
    elif errors:
        check('Gateway errors', 'warn', f'{len(errors)} error line(s) in recent logs')
    else:
        check('Gateway logs', 'ok', 'No errors in last 200 lines')

    if len(disconnects) >= 3:
        check('Discord WebSocket', 'warn', f'{len(disconnects)} disconnect(s) in last hour',
              'Restart gateway: openclaw gateway restart')
    else:
        check('Discord WebSocket', 'ok', 'No recent disconnects')


def check_openclaw_config():
    config_path = OPENCLAW_DIR / 'openclaw.json'
    if not config_path.exists():
        check('OpenClaw config', 'warn', 'openclaw.json not found')
        return

    try:
        cfg = json.loads(config_path.read_text())
    except Exception as e:
        check('OpenClaw config', 'crit', f'Parse error: {e}')
        return

    # Check compaction
    compaction = cfg.get('agents', {}).get('defaults', {}).get('compaction', {})
    mode = compaction.get('mode', 'default')
    if mode == 'safeguard':
        check('Compaction mode', 'warn', '"safeguard" — may allow context to overflow',
              'Change to "default" for more aggressive compaction')
    else:
        check('Compaction mode', 'ok', f'mode={mode}')

    # Check contextPruning
    pruning = cfg.get('agents', {}).get('defaults', {}).get('contextPruning', {})
    if not pruning or pruning.get('mode') == 'off':
        check('Context pruning', 'warn', 'Disabled — context may grow unbounded',
              'Enable contextPruning with ttl and ratio settings')
    else:
        ttl = pruning.get("ttl", "?")
        check('Context pruning', 'ok', f'mode={pruning.get("mode")}, ttl={ttl}')

    # Check cron jobs for expensive models
    cron_jobs = cfg.get('cron', {}).get('jobs', [])
    expensive = [j.get('id', j.get('command', '?'))[:40] for j in cron_jobs
                 if 'opus' in j.get('model', '').lower()]
    if expensive:
        check('Cron model cost', 'warn',
              f'{len(expensive)} cron job(s) using expensive opus model',
              'Downgrade recurring crons to sonnet to save cost')
    elif cron_jobs:
        check('Cron model cost', 'ok', f'{len(cron_jobs)} jobs, no opus usage')

    # Check channels
    channels = cfg.get('channels', {})
    for ch in ['discord', 'imessage']:
        ch_cfg = channels.get(ch, {})
        if ch_cfg.get('enabled'):
            check(f'Channel: {ch}', 'ok', 'Enabled')
        else:
            check(f'Channel: {ch}', 'info', 'Disabled or not configured')


def check_disk():
    code, out, _ = run(['df', '-h', '/'])
    if code == 0 and out:
        lines = out.splitlines()
        if len(lines) >= 2:
            parts = lines[1].split()
            try:
                cap = parts[4].rstrip('%')
                avail = parts[3]
                pct = int(cap)
                if pct >= 90:
                    check('Disk space', 'crit', f'{pct}% used, {avail} available', 'Free up disk space')
                elif pct >= 75:
                    check('Disk space', 'warn', f'{pct}% used, {avail} available')
                else:
                    check('Disk space', 'ok', f'{pct}% used, {avail} available')
            except Exception:
                check('Disk space', 'info', out.splitlines()[-1])


def check_sleep_patterns():
    if not TAGS.exists():
        return
    today = NOW.date()
    recent = []
    for i in range(7):
        d = (today - timedelta(days=i+1)).strftime('%Y-%m-%d')
        p = TAGS / f'{d}.json'
        if p.exists():
            try:
                t = json.loads(p.read_text())
                recent.append(t)
            except Exception:
                pass

    if len(recent) < 3:
        return

    late = sum(1 for t in recent if t.get('late_sleep'))
    avg_sleep = None
    sleep_vals = [t.get('metrics', {}).get('sleep_hours') for t in recent
                  if t.get('metrics', {}).get('sleep_hours')]
    if sleep_vals:
        avg_sleep = sum(sleep_vals) / len(sleep_vals)

    if late >= 5:
        check('Sleep pattern', 'warn',
              f'{late}/{len(recent)} late nights, avg {avg_sleep:.1f}h' if avg_sleep else f'{late}/{len(recent)} late nights',
              'Aim for 01:00 bedtime')
    elif avg_sleep and avg_sleep < 6.5:
        check('Sleep pattern', 'warn', f'Avg {avg_sleep:.1f}h (< 6.5h target)',
              'Prioritise earlier bedtime')
    else:
        status_str = f'avg {avg_sleep:.1f}h, {late}/{len(recent)} late' if avg_sleep else f'{late}/{len(recent)} late nights'
        check('Sleep pattern', 'ok', status_str)


def check_python_scripts():
    key_scripts = [
        SCRIPTS / 'read_diary.py',
        SCRIPTS / 'todoist_sync.py',
        SCRIPTS / 'gcal_today.py',
        SCRIPTS / 'daily_coach_v3.py',
        SCRIPTS / 'sleep_calc.py',
    ]
    missing = [s.name for s in key_scripts if not s.exists()]
    if missing:
        check('Key scripts', 'crit', f'Missing: {", ".join(missing)}', 'Restore from git or recreate')
    else:
        check('Key scripts', 'ok', f'{len(key_scripts)} scripts present')


# ─────────────────────────── run all ────────────────────────────

def run_all():
    check_secrets()
    check_apis()
    check_git()
    check_memory()
    check_delivery_queue()
    check_gateway_logs()
    check_openclaw_config()
    check_disk()
    check_sleep_patterns()
    check_python_scripts()


def print_report():
    icons = {'ok': '✅', 'warn': '⚠️ ', 'crit': '🔴', 'info': 'ℹ️ '}
    order = ['crit', 'warn', 'info', 'ok']

    crits = [r for r in results if r['status'] == 'crit']
    warns = [r for r in results if r['status'] == 'warn']
    infos = [r for r in results if r['status'] == 'info']
    oks   = [r for r in results if r['status'] == 'ok']

    print(f"\n{'='*60}")
    print(f"🔍 System Scanner Report — {NOW.strftime('%Y-%m-%d %H:%M')} (Taipei)")
    print(f"{'='*60}")
    print(f"Summary: {len(crits)} 🔴 critical  {len(warns)} ⚠️  warn  {len(infos)} ℹ️  info  {len(oks)} ✅ ok\n")

    for group in [crits, warns, infos, oks]:
        for r in group:
            icon = icons[r['status']]
            line = f"{icon}  {r['label']}"
            if r['detail']:
                line += f"  —  {r['detail']}"
            print(line)
            if r['fix']:
                print(f"     → Fix: {r['fix']}")

    print(f"\n{'='*60}")
    return len(crits), len(warns)


if __name__ == '__main__':
    run_all()
    crits, warns = print_report()
    sys.exit(1 if crits > 0 else 0)
