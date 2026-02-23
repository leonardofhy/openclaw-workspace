#!/usr/bin/env python3
"""System Scanner v2 — scans OpenClaw workspace for critical issues and improvement opportunities.

Usage:
  python3 scan.py               # full report
  python3 scan.py --quiet       # only problems (warn/crit)
  python3 scan.py --json        # machine-readable JSON
  python3 scan.py --category config  # specific category only
  python3 scan.py --history     # show last 5 scan summaries

Categories: secrets, apis, git, memory, delivery, gateway, config, disk, health, scripts, channels
"""
import argparse
import json
import os
import smtplib
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
SECRETS   = WORKSPACE / 'secrets'
MEMORY    = WORKSPACE / 'memory'
TAGS      = MEMORY / 'tags'
SCRIPTS   = WORKSPACE / 'skills' / 'leo-diary' / 'scripts'
OPENCLAW  = Path.home() / '.openclaw'
LOGS      = OPENCLAW / 'logs'
HISTORY   = MEMORY / 'scanner-history.jsonl'
TZ        = timezone(timedelta(hours=8))
NOW       = datetime.now(TZ)

# ─────────────── state ───────────────

results: list[dict] = []

def check(label: str, status: str, detail: str = '', fix: str = '', category: str = 'general'):
    """Record a check result. status: ok | warn | crit | info"""
    results.append({'label': label, 'status': status, 'detail': detail, 'fix': fix, 'category': category})

