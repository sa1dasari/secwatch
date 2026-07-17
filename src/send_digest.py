"""Run once daily (see .github/workflows/daily_digest.yml) to send everything
queued up by watch_filings.py since the last digest -- both by email and as
a recap post in the Telegram channel."""

from datetime import date
import config
import state_store
import email_client
import telegram_client


def main():
    items = state_store.load_digest_queue()

    if not items:
        print("[info] Nothing to digest today.")
        telegram_client.send_alert(
            f"📋 Daily Recap -- {date.today().isoformat()}\n\n"
            "No qualifying insider buys across tracked sectors today."
        )
        return

    # Group items by sector so the digest reads as sections, not one flat list.
    by_sector = {}
    for item in items:
        by_sector.setdefault(item.get("sector", "Uncategorized"), []).append(item)

    lines = [f"Insider Buy Digest -- {date.today().isoformat()}", ""]
    lines.append(f"{len(items)} qualifying insider purchase(s) today, across {len(by_sector)} sector(s):\n")

    for sector_name, sector_items in sorted(by_sector.items()):
        lines.append(f"=== {sector_name} ({len(sector_items)}) ===\n")
        for i, item in enumerate(sector_items, 1):
            lines.append(f"{i}. {item['issuer_name']} (${item['ticker']}) -- ${item['total_value']:,.0f}")
            lines.append(f"   {item['summary']}")
            lines.append(f"   Filing: {item['filing_url']}\n")

    body = "\n".join(lines)

    email_client.send_digest(
        subject=f"Insider Buy Digest -- {date.today().isoformat()} ({len(items)} alerts)",
        body_text=body,
    )

    telegram_client.send_long_message(f"📋 {body}")

    state_store.save_digest_queue([])  # clear queue after sending
    print("[info] Digest sent (email + Telegram) and queue cleared.")


if __name__ == "__main__":
    main()