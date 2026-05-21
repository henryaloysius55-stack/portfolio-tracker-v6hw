"""
dcf.py — Discounted Cash Flow valuation engine for EquityLens.

Builds a three-scenario DCF model (bull, base, bear) for any ticker.
Outputs intrinsic value per share and margin of safety vs current price.

Key concepts:
- Free Cash Flow: cash the business generates after capital expenditures
- WACC: the discount rate representing investor required return
- Terminal Value: value of all cash flows beyond the projection period
- Margin of Safety: how much cheaper the stock is vs intrinsic value
"""

import numpy as np
import matplotlib.pyplot as plt
from data.fetcher import get_financials, get_current_price


def calculate_dcf(
    free_cash_flow: float,
    growth_rate: float,
    discount_rate: float,
    terminal_growth: float,
    projection_years: int = 10,
    shares_outstanding: float = 1.0
) -> dict:
    """
    Run a single DCF calculation with given assumptions.

    Args:
        free_cash_flow:    Most recent annual free cash flow in dollars
        growth_rate:       Expected annual FCF growth rate as decimal e.g. 0.08
        discount_rate:     WACC as decimal e.g. 0.09
        terminal_growth:   Long term growth rate beyond projection e.g. 0.025
        projection_years:  How many years to project, default 10
        shares_outstanding: Shares outstanding in same units as FCF

    Returns:
        Dictionary with pv_cash_flows, terminal_value, intrinsic_value_per_share
    """
    # Step 1: Project and discount each year's free cash flow
    pv_cash_flows = 0
    for year in range(1, projection_years + 1):
        # Grow the cash flow by growth_rate each year
        projected_fcf = free_cash_flow * (1 + growth_rate) ** year
        # Discount it back to present value
        discounted = projected_fcf / (1 + discount_rate) ** year
        pv_cash_flows += discounted

    # Step 2: Calculate terminal value using Gordon Growth Model
    # Terminal value = final year FCF × (1 + terminal growth) / (WACC - terminal growth)
    final_fcf = free_cash_flow * (1 + growth_rate) ** projection_years
    terminal_value = final_fcf * (1 + terminal_growth) / (discount_rate - terminal_growth)

    # Step 3: Discount terminal value back to present
    pv_terminal = terminal_value / (1 + discount_rate) ** projection_years

    # Step 4: Total intrinsic value = PV of cash flows + PV of terminal value
    total_value = pv_cash_flows + pv_terminal

    # Step 5: Divide by shares to get per share value
    intrinsic_value = total_value / shares_outstanding

    return {
        "pv_cash_flows":          round(pv_cash_flows / 1e9, 2),
        "pv_terminal_value":      round(pv_terminal / 1e9, 2),
        "total_value_billions":   round(total_value / 1e9, 2),
        "intrinsic_value":        round(intrinsic_value, 2)
    }

def run_dcf_analysis(ticker: str) -> dict:
    """
    Run a three-scenario DCF analysis for a given ticker.

    Args:
        ticker: Stock symbol as a string e.g. "AAPL"

    Returns:
        Dictionary with bull, base, bear scenarios and margin of safety.
    """
    print(f"Running DCF analysis for {ticker}...")

    financials    = get_financials(ticker)
    current_price = get_current_price(ticker)

    if not financials:
        return {"ticker": ticker, "error": "No data available"}

    info      = financials["info"]
    cash_flow = financials["cash_flow"]

    try:
        operating_cf   = cash_flow.loc["Operating Cash Flow"].iloc[0]
        capex          = cash_flow.loc["Capital Expenditure"].iloc[0]
        free_cash_flow = operating_cf + capex

        if free_cash_flow < 0:
            return {
                "ticker": ticker,
                "error": "Negative FCF — DCF not applicable for this company"
            }

    except Exception as e:
        print(f"[Error] Could not extract free cash flow: {e}")
        return {"ticker": ticker, "error": "FCF extraction failed"}

    shares = info.get("sharesOutstanding", 1)

    scenarios = {
        "bear": {
            "growth_rate":     0.04,
            "discount_rate":   0.11,
            "terminal_growth": 0.02,
        },
        "base": {
            "growth_rate":     0.07,
            "discount_rate":   0.09,
            "terminal_growth": 0.025,
        },
        "bull": {
            "growth_rate":     0.12,
            "discount_rate":   0.08,
            "terminal_growth": 0.03,
        }
    }

    results = {"ticker": ticker, "current_price": current_price}

    for scenario, assumptions in scenarios.items():
        dcf = calculate_dcf(
            free_cash_flow     = free_cash_flow,
            growth_rate        = assumptions["growth_rate"],
            discount_rate      = assumptions["discount_rate"],
            terminal_growth    = assumptions["terminal_growth"],
            shares_outstanding = shares
        )

        intrinsic = dcf["intrinsic_value"]

        if current_price and intrinsic:
            margin_of_safety = round(
                (intrinsic - current_price) / current_price * 100, 1
            )
        else:
            margin_of_safety = None

        results[scenario] = {
            "intrinsic_value":   intrinsic,
            "margin_of_safety":  margin_of_safety,
            "pv_cash_flows":     dcf["pv_cash_flows"],
            "pv_terminal_value": dcf["pv_terminal_value"],
        }

    return results
