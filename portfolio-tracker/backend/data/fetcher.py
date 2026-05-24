import os
import requests

API_KEY = os.environ.get("FMP_API_KEY")
BASE = "https://financialmodelingprep.com/api/v3"

def _get(endpoint, params={}):
    try:
        params["apikey"] = API_KEY
        r = requests.get(f"{BASE}/{endpoint}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[Error] FMP request failed: {e}")
        return None

def get_price_history(ticker: str, period: str = "1y") -> "pd.DataFrame":
    import pandas as pd
    data = _get(f"historical-price-full/{ticker}", {"serietype": "line"})
    if not data or "historical" not in data:
        return pd.DataFrame()
    df = pd.DataFrame(data["historical"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").set_index("date")
    df = df.rename(columns={"close": "Close", "open": "Open",
                             "high": "High", "low": "Low", "volume": "Volume"})
    # Filter to roughly 1 year
    cutoff = pd.Timestamp.now() - pd.DateOffset(years=1)
    return df[df.index >= cutoff]

def get_financials(ticker: str) -> dict:
    profile   = _get(f"profile/{ticker}")
    income    = _get(f"income-statement/{ticker}", {"limit": 4})
    cashflow  = _get(f"cash-flow-statement/{ticker}", {"limit": 4})
    ratios    = _get(f"ratios-ttm/{ticker}")
    if not profile:
        return {}
    return {
        "profile":   profile[0] if profile else {},
        "income":    income or [],
        "cashflow":  cashflow or [],
        "ratios":    ratios[0] if ratios else {},
    }

def get_current_price(ticker: str):
    data = _get(f"quote-short/{ticker}")
    if data and len(data) > 0:
        return data[0].get("price")
    return None
