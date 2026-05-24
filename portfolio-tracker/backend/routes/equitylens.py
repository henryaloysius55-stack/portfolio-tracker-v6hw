from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from modules.screener import screen_ticker
from modules.fundamentals import analyze_ticker, calculate_analyst_rating
from modules.dcf import run_dcf_analysis, run_monte_carlo
import numpy as np
import math
import asyncio

def clean(obj):
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean(v) for v in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return None if math.isnan(obj) else float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, float) and math.isnan(obj):
        return None
    return obj

router = APIRouter(prefix="/equitylens", tags=["equitylens"])

@router.get("/analyze/{ticker}")
async def analyze(ticker: str):
    ticker = ticker.upper()
    try:
        screener = screen_ticker(ticker)
        await asyncio.sleep(2)
        fundamentals = analyze_ticker(ticker)
        await asyncio.sleep(2)
        dcf = run_dcf_analysis(ticker)
        await asyncio.sleep(2)
        mc = run_monte_carlo(ticker)
        return JSONResponse(content=clean({
            "ticker":       ticker,
            "screener":     screener,
            "fundamentals": fundamentals,
            "dcf":          dcf,
            "monte_carlo":  mc,
            "sentiment":    None
        }))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
