"""
AI Memory — gives CuanBot's LLM contextual awareness of past analyses.
Builds memory context from analysis_history and feedback stats
to inject into AI prompts, making the AI "remember" past verdicts.
"""

import json
from database import get_analysis_history, get_feedback_stats
from logger import get_logger

log = get_logger("ai_memory")


def build_memory_context(symbol, limit=5):
    """
    Fetch the last N analyses for a symbol and format as LLM context.
    Returns a formatted string summarizing past verdicts.
    """
    history = get_analysis_history(symbol, analysis_type="ai_advisor", limit=limit)

    if not history:
        # Fall back to technical analysis history
        history = get_analysis_history(symbol, analysis_type="technical", limit=limit)

    if not history:
        return None

    lines = []
    for entry in history:
        data = entry.get("analysis_data", {})
        created = str(entry.get("created_at", ""))[:10]  # date only
        atype = entry.get("analysis_type", "unknown")

        if atype == "ai_advisor":
            verdict_data = data.get("ai_verdict", {})
            verdict = verdict_data.get("verdict", "N/A")
            confidence = verdict_data.get("confidence", "N/A")
            reasoning = verdict_data.get("reasoning", "")[:100]
            lines.append(f"- [{created}] AI Verdict: {verdict} (confidence: {confidence}) — {reasoning}")
        elif atype == "technical":
            verdict = data.get("verdict", "N/A")
            rsi = data.get("momentum", {}).get("rsi", "N/A")
            trend = data.get("trend", {}).get("status", "N/A")
            price = data.get("price", "N/A")
            lines.append(f"- [{created}] Technical: {verdict} | RSI: {rsi} | Trend: {trend} | Price: {price}")
        elif atype == "sentiment":
            score = data.get("overall_score", "N/A")
            sentiment = data.get("overall_sentiment", "N/A")
            lines.append(f"- [{created}] Sentiment: {sentiment} (score: {score})")
        elif atype == "bandarilogi":
            status = data.get("bandar_status", "N/A")
            lines.append(f"- [{created}] Bandarilogi: {status}")
        else:
            lines.append(f"- [{created}] {atype}: (data available)")

    return "\n".join(lines) if lines else None


def build_feedback_context(symbol):
    """
    Build feedback accuracy stats for a symbol.
    Returns a formatted string describing past accuracy.
    """
    stats = get_feedback_stats(symbol)

    if not stats or stats.get("total", 0) == 0:
        return None

    total = stats["total"]
    accuracy = stats.get("accuracy_pct")
    positive = stats.get("positive", 0)
    negative = stats.get("negative", 0)

    if accuracy is not None:
        return (
            f"Past analysis accuracy for {symbol}: {accuracy}% "
            f"({positive} 👍 / {negative} 👎 dari {total} reviews). "
            f"{'Tingkatkan kualitas analisa!' if accuracy < 60 else 'Akurasi baik, pertahankan!'}"
        )
    return None


def format_memory_prompt(symbol):
    """
    Build the full memory section for injection into LLM prompts.
    Returns a string, or None if no memory available.
    """
    parts = []

    memory = build_memory_context(symbol)
    if memory:
        parts.append(f"## Riwayat Analisa Sebelumnya ({symbol})\n{memory}")

    feedback = build_feedback_context(symbol)
    if feedback:
        parts.append(f"## Feedback Akurasi\n{feedback}")

    if not parts:
        return None

    return "\n\n".join(parts)
