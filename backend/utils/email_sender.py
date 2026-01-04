import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from backend.config import Config

def send_email(to_email: str, subject: str, body: str):
    """Utility to send emails via SMTP."""
    if not Config.SMTP_USER or not Config.SMTP_PASSWORD:
        print("[EMAIL ERROR] SMTP credentials not set. Skipping email.")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = Config.FROM_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'html'))

        with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
            server.starttls()
            server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f"[EMAIL] Successfully sent email to {to_email}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send email: {e}")
        return False
