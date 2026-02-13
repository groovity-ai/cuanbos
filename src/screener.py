"""
Enhanced stock screener for CuanBot.
Full LQ45 universe with composite scoring (0-100).
"""

import sys
import json
import concurrent.futures
from market_data import get_stock_data
from tech_analysis import analyze_market_data
from cache import cached, TTL_SCREENER
from logger import get_logger

log = get_logger("screener")

# Full LQ45 stocks (updated for 2024-2025 composition)
LQ45_STOCKS = [
    # Banking
    "BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK", "BRIS.JK",
    # Telco & Tech
    "TLKM.JK", "GOTO.JK", "BUKA.JK",
    # Mining & Energy
    "ADRO.JK", "PTBA.JK", "ANTM.JK", "INCO.JK", "MDKA.JK",
    "ITMG.JK", "HRUM.JK", "PGAS.JK",
    # Consumer
    "UNVR.JK", "ICBP.JK", "INDF.JK", "MYOR.JK", "KLBF.JK",
    # Automotive & Industrial
    "ASII.JK", "UNTR.JK", "SRTG.JK",
    # Property & Infra
    "CTRA.JK", "BSDE.JK", "SMGR.JK", "INTP.JK",
    # Petrochemical & Diversified
    "BRPT.JK", "AKRA.JK", "TPIA.JK",
    # Media & Services
    "MNCN.JK", "EMTK.JK", "ACES.JK",
    # Finance (non-bank)
    "BBTN.JK", "BTPS.JK",
    # Healthcare
    "SIDO.JK",
    # Others
    "TOWR.JK", "TBIG.JK", "EXCL.JK", "ESSA.JK",
    "AMMN.JK", "CPIN.JK", "JPFA.JK", "ERAA.JK", "MAPI.JK",
]


def _compute_composite_score(analysis_result, fundamentals):
    """
    Compute a composite score from 0-100 based on multiple factors.
    Higher = more attractive.
    """
    score = 50  # Start neutral

    # --- RSI Score (0-30 points) ---
    rsi = analysis_result.get("momentum", {}).get("rsi", 50)
    if rsi < 25:
        score += 30     # Extremely oversold → very attractive
    elif rsi < 35:
        score += 20     # Oversold
    elif rsi < 45:
        score += 10     # Slightly oversold
    elif rsi > 75:
        score -= 20     # Overbought
    elif rsi > 65:
        score -= 10     # Slightly overbought

    # --- Trend Score (-15 to +15 points) ---
    trend = analysis_result.get("trend", {}).get("status", "")
    if "Strong Uptrend" in trend:
        score += 15
    elif "Bullish" in trend:
        score += 10
    elif "Strong Downtrend" in trend:
        score -= 15
    elif "Bearish" in trend:
        score -= 10

    # Golden/Death Cross bonus
    if analysis_result.get("trend", {}).get("golden_cross"):
        score += 10
    elif analysis_result.get("trend", {}).get("death_cross"):
        score -= 10

    # --- MACD Score (-5 to +5 points) ---
    macd = analysis_result.get("momentum", {}).get("macd", "")
    if macd == "Bullish":
        score += 5
    elif macd == "Bearish":
        score -= 5

    # --- Fundamental Score (-10 to +15 points) ---
    if fundamentals:
        pe = fundamentals.get("pe_ratio")
        pb = fundamentals.get("pb_ratio")

        if pe is not None:
            if 0 < pe < 10:
                score += 15     # Very cheap
            elif 0 < pe < 15:
                score += 10     # Cheap
            elif pe > 30:
                score -= 5      # Expensive
            elif pe < 0:
                score -= 10     # Losing money

        if pb is not None:
            if 0 < pb < 1:
                score += 5      # Undervalued
            elif pb > 5:
                score -= 5      # Expensive

    # --- Anomaly Penalty ---
    if analysis_result.get("anomalies", {}).get("is_gorengan"):
        score -= 25  # Hard penalty for gorengan

    # Clamp to 0-100
    return max(0, min(100, score))


def screen_stock(symbol):
    """Analyze a single stock and return screening result with composite score."""
    try:
        data = get_stock_data(symbol)
        if "error" in data:
            return None

        analysis = analyze_market_data(data)
        if "error" in analysis:
            return None

        fundamentals = data.get("fundamentals", {})
        composite = _compute_composite_score(analysis, fundamentals)

        return {
            "symbol": symbol,
            "price": analysis["price"],
            "rsi": round(analysis["momentum"]["rsi"], 2),
            "trend": analysis["trend"]["status"],
            "macd": analysis["momentum"].get("macd", "N/A"),
            "pe": fundamentals.get("pe_ratio"),
            "pb": fundamentals.get("pb_ratio"),
            "sector": fundamentals.get("sector", "Unknown"),
            "market_cap": fundamentals.get("market_cap"),
            "verdict": analysis["verdict"],
            "composite_score": composite,
            "is_gorengan": analysis.get("anomalies", {}).get("is_gorengan", False),
        }
    except Exception as e:
        log.warning(f"Screening failed for {symbol}: {e}")
        return None


def run_screener(filter_type="all", min_score=0, sector=None):
    """
    Screen all LQ45 stocks with optional filters.
    Returns dict with results.
    """
    results = []
    log.info(f"Screening {len(LQ45_STOCKS)} stocks (filter={filter_type}, min_score={min_score})")

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(screen_stock, s): s for s in LQ45_STOCKS}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    # Apply filters
    if filter_type == "oversold":
        results = [r for r in results if r["rsi"] < 35]
    elif filter_type == "bullish":
        results = [r for r in results if "Bullish" in r["trend"]]
    elif filter_type == "cheap":
        results = [r for r in results if r["pe"] is not None and 0 < r["pe"] < 15]
    elif filter_type == "high_score":
        results = [r for r in results if r["composite_score"] >= 70]

    # Minimum score filter
    if min_score > 0:
        results = [r for r in results if r["composite_score"] >= min_score]

    # Sector filter
    if sector:
        results = [r for r in results if sector.lower() in (r.get("sector") or "").lower()]

    # Sort by composite score (best first)
    results.sort(key=lambda x: x["composite_score"], reverse=True)

    # Sector summary
    sectors = {}
    for r in results:
        s = r.get("sector", "Unknown")
        if s not in sectors:
            sectors[s] = {"count": 0, "avg_score": 0}
        sectors[s]["count"] += 1
        sectors[s]["avg_score"] += r["composite_score"]
    for s in sectors:
        sectors[s]["avg_score"] = round(sectors[s]["avg_score"] / sectors[s]["count"], 1)

    log.info(f"Screener done: {len(results)} results")
    return {
        "count": len(results),
        "total_screened": len(LQ45_STOCKS),
        "top_pick": results[0] if results else None,
        "sectors": sectors,
        "stocks": results,
    }


if __name__ == "__main__":
    filter_type = sys.argv[1] if len(sys.argv) > 1 else "all"
    result = run_screener(filter_type)
    print(json.dumps(result, indent=2))