def run_monte_carlo(ticker: str, n_simulations: int = 10000) -> dict:
    """
    Run a Monte Carlo DCF simulation for a given ticker.

    Instead of three fixed scenarios, samples 10,000 random combinations
    of input assumptions from probability distributions. Output is a
    probability distribution of intrinsic values rather than point estimates.

    Args:
        ticker:        Stock symbol as a string e.g. "AAPL"
        n_simulations: Number of simulations to run, default 10,000

    Returns:
        Dictionary containing simulation results and statistics.
    """
    print(f"Running Monte Carlo simulation for {ticker} "
          f"({n_simulations:,} simulations)...")

    financials    = get_financials(ticker)
    current_price = get_current_price(ticker)

    if not financials:
        return {"ticker": ticker, "error": "No data available"}

    info      = financials["info"]
    cash_flow = financials["cash_flow"]
    shares    = info.get("sharesOutstanding", 1)

    try:
        operating_cf   = cash_flow.loc["Operating Cash Flow"].iloc[0]
        capex          = cash_flow.loc["Capital Expenditure"].iloc[0]
        free_cash_flow = operating_cf + capex

        if free_cash_flow < 0:
            print(f"[Warning] {ticker} has negative free cash flow — "
                  f"DCF model not applicable. Consider revenue multiple valuation.")
            return {
                "ticker": ticker,
                "error": "Negative FCF — DCF not applicable for this company"
            }

    except Exception as e:
        print(f"[Error] Could not extract FCF: {e}")
        return {"ticker": ticker, "error": "FCF extraction failed"}

    # ── Define stochastic input distributions ─────────────────────────
    growth_mean   = 0.07
    growth_std    = 0.04
    wacc_mean     = 0.09
    wacc_std      = 0.015
    terminal_mean = 0.025
    terminal_std  = 0.005

    # ── Sample all inputs using numpy ─────────────────────────────────
    np.random.seed(42)

    growth_rates   = np.random.lognormal(
                        mean  = np.log(1 + growth_mean),
                        sigma = growth_std,
                        size  = n_simulations
                     ) - 1

    wacc_rates     = np.random.normal(
                        loc   = wacc_mean,
                        scale = wacc_std,
                        size  = n_simulations
                     )

    terminal_rates = np.random.normal(
                        loc   = terminal_mean,
                        scale = terminal_std,
                        size  = n_simulations
                     )

    # Clip to prevent mathematical impossibilities
    wacc_rates     = np.clip(wacc_rates, 0.05, 0.20)
    terminal_rates = np.clip(terminal_rates, 0.01, 0.04)
    wacc_rates     = np.maximum(wacc_rates, terminal_rates + 0.02)

    # ── Vectorized DCF calculation ─────────────────────────────────────
    projection_years = 10
    pv_cash_flows    = np.zeros(n_simulations)

    for year in range(1, projection_years + 1):
        projected_fcf = free_cash_flow * (1 + growth_rates) ** year
        discounted    = projected_fcf / (1 + wacc_rates) ** year
        pv_cash_flows += discounted

    final_fcf      = free_cash_flow * (1 + growth_rates) ** projection_years
    terminal_value = (final_fcf * (1 + terminal_rates) /
                     (wacc_rates - terminal_rates))
    pv_terminal    = terminal_value / (1 + wacc_rates) ** projection_years

    total_value      = pv_cash_flows + pv_terminal
    intrinsic_values = total_value / shares

    # ── Output statistics ──────────────────────────────────────────────
    p10 = np.percentile(intrinsic_values, 10)
    p25 = np.percentile(intrinsic_values, 25)
    p50 = np.percentile(intrinsic_values, 50)
    p75 = np.percentile(intrinsic_values, 75)
    p90 = np.percentile(intrinsic_values, 90)
    std = np.std(intrinsic_values)

    prob_undervalued = np.mean(intrinsic_values > current_price) * 100

    return {
        "ticker":           ticker,
        "current_price":    current_price,
        "n_simulations":    n_simulations,
        "p10":              round(float(p10), 2),
        "p25":              round(float(p25), 2),
        "p50":              round(float(p50), 2),
        "p75":              round(float(p75), 2),
        "p90":              round(float(p90), 2),
        "std":              round(float(std),  2),
        "prob_undervalued": round(float(prob_undervalued), 1),
        "intrinsic_values": intrinsic_values
    }


