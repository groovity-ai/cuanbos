"""
Macro-Economic Sentiment
Scrape BI Rate, Fed Rate, USD/IDR, and get AI market outlook.
"""

import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import yfinance as yf
from ai_client import chat_completion


def get_usd_idr():
    """Get current USD/IDR exchange rate from yfinance."""
    try:
        ticker = yf.Ticker("USDIDR=X")
        try:
            price = ticker.fast_info['last_price']
        except Exception:
            hist = ticker.history(period="5d")
            if hist.empty:
                return None
            price = hist['Close'].iloc[-1]
        return round(price, 2)
    except Exception:
        return None


def get_ihsg():
    """Get IHSG (JCI) latest data."""
    try:
        ticker = yf.Ticker("^JKSE")
        hist = ticker.history(period="5d")
        if hist.empty:
            return None
        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else hist.iloc[0]
        change_pct = ((latest['Close'] - prev['Close']) / prev['Close']) * 100
        return {
            "value": round(latest['Close'], 2),
            "change_pct": round(change_pct, 2),
        }
    except Exception:
        return None


def get_gold_price():
    """Get gold price (XAU/USD)."""
    try:
        ticker = yf.Ticker("GC=F")
        try:
            price = ticker.fast_info['last_price']
        except Exception:
            hist = ticker.history(period="5d")
            if hist.empty:
                return None
            price = hist['Close'].iloc[-1]
        return round(price, 2)
    except Exception:
        return None


def get_macro_news():
    """Fetch macro-economic news from Google News RSS."""
    try:
        queries = ["BI rate Indonesia", "Fed rate decision", "inflasi Indonesia"]
        all_news = []
        for q in queries:
            encoded = urllib.parse.quote(q)
            url = f"https://news.google.com/rss/search?q={encoded}&hl=id&gl=ID&ceid=ID:id"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                xml_data = resp.read()
            root = ET.fromstring(xml_data)
            for item in root.findall('./channel/item')[:2]:
                title = item.find('title').text if item.find('title') is not None else ""
                if " - " in title:
                    title = title.rsplit(" - ", 1)[0]
                all_news.append({"topic": q, "title": title})
        return all_news
    except Exception:
        return []


def get_macro_data():
    """Collect all macro-economic data points."""
    return {
        "usd_idr": get_usd_idr(),
        "ihsg": get_ihsg(),
        "gold_usd": get_gold_price(),
        "news": get_macro_news(),
    }


def analyze_macro():
    """
    Collect macro data and get AI market outlook.
    Returns dict with macro data + AI analysis.
    """
    data = get_macro_data()

    # Build context for LLM
    context_parts = []
    if data["usd_idr"]:
        context_parts.append(f"USD/IDR: {data['usd_idr']}")
    if data["ihsg"]:
        context_parts.append(f"IHSG: {data['ihsg']['value']} ({data['ihsg']['change_pct']:+.2f}%)")
    if data["gold_usd"]:
        context_parts.append(f"Gold (XAU/USD): ${data['gold_usd']}")
    if data["news"]:
        news_text = "\n".join([f"- [{n['topic']}] {n['title']}" for n in data["news"]])
        context_parts.append(f"Recent News:\n{news_text}")

    context = "\n".join(context_parts)

    messages = [
        {
            "role": "system",
            "content": """You are CuanBot Macro Analyst. Analyze the macro-economic data and respond in VALID JSON:
{
    "outlook": "Bullish / Bearish / Neutral",
    "confidence": "high/medium/low",
    "factors": [
        {"factor": "name", "impact": "positive/negative/neutral", "detail": "brief explanation"}
    ],
    "recommendation": "1-2 sentence market recommendation in Bahasa Indonesia (santai)",
    "risk_level": "Low / Medium / High"
}"""
        },
        {"role": "user", "content": f"Current macro data:\n\n{context}"},
    ]

    try:
        response = chat_completion(messages)
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        try:
            ai_analysis = json.loads(cleaned)
        except json.JSONDecodeError:
            ai_analysis = {"outlook": "Unknown", "raw_response": response}

    except Exception as e:
        ai_analysis = {"error": str(e)}

    return {
        "macro_data": data,
        "analysis": ai_analysis,
    }


if __name__ == "__main__":
    result = analyze_macro()
    print(json.dumps(result, indent=2, default=str))
