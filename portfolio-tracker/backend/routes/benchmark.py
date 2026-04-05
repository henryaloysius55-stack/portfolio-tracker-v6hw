from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Holding, User
from routes.prices import get_current_price
from auth import get_current_user
import yfinance as yf
import time

router = APIRouter(prefix="/benchmark", tags=["benchmark"])

_bench_cache: dict = {}
CACHE_TTL = 300


def get_spy_return() -> dict:
    now = time.time()
    if "spy" in _bench_cache:
        data, ts = _bench_cache["spy"]
        if now - ts < CACHE_TTL:
            return data

    spy = yf.Ticker("SPY")
    hist = spy.history(period="1y")
    if hist.empty:
        raise ValueError("Could not fetch SPY data")

    start_price = float(hist["Close"].iloc[0])
    end_price   = float(hist["Close"].iloc[-1])
    spy_return  = round(((end_price - start_price) / start_price) * 100, 2)

    result = {
        "ticker": "SPY",
        "name": "S&P 500 (SPY)",
        "start_price": round(start_price, 2),
        "current_price": round(end_price, 2),
        "return_pct": spy_return,
        "period": "1 Year",
    }
    _bench_cache["spy"] = (result, now)
    return result


@router.get("/")
def get_benchmark(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    holdings = db.query(Holding).filter(Holding.user_id == current_user.id).all()
    if not holdings:
        raise HTTPException(status_code=400, detail="No holdings to benchmark")

    total_cost = total_value = 0.0
    per_holding = []

    for h in holdings:
        try:
            price = get_current_price(h.ticker)
        except Exception:
            price = h.purchase_price

        cost  = h.purchase_price * h.shares
        value = price * h.shares
        total_cost  += cost
        total_value += value
        per_holding.append({
            "ticker": h.ticker,
            "return_pct": round(((value - cost) / cost) * 100, 2) if cost else 0,
            "weight": 0,
        })

    portfolio_return = round(((total_value - total_cost) / total_cost) * 100, 2) if total_cost else 0

    for item in per_holding:
        h = next(x for x in holdings if x.ticker == item["ticker"])
        try:
            price = get_current_price(h.ticker)
        except Exception:
            price = h.purchase_price
        item["weight"] = round((price * h.shares / total_value) * 100, 1) if total_value else 0

    try:
        spy = get_spy_return()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch benchmark: {e}")

    return {
        "portfolio": {
            "return_pct": portfolio_return,
            "total_cost": round(total_cost, 2),
            "total_value": round(total_value, 2),
        },
        "benchmark": spy,
        "outperformance": round(portfolio_return - spy["return_pct"], 2),
        "per_holding": per_holding,
    }
