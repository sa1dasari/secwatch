"""
Central config for SEC Form 4 Insider Watch.
Change these values to retarget the whole pipeline at a different niche
(sector, dollar threshold, transaction type) without touching the rest
of the code.
"""

import os

# --- SEC EDGAR ---
# SEC requires a descriptive User-Agent identifying who's making requests.
# Format: "Company/AppName contact@email.com" -- update with your real email.
SEC_USER_AGENT = os.environ.get(
    "SEC_USER_AGENT", " SEC Insider Watch secwatchbot@gmail.com"
)
EDGAR_ATOM_FEED = (
    "https://www.sec.gov/cgi-bin/browse-edgar"
    "?action=getcurrent&type=4&company=&dateb=&owner=include&count=100&output=atom"
)
SUBMISSIONS_API = "https://data.sec.gov/submissions/CIK{cik:010d}.json"

# --- Niche filter: named sector groups ---
# Each key is a human-readable sector label used in alerts/emails.
# Each value is the set of SIC codes that count as "in" that sector.
# Add/remove sectors or codes here -- nothing else in the pipeline needs
# to change. A filing only needs to match ONE sector to qualify.
SECTOR_GROUPS = {
    "Biotech / Pharma": {"2836", "8731", "2834", "8071"},
    "Semiconductors / Hardware": {"3674", "3559", "3827", "3576"},
    "Software / Tech": {"7372", "7371", "7379", "7370"},
    "Energy / Cleantech": {"2911", "1311", "4911", "3674"},  # note: 3674 also used for solar wafer mfrs
    "Financial Services": {"6199", "6211", "6021", "6770"},
    "Consumer / Retail": {"5961", "5731", "2300", "5411"},
}

# Flat set of every SIC code across all sectors -- used for the initial filter.
TARGET_SIC_CODES = {code for codes in SECTOR_GROUPS.values() for code in codes}


def get_sector_name(sic_code):
    """Return the human-readable sector label for a SIC code, or None if
    it doesn't match any configured sector."""
    for sector_name, codes in SECTOR_GROUPS.items():
        if sic_code in codes:
            return sector_name
    return None

# Small-cap ceiling in USD. Market cap isn't in the Form 4 itself, so this is
# checked separately (see market_cap.py) using shares outstanding * price.
MAX_MARKET_CAP = 500_000_000  # $500M

# Only alert on these Form 4 transaction codes.
# P = open market purchase, S = open market sale. Default: buys only.
TARGET_TRANSACTION_CODES = {"P"}

# Minimum total dollar value (shares * price) to bother alerting on.
# Filters out routine small option-exercise noise.
MIN_TRANSACTION_VALUE = 100_000  # $100k

# --- Polling ---
POLL_LOOKBACK_MINUTES = 45  # slightly wider than the cron interval to avoid gaps

# --- State files (persisted in the repo between Action runs) ---
STATE_DIR = os.path.join(os.path.dirname(__file__), "..", "state")
SEEN_FILE = os.path.join(STATE_DIR, "seen.json")
DIGEST_QUEUE_FILE = os.path.join(STATE_DIR, "digest_queue.json")

# --- Claude API ---
CLAUDE_MODEL = "claude-sonnet-5"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# --- Email (SMTP) ---
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")  # use an app password, not your real password
DIGEST_FROM = os.environ.get("DIGEST_FROM", SMTP_USER)
DIGEST_TO = os.environ.get("DIGEST_TO")  # comma-separated list of recipients