from pydantic import BaseModel, EmailStr
from typing import Optional, Literal

# ── Auth ────────────────────────────────────────
class UserRegister(BaseModel):
    email: str
    username: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    id: int
    email: str
    username: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut

# ── Holdings ────────────────────────────────────
class HoldingCreate(BaseModel):
    ticker: str
    shares: float
    purchase_price: float
    purchase_date: Optional[str] = None
    notes: Optional[str] = None

class HoldingUpdate(BaseModel):
    shares: Optional[float] = None
    purchase_price: Optional[float] = None
    purchase_date: Optional[str] = None
    notes: Optional[str] = None

class HoldingOut(BaseModel):
    id: int
    ticker: str
    shares: float
    purchase_price: float
    purchase_date: Optional[str]
    notes: Optional[str]
    current_price: float
    current_value: float
    cost_basis: float
    gain_loss: float
    gain_loss_pct: float

    class Config:
        from_attributes = True

# ── Transactions ────────────────────────────────
class TransactionCreate(BaseModel):
    ticker: str
    type: Literal["buy", "sell"]
    shares: float
    price_per_share: float
    date: Optional[str] = None
    notes: Optional[str] = None

class TransactionOut(BaseModel):
    id: int
    ticker: str
    type: str
    shares: float
    price_per_share: float
    total_value: float
    date: Optional[str]
    notes: Optional[str]

    class Config:
        from_attributes = True
