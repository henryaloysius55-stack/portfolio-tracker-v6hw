import pandas as pd
import ta
from data.fetcher import get_price_history

def calculate_rsi(df, period=14):
    try:
        rsi = ta.momentum.RSIIndicator(df["Close"], window=period).rsi()
        return round(float(rsi.iloc[-1]), 2)
    except Exception as e:
        print(f"[Error] RSI failed: {e}")
        return None

def calculate_moving_averages(df):
    try:
        ma_50  = df["Close"].rolling(50).mean().iloc[-1]
        ma_200 = df["Close"].rolling(200).mean().iloc[-1]
        signal = "golden_cross" if ma_50 > ma_200 else "death_cross" if ma_50 < ma_200 else "neutral"
        return {"ma_50": round(ma_50, 2), "ma_200": round(ma_200, 2), "signal": signal}
    except Exception as e:
        print(f"[Error] MA failed: {e}")
        return {}

def calculate_volume_spike(df, threshold=1.5):
    try:
        avg = df["Volume"].rolling(20).mean().iloc[-1]
        cur = df["Volume"].iloc[-1]
        return {"avg_volume": round(avg, 0), "current_volume": round(cur, 0), "spike": bool(cur > threshold * avg)}
    except Exception as e:
        print(f"[Error] Volume spike failed: {e}")
        return {}

def screen_ticker(ticker: str) -> dict:
    print(f"Screening {ticker}...")
    df = get_price_history(ticker, period="1y")
    if df.empty:
        return {"ticker": ticker, "error": "No data available"}

    rsi         = calculate_rsi(df)
    ma_data     = calculate_moving_averages(df)
    volume_data = calculate_volume_spike(df)
    ma_signal   = ma_data.get("signal")

    rsi_signal = "overbought" if rsi and rsi > 70 else "oversold" if rsi and rsi < 30 else "neutral"

    if rsi_signal == "oversold" and ma_signal == "golden_cross":
        overall = "strong_buy"
    elif rsi_signal == "overbought" and ma_signal == "death_cross":
        overall = "strong_sell"
    elif rsi_signal == "oversold" or ma_signal == "golden_cross":
        overall = "buy"
    elif rsi_signal == "overbought" or ma_signal == "death_cross":
        overall = "sell"
    else:
        overall = "neutral"

    return {
        "ticker": ticker, "rsi": rsi, "rsi_signal": rsi_signal,
        "ma_50": ma_data.get("ma_50"), "ma_200": ma_data.get("ma_200"),
        "ma_signal": ma_signal, "avg_volume": volume_data.get("avg_volume"),
        "current_volume": volume_data.get("current_volume"),
        "volume_spike": volume_data.get("spike"), "overall_signal": overall
    }
