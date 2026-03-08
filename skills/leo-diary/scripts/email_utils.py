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

def _md_to_html(text):
    """Convert markdown to styled HTML email body."""
    try:
        import markdown
        html_body = markdown.markdown(text, extensions=['tables', 'fenced_code', 'nl2br'])
    except ImportError:
        # Fallback: wrap in <pre> if markdown not installed
        import html
        html_body = f"<pre>{html.escape(text)}</pre>"
    return f"""<html><body style="font-family: -apple-system, Arial, sans-serif; font-size: 15px; line-height: 1.6; color: #222; max-width: 680px; margin: 0 auto; padding: 16px;">
{html_body}
</body></html>"""


def send_email(subject, body, sender_label=None, receiver=None):
    """Send email using ops credentials from secrets/email_ops.env.
    
    Body is treated as markdown and converted to HTML automatically.
    A plain-text fallback is also attached.
    """
    cfg = _load_config()
    sender = cfg.get('EMAIL_SENDER', '')
    password = cfg.get('EMAIL_PASSWORD', '')
    sender_name = sender_label or cfg.get('EMAIL_SENDER_NAME', 'Little Leo')
    to = receiver or cfg.get('EMAIL_RECEIVER', '')
    
    if not all([sender, password, to]):
        print("❌ Email config incomplete (check secrets/email_ops.env)")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = formataddr((sender_name, sender))
        msg['To'] = to
        msg['Subject'] = subject
        # Plain text fallback
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        # HTML version (preferred by email clients)
        msg.attach(MIMEText(_md_to_html(body), 'html', 'utf-8'))
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, password)
            server.sendmail(sender, to, msg.as_string())
        print(f"📧 Email sent: {subject}")
        return True
    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False
