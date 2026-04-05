from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User
from auth import get_current_user
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/strategies", tags=["strategies"])

STRATEGY_PROFILES = {
    "growth": {
        "name": "Growth Investing",
        "description": "Focus on companies with high revenue/earnings growth potential. Willing to pay premium valuations for future returns.",
        "key_metrics": ["Revenue Growth", "EPS Growth", "TAM", "P/E Ratio"],
        "famous_practitioners": ["Cathie Wood", "Philip Fisher", "Peter Lynch"],
        "typical_horizon": "3–10 years",
        "risk": "High",
        "example_tickers": ["NVDA", "TSLA", "SHOP", "CRWD"],
        "color": "var(--green)",
    },
    "value": {
        "name": "Value Investing",
        "description": "Buy stocks trading below intrinsic value. Focus on margin of safety, strong fundamentals, and patient long-term holding.",
        "key_metrics": ["P/E Ratio", "P/B Ratio", "Free Cash Flow", "Debt/Equity"],
        "famous_practitioners": ["Warren Buffett", "Charlie Munger", "Benjamin Graham", "Seth Klarman"],
        "typical_horizon": "5–20 years",
        "risk": "Low–Medium",
        "example_tickers": ["BRK.B", "JPM", "BAC", "KO"],
        "color": "var(--accent)",
    },
    "dividend": {
        "name": "Dividend / Income Investing",
        "description": "Build a portfolio of dividend-paying stocks for passive income. Focus on dividend yield, payout ratio, and dividend growth.",
        "key_metrics": ["Dividend Yield", "Payout Ratio", "Dividend Growth Rate", "Coverage Ratio"],
        "famous_practitioners": ["John D. Rockefeller", "John Neff"],
        "typical_horizon": "10+ years",
        "risk": "Low",
        "example_tickers": ["JNJ", "PG", "KO", "REALTY"],
        "color": "var(--blue)",
    },
    "momentum": {
        "name": "Momentum Investing",
        "description": "Buy stocks showing strong recent price performance, sell underperformers. Based on trend-following and relative strength.",
        "key_metrics": ["Relative Strength", "52-Week High", "Volume", "RSI"],
        "famous_practitioners": ["Richard Driehaus", "Jesse Livermore"],
        "typical_horizon": "1 month – 1 year",
        "risk": "High",
        "example_tickers": ["NVDA", "META", "AMZN"],
        "color": "var(--purple)",
    },
    "index": {
        "name": "Index / Passive Investing",
        "description": "Match the market rather than beat it. Buy broad index funds and hold long-term. Low cost, diversified, historically reliable.",
        "key_metrics": ["Expense Ratio", "Tracking Error", "Diversification"],
        "famous_practitioners": ["Jack Bogle", "Burton Malkiel"],
        "typical_horizon": "10–30 years",
        "risk": "Low–Medium",
        "example_tickers": ["SPY", "QQQ", "VTI", "VOO"],
        "color": "var(--text-2)",
    },
    "contrarian": {
        "name": "Contrarian Investing",
        "description": "Go against prevailing market sentiment. Buy when others are fearful, sell when others are greedy. Requires conviction and patience.",
        "key_metrics": ["Sentiment Indicators", "Short Interest", "P/E vs History", "52-Week Low"],
        "famous_practitioners": ["Michael Burry", "George Soros", "David Dreman"],
        "typical_horizon": "1–5 years",
        "risk": "High",
        "example_tickers": ["Varies — beaten down sectors"],
        "color": "var(--red)",
    },
}


class StrategyUpdate(BaseModel):
    strategy: Optional[str] = None
    time_horizon: Optional[str] = None
    risk_tolerance: Optional[str] = None
    strategy_notes: Optional[str] = None
    is_public: Optional[bool] = None


@router.get("/")
def get_all_strategies():
    """Return all investment strategy profiles."""
    return list(STRATEGY_PROFILES.values())


@router.get("/my-profile")
def get_my_strategy(current_user: User = Depends(get_current_user)):
    return {
        "strategy":       current_user.strategy,
        "time_horizon":   current_user.time_horizon,
        "risk_tolerance": current_user.risk_tolerance,
        "strategy_notes": current_user.strategy_notes,
        "is_public":      current_user.is_public,
        "profile":        STRATEGY_PROFILES.get(current_user.strategy or "", None),
    }


@router.patch("/my-profile")
def update_my_strategy(
    data: StrategyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.strategy is not None:      current_user.strategy = data.strategy
    if data.time_horizon is not None:  current_user.time_horizon = data.time_horizon
    if data.risk_tolerance is not None: current_user.risk_tolerance = data.risk_tolerance
    if data.strategy_notes is not None: current_user.strategy_notes = data.strategy_notes
    if data.is_public is not None:     current_user.is_public = data.is_public
    db.commit()
    return {"message": "Strategy profile updated"}


@router.get("/community")
def get_community_strategies(db: Session = Depends(get_db)):
    """Public users who have shared their strategy."""
    users = db.query(User).filter(
        User.is_public == True,
        User.is_active == True,
        User.strategy != None,
    ).all()
    return [{
        "username":       u.username,
        "strategy":       u.strategy,
        "time_horizon":   u.time_horizon,
        "risk_tolerance": u.risk_tolerance,
        "strategy_notes": u.strategy_notes,
        "strategy_name":  STRATEGY_PROFILES.get(u.strategy or "", {}).get("name", u.strategy),
    } for u in users]
