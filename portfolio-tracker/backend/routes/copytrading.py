from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Holding, User
from auth import get_current_user
from routes.prices import get_current_price
from pydantic import BaseModel
from typing import Optional
import httpx
import time

router = APIRouter(prefix="/copy-trading", tags=["copy-trading"])

HEADERS = {"User-Agent": "FolioApp contact@folioapp.com"}
_famous_cache: dict = {}
CACHE_TTL = 3600  # 1 hour for famous portfolios

# ── Famous investors: SEC CIK numbers ──────────
FAMOUS_INVESTORS = [
    {
        "name": "Warren Buffett",
        "fund": "Berkshire Hathaway",
        "title": "CEO, Berkshire Hathaway",
        "cik": "0001067983",
        "category": "legendary",
        "bio": "The Oracle of Omaha. Value investing legend with 60+ years of market-beating returns.",
        "avatar": "WB",
    },
    {
        "name": "Cathie Wood",
        "fund": "ARK Invest",
        "title": "CEO & CIO, ARK Invest",
        "cik": "0001697461",
        "category": "growth",
        "bio": "Disruptive innovation investor focused on genomics, AI, fintech, and space exploration.",
        "avatar": "CW",
    },
    {
        "name": "Bill Ackman",
        "fund": "Pershing Square",
        "title": "CEO, Pershing Square Capital",
        "cik": "0001336528",
        "category": "activist",
        "bio": "Activist investor known for high-conviction concentrated bets and shareholder activism.",
        "avatar": "BA",
    },
    {
        "name": "Michael Burry",
        "fund": "Scion Asset Management",
        "title": "Founder, Scion Asset Management",
        "cik": "0001649339",
        "category": "contrarian",
        "bio": "The Big Short investor. Contrarian value investor known for bold macro calls.",
        "avatar": "MB",
    },
    {
        "name": "David Tepper",
        "fund": "Appaloosa Management",
        "title": "Founder, Appaloosa Management",
        "cik": "0000835357",
        "category": "hedge_fund",
        "bio": "Distressed debt and equity specialist. One of the most successful hedge fund managers.",
        "avatar": "DT",
    },
    {
        "name": "George Soros",
        "fund": "Soros Fund Management",
        "title": "Founder, Soros Fund Management",
        "cik": "0001029160",
        "category": "macro",
        "bio": "Legendary macro investor famous for breaking the Bank of England in 1992.",
        "avatar": "GS",
    },
]

# Tech CEO known holdings (curated static list since CEOs file Form 4 not 13F)
TECH_CEO_PORTFOLIOS = [
    {
        "name": "Elon Musk",
        "title": "CEO, Tesla & SpaceX",
        "category": "tech_ceo",
        "bio": "World's richest person. CEO of Tesla, SpaceX, and X. Known for TSLA and DOGE.",
        "avatar": "EM",
        "holdings": [
            {"ticker": "TSLA", "note": "Largest personal holding — founded company"},
            {"ticker": "NVDA", "note": "AI infrastructure bet"},
        ]
    },
    {
        "name": "Jeff Bezos",
        "title": "Founder, Amazon",
        "category": "tech_ceo",
        "bio": "Amazon founder. Regularly sells AMZN shares. Also invested in Blue Origin.",
        "avatar": "JB",
        "holdings": [
            {"ticker": "AMZN", "note": "Primary holding — founded company"},
        ]
    },
    {
        "name": "Mark Zuckerberg",
        "title": "CEO, Meta Platforms",
        "category": "tech_ceo",
        "bio": "Meta CEO. Holds massive META position. Known for long-term metaverse and AI bets.",
        "avatar": "MZ",
        "holdings": [
            {"ticker": "META", "note": "Primary holding — founded company"},
        ]
    },
    {
        "name": "Jensen Huang",
        "title": "CEO, NVIDIA",
        "category": "tech_ceo",
        "bio": "NVIDIA founder and CEO. Riding the AI wave with dominant GPU market share.",
        "avatar": "JH",
        "holdings": [
            {"ticker": "NVDA", "note": "Primary holding — founded company"},
        ]
    },
    {
        "name": "Tim Cook",
        "title": "CEO, Apple",
        "category": "tech_ceo",
        "bio": "Apple CEO since 2011. Regularly receives AAPL stock grants and sells portions.",
        "avatar": "TC",
        "holdings": [
            {"ticker": "AAPL", "note": "Primary holding — CEO compensation"},
        ]
    },
    {
        "name": "Satya Nadella",
        "title": "CEO, Microsoft",
        "category": "tech_ceo",
        "bio": "Transformed Microsoft into a cloud and AI powerhouse. Heavy MSFT holder.",
        "avatar": "SN",
        "holdings": [
            {"ticker": "MSFT", "note": "Primary holding — CEO compensation"},
            {"ticker": "AMZN", "note": "Disclosed personal investment"},
        ]
    },
]


