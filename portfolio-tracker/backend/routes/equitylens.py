from fastapi import APIRouter, HTTPException
from modules.screener import screen_ticker
from modules.fundamentals import analyze_ticker, calculate_analyst_rating
from modules.dcf import run_dcf_analysis, run_monte_carlo

router = APIRouter(prefix="/equitylens", tags=["equitylens"])

@router.get("/analyze/{ticker}")
async def analyze(ticker: str):
    ticker = ticker.upper()
    try:
        screener     = screen_ticker(ticker)
        fundamentals = analyze_ticker(ticker)
        dcf          = run_dcf_analysis(ticker)
        mc           = run_monte_carlo(ticker)
        return {
            "ticker":       ticker,
            "screener":     screener,
            "fundamentals": fundamentals,
            "dcf":          dcf,
            "monte_carlo":  mc,
            "sentiment":    None
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
