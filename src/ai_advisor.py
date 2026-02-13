"""
AI Advisor — CuanBot's unified intelligence endpoint.
Combines Technical, Sentiment, Bandarilogi, Macro analysis + AI Memory
into a single AI-powered verdict. Saves results to analysis history.
"""

import json
from market_data import get_stock_data
from tech_analysis import analyze_market_data
from bandarilogi import analyze_bandarmology
from sentiment_ai import analyze_sentiment
from macro_sentiment import analyze_macro
from ai_client import chat_completion
from ai_memory import format_memory_prompt
from database import save_analysis_history
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

{memory_section}
---

Berdasarkan SEMUA data di atas (termasuk riwayat analisa sebelumnya jika ada), berikan analisa komprehensif dalam format JSON:
{{
  "verdict": "STRONG BUY / BUY / HOLD / SELL / STRONG SELL / AVOID",
  "confidence": 0-100,
  "reasoning": "Penjelasan singkat kenapa kamu kasih verdict itu (bahasa Indonesia, santai)",
  "key_factors": ["faktor 1", "faktor 2", "faktor 3"],
  "risk_level": "Low / Medium / High / Very High",
  "target_entry": harga_entry_ideal_atau_null,
  "target_exit": harga_exit_ideal_atau_null,
  "timeframe": "Short-term / Medium-term / Long-term",
  "consistency_note": "Catatan jika verdict berubah dari analisa sebelumnya, jelaskan kenapa"
}}

PENTING: Jawab HANYA dengan JSON, tanpa markdown atau teks tambahan."""


@cached("ai_advisor", ttl=TTL_ANALYSIS)
def get_ai_advice(symbol):
    """
    Run all analyses and combine into a single AI-powered verdict.
    Injects memory context from past analyses.
    """
    log.info(f"AI Advisor: generating advice for {symbol}")

    # 1. Technical Analysis
    market_data = get_stock_data(symbol)
    if "error" in market_data:
        return {"error": f"Failed to get market data: {market_data['error']}"}

    technical = analyze_market_data(market_data)
    if "error" in technical:
        return {"error": f"Technical analysis failed: {technical['error']}"}

    # Save technical analysis to history
    save_analysis_history(symbol, "technical", technical)

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

    # 5. AI Memory — inject past context
    memory_text = format_memory_prompt(symbol)
    memory_section = f"\n{memory_text}\n" if memory_text else ""

    # Build prompt
    prompt = ADVISOR_PROMPT.format(
        symbol=symbol,
        technical_json=json.dumps(technical, indent=2, default=str),
        bandar_json=json.dumps(bandar, indent=2, default=str),
        sentiment_json=json.dumps(sentiment, indent=2, default=str),
        macro_json=json.dumps(macro, indent=2, default=str),
        memory_section=memory_section,
    )

    # Call LLM
    try:
        raw_response = chat_completion(prompt)
        # Try to parse JSON from response
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
        ai_result = json.loads(cleaned)
    except json.JSONDecodeError:
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

    result = {
        "symbol": symbol,
        "ai_verdict": ai_result,
        "has_memory": memory_text is not None,
        "data_sources": {
            "technical": technical,
            "bandarilogi": bandar if "error" not in bandar else None,
            "sentiment": sentiment if "error" not in sentiment else None,
            "macro": macro if "error" not in macro else None,
        },
    }

    # Save AI advisor result to history
    history_id = save_analysis_history(symbol, "ai_advisor", result)
    if history_id:
        result["analysis_id"] = history_id

    return result
