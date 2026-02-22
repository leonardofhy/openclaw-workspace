#!/usr/bin/env python3
"""Quick email test using shared email_utils."""
import sys
sys.path.insert(0, '/Users/leonardo/.openclaw/workspace/skills/leo-diary/scripts')
from email_utils import send_email

send_email(
    "🦁 Hello from your new Ops Agent!",
    "If you're reading this, the email pipeline is working!\n\n-- Little Leo Ops",
    sender_label="Little Leo Ops"
)
