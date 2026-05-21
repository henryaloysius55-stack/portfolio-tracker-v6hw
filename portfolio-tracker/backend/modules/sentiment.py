"""
sentiment.py — News sentiment analysis engine for EquityLens.

Uses FinBERT, a financial domain BERT model, to score the sentiment
of recent news headlines for a given ticker.

FinBERT was trained on financial news, earnings calls, and analyst
reports — making it far more accurate than general sentiment models
for financial text analysis.
"""

import yfinance as yf
from transformers import pipeline
import numpy as np


# Load FinBERT once at module level so it doesn't reload every call
# This takes 10-15 seconds on first run — subsequent calls are instant
print("Loading FinBERT sentiment model...")
sentiment_pipeline = pipeline(
    "sentiment-analysis",
    model="ProsusAI/finbert",
    truncation=True,
    use_fast=False  # Add this to avoid some multi-threading issues
)
print("FinBERT loaded.")


def get_news_headlines(ticker: str, max_headlines: int = 10) -> list:
    """
    Fetch recent news headlines for a ticker using yfinance.

    Args:
        ticker:        Stock symbol e.g. "AAPL"
        max_headlines: Maximum number of headlines to fetch

    Returns:
        List of headline strings.
    """
    try:
        stock = yf.Ticker(ticker)
        news  = stock.news

        headlines = []
        for article in news[:max_headlines]:
            # yfinance stores headline in 'content' or 'title'
            content = article.get("content", {})
            title   = (content.get("title") if isinstance(content, dict)
                      else article.get("title", ""))
            if title:
                headlines.append(title)

        return headlines

    except Exception as e:
        print(f"[Error] Could not fetch news for {ticker}: {e}")
        return []


def analyze_sentiment(ticker: str) -> dict:
    """
    Analyze sentiment of recent news headlines for a ticker.

    Runs each headline through FinBERT and aggregates the results
    into a composite sentiment score.

    Args:
        ticker: Stock symbol e.g. "AAPL"

    Returns:
        Dictionary with sentiment score, label, and headline details.
    """
    headlines = get_news_headlines(ticker)

    if not headlines:
        return {
            "ticker":          ticker,
            "sentiment_score": None,
            "sentiment_label": "neutral",
            "headline_count":  0,
            "headlines":       [],
            "error":           "No headlines found"
        }

    print(f"Analyzing sentiment for {len(headlines)} headlines...")

    results     = []
    scored_news = []

    for headline in headlines:
        try:
            result = sentiment_pipeline(headline)[0]
            label  = result["label"].lower()
            score  = result["score"]

            # Convert to numeric: positive=+1, negative=-1, neutral=0
            if label == "positive":
                numeric = score
            elif label == "negative":
                numeric = -score
            else:
                numeric = 0

            results.append(numeric)
            scored_news.append({
                "headline": headline,
                "label":    label,
                "score":    round(score, 3),
                "numeric":  round(numeric, 3)
            })

        except Exception as e:
            print(f"[Error] Could not score headline: {e}")
            continue

    if not results:
        return {
            "ticker":          ticker,
            "sentiment_score": None,
            "sentiment_label": "neutral",
            "headline_count":  0,
            "headlines":       scored_news
        }

    # Composite score: average of all numeric scores (-1 to +1)
    composite = np.mean(results)

    # Convert to label
    if composite > 0.15:
        label = "positive"
    elif composite < -0.15:
        label = "negative"
    else:
        label = "neutral"

    # Convert to 0-100 scale for display
    display_score = round((composite + 1) / 2 * 100, 1)

    return {
        "ticker":          ticker,
        "sentiment_score": round(float(composite), 3),
        "display_score":   display_score,
        "sentiment_label": label,
        "headline_count":  len(results),
        "headlines":       scored_news
    }
