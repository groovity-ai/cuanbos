from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json

from market_data import get_stock_data, get_crypto_data
from tech_analysis import analyze_market_data
from news import fetch_news
from backtest import run_backtest
from screener import screen_stock, LQ45_STOCKS
from risk_monitor import monitor_risk
from database import (
    add_portfolio_position, get_portfolio, delete_portfolio_position,
    save_analysis, get_latest_analysis
)
from portfolio import check_portfolio as check_portfolio_json
from chart_vision import analyze_chart
from financial_report import analyze_report
from macro_sentiment import analyze_macro
from bandarilogi import analyze_bandarmology
from sentiment_ai import analyze_sentiment

import concurrent.futures

app = FastAPI(
    title="CuanBot API",
    description="AI-Powered Financial Analyst Agent API 💹",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Models ---
class PortfolioInput(BaseModel):
    symbol: str
    type: str  # 'stock' or 'crypto'
    buy_price: float
    amount: float
    sl_pct: Optional[float] = -5
    tp_pct: Optional[float] = 10


# --- Routes ---

@app.get("/")
def root():
    return {
        "name": "CuanBot API",
        "version": "1.0.0",
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
        ]
    }


@app.get("/api/analyze/{asset_type}/{symbol}")
def analyze(asset_type: str, symbol: str):
    """Fetch market data and run technical analysis."""
    if asset_type == "stock":
        data = get_stock_data(symbol)
    elif asset_type == "crypto":
        data = get_crypto_data(symbol)
    else:
        raise HTTPException(400, "Invalid type. Use 'stock' or 'crypto'.")

    if "error" in data:
        raise HTTPException(404, data["error"])

    analysis = analyze_market_data(data)
    if "error" in analysis:
        raise HTTPException(500, analysis["error"])

    # Save to DB
    symbol_name = data.get("symbol")
    price = analysis.get("price")
    if symbol_name and price:
        save_analysis(symbol_name, price, analysis)

    return {"market_data": data, "analysis": analysis}


@app.get("/api/news/{ticker}")
def news(ticker: str, limit: int = Query(5, ge=1, le=20)):
    """Fetch latest news from Google News RSS."""
    result = fetch_news(ticker, limit)
    if "error" in result:
        raise HTTPException(500, result["error"])
    return result


@app.get("/api/backtest/{symbol}/{strategy}")
def backtest(symbol: str, strategy: str):
    """Run a backtest with the given strategy."""
    valid_strategies = ["rsi_oversold", "ma_crossover", "macd_reversal"]
    if strategy not in valid_strategies:
        raise HTTPException(400, f"Invalid strategy. Choose from: {valid_strategies}")

    # run_backtest prints to stdout, so we capture it
    import io, contextlib
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        run_backtest(symbol, strategy)
    output = f.getvalue()

    try:
        return json.loads(output)
    except json.JSONDecodeError:
        raise HTTPException(500, f"Backtest failed: {output}")


@app.get("/api/screener")
def screener(filter: str = Query("all", description="Filter: all, oversold, bullish, cheap")):
    """Screen LQ45 stocks with optional filter."""
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(screen_stock, s): s for s in LQ45_STOCKS}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    # Apply filter
    if filter == "oversold":
        results = [r for r in results if r["rsi"] < 35]
    elif filter == "bullish":
        results = [r for r in results if "Bullish" in r["trend"]]
    elif filter == "cheap":
        results = [r for r in results if r["pe"] is not None and 0 < r["pe"] < 15]

    results.sort(key=lambda x: x["rsi"])
    return {"count": len(results), "stocks": results}


@app.get("/api/portfolio")
def get_portfolio_route():
    """Get all portfolio positions with current PnL."""
    positions = get_portfolio()
    return {"positions": positions, "count": len(positions)}


@app.post("/api/portfolio")
def add_portfolio_route(body: PortfolioInput):
    """Add a new position to the portfolio."""
    result = add_portfolio_position(
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
def delete_portfolio_route(position_id: int):
    """Delete a portfolio position by ID."""
    deleted = delete_portfolio_position(position_id)
    if not deleted:
        raise HTTPException(404, "Position not found")
    return {"status": "deleted", "id": position_id}


@app.get("/api/risk")
def risk():
    """Check portfolio for Stop Loss / Take Profit alerts."""
    import io, contextlib
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        monitor_risk()
    output = f.getvalue()

    try:
        return json.loads(output)
    except json.JSONDecodeError:
        raise HTTPException(500, f"Risk monitor failed: {output}")


@app.get("/api/history/{symbol}")
def history(symbol: str):
    """Get latest saved analysis for a symbol."""
    result = get_latest_analysis(symbol)
    if result is None:
        raise HTTPException(404, f"No analysis found for {symbol}")
    # Convert date/decimal types for JSON
    return {k: str(v) if not isinstance(v, (str, int, float, type(None))) else v for k, v in result.items()}


# ========== NEW FEATURES ==========

@app.post("/api/chart-vision")
async def chart_vision(file: UploadFile = File(...)):
    """Analyze a candlestick chart screenshot using Gemini Vision."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image (PNG, JPG)")

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(400, "Image too large. Max 10MB.")

    result = analyze_chart(image_bytes)
    if "error" in result:
        raise HTTPException(500, result["error"])
    return result


@app.post("/api/report")
async def report(file: UploadFile = File(...)):
    """Upload and analyze a PDF financial report using RAG."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "File must be a PDF")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > 20 * 1024 * 1024:  # 20MB limit
        raise HTTPException(400, "PDF too large. Max 20MB.")

    result = analyze_report(pdf_bytes)
    if "error" in result:
        raise HTTPException(500, result["error"])
    return result


@app.get("/api/macro")
def macro():
    """Get macro-economic data and AI market outlook."""
    result = analyze_macro()
    return result


@app.get("/api/bandarilogi/{symbol}")
def bandarilogi(symbol: str):
    """Analyze foreign flow / bandarmology for a stock."""
    result = analyze_bandarmology(symbol)
    if "error" in result:
        raise HTTPException(500, result["error"])
    return result


@app.get("/api/sentiment/{ticker}")
def sentiment(ticker: str):
    """Analyze news sentiment for a ticker using AI."""
    result = analyze_sentiment(ticker)
    if "error" in result:
        raise HTTPException(500, result["error"])
    return result
