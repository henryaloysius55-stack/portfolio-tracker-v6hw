from data.fetcher import get_financials, get_current_price
from data.fetcher import get_price_history
import numpy as np

def get_beta(ticker: str):
    try:
        import pandas as pd
        stock_df = get_price_history(ticker)
        spy_df   = get_price_history("SPY")
        if stock_df.empty or spy_df.empty:
            return None
        sr = stock_df["Close"].pct_change().dropna()
        mr = spy_df["Close"].pct_change().dropna()
        common = sr.index.intersection(mr.index)
        sr, mr = sr[common], mr[common]
        cov = np.cov(sr, mr)[0][1]
        var = np.var(mr)
        return round(cov / var, 2)
    except Exception as e:
        print(f"[Error] Beta failed: {e}")
        return None

def calculate_analyst_rating(gross_margin, revenue_cagr, fundamental_score,
                              rsi, ma_signal, base_mos, prob_undervalued,
                              recommendation, beta, current_ratio):
    score = 0
    breakdown = {}

    val = 0
    if base_mos and base_mos > 0: val += 1
    if prob_undervalued and prob_undervalued > 50: val += 1
    if recommendation in ["BUY", "STRONG_BUY", "STRONG BUY"]: val += 1
    breakdown["valuation"] = val
    score += val

    qual = 0
    if gross_margin and gross_margin > 40: qual += 1
    if revenue_cagr and revenue_cagr > 10: qual += 1
    if fundamental_score and fundamental_score >= 4: qual += 1
    breakdown["quality"] = qual
    score += qual

    mom = 0
    if ma_signal == "golden_cross": mom += 1
    if rsi and 30 <= rsi <= 70: mom += 1
    breakdown["momentum"] = mom
    score += mom

    risk = 0
    if beta and beta < 1.5: risk += 1
    if current_ratio and current_ratio > 1.0: risk += 1
    breakdown["risk"] = risk
    score += risk

    label = "STRONG BUY" if score >= 8 else "BUY" if score >= 6 else "HOLD" if score >= 4 else "SELL" if score >= 2 else "STRONG SELL"
    return {"score": score, "label": label, "breakdown": breakdown}

def analyze_ticker(ticker: str) -> dict:
    print(f"Analyzing fundamentals for {ticker}...")
    financials = get_financials(ticker)
    if not financials:
        return {"ticker": ticker, "error": "No data available"}

    profile = financials.get("profile", {})
    ratios  = financials.get("ratios", {})
    income  = financials.get("income", [])

    price        = profile.get("price")
    pe           = round(ratios.get("peRatioTTM", None) or 0, 2) or None
    ev_ebitda    = round(ratios.get("enterpriseValueMultipleTTM", None) or 0, 2) or None
    debt_equity  = round(ratios.get("debtEquityRatioTTM", None) or 0, 2) or None
    current      = round(ratios.get("currentRatioTTM", None) or 0, 2) or None
    gross_margin = round((ratios.get("grossProfitMarginTTM") or 0) * 100, 2) or None

    cagr = None
    if len(income) >= 2:
        try:
            rev_new = income[0].get("revenue", 0)
            rev_old = income[-1].get("revenue", 0)
            years   = len(income) - 1
            cagr    = round(((rev_new / rev_old) ** (1 / years) - 1) * 100, 2)
        except:
            pass

    beta = get_beta(ticker)

    fs = 3
    if gross_margin and gross_margin > 40: fs += 1
    if cagr and cagr > 10: fs += 1
    if debt_equity and debt_equity > 100: fs -= 1
    if current and current < 1.0: fs -= 1
    fs = max(1, min(5, fs))

    return {
        "ticker": ticker, "price": price, "pe_ratio": pe,
        "ev_ebitda": ev_ebitda, "debt_equity": debt_equity,
        "current_ratio": current, "gross_margin": gross_margin,
        "revenue_cagr": cagr, "beta": beta, "fundamental_score": fs
    }
