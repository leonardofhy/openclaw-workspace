#!/usr/bin/env python3
"""OpenClaw system scanner — diagnose and optionally auto-fix issues.

Usage:
  python3 scan.py               # full report
  python3 scan.py --quiet       # problems only
  python3 scan.py --fix         # diagnose + auto-fix safe issues
  python3 scan.py --json        # machine-readable output
  python3 scan.py --category git cron   # run specific categories
  python3 scan.py --history [N] # last N scan summaries (default 5)
  python3 scan.py --no-save     # skip history write

Categories: secrets, todoist, gcal, diary, smtp, git, memory,
            delivery, gateway, config, cron, disk, deps, scripts
"""

import argparse
import json
import smtplib
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── paths ──────────────────────────────────────────────────────────────────

WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
SCRIPTS   = WORKSPACE / 'skills' / 'leo-diary' / 'scripts'
MEMORY    = WORKSPACE / 'memory'
OPENCLAW  = Path.home() / '.openclaw'
LOGS      = OPENCLAW / 'logs'
CRON_JOBS = OPENCLAW / 'cron' / 'jobs.json'
CRON_RUNS = OPENCLAW / 'cron' / 'runs'
HISTORY   = MEMORY / 'scanner-history.jsonl'

NOW = datetime.now(timezone(timedelta(hours=8)))

FORBIDDEN_MODELS = {
    'anthropic/claude-opus-4',
    'anthropic/claude-opus-4-5',
    'anthropic/claude-sonnet-4-5',
}

# ── result store ──────────────────────────────────────────────────────────

results: list[dict] = []
_fix_queue: list[dict] = []


def check(label: str, status: str, detail: str = '', fix_hint: str = '', fix_fn=None):
    """Record a check result. status: ok | warn | crit | info"""
    results.append({
        'label': label,
        'status': status,
        'detail': detail,
        'fix': fix_hint,
        'fixable': fix_fn is not None,
    })
    if fix_fn is not None and status in ('warn', 'crit'):
        _fix_queue.append({'label': label, 'fn': fix_fn})


# ── helpers ───────────────────────────────────────────────────────────────

