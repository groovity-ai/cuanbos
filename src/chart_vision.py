"""
Chart Pattern Vision 👁️ — "The Eye"
Analyze candlestick chart screenshots using Gemini Vision via OpenClaw.
"""

import json
from ai_client import vision_completion

CHART_VISION_PROMPT = """You are CuanBot, an expert technical analyst AI.
Analyze this candlestick/price chart image carefully.

RESPOND IN VALID JSON ONLY with this exact structure:
{
    "patterns": [
        {"name": "pattern name", "confidence": "high/medium/low", "description": "brief explanation"}
    ],
    "support_resistance": {
        "support_levels": [price1, price2],
        "resistance_levels": [price1, price2]
    },
    "trend": "Bullish/Bearish/Sideways",
    "verdict": "Breakout Potential / Reversal Risk / Consolidation / Continuation",
    "explanation": "2-3 sentence human-readable explanation in Bahasa Indonesia (santai tapi data-driven)"
}

Patterns to look for: Head & Shoulders, Double Top/Bottom, Triangles (Ascending/Descending/Symmetrical), 
Flags/Pennants, Cup & Handle, Wedges, Channel patterns, and Support/Resistance zones.

If you cannot clearly identify patterns, say so. Be honest and data-driven."""


def analyze_chart(image_bytes):
    """
    Analyze a chart image using Gemini Vision.
    
    Args:
        image_bytes: Raw bytes of the chart image (PNG/JPG).
    
    Returns:
        dict with patterns, support/resistance, trend, verdict.
    """
    try:
        response = vision_completion(image_bytes, CHART_VISION_PROMPT)

        # Try to parse as JSON
        # Sometimes LLM wraps in ```json ... ```
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]  # Remove first line
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        try:
            result = json.loads(cleaned)
            result["raw_response"] = None  # Don't include raw if parsed OK
            return result
        except json.JSONDecodeError:
            # Return raw response if JSON parsing fails
            return {
                "patterns": [],
                "support_resistance": {"support_levels": [], "resistance_levels": []},
                "trend": "Unknown",
                "verdict": "Unable to parse structured response",
                "explanation": response,
                "raw_response": response,
            }

    except Exception as e:
        return {"error": f"Chart analysis failed: {str(e)}"}
