#!/usr/bin/env python3
"""OpenClaw system scanner — diagnose and optionally auto-fix issues.

Usage:
  python3 scan.py               # full report
  python3 scan.py --quiet       # problems only
  python3 scan.py --json        # machine-readable output
  python3 scan.py --category git memory   # run specific categories

Categories: secrets, git, memory, gateway, disk, scripts
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────
TZ_OFFSET_HOURS = 8  # Change to match your timezone
TZ = timezone(timedelta(hours=TZ_OFFSET_HOURS))

import os

def find_workspace():
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        if os.path.isdir(os.path.join(d, '.git')):
            return Path(d)
        d = os.path.dirname(d)
    return Path.home() / '.openclaw' / 'workspace'

WORKSPACE = find_workspace()
MEMORY = WORKSPACE / 'memory'
OPENCLAW = Path.home() / '.openclaw'

NOW = datetime.now(TZ)

# ── Scan context ───────────────────────────────────────────────────────────

@dataclass
class ScanContext:
    results: list[dict] = field(default_factory=list)


def check(ctx: ScanContext, label: str, status: str, detail: str = '', fix_hint: str = ''):
    """Record a check result. status: ok | warn | crit | info"""
    ctx.results.append({
        'label': label,
        'status': status,
        'detail': detail,
        'fix': fix_hint,
    })


def sh(cmd: list, cwd=None, timeout=10):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return -1, '', str(e)


# ── Check functions ────────────────────────────────────────────────────────

def check_secrets(ctx):
    """Check that required secret files exist."""
    secrets_dir = WORKSPACE / 'secrets'
    required = ['todoist.env', 'google-service-account.json', 'email_ops.env']

    for name in required:
        path = secrets_dir / name
        if not path.exists():
            check(ctx, f'secrets/{name}', 'warn', 'File missing', f'Create {path} with appropriate credentials')
        elif path.stat().st_size == 0:
            check(ctx, f'secrets/{name}', 'warn', 'File is empty', f'Add credentials to {path}')
        else:
            check(ctx, f'secrets/{name}', 'ok')


def check_git(ctx):
    """Check git status."""
    rc, out, _ = sh(['git', 'status', '--short'], cwd=WORKSPACE)
    if rc != 0:
        check(ctx, 'git', 'warn', 'Not a git repo or git not available')
        return

    if out:
        lines = out.strip().splitlines()
        check(ctx, 'git/uncommitted', 'warn', f'{len(lines)} uncommitted change(s)',
              'git add -A && git commit -m "sync" && git push')
    else:
        check(ctx, 'git/uncommitted', 'ok')

    # Check for unpushed commits
    rc, out, _ = sh(['git', 'log', '--oneline', '@{push}..HEAD'], cwd=WORKSPACE)
    if rc == 0 and out:
        lines = out.strip().splitlines()
        check(ctx, 'git/unpushed', 'warn', f'{len(lines)} unpushed commit(s)', 'git push')
    elif rc == 0:
        check(ctx, 'git/unpushed', 'ok')


def check_memory(ctx):
    """Check memory file coverage."""
    today = NOW.strftime('%Y-%m-%d')
    coverage = 0
    for i in range(7):
        d = (NOW - timedelta(days=i)).strftime('%Y-%m-%d')
        if (MEMORY / f'{d}.md').exists():
            coverage += 1

    if coverage < 3:
        check(ctx, 'memory/coverage', 'warn',
              f'{coverage}/7 days have daily notes',
              'Bot should create daily memory files automatically')
    else:
        check(ctx, 'memory/coverage', 'ok', f'{coverage}/7 days have daily notes')

    # MEMORY.md freshness
    mem_path = WORKSPACE / 'MEMORY.md'
    if mem_path.exists():
        mtime = datetime.fromtimestamp(mem_path.stat().st_mtime, tz=TZ)
        age_days = (NOW - mtime).days
        if age_days > 14:
            check(ctx, 'memory/freshness', 'warn',
                  f'MEMORY.md last modified {age_days} days ago',
                  'Review and update MEMORY.md during next heartbeat')
        else:
            check(ctx, 'memory/freshness', 'ok', f'Updated {age_days} days ago')
    else:
        check(ctx, 'memory/freshness', 'warn', 'MEMORY.md not found', 'Create MEMORY.md')


def check_gateway(ctx):
    """Check OpenClaw gateway status."""
    rc, out, _ = sh(['pgrep', '-f', 'openclaw'], timeout=5)
    if rc == 0:
        check(ctx, 'gateway', 'ok', 'OpenClaw process running')
    else:
        check(ctx, 'gateway', 'info', 'No OpenClaw process detected',
              'Start with: openclaw gateway start')


def check_disk(ctx):
    """Check disk usage."""
    rc, out, _ = sh(['df', '-h', str(WORKSPACE)])
    if rc != 0:
        check(ctx, 'disk', 'info', 'Could not check disk usage')
        return

    lines = out.strip().splitlines()
    if len(lines) >= 2:
        parts = lines[1].split()
        for part in parts:
            if part.endswith('%'):
                pct = int(part.rstrip('%'))
                if pct >= 90:
                    check(ctx, 'disk', 'crit', f'Disk usage at {pct}%', 'Free up disk space')
                elif pct >= 75:
                    check(ctx, 'disk', 'warn', f'Disk usage at {pct}%', 'Consider cleanup')
                else:
                    check(ctx, 'disk', 'ok', f'Disk usage at {pct}%')
                return


def check_scripts(ctx):
    """Check that core scripts exist."""
    scripts = [
        'skills/shared/boot_budget_check.py',
        'skills/shared/ensure_state.py',
        'skills/shared/jsonl_store.py',
        'skills/self-improve/scripts/learn.py',
        'skills/remember/scripts/append_memory.py',
    ]
    missing = [s for s in scripts if not (WORKSPACE / s).exists()]
    if missing:
        check(ctx, 'scripts', 'warn', f'{len(missing)} core script(s) missing: {", ".join(missing)}')
    else:
        check(ctx, 'scripts', 'ok', f'All {len(scripts)} core scripts present')


# ── Runner ─────────────────────────────────────────────────────────────────

ALL_CHECKS = {
    'secrets': check_secrets,
    'git': check_git,
    'memory': check_memory,
    'gateway': check_gateway,
    'disk': check_disk,
    'scripts': check_scripts,
}


def run_all(categories=None):
    ctx = ScanContext()
    checks = {k: v for k, v in ALL_CHECKS.items() if not categories or k in categories}
    for name, fn in checks.items():
        try:
            fn(ctx)
        except Exception as e:
            check(ctx, name, 'warn', f'Check failed: {e}')
    return ctx


def print_report(ctx, quiet=False):
    icon = {'ok': '✅', 'warn': '⚠️', 'crit': '🔴', 'info': 'ℹ️'}

    print(f"System Scan — {NOW.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    for r in ctx.results:
        if quiet and r['status'] == 'ok':
            continue
        i = icon.get(r['status'], '?')
        line = f"  {i} {r['label']}"
        if r['detail']:
            line += f": {r['detail']}"
        print(line)
        if r['fix'] and r['status'] in ('warn', 'crit'):
            print(f"     → {r['fix']}")

    crits = sum(1 for r in ctx.results if r['status'] == 'crit')
    warns = sum(1 for r in ctx.results if r['status'] == 'warn')
    print("-" * 60)
    print(f"  Summary: {crits} critical, {warns} warnings, {len(ctx.results)} total checks")


def main():
    parser = argparse.ArgumentParser(description="OpenClaw system scanner")
    parser.add_argument('--quiet', action='store_true', help='Show problems only')
    parser.add_argument('--json', action='store_true', help='JSON output')
    parser.add_argument('--category', nargs='+', choices=list(ALL_CHECKS.keys()),
                        help='Run specific categories only')
    args = parser.parse_args()

    ctx = run_all(args.category)

    if args.json:
        print(json.dumps(ctx.results, indent=2))
    else:
        print_report(ctx, quiet=args.quiet)

    has_crit = any(r['status'] == 'crit' for r in ctx.results)
    sys.exit(1 if has_crit else 0)


if __name__ == '__main__':
    main()
