# SEC Insider Buy Watch

Watches SEC EDGAR in near-real-time for Form 4 filings (insider stock
transactions), filters down to a specific niche (default: small-cap
biotech open-market purchases over $100k), summarizes matches with
Claude, and sends:

- **Instant alerts** to a Telegram bot/channel
- **A daily digest email** of everything that matched that day

Runs entirely on GitHub Actions -- no server to host, no monthly infra
cost. State (which filings have been seen, what's queued for the digest)
is persisted as JSON files committed back to the repo.

## How it works

```
watch.yml (every 30 min, market hours, Mon-Fri)
  -> watch_filings.py
      -> sec_client.fetch_latest_form4_entries()   [EDGAR atom feed]
      -> sec_client.get_sic_code()                  [filter: is it biotech?]
      -> sec_client.parse_form4()                   [extract transaction]
      -> filter: transaction code == P, value >= $100k
      -> claude_client.summarize_transaction()       [2-3 sentence alert]
      -> telegram_client.send_alert()                [instant push]
      -> state_store.append_to_digest_queue()        [save for later]

daily_digest.yml (once daily, after market close)
  -> send_digest.py
      -> reads state/digest_queue.json
      -> email_client.send_digest()
      -> clears the queue
```

## Known limitations / next steps

- **Market cap filtering isn't implemented yet.** `MAX_MARKET_CAP` is defined
  in config but not checked -- Form 4 doesn't include market cap directly.
  To add it: pull `sharesOutstanding` from the company's latest 10-K/10-Q via
  the XBRL companyfacts API (`data.sec.gov/api/xbrl/companyfacts/CIK##########.json`)
  and multiply by a recent price (e.g. from a free quote API) to estimate cap.
- **No "prior purchase history" signal yet** -- the Claude prompt has a slot for
  it (`prior_buy_count`) but it's not being populated. Could compute this by
  checking the reporting owner's CIK against their filing history.
- **Cron timing is fixed UTC**, so it drifts by an hour across daylight saving
  transitions. Fine for a v1; not worth over-engineering yet.
- **Monetization/paywall isn't built.** This repo is the alerting engine only.
  Adding paid tiers means gating the Telegram channel (Telegram supports native
  paid channel subscriptions) or adding a simple Stripe-gated signup flow that
  writes approved subscriber chat_ids/emails into config instead of a single
  hardcoded channel.
