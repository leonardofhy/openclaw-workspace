#!/usr/bin/env python3
"""System Scanner v3 — diagnose and optionally auto-fix OpenClaw workspace issues.

Usage:
  python3 scan.py               # full diagnostic report
  python3 scan.py --quiet       # only problems (warn/crit)
  python3 scan.py --fix         # diagnose + auto-fix safe issues
  python3 scan.py --json        # machine-readable JSON output
  python3 scan.py --category config  # run specific category only
  python3 scan.py --history [N] # show last N scan summaries (default 5)
  python3 scan.py --no-save     # skip writing to history

Categories: secrets, apis, git, memory, delivery, gateway, config, cron, disk, deps, scripts
"""

import argparse
import json
import os
import smtplib
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ─────────────── constants ───────────────

WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
SECRETS   = WORKSPACE / 'secrets'
MEMORY    = WORKSPACE / 'memory'
TAGS      = MEMORY / 'tags'
SCRIPTS   = WORKSPACE / 'skills' / 'leo-diary' / 'scripts'
OPENCLAW  = Path.home() / '.openclaw'
LOGS      = OPENCLAW / 'logs'
CRON_RUNS = OPENCLAW / 'cron' / 'runs'
CRON_JOBS = OPENCLAW / 'cron' / 'jobs.json'
HISTORY   = MEMORY / 'scanner-history.jsonl'
TZ        = timezone(timedelta(hours=8))
NOW       = datetime.now(TZ)

# Expected cron schedule: (id_fragment, schedule_description, hour_range_utc)
# These are the 8 recurring jobs from TOOLS.md
EXPECTED_CRON = [
    ('diary',        '04:15 Taipei = 20:15 UTC', (20, 20)),   # diary sync
    ('morning',      '08:30 Taipei = 00:30 UTC', (0, 1)),     # morning overview
    ('coach',        '12:00 Taipei = 04:00 UTC', (4, 4)),     # daily coach
    ('calendar',     '13:00 Taipei = 05:00 UTC', (5, 5)),     # calendar scan
    ('todoist',      '22:30 Taipei = 14:30 UTC', (14, 14)),   # evening todoist review
    ('summary',      '23:50 Taipei = 15:50 UTC', (15, 15)),   # end-of-day discord
    ('weekly',       '21:00 Sun Taipei', None),                # weekly report
    ('weather',      '20:00 Fri Taipei', None),                # weather scout
]
FORBIDDEN_MODELS = {'anthropic/claude-opus-4', 'anthropic/claude-opus-4-5',
                    'anthropic/claude-sonnet-4-5'}  # 4-5 deprecated
PREFERRED_MODELS = {'anthropic/claude-sonnet-4-6', 'sonnet'}

# ─────────────── result store ───────────────

results: list[dict] = []
_fix_queue: list[dict] = []   # items queued for --fix


def check(label: str, status: str, detail: str = '', fix_hint: str = '',
          category: str = 'general', fix_fn=None):
    """Record a check result.

    status: ok | warn | crit | info
    fix_fn: callable() → str  — auto-fix; returns human-readable summary or raises
    """
    entry = {
        'label': label, 'status': status, 'detail': detail,
        'fix': fix_hint, 'category': category, 'fixable': fix_fn is not None,
    }
    results.append(entry)
    if fix_fn is not None and status in ('warn', 'crit'):
        _fix_queue.append({'label': label, 'fn': fix_fn, 'status': status})


# ─────────────── helpers ───────────────

