"""
fundamentals.py — Fundamental analysis engine for EquityLens.

Calculates key financial ratios and metrics for a given ticker:
- P/E Ratio
- EV/EBITDA
- Debt to Equity
- Current Ratio
- Gross Margin
- 3-Year Revenue CAGR
"""

import pandas as pd
import numpy as np
from data.fetcher import get_financials, get_current_price


def get_pe_ratio(info: dict) -> float:
    """
    Fetch the trailing P/E ratio from stock info.

    Args:
        info: Dictionary from yfinance stock.info

    Returns:
        P/E ratio as a float, or None if unavailable.
    """
    try:
        pe = info.get("trailingPE")
        if pe is None:
            return None
        return round(pe, 2)
    except Exception as e:
        print(f"[Error] P/E calculation failed: {e}")
        return None


def get_ev_ebitda(info: dict) -> float:
    """
    Fetch the EV/EBITDA ratio from stock info.

    Args:
        info: Dictionary from yfinance stock.info

    Returns:
        EV/EBITDA as a float, or None if unavailable.
    """
    try:
        ev_ebitda = info.get("enterpriseToEbitda")
        if ev_ebitda is None:
            return None
        return round(ev_ebitda, 2)
    except Exception as e:
        print(f"[Error] EV/EBITDA calculation failed: {e}")
        return None


def get_debt_to_equity(info: dict) -> float:
    """
    Fetch the debt to equity ratio from stock info.

    Args:
        info: Dictionary from yfinance stock.info

    Returns:
        Debt to equity ratio as a float, or None if unavailable.
    """
    try:
        de = info.get("debtToEquity")
        if de is None:
            return None
        return round(de, 2)
    except Exception as e:
        print(f"[Error] Debt to equity calculation failed: {e}")
        return None


def get_current_ratio(info: dict) -> float:
    """
    Fetch the current ratio from stock info.

    Args:
        info: Dictionary from yfinance stock.info

    Returns:
        Current ratio as a float, or None if unavailable.
    """
    try:
        cr = info.get("currentRatio")
        if cr is None:
            return None
        return round(cr, 2)
    except Exception as e:
        print(f"[Error] Current ratio calculation failed: {e}")
        return None


def get_gross_margin(info: dict) -> float:
    """
    Fetch gross margin as a percentage from stock info.

    Args:
        info: Dictionary from yfinance stock.info

    Returns:
        Gross margin as a percentage float, or None if unavailable.
    """
    try:
        gm = info.get("grossMargins")
        if gm is None:
            return None
        return round(gm * 100, 2)
    except Exception as e:
        print(f"[Error] Gross margin calculation failed: {e}")
        return None


def get_revenue_cagr(income_stmt: pd.DataFrame) -> float:
    """
    Calculate 3-year revenue CAGR from the income statement.

    CAGR formula: (Ending Value / Beginning Value) ^ (1 / years) - 1

    Args:
        income_stmt: Income statement DataFrame from yfinance

    Returns:
        3-year CAGR as a percentage float, or None if unavailable.
    """
    try:
        # yfinance returns columns in reverse chronological order
        # so we reverse them to get oldest to newest
        revenue_row = income_stmt.loc["Total Revenue"]
        revenue = revenue_row.iloc[::-1]

        if len(revenue) < 2:
            return None

        # Use as many years as we have, up to 3
        years = min(len(revenue) - 1, 3)
        ending = revenue.iloc[-1]
        beginning = revenue.iloc[-1 - years]

        cagr = (ending / beginning) ** (1 / years) - 1
        return round(cagr * 100, 2)

    except Exception as e:
        print(f"[Error] CAGR calculation failed: {e}")
        return None
def get_beta(ticker: str) -> float:
    """
    Calculate beta of a stock vs the S&P 500 (SPY) over 1 year.

    Beta measures systematic risk — how much the stock moves
    relative to the overall market.

    Beta > 1: more volatile than market
    Beta < 1: less volatile than market  
    Beta < 0: moves opposite to market

    Formula: Beta = Covariance(stock, market) / Variance(market)

    Args:
        ticker: Stock symbol as a string e.g. "AAPL"

    Returns:
        Beta as a float, or None if calculation fails.
    """
    try:
        import yfinance as yf
        import numpy as np

        # Fetch 1 year of closing prices for stock and S&P 500
        stock_data = yf.Ticker(ticker).history(period="1y")["Close"]
        spy_data   = yf.Ticker("SPY").history(period="1y")["Close"]

        # Convert prices to daily percentage returns
        # pct_change() calculates: (today - yesterday) / yesterday
        stock_returns = stock_data.pct_change().dropna()
        spy_returns   = spy_data.pct_change().dropna()

        # Align on common trading dates
        common        = stock_returns.index.intersection(spy_returns.index)
        stock_returns = stock_returns[common]
        spy_returns   = spy_returns[common]

        # Beta formula
        covariance = np.cov(stock_returns, spy_returns)[0][1]
        variance   = np.var(spy_returns)
        beta       = covariance / variance

        return round(beta, 2)

    except Exception as e:
        print(f"[Error] Beta calculation failed: {e}")
 
        return None
