import yfinance as yf
from functools import lru_cache
import time

# Simple in-memory cache: {ticker: (price, timestamp)}
_price_cache: dict = {}
CACHE_TTL = 60  # seconds

def get_current_price(ticker: str) -> float:
    """Fetch the latest closing price for a ticker, with short-term caching."""
    now = time.time()
    if ticker in _price_cache:
        price, ts = _price_cache[ticker]
        if now - ts < CACHE_TTL:
            return price

    stock = yf.Ticker(ticker)
    data = stock.history(period="1d")
    if data.empty:
        raise ValueError(f"Ticker '{ticker}' not found or no data available.")
    price = round(float(data["Close"].iloc[-1]), 2)
    _price_cache[ticker] = (price, now)
    return price

def get_ticker_info(ticker: str) -> dict:
    """Return basic info about a ticker for validation."""
    stock = yf.Ticker(ticker)
    info = stock.info
    return {
        "ticker": ticker.upper(),
        "name": info.get("longName") or info.get("shortName", ticker.upper()),
        "currency": info.get("currency", "USD"),
        "exchange": info.get("exchange", ""),
    }
