from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Holding, User
from schemas import HoldingCreate, HoldingUpdate, HoldingOut
from routes.prices import get_current_price, get_ticker_info
from auth import get_current_user
from typing import List

router = APIRouter(prefix="/holdings", tags=["holdings"])


def enrich_holding(h: Holding) -> dict:
    try:
        current_price = get_current_price(h.ticker)
    except Exception:
        current_price = 0.0

    cost_basis    = round(h.purchase_price * h.shares, 2)
    current_value = round(current_price * h.shares, 2)
    gain_loss     = round(current_value - cost_basis, 2)
    gain_loss_pct = round((gain_loss / cost_basis) * 100, 2) if cost_basis else 0.0

    return {
        "id": h.id,
        "ticker": h.ticker,
        "shares": h.shares,
        "purchase_price": h.purchase_price,
        "purchase_date": h.purchase_date,
        "notes": h.notes,
        "current_price": current_price,
        "current_value": current_value,
        "cost_basis": cost_basis,
        "gain_loss": gain_loss,
        "gain_loss_pct": gain_loss_pct,
    }


@router.get("/", response_model=List[HoldingOut])
def get_all_holdings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    holdings = db.query(Holding).filter(Holding.user_id == current_user.id).all()
    return [enrich_holding(h) for h in holdings]


@router.get("/validate/{ticker}")
def validate_ticker(ticker: str, current_user: User = Depends(get_current_user)):
    try:
        info = get_ticker_info(ticker.upper())
        return {"valid": True, **info}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{holding_id}", response_model=HoldingOut)
def get_holding(
    holding_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    h = db.query(Holding).filter(
        Holding.id == holding_id, Holding.user_id == current_user.id
    ).first()
    if not h:
        raise HTTPException(status_code=404, detail="Holding not found")
    return enrich_holding(h)


@router.post("/", response_model=HoldingOut, status_code=201)
def add_holding(
    data: HoldingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticker = data.ticker.upper().strip()
    try:
        get_current_price(ticker)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid ticker: {ticker}")

    holding = Holding(
        user_id=current_user.id,
        ticker=ticker,
        shares=data.shares,
        purchase_price=data.purchase_price,
        purchase_date=data.purchase_date,
        notes=data.notes,
    )
    db.add(holding)
    db.commit()
    db.refresh(holding)
    return enrich_holding(holding)


@router.patch("/{holding_id}", response_model=HoldingOut)
def update_holding(
    holding_id: int,
    data: HoldingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    h = db.query(Holding).filter(
        Holding.id == holding_id, Holding.user_id == current_user.id
    ).first()
    if not h:
        raise HTTPException(status_code=404, detail="Holding not found")
    for field, value in data.dict(exclude_unset=True).items():
        setattr(h, field, value)
    db.commit()
    db.refresh(h)
    return enrich_holding(h)


@router.delete("/{holding_id}")
def delete_holding(
    holding_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    h = db.query(Holding).filter(
        Holding.id == holding_id, Holding.user_id == current_user.id
    ).first()
    if not h:
        raise HTTPException(status_code=404, detail="Holding not found")
    db.delete(h)
    db.commit()
    return {"message": f"Holding {holding_id} deleted"}