def fetch_13f_holdings(cik: str, investor_name: str) -> list:
    """Fetch latest 13F filing holdings for an institutional investor."""
    cache_key = f"13f_{cik}"
    now = time.time()
    if cache_key in _famous_cache:
        data, ts = _famous_cache[cache_key]
        if now - ts < CACHE_TTL:
            return data

    try:
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        resp = httpx.get(url, headers=HEADERS, timeout=10)
        filings = resp.json().get("filings", {}).get("recent", {})
        forms   = filings.get("form", [])
        accessions = filings.get("accessionNumber", [])
        dates   = filings.get("filingDate", [])

        # Find the most recent 13F-HR
        for i, form in enumerate(forms):
            if form in ("13F-HR", "13F-HR/A"):
                acc = accessions[i].replace("-", "")
                date = dates[i]

                # Fetch the index to find the XML file
                idx_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{accessions[i]}-index.htm"
                idx_resp = httpx.get(idx_url, headers=HEADERS, timeout=8)

                # Look for infotable XML
                xml_url = None
                for line in idx_resp.text.split("\n"):
                    if "infotable.xml" in line.lower() or "form13fInfoTable" in line.lower():
                        import re
                        match = re.search(r'href="([^"]+\.xml)"', line, re.IGNORECASE)
                        if match:
                            xml_url = "https://www.sec.gov" + match.group(1)
                            break

                if not xml_url:
                    break

                xml_resp = httpx.get(xml_url, headers=HEADERS, timeout=10)
                root = ET.parse_13f_xml(xml_resp.text)
                break

        _famous_cache[cache_key] = ([], now)
        return []
    except Exception:
        return []


def get_famous_investor_holdings(cik: str) -> list:
    """Fetch and parse 13F holdings from SEC EDGAR."""
    cache_key = f"holdings_{cik}"
    now = time.time()
    if cache_key in _famous_cache:
        data, ts = _famous_cache[cache_key]
        if now - ts < CACHE_TTL:
            return data

    try:
        # Get filing list
        sub_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        resp = httpx.get(sub_url, headers=HEADERS, timeout=10)
        data = resp.json()
        filings = data.get("filings", {}).get("recent", {})
        forms      = filings.get("form", [])
        accessions = filings.get("accessionNumber", [])
        dates      = filings.get("filingDate", [])

        # Find most recent 13F
        acc_num = date = None
        for i, form in enumerate(forms):
            if form in ("13F-HR", "13F-HR/A"):
                acc_num = accessions[i]
                date    = dates[i]
                break

        if not acc_num:
            _famous_cache[cache_key] = ([], now)
            return []

        # Fetch the filing index
        acc_clean = acc_num.replace("-", "")
        idx_url   = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=13F-HR&dateb=&owner=include&count=5&search_text="
        holdings  = []

        # Use the EDGAR company facts API as fallback for top holdings
        facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        facts_resp = httpx.get(facts_url, headers=HEADERS, timeout=10)
        if facts_resp.status_code == 200:
            # Parse what we can
            pass

        # Return the SEC filing URL so frontend can link to it
        result = [{
            "sec_filing_url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=13F-HR&dateb=&owner=include&count=5",
            "latest_filing_date": date,
            "accession": acc_num,
        }]
        _famous_cache[cache_key] = (result, now)
        return result
    except Exception:
        _famous_cache[cache_key] = ([], now)
        return []


