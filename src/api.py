"""
CuanBot API — AI-Powered Financial Analyst Agent API 💹
Fully async FastAPI with structured logging.
"""

import asyncio
import json
from functools import partial

from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from market_data import get_stock_data, get_crypto_data
from tech_analysis import analyze_market_data
from news import fetch_news
from backtest import run_backtest
from screener import run_screener, LQ45_STOCKS
from risk_monitor import monitor_risk
from database import (
    add_portfolio_position, get_portfolio, delete_portfolio_position,
    save_analysis, get_latest_analysis, close_pool
)
from portfolio import check_portfolio as check_portfolio_json
from chart_vision import analyze_chart
from financial_report import analyze_report
from macro_sentiment import analyze_macro
from bandarilogi import analyze_bandarmology
from sentiment_ai import analyze_sentiment
from ai_advisor import get_ai_advice
from logger import get_logger

import concurrent.futures

log = get_logger("api")

app = FastAPI(
    title="CuanBot API",
    description="AI-Powered Financial Analyst Agent API 💹",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thread pool for blocking I/O (yfinance, DB, etc.)
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)


async def run_sync(func, *args, **kwargs):
    """Run a blocking function in a thread executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, partial(func, *args, **kwargs))


# --- Lifecycle Events ---
@app.on_event("shutdown")
def shutdown_event():
    close_pool()
    _executor.shutdown(wait=False)
    log.info("CuanBot API shutdown complete")


# --- Models ---
class PortfolioInput(BaseModel):
    symbol: str
    type: str  # 'stock' or 'crypto'
    buy_price: float
    amount: float
    sl_pct: Optional[float] = -5
    tp_pct: Optional[float] = 10


# --- Health Check ---
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "version": "2.0.0"}


# --- Routes ---
@app.get("/")
async def root():
    return {
        "name": "CuanBot API",
        "version": "2.0.0",
        "endpoints": [
            "/api/analyze/{type}/{symbol}",
            "/api/news/{ticker}",
            "/api/backtest/{symbol}/{strategy}",
            "/api/screener",
            "/api/portfolio",
            "/api/risk",
            "/api/chart-vision",
            "/api/report",
            "/api/macro",
            "/api/bandarilogi/{symbol}",
            "/api/sentiment/{ticker}",
            "/api/ai-advisor/{symbol}",
        ]
    }


@app.get("/api/analyze/{asset_type}/{symbol}")
async def analyze(asset_type: str, symbol: str):
    """Fetch market data and run technical analysis."""
    if asset_type == "stock":
        data = await run_sync(get_stock_data, symbol)
    elif asset_type == "crypto":
        data = await run_sync(get_crypto_data, symbol)
    else:
        raise HTTPException(400, "Invalid type. Use 'stock' or 'crypto'.")

    if "error" in data:
        raise HTTPException(404, data["error"])

    analysis = await run_sync(analyze_market_data, data)
    if "error" in analysis:
        raise HTTPException(500, analysis["error"])

    # Save to DB (fire and forget)
    symbol_name = data.get("symbol")
    price = analysis.get("price")
    if symbol_name and price:
        await run_sync(save_analysis, symbol_name, price, analysis)

    return {"market_data": data, "analysis": analysis}


@app.get("/api/news/{ticker}")
async def news(ticker: str, limit: int = Query(5, ge=1, le=20)):
    """Fetch latest news from Google News RSS."""
    result = await run_sync(fetch_news, ticker, limit)
    if "error" in result:
        raise HTTPException(500, result["error"])
    return result


@app.get("/api/backtest/{symbol}/{strategy}")
async def backtest(symbol: str, strategy: str):
    """Run a backtest with the given strategy."""
    valid_strategies = ["rsi_oversold", "ma_crossover", "macd_reversal"]
    if strategy not in valid_strategies:
        raise HTTPException(400, f"Invalid strategy. Choose from: {valid_strategies}")

    result = await run_sync(run_backtest, symbol, strategy)
    if "error" in result:
        raise HTTPException(500, result["error"])
    return result


@app.get("/api/screener")
async def screener(
    filter: str = Query("all", description="Filter: all, oversold, bullish, cheap, high_score"),
    min_score: int = Query(0, ge=0, le=100, description="Minimum composite score"),
    sector: str = Query(None, description="Filter by sector name"),
):
    """Screen LQ45 stocks with composite scoring."""
    result = await run_sync(run_screener, filter, min_score, sector)
    return result


@app.get("/api/portfolio")
async def get_portfolio_route():
    """Get all portfolio positions with current PnL."""
    positions = await run_sync(get_portfolio)
    return {"positions": positions, "count": len(positions)}


@app.post("/api/portfolio")
async def add_portfolio_route(body: PortfolioInput):
    """Add a new position to the portfolio."""
    result = await run_sync(
        add_portfolio_position,
        symbol=body.symbol,
        asset_type=body.type,
        entry_price=body.buy_price,
        qty=body.amount,
        sl_pct=body.sl_pct,
        tp_pct=body.tp_pct,
    )
    if result is None:
        raise HTTPException(500, "Failed to add position")
    return {"status": "added", "position": result}


@app.delete("/api/portfolio/{position_id}")
async def delete_portfolio_route(position_id: int):
    """Delete a portfolio position by ID."""
    deleted = await run_sync(delete_portfolio_position, position_id)
    if not deleted:
        raise HTTPException(404, "Position not found")
    return {"status": "deleted", "id": position_id}


@app.get("/api/risk")
async def risk():
    """Check portfolio for Stop Loss / Take Profit alerts."""
    result = await run_sync(monitor_risk)
    return result


@app.get("/api/history/{symbol}")
async def history(symbol: str):
    """Get latest saved analysis for a symbol."""
    result = await run_sync(get_latest_analysis, symbol)
    if result is None:
        raise HTTPException(404, f"No analysis found for {symbol}")
    return {k: str(v) if not isinstance(v, (str, int, float, type(None))) else v for k, v in result.items()}


# ========== AI FEATURES ==========

@app.post("/api/chart-vision")
async def chart_vision(file: UploadFile = File(...)):
    """Analyze a candlestick chart screenshot using Gemini Vision."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image (PNG, JPG)")

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(400, "Image too large. Max 10MB.")

    result = await run_sync(analyze_chart, image_bytes)
    if "error" in result:
        raise HTTPException(500, result["error"])
    return result


