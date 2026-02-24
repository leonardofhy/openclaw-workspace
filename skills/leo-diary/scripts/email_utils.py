"""Shared email utility - reads credentials from secrets/email_ops.env."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent.parent.parent / 'secrets' / 'email_ops.env'

def _load_config():
    config = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                config[k.strip()] = v.strip()
    return config

def send_email(subject, body, sender_label=None, receiver=None):
    """Send email using ops credentials from secrets/email_ops.env."""
    cfg = _load_config()
    sender = cfg.get('EMAIL_SENDER', '')
    password = cfg.get('EMAIL_PASSWORD', '')
    sender_name = sender_label or cfg.get('EMAIL_SENDER_NAME', 'Little Leo')
    to = receiver or cfg.get('EMAIL_RECEIVER', '')
    
    if not all([sender, password, to]):
        print("❌ Email config incomplete (check secrets/email_ops.env)")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = formataddr((sender_name, sender))
        msg['To'] = to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, password)
            server.sendmail(sender, to, msg.as_string())
        print(f"📧 Email sent: {subject}")
        return True
    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False