def plot_monte_carlo(results: dict):
    """
    Visualize Monte Carlo simulation results as a histogram.

    Args:
        results: Output dictionary from run_monte_carlo()
    """
    if "error" in results:
        print(f"Cannot plot: {results['error']}")
        return

    ticker        = results["ticker"]
    current_price = results["current_price"]
    values        = results["intrinsic_values"]
    p10           = results["p10"]
    p50           = results["p50"]
    p90           = results["p90"]
    prob          = results["prob_undervalued"]

    fig, ax = plt.subplots(figsize=(12, 6))

    n, bins, patches = ax.hist(values, bins=100, alpha=0.7,
                                color="steelblue", edgecolor="none")

    for patch, left_edge in zip(patches, bins[:-1]):
        if left_edge < current_price:
            patch.set_facecolor("#e74c3c")
            patch.set_alpha(0.7)
        else:
            patch.set_facecolor("#2ecc71")
            patch.set_alpha(0.7)

    ax.axvline(current_price, color="white",  linewidth=2,
               linestyle="--", label=f"Current Price: ${current_price}")
    ax.axvline(p50,           color="yellow", linewidth=2,
               linestyle="-",  label=f"Median (P50): ${p50:.2f}")
    ax.axvline(p10,           color="orange", linewidth=1.5,
               linestyle=":",  label=f"P10 (Deep Bear): ${p10:.2f}")
    ax.axvline(p90,           color="cyan",   linewidth=1.5,
               linestyle=":",  label=f"P90 (Deep Bull): ${p90:.2f}")

    ax.set_title(
        f"{ticker} — Monte Carlo DCF Simulation (10,000 scenarios)\n"
        f"Probability Undervalued: {prob:.1f}%",
        fontsize=14, fontweight="bold", color="white", pad=15
    )
    ax.set_xlabel("Intrinsic Value Per Share ($)", fontsize=12, color="white")
    ax.set_ylabel("Number of Scenarios",           fontsize=12, color="white")
    ax.legend(fontsize=10, facecolor="#2c2c2c", labelcolor="white")

    ax.set_facecolor("#1a1a2e")
    fig.patch.set_facecolor("#1a1a2e")
    ax.tick_params(colors="white")
    ax.spines["bottom"].set_color("white")
    ax.spines["left"].set_color("white")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    plt.savefig(f"outputs/{ticker}_monte_carlo.png",
                dpi=150, bbox_inches="tight",
                facecolor="#1a1a2e")
    plt.show()
    print(f"Chart saved to outputs/{ticker}_monte_carlo.png")
