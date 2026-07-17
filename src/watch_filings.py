"""
Main entrypoint, run on a schedule (see .github/workflows/watch.yml).

Flow per run:
1. Pull latest Form 4 entries from EDGAR's atom feed.
2. Skip any we've already processed (state/seen.json).
3. For each new Form 4, look up the issuer's SIC code.
4. If the SIC code matches our niche AND the filing has a qualifying
   purchase transaction (code + dollar threshold from config.py):
     - Summarize it with Claude
     - Send an instant Telegram alert
     - Queue it for the daily email digest
5. Persist updated state.
"""

import sys
import traceback

import config
import sec_client
import claude_client
import telegram_client
import state_store


def process_entry(entry, seen):
    if entry["form_type"] != "4":
        return
    if entry["accession_no"] in seen:
        return
    seen.add(entry["accession_no"])

    if not entry["index_url"] or not entry["cik"]:
        return

    sic_description, sic_code = sec_client.get_sic_code(entry["cik"])
    sector_name = config.get_sector_name(sic_code)
    if sector_name is None:
        return

    xml_url = sec_client.get_form4_xml_url(entry["index_url"])
    if not xml_url:
        return

    try:
        transactions = sec_client.parse_form4(xml_url)
    except Exception as e:
        print(f"[warn] Failed to parse {xml_url}: {e}")
        return

    for tx in transactions:
        if tx["transaction_code"] not in config.TARGET_TRANSACTION_CODES:
            continue
        if tx["total_value"] < config.MIN_TRANSACTION_VALUE:
            continue

        print(f"[match] {tx['owner_name']} bought ${tx['total_value']:,.0f} of {tx['ticker']}")

        try:
            summary = claude_client.summarize_transaction(tx, sector_name, sic_description)
        except Exception as e:
            print(f"[warn] Claude summarization failed, using raw fallback: {e}")
            summary = (
                f"{tx['owner_name']} ({tx['role']}) bought {tx['shares']:,.0f} shares "
                f"of {tx['issuer_name']} (${tx['ticker']}) at ${tx['price_per_share']:.2f}, "
                f"total ${tx['total_value']:,.0f}, on {tx['transaction_date']}."
            )

        alert_text = (
            f"🔔 Insider Buy Alert -- {sector_name}\n\n"
            f"{summary}\n\nFiling: {entry['index_url']}"
        )
        telegram_client.send_alert(alert_text)

        state_store.append_to_digest_queue(
            {
                "sector": sector_name,
                "summary": summary,
                "ticker": tx["ticker"],
                "issuer_name": tx["issuer_name"],
                "total_value": tx["total_value"],
                "filing_url": entry["index_url"],
            }
        )


def main():
    seen = state_store.load_seen()
    try:
        entries = sec_client.fetch_latest_form4_entries()
    except Exception as e:
        print(f"[error] Could not fetch EDGAR feed: {e}")
        traceback.print_exc()
        sys.exit(1)

    print(f"[info] Fetched {len(entries)} recent filings from EDGAR.")

    for entry in entries:
        try:
            process_entry(entry, seen)
        except Exception as e:
            print(f"[warn] Error processing entry {entry.get('accession_no')}: {e}")
            traceback.print_exc()

    state_store.save_seen(seen)
    print("[info] Run complete.")


if __name__ == "__main__":
    main()