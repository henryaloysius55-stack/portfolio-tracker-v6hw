from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Holding, WatchlistItem, User
from auth import get_current_user
import yfinance as yf
import time

router = APIRouter(prefix="/news", tags=["news"])

_news_cache: dict = {}
CACHE_TTL = 300  # 5 minutes


def fetch_news_for_ticker(ticker: str) -> list:
    now = time.time()
    if ticker in _news_cache:
        data, ts = _news_cache[ticker]
        if now - ts < CACHE_TTL:
            return data

    try:
        stock = yf.Ticker(ticker)
        raw = stock.news or []
        articles = []
        for item in raw[:5]:
            content = item.get("content", {})
            # Handle both old and new yfinance response formats
            title     = content.get("title") or item.get("title", "")
            summary   = content.get("summary") or item.get("summary", "")
            publisher = content.get("provider", {}).get("displayName") or item.get("publisher", "")
            url_data  = content.get("canonicalUrl") or {}
            link      = url_data.get("url") if isinstance(url_data, dict) else item.get("link", "")
            pub_time  = content.get("pubDate") or ""
            thumbnail = ""
            thumb_data = content.get("thumbnail") or item.get("thumbnail") or {}
            resolutions = thumb_data.get("resolutions", []) if isinstance(thumb_data, dict) else []
            if resolutions:
                thumbnail = resolutions[0].get("url", "")

            if title:
                articles.append({
                    "ticker": ticker,
                    "title": title,
                    "summary": summary[:200] + "…" if len(summary) > 200 else summary,
                    "publisher": publisher,
                    "link": link,
                    "published": pub_time[:10] if pub_time else "",
                    "thumbnail": thumbnail,
                })
        _news_cache[ticker] = (articles, now)
        return articles
    except Exception:
        return []


@router.get("/")
def get_news(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Get tickers from holdings + watchlist
    holdings  = db.query(Holding).filter(Holding.user_id == current_user.id).all()
    watchlist = db.query(WatchlistItem).filter(WatchlistItem.user_id == current_user.id).all()

    tickers = list({h.ticker for h in holdings} | {w.ticker for w in watchlist})

    # Always include market-wide news
    market_tickers = ["SPY", "QQQ", "DIA"]
    all_tickers = (tickers + market_tickers)[:12]  # cap at 12 to avoid rate limits

    all_news = []
    for ticker in all_tickers:
        all_news.extend(fetch_news_for_ticker(ticker))

    # Deduplicate by title and sort by published date
    seen = set()
    unique = []
    for article in all_news:
        if article["title"] not in seen:
            seen.add(article["title"])
            unique.append(article)

    unique.sort(key=lambda x: x.get("published", ""), reverse=True)
    return unique[:40]


@router.get("/market")
def get_market_news():
    """General market news — no auth required."""
    all_news = []
    for ticker in ["SPY", "QQQ", "BTC-USD"]:
        all_news.extend(fetch_news_for_ticker(ticker))
    seen = set()
    unique = [a for a in all_news if not (a["title"] in seen or seen.add(a["title"]))]
    return unique[:20]
