#!/usr/bin/env python3
"""Send HN digest markdown file as email. Usage: python3 send_digest_email.py [file]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'leo-diary' / 'scripts'))
from email_utils import send_email
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))
date_str = datetime.now(TZ).strftime('%Y-%m-%d')

path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/hn-digest.md'
body = Path(path).read_text()
send_email(f'📰 HN Daily Digest — {date_str}', body)
