from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Holding, User
from auth import get_current_user
import httpx
import time
import xml.etree.ElementTree as ET

router = APIRouter(prefix="/insider", tags=["insider"])

_insider_cache: dict = {}
_cik_cache: dict = {}
CACHE_TTL = 600

HEADERS = {"User-Agent": "FolioApp contact@folioapp.com"}

TRANSACTION_CODES = {
    "P": "Purchase",
    "S": "Sale",
    "A": "Award",
    "D": "Disposition",
    "F": "Tax Withholding",
    "G": "Gift",
    "M": "Option Exercise",
    "X": "Option Exercise (Expired)",
    "C": "Conversion",
    "W": "Will/Inheritance",
}


def get_cik_for_ticker(ticker: str) -> str | None:
    if ticker in _cik_cache:
        return _cik_cache[ticker]
    try:
        url = "https://www.sec.gov/files/company_tickers.json"
        resp = httpx.get(url, headers=HEADERS, timeout=10)
        data = resp.json()
        for entry in data.values():
            if entry.get("ticker", "").upper() == ticker.upper():
                cik = str(entry["cik_str"]).zfill(10)
                _cik_cache[ticker] = cik
                return cik
    except Exception:
        pass
    return None


def parse_form4_xml(accession: str, cik: str) -> dict:
    """Parse a Form 4 XML filing to extract detailed transaction info."""
    try:
        acc_clean = accession.replace("-", "")
        url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_clean}/{accession}.txt"
        resp = httpx.get(url, headers=HEADERS, timeout=8)
        text = resp.text

        # Find XML section within the filing
        xml_start = text.find("<?xml")
        xml_end   = text.rfind("</ownershipDocument>")
        if xml_start == -1 or xml_end == -1:
            return {}
        xml_text = text[xml_start:xml_end + len("</ownershipDocument>")]
        root = ET.fromstring(xml_text)

        # Filer info
        reporter_name = ""
        relationship  = ""
        is_director = root.findtext(".//isDirector") or "0"
        is_officer  = root.findtext(".//isOfficer")  or "0"
        officer_title = root.findtext(".//officerTitle") or ""
        rpt_name = root.find(".//reportingOwner/reportingOwnerId/rptOwnerName")
        if rpt_name is not None:
            reporter_name = rpt_name.text or ""

        if is_officer == "1" and officer_title:
            relationship = officer_title
        elif is_director == "1":
            relationship = "Director"
        else:
            relationship = "10% Owner"

        # Transactions
        transactions = []
        for txn in root.findall(".//nonDerivativeTransaction"):
            code_el     = txn.find(".//transactionCode")
            shares_el   = txn.find(".//transactionShares/value")
            price_el    = txn.find(".//transactionPricePerShare/value")
            acquired_el = txn.find(".//transactionAcquiredDisposedCode/value")

            code     = code_el.text   if code_el    is not None else ""
            shares   = float(shares_el.text) if shares_el is not None and shares_el.text else 0
            price    = float(price_el.text)  if price_el  is not None and price_el.text  else 0
            acquired = acquired_el.text      if acquired_el is not None else ""

            txn_type = TRANSACTION_CODES.get(code, code)
            total    = round(shares * price, 2)
            direction = "BUY" if acquired == "A" else "SELL" if acquired == "D" else txn_type

            if shares > 0:
                transactions.append({
                    "type":      direction,
                    "code":      code,
                    "shares":    shares,
                    "price":     price,
                    "total":     total,
                })

        return {
            "reporter_name": reporter_name,
            "relationship":  relationship,
            "transactions":  transactions,
        }
    except Exception:
        return {}


def fetch_insider_trades(ticker: str) -> list:
    now = time.time()
    if ticker in _insider_cache:
        data, ts = _insider_cache[ticker]
        if now - ts < CACHE_TTL:
            return data

    cik = get_cik_for_ticker(ticker)
    if not cik:
        return []

    try:
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        resp = httpx.get(url, headers=HEADERS, timeout=10)
        company = resp.json()

        filings    = company.get("filings", {}).get("recent", {})
        forms      = filings.get("form", [])
        dates      = filings.get("filingDate", [])
        accessions = filings.get("accessionNumber", [])

        trades = []
        count  = 0
        for i, form in enumerate(forms):
            if form != "4":
                continue
            if count >= 10:  # limit XML fetches per ticker
                break

            acc   = accessions[i] if i < len(accessions) else ""
            date  = dates[i]      if i < len(dates)      else ""
            sec_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=4&dateb=&owner=include&count=10"

            # Try to parse detailed XML
            details = parse_form4_xml(acc, cik) if acc else {}
            txns = details.get("transactions", [])

            if txns:
                for txn in txns:
                    trades.append({
                        "ticker":        ticker,
                        "company":       company.get("name", ticker),
                        "filing_date":   date,
                        "insider_name":  details.get("reporter_name", "Unknown"),
                        "position":      details.get("relationship", "Insider"),
                        "transaction":   txn["type"],
                        "shares":        txn["shares"],
                        "price":         txn["price"],
                        "total_value":   txn["total"],
                        "sec_url":       sec_url,
                    })
            else:
                # Fallback if XML parse fails
                trades.append({
                    "ticker":       ticker,
                    "company":      company.get("name", ticker),
                    "filing_date":  date,
                    "insider_name": "Unknown",
                    "position":     "Insider",
                    "transaction":  "Form 4 Filed",
                    "shares":       0,
                    "price":        0,
                    "total_value":  0,
                    "sec_url":      sec_url,
                })
            count += 1

        _insider_cache[ticker] = (trades, now)
        return trades
    except Exception:
        return []


@router.get("/")
def get_insider_trades(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    holdings = db.query(Holding).filter(Holding.user_id == current_user.id).all()
    tickers  = list({h.ticker for h in holdings})[:6]

    all_trades = []
    for ticker in tickers:
        all_trades.extend(fetch_insider_trades(ticker))

    all_trades.sort(key=lambda x: x.get("filing_date", ""), reverse=True)
    return all_trades[:60]


@router.get("/ticker/{ticker}")
def get_insider_trades_for_ticker(
    ticker: str,
    current_user: User = Depends(get_current_user),
):
    return fetch_insider_trades(ticker.upper())
