"""
Sentiment AI — Auto-analyze news sentiment for a stock/crypto ticker.
Uses existing news.py + LLM for sentiment scoring.
Saves results to analysis_history for AI memory.
"""

import json
from news import fetch_news
from ai_client import chat_completion
from database import save_analysis_history
from logger import get_logger

log = get_logger("sentiment_ai")


def analyze_sentiment(ticker, limit=5, skip_llm=True):
    """
    Fetch news for a ticker and optionally analyze sentiment using LLM.
    skip_llm=True: return raw headlines (agent does reasoning).

    Returns:
        dict with per-article sentiment and overall score.
        Score: -100 (very bearish) to +100 (very bullish).
    """
    # 1. Fetch news
    news_data = fetch_news(ticker, limit)
    if "error" in news_data:
        return news_data

    if not news_data.get("news"):
        return {
            "ticker": ticker,
            "sentiment_score": 0,
            "sentiment_label": "Neutral",
            "articles": [],
            "summary": "Tidak ada berita ditemukan untuk ticker ini.",
            "llm_analyzed": False,
        }

    if skip_llm:
        # Agent-centric: return raw headlines, let agent reason
        result = {
            "ticker": ticker,
            "news_count": len(news_data["news"]),
            "articles": news_data["news"],
            "llm_analyzed": False,
        }
        save_analysis_history(ticker, "sentiment", result)
        return result

    # 2. Build prompt with news headlines
    headlines = "\n".join(
        [f"{i+1}. {n['title']} ({n.get('date', 'unknown')})" for i, n in enumerate(news_data["news"])]
    )

    messages = [
        {
            "role": "system",
            "content": """You are CuanBot Sentiment Analyst. Analyze these news headlines for a stock/crypto.
RESPOND IN VALID JSON ONLY:
{
    "articles": [
        {
            "title": "headline text",
            "sentiment": "Bullish / Bearish / Neutral",
            "score": number_from_minus100_to_plus100,
            "reason": "brief 1-sentence reason"
        }
    ],
    "overall_score": number_from_minus100_to_plus100,
    "overall_sentiment": "Bullish / Bearish / Neutral",
    "summary": "2-3 sentence summary in Bahasa Indonesia (santai) tentang sentimen pasar untuk saham/crypto ini"
}

Scoring guide:
- Strong Bullish: +60 to +100 (major positive catalyst, earnings beat, contract win)
- Mild Bullish: +20 to +59 (positive sentiment, growth news)
- Neutral: -19 to +19 (routine news, no clear direction)
- Mild Bearish: -20 to -59 (negative sentiment, concerns)
- Strong Bearish: -60 to -100 (scandal, loss, regulatory action)"""
        },
        {
            "role": "user",
            "content": f"Ticker: {ticker}\n\nNews Headlines:\n{headlines}",
        },
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
            result = json.loads(cleaned)
            result["ticker"] = ticker
            result["news_count"] = len(news_data["news"])
            result["llm_analyzed"] = True
            # Save to history
            save_analysis_history(ticker, "sentiment", result)
            return result
        except json.JSONDecodeError:
            return {
                "ticker": ticker,
                "sentiment_score": 0,
                "sentiment_label": "Unknown",
                "summary": response,
                "raw_response": response,
                "llm_analyzed": True,
            }

    except Exception as e:
        return {"error": f"Sentiment analysis failed: {str(e)}"}


if __name__ == "__main__":
    import sys

    ticker = sys.argv[1] if len(sys.argv) > 1 else "BBCA.JK"
    result = analyze_sentiment(ticker)
    print(json.dumps(result, indent=2, default=str))
