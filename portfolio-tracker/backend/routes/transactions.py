from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Transaction, User
from schemas import TransactionCreate, TransactionOut
from auth import get_current_user
from typing import List, Optional

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/", response_model=List[TransactionOut])
def get_all_transactions(
    ticker: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Transaction).filter(Transaction.user_id == current_user.id)
    if ticker:
        q = q.filter(Transaction.ticker == ticker.upper())
    return q.order_by(Transaction.date.desc(), Transaction.created_at.desc()).all()


@router.post("/", response_model=TransactionOut, status_code=201)
def add_transaction(
    data: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticker = data.ticker.upper().strip()
    total  = round(data.shares * data.price_per_share, 2)
    txn = Transaction(
        user_id=current_user.id,
        ticker=ticker,
        type=data.type,
        shares=data.shares,
        price_per_share=data.price_per_share,
        total_value=total,
        date=data.date,
        notes=data.notes,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


@router.delete("/{txn_id}")
def delete_transaction(
    txn_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    txn = db.query(Transaction).filter(
        Transaction.id == txn_id, Transaction.user_id == current_user.id
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(txn)
    db.commit()
    return {"message": f"Transaction {txn_id} deleted"}