def calculate_analyst_rating(
    gross_margin: float,
    revenue_cagr: float,
    fundamental_score: int,
    rsi: float,
    ma_signal: str,
    base_mos: float,
    prob_undervalued: float,
    recommendation: str,
    beta: float,
    current_ratio: float
) -> dict:
    """
    Calculate a 0-10 analyst rating combining valuation, quality,
    momentum and risk signals.

    Scoring breakdown:
    - Valuation:        0-3 points
    - Business Quality: 0-3 points
    - Momentum:         0-2 points
    - Risk:             0-2 points

    Args:
        All fundamental and technical metrics as floats/strings.

    Returns:
        Dictionary with score, breakdown, and label.
    """
    score = 0
    breakdown = {}

    # ── Valuation (0-3 points) ─────────────────────────────────────────
    valuation_points = 0

    if base_mos is not None and base_mos > 0:
        valuation_points += 1
    if prob_undervalued is not None and prob_undervalued > 50:
        valuation_points += 1
    if recommendation in ["BUY", "STRONG_BUY", "STRONG BUY"]:
        valuation_points += 1

    breakdown["valuation"] = valuation_points
    score += valuation_points

    # ── Business Quality (0-3 points) ──────────────────────────────────
    quality_points = 0

    if gross_margin is not None and gross_margin > 40:
        quality_points += 1
    if revenue_cagr is not None and revenue_cagr > 10:
        quality_points += 1
    if fundamental_score is not None and fundamental_score >= 4:
        quality_points += 1

    breakdown["quality"] = quality_points
    score += quality_points

    # ── Momentum (0-2 points) ──────────────────────────────────────────
    momentum_points = 0

    if ma_signal == "golden_cross":
        momentum_points += 1
    if rsi is not None and 30 <= rsi <= 70:
        momentum_points += 1

    breakdown["momentum"] = momentum_points
    score += momentum_points

    # ── Risk (0-2 points) ──────────────────────────────────────────────
    risk_points = 0

    if beta is not None and beta < 1.5:
        risk_points += 1
    if current_ratio is not None and current_ratio > 1.0:
        risk_points += 1

    breakdown["risk"] = risk_points
    score += risk_points

    # ── Label ──────────────────────────────────────────────────────────
    if score >= 8:
        label = "STRONG BUY"
    elif score >= 6:
        label = "BUY"
    elif score >= 4:
        label = "HOLD"
    elif score >= 2:
        label = "SELL"
    else:
        label = "STRONG SELL"

    return {
        "score":     score,
        "label":     label,
        "breakdown": breakdown
    }

def analyze_ticker(ticker: str) -> dict:
    """
    Run full fundamental analysis on a single ticker.

    Args:
        ticker: Stock symbol as a string e.g. "AAPL"

    Returns:
        Dictionary containing all fundamental metrics and
        a simple interpretation for each.
    """
    print(f"Analyzing fundamentals for {ticker}...")

    financials = get_financials(ticker)
    if not financials:
        return {"ticker": ticker, "error": "No data available"}

    info         = financials["info"]
    income_stmt  = financials["income_stmt"]

    pe           = get_pe_ratio(info)
    ev_ebitda    = get_ev_ebitda(info)
    debt_equity  = get_debt_to_equity(info)
    current      = get_current_ratio(info)
    gross_margin = get_gross_margin(info)
    cagr         = get_revenue_cagr(income_stmt)
    price        = get_current_price(ticker)
    beta         = get_beta(ticker)
    fundamental_score = 3 
    if gross_margin is not None and gross_margin > 40:
        fundamental_score += 1
    if cagr is not None and cagr> 10:
        fundamental_score += 1
    if debt_equity is not None and debt_equity > 100: 
        fundamental_score -= 1
    if current is not None and current < 1.0:
        fundamental_score -= 1
    score = max(1, min(5, fundamental_score))
    return {
        "ticker":        ticker,
        "price":         price,
        "pe_ratio":      pe,
        "ev_ebitda":     ev_ebitda,
        "debt_equity":   debt_equity,
        "current_ratio": current,
        "gross_margin":  gross_margin,
        "revenue_cagr":  cagr,
        "beta": beta,
        "fundamental_score": score
    }
