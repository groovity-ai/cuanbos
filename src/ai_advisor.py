"""
AI Advisor — CuanBot's unified intelligence endpoint.
Combines Technical, Sentiment, Bandarilogi, and Macro analysis
into a single AI-powered verdict.
"""

import json
from market_data import get_stock_data
from tech_analysis import analyze_market_data
from bandarilogi import analyze_bandarmology
from sentiment_ai import analyze_sentiment
from macro_sentiment import analyze_macro
from ai_client import chat_completion
from cache import cached, TTL_ANALYSIS
from logger import get_logger

log = get_logger("ai_advisor")

ADVISOR_PROMPT = """Kamu adalah CuanBot AI Advisor — penasehat investasi saham Indonesia yang cerdas dan berbasis data.

Berikut data lengkap untuk saham {symbol}:

## 1. Data Teknikal
{technical_json}

## 2. Analisa Bandarilogi (Foreign Flow)
{bandar_json}

## 3. Sentimen Berita
{sentiment_json}

## 4. Kondisi Makro Ekonomi
{macro_json}

---

Berdasarkan SEMUA data di atas, berikan analisa komprehensif dalam format JSON:
{{
  "verdict": "STRONG BUY / BUY / HOLD / SELL / STRONG SELL / AVOID",
  "confidence": 0-100,
  "reasoning": "Penjelasan singkat kenapa kamu kasih verdict itu (bahasa Indonesia, santai)",
  "key_factors": ["faktor 1", "faktor 2", "faktor 3"],
  "risk_level": "Low / Medium / High / Very High",
  "target_entry": harga_entry_ideal_atau_null,
  "target_exit": harga_exit_ideal_atau_null,
  "timeframe": "Short-term / Medium-term / Long-term"
}}

PENTING: Jawab HANYA dengan JSON, tanpa markdown atau teks tambahan."""


@cached("ai_advisor", ttl=TTL_ANALYSIS)
def get_ai_advice(symbol):
    """
    Run all analyses and combine into a single AI-powered verdict.
    """
    log.info(f"AI Advisor: generating advice for {symbol}")

    # 1. Technical Analysis
    market_data = get_stock_data(symbol)
    if "error" in market_data:
        return {"error": f"Failed to get market data: {market_data['error']}"}

    technical = analyze_market_data(market_data)
    if "error" in technical:
        return {"error": f"Technical analysis failed: {technical['error']}"}

    # 2. Bandarilogi
    try:
        bandar = analyze_bandarmology(symbol)
    except Exception as e:
        bandar = {"error": str(e)}

    # 3. Sentiment
    try:
        sentiment = analyze_sentiment(symbol.replace(".JK", ""))
    except Exception as e:
        sentiment = {"error": str(e)}

    # 4. Macro
    try:
        macro = analyze_macro()
    except Exception as e:
        macro = {"error": str(e)}

    # Build prompt
    prompt = ADVISOR_PROMPT.format(
        symbol=symbol,
        technical_json=json.dumps(technical, indent=2, default=str),
        bandar_json=json.dumps(bandar, indent=2, default=str),
        sentiment_json=json.dumps(sentiment, indent=2, default=str),
        macro_json=json.dumps(macro, indent=2, default=str),
    )

    # Call LLM
    try:
        raw_response = chat_completion(prompt)
        # Try to parse JSON from response
        ai_result = json.loads(raw_response)
    except json.JSONDecodeError:
        # If LLM didn't return clean JSON, wrap it
        ai_result = {
            "verdict": "HOLD",
            "confidence": 50,
            "reasoning": raw_response,
            "key_factors": ["AI response was not structured"],
            "risk_level": "Medium",
        }
    except Exception as e:
        log.error(f"AI Advisor LLM call failed: {e}")
        ai_result = {
            "verdict": "HOLD",
            "confidence": 0,
            "reasoning": f"AI analysis unavailable: {str(e)}",
            "risk_level": "Unknown",
        }

    return {
        "symbol": symbol,
        "ai_verdict": ai_result,
        "data_sources": {
            "technical": technical,
            "bandarilogi": bandar if "error" not in bandar else None,
            "sentiment": sentiment if "error" not in sentiment else None,
            "macro": macro if "error" not in macro else None,
        },
    }
