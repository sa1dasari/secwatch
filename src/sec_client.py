"""
Thin client around SEC EDGAR's free, no-auth-required endpoints:
- Atom feed of the latest Form 4 filings (updated ~every 10 min by SEC)
- data.sec.gov submissions API, to pull each issuer's SIC code
- The Form 4 primary XML document itself, to pull transaction details

SEC asks that all automated requests carry a descriptive User-Agent
(see config.SEC_USER_AGENT) -- requests without one get rate-limited or
blocked, so don't strip that header.
"""

import time
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import requests

import config

HEADERS = {"User-Agent": config.SEC_USER_AGENT}


def _get(url, **kwargs):
    """GET with SEC's required headers and basic rate-limit courtesy."""
    resp = requests.get(url, headers=HEADERS, timeout=20, **kwargs)
    resp.raise_for_status()
    time.sleep(0.15)  # SEC asks for <=10 req/sec; stay well under that
    return resp


def fetch_latest_form4_entries():
    """
    Pull the latest Form 4 filings from EDGAR's real-time atom feed.
    Returns a list of dicts: accession_no, cik, company_name, filed_at, index_url
    """
    resp = _get(config.EDGAR_ATOM_FEED)
    root = ET.fromstring(resp.content)
    ns = {"a": "http://www.w3.org/2005/Atom"}

    entries = []
    for entry in root.findall("a:entry", ns):
        title = entry.find("a:title", ns).text or ""
        link_el = entry.find("a:link", ns)
        index_url = link_el.attrib["href"] if link_el is not None else None
        updated = entry.find("a:updated", ns).text
        id_el = entry.find("a:id", ns).text or ""

        # title looks like: "4 - Some Biotech Inc (0001234567) (Reporting)"
        m = re.match(r"^(\S+)\s*-\s*(.+?)\s*\((\d{10})\)", title)
        if not m:
            continue
        form_type, company_name, cik = m.group(1), m.group(2), m.group(3)

        acc_match = re.search(r"accession-number=([\d\-]+)", id_el)
        accession_no = acc_match.group(1) if acc_match else None

        entries.append(
            {
                "form_type": form_type,
                "company_name": company_name,
                "cik": cik,
                "accession_no": accession_no,
                "index_url": index_url,
                "filed_at": updated,
            }
        )
    return entries


def get_sic_code(cik):
    """Look up a company's SIC code via the free data.sec.gov submissions API."""
    url = config.SUBMISSIONS_API.format(cik=int(cik))
    try:
        resp = _get(url)
        data = resp.json()
        return str(data.get("sicDescription", "")), str(data.get("sic", ""))
    except Exception:
        return "", ""


def get_form4_xml_url(index_url):
    """
    Given a filing's index page URL, find the primary Form 4 XML document.
    Index pages list all documents in the filing; the ownership XML is
    usually named like 'xslF345X05/*.xml' or ends in '.xml' and isn't
    the index itself.
    """
    resp = _get(index_url)
    # crude but effective: pull all .xml document links from the index page
    candidates = re.findall(r'href="([^"]+\.xml)"', resp.text)
    for c in candidates:
        if "index" not in c.lower():
            if c.startswith("http"):
                return c
            base = index_url.rsplit("/", 1)[0]
            return f"{base}/{c.split('/')[-1]}"
    return None


def parse_form4(xml_url):
    """Fetch a Form 4 XML document by URL and parse it."""
    resp = _get(xml_url)
    return parse_form4_content(resp.content)


def parse_form4_content(xml_bytes):
    """
    Parse Form 4 ownership XML content (bytes or str) into a list of
    transaction dicts. Handles the standard SEC ownership document schema.
    Split out from parse_form4() so it's testable without network access.
    """
    root = ET.fromstring(xml_bytes)

    def text(el, path, default=None):
        found = el.find(path)
        if found is not None and found.text:
            return found.text.strip()
        return default

    issuer = root.find("issuer")
    ticker = text(issuer, "issuerTradingSymbol")
    issuer_name = text(issuer, "issuerName")

    owner = root.find("reportingOwner")
    owner_name = text(owner, "reportingOwnerId/rptOwnerName")
    relationship = owner.find("reportingOwnerRelationship") if owner is not None else None
    is_officer = text(relationship, "isOfficer") == "1" if relationship is not None else False
    officer_title = text(relationship, "officerTitle", "") if relationship is not None else ""
    is_director = text(relationship, "isDirector") == "1" if relationship is not None else False

    role = officer_title if is_officer and officer_title else (
        "Director" if is_director else "10%+ Owner"
    )

    transactions = []
    for tx in root.findall(".//nonDerivativeTransaction"):
        code = text(tx, "transactionCoding/transactionCode")
        date = text(tx, "transactionDate/value")
        shares = text(tx, "transactionAmounts/transactionShares/value")
        price = text(tx, "transactionAmounts/transactionPricePerShare/value")
        shares_owned_after = text(
            tx, "postTransactionAmounts/sharesOwnedFollowingTransaction/value"
        )

        try:
            shares_f = float(shares) if shares else 0.0
            price_f = float(price) if price else 0.0
        except ValueError:
            shares_f, price_f = 0.0, 0.0

        transactions.append(
            {
                "ticker": ticker,
                "issuer_name": issuer_name,
                "owner_name": owner_name,
                "role": role,
                "transaction_code": code,
                "transaction_date": date,
                "shares": shares_f,
                "price_per_share": price_f,
                "total_value": round(shares_f * price_f, 2),
                "shares_owned_after": shares_owned_after,
            }
        )
    return transactions
