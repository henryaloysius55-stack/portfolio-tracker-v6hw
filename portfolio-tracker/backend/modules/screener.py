"""
screener.py — Technical screening engine for EquityLens.

Filters a list of stock tickers by three technical signals:
1. RSI — identifies overbought and oversold conditions
2. Moving Average Crossover — identifies golden cross and death cross
3. Volume Spike — identifies unusual trading activity
"""

import pandas as pd
import ta
from data.fetcher import get_price_history


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> float:
    """
    Calculate the most recent RSI value for a stock.

    Args:
        df: DataFrame of price history from get_price_history()
        period: Lookback period in days, default is 14

    Returns:
        Most recent RSI value as a float, or None if calculation fails.
    """
    try:
        rsi = ta.momentum.RSIIndicator(df["Close"], window=period).rsi()
        return round(float(rsi.iloc[-1]), 2)
    except Exception as e:
        print(f"[Error] RSI calculation failed: {e}")
        return None


def calculate_moving_averages(df: pd.DataFrame) -> dict:
    """
    Calculate 50-day and 200-day simple moving averages.

    A golden cross occurs when the 50-day crosses above the 200-day — bullish signal.
    A death cross occurs when the 50-day crosses below the 200-day — bearish signal.

    Args:
        df: DataFrame of price history from get_price_history()

    Returns:
        Dictionary with keys: ma_50, ma_200, signal
        Signal is one of: 'golden_cross', 'death_cross', 'neutral'
    """
    try:
        ma_50 = df["Close"].rolling(window=50).mean().iloc[-1]
        ma_200 = df["Close"].rolling(window=200).mean().iloc[-1]

        if ma_50 > ma_200:
            signal = "golden_cross"
        elif ma_50 < ma_200:
            signal = "death_cross"
        else:
            signal = "neutral"

        return {
            "ma_50":   round(ma_50, 2),
            "ma_200":  round(ma_200, 2),
            "signal":  signal
        }

    except Exception as e:
        print(f"[Error] Moving average calculation failed: {e}")
        return {}


def calculate_volume_spike(df: pd.DataFrame, threshold: float = 1.5) -> dict:
    """
    Detect whether today's volume is significantly above the 20-day average.

    A volume spike confirms that a price move has conviction behind it.
    Without volume, price moves are considered weak and unreliable.

    Args:
        df: DataFrame of price history from get_price_history()
        threshold: How many times above average counts as a spike, default 1.5x

    Returns:
        Dictionary with keys: avg_volume, current_volume, spike
        spike is True if current volume exceeds threshold * average volume.
    """
    try:
        avg_volume = df["Volume"].rolling(window=20).mean().iloc[-1]
        current_volume = df["Volume"].iloc[-1]
        spike = current_volume > (threshold * avg_volume)

        return {
            "avg_volume":     round(avg_volume, 0),
            "current_volume": round(current_volume, 0),
            "spike":          spike
        }

    except Exception as e:
        print(f"[Error] Volume spike calculation failed: {e}")
        return {}


def screen_ticker(ticker: str) -> dict:
    """
    Run all three technical screens on a single ticker.

    Args:
        ticker: Stock symbol as a string e.g. "AAPL"

    Returns:
        Dictionary with full screening results for the ticker.
    """
    print(f"Screening {ticker}...")
    df = get_price_history(ticker, period="1y")

    if df.empty:
        return {"ticker": ticker, "error": "No data available"}

    rsi = calculate_rsi(df)
    ma_data = calculate_moving_averages(df)
    volume_data = calculate_volume_spike(df)
    ma_signal = ma_data.get("signal")
    if rsi is not None and rsi > 70:
        rsi_signal = "overbought"
    elif rsi is not None and rsi < 30:
        rsi_signal = "oversold"
    else:
        rsi_signal = "neutral"

    if rsi_signal == "oversold" and ma_signal == "golden_cross":
        overall_signal = "strong_buy"
    elif rsi_signal == "overbought" and ma_signal == "death_cross":
        overall_signal = "strong_sell"
    elif rsi_signal == "oversold" or ma_signal == "golden_cross":
        overall_signal = "buy"
    elif rsi_signal == "overbought" or ma_signal == "death_cross": 
        overall_signal = "sell"
    else:
        overall_signal = "neutral"


    return {
        "ticker":          ticker,
        "rsi":             rsi,
        "rsi_signal":      rsi_signal,
        "ma_50":           ma_data.get("ma_50"),
        "ma_200":          ma_data.get("ma_200"),
        "ma_signal":       ma_data.get("signal"),
        "avg_volume":      volume_data.get("avg_volume"),
        "current_volume":  volume_data.get("current_volume"),
        "volume_spike":    volume_data.get("spike"),
        "overall_signal":  overall_signal
    }


def run_screener(tickers: list) -> pd.DataFrame:
    """
    Screen a list of tickers and return a ranked watchlist DataFrame.

    Args:
        tickers: List of stock ticker strings e.g. ["AAPL", "MSFT", "NVDA"]

    Returns:
        A pandas DataFrame with all screening results, saved to outputs/watchlist.csv
    """
    results = []

    for ticker in tickers:
        result = screen_ticker(ticker)
        results.append(result)

    df = pd.DataFrame(results)
    df.to_csv("outputs/watchlist.csv", index=False)
    print(f"\nWatchlist saved to outputs/watchlist.csv")

    return df
