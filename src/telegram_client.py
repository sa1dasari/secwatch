"""Send a message to a Telegram chat/channel via the Bot API."""

import requests
import config

TELEGRAM_MAX_LEN = 4096


def send_alert(text):
    """Send a single message. For anything that might be long (like a daily
    digest), use send_long_message() instead, which chunks automatically."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("[telegram] Skipped -- bot token or chat id not configured.")
        return

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(
        url,
        json={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": text,
            "disable_web_page_preview": True,
        },
        timeout=15,
    )
    if not resp.ok:
        print(f"[telegram] Failed to send: {resp.status_code} {resp.text}")


def send_long_message(text):
    """Split text into <=4096-char chunks on line boundaries (so we never
    cut a sentence/filing mid-way) and send each as a separate message,
    in order. Use for daily digests, which can exceed the single-message
    limit on a busy day."""
    if not text:
        return

    chunks = []
    current = ""
    for line in text.split("\n"):
        # +1 for the newline we'll rejoin with
        if len(current) + len(line) + 1 > TELEGRAM_MAX_LEN:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)

    total = len(chunks)
    for i, chunk in enumerate(chunks, 1):
        prefix = f"(part {i}/{total})\n" if total > 1 else ""
        send_alert(prefix + chunk)