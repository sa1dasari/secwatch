"""Send the daily digest email via SMTP."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import config


def send_digest(subject, body_text):
    if not config.SMTP_USER or not config.SMTP_PASSWORD or not config.DIGEST_TO:
        print("[email] Skipped -- SMTP credentials or recipients not configured.")
        return

    msg = MIMEMultipart()
    msg["From"] = config.DIGEST_FROM
    msg["To"] = config.DIGEST_TO
    msg["Subject"] = subject
    msg.attach(MIMEText(body_text, "plain"))

    recipients = [addr.strip() for addr in config.DIGEST_TO.split(",")]

    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
        server.starttls()
        server.login(config.SMTP_USER, config.SMTP_PASSWORD)
        server.sendmail(config.DIGEST_FROM, recipients, msg.as_string())
    print(f"[email] Digest sent to {recipients}")