def sh(cmd, cwd=None, timeout=10):
    """Run shell command; returns (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return -1, '', str(e)

def load_env(path: Path) -> dict:
    env = {}
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return env

# ─────────────── checks ───────────────

def check_secrets():
    cat = 'secrets'
    required = [
        ('secrets/email_ops.env', 20),
        ('secrets/todoist.env', 10),
        ('secrets/google-service-account.json', 50),
    ]
    for rel, min_size in required:
        p = WORKSPACE / rel
        if not p.exists():
            check(f'Secret: {Path(rel).name}', 'crit', 'File missing', f'Restore {rel}', cat)
        elif p.stat().st_size < min_size:
            check(f'Secret: {Path(rel).name}', 'warn', 'File suspiciously small', f'Verify {rel}', cat)
        else:
            check(f'Secret: {Path(rel).name}', 'ok', '', '', cat)


def check_apis():
    cat = 'apis'
    sys.path.insert(0, str(SCRIPTS))

    # Todoist — direct HTTP check
    env = load_env(WORKSPACE / 'secrets' / 'todoist.env')
    token = env.get('TODOIST_API_TOKEN', '')
    if not token:
        check('Todoist API', 'crit', 'Token missing', 'Check secrets/todoist.env', cat)
    else:
        try:
            req = urllib.request.Request(
                'https://api.todoist.com/api/v1/tasks?limit=1',
                headers={'Authorization': f'Bearer {token}'}
            )
            urllib.request.urlopen(req, timeout=6)
            check('Todoist API', 'ok', 'Reachable', '', cat)
        except Exception as e:
            check('Todoist API', 'crit', str(e)[:70], 'Check token / internet', cat)

    # Google Calendar
    try:
        from gcal_today import get_events
        evts = get_events(days_ahead=0, days_range=1)
        check('Google Calendar API', 'ok', f'{len(evts)} events today', '', cat)
    except Exception as e:
        check('Google Calendar API', 'crit', str(e)[:70], 'Check google-service-account.json', cat)

    # Diary data freshness
    try:
        from read_diary import load_diary
        entries = load_diary()
        if entries:
            latest = max(e.get('date', '') for e in entries)
            days_ago = (NOW.date() - datetime.strptime(latest, '%Y-%m-%d').date()).days
            if days_ago > 3:
                check('Diary data', 'warn', f'Stale — latest {days_ago}d ago ({latest})',
                      'Check Google Sheets sync', cat)
            else:
                check('Diary data', 'ok', f'{len(entries)} entries, latest {latest}', '', cat)
        else:
            check('Diary data', 'crit', 'No entries loaded', 'Check read_diary.py', cat)
    except Exception as e:
        check('Diary data', 'crit', str(e)[:70], '', cat)


def check_email():
    cat = 'apis'
    env = load_env(WORKSPACE / 'secrets' / 'email_ops.env')
    host = env.get('SMTP_HOST', 'smtp.gmail.com')
    port = int(env.get('SMTP_PORT', '587'))
    # Support both naming conventions
    user = env.get('SMTP_USER', env.get('EMAIL_SENDER', ''))
    pwd  = env.get('SMTP_PASS', env.get('SMTP_PASSWORD', env.get('EMAIL_PASSWORD', '')))
    if not user or not pwd:
        check('Email SMTP', 'warn', 'Credentials missing in email_ops.env', '', cat)
        return
    try:
        with smtplib.SMTP(host, port, timeout=6) as s:
            s.starttls()
            s.login(user, pwd)
        check('Email SMTP', 'ok', f'{user} authenticated', '', cat)
    except Exception as e:
        check('Email SMTP', 'warn', str(e)[:70], 'Check SMTP credentials / App Password', cat)


def check_imsg():
    cat = 'channels'
    code, out, err = sh(['imsg', '--version'])
    if code != 0:
        check('imsg binary', 'crit', 'Not found or broken', 'brew install steipete/tap/imsg', cat)
        return
    version = out.strip() or 'unknown'
    # Test read access
    code2, out2, err2 = sh(['imsg', 'chats', '--limit', '1'])
    if code2 != 0:
        check('imsg (iMessage)', 'warn', f'v{version} installed but chats failed: {err2[:50]}',
              'Grant Full Disk Access to Terminal/node in System Settings', cat)
    else:
        check('imsg (iMessage)', 'ok', f'v{version}, DB readable', '', cat)


def check_git():
    cat = 'git'
    code, out, err = sh(['git', 'status', '--short'], cwd=str(WORKSPACE))
    if code != 0:
        check('Git status', 'warn', f'Error: {err[:60]}', '', cat)
        return
    if out:
        n = len(out.strip().splitlines())
        check('Git uncommitted', 'warn', f'{n} changed file(s)',
              'git add -A && git commit && git push', cat)
    else:
        check('Git status', 'ok', 'Clean', '', cat)

    code2, out2, _ = sh(['git', 'log', 'origin/main..HEAD', '--oneline'], cwd=str(WORKSPACE))
    if code2 == 0 and out2:
        check('Git unpushed', 'warn', f'{len(out2.splitlines())} commit(s) ahead', 'git push', cat)
    elif code2 == 0:
        check('Git remote sync', 'ok', 'Up to date', '', cat)


def check_memory():
    cat = 'memory'
    today = NOW.date()
    missing = [
        (today - timedelta(days=i)).strftime('%Y-%m-%d')
        for i in range(7)
        if not (MEMORY / f'{(today - timedelta(days=i)).strftime("%Y-%m-%d")}.md').exists()
    ]
    if missing:
        check('Memory coverage', 'warn',
              f'Missing {len(missing)}/7 days: {", ".join(missing[:3])}{"…" if len(missing) > 3 else ""}',
              'Run diary sync or create missing files', cat)
    else:
        check('Memory coverage', 'ok', '7 recent days present', '', cat)

    mm = WORKSPACE / 'MEMORY.md'
    if mm.exists():
        age = (NOW.timestamp() - mm.stat().st_mtime) / 86400
        if age > 14:
            check('MEMORY.md freshness', 'info', f'Last updated {int(age)}d ago',
                  'Review and update long-term memory', cat)
        else:
            check('MEMORY.md freshness', 'ok', f'Updated {int(age)}d ago', '', cat)

    # Tags coverage — check last 7 diary days have tags
    if TAGS.exists():
        missing_tags = [
            (today - timedelta(days=i+1)).strftime('%Y-%m-%d')
            for i in range(7)
            if not (TAGS / f'{(today - timedelta(days=i+1)).strftime("%Y-%m-%d")}.json').exists()
        ]
        if len(missing_tags) > 3:
            check('Tags coverage', 'warn',
                  f'Missing tags for {len(missing_tags)}/7 recent days',
                  'Run: python3 skills/leo-diary/scripts/generate_tags.py', cat)
        else:
            check('Tags coverage', 'ok', f'Tags present for {7 - len(missing_tags)}/7 days', '', cat)


def check_delivery():
    cat = 'delivery'
    dq = OPENCLAW / 'delivery-queue'
    if dq.exists():
        stuck = [f for f in dq.iterdir() if f.is_file()]
        if stuck:
            check('Delivery queue', 'warn', f'{len(stuck)} message(s) stuck',
                  'Check gateway logs; may clear manually', cat)
        else:
            check('Delivery queue', 'ok', 'Empty', '', cat)
    else:
        check('Delivery queue', 'ok', 'No queue dir', '', cat)


def check_gateway():
    cat = 'gateway'
    log = LOGS / 'gateway.log'
    if not log.exists():
        check('Gateway log', 'warn', 'Log file not found', '', cat)
        return

    code, out, _ = sh(['tail', '-300', str(log)])
    lines = out.splitlines()

    # Config errors — only recent (last 2h), exclude one-off config.patch attempts
    cutoff24 = (NOW.astimezone(timezone.utc) - timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M')
    cfg_errs = [l for l in lines if ('INVALID_REQUEST' in l or 'invalid config' in l.lower())
                and 'config.patch' not in l
                and len(l) >= 16 and l[:16] >= cutoff24]
    if cfg_errs:
        check('Gateway config', 'crit', f'{len(cfg_errs)} config error(s) in last 2h',
              'Run: openclaw status', cat)
    else:
        # General errors (exclude known noise)
        errs = [l for l in lines if ('[error]' in l.lower())
                and 'imsg not found' not in l.lower()
                and len(l) >= 16 and l[:16] >= cutoff24]
        if errs:
            check('Gateway errors', 'warn', f'{len(errs)} error line(s) in last 24h', '', cat)
        else:
            check('Gateway logs', 'ok', 'Clean (last 24h)', '', cat)

    # Discord disconnects — last 1 hour only (log timestamps UTC)
    cutoff = (NOW.astimezone(timezone.utc) - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')
    disc_dc = [l for l in lines
               if 'WebSocket connection closed with code 1006' in l
               and len(l) >= 16 and l[:16] >= cutoff]
    if len(disc_dc) >= 3:
        check('Discord WebSocket', 'warn', f'{len(disc_dc)} fatal disconnect(s) in last hour',
              'openclaw gateway restart', cat)
    else:
        check('Discord WebSocket', 'ok', 'Stable', '', cat)

    # Cron job health — check ~/.openclaw/cron/runs/ for recent activity
    runs_dir = OPENCLAW / 'cron' / 'runs'
    if runs_dir.exists():
        cutoff_ts = (NOW.timestamp() - 25 * 3600) * 1000  # ms
        recent_runs = []
        for f in runs_dir.iterdir():
            if f.suffix == '.jsonl' and f.stat().st_mtime > (NOW.timestamp() - 25 * 3600):
                recent_runs.append(f.name)
        if recent_runs:
            check('Cron activity', 'ok', f'{len(recent_runs)} job run(s) in last 25h', '', cat)
        else:
            check('Cron activity', 'warn', 'No cron runs in last 25h',
                  'Check cron jobs: openclaw status', cat)
    else:
        check('Cron activity', 'info', 'No runs directory found', '', cat)


def check_config():
    cat = 'config'
    cfg_path = OPENCLAW / 'openclaw.json'
    if not cfg_path.exists():
        check('OpenClaw config', 'warn', 'openclaw.json not found', '', cat)
        return

    try:
        cfg = json.loads(cfg_path.read_text())
    except Exception as e:
        check('OpenClaw config', 'crit', f'Parse error: {e}', '', cat)
        return

    # Compaction
    mode = cfg.get('agents', {}).get('defaults', {}).get('compaction', {}).get('mode', 'default')
    if mode == 'safeguard':
        check('Compaction', 'warn', '"safeguard" risks context overflow',
              'Set to "default"', cat)
    else:
        check('Compaction', 'ok', f'mode={mode}', '', cat)

    # Context pruning
    pruning = cfg.get('agents', {}).get('defaults', {}).get('contextPruning', {})
    if not pruning or pruning.get('mode', 'off') == 'off':
        check('Context pruning', 'warn', 'Disabled — context may grow unbounded',
              'Enable cache-ttl mode', cat)
    else:
        check('Context pruning', 'ok', f'mode={pruning.get("mode")}, ttl={pruning.get("ttl","?")}', '', cat)

    # Cron model cost
    jobs = cfg.get('cron', {}).get('jobs', [])
    opus_jobs = [j.get('id', '?')[:35] for j in jobs if 'opus' in j.get('model', '').lower()]
    if opus_jobs:
        check('Cron model cost', 'warn', f'{len(opus_jobs)} job(s) using opus (expensive)',
              'Downgrade to sonnet', cat)
    elif jobs:
        check('Cron model cost', 'ok', f'{len(jobs)} jobs, no opus', '', cat)

    # OpenClaw update available
    update_file = OPENCLAW / 'update-check.json'
    if update_file.exists():
        try:
            uc = json.loads(update_file.read_text())
            if uc.get('updateAvailable'):
                latest = uc.get('latest', '?')
                check('OpenClaw update', 'info', f'v{latest} available',
                      'Run: openclaw update', cat)
            else:
                check('OpenClaw update', 'ok', 'Up to date', '', cat)
        except Exception:
            pass


def check_disk():
    cat = 'disk'
    code, out, _ = sh(['df', '-h', '/'])
    if code == 0 and out:
        parts = out.splitlines()[-1].split()
        try:
            pct  = int(parts[4].rstrip('%'))
            avail = parts[3]
            status = 'crit' if pct >= 90 else 'warn' if pct >= 75 else 'ok'
            fix = 'Free up disk space urgently' if pct >= 90 else ('Consider cleanup' if pct >= 75 else '')
            check('Disk space', status, f'{pct}% used, {avail} free', fix, cat)
        except Exception:
            check('Disk space', 'info', out.splitlines()[-1], '', cat)


def check_health():
    cat = 'health'
    if not TAGS.exists():
        return
    today = NOW.date()
    recent = []
    for i in range(7):
        p = TAGS / f'{(today - timedelta(days=i+1)).strftime("%Y-%m-%d")}.json'
        if p.exists():
            try:
                recent.append(json.loads(p.read_text()))
            except Exception:
                pass
    if len(recent) < 3:
        return

    late = sum(1 for t in recent if t.get('late_sleep'))
    sleep_vals = [t['metrics']['sleep_hours'] for t in recent
                  if (t.get('metrics') or {}).get('sleep_hours')]
    avg_sleep = sum(sleep_vals) / len(sleep_vals) if sleep_vals else None
    avg_str = f', avg {avg_sleep:.1f}h' if avg_sleep else ''

    if late >= 5:
        check('Sleep pattern', 'warn', f'{late}/{len(recent)} late nights{avg_str}',
              'Target 01:00 bedtime; put phone away', cat)
    elif avg_sleep and avg_sleep < 6.5:
        check('Sleep pattern', 'warn', f'Avg {avg_sleep:.1f}h < 6.5h target',
              'Prioritise earlier bedtime', cat)
    else:
        check('Sleep pattern', 'ok', f'{late}/{len(recent)} late nights{avg_str}', '', cat)


def check_scripts():
    cat = 'scripts'
    key = [
        SCRIPTS / 'read_diary.py',
        SCRIPTS / 'todoist_sync.py',
        SCRIPTS / 'gcal_today.py',
        SCRIPTS / 'daily_coach_v3.py',
        SCRIPTS / 'sleep_calc.py',
        SCRIPTS / 'generate_tags.py',
        SCRIPTS / 'email_utils.py',
    ]
    missing = [s.name for s in key if not s.exists()]
    if missing:
        check('Key scripts', 'crit', f'Missing: {", ".join(missing)}', 'Restore from git', cat)
    else:
        check('Key scripts', 'ok', f'All {len(key)} scripts present', '', cat)

    # Syntax check on recently modified scripts
    broken = []
    for s in key:
        if s.exists():
            code, _, err = sh([sys.executable, '-m', 'py_compile', str(s)])
            if code != 0:
                broken.append(s.name)
    if broken:
        check('Script syntax', 'crit', f'Syntax errors: {", ".join(broken)}',
              'Fix syntax errors immediately', cat)
    else:
        check('Script syntax', 'ok', 'No syntax errors', '', cat)


# ─────────────── history ───────────────

def save_history(crits: int, warns: int, total: int):
    entry = {
        'ts': NOW.isoformat(),
        'critical': crits,
        'warn': warns,
        'total': total,
    }
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY, 'a') as f:
        f.write(json.dumps(entry) + '\n')


def show_history(n: int = 5):
    if not HISTORY.exists():
        print('No history yet.')
        return
    lines = HISTORY.read_text().strip().splitlines()
    recent = lines[-n:]
    print(f'\n📈 Last {len(recent)} scans:\n')
    for line in recent:
        try:
            e = json.loads(line)
            ts = datetime.fromisoformat(e['ts']).strftime('%m/%d %H:%M')
            c, w = e['critical'], e['warn']
            emoji = '🔴' if c else ('⚠️ ' if w else '✅')
            print(f"  {ts}  {emoji}  {c} crit  {w} warn  ({e['total']} checks)")
        except Exception:
            pass
    print()


# ─────────────── runner ───────────────

ALL_CHECKS = {
    'secrets':  check_secrets,
    'apis':     lambda: (check_apis(), check_email()),
    'channels': check_imsg,
    'git':      check_git,
    'memory':   check_memory,
    'delivery': check_delivery,
    'gateway':  check_gateway,
    'config':   check_config,
    'disk':     check_disk,
    'health':   check_health,
    'scripts':  check_scripts,
}

def run_all(categories=None):
    targets = categories or list(ALL_CHECKS.keys())
    for cat in targets:
        if cat in ALL_CHECKS:
            fn = ALL_CHECKS[cat]
            try:
                fn()
            except Exception as e:
                check(f'[{cat}] runner error', 'warn', str(e)[:80], '', cat)


def print_report(quiet=False):
    icons = {'ok': '✅', 'warn': '⚠️ ', 'crit': '🔴', 'info': 'ℹ️ '}
    crits = [r for r in results if r['status'] == 'crit']
    warns = [r for r in results if r['status'] == 'warn']
    infos = [r for r in results if r['status'] == 'info']
    oks   = [r for r in results if r['status'] == 'ok']

    print(f"\n{'='*62}")
    print(f"🔍 System Scanner v2 — {NOW.strftime('%Y-%m-%d %H:%M')} (Taipei)")
    print(f"{'='*62}")
    total = len(results)
    print(f"Summary: {len(crits)} 🔴  {len(warns)} ⚠️   {len(infos)} ℹ️   {len(oks)} ✅  ({total} checks)\n")

    show = [crits, warns, infos] + ([] if quiet else [oks])
    for group in show:
        for r in group:
            icon = icons[r['status']]
            line = f"{icon}  {r['label']}"
            if r['detail']:
                line += f"  —  {r['detail']}"
            print(line)
            if r['fix']:
                print(f"     → {r['fix']}")

    if quiet and oks:
        print(f"\n({len(oks)} checks OK — use without --quiet to see all)")
    print(f"\n{'='*62}")
    return len(crits), len(warns), total


def print_json():
    crits = sum(1 for r in results if r['status'] == 'crit')
    warns = sum(1 for r in results if r['status'] == 'warn')
    print(json.dumps({
        'ts': NOW.isoformat(),
        'summary': {'critical': crits, 'warn': warns, 'total': len(results)},
        'checks': results,
    }, ensure_ascii=False, indent=2))
    return crits, warns, len(results)


# ─────────────── main ───────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='OpenClaw system scanner')
    parser.add_argument('--quiet', '-q', action='store_true', help='Show only problems')
    parser.add_argument('--json', '-j', action='store_true', help='JSON output')
    parser.add_argument('--category', '-c', nargs='+', choices=list(ALL_CHECKS.keys()),
                        metavar='CAT', help='Run specific categories only')
    parser.add_argument('--history', action='store_true', help='Show scan history')
    parser.add_argument('--no-save', action='store_true', help='Do not save to history')
    args = parser.parse_args()

    if args.history:
        show_history()
        sys.exit(0)

    run_all(args.category)

    if args.json:
        crits, warns, total = print_json()
    else:
        crits, warns, total = print_report(quiet=args.quiet)

    if not args.no_save:
        save_history(crits, warns, total)

    sys.exit(1 if crits > 0 else 0)
