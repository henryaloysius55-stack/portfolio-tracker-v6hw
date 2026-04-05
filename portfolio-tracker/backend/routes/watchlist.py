from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import WatchlistItem, User
from auth import get_current_user
from routes.prices import get_current_price
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/watchlist", tags=["watchlist"])

class WatchlistCreate(BaseModel):
    ticker: str
    target_price: Optional[float] = None
    notes: Optional[str] = None


@router.get("/")
def get_watchlist(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    items = db.query(WatchlistItem).filter(WatchlistItem.user_id == current_user.id).all()
    result = []
    for item in items:
        try:
            current_price = get_current_price(item.ticker)
        except Exception:
            current_price = None

        distance_pct = None
        if current_price and item.target_price:
            distance_pct = round(((item.target_price - current_price) / current_price) * 100, 2)

        result.append({
            "id": item.id,
            "ticker": item.ticker,
            "target_price": item.target_price,
            "current_price": current_price,
            "distance_pct": distance_pct,
            "notes": item.notes,
            "added_at": str(item.added_at)[:10] if item.added_at else None,
        })
    return result


@router.post("/", status_code=201)
def add_to_watchlist(
    data: WatchlistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticker = data.ticker.upper().strip()
    # Prevent duplicates
    exists = db.query(WatchlistItem).filter(
        WatchlistItem.user_id == current_user.id,
        WatchlistItem.ticker == ticker
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail=f"{ticker} is already in your watchlist")

    item = WatchlistItem(
        user_id=current_user.id,
        ticker=ticker,
        target_price=data.target_price,
        notes=data.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"message": f"{ticker} added to watchlist", "id": item.id}


@router.delete("/{item_id}")
def remove_from_watchlist(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(WatchlistItem).filter(
        WatchlistItem.id == item_id,
        WatchlistItem.user_id == current_user.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    db.delete(item)
    db.commit()
    return {"message": "Removed from watchlist"}