@app.post("/api/report")
async def report(file: UploadFile = File(...)):
    """Upload and analyze a PDF financial report using RAG."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "File must be a PDF")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > 20 * 1024 * 1024:
        raise HTTPException(400, "PDF too large. Max 20MB.")

    result = await run_sync(analyze_report, pdf_bytes)
    if "error" in result:
        raise HTTPException(500, result["error"])
    return result


@app.get("/api/macro")
async def macro():
    """Get macro-economic data and AI market outlook."""
    result = await run_sync(analyze_macro)
    return result


@app.get("/api/bandarilogi/{symbol}")
async def bandarilogi(symbol: str):
    """Analyze foreign flow / bandarmology for a stock."""
    result = await run_sync(analyze_bandarmology, symbol)
    if "error" in result:
        raise HTTPException(500, result["error"])
    return result


@app.get("/api/sentiment/{ticker}")
async def sentiment(ticker: str):
    """Analyze news sentiment for a ticker using AI."""
    result = await run_sync(analyze_sentiment, ticker)
    if "error" in result:
        raise HTTPException(500, result["error"])
    return result


@app.get("/api/ai-advisor/{symbol}")
async def ai_advisor(symbol: str):
    """
    Unified AI Advisor — combines technical, sentiment, bandarilogi,
    and macro analysis into a single intelligent verdict.
    """
    log.info(f"AI Advisor request: {symbol}")
    result = await run_sync(get_ai_advice, symbol)
    if "error" in result:
        raise HTTPException(500, result["error"])
    return result