def sh(cmd: list, cwd=None, timeout=10):
    """Run a subprocess. Returns (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return -1, '', str(e)


def load_env(path: Path) -> dict:
    """Parse a .env file. Returns {} on any error."""
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


def load_json(path: Path):
    """Load a JSON file. Returns None on any error."""
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def save_json(path: Path, data) -> bool:
    """Write data as JSON. Returns False on error."""
    try:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        return True
    except Exception:
        return False


def load_cron_jobs() -> list[dict]:
    data = load_json(CRON_JOBS)
    if data is None:
        return []
    return data.get('jobs', []) if isinstance(data, dict) else data


def save_cron_jobs(jobs: list[dict]) -> bool:
    data = load_json(CRON_JOBS)
    if isinstance(data, dict):
        data['jobs'] = jobs
    else:
        data = {'version': 1, 'jobs': jobs}
    return save_json(CRON_JOBS, data)


# ── checks ────────────────────────────────────────────────────────────────

def check_secrets():
    for rel, min_size in [
        ('secrets/email_ops.env', 20),
        ('secrets/todoist.env', 10),
        ('secrets/google-service-account.json', 50),
    ]:
        p = WORKSPACE / rel
        name = Path(rel).name
        if not p.exists():
            check(f'Secret: {name}', 'crit', 'File missing', f'Restore {rel}')
        elif p.stat().st_size < min_size:
            check(f'Secret: {name}', 'warn', 'File suspiciously small', f'Verify {rel}')
        else:
            check(f'Secret: {name}', 'ok')


def check_todoist():
    import urllib.request
    env = load_env(WORKSPACE / 'secrets' / 'todoist.env')
    token = env.get('TODOIST_API_TOKEN', '')
    if not token:
        check('Todoist API', 'crit', 'Token missing', 'Check secrets/todoist.env')
        return
    try:
        req = urllib.request.Request(
            'https://api.todoist.com/api/v1/tasks?limit=1',
            headers={'Authorization': f'Bearer {token}'}
        )
        urllib.request.urlopen(req, timeout=6)
        check('Todoist API', 'ok', 'Reachable')
    except Exception as e:
        check('Todoist API', 'crit', str(e)[:70], 'Check token / internet')


def check_gcal():
    sys.path.insert(0, str(SCRIPTS))
    try:
        from gcal_today import get_events
        evts = get_events(days_ahead=0, days_range=1)
        check('Google Calendar API', 'ok', f'{len(evts)} events today')
    except Exception as e:
        check('Google Calendar API', 'crit', str(e)[:70], 'Check google-service-account.json')


def check_diary():
    sys.path.insert(0, str(SCRIPTS))
    try:
        from read_diary import load_diary
        entries = load_diary()
        if not entries:
            check('Diary data', 'crit', 'No entries loaded', 'Check read_diary.py')
            return
        latest = max(e.get('date', '') for e in entries)
        days_ago = (NOW.date() - datetime.strptime(latest, '%Y-%m-%d').date()).days
        if days_ago > 3:
            check('Diary data', 'warn', f'Stale — latest {days_ago}d ago ({latest})',
                  'Check Google Sheets sync')
        else:
            check('Diary data', 'ok', f'{len(entries)} entries, latest {latest}')
    except Exception as e:
        check('Diary data', 'crit', str(e)[:70])


def check_smtp():
    env = load_env(WORKSPACE / 'secrets' / 'email_ops.env')
    host = env.get('SMTP_HOST', 'smtp.gmail.com')
    port = int(env.get('SMTP_PORT', '587'))
    user = env.get('SMTP_USER', env.get('EMAIL_SENDER', ''))
    pwd  = env.get('SMTP_PASS', env.get('SMTP_PASSWORD', env.get('EMAIL_PASSWORD', '')))
    if not user or not pwd:
        check('Email SMTP', 'warn', 'Credentials missing in email_ops.env')
        return
    try:
        with smtplib.SMTP(host, port, timeout=6) as s:
            s.starttls()
            s.login(user, pwd)
        check('Email SMTP', 'ok', f'{user} authenticated')
    except Exception as e:
        check('Email SMTP', 'warn', str(e)[:70], 'Check SMTP credentials / App Password')


def check_git():
    def _fix():
        for cmd in [['git', 'add', '-A'], ['git', 'commit', '-m', 'chore: scanner auto-fix'],
                    ['git', 'push']]:
            rc, out, err = sh(cmd, cwd=str(WORKSPACE))
            if rc != 0 and 'nothing to commit' not in out + err:
                raise RuntimeError(err)
        return 'committed and pushed'

    rc, out, _ = sh(['git', 'status', '--short'], cwd=str(WORKSPACE))
    if rc != 0:
        check('Git status', 'warn', 'git command failed')
        return
    if out:
        check('Git uncommitted', 'warn', f'{len(out.splitlines())} changed file(s)',
              'git add -A && git commit && git push', fix_fn=_fix)
    else:
        check('Git status', 'ok', 'Clean')
        rc2, out2, _ = sh(['git', 'log', 'origin/main..HEAD', '--oneline'], cwd=str(WORKSPACE))
        if rc2 == 0 and out2:
            check('Git unpushed', 'warn', f'{len(out2.splitlines())} commit(s) ahead', 'git push',
                  fix_fn=lambda: sh(['git', 'push'], cwd=str(WORKSPACE))[1])
        elif rc2 == 0:
            check('Git remote sync', 'ok', 'Up to date')


def check_memory():
    today = NOW.date()
    missing = [
        (today - timedelta(days=i)).strftime('%Y-%m-%d')
        for i in range(7)
        if not (MEMORY / f'{(today - timedelta(days=i)).strftime("%Y-%m-%d")}.md').exists()
    ]

    def _fix():
        created = [d for d in missing
                   if not (MEMORY / f'{d}.md').exists()
                   and (MEMORY / f'{d}.md').write_text(f'# {d}\n\n_(auto-created)_\n') is None]
        return f'Created: {", ".join(created)}' if created else 'Nothing to create'

    if missing:
        check('Memory coverage', 'warn',
              f'Missing {len(missing)}/7 days: {", ".join(missing[:3])}{"…" if len(missing) > 3 else ""}',
              'Run diary sync or --fix', fix_fn=_fix)
    else:
        check('Memory coverage', 'ok', '7 recent days present')

    mm = WORKSPACE / 'MEMORY.md'
    if mm.exists():
        age_days = int((NOW.timestamp() - mm.stat().st_mtime) / 86400)
        if age_days > 14:
            check('MEMORY.md freshness', 'info', f'Last updated {age_days}d ago',
                  'Review and update long-term memory')
        else:
            check('MEMORY.md freshness', 'ok', f'Updated {age_days}d ago')

    tags_dir = MEMORY / 'tags'
    if tags_dir.exists():
        missing_tags = sum(
            1 for i in range(1, 8)
            if not (tags_dir / f'{(today - timedelta(days=i)).strftime("%Y-%m-%d")}.json').exists()
        )
        if missing_tags > 3:
            check('Tags coverage', 'warn', f'Missing tags for {missing_tags}/7 days',
                  'python3 skills/leo-diary/scripts/generate_tags.py')
        else:
            check('Tags coverage', 'ok', f'Tags present for {7 - missing_tags}/7 days')


def check_delivery():
    dq = OPENCLAW / 'delivery-queue'
    if not dq.exists():
        check('Delivery queue', 'ok', 'No queue dir')
        return
    stuck = [f for f in dq.iterdir() if f.is_file()]
    if not stuck:
        check('Delivery queue', 'ok', 'Empty')
        return

    def _fix():
        removed = sum(1 for f in stuck if not f.unlink() and True)
        return f'Removed {removed} stuck message(s)'

    check('Delivery queue', 'warn', f'{len(stuck)} message(s) stuck',
          'Check gateway logs; or run --fix', fix_fn=_fix)


def check_gateway():
    # LaunchAgent
    rc, out, _ = sh(['launchctl', 'list', 'ai.openclaw.gateway'])
    if rc != 0:
        check('LaunchAgent', 'crit', 'ai.openclaw.gateway not loaded', 'openclaw gateway start')
    else:
        la = load_json(Path('/dev/stdin')) if False else {}  # can't parse from out easily
        try:
            la = json.loads(out) if out.startswith('{') else {}
        except Exception:
            la = {}
        pid = la.get('PID', 0)
        last_exit = la.get('LastExitStatus', 0)
        if pid:
            check('LaunchAgent', 'ok', f'Running (pid {pid})')
        elif last_exit:
            check('LaunchAgent', 'warn', f'Not running (last exit {last_exit})', 'openclaw gateway start')
        else:
            check('LaunchAgent', 'ok', 'Registered')

    # Log health
    log = LOGS / 'gateway.log'
    if not log.exists():
        check('Gateway log', 'warn', 'Log file not found')
        return

    _, out, _ = sh(['tail', '-500', str(log)])
    lines = out.splitlines()
    cutoff_2h = (NOW.astimezone(timezone.utc) - timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M')

    config_errs = [l for l in lines
                   if ('INVALID_REQUEST' in l or 'invalid config' in l.lower())
                   and 'config.patch' not in l
                   and len(l) >= 16 and l[:16] >= cutoff_2h]
    if config_errs:
        check('Gateway config errors', 'crit', f'{len(config_errs)} error(s) in last 2h',
              'Check cron model names')
    else:
        recent_errs = [l for l in lines
                       if '[error]' in l.lower() and len(l) >= 16 and l[:16] >= cutoff_2h]
        status = 'warn' if recent_errs else 'ok'
        detail = f'{len(recent_errs)} error line(s) in last 2h' if recent_errs else 'Clean (last 2h)'
        check('Gateway logs', status, detail)

    # Discord WebSocket
    cutoff_1h = (NOW.astimezone(timezone.utc) - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')
    dc_count = sum(1 for l in lines
                   if 'WebSocket connection closed with code 1006' in l
                   and len(l) >= 16 and l[:16] >= cutoff_1h)
    if dc_count >= 3:
        check('Discord WebSocket', 'warn', f'{dc_count} fatal disconnect(s) in last hour',
              'openclaw gateway restart')
    else:
        check('Discord WebSocket', 'ok', 'Stable')


def check_config():
    cfg_path = OPENCLAW / 'openclaw.json'
    cfg = load_json(cfg_path)
    if cfg is None:
        check('OpenClaw config', 'warn', 'openclaw.json missing or invalid')
        return
    check('OpenClaw config', 'ok', 'Parses cleanly')

    # Compaction mode
    mode = cfg.get('agents', {}).get('defaults', {}).get('compaction', {}).get('mode', 'default')
    if mode == 'safeguard':
        def _fix_compaction():
            c = load_json(cfg_path)
            c.setdefault('agents', {}).setdefault('defaults', {}).setdefault('compaction', {})['mode'] = 'default'
            save_json(cfg_path, c)
            return 'compaction.mode → default'
        check('Compaction mode', 'warn', '"safeguard" may cause context overflow',
              'Set to "default"', fix_fn=_fix_compaction)
    else:
        check('Compaction mode', 'ok', f'mode={mode}')

    # Context pruning
    pruning = cfg.get('agents', {}).get('defaults', {}).get('contextPruning', {})
    if not pruning or pruning.get('mode', 'off') == 'off':
        check('Context pruning', 'warn', 'Disabled — context may grow unbounded',
              'Enable cache-ttl mode in openclaw.json')
    else:
        check('Context pruning', 'ok', f'mode={pruning.get("mode")}, ttl={pruning.get("ttl", "?")}')

    # Update available
    uc = load_json(OPENCLAW / 'update-check.json')
    if uc and uc.get('updateAvailable'):
        check('OpenClaw update', 'info', f'v{uc.get("latest", "?")} available', 'openclaw update')
    elif uc:
        check('OpenClaw update', 'ok', 'Up to date')


def check_cron():
    jobs = load_cron_jobs()
    if not jobs:
        check('Cron jobs', 'warn', f'No jobs found at {CRON_JOBS}', 'openclaw cron list')
        return

    enabled = [j for j in jobs if j.get('enabled', True)]
    check('Cron job count', 'ok', f'{len(enabled)} enabled / {len(jobs)} total')

    # Model validation
    bad = [(j.get('name', '?')[:35], j.get('payload', {}).get('model', ''))
           for j in enabled
           if (m := j.get('payload', {}).get('model', '') or '') and m in FORBIDDEN_MODELS]
    if bad:
        names = ', '.join(n for n, _ in bad[:3])

        def _fix_models():
            all_jobs = load_cron_jobs()
            fixed = []
            for j in all_jobs:
                m = j.get('payload', {}).get('model', '') or ''
                if m in FORBIDDEN_MODELS:
                    j['payload']['model'] = 'anthropic/claude-sonnet-4-6'
                    fixed.append(f'{j.get("name","?")[:30]}: {m} → sonnet-4-6')
            save_cron_jobs(all_jobs)
            return '; '.join(fixed) or 'Nothing to fix'

        check('Cron model versions', 'crit', f'{len(bad)} job(s) with forbidden model: {names}',
              'Downgrade to anthropic/claude-sonnet-4-6', fix_fn=_fix_models)
    else:
        has_model = sum(1 for j in enabled if j.get('payload', {}).get('model'))
        check('Cron model versions', 'ok', f'{has_model}/{len(enabled)} jobs have explicit model')

    # One-time jobs: only warn if overdue
    now_ms = NOW.timestamp() * 1000
    overdue = [j for j in jobs if j.get('deleteAfterRun')
               and j.get('state', {}).get('nextRunAtMs', now_ms + 1) < now_ms - 3_600_000]
    if overdue:
        check('Cron one-time jobs', 'warn',
              f'{len(overdue)} overdue job(s): {", ".join(j.get("name","?")[:25] for j in overdue[:3])}',
              'Check if gateway missed them')
    else:
        pending = sum(1 for j in jobs if j.get('deleteAfterRun'))
        if pending:
            check('Cron one-time jobs', 'ok', f'{pending} future job(s) scheduled')

    # Consecutive errors
    errored = [j for j in enabled if j.get('state', {}).get('consecutiveErrors', 0) > 0]
    if errored:
        check('Cron error state', 'warn',
              f'{len(errored)} job(s) with errors: {", ".join(j.get("name","?")[:25] for j in errored[:3])}',
              'Check gateway logs')
    else:
        check('Cron error state', 'ok', 'No consecutive errors')

    # Recent activity
    if CRON_RUNS.exists():
        recent = [f for f in CRON_RUNS.iterdir()
                  if f.suffix == '.jsonl' and f.stat().st_mtime > NOW.timestamp() - 25 * 3600]
        if recent:
            check('Cron activity', 'ok', f'{len(recent)} run(s) in last 25h')
        else:
            check('Cron activity', 'warn', 'No cron runs in last 25h', 'openclaw cron list')


def check_disk():
    rc, out, _ = sh(['df', '-h', '/'])
    if rc == 0 and out:
        try:
            parts = out.splitlines()[-1].split()
            pct, avail = int(parts[4].rstrip('%')), parts[3]
            status = 'crit' if pct >= 90 else ('warn' if pct >= 75 else 'ok')
            fix = 'Free up disk space urgently' if pct >= 90 else ('Consider cleanup' if pct >= 75 else '')
            check('Disk space', status, f'{pct}% used, {avail} free', fix)
        except Exception:
            check('Disk space', 'info', out.splitlines()[-1])

    rc2, out2, _ = sh(['du', '-sh', str(WORKSPACE)])
    if rc2 == 0 and out2:
        check('Workspace size', 'ok', out2.split()[0])


def check_deps():
    packages = [
        ('google.oauth2.service_account', 'google-auth'),
        ('googleapiclient.discovery',     'google-api-python-client'),
        ('gspread',                        'gspread'),
    ]
    missing = [pkg for mod, pkg in packages if not _can_import(mod)]
    if missing:
        check('Python packages', 'crit', f'Missing: {", ".join(missing)}',
              f'pip3 install {" ".join(missing)}')
    else:
        check('Python packages', 'ok', f'All {len(packages)} packages importable')

    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 10):
        check('Python version', 'warn', f'Python {major}.{minor} — recommend 3.10+')
    else:
        check('Python version', 'ok', f'Python {major}.{minor}')


def _can_import(module: str) -> bool:
    try:
        __import__(module)
        return True
    except ImportError:
        return False


def check_scripts():
    key_scripts = [
        'read_diary.py', 'todoist_sync.py', 'gcal_today.py',
        'daily_coach_v3.py', 'sleep_calc.py', 'generate_tags.py', 'email_utils.py',
    ]
    missing = [s for s in key_scripts if not (SCRIPTS / s).exists()]
    if missing:
        check('Key scripts', 'crit', f'Missing: {", ".join(missing)}', 'Restore from git')
    else:
        check('Key scripts', 'ok', f'All {len(key_scripts)} present')

    broken = []
    for name in key_scripts:
        p = SCRIPTS / name
        if p.exists():
            rc, _, err = sh([sys.executable, '-m', 'py_compile', str(p)])
            if rc != 0:
                broken.append(f'{name}: {err[:50]}')
    if broken:
        check('Script syntax', 'crit', f'{len(broken)} file(s) with errors: {broken[0]}',
              'Fix syntax errors immediately')
    else:
        check('Script syntax', 'ok', 'No syntax errors')


# ── fix engine ────────────────────────────────────────────────────────────

def run_fixes() -> list[dict]:
    if not _fix_queue:
        return []
    print(f'\n🔧 Running {len(_fix_queue)} auto-fix(es)...\n')
    results_list = []
    for item in _fix_queue:
        try:
            msg = item['fn']()
            results_list.append({'label': item['label'], 'success': True, 'msg': msg or 'Fixed'})
            print(f"  ✅  {item['label']}: {msg or 'Fixed'}")
        except Exception as e:
            results_list.append({'label': item['label'], 'success': False, 'msg': str(e)})
            print(f"  ❌  {item['label']}: {e}")
    return results_list


# ── history ───────────────────────────────────────────────────────────────

def save_history(crits: int, warns: int, total: int, fixed: int = 0):
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY, 'a') as f:
        f.write(json.dumps({
            'ts': NOW.isoformat(), 'critical': crits,
            'warn': warns, 'total': total, 'fixed': fixed,
        }) + '\n')


def show_history(n: int = 5):
    if not HISTORY.exists():
        print('No history yet.')
        return
    lines = HISTORY.read_text().strip().splitlines()
    print(f'\n📈 Last {min(n, len(lines))} scans:\n')
    for line in lines[-n:]:
        try:
            e = json.loads(line)
            ts  = datetime.fromisoformat(e['ts']).strftime('%m/%d %H:%M')
            c, w = e['critical'], e['warn']
            fx  = e.get('fixed', 0)
            icon = '🔴' if c else ('⚠️ ' if w else '✅')
            print(f'  {ts}  {icon}  {c} crit  {w} warn  ({e["total"]} checks)'
                  + (f'  [{fx} fixed]' if fx else ''))
        except Exception:
            pass
    print()


# ── runner ────────────────────────────────────────────────────────────────

ALL_CHECKS = {
    'secrets':  check_secrets,
    'todoist':  check_todoist,
    'gcal':     check_gcal,
    'diary':    check_diary,
    'smtp':     check_smtp,
    'git':      check_git,
    'memory':   check_memory,
    'delivery': check_delivery,
    'gateway':  check_gateway,
    'config':   check_config,
    'cron':     check_cron,
    'disk':     check_disk,
    'deps':     check_deps,
    'scripts':  check_scripts,
}


def run_checks(categories=None):
    for name in (categories or ALL_CHECKS):
        fn = ALL_CHECKS.get(name)
        if fn:
            try:
                fn()
            except Exception as e:
                check(f'[{name}] runner error', 'warn', str(e)[:80])


def print_report(quiet=False) -> tuple[int, int, int]:
    icons = {'ok': '✅', 'warn': '⚠️ ', 'crit': '🔴', 'info': 'ℹ️ '}
    by_status = {s: [r for r in results if r['status'] == s]
                 for s in ('crit', 'warn', 'info', 'ok')}
    crits, warns = len(by_status['crit']), len(by_status['warn'])

    print(f"\n{'=' * 62}")
    print(f"🔍 System Scanner — {NOW.strftime('%Y-%m-%d %H:%M')} (Taipei)")
    print(f"{'=' * 62}")
    print(f"Summary: {crits} 🔴  {warns} ⚠️   {len(by_status['info'])} ℹ️   "
          f"{len(by_status['ok'])} ✅  ({len(results)} checks)\n")

    show = ['crit', 'warn', 'info'] + ([] if quiet else ['ok'])
    for status in show:
        for r in by_status[status]:
            badge = ' [auto-fixable]' if r.get('fixable') else ''
            line = f"{icons[status]}  {r['label']}{badge}"
            if r['detail']:
                line += f"  —  {r['detail']}"
            print(line)
            if r['fix']:
                print(f"     → {r['fix']}")

    if quiet and by_status['ok']:
        print(f"\n({len(by_status['ok'])} checks OK — run without --quiet to see all)")
    print(f"\n{'=' * 62}")
    return crits, warns, len(results)


def print_json(fix_results=None) -> tuple[int, int, int]:
    crits = sum(1 for r in results if r['status'] == 'crit')
    warns = sum(1 for r in results if r['status'] == 'warn')
    out = {'ts': NOW.isoformat(),
           'summary': {'critical': crits, 'warn': warns, 'total': len(results)},
           'checks': results}
    if fix_results:
        out['fixes'] = fix_results
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return crits, warns, len(results)


# ── main ──────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='OpenClaw system scanner')
    parser.add_argument('--quiet',    '-q', action='store_true', help='Show problems only')
    parser.add_argument('--fix',      '-f', action='store_true', help='Auto-fix safe issues')
    parser.add_argument('--json',     '-j', action='store_true', help='JSON output')
    parser.add_argument('--category', '-c', nargs='+', choices=list(ALL_CHECKS), metavar='CAT')
    parser.add_argument('--history',        nargs='?', const=5, type=int, metavar='N')
    parser.add_argument('--no-save',        action='store_true', help='Skip history write')
    args = parser.parse_args()

    if args.history is not None:
        show_history(args.history)
        sys.exit(0)

    run_checks(args.category)

    fix_results = None
    if args.fix:
        fix_results = run_fixes()
        if fix_results:                   # re-scan to show post-fix state
            results.clear()
            _fix_queue.clear()
            run_checks(args.category)

    crits, warns, total = (print_json(fix_results) if args.json
                           else print_report(quiet=args.quiet))

    if not args.no_save:
        fixed = sum(1 for f in (fix_results or []) if f.get('success'))
        save_history(crits, warns, total, fixed=fixed)

    sys.exit(1 if crits > 0 else 0)
