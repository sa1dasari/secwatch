"""Summarize a filtered Form 4 transaction into a short, punchy alert using Claude."""

import requests
import config

API_URL = "https://api.anthropic.com/v1/messages"


def summarize_transaction(tx, sector_name, sic_description, prior_buy_count=None):
    """
    tx: dict from sec_client.parse_form4()
    sector_name: human-readable sector label, e.g. "Biotech / Pharma"
                 (from config.get_sector_name())
    sic_description: e.g. "Pharmaceutical Preparations" -- the SEC's own,
                      more granular industry description, used as extra context
    prior_buy_count: optional int, how many prior open-market buys this
                      insider has made this year (pass None if unknown)
    Returns a 2-3 sentence plain-text summary suitable for Telegram/email.
    """
    history_note = (
        f"This is their {prior_buy_count} open-market purchase this year."
        if prior_buy_count
        else "No prior purchase history was checked for this run."
    )

    prompt = f"""You are writing a short, punchy alert for a paid insider-trading alert
service covering small-cap companies across several sectors. Summarize this SEC Form 4
filing in 2-3 sentences, plain text, no markdown. Include: who bought, their role, the
company, the sector, dollar amount, and one line of context on why it might matter
(e.g. notable size, insider conviction, timing). Be factual and neutral -- do not give
investment advice or tell the reader to buy/sell.

Sector: {sector_name} ({sic_description})
Insider: {tx['owner_name']} ({tx['role']})
Company: {tx['issuer_name']} (${tx['ticker']})
Transaction: {tx['shares']:,.0f} shares at ${tx['price_per_share']:.2f}/share
Total value: ${tx['total_value']:,.0f}
Date: {tx['transaction_date']}
Shares owned after: {tx['shares_owned_after']}
{history_note}
"""

    resp = requests.post(
        API_URL,
        headers={
            "x-api-key": config.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": config.CLAUDE_MODEL,
            "max_tokens": 300,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return "".join(
        block["text"] for block in data.get("content", []) if block.get("type") == "text"
    ).strip()