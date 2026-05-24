"""
fetcher.py — Centralized data layer for EquityLens.
"""
import yfinance as yf
import pandas as pd

def get_price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df.empty:
            return pd.DataFrame()
        return df
    except Exception as e:
        print(f"[Error] Could not fetch price data for {ticker}: {e}")
        return pd.DataFrame()

def get_financials(ticker: str) -> dict:
    try:
        stock = yf.Ticker(ticker)
        return {
            "income_stmt":   stock.income_stmt,
            "balance_sheet": stock.balance_sheet,
            "cash_flow":     stock.cash_flow,
            "info":          stock.info
        }
    except Exception as e:
        print(f"[Error] Could not fetch financials for {ticker}: {e}")
        return {}

def get_current_price(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        return stock.info["currentPrice"]
    except Exception as e:
        print(f"[Error] Could not fetch current price for {ticker}: {e}")
        return None
