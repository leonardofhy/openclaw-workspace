#!/usr/bin/env python3
"""Check Claude Code plan usage (session, weekly, sonnet-only).

Usage:
    python3 claude_usage.py              # Human-readable output
    python3 claude_usage.py --json       # JSON output (for scripts/heartbeat)
    python3 claude_usage.py --oneline    # Compact one-line summary
"""
import json, re, sys, argparse
import pexpect

ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\][^\x07]*\x07|\x1b[>?][0-9;]*[a-zA-Z]')
PERCENT_RE = re.compile(r'(\d+)%\s*used')

def strip_ansi(text):
    return ANSI_RE.sub('', text)

def parse_usage(raw):
    """Parse /usage output into structured data."""
    clean = strip_ansi(raw)
    lines = [l.strip() for l in clean.splitlines() if l.strip()]
    
    result = {
        'session': None,
        'weekly_all': None,
        'weekly_sonnet': None,
        'extra_usage': None,
        'session_reset': None,
        'weekly_reset': None,
        'raw_lines': []
    }
    
    context = None
    for line in lines:
        result['raw_lines'].append(line)
        lo = line.lower()
        
        # Context detection (handle joined words from ANSI stripping)
        if 'currentsession' in lo.replace(' ', '') or 'curretsession' in lo.replace(' ', ''):
            context = 'session'
        elif 'allmodels' in lo.replace(' ', '') or 'week(all' in lo:
            context = 'weekly_all'
        elif 'sonnetonly' in lo.replace(' ', '') or 'sonnet' in lo and 'week' in lo:
            context = 'weekly_sonnet'
        elif 'extrausage' in lo.replace(' ', ''):
            context = 'extra'
        
        # Extract percentage (handles "13%used", "13% used", etc.)
        m = re.search(r'(\d+)%\s*used', lo.replace(' ', ''))
        if not m:
            m = re.search(r'(\d+)%\s*used', lo)
        if m and context:
            pct = int(m.group(1))
            if context == 'session' and result['session'] is None:
                result['session'] = pct
            elif context == 'weekly_all' and result['weekly_all'] is None:
                result['weekly_all'] = pct
            elif context == 'weekly_sonnet' and result['weekly_sonnet'] is None:
                result['weekly_sonnet'] = pct
        
        # Extract reset time
        if 'reset' in lo or 'rese' in lo:
            reset_text = line.strip()
            if context == 'session' and result['session_reset'] is None:
                result['session_reset'] = reset_text
            elif context in ('weekly_all', 'weekly_sonnet') and result['weekly_reset'] is None:
                result['weekly_reset'] = reset_text
        
        # Extra usage status
        if 'notenabled' in lo.replace(' ', '') or 'not enabled' in lo:
            result['extra_usage'] = 'not_enabled'
        elif 'enabled' in lo and context == 'extra' and 'not' not in lo:
            result['extra_usage'] = 'enabled'
    
    return result

def check_usage(timeout=25):
    """Launch claude interactively, send /usage, capture and parse output."""
    import time
    child = pexpect.spawn('claude', encoding='utf-8', timeout=timeout,
                          dimensions=(40, 120))
    
    try:
        # Wait for the prompt to appear
        child.expect(['❯', '>', r'\$'], timeout=timeout)
        time.sleep(2)  # Let UI fully settle
        
        # Type /usage and wait for autocomplete to appear
        child.send('/usage')
        time.sleep(1)  # Wait for autocomplete dropdown
        
        # Press Enter to confirm the command
        child.send('\r')
        time.sleep(3)  # Wait for usage data to load from API
        
        # Read all available output
        try:
            child.expect('cancel', timeout=10)
            raw_output = child.before + child.after
        except pexpect.TIMEOUT:
            raw_output = child.before or ''
        
        # Collect any remaining output
        time.sleep(1)
        try:
            remaining = child.read_nonblocking(size=10000, timeout=2)
            raw_output += remaining
        except (pexpect.TIMEOUT, pexpect.EOF):
            pass
        
        # Exit claude
        child.send('\x1b')  # Escape to close usage panel
        time.sleep(0.5)
        child.sendline('/exit')
        try:
            child.expect(pexpect.EOF, timeout=5)
        except pexpect.TIMEOUT:
            pass
        
        return parse_usage(raw_output)
        
    except pexpect.TIMEOUT:
        # Try to capture whatever we got
        raw_output = child.before or ''
        return parse_usage(raw_output)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        return None
    finally:
        if child.isalive():
            child.terminate(force=True)

def format_bar(pct, width=8):
    """Create a compact progress bar."""
    if pct is None:
        return '❓ (could not read)'
    filled = int(width * pct / 100)
    bar = '█' * filled + '░' * (width - filled)
    if pct >= 80:
        emoji = '🔴'
    elif pct >= 50:
        emoji = '🟡'
    else:
        emoji = '🟢'
    return f'{emoji} {bar} {pct:>3d}%'

def clean_reset_time(raw):
    """Extract a human-readable reset time from raw parsed text."""
    if not raw:
        return None
    import re as _re
    # Try to find time patterns like "11pm", "11:00 PM", "Mar 20 12pm", etc.
    clean = strip_ansi(raw)
    # Remove "Reset" prefix variants (Resets, Rese, etc.)
    clean = _re.sub(r'(?i)^rese?t?s?\s*:?\s*', '', clean).strip()
    if not clean:
        return None
    return clean

def main():
    parser = argparse.ArgumentParser(description='Check Claude Code plan usage')
    parser.add_argument('--json', action='store_true', help='Output JSON')
    parser.add_argument('--oneline', action='store_true', help='Compact one-line output')
    parser.add_argument('--timeout', type=int, default=25, help='Timeout in seconds')
    parser.add_argument('--retries', type=int, default=2, help='Number of retries on failure')
    args = parser.parse_args()
    
    usage = None
    for attempt in range(args.retries + 1):
        usage = check_usage(timeout=args.timeout)
        if usage and usage.get('session') is not None:
            break
        if attempt < args.retries:
            import time
            print(f'⏳ Retry {attempt + 1}...', file=sys.stderr)
            time.sleep(2)
    
    if not usage:
        print('❌ Failed to retrieve usage data', file=sys.stderr)
        sys.exit(1)
    
    if args.json:
        out = {k: v for k, v in usage.items()}
        print(json.dumps(out, indent=2, ensure_ascii=False))
    elif args.oneline:
        s = usage.get('session') or '?'
        w = usage.get('weekly_all') or '?'
        ws = usage.get('weekly_sonnet') or '?'
        print(f'Session: {s}% | Week(all): {w}% | Week(sonnet): {ws}%')
    else:
        s_reset = clean_reset_time(usage.get('session_reset'))
        w_reset = clean_reset_time(usage.get('weekly_reset'))
        s_tag = f'  (reset {s_reset})' if s_reset else ''
        w_tag = f'  (reset {w_reset})' if w_reset else ''
        
        print('📊 Claude Max 額度')
        print(f'  Session  {format_bar(usage["session"])}{s_tag}')
        print(f'  Weekly   {format_bar(usage["weekly_all"])}{w_tag}')
        print(f'  Sonnet   {format_bar(usage["weekly_sonnet"])}{w_tag}')
        if usage.get('extra_usage'):
            print(f'  Extra: {usage["extra_usage"]}')

if __name__ == '__main__':
    main()
