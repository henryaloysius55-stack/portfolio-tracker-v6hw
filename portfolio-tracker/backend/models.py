from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"
    id              = Column(Integer, primary_key=True, index=True)
    email           = Column(String, unique=True, nullable=False, index=True)
    username        = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    is_active       = Column(Boolean, default=True)
    is_public       = Column(Boolean, default=False)
    bio             = Column(String, nullable=True)
    # Strategy profile
    strategy        = Column(String, nullable=True)       # growth, value, dividend, etc.
    time_horizon    = Column(String, nullable=True)       # short, medium, long
    risk_tolerance  = Column(String, nullable=True)       # low, medium, high, aggressive
    strategy_notes  = Column(Text, nullable=True)         # user's own strategy description
    created_at      = Column(DateTime, server_default=func.now())

class Holding(Base):
    __tablename__ = "holdings"
    id             = Column(Integer, primary_key=True, index=True)
    user_id        = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ticker         = Column(String, nullable=False)
    shares         = Column(Float, nullable=False)
    purchase_price = Column(Float, nullable=False)
    purchase_date  = Column(String, nullable=True)
    notes          = Column(String, nullable=True)

class Transaction(Base):
    __tablename__ = "transactions"
    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ticker          = Column(String, nullable=False, index=True)
    type            = Column(String, nullable=False)
    shares          = Column(Float, nullable=False)
    price_per_share = Column(Float, nullable=False)
    total_value     = Column(Float, nullable=False)
    date            = Column(String, nullable=True)
    notes           = Column(String, nullable=True)
    # Extended trading log fields
    strategy_tag    = Column(String, nullable=True)   # why this trade
    emotion_tag     = Column(String, nullable=True)   # FOMO, conviction, research, etc.
    created_at      = Column(DateTime, server_default=func.now())

class WatchlistItem(Base):
    __tablename__ = "watchlist"
    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ticker       = Column(String, nullable=False)
    target_price = Column(Float, nullable=True)
    notes        = Column(String, nullable=True)
    added_at     = Column(DateTime, server_default=func.now())

class PaperPortfolio(Base):
    __tablename__ = "paper_portfolios"
    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name         = Column(String, nullable=False, default="My Paper Portfolio")
    cash_balance = Column(Float, nullable=False, default=100000.0)  # starts with $100k
    created_at   = Column(DateTime, server_default=func.now())

class PaperTrade(Base):
    __tablename__ = "paper_trades"
    id              = Column(Integer, primary_key=True, index=True)
    portfolio_id    = Column(Integer, ForeignKey("paper_portfolios.id"), nullable=False, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ticker          = Column(String, nullable=False)
    type            = Column(String, nullable=False)   # buy or sell
    shares          = Column(Float, nullable=False)
    price_per_share = Column(Float, nullable=False)
    total_value     = Column(Float, nullable=False)
    date            = Column(String, nullable=True)
    notes           = Column(String, nullable=True)
    created_at      = Column(DateTime, server_default=func.now())