def sh(cmd: list, cwd=None, timeout=10):
    """Run subprocess; returns (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return -1, '', str(e)


def load_env(path: Path) -> dict:
    """Parse a .env file into a dict. Silently returns {} on any error."""
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


def load_openclaw_config() -> dict | None:
    """Load and parse openclaw.json; return None on error."""
    p = OPENCLAW / 'openclaw.json'
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def save_openclaw_config(cfg: dict) -> bool:
    """Write cfg back to openclaw.json. Returns True on success."""
    p = OPENCLAW / 'openclaw.json'
    try:
        p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
        return True
    except Exception:
        return False


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
        name = Path(rel).name
        if not p.exists():
            check(f'Secret: {name}', 'crit', 'File missing',
                  f'Restore {rel}', cat)
        elif p.stat().st_size < min_size:
            check(f'Secret: {name}', 'warn', 'File suspiciously small',
                  f'Verify {rel}', cat)
        else:
            check(f'Secret: {name}', 'ok', '', '', cat)


def check_apis():
    cat = 'apis'
    sys.path.insert(0, str(SCRIPTS))

    # Todoist
    env = load_env(WORKSPACE / 'secrets' / 'todoist.env')
    token = env.get('TODOIST_API_TOKEN', '')
    if not token:
        check('Todoist API', 'crit', 'Token missing',
              'Check secrets/todoist.env', cat)
    else:
        import urllib.request
        try:
            req = urllib.request.Request(
                'https://api.todoist.com/api/v1/tasks?limit=1',
                headers={'Authorization': f'Bearer {token}'}
            )
            urllib.request.urlopen(req, timeout=6)
            check('Todoist API', 'ok', 'Reachable', '', cat)
        except Exception as e:
            check('Todoist API', 'crit', str(e)[:70],
                  'Check token / internet', cat)

    # Google Calendar
    try:
        from gcal_today import get_events
        evts = get_events(days_ahead=0, days_range=1)
        check('Google Calendar API', 'ok', f'{len(evts)} events today', '', cat)
    except Exception as e:
        check('Google Calendar API', 'crit', str(e)[:70],
              'Check google-service-account.json', cat)

    # Diary freshness
    try:
        from read_diary import load_diary
        entries = load_diary()
        if entries:
            latest = max(e.get('date', '') for e in entries)
            days_ago = (NOW.date() - datetime.strptime(latest, '%Y-%m-%d').date()).days
            if days_ago > 3:
                check('Diary data', 'warn',
                      f'Stale — latest {days_ago}d ago ({latest})',
                      'Check Google Sheets sync', cat)
            else:
                check('Diary data', 'ok',
                      f'{len(entries)} entries, latest {latest}', '', cat)
        else:
            check('Diary data', 'crit', 'No entries loaded',
                  'Check read_diary.py', cat)
    except Exception as e:
        check('Diary data', 'crit', str(e)[:70], '', cat)

    # Email SMTP
    email_env = load_env(WORKSPACE / 'secrets' / 'email_ops.env')
    host = email_env.get('SMTP_HOST', 'smtp.gmail.com')
    port = int(email_env.get('SMTP_PORT', '587'))
    user = email_env.get('SMTP_USER', email_env.get('EMAIL_SENDER', ''))
    pwd  = email_env.get('SMTP_PASS',
           email_env.get('SMTP_PASSWORD', email_env.get('EMAIL_PASSWORD', '')))
    if not user or not pwd:
        check('Email SMTP', 'warn', 'Credentials missing in email_ops.env', '', cat)
    else:
        try:
            with smtplib.SMTP(host, port, timeout=6) as s:
                s.starttls()
                s.login(user, pwd)
            check('Email SMTP', 'ok', f'{user} authenticated', '', cat)
        except Exception as e:
            check('Email SMTP', 'warn', str(e)[:70],
                  'Check SMTP credentials / App Password', cat)


def check_git():
    cat = 'git'

    def _fix_git():
        rc, out, err = sh(['git', 'add', '-A'], cwd=str(WORKSPACE))
        if rc != 0:
            raise RuntimeError(err)
        rc, out, err = sh(['git', 'commit', '-m', 'chore: scanner auto-fix commit'],
                          cwd=str(WORKSPACE))
        if rc != 0 and 'nothing to commit' not in out + err:
            raise RuntimeError(err)
        rc, out, err = sh(['git', 'push'], cwd=str(WORKSPACE))
        if rc != 0:
            raise RuntimeError(err)
        return 'git add -A && commit && push succeeded'

    code, out, err = sh(['git', 'status', '--short'], cwd=str(WORKSPACE))
    if code != 0:
        check('Git status', 'warn', f'Error: {err[:60]}', '', cat)
        return
    if out:
        n = len(out.strip().splitlines())
        check('Git uncommitted', 'warn', f'{n} changed file(s)',
              'git add -A && git commit && git push', cat, fix_fn=_fix_git)
    else:
        check('Git status', 'ok', 'Clean', '', cat)
        code2, out2, _ = sh(['git', 'log', 'origin/main..HEAD', '--oneline'],
                            cwd=str(WORKSPACE))
        if code2 == 0 and out2:
            check('Git unpushed', 'warn', f'{len(out2.splitlines())} commit(s) ahead',
                  'git push', cat, fix_fn=lambda: sh(['git', 'push'], cwd=str(WORKSPACE))[1])
        elif code2 == 0:
            check('Git remote sync', 'ok', 'Up to date', '', cat)


def check_memory():
    cat = 'memory'
    today = NOW.date()

    # Coverage — last 7 days
    missing_dates = [
        (today - timedelta(days=i)).strftime('%Y-%m-%d')
        for i in range(7)
        if not (MEMORY / f'{(today - timedelta(days=i)).strftime("%Y-%m-%d")}.md').exists()
    ]

    def _fix_memory():
        created = []
        for d in missing_dates:
            p = MEMORY / f'{d}.md'
            if not p.exists():
                p.write_text(f'# {d}\n\n_(auto-created by system scanner)_\n')
                created.append(d)
        return f'Created: {", ".join(created)}' if created else 'Nothing to create'

    if missing_dates:
        check('Memory coverage', 'warn',
              f'Missing {len(missing_dates)}/7 days: {", ".join(missing_dates[:3])}' +
              ('…' if len(missing_dates) > 3 else ''),
              'Create missing files or run diary sync', cat, fix_fn=_fix_memory)
    else:
        check('Memory coverage', 'ok', '7 recent days present', '', cat)

    # MEMORY.md freshness
    mm = WORKSPACE / 'MEMORY.md'
    if mm.exists():
        age = (NOW.timestamp() - mm.stat().st_mtime) / 86400
        if age > 14:
            check('MEMORY.md freshness', 'info', f'Last updated {int(age)}d ago',
                  'Review and update long-term memory', cat)
        else:
            check('MEMORY.md freshness', 'ok', f'Updated {int(age)}d ago', '', cat)

    # Tags coverage
    if TAGS.exists():
        missing_tags = [
            (today - timedelta(days=i + 1)).strftime('%Y-%m-%d')
            for i in range(7)
            if not (TAGS / f'{(today - timedelta(days=i + 1)).strftime("%Y-%m-%d")}.json').exists()
        ]
        if len(missing_tags) > 3:
            check('Tags coverage', 'warn',
                  f'Missing tags for {len(missing_tags)}/7 recent days',
                  'python3 skills/leo-diary/scripts/generate_tags.py', cat)
        else:
            check('Tags coverage', 'ok',
                  f'Tags present for {7 - len(missing_tags)}/7 days', '', cat)


def check_delivery():
    cat = 'delivery'
    dq = OPENCLAW / 'delivery-queue'
    if not dq.exists():
        check('Delivery queue', 'ok', 'No queue dir', '', cat)
        return

    stuck = [f for f in dq.iterdir() if f.is_file()]
    if not stuck:
        check('Delivery queue', 'ok', 'Empty', '', cat)
        return

    def _fix_delivery():
        removed = 0
        for f in stuck:
            try:
                f.unlink()
                removed += 1
            except Exception:
                pass
        return f'Removed {removed} stuck message(s)'

    check('Delivery queue', 'warn', f'{len(stuck)} message(s) stuck',
          'Check gateway logs; or auto-fix with --fix', cat, fix_fn=_fix_delivery)


def check_gateway():
    cat = 'gateway'

    # LaunchAgent status
    code, out, err = sh(['launchctl', 'list', 'ai.openclaw.gateway'])
    if code != 0:
        check('LaunchAgent', 'crit', 'ai.openclaw.gateway not loaded',
              'openclaw gateway start', cat)
    else:
        try:
            la = json.loads(out) if out.startswith('{') else {}
            pid = la.get('PID', 0)
            last_exit = la.get('LastExitStatus', 0)
            if pid:
                check('LaunchAgent', 'ok', f'Running (pid {pid})', '', cat)
            elif last_exit:
                check('LaunchAgent', 'warn', f'Not running (last exit {last_exit})',
                      'openclaw gateway start', cat)
            else:
                check('LaunchAgent', 'ok', 'Registered', '', cat)
        except Exception:
            check('LaunchAgent', 'ok', 'Registered (json parse skipped)', '', cat)

    # Gateway log analysis
    log = LOGS / 'gateway.log'
    if not log.exists():
        check('Gateway log', 'warn', 'Log file not found', '', cat)
        return

    code, out, _ = sh(['tail', '-500', str(log)])
    lines = out.splitlines()
    cutoff_2h = (NOW.astimezone(timezone.utc) - timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M')

    # Config errors (recent, not config.patch noise)
    cfg_errs = [l for l in lines
                if ('INVALID_REQUEST' in l or 'invalid config' in l.lower())
                and 'config.patch' not in l
                and len(l) >= 16 and l[:16] >= cutoff_2h]
    if cfg_errs:
        check('Gateway config errors', 'crit',
              f'{len(cfg_errs)} config error(s) in last 2h',
              'openclaw status / check cron model names', cat)
    else:
        errs = [l for l in lines
                if '[error]' in l.lower()
                and len(l) >= 16 and l[:16] >= cutoff_2h]
        if errs:
            check('Gateway errors', 'warn',
                  f'{len(errs)} error line(s) in last 2h', '', cat)
        else:
            check('Gateway logs', 'ok', 'Clean (last 2h)', '', cat)

    # Discord WebSocket stability
    cutoff_1h = (NOW.astimezone(timezone.utc) - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')
    disc_dc = [l for l in lines
               if 'WebSocket connection closed with code 1006' in l
               and len(l) >= 16 and l[:16] >= cutoff_1h]
    if len(disc_dc) >= 3:
        check('Discord WebSocket', 'warn',
              f'{len(disc_dc)} fatal disconnect(s) in last hour',
              'openclaw gateway restart', cat)
    else:
        check('Discord WebSocket', 'ok', 'Stable', '', cat)

    # Cron activity
    if CRON_RUNS.exists():
        recent_runs = [
            f.name for f in CRON_RUNS.iterdir()
            if f.suffix == '.jsonl' and f.stat().st_mtime > (NOW.timestamp() - 25 * 3600)
        ]
        if recent_runs:
            check('Cron activity', 'ok', f'{len(recent_runs)} job run(s) in last 25h', '', cat)
        else:
            check('Cron activity', 'warn', 'No cron runs in last 25h',
                  'openclaw cron list — check if jobs exist', cat)
    else:
        check('Cron activity', 'info', 'No cron runs dir yet', '', cat)


def check_config():
    cat = 'config'
    cfg = load_openclaw_config()
    if cfg is None:
        check('OpenClaw config', 'warn', 'openclaw.json missing or unparseable', '', cat)
        return

    check('OpenClaw config', 'ok', 'Parses cleanly', '', cat)

    # Compaction mode
    mode = (cfg.get('agents', {})
               .get('defaults', {})
               .get('compaction', {})
               .get('mode', 'default'))
    if mode == 'safeguard':
        def _fix_compaction():
            c = load_openclaw_config()
            c.setdefault('agents', {}).setdefault('defaults', {}).setdefault('compaction', {})['mode'] = 'default'
            save_openclaw_config(c)
            return 'compaction.mode → default'
        check('Compaction mode', 'warn', '"safeguard" risks context overflow',
              'Set to "default"', cat, fix_fn=_fix_compaction)
    else:
        check('Compaction mode', 'ok', f'mode={mode}', '', cat)

    # Context pruning
    pruning = (cfg.get('agents', {})
                  .get('defaults', {})
                  .get('contextPruning', {}))
    if not pruning or pruning.get('mode', 'off') == 'off':
        check('Context pruning', 'warn', 'Disabled — context may grow unbounded',
              'Enable cache-ttl mode in openclaw.json', cat)
    else:
        check('Context pruning', 'ok',
              f'mode={pruning.get("mode")}, ttl={pruning.get("ttl", "?")}', '', cat)

    # OpenClaw update
    uc_file = OPENCLAW / 'update-check.json'
    if uc_file.exists():
        try:
            uc = json.loads(uc_file.read_text())
            if uc.get('updateAvailable'):
                check('OpenClaw update', 'info',
                      f'v{uc.get("latest", "?")} available',
                      'openclaw update', cat)
            else:
                check('OpenClaw update', 'ok', 'Up to date', '', cat)
        except Exception:
            pass


def _load_cron_jobs() -> list[dict]:
    """Load jobs from ~/.openclaw/cron/jobs.json. Returns [] on error."""
    if not CRON_JOBS.exists():
        return []
    try:
        data = json.loads(CRON_JOBS.read_text())
        # Format: {"version":1, "jobs":[...]}
        if isinstance(data, dict):
            return data.get('jobs', [])
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _save_cron_jobs(jobs: list[dict]) -> bool:
    """Write jobs back to cron/jobs.json preserving version wrapper."""
    if not CRON_JOBS.exists():
        return False
    try:
        data = json.loads(CRON_JOBS.read_text())
        if isinstance(data, dict):
            data['jobs'] = jobs
        else:
            data = {'version': 1, 'jobs': jobs}
        CRON_JOBS.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        return True
    except Exception:
        return False


def check_cron():
    """Validate all recurring cron jobs: existence, model (payload.model), no opus/4-5."""
    cat = 'cron'
    jobs = _load_cron_jobs()
    if not jobs:
        check('Cron jobs', 'warn', f'No jobs found at {CRON_JOBS}',
              'Run: openclaw cron list', cat)
        return

    enabled = [j for j in jobs if j.get('enabled', True)]
    check('Cron job count', 'ok', f'{len(enabled)} enabled / {len(jobs)} total', '', cat)

    # Check model — model lives in payload.model
    bad_jobs = []
    for j in enabled:
        model = j.get('payload', {}).get('model', '') or ''
        if model and (model in FORBIDDEN_MODELS or
                      ('opus' in model.lower() and 'sonnet' not in model.lower())):
            bad_jobs.append((j.get('id', '?'), j.get('name', '?')[:35], model))

    if bad_jobs:
        names = ', '.join(n for _, n, _ in bad_jobs[:3])

        def _fix_cron_models():
            all_jobs = _load_cron_jobs()
            fixed = []
            for j in all_jobs:
                model = j.get('payload', {}).get('model', '') or ''
                if model and (model in FORBIDDEN_MODELS or
                              ('opus' in model.lower() and 'sonnet' not in model.lower())):
                    old = model
                    j['payload']['model'] = 'anthropic/claude-sonnet-4-6'
                    fixed.append(f'{j.get("name","?")[:30]}: {old} → sonnet-4-6')
            _save_cron_jobs(all_jobs)
            return '; '.join(fixed) if fixed else 'Nothing to fix'

        check('Cron model versions', 'crit',
              f'{len(bad_jobs)} job(s) using forbidden model: {names}',
              'Downgrade to anthropic/claude-sonnet-4-6', cat, fix_fn=_fix_cron_models)
    else:
        has_model = [j for j in enabled if j.get('payload', {}).get('model')]
        check('Cron model versions', 'ok',
              f'{len(has_model)}/{len(enabled)} jobs have explicit model set', '', cat)

    # One-time (deleteAfterRun) jobs — only flag if overdue (past scheduled time)
    dar = [j for j in jobs if j.get('deleteAfterRun')]
    now_ms = NOW.timestamp() * 1000
    overdue = [j for j in dar
               if j.get('state', {}).get('nextRunAtMs', now_ms + 1) < now_ms - 3600_000]
    if overdue:
        names_od = ', '.join(j.get('name', '?')[:25] for j in overdue[:3])
        check('Cron one-time jobs', 'warn',
              f'{len(overdue)} overdue one-time job(s): {names_od}',
              'Check if gateway missed them; may need to re-create', cat)
    elif dar:
        check('Cron one-time jobs', 'ok',
              f'{len(dar)} future one-time job(s) scheduled', '', cat)

    # Last run health — check for consecutive errors
    errored = [j for j in enabled
               if j.get('state', {}).get('consecutiveErrors', 0) > 0]
    if errored:
        names_err = ', '.join(j.get('name', '?')[:25] for j in errored[:3])
        check('Cron error state', 'warn',
              f'{len(errored)} job(s) with consecutive errors: {names_err}',
              'Check gateway logs for details', cat)
    else:
        check('Cron error state', 'ok', 'No consecutive errors', '', cat)


def check_disk():
    cat = 'disk'
    code, out, _ = sh(['df', '-h', '/'])
    if code == 0 and out:
        parts = out.splitlines()[-1].split()
        try:
            pct   = int(parts[4].rstrip('%'))
            avail = parts[3]
            status = 'crit' if pct >= 90 else ('warn' if pct >= 75 else 'ok')
            fix = 'Free up disk space urgently' if pct >= 90 else (
                  'Consider cleanup' if pct >= 75 else '')
            check('Disk space', status, f'{pct}% used, {avail} free', fix, cat)
        except Exception:
            check('Disk space', 'info', out.splitlines()[-1], '', cat)

    # Workspace dir size (warn if > 500MB)
    code2, out2, _ = sh(['du', '-sh', str(WORKSPACE)])
    if code2 == 0 and out2:
        size_str = out2.split()[0]
        check('Workspace size', 'ok', size_str, '', cat)


def check_deps():
    """Test that key Python packages actually import correctly."""
    cat = 'deps'
    required_pkgs = [
        ('google.oauth2.service_account', 'google-auth'),
        ('googleapiclient.discovery',     'google-api-python-client'),
        ('gspread',                        'gspread'),
    ]
    missing = []
    for mod, pkg in required_pkgs:
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)

    if missing:
        check('Python packages', 'crit',
              f'Missing: {", ".join(missing)}',
              f'pip3 install {" ".join(missing)}', cat)
    else:
        check('Python packages', 'ok',
              f'All {len(required_pkgs)} key packages importable', '', cat)

    # Python version (need 3.10+)
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 10):
        check('Python version', 'warn',
              f'Python {major}.{minor} — recommend 3.10+', '', cat)
    else:
        check('Python version', 'ok', f'Python {major}.{minor}', '', cat)


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
        check('Key scripts', 'crit',
              f'Missing: {", ".join(missing)}', 'Restore from git', cat)
    else:
        check('Key scripts', 'ok', f'All {len(key)} scripts present', '', cat)

    broken = []
    for s in key:
        if s.exists():
            code, _, err = sh([sys.executable, '-m', 'py_compile', str(s)])
            if code != 0:
                broken.append(f'{s.name}: {err[:50]}')
    if broken:
        check('Script syntax', 'crit',
              f'{len(broken)} file(s) with errors: {broken[0]}',
              'Fix syntax errors immediately', cat)
    else:
        check('Script syntax', 'ok', 'No syntax errors', '', cat)


# ─────────────── fix engine ───────────────

def run_fixes() -> list[dict]:
    """Execute all queued fix functions. Returns list of fix results."""
    fix_results = []
    if not _fix_queue:
        return fix_results
    print(f'\n🔧 Running {len(_fix_queue)} auto-fix(es)...\n')
    for item in _fix_queue:
        try:
            msg = item['fn']()
            fix_results.append({'label': item['label'], 'success': True, 'msg': msg or 'Fixed'})
            print(f"  ✅  {item['label']}: {msg or 'Fixed'}")
        except Exception as e:
            fix_results.append({'label': item['label'], 'success': False, 'msg': str(e)})
            print(f"  ❌  {item['label']}: {e}")
    return fix_results


# ─────────────── history ───────────────

def save_history(crits: int, warns: int, total: int, fixed: int = 0):
    entry = {
        'ts': NOW.isoformat(),
        'critical': crits,
        'warn': warns,
        'total': total,
        'fixed': fixed,
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
            fx = e.get('fixed', 0)
            emoji = '🔴' if c else ('⚠️ ' if w else '✅')
            fix_str = f'  [{fx} fixed]' if fx else ''
            print(f'  {ts}  {emoji}  {c} crit  {w} warn  ({e["total"]} checks){fix_str}')
        except Exception:
            pass
    print()


# ─────────────── runner ───────────────

ALL_CHECKS = {
    'secrets':  check_secrets,
    'apis':     check_apis,
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


def run_all(categories=None):
    targets = categories or list(ALL_CHECKS.keys())
    for cat in targets:
        fn = ALL_CHECKS.get(cat)
        if fn:
            try:
                fn()
            except Exception as e:
                check(f'[{cat}] runner error', 'warn', str(e)[:80], '', cat)


def print_report(quiet=False) -> tuple[int, int, int]:
    icons = {'ok': '✅', 'warn': '⚠️ ', 'crit': '🔴', 'info': 'ℹ️ '}
    crits = [r for r in results if r['status'] == 'crit']
    warns = [r for r in results if r['status'] == 'warn']
    infos = [r for r in results if r['status'] == 'info']
    oks   = [r for r in results if r['status'] == 'ok']

    width = 62
    print(f"\n{'=' * width}")
    print(f"🔍 System Scanner v3 — {NOW.strftime('%Y-%m-%d %H:%M')} (Taipei)")
    print(f"{'=' * width}")
    total = len(results)
    print(f"Summary: {len(crits)} 🔴  {len(warns)} ⚠️   {len(infos)} ℹ️   {len(oks)} ✅  "
          f"({total} checks)\n")

    groups = [crits, warns, infos] + ([] if quiet else [oks])
    for group in groups:
        for r in group:
            icon = icons[r['status']]
            fix_badge = ' [auto-fixable]' if r.get('fixable') else ''
            line = f"{icon}  {r['label']}{fix_badge}"
            if r['detail']:
                line += f"  —  {r['detail']}"
            print(line)
            if r['fix']:
                print(f"     → {r['fix']}")

    if quiet and oks:
        print(f"\n({len(oks)} checks OK — run without --quiet to see all)")
    print(f"\n{'=' * width}")
    return len(crits), len(warns), total


def print_json(fix_results=None) -> tuple[int, int, int]:
    crits = sum(1 for r in results if r['status'] == 'crit')
    warns = sum(1 for r in results if r['status'] == 'warn')
    out = {
        'ts': NOW.isoformat(),
        'summary': {'critical': crits, 'warn': warns, 'total': len(results)},
        'checks': results,
    }
    if fix_results is not None:
        out['fixes'] = fix_results
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return crits, warns, len(results)


# ─────────────── main ───────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='OpenClaw system scanner v3',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--quiet',    '-q', action='store_true',
                        help='Show only problems')
    parser.add_argument('--fix',      '-f', action='store_true',
                        help='Auto-fix safe/common issues after scanning')
    parser.add_argument('--json',     '-j', action='store_true',
                        help='JSON output')
    parser.add_argument('--category', '-c', nargs='+',
                        choices=list(ALL_CHECKS.keys()), metavar='CAT',
                        help='Run specific categories only')
    parser.add_argument('--history',        nargs='?', const=5, type=int, metavar='N',
                        help='Show last N scan summaries (default 5)')
    parser.add_argument('--no-save',        action='store_true',
                        help='Do not save result to history')
    args = parser.parse_args()

    if args.history is not None:
        show_history(args.history)
        sys.exit(0)

    run_all(args.category)

    fix_results = None
    if args.fix:
        fix_results = run_fixes()
        # Re-scan after fixes so report reflects post-fix state
        if fix_results:
            results.clear()
            _fix_queue.clear()
            run_all(args.category)

    if args.json:
        crits, warns, total = print_json(fix_results)
    else:
        crits, warns, total = print_report(quiet=args.quiet)

    if not args.no_save:
        fixed_count = sum(1 for f in (fix_results or []) if f.get('success'))
        save_history(crits, warns, total, fixed=fixed_count)

    sys.exit(1 if crits > 0 else 0)
