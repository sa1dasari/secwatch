"""Run once daily (see .github/workflows/daily_digest.yml) to email everything
queued up by watch_filings.py since the last digest."""

from datetime import date
import state_store
import email_client


def main():
    items = state_store.load_digest_queue()
    if not items:
        print("[info] Nothing to digest today.")
        return

    lines = [f"Insider Buy Digest -- {date.today().isoformat()}", ""]
    lines.append(f"{len(items)} qualifying insider purchase(s) today:\n")
    for i, item in enumerate(items, 1):
        lines.append(f"{i}. {item['issuer_name']} (${item['ticker']}) -- ${item['total_value']:,.0f}")
        lines.append(f"   {item['summary']}")
        lines.append(f"   Filing: {item['filing_url']}\n")

    body = "\n".join(lines)
    email_client.send_digest(
        subject=f"Insider Buy Digest -- {date.today().isoformat()} ({len(items)} alerts)",
        body_text=body,
    )

    state_store.save_digest_queue([])  # clear queue after sending
    print("[info] Digest sent and queue cleared.")


if __name__ == "__main__":
    main()