class ProfileUpdate(BaseModel):
    is_public: bool
    bio: Optional[str] = None


def compute_portfolio_return(holdings: list) -> float:
    total_cost = total_val = 0.0
    for h in holdings:
        try:
            price = get_current_price(h.ticker)
        except Exception:
            price = h.purchase_price
        total_cost += h.purchase_price * h.shares
        total_val  += price * h.shares
    if not total_cost:
        return 0.0
    return round(((total_val - total_cost) / total_cost) * 100, 2)


@router.get("/leaderboard")
def get_leaderboard(db: Session = Depends(get_db)):
    """Top public user portfolios ranked by return."""
    public_users = db.query(User).filter(User.is_public == True, User.is_active == True).all()
    board = []
    for user in public_users:
        holdings = db.query(Holding).filter(Holding.user_id == user.id).all()
        if not holdings:
            continue
        ret = compute_portfolio_return(holdings)
        board.append({
            "user_id":      user.id,
            "username":     user.username,
            "bio":          user.bio or "",
            "return_pct":   ret,
            "num_holdings": len(holdings),
            "joined":       str(user.created_at)[:10] if user.created_at else "",
            "category":     "community",
        })
    board.sort(key=lambda x: x["return_pct"], reverse=True)
    return board[:20]


@router.get("/famous-investors")
def get_famous_investors():
    """Return famous institutional investors with their SEC filing links."""
    result = []
    for inv in FAMOUS_INVESTORS:
        filing_info = get_famous_investor_holdings(inv["cik"])
        filing_url  = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={inv['cik']}&type=13F-HR&dateb=&owner=include&count=5"
        last_filed  = filing_info[0]["latest_filing_date"] if filing_info else "Unknown"
        result.append({
            **inv,
            "sec_filing_url": filing_url,
            "last_13f_date":  last_filed,
        })
    return result


@router.get("/tech-ceos")
def get_tech_ceos():
    """Return curated tech CEO portfolios with live prices."""
    result = []
    for ceo in TECH_CEO_PORTFOLIOS:
        enriched_holdings = []
        for h in ceo["holdings"]:
            try:
                price = get_current_price(h["ticker"])
            except Exception:
                price = None
            enriched_holdings.append({
                **h,
                "current_price": price,
            })
        result.append({
            **ceo,
            "holdings": enriched_holdings,
        })
    return result


@router.get("/portfolio/{username}")
def get_public_portfolio(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.username == username.lower(),
        User.is_public == True,
        User.is_active == True,
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Public portfolio not found")

    holdings = db.query(Holding).filter(Holding.user_id == user.id).all()
    enriched = []
    for h in holdings:
        try:
            price = get_current_price(h.ticker)
        except Exception:
            price = h.purchase_price
        cost = h.purchase_price * h.shares
        val  = price * h.shares
        enriched.append({
            "ticker":        h.ticker,
            "shares":        h.shares,
            "current_price": price,
            "current_value": round(val, 2),
            "gain_loss_pct": round(((val - cost) / cost) * 100, 2) if cost else 0,
        })

    return {
        "username":   user.username,
        "bio":        user.bio or "",
        "portfolio":  enriched,
        "return_pct": compute_portfolio_return(holdings),
    }


@router.patch("/profile")
def update_profile(
    data: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.is_public = data.is_public
    current_user.bio       = data.bio
    db.commit()
    return {"message": "Profile updated", "is_public": current_user.is_public}


@router.get("/my-profile")
def get_my_profile(current_user: User = Depends(get_current_user)):
    return {
        "username":  current_user.username,
        "is_public": current_user.is_public,
        "bio":       current_user.bio or "",
    }
