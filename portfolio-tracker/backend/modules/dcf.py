import numpy as np
from data.fetcher import get_financials, get_current_price

def calculate_dcf(free_cash_flow, growth_rate, discount_rate,
                  terminal_growth, projection_years=10, shares_outstanding=1.0):
    pv_cash_flows = 0
    for year in range(1, projection_years + 1):
        projected = free_cash_flow * (1 + growth_rate) ** year
        pv_cash_flows += projected / (1 + discount_rate) ** year

    final_fcf      = free_cash_flow * (1 + growth_rate) ** projection_years
    terminal_value = final_fcf * (1 + terminal_growth) / (discount_rate - terminal_growth)
    pv_terminal    = terminal_value / (1 + discount_rate) ** projection_years
    total          = pv_cash_flows + pv_terminal
    intrinsic      = total / shares_outstanding

    return {
        "pv_cash_flows": round(pv_cash_flows / 1e9, 2),
        "pv_terminal_value": round(pv_terminal / 1e9, 2),
        "intrinsic_value": round(intrinsic, 2)
    }

def run_dcf_analysis(ticker: str) -> dict:
    print(f"Running DCF analysis for {ticker}...")
    financials    = get_financials(ticker)
    current_price = get_current_price(ticker)
    if not financials:
        return {"ticker": ticker, "error": "No data available"}

    cashflow = financials.get("cashflow", [])
    profile  = financials.get("profile", {})
    shares   = profile.get("sharesOutstanding", 1)

    try:
        op_cf = cashflow[0].get("operatingCashFlow", 0)
        capex = cashflow[0].get("capitalExpenditure", 0)
        fcf   = op_cf - abs(capex)
        if fcf < 0:
            return {"ticker": ticker, "error": "Negative FCF — DCF not applicable"}
    except:
        return {"ticker": ticker, "error": "FCF extraction failed"}

    scenarios = {
        "bear": {"growth_rate": 0.04, "discount_rate": 0.11, "terminal_growth": 0.02},
        "base": {"growth_rate": 0.07, "discount_rate": 0.09, "terminal_growth": 0.025},
        "bull": {"growth_rate": 0.12, "discount_rate": 0.08, "terminal_growth": 0.03},
    }

    results = {"ticker": ticker, "current_price": current_price}
    for scenario, assumptions in scenarios.items():
        dcf = calculate_dcf(fcf, shares_outstanding=shares, **assumptions)
        iv  = dcf["intrinsic_value"]
        mos = round((iv - current_price) / current_price * 100, 1) if current_price and iv else None
        results[scenario] = {"intrinsic_value": iv, "margin_of_safety": mos,
                             "pv_cash_flows": dcf["pv_cash_flows"],
                             "pv_terminal_value": dcf["pv_terminal_value"]}
    return results

def run_monte_carlo(ticker: str, n_simulations: int = 10000) -> dict:
    print(f"Running Monte Carlo simulation for {ticker} ({n_simulations:,} simulations)...")
    financials    = get_financials(ticker)
    current_price = get_current_price(ticker)
    if not financials:
        return {"ticker": ticker, "error": "No data available"}

    cashflow = financials.get("cashflow", [])
    profile  = financials.get("profile", {})
    shares   = profile.get("sharesOutstanding", 1)

    try:
        op_cf = cashflow[0].get("operatingCashFlow", 0)
        capex = cashflow[0].get("capitalExpenditure", 0)
        fcf   = op_cf - abs(capex)
        if fcf < 0:
            return {"ticker": ticker, "error": "Negative FCF — DCF not applicable"}
    except:
        return {"ticker": ticker, "error": "FCF extraction failed"}

    np.random.seed(42)
    growth_rates   = np.random.lognormal(np.log(1.07), 0.04, n_simulations) - 1
    wacc_rates     = np.clip(np.random.normal(0.09, 0.015, n_simulations), 0.05, 0.20)
    terminal_rates = np.clip(np.random.normal(0.025, 0.005, n_simulations), 0.01, 0.04)
    wacc_rates     = np.maximum(wacc_rates, terminal_rates + 0.02)

    pv_cf = np.zeros(n_simulations)
    for year in range(1, 11):
        pv_cf += fcf * (1 + growth_rates) ** year / (1 + wacc_rates) ** year

    final_fcf  = fcf * (1 + growth_rates) ** 10
    tv         = final_fcf * (1 + terminal_rates) / (wacc_rates - terminal_rates)
    pv_tv      = tv / (1 + wacc_rates) ** 10
    iv_vals    = (pv_cf + pv_tv) / shares

    return {
        "ticker": ticker, "current_price": current_price,
        "n_simulations": n_simulations,
        "p10": round(float(np.percentile(iv_vals, 10)), 2),
        "p25": round(float(np.percentile(iv_vals, 25)), 2),
        "p50": round(float(np.percentile(iv_vals, 50)), 2),
        "p75": round(float(np.percentile(iv_vals, 75)), 2),
        "p90": round(float(np.percentile(iv_vals, 90)), 2),
        "std": round(float(np.std(iv_vals)), 2),
        "prob_undervalued": round(float(np.mean(iv_vals > current_price) * 100), 1),
        "intrinsic_values": iv_vals.tolist()
    }
