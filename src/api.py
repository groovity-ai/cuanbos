"""
CuanBot API — AI-Powered Financial Analyst Agent API 💹
Fully async FastAPI with structured logging.
v3.0 — Data Intelligence: History, Multi-Source, AI Memory
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
    save_analysis, get_latest_analysis, close_pool,
    save_analysis_history, get_analysis_history, get_analysis_trend,
    save_feedback, get_feedback_stats,
)
from portfolio import check_portfolio as check_portfolio_json
from chart_vision import analyze_chart
from financial_report import analyze_report
from macro_sentiment import analyze_macro
from bandarilogi import analyze_bandarmology
from sentiment_ai import analyze_sentiment
from ai_advisor import get_ai_advice
from data_sources import aggregate_all_sources
from logger import get_logger

import concurrent.futures

log = get_logger("api")

app = FastAPI(
    title="CuanBot API",
    description="AI-Powered Financial Analyst Agent API 💹",
    version="3.0.0"
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


class FeedbackInput(BaseModel):
    analysis_id: int
    symbol: str = ""
    rating: int  # 1 = 👍, -1 = 👎
    comment: Optional[str] = None


# --- Health Check ---
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "version": "3.0.0"}


# --- Routes ---
@app.get("/")
async def root():
    return {
        "name": "CuanBot API",
        "version": "3.0.0",
        "endpoints": [
            "/api/analyze/{type}/{symbol}",
            "/api/news/{ticker}",
            "/api/backtest/{symbol}/{strategy}",
            "/api/screener",
            "/api/portfolio",
            "/api/risk",
            "/api/history/{symbol}",
            "/api/history/{symbol}/full",
            "/api/history/{symbol}/trend",
            "/api/feedback",
            "/api/feedback/stats",
            "/api/data-sources/{symbol}",
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
        # Also save to analysis_history
        await run_sync(save_analysis_history, symbol_name, "technical", analysis)

    return {"market_data": data, "analysis": analysis}


@app.get("/api/news/{ticker}")
async def news(ticker: str, limit: int = Query(5, ge=1, le=20)):
    """Fetch latest news from Google News RSS + CNBC Indonesia."""
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


# ========== HISTORY & INTELLIGENCE ==========

@app.get("/api/history/{symbol}")
async def history(symbol: str):
    """Get latest saved analysis for a symbol (from daily_analysis)."""
    result = await run_sync(get_latest_analysis, symbol)
    if result is None:
        raise HTTPException(404, f"No analysis found for {symbol}")
    return {k: str(v) if not isinstance(v, (str, int, float, type(None))) else v for k, v in result.items()}


@app.get("/api/history/{symbol}/full")
async def history_full(
    symbol: str,
    type: str = Query(None, description="Filter by analysis type: technical, ai_advisor, sentiment, bandarilogi, macro"),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
):
    """
    Get full analysis history (JSONB snapshots) for a symbol.
    Paginated, optionally filtered by analysis_type.
    """
    results = await run_sync(get_analysis_history, symbol, type, limit, offset)
    # Serialize dates
    for r in results:
        if "created_at" in r:
            r["created_at"] = str(r["created_at"])
    return {"symbol": symbol, "count": len(results), "history": results}


@app.get("/api/history/{symbol}/trend")
async def history_trend(
    symbol: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
):
    """
    Get time-series trend data (RSI, price, verdict) for a symbol.
    Useful for tracking how a stock has performed over time.
    """
    results = await run_sync(get_analysis_trend, symbol, days)
    # Serialize dates
    for r in results:
        if "analysis_date" in r:
            r["analysis_date"] = str(r["analysis_date"])
        if "price" in r and r["price"] is not None:
            r["price"] = float(r["price"])
        if "rsi" in r and r["rsi"] is not None:
            r["rsi"] = float(r["rsi"])
    return {"symbol": symbol, "days": days, "data_points": len(results), "trend": results}


@app.post("/api/feedback")
async def submit_feedback(body: FeedbackInput):
    """
    Submit feedback (👍/👎) on an AI analysis.
    Rating: 1 = thumbs up, -1 = thumbs down.
    """
    if body.rating not in (1, -1):
        raise HTTPException(400, "Rating must be 1 (👍) or -1 (👎)")

    result = await run_sync(save_feedback, body.analysis_id, body.symbol, body.rating, body.comment)
    if result is None:
        raise HTTPException(500, "Failed to save feedback")

    # Serialize dates
    if "created_at" in result:
        result["created_at"] = str(result["created_at"])
    return {"status": "saved", "feedback": result}


@app.get("/api/feedback/stats")
async def feedback_stats(symbol: str = Query(None, description="Optional: filter by symbol")):
    """Get accuracy stats from user feedback."""
    stats = await run_sync(get_feedback_stats, symbol)
    return {"symbol": symbol, "stats": stats}


@app.get("/api/data-sources/{symbol}")
async def data_sources(symbol: str):
    """
    Get aggregated data from multiple sources
    (CNBC Indonesia, macro indicators, BI rate, bonds, VIX, oil).
    """
    result = await run_sync(aggregate_all_sources, symbol)
    return result


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
async def report(file: UploadFile = File(...), skip_llm: bool = Query(True, description="Skip LLM analysis, return raw extracted text")):
    """Upload and analyze a PDF financial report using RAG."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "File must be a PDF")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > 20 * 1024 * 1024:
        raise HTTPException(400, "PDF too large. Max 20MB.")

    result = await run_sync(analyze_report, pdf_bytes, skip_llm)
    if "error" in result:
        raise HTTPException(500, result["error"])
    return result


@app.get("/api/macro")
async def macro(skip_llm: bool = Query(True, description="Skip LLM analysis, return raw macro data")):
    """Get macro-economic data and optionally AI market outlook (multi-source)."""
    result = await run_sync(analyze_macro, skip_llm)
    return result


@app.get("/api/bandarilogi/{symbol}")
async def bandarilogi(symbol: str, skip_llm: bool = Query(True, description="Skip LLM commentary, return raw indicators")):
    """Analyze foreign flow / bandarmology for a stock."""
    result = await run_sync(analyze_bandarmology, symbol, skip_llm)
    if "error" in result:
        raise HTTPException(500, result["error"])
    return result


@app.get("/api/sentiment/{ticker}")
async def sentiment(ticker: str, skip_llm: bool = Query(True, description="Skip LLM sentiment scoring, return raw headlines")):
    """Get news headlines and optionally analyze sentiment using AI."""
    result = await run_sync(analyze_sentiment, ticker, 5, skip_llm)
    if "error" in result:
        raise HTTPException(500, result["error"])
    return result


@app.get("/api/ai-advisor/{symbol}")
async def ai_advisor(symbol: str, skip_llm: bool = Query(True, description="Skip LLM verdict, return raw data for agent reasoning")):
    """
    Unified AI Advisor — combines technical, sentiment, bandarilogi,
    macro analysis, AND memory from past analyses.
    skip_llm=True (default): returns raw data, calling agent does reasoning.
    skip_llm=False: backend LLM generates verdict.
    """
    log.info(f"AI Advisor request: {symbol} (skip_llm={skip_llm})")
    result = await run_sync(get_ai_advice, symbol, skip_llm)
    if "error" in result:
        raise HTTPException(500, result["error"])
    return result
