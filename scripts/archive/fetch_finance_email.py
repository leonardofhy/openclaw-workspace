#!/usr/bin/env python3
"""Fetch finance emails from ops inbox using IMAP."""
import imaplib
import email
from email.header import decode_header
import os
from pathlib import Path

# Read credentials from secrets
ENV_PATH = Path('/Users/leonardo/.openclaw/workspace/secrets/email_ops.env')
SAVE_DIR = "memory/finance_data"

def load_creds():
    config = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                config[k.strip()] = v.strip()
    return config.get('EMAIL_SENDER', ''), config.get('EMAIL_PASSWORD', '')

if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

def clean_filename(filename):
    return "".join([c for c in filename if c.isalpha() or c.isdigit() or c in "._- "]).strip()

def fetch_latest_finance_email():
    user, password = load_creds()
    if not user or not password:
        print("❌ Email credentials not found in secrets/email_ops.env")
        return
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(user, password)
        mail.select("inbox")
        
        status, messages = mail.search(None, '(SUBJECT "Finance Report")')
        if status != 'OK' or not messages[0]:
            print("No finance emails found.")
            mail.logout()
            return
        
        msg_ids = messages[0].split()
        latest_id = msg_ids[-1]
        
        status, msg_data = mail.fetch(latest_id, "(RFC822)")
        if status != 'OK':
            print("Failed to fetch email.")
            mail.logout()
            return
        
        msg = email.message_from_bytes(msg_data[0][1])
        subject = decode_header(msg["Subject"])[0][0]
        if isinstance(subject, bytes):
            subject = subject.decode()
        print(f"📧 Found: {subject}")
        
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            filename = part.get_filename()
            if filename:
                filename = clean_filename(filename)
                filepath = os.path.join(SAVE_DIR, filename)
                with open(filepath, 'wb') as f:
                    f.write(part.get_payload(decode=True))
                print(f"💾 Saved: {filepath}")
        
        mail.logout()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    fetch_latest_finance_email()
