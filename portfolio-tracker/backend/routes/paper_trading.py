from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from database import get_db
from models import PaperPortfolio, PaperTrade, User
from auth import get_current_user
from routes.prices import get_current_price
from pydantic import BaseModel
from typing import Optional, List
from collections import defaultdict

router = APIRouter(prefix="/paper-trading", tags=["paper-trading"])

STARTING_CASH = 100_000.0


class PaperTradeCreate(BaseModel):
    ticker: str
    type: str   # "buy" or "sell"
    shares: float
    notes: Optional[str] = None


class PortfolioCreate(BaseModel):
    name: str = "My Paper Portfolio"


# ── Helpers ─────────────────────────────────────
def get_or_create_portfolio(user_id: int, db: Session) -> PaperPortfolio:
    port = db.query(PaperPortfolio).filter(PaperPortfolio.user_id == user_id).first()
    if not port:
        port = PaperPortfolio(user_id=user_id, name="My Paper Portfolio", cash_balance=STARTING_CASH)
        db.add(port)
        db.commit()
        db.refresh(port)
    return port


def compute_paper_holdings(trades: list) -> dict:
    """Aggregate trades into current positions."""
    positions = defaultdict(lambda: {"shares": 0.0, "cost_basis": 0.0, "trades": 0})
    for t in trades:
        if t.type == "buy":
            positions[t.ticker]["shares"]     += t.shares
            positions[t.ticker]["cost_basis"] += t.total_value
            positions[t.ticker]["trades"]     += 1
        elif t.type == "sell":
            positions[t.ticker]["shares"]     -= t.shares
            positions[t.ticker]["cost_basis"] -= (t.price_per_share * t.shares)
            positions[t.ticker]["trades"]     += 1
    return {k: v for k, v in positions.items() if v["shares"] > 0.001}


# ── Routes ───────────────────────────────────────
@router.get("/portfolio")
def get_paper_portfolio(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    port = get_or_create_portfolio(current_user.id, db)
    trades = db.query(PaperTrade).filter(PaperTrade.portfolio_id == port.id).all()
    positions = compute_paper_holdings(trades)

    enriched = []
    total_market_value = 0.0
    total_cost = 0.0

    for ticker, pos in positions.items():
        try:
            price = get_current_price(ticker)
        except Exception:
            price = pos["cost_basis"] / pos["shares"] if pos["shares"] else 0

        shares = pos["shares"]
        cost   = pos["cost_basis"]
        mkt    = price * shares
        gl     = mkt - cost
        pct    = (gl / cost * 100) if cost else 0

        total_market_value += mkt
        total_cost += cost

        enriched.append({
            "ticker":        ticker,
            "shares":        round(shares, 4),
            "avg_cost":      round(cost / shares, 2) if shares else 0,
            "current_price": price,
            "market_value":  round(mkt, 2),
            "gain_loss":     round(gl, 2),
            "gain_loss_pct": round(pct, 2),
        })

    enriched.sort(key=lambda x: x["market_value"], reverse=True)

    total_equity = total_market_value + port.cash_balance
    total_gl = total_market_value - total_cost
    total_gl_pct = (total_gl / total_cost * 100) if total_cost else 0

    return {
        "portfolio_id":       port.id,
        "portfolio_name":     port.name,
        "cash_balance":       round(port.cash_balance, 2),
        "total_market_value": round(total_market_value, 2),
        "total_equity":       round(total_equity, 2),
        "total_cost":         round(total_cost, 2),
        "total_gain_loss":    round(total_gl, 2),
        "total_gain_loss_pct":round(total_gl_pct, 2),
        "starting_cash":      STARTING_CASH,
        "positions":          enriched,
    }


@router.post("/trade")
def execute_paper_trade(
    data: PaperTradeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    port = get_or_create_portfolio(current_user.id, db)
    ticker = data.ticker.upper().strip()

    try:
        price = get_current_price(ticker)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Could not fetch price for {ticker}")

    total = round(price * data.shares, 2)

    if data.type == "buy":
        if total > port.cash_balance:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient funds. Need ${total:,.2f} but only have ${port.cash_balance:,.2f} cash."
            )
        port.cash_balance = round(port.cash_balance - total, 2)

    elif data.type == "sell":
        # Check we have enough shares
        trades = db.query(PaperTrade).filter(PaperTrade.portfolio_id == port.id).all()
        positions = compute_paper_holdings(trades)
        current_shares = positions.get(ticker, {}).get("shares", 0)
        if data.shares > current_shares:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient shares. You have {current_shares:.4f} {ticker} but tried to sell {data.shares}."
            )
        port.cash_balance = round(port.cash_balance + total, 2)
    else:
        raise HTTPException(status_code=400, detail="Type must be 'buy' or 'sell'")

    trade = PaperTrade(
        portfolio_id=port.id,
        user_id=current_user.id,
        ticker=ticker,
        type=data.type,
        shares=data.shares,
        price_per_share=price,
        total_value=total,
        notes=data.notes,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)

    return {
        "message":   f"Paper {data.type} executed: {data.shares} {ticker} @ ${price:.2f}",
        "ticker":    ticker,
        "shares":    data.shares,
        "price":     price,
        "total":     total,
        "cash_left": port.cash_balance,
    }


@router.get("/trades")
def get_paper_trades(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    port = get_or_create_portfolio(current_user.id, db)
    trades = db.query(PaperTrade).filter(
        PaperTrade.portfolio_id == port.id
    ).order_by(PaperTrade.created_at.desc()).all()

    return [{
        "id":            t.id,
        "ticker":        t.ticker,
        "type":          t.type,
        "shares":        t.shares,
        "price_per_share": t.price_per_share,
        "total_value":   t.total_value,
        "notes":         t.notes,
        "date":          str(t.created_at)[:10] if t.created_at else "",
        "time":          str(t.created_at)[11:16] if t.created_at else "",
    } for t in trades]


@router.post("/reset")
def reset_paper_portfolio(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    port = get_or_create_portfolio(current_user.id, db)
    db.query(PaperTrade).filter(PaperTrade.portfolio_id == port.id).delete()
    port.cash_balance = STARTING_CASH
    db.commit()
    return {"message": "Paper portfolio reset to $100,000 cash"}
